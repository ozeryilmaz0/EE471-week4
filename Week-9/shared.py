"""Helpers shared by the Task 1 and Task 4 scripts and the recording runner.

Every task script exposes the same small interface so it can run on its own
(``python task1/sentiment_analysis.py``) and also inside ``run_task1_task4.py``:

    TITLE        upper-case task name shown in the big title
    MODEL        Hugging Face model id
    inputs()     list of (label, text-or-renderable) pairs that describe the input
    load()       load the pipeline / tokenizer (cached, so it is loaded only once)
    run(obj)     do the work and return a plain Python result
    render(res)  turn the result into a rich renderable
"""

from __future__ import annotations

import os
import sys
import time
import warnings
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any

# Models are downloaded once with download_models.py; after that we never touch the network,
# so loading is fast and the demos also work offline.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
warnings.filterwarnings("ignore")

import torch  # noqa: E402
from rich.console import Console, Group  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.table import Table  # noqa: E402
from rich.text import Text  # noqa: E402
from transformers import pipeline  # noqa: E402
from transformers.utils import logging as hf_logging  # noqa: E402

hf_logging.set_verbosity_error()

WEEK_DIR = Path(__file__).resolve().parent
ASSETS = WEEK_DIR / "assets"
IMAGE_PATH = ASSETS / "tiger.jpg"
AUDIO_PATH = ASSETS / "speech.flac"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
console = Console(highlight=False)

GPU = torch.cuda.is_available()


@lru_cache(maxsize=None)
def get_pipeline(task: str, model: str, gpu_fp16: bool = False) -> Any:
    """Create a pipeline once per process.

    Only whisper-large-v3 asks for ``gpu_fp16``: in fp16 it needs about 3 GB, which
    fits the 4 GB RTX 3050 Ti. The other models are small enough to stay on the CPU.
    """
    if gpu_fp16 and GPU:
        return pipeline(task, model=model, device="cuda:0", dtype=torch.float16)
    return pipeline(task, model=model, device="cpu")


def table(*columns: str, title: str | None = None, **kwargs: Any) -> Table:
    """A table with the common style of all demos."""
    t = Table(title=title, header_style="bold cyan", border_style="bright_black",
              title_style="bold", **kwargs)
    for col in columns:
        t.add_column(col)
    return t


def stack(*items: Any) -> Group:
    """Stack renderables vertically with one empty line between them."""
    out: list[Any] = []
    for item in items:
        if out:
            out.append(Text())
        out.append(item)
    return Group(*out)


def score_bar(score: float, width: int = 20) -> Text:
    """A small coloured bar for a probability between 0 and 1."""
    filled = round(score * width)
    colour = "green" if score >= 0.6 else "yellow" if score >= 0.3 else "red"
    return Text("█" * filled, style=colour) + Text("░" * (width - filled), style="bright_black") \
        + Text(f" {score:6.1%}", style="bold")


def image_preview(path: Path, width: int = 44) -> Text:
    """Draw a small colour thumbnail of an image with half-block characters."""
    from PIL import Image

    img = Image.open(path).convert("RGB")
    height = max(2, round(width * img.height / img.width / 2) * 2)
    img = img.resize((width, height))
    px = img.load()
    out = Text()
    for y in range(0, height, 2):
        for x in range(width):
            top, bottom = px[x, y], px[x, y + 1]
            out.append("▀", style=f"rgb({top[0]},{top[1]},{top[2]}) on rgb({bottom[0]},{bottom[1]},{bottom[2]})")
        if y + 2 < height:
            out.append("\n")
    return out


def load_audio(path: Path, target_sr: int = 16000) -> tuple[Any, int]:
    """Read an audio file as mono float32 at ``target_sr`` Hz (what Whisper expects)."""
    import numpy as np
    import soundfile as sf

    audio, sr = sf.read(str(path), dtype="float32", always_2d=True)
    audio = audio.mean(axis=1)
    if sr != target_sr:
        import librosa
        audio = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)
    return np.ascontiguousarray(audio, dtype="float32"), target_sr


def waveform(audio: Any, sr: int, width: int = 60) -> Text:
    """A one-line waveform of an audio clip and its duration."""
    import numpy as np

    levels = " ▁▂▃▄▅▆▇█"
    chunks = np.array_split(np.abs(audio), width)
    peaks = np.array([c.max() if len(c) else 0.0 for c in chunks])
    peaks = peaks / (peaks.max() or 1.0)
    line = "".join(levels[int(p * (len(levels) - 1))] for p in peaks)
    return Text(line, style="cyan") + Text(f"  {len(audio) / sr:.1f} s @ {sr} Hz", style="dim")


def input_panel(module: ModuleType) -> Panel:
    """Show the inputs of a task as a labelled grid."""
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold magenta", no_wrap=True)
    grid.add_column()
    for label, value in module.inputs():
        grid.add_row(label, Text(value) if isinstance(value, str) else value)
    return Panel(grid, title="[bold]INPUT", subtitle=f"model: {module.MODEL}",
                 border_style="magenta", padding=(1, 2))


def run_standalone(module: ModuleType) -> None:
    """Entry point used by every script's ``if __name__ == "__main__"`` block."""
    console.rule(f"[bold cyan]{module.TITLE}")
    console.print(input_panel(module))
    start = time.perf_counter()
    obj = module.load()
    console.print(f"[dim]Loaded in {time.perf_counter() - start:.1f} s[/]")
    start = time.perf_counter()
    result = module.run(obj)
    elapsed = time.perf_counter() - start
    console.print(Panel(module.render(result), title="[bold]OUTPUT", border_style="green",
                        subtitle=f"inference {elapsed:.2f} s", padding=(1, 2)))
