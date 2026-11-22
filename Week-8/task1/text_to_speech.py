"""Text-to-Speech: turn text into speech on the device with the Phonon 31M model."""

import soundfile as sf
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.audio import TextToSpeech, TextToSpeechOptions

import common

common.header("TEXT-TO-SPEECH", "Model: Phonon 31M English (Apache-2.0)  |  Input: assets/tts.txt")

text = common.read_text("tts.txt")
print(f"Input text: \"{text}\"")

options = TextToSpeechOptions(base_options=BaseOptions(model_asset_path=common.model("phonon_int8.litertlm")))
with TextToSpeech.create_from_options(options) as tts:
    voices = tts.list_voices()
    print("Available voices:", ", ".join(v.voice_id for v in voices[:8]) + (" ..." if len(voices) > 8 else ""))
    result = tts.synthesize(text)

duration = len(result.samples) / result.sample_rate_hz
common.section("Result")
print(f"  Generated {duration:.1f} s of audio at {result.sample_rate_hz} Hz")

common.OUTPUTS.mkdir(exist_ok=True)
out = common.OUTPUTS / "text_to_speech.wav"
sf.write(out, result.samples, result.sample_rate_hz)
print(f"  Saved: {out}")

common.section("Playing the generated speech")
common.play(result.samples, result.sample_rate_hz)
common.done()
