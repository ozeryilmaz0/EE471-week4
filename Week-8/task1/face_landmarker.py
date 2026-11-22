"""Face Landmarker: 478 3D face points, 52 expression scores (blendshapes) and the head pose matrix."""

import math

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (FaceLandmarker, FaceLandmarkerOptions, FaceLandmarksConnections,
                                           drawing_styles, drawing_utils)

import common

common.header("FACE LANDMARKER", "Model: face_landmarker.task  |  Input: inputs/face-1.png, face-2.png, face-3.png")

options = FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=common.model("face_landmarker.task")),
    output_face_blendshapes=True,
    output_facial_transformation_matrixes=True,
    num_faces=1)

tiles = []
with FaceLandmarker.create_from_options(options) as landmarker:
    for name in ("face-1.png", "face-2.png", "face-3.png"):
        mp_img, rgb = common.load_mp(common.INPUTS / name, min_side=480)
        result = landmarker.detect(mp_img)
        common.section(name)
        if not result.face_landmarks:
            print("  No face found")
            continue
        lms = result.face_landmarks[0]
        drawing_utils.draw_landmarks(rgb, lms, FaceLandmarksConnections.FACE_LANDMARKS_TESSELATION, None,
                                     drawing_styles.get_default_face_mesh_tesselation_style())
        drawing_utils.draw_landmarks(rgb, lms, FaceLandmarksConnections.FACE_LANDMARKS_CONTOURS, None,
                                     drawing_styles.get_default_face_mesh_contours_style())
        top = sorted(result.face_blendshapes[0], key=lambda c: -c.score)[:3]
        m = result.facial_transformation_matrixes[0]
        yaw = math.degrees(math.atan2(-m[2][0], math.hypot(m[2][1], m[2][2])))
        print(f"  {len(lms)} landmarks")
        print("  Top blendshapes: " + ", ".join(f"{c.category_name} {c.score:.2f}" for c in top))
        print(f"  Head yaw from the transformation matrix: {yaw:+.1f} deg")
        common.label(rgb, f"{len(lms)} points, yaw {yaw:+.0f} deg", (10, 30))
        tiles.append(common.rgb2bgr(rgb))

common.save_and_show(common.montage(tiles), "face_landmarker.png")
common.done()
