"""Speech-to-text: browser recording -> ffmpeg (16 kHz mono wav) -> whisper-small (CPU)."""

from __future__ import annotations

import subprocess
import tempfile
import threading
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor

from config import STT_MODEL

SAMPLE_RATE = 16_000
MIN_SECONDS = 0.4      # shorter clips are treated as empty
SILENCE_RMS = 0.004    # below this the recording is considered silent


class AudioError(ValueError):
    """Raised for empty, silent or unreadable recordings (HTTP 422)."""


def to_wav_16k_mono(data: bytes, suffix: str = ".webm") -> np.ndarray:
    """Convert any ffmpeg-readable audio to a 16 kHz mono float32 array."""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / f"input{suffix}"
        dst = Path(tmp) / "audio.wav"
        src.write_bytes(data)
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-i", str(src), "-ac", "1", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", str(dst)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0 or not dst.exists():
            raise AudioError("Could not read the recording. Please try again.")
        audio, _ = sf.read(dst, dtype="float32")
    return audio


class SpeechService:
    def __init__(self) -> None:
        self.processor = WhisperProcessor.from_pretrained(STT_MODEL)
        self.model = WhisperForConditionalGeneration.from_pretrained(STT_MODEL, torch_dtype=torch.float32)
        self.model.eval()
        self._lock = threading.Lock()

    def warm_up(self) -> float:
        start = time.perf_counter()
        t = np.linspace(0, 1, SAMPLE_RATE, dtype=np.float32)
        self._transcribe_array(0.1 * np.sin(2 * np.pi * 220 * t))
        return time.perf_counter() - start

    def _transcribe_array(self, audio: np.ndarray) -> str:
        features = self.processor(audio, sampling_rate=SAMPLE_RATE, return_tensors="pt").input_features
        with self._lock, torch.inference_mode():
            ids = self.model.generate(features, language="en", task="transcribe", max_new_tokens=128)
        return self.processor.batch_decode(ids, skip_special_tokens=True)[0].strip()

    def transcribe(self, data: bytes, suffix: str = ".webm") -> tuple[str, float]:
        """Return (text, seconds). Raises AudioError for empty or silent input."""
        if not data:
            raise AudioError("The recording is empty. Hold the mic a bit longer and speak.")
        start = time.perf_counter()
        audio = to_wav_16k_mono(data, suffix)
        if audio.size < MIN_SECONDS * SAMPLE_RATE:
            raise AudioError("The recording is too short. Please speak for at least a second.")
        rms = float(np.sqrt(np.mean(np.square(audio))))
        if rms < SILENCE_RMS:
            raise AudioError("I could not hear anything. Check your microphone and try again.")
        text = self._transcribe_array(audio)
        if not text:
            raise AudioError("No speech was recognized. Please try again.")
        return text, time.perf_counter() - start
