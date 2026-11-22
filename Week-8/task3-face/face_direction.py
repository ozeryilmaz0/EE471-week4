"""Where is the face looking? Classify a face photo as "left", "right" or "straight".

Usage:
    python face_direction.py <image path> [--perspective subject|viewer] [--method auto|matrix|nose]
                             [--annotate out.png] [-v]

The answer (one word) is printed to stdout. The yaw angle and other details go to the log (stderr).

How it works:
  1. MediaPipe Face Landmarker finds 478 face points and a 4x4 facial transformation
     matrix (the head pose of the canonical face model).
  2. The yaw angle (turn around the vertical axis) is read from the rotation part of
     the matrix: yaw = atan2(R[0][2], R[2][2]).
     yaw > 0: the nose points to the right side of the image.
  3. Fallback (if no matrix is returned, or with --method nose): the nose tip position
     between the two outer eye corners. ratio = 0.5 for a frontal face; the rough
     estimate yaw = (ratio - 0.5) * 90 degrees is used.
  4. |yaw| < 10 degrees -> "straight", otherwise left/right from the sign.

Perspective:
    subject (default)  the person's own left/right. A face that turns to its own left
                       has its nose on the right side of the image (yaw > 0) -> "left".
    viewer             left/right as seen in the image (yaw > 0 -> "right").
"""

import argparse
import logging
import math
import sys
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (FaceLandmarker, FaceLandmarkerOptions, FaceLandmarksConnections,
                                           drawing_styles, drawing_utils)

MODEL_PATH = Path(__file__).resolve().parent / "face_landmarker.task"
STRAIGHT_DEG = 10.0   # |yaw| below this is "straight"
MIN_SIDE = 480        # small photos are upscaled to at least this size

NOSE_TIP = 1
EYE_OUTER_SUBJECT_RIGHT = 33    # on the left side of the image for a frontal face
EYE_OUTER_SUBJECT_LEFT = 263    # on the right side of the image

log = logging.getLogger("face_direction")


# ---------------------------------------------------------------- model
def create_landmarker(model_path=MODEL_PATH):
    """Load the MediaPipe Face Landmarker with head-pose matrices turned on."""
    options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path)),
        output_facial_transformation_matrixes=True,
        num_faces=1)
    return FaceLandmarker.create_from_options(options)


def load_image(path):
    """Read an image as an RGB array; upscale small images."""
    bgr = cv2.imread(str(path))
    if bgr is None:
        raise FileNotFoundError(f"cannot read image: {path}")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    short = min(rgb.shape[:2])
    if short < MIN_SIDE:
        f = MIN_SIDE / short
        rgb = cv2.resize(rgb, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
    return rgb


# ---------------------------------------------------------------- yaw
def yaw_from_matrix(matrix):
    """Yaw in degrees from the 4x4 facial transformation matrix (rotation about the y axis)."""
    r = matrix  # only the upper-left 3x3 rotation part is used
    return math.degrees(math.atan2(r[0][2], r[2][2]))


def yaw_from_nose(landmarks):
    """Rough yaw in degrees from where the nose tip sits between the outer eye corners."""
    a = landmarks[EYE_OUTER_SUBJECT_RIGHT].x
    b = landmarks[EYE_OUTER_SUBJECT_LEFT].x
    ratio = (landmarks[NOSE_TIP].x - a) / (b - a)
    log.info("nose ratio = %.3f (0.5 = centred between the eyes)", ratio)
    return (ratio - 0.5) * 90.0


def to_label(yaw, perspective="subject"):
    """Turn a yaw angle into "left", "right" or "straight"."""
    if abs(yaw) < STRAIGHT_DEG:
        return "straight"
    image_side = "right" if yaw > 0 else "left"   # where the nose points in the image
    if perspective == "viewer":
        return image_side
    return "left" if image_side == "right" else "right"  # the person's own side is mirrored


# ---------------------------------------------------------------- main API
def classify(landmarker, image_path, perspective="subject", method="auto", annotate=None):
    """Classify one image. Returns (label, yaw_degrees, method_used)."""
    if perspective not in ("subject", "viewer"):
        raise ValueError("perspective must be 'subject' or 'viewer'")
    rgb = load_image(image_path)
    result = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    if not result.face_landmarks:
        log.warning("no face found")
        return "None", None, None

    lms = result.face_landmarks[0]
    if method in ("auto", "matrix") and result.facial_transformation_matrixes:
        yaw, used = yaw_from_matrix(result.facial_transformation_matrixes[0]), "matrix"
        log.info("yaw from transformation matrix = %+.1f deg (nose estimate %+.1f deg)", yaw, yaw_from_nose(lms))
    else:
        if method == "matrix":
            log.warning("no transformation matrix returned, using the nose fallback")
        yaw, used = yaw_from_nose(lms), "nose"
        log.info("yaw from nose position = %+.1f deg", yaw)

    label = to_label(yaw, perspective)
    log.info("yaw = %+.1f deg (%s), threshold %.0f deg, %s perspective -> %s",
             yaw, used, STRAIGHT_DEG, perspective, label)
    if annotate:
        save_annotated(rgb, lms, yaw, label, perspective, annotate)
    return label, yaw, used


def save_annotated(rgb, lms, yaw, label, perspective, out_path):
    """Draw the face mesh, a nose direction arrow and the answer, then save a PNG."""
    img = rgb.copy()
    drawing_utils.draw_landmarks(img, lms, FaceLandmarksConnections.FACE_LANDMARKS_TESSELATION, None,
                                 drawing_styles.get_default_face_mesh_tesselation_style())
    drawing_utils.draw_landmarks(img, lms, FaceLandmarksConnections.FACE_LANDMARKS_CONTOURS, None,
                                 drawing_styles.get_default_face_mesh_contours_style())
    h, w = img.shape[:2]
    nose = (int(lms[NOSE_TIP].x * w), int(lms[NOSE_TIP].y * h))
    tip_x = nose[0] + math.sin(math.radians(yaw)) * w * 0.4
    tip = (int(min(max(tip_x, 15), w - 15)), nose[1])  # keep the arrow inside the image
    cv2.arrowedLine(img, nose, tip, (255, 0, 0), 4, tipLength=0.25)
    for i in (NOSE_TIP, EYE_OUTER_SUBJECT_RIGHT, EYE_OUTER_SUBJECT_LEFT):
        cv2.circle(img, (int(lms[i].x * w), int(lms[i].y * h)), 6, (255, 220, 0), -1)
    cv2.rectangle(img, (0, 0), (w, 44), (30, 30, 30), -1)
    cv2.putText(img, f"{label}  yaw {yaw:+.1f} deg  ({perspective})", (10, 31),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    log.info("annotated image saved: %s", out_path)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Where is the face looking? Prints left, right or straight.")
    parser.add_argument("image", help="path to the input image")
    parser.add_argument("--perspective", choices=["subject", "viewer"], default="subject",
                        help="subject = the person's own left/right (default); viewer = as seen in the image")
    parser.add_argument("--method", choices=["auto", "matrix", "nose"], default="auto",
                        help="auto = matrix, nose position if no matrix (default)")
    parser.add_argument("--annotate", metavar="PNG", help="save an image with the landmarks drawn")
    parser.add_argument("-v", "--verbose", action="store_true", help="show the yaw angle and details on stderr")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format="[face_direction] %(message)s", stream=sys.stderr)
    with create_landmarker() as landmarker:
        label, _, _ = classify(landmarker, args.image, args.perspective, args.method, args.annotate)
    print(label)


if __name__ == "__main__":
    main()
