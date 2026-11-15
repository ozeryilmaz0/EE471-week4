"""Web front end that compares two Cog models side by side.

The browser uploads an image to /api/classify. The app turns it into a base64
data URI and sends it to the baseline and the optimized Cog containers in
parallel (POST /predictions), then returns both results with their response
times.

Environment variables:
  APP_TITLE      page title, e.g. "Garment Classifier 👕"
  BASELINE_URL   baseline Cog server, e.g. http://fashion-baseline:5000
  OPTIMIZED_URL  optimized Cog server, e.g. http://fashion-optimized:5000
  SAMPLES_DIR    folder with sample images for the "Try a sample" gallery
"""

import base64
import mimetypes
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from flask import Flask, abort, jsonify, request, send_from_directory

APP_TITLE = os.environ.get("APP_TITLE", "Image Classifier")
MODELS = {
    "baseline": os.environ.get("BASELINE_URL", "http://localhost:5010").rstrip("/"),
    "optimized": os.environ.get("OPTIMIZED_URL", "http://localhost:5011").rstrip("/"),
}
SAMPLES_DIR = Path(os.environ.get("SAMPLES_DIR", "samples"))
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB upload limit
pool = ThreadPoolExecutor(max_workers=8)


def error(message, status):
    """Return a JSON error response."""
    return jsonify(error=message), status


def to_data_uri(file_storage):
    """Read an uploaded file and return it as a base64 data URI, or None if empty."""
    data = file_storage.read()
    if not data:
        return None
    mime = file_storage.mimetype
    if not mime or not mime.startswith("image/"):
        mime = mimetypes.guess_type(file_storage.filename or "")[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def predict(url, data_uri):
    """Send one image to one Cog server. Never raises; errors go into the result."""
    start = time.perf_counter()
    result = {"ok": False, "output": None, "error": None}
    try:
        response = requests.post(f"{url}/predictions", json={"input": {"image": data_uri}},
                                 timeout=60)
        prediction = response.json()
        if response.status_code == 200 and prediction.get("status") == "succeeded":
            result.update(ok=True, output=prediction["output"])
        else:
            result["error"] = prediction.get("error") or f"HTTP {response.status_code}"
    except requests.ConnectionError:
        result["error"] = "Model server is not reachable (is the container running?)"
    except (requests.RequestException, ValueError) as exc:
        result["error"] = f"Model server did not answer: {exc.__class__.__name__}"
    result["time_ms"] = round((time.perf_counter() - start) * 1000)
    return result


def list_samples():
    if not SAMPLES_DIR.is_dir():
        return []
    return sorted(p.name for p in SAMPLES_DIR.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)


@app.get("/")
def index():
    """Serve the single-page front end."""
    return app.send_static_file("index.html")


@app.get("/api/config")
def config():
    """Page title and sample file names for the front end."""
    return jsonify(title=APP_TITLE, samples=list_samples())


@app.get("/samples/<path:name>")
def sample(name):
    if name not in list_samples():
        abort(404)
    return send_from_directory(SAMPLES_DIR.resolve(), name)


@app.get("/api/health")
def health():
    """Health-check status of both Cog servers."""
    def status(url):
        try:
            return requests.get(f"{url}/health-check", timeout=3).json().get("status")
        except (requests.RequestException, ValueError):
            return None
    return jsonify({name: status(url) for name, url in MODELS.items()})


@app.post("/api/classify")
def classify():
    """Classify an uploaded image (multipart field 'image') with both models in parallel."""
    upload = request.files.get("image")
    if upload is None or not upload.filename:
        return error("Please choose an image first.", 400)
    if upload.mimetype and not upload.mimetype.startswith("image/"):
        return error("That file is not an image.", 400)
    data_uri = to_data_uri(upload)
    if data_uri is None:
        return error("The uploaded file is empty.", 400)

    futures = {name: pool.submit(predict, url, data_uri) for name, url in MODELS.items()}
    results = {name: future.result() for name, future in futures.items()}
    base, opt = results["baseline"], results["optimized"]
    agree = None
    if base["ok"] and opt["ok"]:
        agree = base["output"]["predicted_class"] == opt["output"]["predicted_class"]
    return jsonify(baseline=base, optimized=opt, agree=agree)


@app.errorhandler(413)
def too_large(_):
    """Uploads above MAX_CONTENT_LENGTH."""
    return error("The image is too large (max 10 MB).", 413)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
