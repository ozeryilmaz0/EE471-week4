"""Gesture Recognizer: recognise hand gestures (thumb up, victory, open palm, ...) and draw the hand."""

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (GestureRecognizer, GestureRecognizerOptions, HandLandmarksConnections,
                                           drawing_styles, drawing_utils)

import common

common.header("GESTURE RECOGNIZER", "Model: gesture_recognizer.task  |  Input: assets/thumbs_up.jpg, victory.jpg")

options = GestureRecognizerOptions(
    base_options=BaseOptions(model_asset_path=common.model("gesture_recognizer.task")), num_hands=2)

tiles = []
with GestureRecognizer.create_from_options(options) as recognizer:
    for name in ("thumbs_up.jpg", "victory.jpg"):
        mp_img, rgb = common.load_mp(common.ASSETS / name)
        result = recognizer.recognize(mp_img)
        common.section(name)
        for gestures, hand, lms in zip(result.gestures, result.handedness, result.hand_landmarks):
            g = gestures[0]
            print(f"  {hand[0].category_name} hand: {g.category_name} (score {g.score:.2f})")
            drawing_utils.draw_landmarks(rgb, lms, HandLandmarksConnections.HAND_CONNECTIONS,
                                         drawing_styles.get_default_hand_landmarks_style(),
                                         drawing_styles.get_default_hand_connections_style())
            common.label(rgb, f"{g.category_name} {g.score:.2f}", (10, 30))
        if not result.gestures:
            print("  No hand found")
        tiles.append(common.rgb2bgr(rgb))

common.save_and_show(common.montage(tiles), "gesture_recognizer.png")
common.done()
