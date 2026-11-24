"""Task 4.1 - Load a model and tokenizer, save them, list the files and load them back.

AutoModel / AutoTokenizer.from_pretrained  ->  save_pretrained("saved_model")
->  list the saved files with their sizes  ->  from_pretrained("saved_model").
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import torch  # noqa: E402
from rich.columns import Columns  # noqa: E402
from rich.text import Text  # noqa: E402
from shared import get_model, get_tokenizer, run_standalone, table  # noqa: E402
from transformers import AutoModel, AutoTokenizer  # noqa: E402

TITLE = "LOAD AND SAVE"
MODEL = "bert-base-cased"
SAVE_DIR = Path(__file__).resolve().parent / "saved_model"


def inputs():
    return [("Checkpoint", MODEL), ("Save to", f"task4/{SAVE_DIR.name}/"),
            ("Steps", "from_pretrained → save_pretrained → list files → from_pretrained(saved_model)")]


def load():
    return get_model(MODEL), get_tokenizer(MODEL)


def human(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{size} B"
        size /= 1024


def run(objs):
    model, tokenizer = objs
    steps = []

    start = time.perf_counter()
    model.save_pretrained(SAVE_DIR)
    tokenizer.save_pretrained(SAVE_DIR)
    steps.append(("save_pretrained", time.perf_counter() - start))

    files = sorted((p.name, p.stat().st_size) for p in SAVE_DIR.iterdir() if p.is_file())

    start = time.perf_counter()
    model2 = AutoModel.from_pretrained(SAVE_DIR)
    tokenizer2 = AutoTokenizer.from_pretrained(SAVE_DIR)
    steps.append(("from_pretrained(saved_model)", time.perf_counter() - start))

    same = all(torch.equal(a, b) for a, b in zip(model.state_dict().values(), model2.state_dict().values()))
    return {
        "model_class": type(model).__name__,
        "tokenizer_class": type(tokenizer).__name__,
        "params": sum(p.numel() for p in model.parameters()),
        "files": files,
        "steps": steps,
        "reloaded": f"{type(model2).__name__} + {type(tokenizer2).__name__}",
        "same_weights": same,
        "same_vocab": tokenizer.get_vocab() == tokenizer2.get_vocab(),
    }


def render(result):
    info = table("Item", "Value")
    info.add_row("Loaded", f"{result['model_class']} + {result['tokenizer_class']}")
    info.add_row("Parameters", f"{result['params'] / 1e6:.1f} M")
    for name, sec in result["steps"]:
        info.add_row(name, f"{sec:.2f} s")
    info.add_row("Reloaded", result["reloaded"])
    ok = result["same_weights"] and result["same_vocab"]
    info.add_row("Same weights & vocab", Text("✓ yes" if ok else "✗ no", style="bold green" if ok else "bold red"))

    files = table("File in saved_model/", "Size")
    for name, size in result["files"]:
        files.add_row(Text(name, style="bold"), human(size))
    files.add_row(Text("total", style="dim"), human(sum(s for _, s in result["files"])))

    return Columns([files, info], padding=(0, 4))


if __name__ == "__main__":
    run_standalone(sys.modules[__name__])
