"""Download the MediaPipe models and the official sample inputs used in Week 8.

Models go to Week-8/models, sample inputs to Week-8/assets.
Files that already exist are skipped, so the script can be run again safely.

Usage:
    .venv\\Scripts\\python.exe download_models.py
"""

import sys
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
MODELS_DIR = HERE / "models"
ASSETS_DIR = HERE / "assets"

HF = "https://huggingface.co/litert-community"
MP_ASSETS = "https://storage.googleapis.com/mediapipe-assets"
MP_TASKS = "https://storage.googleapis.com/mediapipe-tasks"

# All URLs come from the "Models" sections of ai.google.dev/edge/mediapipe/solutions.
MODELS = {
    # Audio
    "yamnet.tflite": f"{HF}/MediaPipe-AudioClassifier-YAMNet/resolve/main/yamnet.tflite",
    # Keep the original .litertlm file names: the runtime reads the model type from them.
    "parakeet_tdt_0.6b_v3_5s_i8_stateful.litertlm":
        f"{HF}/parakeet-tdt-0.6b-v3/resolve/main/parakeet_tdt_0.6b_v3_5s_i8_stateful.litertlm",
    "phonon_int8.litertlm": f"{HF}/phonon-31m-en/resolve/main/phonon_int8.litertlm",
    # Decision / retrieval (EmbeddingGemma 2, Apache-2.0)
    "embeddinggemma-2-text-270m.litertlm":
        f"{HF}/embeddinggemma-2-text-270m-litert-lm/resolve/main/embeddinggemma-2-text-270m.litertlm",
    "embeddinggemma-2-text-vision-440m.litertlm":
        f"{HF}/embeddinggemma-2-text-vision-440m-litert-lm/resolve/main/embeddinggemma-2-text-vision-440m.litertlm",
    # Text
    "language_detector.tflite": f"{HF}/MediaPipe-LanguageDetector/resolve/main/language_detector.tflite",
    "bert_classifier.tflite": f"{HF}/MediaPipe-TextClassifier-MobileBERT/resolve/main/bert_classifier.tflite",
    "universal_sentence_encoder.tflite":
        f"{HF}/MediaPipe-TextEmbedder-Universal-Sentence-Encoder/resolve/main/universal_sentence_encoder.tflite",
    # Gemma Terms of Use apply to these two models.
    "proofread_quant_200m.litertlm":
        f"{HF}/MediaPipe-TextProofreader-200M/resolve/main/proofread_quant_200m.litertlm",
    "summarization_quant_200m_2modes.litertlm":
        f"{HF}/MediaPipe-TextSummarizer-200M/resolve/main/summarization_quant_200m_2modes.litertlm",
    # Vision
    "blaze_face_short_range.tflite":
        f"{HF}/MediaPipe-FaceDetector-BlazeFace-Short-Range/resolve/main/blaze_face_short_range.tflite",
    "face_landmarker.task": f"{HF}/MediaPipe-FaceLandmarker/resolve/main/face_landmarker.task",
    "gesture_recognizer.task": f"{HF}/MediaPipe-GestureRecognizer/resolve/main/gesture_recognizer.task",
    "hand_landmarker.task": f"{HF}/MediaPipe-HandLandmarker-Full/resolve/main/hand_landmarker.task",
    "holistic_landmarker.task": f"{HF}/MediaPipe-HolisticLandmarker/resolve/main/holistic_landmarker.task",
    "efficientnet_lite0_float32.tflite":
        f"{HF}/MediaPipe-ImageClassifier-EfficientNet-Lite0/resolve/main/efficientnet_lite0_float32.tflite",
    "mobilenet_v3_small.tflite":
        f"{HF}/MediaPipe-ImageEmbedder-MobileNet-V3-Small/resolve/main/mobilenet_v3_small.tflite",
    "deeplab_v3.tflite": f"{HF}/MediaPipe-ImageSegmenter-DeepLab-V3/resolve/main/deeplab_v3.tflite",
    "interactive_segmentation.task":
        f"{HF}/MediaPipe-InteractiveSegmenter-MagicTouch/resolve/main/interactive_segmentation.task",
    # MagicTouch for the keypoint (legacy) Interactive Segmenter API; much faster on CPU.
    "magic_touch.tflite":
        "https://storage.googleapis.com/mediapipe-models/interactive_segmenter/magic_touch/float32/latest/magic_touch.tflite",
    "efficientdet_lite0_float32.tflite":
        f"{HF}/MediaPipe-ObjectDetector-EfficientDet-Lite0/resolve/main/efficientdet_lite0_float32.tflite",
    "pose_landmarker_heavy.task": f"{HF}/MediaPipe-PoseLandmarker-Heavy/resolve/main/pose_landmarker_heavy.task",
}

# Official MediaPipe sample inputs (used by the MediaPipe tests and Colab notebooks).
ASSETS = {
    "speech_16000_hz_mono.wav": f"{MP_ASSETS}/speech_16000_hz_mono.wav",
    "burger.jpg": f"{MP_TASKS}/image_classifier/burger.jpg",
    "cat.jpg": f"{MP_TASKS}/image_classifier/cat.jpg",
    "cat_and_dog.jpg": f"{MP_TASKS}/object_detector/cat_and_dog.jpg",
    "thumbs_up.jpg": f"{MP_TASKS}/gesture_recognizer/thumbs_up.jpg",
    "victory.jpg": f"{MP_TASKS}/gesture_recognizer/victory.jpg",
    "woman_hands.jpg": f"{MP_TASKS}/hand_landmarker/woman_hands.jpg",
    "portrait.jpg": f"{MP_ASSETS}/portrait.jpg",
    "pose.jpg": f"{MP_ASSETS}/pose.jpg",
    "segmentation_input_rotation0.jpg": f"{MP_ASSETS}/segmentation_input_rotation0.jpg",
}

# Text inputs for the text and retrieval demos (written locally, no download needed).
TEXTS = {
    "text_classifier.txt": "I loved this movie. The story was moving and the actors were great.",
    "language_detector.txt": "Bonjour, comment allez-vous aujourd'hui ?\n"
                             "Merhaba, bugün nasılsın?\n"
                             "Guten Morgen, wie geht es dir?",
    "proofreader.txt": "Their going too the libary tomorow to studdy for they're exam.",
    "summarizer.txt": (
        "MediaPipe Solutions is a set of libraries and tools from Google for applying "
        "machine learning in applications. It runs on Android, iOS, the web and desktop "
        "with Python. Each solution, such as the face landmarker or the text classifier, "
        "comes with a ready-to-use model and a simple task API. Developers can load a model "
        "file, pass an image, an audio clip or a piece of text, and get structured results "
        "back in a few lines of code. Many models run fully on the device, so user data "
        "does not have to leave the phone or the computer. This keeps latency low and helps "
        "privacy. With MediaPipe Model Maker, developers can also retrain some models on "
        "their own data, for example to recognise new hand gestures or new object classes."
    ),
    "tts.txt": "Hello! This voice was generated on my own computer with MediaPipe text to speech.",
}


def download(url, dest):
    """Stream one file to dest, printing a short progress line."""
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  skip  {dest.name} (already there)")
        return
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        done = 0
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r  get   {dest.name}: {done / 1e6:7.1f} / {total / 1e6:.1f} MB",
                          end="", flush=True)
    tmp.replace(dest)
    print(f"\r  done  {dest.name} ({dest.stat().st_size / 1e6:.1f} MB)" + " " * 20)


def main():
    MODELS_DIR.mkdir(exist_ok=True)
    ASSETS_DIR.mkdir(exist_ok=True)
    failed = []
    for group, items, folder in (("models", MODELS, MODELS_DIR), ("assets", ASSETS, ASSETS_DIR)):
        print(f"== {group} -> {folder}")
        for name, url in items.items():
            try:
                download(url, folder / name)
            except Exception as exc:  # keep going, report at the end
                print(f"\n  FAIL  {name}: {exc}")
                failed.append(name)
    for name, text in TEXTS.items():
        (ASSETS_DIR / name).write_text(text + "\n", encoding="utf-8")
    print(f"== texts -> {ASSETS_DIR} ({len(TEXTS)} files)")
    if failed:
        print("Failed:", ", ".join(failed))
        sys.exit(1)
    print("All files are ready.")


if __name__ == "__main__":
    main()
