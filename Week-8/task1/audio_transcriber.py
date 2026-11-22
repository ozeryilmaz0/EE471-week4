"""Audio Transcriber: speech-to-text on the device with NVIDIA Parakeet TDT 0.6B v3."""

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.audio import AudioTranscriber, AudioTranscriberOptions

import common

common.header("AUDIO TRANSCRIBER",
              "Model: Parakeet TDT 0.6B v3 (CC-BY-4.0)  |  Input: assets/speech_16000_hz_mono.wav")

wav = common.ASSETS / "speech_16000_hz_mono.wav"
samples, sr = common.load_wav_mono(wav)
print(f"Input clip: {wav.name}, {len(samples) / sr:.1f} s at {sr} Hz")

common.section("Playing the input clip")
common.play(samples, sr)

options = AudioTranscriberOptions(
    base_options=BaseOptions(
        model_asset_path=common.model("parakeet_tdt_0.6b_v3_5s_i8_stateful.litertlm")),
    sample_rate_hz=sr,
)
common.section("Loading the model and transcribing")
with AudioTranscriber.create_from_options(options) as transcriber:
    result = transcriber.transcribe(samples, end_of_stream=True)

common.section("Segments")
for seg in result.segments:
    print(f"  [{seg.from_timestamp_ms / 1000:5.2f} s - {seg.to_timestamp_ms / 1000:5.2f} s] "
          f"{seg.transcript.strip()}")
common.section("Transcript")
print("  " + " ".join(s.transcript.strip() for s in result.segments))
common.done()
