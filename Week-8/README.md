# Week 8 – MediaPipe Solutions

In-class exercise for EE 471, week 8.

* **Task 1** – a Python demo for each of the 22 MediaPipe solutions (`task1/`)
* **Task 2** – which arm is up? Pose Landmarker + Cog (`task2-arm/`)
* **Task 3** – where is the face looking? Face Landmarker + Cog (`task3-face/`)

```
Week-8/
├── download_models.py     downloads all models and the official sample inputs
├── requirements.txt       Python packages for the local virtual environment
├── models/                .task / .tflite / .litertlm model files
├── assets/                official MediaPipe sample images and audio, demo texts
├── inputs/                the assignment images pose-1..3.jpg and face-1..3.png
├── task1/                 22 demo scripts, common.py, run_all_demos.py, outputs/
├── task2-arm/             arm_up.py, Cog files (cog.yaml, run.py), outputs/
└── task3-face/            face_direction.py, Cog files (cog.yaml, run.py), outputs/
```

## 1. Setup

Windows, PowerShell, from the `Week-8` folder. MediaPipe 1.2.3 needs Python 3.9–3.12,
so the virtual environment uses Python 3.12 (installed with [uv](https://docs.astral.sh/uv/)).

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
.venv\Scripts\python.exe download_models.py
```

`download_models.py` downloads about 1.9 GB and skips files that already exist.
The URLs come from the "Models" section of each solution page on
[ai.google.dev/edge/mediapipe](https://ai.google.dev/edge/mediapipe/solutions/guide).
No login is needed. Model files larger than 50 MB (the `.litertlm` files) are not in Git;
run the script to get them.

Licenses: most models are Apache-2.0. Parakeet TDT (Audio Transcriber) is CC-BY-4.0 (NVIDIA).
The Text Proofreader and Text Summarizer models are under the
[Gemma Terms of Use](https://ai.google.dev/gemma/terms); they are downloaded, not redistributed.

## 2. Task 1 – 22 MediaPipe solutions

Every solution in the assignment has a **Python** task API in `mediapipe==1.2.3`, so all
22 demos are Python scripts. No web (JavaScript) fallback was needed.

Each script loads its model, runs it on a sample input, prints a readable result and finishes
in a few seconds. Vision demos save a PNG to `task1/outputs/` and open it; audio demos play
the sound.

```powershell
.venv\Scripts\python.exe task1\text_to_speech.py        # one demo
.venv\Scripts\python.exe task1\run_all_demos.py         # all 22, for the screen recording
```

`run_all_demos.py` clears the terminal and shows a big title (`3/22 TEXT-TO-SPEECH`) before
each demo, runs it after Enter, and writes the time each title appeared to
`task1/demo_timestamps.json` (to cut the long recording into 22 videos later).
Options: `--start N` continues from demo N, `--auto` runs without Enter.
It hides the C++ log lines of MediaPipe/LiteRT; Python errors are still shown.

| # | Solution | Script | Python or web | Input | Output |
|---|---|---|---|---|---|
| 1 | Audio Classifier | `audio_classifier.py` | Python | `speech_16000_hz_mono.wav` | top-3 sound classes per second (YAMNet): *Speech* |
| 2 | Audio Transcriber | `audio_transcriber.py` | Python | `speech_16000_hz_mono.wav` | text: "Send a text to Mike, I'll be home late tomorrow." (Parakeet TDT 0.6B) |
| 3 | Text-to-Speech | `text_to_speech.py` | Python | `assets/tts.txt` | 6 s of speech, played and saved to `outputs/text_to_speech.wav` (Phonon 31M) |
| 4 | Decision Maker | `decision_maker.py` | Python | 3 support messages | department (billing / technical / how_to) and urgent yes/no (EmbeddingGemma 2 270M) |
| 5 | Semantic Retriever | `semantic_retriever.py` | Python | 6 notes + 3 questions | best matching notes with scores, in-memory vector database |
| 6 | Universal Embedder | `universal_embedder.py` | Python | 3 images + 3 captions | image-text similarity matrix, best caption per image (EmbeddingGemma 2 440M) |
| 7 | Language Detector | `language_detector.py` | Python | French, Turkish, German sentences | `fr`, `tr`, `de` with probabilities |
| 8 | Text Classifier | `text_classifier.py` | Python | 2 movie reviews | positive / negative (MobileBERT) |
| 9 | Text Embedder | `text_embedder.py` | Python | 4 sentences | cosine similarities (Universal Sentence Encoder) |
| 10 | Text Proofreader | `text_proofreader.py` | Python | sentence with spelling errors | corrected sentence and changed words (Proofread 200M) |
| 11 | Text Summarizer | `text_summarizer.py` | Python | 129-word paragraph | TL;DR and key-point summaries (Summarization 200M) |
| 12 | Face Detector | `face_detector.py` | Python | `inputs/face-1..3.png` | face boxes and 6 key points |
| 13 | Face Landmarker | `face_landmarker.py` | Python | `inputs/face-1..3.png` | 478-point mesh, top blendshapes, head yaw |
| 14 | Gesture Recognizer | `gesture_recognizer.py` | Python | `thumbs_up.jpg`, `victory.jpg` | *Thumb_Up*, *Victory* + hand skeleton |
| 15 | Hand Landmarker | `hand_landmarker.py` | Python | `woman_hands.jpg` | 2 hands × 21 points, left/right |
| 16 | Holistic Landmarker | `holistic_landmarker.py` | Python | `inputs/pose-3.jpg` | pose 33 + face 478 + 2 hands × 21 points in one pass |
| 17 | Image Classifier | `image_classifier.py` | Python | `burger.jpg`, `cat.jpg` | top-3 ImageNet classes (*cheeseburger*, *tabby*) |
| 18 | Image Embedder | `image_embedder.py` | Python | `cat.jpg`, `cat_and_dog.jpg`, `burger.jpg` | cosine similarity to the cat photo |
| 19 | Image Segmenter | `image_segmenter.py` | Python | `segmentation_input_rotation0.jpg`, `inputs/pose-3.jpg` | per-pixel classes (*person*, *horse*) as a colour overlay |
| 20 | Interactive Segmenter | `interactive_segmenter.py` | Python | `cat_and_dog.jpg` + a fixed click on the dog | mask of the clicked object |
| 21 | Object Detector | `object_detector.py` | Python | `cat_and_dog.jpg`, `inputs/pose-2.jpg` | boxes: *cat*, *dog*, *person* |
| 22 | Pose Landmarker | `pose_landmarker.py` | Python | `pose.jpg`, `inputs/pose-1..3.jpg` | 33-point skeletons (heavy model) |

Notes

* **Interactive Segmenter.** `mediapipe` 1.2.3 has two Python APIs. The new stroke API
  (`InteractiveSegmenter` + `interactive_segmentation.task`) works, but one `segment()` call
  takes about 55 s on this laptop's CPU and the GPU path is disabled in the pip package.
  The demo therefore uses the keypoint API (`InteractiveSegmenterLegacy`) with the official
  `magic_touch.tflite` model (under 1 s). `python task1\interactive_segmenter.py --new-api`
  runs the stroke API; both give the same mask (19.7 % of the image, the dog).
* **Decision Maker.** The choice question works very well with the 270M embedding model. The
  yes/no probabilities of an embedding model are low in absolute terms, so the "urgent"
  question uses `threshold=0.2` instead of 0.5.
* **Image Segmenter.** DeepLab-V3 (PASCAL VOC) labels the cat in `cat_and_dog.jpg` as *dog*, so
  the demo uses the official MediaPipe segmentation test image and a person photo.

## 3. Task 2 – Which arm is up?

`task2-arm/arm_up.py` prints one word: `left`, `right`, `both` or `None`.

**Rule.** MediaPipe Pose Landmarker (heavy) gives 33 body landmarks with `x`, `y` in 0..1
(`y` grows downwards) and a `visibility` score. An arm is *up* when its wrist is clearly above
its shoulder:

```
shoulder.y - wrist.y > 0.10 × torso length       (torso length = shoulder centre to hip centre)
```

Landmarks with `visibility < 0.5` are ignored (that arm counts as down). No person → `None`.

### Perspective

* `subject` (default): the person's **own** left and right. This is how MediaPipe names its
  landmarks (`LEFT_WRIST` is the person's left wrist), so the answer is the arm the person
  would call their left/right arm.
* `viewer` (`--perspective viewer`): left and right as seen in the image. For a person
  facing the camera this is the mirror image of `subject`.

### Usage

```powershell
# CLI (Windows, from Week-8)
.venv\Scripts\python.exe task2-arm\arm_up.py inputs\pose-1.jpg
.venv\Scripts\python.exe task2-arm\arm_up.py inputs\pose-1.jpg --perspective viewer -v --annotate task2-arm\outputs\pose-1-annotated.png
```

```bash
# Cog (Ubuntu / WSL)
cd /mnt/c/<repo>/Week-8/task2-arm
cog run --use-cog-base-image=false -i image=@../inputs/pose-1.jpg
cog run --use-cog-base-image=false -i image=@../inputs/pose-1.jpg -i perspective=viewer
cog build --use-cog-base-image=false -t arm-up-classifier

# Docker + HTTP API (ports 5000-5003 are kept free, so 5040 is used)
docker run -d --rm --name arm-up -p 5040:5000 arm-up-classifier
curl -s http://localhost:5040/health-check
curl -s -X POST http://localhost:5040/predictions -H "Content-Type: application/json" \
  -d "{\"input\": {\"image\": \"data:image/jpeg;base64,$(base64 -w0 ../inputs/pose-1.jpg)\", \"perspective\": \"subject\"}}"
docker stop arm-up
```

### Results

| Image | What the photo shows (checked by eye) | Left wrist lift | Right wrist lift | CLI `subject` | CLI `viewer` | Cog `subject` | Cog `viewer` |
|---|---|---|---|---|---|---|---|
| `pose-1.jpg` | woman raises her **left** arm over her head (right side of the image); right hand down at the hip | +0.171 (up) | −0.226 (down) | `left` | `right` | `left` | `right` |
| `pose-2.jpg` | man raises his **right** fist (left side of the image); left fist at the chest, below the shoulder | −0.065 (down) | +0.139 (up) | `right` | `left` | `right` | `left` |
| `pose-3.jpg` | man raises **both** fists | +0.206 (up) | +0.209 (up) | `both` | `both` | `both` | `both` |

Lift = shoulder.y − wrist.y (normalized); the margin is 0.018–0.028 for these photos.
A photo without a person (`assets/burger.jpg`) gives `None`.

`task2-arm/outputs/pose-N-annotated.png` shows the skeleton, the shoulders and wrists
(orange = the person's left, blue = the person's right) and the answer.

## 4. Task 3 – Where is the face looking?

`task3-face/face_direction.py` prints one word: `left`, `right` or `straight`
(`None` if no face is found).

**Method.** MediaPipe Face Landmarker is created with
`output_facial_transformation_matrixes=True`. The 4×4 matrix is the head pose of the canonical
face model; its rotation part gives the yaw (turn around the vertical axis):

```
yaw = atan2(R[0][2], R[2][2])        yaw > 0: the nose points to the right side of the image
```

Fallback (no matrix, or `--method nose`): the nose tip (landmark 1) is compared with the outer
eye corners (landmarks 33 and 263). `ratio = 0.5` means a frontal face;
`yaw ≈ (ratio − 0.5) × 90°`.

`|yaw| < 10°` → `straight`; otherwise the sign gives the side. The yaw angle is written to the
log (`-v` on the CLI, always in the Cog log).

### Perspective

* `subject` (default): the person's own left/right. When a person turns to their own left,
  the nose moves to the right side of the image (yaw > 0) → `left`.
* `viewer`: as seen in the image (yaw > 0 → `right`).

### Usage

```powershell
.venv\Scripts\python.exe task3-face\face_direction.py inputs\face-1.png
.venv\Scripts\python.exe task3-face\face_direction.py inputs\face-1.png --perspective viewer -v --annotate task3-face\outputs\face-1-annotated.png
```

```bash
cd /mnt/c/<repo>/Week-8/task3-face
cog run --use-cog-base-image=false -i image=@../inputs/face-1.png
cog build --use-cog-base-image=false -t face-direction-classifier

docker run -d --rm --name face-dir -p 5041:5000 face-direction-classifier
curl -s -X POST http://localhost:5041/predictions -H "Content-Type: application/json" \
  -d "{\"input\": {\"image\": \"data:image/png;base64,$(base64 -w0 ../inputs/face-1.png)\", \"perspective\": \"subject\"}}"
docker stop face-dir
```

### Results

| Image | What the photo shows (checked by eye) | Yaw (matrix) | Yaw (nose fallback) | CLI `subject` | CLI `viewer` | Cog `subject` | Cog `viewer` |
|---|---|---|---|---|---|---|---|
| `face-1.png` | nose points to the left of the image: she looks to her **own right** | −35.4° | −44.4° | `right` | `left` | `right` | `left` |
| `face-2.png` | nose points to the right of the image: she looks to her **own left** | +32.0° | +42.0° | `left` | `right` | `left` | `right` |
| `face-3.png` | frontal face | −2.4° | −0.8° | `straight` | `straight` | `straight` | `straight` |

The matrix and the nose fallback agree on all three images (`--method nose`).
`task3-face/outputs/face-N-annotated.png` shows the face mesh, the nose tip and outer eye
corners, an arrow in the nose direction and the answer.

## 5. Cog notes

* `cog.yaml` uses Python 3.12 (supported by mediapipe 1.2.3). It installs `libgl1` and
  `libglib2.0-0` for OpenCV, and `libegl1` and `libgles2`: the Linux `libmediapipe.so`
  links to `libEGL.so.1` and `libGLESv2.so.2`, and `setup()` fails without them.
* The runner logs to file descriptor 2 (shown by `cog run` and `docker logs`) and to the
  current `sys.stdout` (the `logs` field of the HTTP response), so the measurements and the
  yaw angle are visible everywhere. The MediaPipe C++ warnings in the log are harmless.
* The line `ERROR: ... no access allowed to dir "context"` during `cog run` / `cog build` is a
  harmless message of Cog's second build stage (it also appears for the Week 7 images).
* The model file (`pose_landmarker_heavy.task`, `face_landmarker.task`) is in the Cog folder,
  so `cog build` copies it into the image. `.dockerignore` keeps `outputs/` out of the image.
* `run.py` is a Cog `BaseRunner`: `setup()` loads the model once, `run()` takes
  `image: Path` and `perspective: str = "subject"` and returns a string.
