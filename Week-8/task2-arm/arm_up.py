"""Which arm is up? Classify a photo of a person as "left", "right", "both" or "None".

Usage:
    python arm_up.py <image path> [--perspective subject|viewer] [--annotate out.png] [-v]

The answer (one word) is printed to stdout. Details go to the log (stderr).

Rule: an arm is "up" when its wrist is clearly above its shoulder, i.e. the wrist's
y value is smaller than the shoulder's y value by more than MARGIN x torso length
(image y grows downwards). Landmarks with low visibility are ignored.

Perspective:
    subject (default)  the person's own left/right. This matches MediaPipe's
                       LEFT_*/RIGHT_* landmark names.
    viewer             left/right as seen in the image (mirror of "subject").
"""

import argparse
import logging
import sys
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (PoseLandmark, PoseLandmarker, PoseLandmarkerOptions,
                                           PoseLandmarksConnections, drawing_styles, drawing_utils)

MODEL_PATH = Path(__file__).resolve().parent / "pose_landmarker_heavy.task"
MIN_VISIBILITY = 0.5   # ignore landmarks the model is not sure about
MARGIN = 0.10          # wrist must be this many torso lengths above the shoulder
MIN_SIDE = 600         # small photos are upscaled to at least this size

ARMS = {  # arm name (subject perspective) -> (shoulder, wrist) landmarks
    "left": (PoseLandmark.LEFT_SHOULDER, PoseLandmark.LEFT_WRIST),
    "right": (PoseLandmark.RIGHT_SHOULDER, PoseLandmark.RIGHT_WRIST),
}

log = logging.getLogger("arm_up")


# ---------------------------------------------------------------- model
def create_landmarker(model_path=MODEL_PATH):
    """Load the MediaPipe Pose Landmarker (single image mode, one person)."""
    options = PoseLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(model_path)), num_poses=1)
    return PoseLandmarker.create_from_options(options)


def load_image(path):
    """Read an image as an RGB array; upscale small images so the model sees more detail."""
    bgr = cv2.imread(str(path))
    if bgr is None:
        raise FileNotFoundError(f"cannot read image: {path}")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    short = min(rgb.shape[:2])
    if short < MIN_SIDE:
        f = MIN_SIDE / short
        rgb = cv2.resize(rgb, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
    return rgb


# ---------------------------------------------------------------- rule
def torso_length(lms):
    """Distance between the shoulder centre and the hip centre (normalized units)."""
    sh_y = (lms[PoseLandmark.LEFT_SHOULDER].y + lms[PoseLandmark.RIGHT_SHOULDER].y) / 2
    hip_y = (lms[PoseLandmark.LEFT_HIP].y + lms[PoseLandmark.RIGHT_HIP].y) / 2
    return max(abs(hip_y - sh_y), 0.05)  # lower bound in case the hips are hidden


def arms_up(lms):
    """Return {"left": bool, "right": bool} in the subject's perspective."""
    margin = MARGIN * torso_length(lms)
    result = {}
    for arm, (sh_id, wr_id) in ARMS.items():
        sh, wr = lms[sh_id], lms[wr_id]
        if sh.visibility < MIN_VISIBILITY or wr.visibility < MIN_VISIBILITY:
            log.info("%-5s arm: ignored (visibility shoulder %.2f, wrist %.2f)", arm, sh.visibility, wr.visibility)
            result[arm] = False
            continue
        lift = sh.y - wr.y  # > 0 means the wrist is above the shoulder
        result[arm] = lift > margin
        log.info("%-5s arm: shoulder y=%.3f wrist y=%.3f lift=%+.3f margin=%.3f -> %s",
                 arm, sh.y, wr.y, lift, margin, "UP" if result[arm] else "down")
    return result


def to_label(up, perspective="subject"):
    """Turn {"left": bool, "right": bool} into "left", "right", "both" or "None"."""
    if perspective == "viewer":  # the person's left arm is on the right side of the image
        up = {"left": up["right"], "right": up["left"]}
    if up["left"] and up["right"]:
        return "both"
    if up["left"]:
        return "left"
    if up["right"]:
        return "right"
    return "None"


# ---------------------------------------------------------------- main API
def classify(landmarker, image_path, perspective="subject", annotate=None):
    """Classify one image. Returns the label as a string."""
    if perspective not in ("subject", "viewer"):
        raise ValueError("perspective must be 'subject' or 'viewer'")
    rgb = load_image(image_path)
    result = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    if not result.pose_landmarks:
        log.info("no person found")
        label = "None"
    else:
        lms = result.pose_landmarks[0]
        label = to_label(arms_up(lms), perspective)
    log.info("result (%s perspective): %s", perspective, label)
    if annotate:
        save_annotated(rgb, result, label, perspective, annotate)
    return label


def save_annotated(rgb, result, label, perspective, out_path):
    """Draw the skeleton, shoulder/wrist markers and the answer, then save a PNG."""
    img = rgb.copy()
    if result.pose_landmarks:
        lms = result.pose_landmarks[0]
        drawing_utils.draw_landmarks(img, lms, PoseLandmarksConnections.POSE_LANDMARKS,
                                     drawing_styles.get_default_pose_landmarks_style())
        h, w = img.shape[:2]
        for arm, (sh_id, wr_id) in ARMS.items():
            color = (255, 80, 0) if arm == "left" else (0, 140, 255)  # RGB: orange = left, blue = right
            for i in (sh_id, wr_id):
                cv2.circle(img, (int(lms[i].x * w), int(lms[i].y * h)), 10, color, 3)
            wr = lms[wr_id]
            cv2.putText(img, f"{arm.upper()} wrist", (int(wr.x * w) - 60, int(wr.y * h) - 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)
    text = f"arm up: {label}  ({perspective})"
    cv2.rectangle(img, (0, 0), (img.shape[1], 44), (30, 30, 30), -1)
    cv2.putText(img, text, (10, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    log.info("annotated image saved: %s", out_path)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Which arm is up? Prints left, right, both or None.")
    parser.add_argument("image", help="path to the input image")
    parser.add_argument("--perspective", choices=["subject", "viewer"], default="subject",
                        help="subject = the person's own left/right (default); viewer = as seen in the image")
    parser.add_argument("--annotate", metavar="PNG", help="save an image with the landmarks drawn")
    parser.add_argument("-v", "--verbose", action="store_true", help="show the measurements on stderr")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="[arm_up] %(message)s", stream=sys.stderr)
    with create_landmarker() as landmarker:
        print(classify(landmarker, args.image, args.perspective, args.annotate))


if __name__ == "__main__":
    main()
