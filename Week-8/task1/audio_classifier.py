"""Audio Classifier: label the sounds in an audio clip with YAMNet (521 AudioSet classes)."""

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.audio import AudioClassifier, AudioClassifierOptions, RunningMode
from mediapipe.tasks.python.components.containers import AudioData

import common

common.header("AUDIO CLASSIFIER", "Model: YAMNet  |  Input: assets/speech_16000_hz_mono.wav")

wav = common.ASSETS / "speech_16000_hz_mono.wav"
samples, sr = common.load_wav_mono(wav)
print(f"Input clip: {wav.name}, {len(samples) / sr:.1f} s at {sr} Hz")

common.section("Playing the input clip")
common.play(samples, sr)

options = AudioClassifierOptions(
    base_options=BaseOptions(model_asset_path=common.model("yamnet.tflite")),
    running_mode=RunningMode.AUDIO_CLIPS,
    max_results=3,
)
with AudioClassifier.create_from_options(options) as classifier:
    audio = AudioData.create_from_array(samples, sr)
    results = classifier.classify(audio)  # one result per ~0.975 s window

common.section("Top-3 classes for each time window")
for r in results:
    cats = ", ".join(f"{c.category_name} ({c.score:.2f})" for c in r.classifications[0].categories)
    print(f"  t = {r.timestamp_ms / 1000:4.1f} s : {cats}")

# Overall answer: the class with the highest average score over all windows.
totals = {}
for r in results:
    for c in r.classifications[0].categories:
        totals[c.category_name] = totals.get(c.category_name, 0.0) + c.score / len(results)
best = max(totals, key=totals.get)
common.section("Result")
print(f"  Main sound in the clip: {best} (average score {totals[best]:.2f})")
common.done()
