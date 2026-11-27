"""End-to-end API tests for DreamCanvas AI (the server must be running on 127.0.0.1:5000).

Creates its test audio with Windows SAPI (PowerShell System.Speech) and ffmpeg:
  test_audio/hello.wav  -> "Hello, can you help me draw a picture?"
  test_audio/hello.webm -> same, Opus/WebM like a browser recording
  test_audio/silence.webm, test_audio/empty.webm

Usage (from the repo root):
    venv\\Scripts\\python.exe MiniProject3\\test_api.py
"""

from __future__ import annotations

import base64
import io
import subprocess
import sys
import time
from pathlib import Path

import requests
from PIL import Image

BASE = "http://127.0.0.1:5000"
HERE = Path(__file__).resolve().parent
AUDIO = HERE / "test_audio"
OUT = HERE / "outputs"
SENTENCE = "Hello, can you help me draw a picture?"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}  {detail}", flush=True)


def make_audio() -> None:
    AUDIO.mkdir(exist_ok=True)
    wav = AUDIO / "hello.wav"
    ps = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.SetOutputToWaveFile('{wav}'); $s.Speak('{SENTENCE}'); $s.Dispose()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    ff = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    subprocess.run(ff + ["-i", str(wav), "-c:a", "libopus", "-b:a", "48k", str(AUDIO / "hello.webm")], check=True)
    subprocess.run(ff + ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", "2",
                         "-c:a", "libopus", str(AUDIO / "silence.webm")], check=True)
    (AUDIO / "empty.webm").write_bytes(b"")


def test_chat() -> None:
    question = "Can you give me a prompt for a beautiful fantasy landscape image?"
    t = time.perf_counter()
    r = requests.post(f"{BASE}/api/chat", json={"messages": [{"role": "user", "content": question}]})
    elapsed = time.perf_counter() - t
    reply = r.json().get("reply", "")
    words = len(reply.split())
    ok = r.status_code == 200 and 5 <= words <= 40 and not reply.startswith('"')
    check("chat: image prompt request", ok, f"{elapsed:.2f}s, {words} words -> {reply}")

    convo = [
        {"role": "user", "content": question},
        {"role": "assistant", "content": reply},
        {"role": "user", "content": "Thanks! What colors would look nice in it?"},
    ]
    t = time.perf_counter()
    r = requests.post(f"{BASE}/api/chat", json={"messages": convo})
    elapsed = time.perf_counter() - t
    reply2 = r.json().get("reply", "")
    check("chat: follow-up turn", r.status_code == 200 and reply2.rstrip()[-1:] in ".!?", f"{elapsed:.2f}s -> {reply2}")

    r = requests.post(f"{BASE}/api/chat", json={"messages": []})
    check("chat: empty messages -> 400", r.status_code == 400 and "error" in r.json(), r.text.strip())


def test_image() -> str | None:
    prompt = "a beautiful fantasy landscape with floating islands, waterfalls and a glowing castle, golden hour, digital painting"
    t = time.perf_counter()
    r = requests.post(f"{BASE}/api/generate-image", json={"prompt": prompt})
    elapsed = time.perf_counter() - t
    path = None
    ok = False
    detail = r.text[:200]
    if r.status_code == 200:
        data = r.json()
        png = base64.b64decode(data["image"])
        img = Image.open(io.BytesIO(png))
        OUT.mkdir(exist_ok=True)
        path = OUT / "test_api_landscape.png"
        path.write_bytes(png)
        ok = png[:8] == b"\x89PNG\r\n\x1a\n" and img.size == (512, 512) and (OUT / data["file"]).exists()
        detail = f"server {data['seconds']}s, round trip {elapsed:.2f}s, {img.size}, saved {data['file']}"
    check("generate-image: valid 512x512 PNG", ok, detail)

    r = requests.post(f"{BASE}/api/generate-image", json={"prompt": "   "})
    check("generate-image: empty prompt -> 400", r.status_code == 400 and "error" in r.json(), r.text.strip())
    return str(path) if path else None


def post_audio(name: str):
    with open(AUDIO / name, "rb") as fh:
        t = time.perf_counter()
        r = requests.post(f"{BASE}/api/transcribe", files={"audio": (name, fh, "audio/webm")})
    return r, time.perf_counter() - t


def test_transcribe() -> None:
    r, elapsed = post_audio("hello.webm")
    text = r.json().get("text", "") if r.ok else r.text
    norm = "".join(c for c in text.lower() if c.isalnum() or c == " ")
    ok = r.status_code == 200 and "help me draw a picture" in norm
    check("transcribe: SAPI webm", ok, f"{elapsed:.2f}s -> {text}")

    for name in ("silence.webm", "empty.webm"):
        r, _ = post_audio(name)
        check(f"transcribe: {name} -> 422", r.status_code == 422 and "error" in r.json(), r.text.strip())

    r = requests.post(f"{BASE}/api/transcribe")
    check("transcribe: no file -> 400", r.status_code == 400 and "error" in r.json(), r.text.strip())


def main() -> int:
    make_audio()
    health = requests.get(f"{BASE}/api/health").json()
    print("health:", health, flush=True)
    test_chat()
    image = test_image()
    test_transcribe()
    passed = sum(ok for _, ok, _ in results)
    print(f"\n{passed}/{len(results)} checks passed. Test image: {image}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
