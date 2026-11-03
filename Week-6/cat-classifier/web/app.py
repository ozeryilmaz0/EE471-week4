"""Web front end for the Cog cat-kind classifier.

The browser uploads a photo to /api/classify. This app turns it into a
base64 data URI and forwards it to the Cog HTTP API (POST /predictions).
"""

import base64
import mimetypes
import os

import requests
from flask import Flask, jsonify, request

# Where the Cog container listens. In docker-compose this is http://cog:5000.
COG_URL = os.environ.get("COG_URL", "http://localhost:5002").rstrip("/")

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB upload limit


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
        mime = mimetypes.guess_type(file_storage.filename or "")[0] or "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def cog_status():
    """Return Cog's health-check status ("READY", "STARTING", ...) or None if unreachable."""
    try:
        response = requests.get(f"{COG_URL}/health-check", timeout=5)
        return response.json().get("status")
    except (requests.RequestException, ValueError):
        return None


@app.get("/")
def index():
    """Serve the single-page front end."""
    return app.send_static_file("index.html")


@app.post("/api/classify")
def classify():
    """Classify an uploaded photo (multipart field 'image') with the Cog model."""
    upload = request.files.get("image")
    if upload is None or not upload.filename:
        return error("Please choose a photo first.", 400)
    if upload.mimetype and not upload.mimetype.startswith("image/"):
        return error("That file is not an image.", 400)
    data_uri = to_data_uri(upload)
    if data_uri is None:
        return error("The uploaded file is empty.", 400)

    status = cog_status()
    if status != "READY":
        detail = f"status: {status}" if status else "not reachable"
        return error(f"The cat model is not ready yet ({detail}). Please try again soon.", 503)

    try:
        response = requests.post(f"{COG_URL}/predictions",
                                 json={"input": {"image": data_uri}}, timeout=120)
        prediction = response.json()
    except (requests.RequestException, ValueError):
        return error("The cat model did not answer. Please try again.", 503)

    if response.status_code != 200 or prediction.get("status") != "succeeded":
        return error(prediction.get("error") or "The cat model could not classify this photo.", 502)
    return jsonify(prediction["output"])


@app.errorhandler(413)
def too_large(_):
    """Uploads above MAX_CONTENT_LENGTH."""
    return error("The photo is too large (max 10 MB).", 413)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
