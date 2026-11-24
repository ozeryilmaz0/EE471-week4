"""Create the English speech sample (assets/speech.flac) with Azure Text-to-Speech.

Same approach as Week 5: SPEECH_KEY and SPEECH_REGION are read from the .env file in the
repository root by python-dotenv. The audio is saved as 16 kHz mono FLAC (Whisper's input
format), so no .wav file is created.

The generated file is already committed, so this script is only needed to re-create it.

Usage (from the repo root):
    venv\\Scripts\\python.exe Week-9\\make_speech_sample.py
"""

import io
import os
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import azure.cognitiveservices.speech as speechsdk
import soundfile as sf
from dotenv import find_dotenv, load_dotenv

VOICE = "en-US-JennyNeural"
TEXT = "Hugging Face pipelines let us use powerful AI models with only a few lines of Python code."
OUTPUT = Path(__file__).resolve().parent / "assets" / "speech.flac"


def main() -> int:
    load_dotenv(find_dotenv())
    key, region = os.getenv("SPEECH_KEY"), os.getenv("SPEECH_REGION")
    if not key or not region:
        sys.exit("SPEECH_KEY and SPEECH_REGION must be set in the .env file (see .env.example).")

    config = speechsdk.SpeechConfig(subscription=key, region=region)
    config.set_speech_synthesis_output_format(speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm)
    ssml = (f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">'
            f'<voice name="{VOICE}">{escape(TEXT)}</voice></speak>')
    result = speechsdk.SpeechSynthesizer(speech_config=config, audio_config=None).speak_ssml_async(ssml).get()
    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        details = getattr(result, "cancellation_details", None)
        sys.exit(f"Synthesis failed: {getattr(details, 'error_details', None) or result.reason}")

    audio, sr = sf.read(io.BytesIO(result.audio_data), dtype="int16")  # RIFF bytes -> samples
    OUTPUT.parent.mkdir(exist_ok=True)
    sf.write(OUTPUT, audio, sr, format="FLAC")
    print(f"Saved {OUTPUT.name}: {len(audio) / sr:.1f} s, {sr} Hz")
    return 0


if __name__ == "__main__":
    sys.exit(main())
