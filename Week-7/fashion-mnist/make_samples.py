"""Save 2 test images per class as 140x140 PNGs in sample_images/.

File names hold the true class, e.g. 03_dress_1.png.

Usage: python make_samples.py
"""

import re

from torchvision import datasets

from common import DATA_DIR, ROOT
from model import CLASSES

PER_CLASS = 2
SIZE = 140


def slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def main():
    test_data = datasets.FashionMNIST(root=DATA_DIR, train=False, download=True)
    out_dir = ROOT / "sample_images"
    out_dir.mkdir(exist_ok=True)
    counts = [0] * len(CLASSES)
    for img, label in test_data:  # PIL images (no transform)
        if counts[label] >= PER_CLASS:
            continue
        counts[label] += 1
        path = out_dir / f"{label:02d}_{slug(CLASSES[label])}_{counts[label]}.png"
        img.resize((SIZE, SIZE), resample=0).save(path)  # nearest: keep the original pixels
        if min(counts) == PER_CLASS:
            break
    print(f"Saved {sum(counts)} images to {out_dir}")


if __name__ == "__main__":
    main()
