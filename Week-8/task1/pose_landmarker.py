"""Pose Landmarker: 33 body key points (with visibility) for each person in the image."""

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (PoseLandmark, PoseLandmarker, PoseLandmarkerOptions,
                                           PoseLandmarksConnections, drawing_styles, drawing_utils)

import common

common.header("POSE LANDMARKER", "Model: pose_landmarker_heavy.task  |  Input: assets/pose.jpg, inputs/pose-1..3.jpg")

options = PoseLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=common.model("pose_landmarker_heavy.task")), num_poses=1)

files = [common.ASSETS / "pose.jpg"] + [common.INPUTS / f"pose-{i}.jpg" for i in (1, 2, 3)]
tiles = []
with PoseLandmarker.create_from_options(options) as landmarker:
    for path in files:
        mp_img, rgb = common.load_mp(path, min_side=600)
        result = landmarker.detect(mp_img)
        common.section(path.name)
        if not result.pose_landmarks:
            print("  No person found")
            continue
        lms = result.pose_landmarks[0]
        print(f"  {len(lms)} landmarks (x, y normalized to 0..1, y grows downwards)")
        for p in (PoseLandmark.NOSE, PoseLandmark.LEFT_WRIST, PoseLandmark.RIGHT_WRIST):
            lm = lms[p]
            print(f"  {p.name:<12} x={lm.x:.2f} y={lm.y:.2f} visibility={lm.visibility:.2f}")
        drawing_utils.draw_landmarks(rgb, lms, PoseLandmarksConnections.POSE_LANDMARKS,
                                     drawing_styles.get_default_pose_landmarks_style())
        common.label(rgb, path.name, (10, 35), 1.0)
        tiles.append(common.rgb2bgr(rgb))

common.save_and_show(common.montage(tiles, 520), "pose_landmarker.png")
common.done()
