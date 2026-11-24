"""Task 1.10 - Automatic speech recognition with pipeline() (Whisper large-v3).

Whisper large-v3 has 1.55 B parameters. In fp16 it needs about 3 GB of GPU memory,
so it runs on the 4 GB RTX 3050 Ti. Without a GPU it falls back to the CPU (slow).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rich.text import Text  # noqa: E402
from shared import AUDIO_PATH, GPU, get_pipeline, load_audio, run_standalone, waveform  # noqa: E402

TITLE = "SPEECH RECOGNITION"
MODEL = "openai/whisper-large-v3"


def inputs():
    audio, sr = load_audio(AUDIO_PATH)
    return [("Audio", f"assets/{AUDIO_PATH.name}"), ("Waveform", waveform(audio, sr)),
            ("Device", "GPU (cuda, fp16)" if GPU else "CPU (fp32)")]


def load():
    return get_pipeline("automatic-speech-recognition", MODEL, gpu_fp16=True)


def run(asr):
    audio, sr = load_audio(AUDIO_PATH)
    # The ASR pipeline defaults to beam search with 5 beams. Greedy decoding (num_beams=1)
    # gives the same text here, is ~10x faster and keeps Whisper inside the 4 GB of VRAM.
    out = asr({"raw": audio, "sampling_rate": sr},
              generate_kwargs={"language": "english", "task": "transcribe", "num_beams": 1})
    return out["text"].strip()


def render(result):
    return Text(f"“{result}”", style="bold green")


if __name__ == "__main__":
    run_standalone(sys.modules[__name__])
