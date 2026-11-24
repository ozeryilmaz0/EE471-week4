"""Task 1.9 - Image classification with pipeline() (ViT, ImageNet-1k labels)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rich.text import Text  # noqa: E402
from shared import IMAGE_PATH, get_pipeline, image_preview, run_standalone, score_bar, table  # noqa: E402

TITLE = "IMAGE CLASSIFICATION"
MODEL = "google/vit-base-patch16-224"
TOP_K = 3


def inputs():
    return [("Image", f"assets/{IMAGE_PATH.name}"), ("", image_preview(IMAGE_PATH)), ("top_k", str(TOP_K))]


def load():
    return get_pipeline("image-classification", MODEL)


def run(classifier):
    return classifier(str(IMAGE_PATH), top_k=TOP_K)


def render(result):
    t = table("Rank", "Label", "Score")
    for rank, r in enumerate(result, 1):
        t.add_row(str(rank), Text(r["label"], style="bold green" if rank == 1 else ""), score_bar(r["score"]))
    return t


if __name__ == "__main__":
    run_standalone(sys.modules[__name__])
