"""Image Segmenter: label every pixel of the image with a class (DeepLab-V3, 21 PASCAL VOC classes)."""

import cv2
import numpy as np
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import ImageSegmenter, ImageSegmenterOptions

import common

common.header("IMAGE SEGMENTER",
              "Model: DeepLab-V3  |  Input: assets/segmentation_input_rotation0.jpg, inputs/pose-3.jpg")

# Class order of the DeepLab-V3 PASCAL VOC model.
LABELS = ["background", "aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair",
          "cow", "dining table", "dog", "horse", "motorbike", "person", "potted plant", "sheep", "sofa",
          "train", "tv"]
rng = np.random.default_rng(3)
COLORS = rng.integers(60, 255, size=(len(LABELS), 3), dtype=np.uint8)
COLORS[0] = 0

options = ImageSegmenterOptions(
    base_options=BaseOptions(model_asset_path=common.model("deeplab_v3.tflite")),
    output_category_mask=True, output_confidence_masks=False)

tiles = []
with ImageSegmenter.create_from_options(options) as segmenter:
    for path in (common.ASSETS / "segmentation_input_rotation0.jpg", common.INPUTS / "pose-3.jpg"):
        mp_img, rgb = common.load_mp(path, min_side=400)
        mask = np.squeeze(segmenter.segment(mp_img).category_mask.numpy_view()).astype(int)
        common.section(f"{path.name}: share of pixels per class")
        found = [int(c) for c in np.unique(mask)]
        for cls in found:
            print(f"  {LABELS[cls]:<12} {(mask == cls).mean() * 100:5.1f} %")

        img = common.rgb2bgr(rgb)
        color_mask = COLORS[mask][:, :, ::-1]
        overlay = np.where(mask[..., None] > 0, cv2.addWeighted(img, 0.4, color_mask, 0.6, 0), img)
        for i, cls in enumerate(c for c in found if c > 0):
            common.label(overlay, LABELS[cls], (10, 35 + 38 * i), 0.9, tuple(int(v) for v in COLORS[cls][::-1]))
        tiles += [img, overlay]

common.save_and_show(common.montage(tiles, 400), "image_segmenter.png")
common.done()
