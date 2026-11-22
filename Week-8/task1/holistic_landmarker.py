"""Holistic Landmarker: body, face and both hands in one model (33 + 478 + 2 x 21 points)."""

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (FaceLandmarksConnections, HandLandmarksConnections,
                                           HolisticLandmarker, HolisticLandmarkerOptions,
                                           PoseLandmarksConnections, drawing_styles, drawing_utils)

import common

common.header("HOLISTIC LANDMARKER", "Model: holistic_landmarker.task  |  Input: inputs/pose-3.jpg")

options = HolisticLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=common.model("holistic_landmarker.task")))

mp_img, rgb = common.load_mp(common.INPUTS / "pose-3.jpg", min_side=800)
with HolisticLandmarker.create_from_options(options) as landmarker:
    r = landmarker.detect(mp_img)

parts = {
    "pose": r.pose_landmarks,
    "face": r.face_landmarks,
    "left hand": r.left_hand_landmarks,
    "right hand": r.right_hand_landmarks,
}
common.section("Landmarks found in one pass")
for name, lms in parts.items():
    print(f"  {name:<10}: {len(lms) if lms else 0} points")

if r.face_landmarks:
    drawing_utils.draw_landmarks(rgb, r.face_landmarks, FaceLandmarksConnections.FACE_LANDMARKS_CONTOURS, None,
                                 drawing_styles.get_default_face_mesh_contours_style())
if r.pose_landmarks:
    drawing_utils.draw_landmarks(rgb, r.pose_landmarks, PoseLandmarksConnections.POSE_LANDMARKS,
                                 drawing_styles.get_default_pose_landmarks_style())
for lms in (r.left_hand_landmarks, r.right_hand_landmarks):
    if lms:
        drawing_utils.draw_landmarks(rgb, lms, HandLandmarksConnections.HAND_CONNECTIONS,
                                     drawing_styles.get_default_hand_landmarks_style(),
                                     drawing_styles.get_default_hand_connections_style())
common.label(rgb, "pose + face + hands", (10, 35), 1.0)
common.save_and_show(common.rgb2bgr(rgb), "holistic_landmarker.png")
common.done()
