"""DreamCanvas AI - Flask backend.

Routes
  GET  /                     -> web app
  GET  /api/health           -> model status + warm-up times
  POST /api/generate-image   -> {prompt} -> {image (base64 PNG), seconds, file}
  POST /api/transcribe       -> multipart 'audio' -> {text, seconds}
  POST /api/chat             -> {messages: [{role, content}]} -> {reply, seconds}

Run (from the repo root):
    venv\\Scripts\\python.exe MiniProject3\\app.py
"""

from __future__ import annotations

import base64
import logging
import os
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")  # models come from download_models.py

from flask import Flask, jsonify, render_template, request  # noqa: E402
from werkzeug.exceptions import HTTPException  # noqa: E402

from chat_service import ChatService  # noqa: E402
from config import HOST, PORT  # noqa: E402
from image_service import ImageService  # noqa: E402
from stt_service import AudioError, SpeechService  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("dreamcanvas")

MAX_PROMPT_CHARS = 500

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB audio upload limit


def load_models() -> dict:
    timings = {}
    services = {}
    for name, cls in (("image", ImageService), ("chat", ChatService), ("stt", SpeechService)):
        start = time.perf_counter()
        services[name] = cls()
        load = time.perf_counter() - start
        warm = services[name].warm_up()
        timings[name] = {"load_s": round(load, 2), "warmup_s": round(warm, 2)}
        log.info("%s model loaded in %.1fs, warm-up %.1fs", name, load, warm)
    services["timings"] = timings
    return services


SERVICES: dict = {}


def error(message: str, status: int):
    return jsonify({"error": message}), status


@app.errorhandler(HTTPException)
def handle_http_error(exc: HTTPException):
    return error(exc.description or exc.name, exc.code or 500)


@app.errorhandler(Exception)
def handle_unexpected(exc: Exception):
    log.exception("Unhandled error")
    return error(f"Internal server error: {exc}", 500)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def health():
    image = SERVICES.get("image")
    return jsonify({
        "status": "ok",
        "device": image.device if image else None,
        "cpu_offload": image.offloaded if image else None,
        "timings": SERVICES.get("timings", {}),
    })


@app.post("/api/generate-image")
def generate_image():
    data = request.get_json(silent=True) or {}
    prompt = str(data.get("prompt", "")).strip()
    if not prompt:
        return error("Please enter a prompt first.", 400)
    if len(prompt) > MAX_PROMPT_CHARS:
        return error(f"The prompt is too long (max {MAX_PROMPT_CHARS} characters).", 400)
    seed = data.get("seed")
    seed = int(seed) if isinstance(seed, (int, float, str)) and str(seed).lstrip("-").isdigit() else None

    png, seconds, filename = SERVICES["image"].generate(prompt, seed=seed)
    log.info("image %.2fs  %s", seconds, prompt[:60])
    return jsonify({
        "image": base64.b64encode(png).decode("ascii"),
        "seconds": round(seconds, 2),
        "file": filename,
    })


@app.post("/api/transcribe")
def transcribe():
    upload = request.files.get("audio")
    if upload is None:
        return error("No audio file was sent (expected multipart field 'audio').", 400)
    data = upload.read()
    suffix = Path(upload.filename or "audio.webm").suffix or ".webm"
    try:
        text, seconds = SERVICES["stt"].transcribe(data, suffix=suffix)
    except AudioError as exc:
        return error(str(exc), 422)
    log.info("transcribe %.2fs  %s", seconds, text[:60])
    return jsonify({"text": text, "seconds": round(seconds, 2)})


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    messages = data.get("messages")
    if not isinstance(messages, list) or not messages:
        return error("'messages' must be a non-empty list of {role, content}.", 400)
    start = time.perf_counter()
    try:
        reply = SERVICES["chat"].reply(messages)
    except ValueError as exc:
        return error(str(exc), 400)
    seconds = time.perf_counter() - start
    log.info("chat %.2fs  %s", seconds, reply[:60])
    return jsonify({"reply": reply, "seconds": round(seconds, 2)})


if __name__ == "__main__":
    SERVICES.update(load_models())
    log.info("DreamCanvas AI ready on http://%s:%d", HOST, PORT)
    app.run(host=HOST, port=PORT, debug=False, threaded=True, use_reloader=False)
