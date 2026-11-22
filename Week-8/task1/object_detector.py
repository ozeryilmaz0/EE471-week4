"""Object Detector: find objects, their class (80 COCO classes) and bounding boxes."""

import cv2
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import ObjectDetector, ObjectDetectorOptions

import common

common.header("OBJECT DETECTOR", "Model: EfficientDet-Lite0  |  Input: assets/cat_and_dog.jpg, inputs/pose-2.jpg")

options = ObjectDetectorOptions(
    base_options=BaseOptions(model_asset_path=common.model("efficientdet_lite0_float32.tflite")),
    max_results=5, score_threshold=0.4)

tiles = []
with ObjectDetector.create_from_options(options) as detector:
    for path in (common.ASSETS / "cat_and_dog.jpg", common.INPUTS / "pose-2.jpg"):
        mp_img, rgb = common.load_mp(path, min_side=416)
        result = detector.detect(mp_img)
        img = common.rgb2bgr(rgb)
        common.section(path.name)
        for det in result.detections:
            c, b = det.categories[0], det.bounding_box
            print(f"  {c.category_name:<8} score {c.score:.2f}  box x={b.origin_x} y={b.origin_y} "
                  f"w={b.width} h={b.height}")
            cv2.rectangle(img, (b.origin_x, b.origin_y), (b.origin_x + b.width, b.origin_y + b.height),
                          (0, 200, 255), 3)
            common.label(img, f"{c.category_name} {c.score:.2f}", (b.origin_x + 4, b.origin_y + 28), 0.8)
        tiles.append(img)

common.save_and_show(common.montage(tiles), "object_detector.png")
common.done()
