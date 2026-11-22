"""Image Classifier: name the main object in a photo (1000 ImageNet classes)."""

import cv2
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import ImageClassifier, ImageClassifierOptions

import common

common.header("IMAGE CLASSIFIER", "Model: EfficientNet-Lite0  |  Input: assets/burger.jpg, cat.jpg")

options = ImageClassifierOptions(
    base_options=BaseOptions(model_asset_path=common.model("efficientnet_lite0_float32.tflite")), max_results=3)

tiles = []
with ImageClassifier.create_from_options(options) as classifier:
    for name in ("burger.jpg", "cat.jpg"):
        mp_img, rgb = common.load_mp(common.ASSETS / name)
        cats = classifier.classify(mp_img).classifications[0].categories
        common.section(name)
        img = common.rgb2bgr(rgb)
        for i, c in enumerate(cats):
            print(f"  {i + 1}. {c.category_name:<20} {c.score:.2f}")
            common.label(img, f"{i + 1}. {c.category_name} {c.score:.2f}", (10, 35 + 38 * i), 0.9,
                         (0, 255, 0) if i == 0 else (255, 255, 255))
        tiles.append(img)

common.save_and_show(common.montage(tiles), "image_classifier.png")
common.done()
