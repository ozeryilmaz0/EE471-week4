"""Cog runner for the Fashion-MNIST garment classifier.

The same file is used by cog-baseline/ and cog-optimized/. model_info.json
(written by the training script) says which weights and settings to load.
"""

import json
import logging
import sys
from pathlib import Path as FilePath

import torch
from cog import BaseRunner, Input, Path
from PIL import Image, ImageOps, ImageStat
from torchvision.transforms import ToTensor

from model import CLASSES, build_model

HERE = FilePath(__file__).resolve().parent
LOG_FILE = "/tmp/predictions.log"


def make_logger():
    """Return a logger that writes to stdout and to LOG_FILE."""
    logger = logging.getLogger("garment-classifier")
    if not logger.handlers:  # setup() may run more than once in a process
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter("%(message)s")
        for handler in (logging.StreamHandler(sys.stdout), logging.FileHandler(LOG_FILE)):
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.propagate = False
    return logger


def background_mean(img):
    """Mean brightness of a frame along the image border (where the background is)."""
    w, h = img.size
    b = max(1, min(w, h) // 20)
    strips = [img.crop(box) for box in ((0, 0, w, b), (0, h - b, w, h),
                                        (0, 0, b, h), (w - b, 0, w, h))]
    total = sum(s.width * s.height for s in strips)
    return sum(ImageStat.Stat(s).mean[0] * s.width * s.height for s in strips) / total


def preprocess(img):
    """Turn any photo into a 1x1x28x28 tensor that looks like Fashion-MNIST.

    Fashion-MNIST shows light garments on a black background, so a photo with a
    light background (border mean > 127) is inverted first. The border is used
    instead of the whole image so that a big, bright garment on black is not inverted.
    """
    img = img.convert("L")
    if background_mean(img) > 127:
        img = ImageOps.invert(img)
    # Keep the aspect ratio and pad with black. BOX (area average) is anti-aliased for
    # photos and gives back the exact pixels of the 5x upscaled sample images.
    img = ImageOps.pad(img, (28, 28), method=Image.Resampling.BOX, color=0)
    return ToTensor()(img).unsqueeze(0)


class Runner(BaseRunner):
    def setup(self):
        """Load the model once so every prediction can reuse it."""
        self.logger = make_logger()
        self.info = json.loads((HERE / "model_info.json").read_text())
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = build_model(self.info["architecture"], **self.info["kwargs"])
        state = torch.load(HERE / self.info["weights"], map_location=self.device, weights_only=True)
        self.model.load_state_dict(state)
        self.model.to(self.device).eval()
        self.logger.info("Model loaded: %s (%s)", self.info["model_name"], self.device)

    def run(self, image: Path = Input(description="Photo of a garment")) -> dict:
        """Classify the garment and return the top-3 classes."""
        x = preprocess(Image.open(image)).to(self.device)
        with torch.no_grad():
            probs = self.model(x)[0].softmax(0).cpu()
        top_probs, top_indices = probs.topk(3)
        result = {
            "predicted_class": CLASSES[int(top_indices[0])],
            "confidence": round(top_probs[0].item(), 4),
            "top3": {CLASSES[int(i)]: round(p.item(), 4) for p, i in zip(top_probs, top_indices)},
            "model_name": self.info["model_name"],
            "model_test_accuracy": self.info["test_accuracy"],
        }
        self.logger.info("PREDICTION %s", json.dumps(result))
        return result
