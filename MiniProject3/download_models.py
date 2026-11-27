"""Pre-download every model used by DreamCanvas AI into the local Hugging Face cache.

Only the files that are actually needed at runtime are fetched:
  * stabilityai/sd-turbo           -> fp16 diffusers weights only (~2.6 GB, not the 5 GB single file)
  * HuggingFaceTB/SmolLM2-360M-Instruct -> safetensors + tokenizer (~0.7 GB)
  * openai/whisper-small           -> safetensors + tokenizer/processor (~1 GB)

Files that are already cached are skipped, so the script can be re-run safely.

Usage (from the repo root):
    venv\\Scripts\\python.exe MiniProject3\\download_models.py
"""

from __future__ import annotations

import os
import sys
import time

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
from huggingface_hub import snapshot_download  # noqa: E402

from config import CHAT_MODEL, IMAGE_MODEL, STT_MODEL  # noqa: E402

DOWNLOADS: list[tuple[str, list[str]]] = [
    (
        IMAGE_MODEL,
        [
            "model_index.json",
            "scheduler/*",
            "tokenizer/*",
            "text_encoder/config.json",
            "text_encoder/model.fp16.safetensors",
            "unet/config.json",
            "unet/diffusion_pytorch_model.fp16.safetensors",
            "vae/config.json",
            "vae/diffusion_pytorch_model.fp16.safetensors",
        ],
    ),
    (
        CHAT_MODEL,
        ["*.json", "*.txt", "model.safetensors"],
    ),
    (
        STT_MODEL,
        ["*.json", "*.txt", "model.safetensors"],
    ),
]


def main() -> int:
    for repo_id, patterns in DOWNLOADS:
        start = time.perf_counter()
        print(f"[download] {repo_id} ...", flush=True)
        try:
            path = snapshot_download(repo_id, allow_patterns=patterns)
        except Exception as exc:  # gated repo, no network, ...
            print(f"[download] FAILED {repo_id}: {exc}", file=sys.stderr, flush=True)
            return 1
        print(f"[download] done {repo_id} in {time.perf_counter() - start:.1f}s -> {path}", flush=True)
    print("[download] all models are ready", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
