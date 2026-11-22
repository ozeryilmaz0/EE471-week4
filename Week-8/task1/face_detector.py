"""Face Detector: find faces, their boxes and 6 key points (eyes, nose, mouth, ears)."""

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import FaceDetector, FaceDetectorOptions, drawing_utils

import common

common.header("FACE DETECTOR", "Model: BlazeFace short range  |  Input: inputs/face-1.png, face-2.png, face-3.png")

options = FaceDetectorOptions(
    base_options=BaseOptions(model_asset_path=common.model("blaze_face_short_range.tflite")),
    min_detection_confidence=0.5)

tiles = []
with FaceDetector.create_from_options(options) as detector:
    for name in ("face-1.png", "face-2.png", "face-3.png"):
        mp_img, rgb = common.load_mp(common.INPUTS / name, min_side=480)
        result = detector.detect(mp_img)
        common.section(name)
        print(f"  Faces found: {len(result.detections)}")
        for det in result.detections:
            box = det.bounding_box
            print(f"  score {det.categories[0].score:.2f}, box x={box.origin_x} y={box.origin_y} "
                  f"w={box.width} h={box.height}, {len(det.keypoints)} key points")
            drawing_utils.draw_detection(rgb, det)
            common.label(rgb, f"face {det.categories[0].score:.2f}", (box.origin_x, max(25, box.origin_y - 10)))
        tiles.append(common.rgb2bgr(rgb))

common.save_and_show(common.montage(tiles), "face_detector.png")
common.done()
