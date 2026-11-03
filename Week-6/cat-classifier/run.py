"""Cat breed classifier on top of the pretrained ResNet-50 from the Cog guide."""

import json
import logging
import os
import sys

# Download the weights into ./hub so they are copied into the image at build time.
os.environ["TORCH_HOME"] = "."

import torch
from cog import BaseRunner, Input, Path
from PIL import Image
from torchvision import models

WEIGHTS = models.ResNet50_Weights.IMAGENET1K_V1

# ImageNet class index -> cat kind.
CAT_CLASSES = {
    281: "Tabby cat",
    282: "Tiger cat",
    283: "Persian cat",
    284: "Siamese cat",
    285: "Egyptian cat",
}
# The photo counts as a cat when the five cat classes together reach this.
CAT_THRESHOLD = 0.3
LOG_FILE = "/tmp/predictions.log"


def make_logger():
    """Return a logger that writes to stdout and to LOG_FILE."""
    logger = logging.getLogger("cat-classifier")
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
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = models.resnet50(weights=WEIGHTS).to(self.device)
        self.model.eval()
        self.categories = WEIGHTS.meta["categories"]
        self.logger.info("Model loaded on %s", self.device)

    def run(self, image: Path = Input(description="Photo of a cat (or anything else)")) -> dict:
        """Say whether the photo shows a cat and which kind it is."""
        img = Image.open(image).convert("RGB")
        with torch.no_grad():
            logits = self.model(WEIGHTS.transforms()(img).unsqueeze(0).to(self.device))
        probs = logits[0].softmax(0).cpu()

        cat_probs = {name: probs[index].item() for index, name in CAT_CLASSES.items()}
        cat_total = sum(cat_probs.values())
        is_cat = cat_total >= CAT_THRESHOLD
        best_kind = max(cat_probs, key=cat_probs.get)

        top_probs, top_indices = probs.topk(3)
        result = {
            "is_cat": is_cat,
            # Kind and confidence only make sense when the photo is a cat.
            "cat_kind": best_kind if is_cat else None,
            # Share of the best kind among the five cat classes.
            "cat_confidence": round(cat_probs[best_kind] / cat_total, 4) if is_cat else None,
            "cat_probabilities": {name: round(p, 4) for name, p in cat_probs.items()},
            # A list keeps the ranking (JSON objects may be re-sorted by key).
            "top3_imagenet": [{"label": self.categories[i], "probability": round(p.item(), 4)}
                              for p, i in zip(top_probs, top_indices)],
        }
        self.logger.info("PREDICTION %s", json.dumps(result))
        return result
