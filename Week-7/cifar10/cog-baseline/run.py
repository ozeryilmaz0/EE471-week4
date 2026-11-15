"""Cog runner for the CIFAR-10 classifier.

The same file is used by cog-baseline/ and cog-optimized/. model_info.json
(written by the training script) says which architecture and weights to load.
"""

import json
import logging
import sys
from pathlib import Path as FilePath

import torch
import torchvision.transforms as transforms
from cog import BaseRunner, Input, Path
from PIL import Image

from model import CLASSES, build_model

HERE = FilePath(__file__).resolve().parent
LOG_FILE = "/tmp/predictions.log"

# Same normalization as the "Training a Classifier" tutorial.
TRANSFORM = transforms.Compose([
    # BOX = area average: anti-aliased for photos, and exact for 4x upscaled samples.
    transforms.Resize((32, 32), interpolation=transforms.InterpolationMode.BOX),
    transforms.ToTensor(),
    transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
])


def make_logger():
    """Return a logger that writes to stdout and to LOG_FILE."""
    logger = logging.getLogger("cifar-classifier")
    if not logger.handlers:  # setup() may run more than once in a process
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter("%(message)s")
        for handler in (logging.StreamHandler(sys.stdout), logging.FileHandler(LOG_FILE)):
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.propagate = False
    return logger


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

    def run(self, image: Path = Input(description="Photo of a plane, car, bird, cat, deer, "
                                                  "dog, frog, horse, ship or truck")) -> dict:
        """Classify the photo into one of the 10 CIFAR-10 classes."""
        x = TRANSFORM(Image.open(image).convert("RGB")).unsqueeze(0).to(self.device)
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
