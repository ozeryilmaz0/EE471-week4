"""Hand Landmarker: 21 key points per hand and left/right handedness."""

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (HandLandmarker, HandLandmarkerOptions, HandLandmarksConnections,
                                           drawing_styles, drawing_utils)

import common

common.header("HAND LANDMARKER", "Model: hand_landmarker.task  |  Input: assets/woman_hands.jpg")

options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=common.model("hand_landmarker.task")), num_hands=2)

mp_img, rgb = common.load_mp(common.ASSETS / "woman_hands.jpg")
with HandLandmarker.create_from_options(options) as landmarker:
    result = landmarker.detect(mp_img)

h, w = rgb.shape[:2]
print(f"Hands found: {len(result.hand_landmarks)}")
for hand, lms in zip(result.handedness, result.hand_landmarks):
    tip = lms[8]  # index finger tip
    common.section(f"{hand[0].category_name} hand (score {hand[0].score:.2f})")
    print(f"  21 landmarks, index finger tip at pixel ({tip.x * w:.0f}, {tip.y * h:.0f})")
    drawing_utils.draw_landmarks(rgb, lms, HandLandmarksConnections.HAND_CONNECTIONS,
                                 drawing_styles.get_default_hand_landmarks_style(),
                                 drawing_styles.get_default_hand_connections_style())
    wrist = lms[0]
    common.label(rgb, hand[0].category_name, (int(wrist.x * w) - 40, int(wrist.y * h) + 40), 1.2)

common.save_and_show(common.rgb2bgr(rgb), "hand_landmarker.png")
common.done()
