"""Pre-download every Hugging Face model used in Week 9 into the local HF cache.

Only the files that PyTorch needs are fetched (config, tokenizer files and the
safetensors weights). TensorFlow, Flax, ONNX and duplicate fp32 shards are skipped,
which saves several gigabytes (mostly for openai/whisper-large-v3).

Files that are already in the cache are not downloaded again, so the script can be
run more than once.

Usage (from the repo root):
    venv\\Scripts\\python.exe Week-9\\download_models.py
"""

from __future__ import annotations

import os
import sys
import time
import urllib.request
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
from huggingface_hub import HfApi, hf_hub_download  # noqa: E402

ASSETS = Path(__file__).resolve().parent / "assets"
# Sample image from the widget examples of google/vit-base-patch16-224.
# (assets/speech.flac is created with make_speech_sample.py and is committed.)
IMAGE_URL = "https://huggingface.co/datasets/mishig/sample_images/resolve/main/tiger.jpg"

MODELS: list[str] = [
    "distilbert-base-uncased-finetuned-sst-2-english",  # sentiment analysis
    "facebook/bart-large-mnli",                         # zero-shot classification
    "gpt2",                                             # text generation
    "distilroberta-base",                               # fill-mask
    "dbmdz/bert-large-cased-finetuned-conll03-english", # named entity recognition
    "distilbert-base-cased-distilled-squad",            # question answering
    "sshleifer/distilbart-cnn-12-6",                    # summarization
    "Helsinki-NLP/opus-mt-fr-en",                       # translation
    "google/vit-base-patch16-224",                      # image classification
    "openai/whisper-large-v3",                          # speech recognition
    "bert-base-cased",                                  # Task 4 (chapter 2)
]

# Small text files that pipelines and tokenizers may need.
SUPPORT_SUFFIXES = (".json", ".txt", ".model", ".spm")
SKIP_WORDS = ("onnx", "tf_model", "flax", "msgpack", "rust_model", "coreml", "openvino", ".h5", "fp32")


def pick_files(files: list[str]) -> list[str]:
    """Return the files of one repo that are needed to run it with PyTorch."""
    top_level = [f for f in files if "/" not in f]  # sub folders hold ONNX/CoreML exports
    usable = [f for f in top_level if not any(w in f.lower() for w in SKIP_WORDS)]
    weights = [f for f in usable if f.endswith(".safetensors")]
    if not weights:  # old repos without safetensors
        weights = [f for f in usable if f == "pytorch_model.bin"]
    support = [f for f in usable if f.endswith(SUPPORT_SUFFIXES) or f.startswith(("vocab", "merges"))]
    return sorted(set(weights + support))


def main() -> int:
    api = HfApi()
    failed: list[str] = []
    for i, repo in enumerate(MODELS, 1):
        start = time.time()
        try:
            files = pick_files(api.list_repo_files(repo))
            size = 0
            for name in files:
                path = hf_hub_download(repo, name)
                size += os.path.getsize(path)
            print(f"[{i:2}/{len(MODELS)}] OK   {repo:52} {len(files):2} files "
                  f"{size / 1e6:8.1f} MB  {time.time() - start:6.1f}s", flush=True)
        except Exception as exc:  # keep going, report at the end
            failed.append(repo)
            print(f"[{i:2}/{len(MODELS)}] FAIL {repo}: {exc}", flush=True)

    image = ASSETS / "tiger.jpg"
    if not image.exists():
        ASSETS.mkdir(exist_ok=True)
        urllib.request.urlretrieve(IMAGE_URL, image)
        print(f"Downloaded sample image -> {image.name}")

    if failed:
        print("Failed:", ", ".join(failed))
        return 1
    print("All models are in the Hugging Face cache.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
