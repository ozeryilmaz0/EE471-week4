"""Save 2 test images per class as 128x128 PNGs in sample_images/.

File names hold the true class, e.g. 03_cat_1.png.

Usage: python make_samples.py
"""

from torchvision import datasets

from common import DATA_DIR, ROOT
from model import CLASSES

PER_CLASS = 2
SIZE = 128


def main():
    test_data = datasets.CIFAR10(root=DATA_DIR, train=False, download=True)
    out_dir = ROOT / "sample_images"
    out_dir.mkdir(exist_ok=True)
    counts = [0] * len(CLASSES)
    for img, label in test_data:  # PIL images (no transform)
        if counts[label] >= PER_CLASS:
            continue
        counts[label] += 1
        path = out_dir / f"{label:02d}_{CLASSES[label]}_{counts[label]}.png"
        img.resize((SIZE, SIZE), resample=0).save(path)  # nearest: keep the original pixels
        if min(counts) == PER_CLASS:
            break
    print(f"Saved {sum(counts)} images to {out_dir}")


if __name__ == "__main__":
    main()
