"""Interactive Segmenter: the user clicks on an object and the model cuts out that object.

The click point is fixed in the code so the demo always runs the same way.

Two MediaPipe APIs are available in Python:
  * default      InteractiveSegmenterLegacy + magic_touch.tflite (a keypoint click), ~1 s
  * --new-api    InteractiveSegmenter + interactive_segmentation.task (brush strokes);
                 on CPU one segment() call takes about a minute on this laptop,
                 and the GPU path is disabled in the pip package.
"""

import sys

import cv2
import numpy as np
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.components.containers.keypoint import NormalizedKeypoint
from mediapipe.tasks.python.vision import (InteractiveSegmenter, InteractiveSegmenterBrushMode,
                                           InteractiveSegmenterLegacy, InteractiveSegmenterLegacyOptions,
                                           InteractiveSegmenterOptions, InteractiveSegmenterStroke,
                                           InteractiveSegmenterStrokePoint)
from mediapipe.tasks.python.vision.interactive_segmenter_legacy import RegionOfInterest

import common

CLICK = (0.70, 0.55)  # normalized (x, y): a point on the dog's body in cat_and_dog.jpg
NEW_API = "--new-api" in sys.argv

model_name = "interactive_segmentation.task" if NEW_API else "magic_touch.tflite"
common.header("INTERACTIVE SEGMENTER", f"Model: MagicTouch ({model_name})  |  Input: assets/cat_and_dog.jpg + one click")

mp_img, rgb = common.load_mp(common.ASSETS / "cat_and_dog.jpg")
h, w = rgb.shape[:2]
print(f"Click point: x={CLICK[0]:.2f}, y={CLICK[1]:.2f} (pixel {int(CLICK[0] * w)}, {int(CLICK[1] * h)})")


def segment_legacy():
    """One click = a keypoint region of interest."""
    options = InteractiveSegmenterLegacyOptions(
        base_options=BaseOptions(model_asset_path=common.model("magic_touch.tflite")),
        output_category_mask=True)
    roi = RegionOfInterest(format=RegionOfInterest.Format.KEYPOINT,
                           keypoint=NormalizedKeypoint(x=CLICK[0], y=CLICK[1]))
    with InteractiveSegmenterLegacy.create_from_options(options) as segmenter:
        result = segmenter.segment(mp_img, roi)
    # In the category mask the selected object has the value 0 and the rest is non-zero.
    return np.squeeze(result.category_mask.numpy_view()) == 0


def segment_new():
    """One click = a positive brush stroke with a single point."""
    stroke = InteractiveSegmenterStroke(
        brush_mode=InteractiveSegmenterBrushMode.POSITIVE,  # "this is the object I want"
        points=[InteractiveSegmenterStrokePoint(x=CLICK[0], y=CLICK[1])],
        is_completed=True)
    options = InteractiveSegmenterOptions(
        base_options=BaseOptions(model_asset_path=common.model("interactive_segmentation.task")))
    print("New stroke API on CPU: this takes about one minute ...")
    with InteractiveSegmenter.create_from_options(options) as segmenter:
        segmenter.set_image(mp_img)
        mask = np.squeeze(segmenter.segment([stroke]).numpy_view()).astype(np.float32)
    return mask > (127 if mask.max() > 1 else 0.5)


selected = segment_new() if NEW_API else segment_legacy()
ys, xs = np.nonzero(selected)
common.section("Result")
print(f"  Selected object covers {selected.mean() * 100:.1f} % of the image")
if len(xs):
    print(f"  Bounding box: x {xs.min()}-{xs.max()}, y {ys.min()}-{ys.max()}  (the dog)")

img = common.rgb2bgr(rgb)
gray = cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR) // 2
cut = np.where(selected[..., None], img, gray)
contours, _ = cv2.findContours(selected.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
cv2.drawContours(cut, contours, -1, (0, 255, 0), 2)
px = (int(CLICK[0] * w), int(CLICK[1] * h))
for im in (img, cut):
    cv2.circle(im, px, 9, (0, 0, 255), -1)
    cv2.circle(im, px, 11, (255, 255, 255), 2)
common.label(img, "input + click", (10, 35), 0.9)
common.label(cut, "selected object", (10, 35), 0.9, (0, 255, 0))
common.save_and_show(common.montage([img, cut]), "interactive_segmenter.png")
common.done()
