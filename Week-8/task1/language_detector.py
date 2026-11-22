"""Language Detector: find the language of a sentence (110 languages)."""

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.text import LanguageDetector, LanguageDetectorOptions

import common

common.header("LANGUAGE DETECTOR", "Model: language_detector.tflite  |  Input: assets/language_detector.txt")

sentences = common.read_text("language_detector.txt").splitlines()
options = LanguageDetectorOptions(
    base_options=BaseOptions(model_asset_path=common.model("language_detector.tflite")), max_results=2)

with LanguageDetector.create_from_options(options) as detector:
    for s in sentences:
        result = detector.detect(s)
        preds = ", ".join(f"{p.language_code} ({p.probability:.2f})" for p in result.detections)
        common.section(f"\"{s}\"")
        print(f"  Detected: {preds}")
common.done()
