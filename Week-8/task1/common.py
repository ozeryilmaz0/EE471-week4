"""Shared helpers for the Week 8 MediaPipe demos (paths, printing, images, audio).

Environment variables (handy for automatic test runs):
    MP_DEMO_NO_OPEN=1   do not open the result PNG
    MP_DEMO_NO_AUDIO=1  do not play sound
"""

import os
import time
from pathlib import Path

import cv2
import numpy as np

TASK1 = Path(__file__).resolve().parent
WEEK8 = TASK1.parent
MODELS = WEEK8 / "models"
ASSETS = WEEK8 / "assets"
INPUTS = WEEK8 / "inputs"
OUTPUTS = TASK1 / "outputs"

_START = time.perf_counter()


def model(name):
    """Return the path of a model file and fail with a clear hint if it is missing."""
    path = MODELS / name
    if not path.exists():
        raise SystemExit(f"Model not found: {path}\nRun: .venv\\Scripts\\python.exe download_models.py")
    return str(path)


def header(title, what):
    """Print the demo title and a one-line description."""
    print("=" * 70)
    print(f"  {title}")
    print(f"  {what}")
    print("=" * 70)


def section(text):
    print(f"\n--- {text} ---")


def done():
    print(f"\nFinished in {time.perf_counter() - _START:.1f} s")


def read_text(name):
    return (ASSETS / name).read_text(encoding="utf-8").strip()


# ---------- images ----------

def load_bgr(path):
    """Read an image with OpenCV (BGR)."""
    img = cv2.imread(str(path))
    if img is None:
        raise SystemExit(f"Cannot read image: {path}")
    return img


def load_mp(path, min_side=None):
    """Read an image as (mp.Image, writable RGB array).

    Small inputs (like the 260 px assignment photos) can be upscaled so that the
    shorter side is at least min_side pixels; this helps the face and pose models.
    """
    import mediapipe as mp
    rgb = cv2.cvtColor(load_bgr(path), cv2.COLOR_BGR2RGB)
    if min_side and min(rgb.shape[:2]) < min_side:
        f = min_side / min(rgb.shape[:2])
        rgb = cv2.resize(rgb, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
    rgb = np.ascontiguousarray(rgb)
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), rgb.copy()


def rgb2bgr(rgb):
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def to_rgb(mp_image):
    """mp.Image -> writable RGB numpy array (drops alpha if present)."""
    arr = np.copy(mp_image.numpy_view())
    if arr.ndim == 3 and arr.shape[2] == 4:
        arr = arr[:, :, :3]
    return arr


def label(img, text, org=(10, 30), scale=0.8, color=(255, 255, 255)):
    """Draw text on a dark box so it is readable on any background (org = text baseline)."""
    thick = max(1, int(round(scale * 2)))
    (tw, th), base = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
    x, y = int(max(0, org[0])), int(max(th + 6, org[1]))
    cv2.rectangle(img, (x - 4, y - th - 6), (x + tw + 4, y + base + 2), (30, 30, 30), -1)
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)


def montage(images, height=480):
    """Resize BGR images to the same height and put them side by side."""
    row = []
    for img in images:
        h, w = img.shape[:2]
        row.append(cv2.resize(img, (max(1, int(w * height / h)), height)))
        row.append(np.full((height, 8, 3), 255, np.uint8))
    return np.hstack(row[:-1])


def save_and_show(img_bgr, name):
    """Save the result PNG under task1/outputs and open it with the default viewer."""
    OUTPUTS.mkdir(exist_ok=True)
    out = OUTPUTS / name
    cv2.imwrite(str(out), img_bgr)
    print(f"\nResult image saved: {out}")
    if os.environ.get("MP_DEMO_NO_OPEN") != "1" and hasattr(os, "startfile"):
        os.startfile(out)  # Windows: open with the default image viewer
    return out


# ---------- audio ----------

def load_wav_mono(path):
    """Read a WAV file as mono float32 samples in [-1, 1]."""
    import soundfile as sf
    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    return data.mean(axis=1), sr


def play(samples, sample_rate):
    """Play mono float samples and wait until playback ends."""
    if os.environ.get("MP_DEMO_NO_AUDIO") == "1":
        print("(audio playback skipped)")
        return
    import sounddevice as sd
    sd.play(np.asarray(samples, dtype=np.float32), int(sample_rate))
    sd.wait()
