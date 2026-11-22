"""Text Classifier: positive / negative sentiment with a MobileBERT model trained on movie reviews."""

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.text import TextClassifier, TextClassifierOptions

import common

common.header("TEXT CLASSIFIER", "Model: MobileBERT (SST-2 sentiment)  |  Input: assets/text_classifier.txt")

reviews = [
    common.read_text("text_classifier.txt"),
    "The film was boring and far too long. I almost fell asleep.",
]
options = TextClassifierOptions(base_options=BaseOptions(model_asset_path=common.model("bert_classifier.tflite")))

with TextClassifier.create_from_options(options) as classifier:
    for text in reviews:
        cats = classifier.classify(text).classifications[0].categories
        best = max(cats, key=lambda c: c.score)
        common.section(f"\"{text}\"")
        print("  Scores: " + ", ".join(f"{c.category_name} {c.score:.3f}" for c in cats))
        print(f"  Result: {best.category_name.upper()}")
common.done()
