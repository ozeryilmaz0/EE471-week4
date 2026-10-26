"""Generate test audio files with Azure Text-to-Speech.

Standalone helper (not used by the web app). Saves WAV files to test_audio/.
Usage: python make_test_audio.py
"""

import os
import sys
from xml.sax.saxutils import escape

import azure.cognitiveservices.speech as speechsdk
from dotenv import find_dotenv, load_dotenv

# Load SPEECH_KEY and SPEECH_REGION from the .env file in the repository root
load_dotenv(find_dotenv())

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_audio")

# Six alternating lines, each followed by an 800 ms pause
DIALOG = [
    ("en-US-JennyNeural", "Hi Guy, are you ready for the EE471 lab today?"),
    ("en-US-GuyNeural", "Almost. I still need to set up my Azure Speech key."),
    ("en-US-JennyNeural", "It only takes a minute. Just copy it into the env file."),
    ("en-US-GuyNeural", "Done. Should we try text to speech or speech to text first?"),
    ("en-US-JennyNeural", "Let's start with text to speech, then transcribe the result."),
    ("en-US-GuyNeural", "Great idea. Let's get started."),
]

# (filename, voice, text) for the single-voice files
SINGLE_VOICE_FILES = [
    ("turkish.wav", "tr-TR-EmelNeural", "Merhaba, bugün hava çok güzel ve ders çalışıyorum."),
    ("pronunciation.wav", "en-US-JennyNeural", "The quick brown fox jumps over the lazy dog."),
    ("five_plus_two.wav", "en-US-GuyNeural", "five plus two is"),
    ("seven_minus_three.wav", "en-US-GuyNeural", "seven minus three is"),
    ("three_times_two.wav", "en-US-GuyNeural", "three times two is"),
    ("nine_over_three.wav", "en-US-GuyNeural", "nine over three is"),
]


# Build the Azure Speech configuration from environment variables
def get_speech_config():
    speech_key = os.getenv("SPEECH_KEY")
    speech_region = os.getenv("SPEECH_REGION")

    if not speech_key or not speech_region:
        sys.exit(
            "Missing Azure credentials: SPEECH_KEY and SPEECH_REGION must be set "
            "in the .env file at the repository root (see .env.example)."
        )

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
    )
    return speech_config


# Wrap one or more <voice> elements in a <speak> root element
def build_ssml(voice_elements, lang="en-US"):
    return (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{lang}">'
        f"{''.join(voice_elements)}"
        "</speak>"
    )


# Build a single <voice> element, optionally followed by a pause
def voice_element(voice, text, pause=None):
    pause_tag = f'<break time="{pause}"/>' if pause else ""
    return f'<voice name="{voice}">{escape(text)}{pause_tag}</voice>'


# Synthesize SSML and write the audio to a WAV file; return True on success
def synthesize_to_file(speech_config, ssml, filename):
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    result = synthesizer.speak_ssml_async(ssml).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        with open(os.path.join(OUTPUT_DIR, filename), "wb") as f:
            f.write(result.audio_data)
        print(f"Saved: test_audio/{filename}")
        return True

    if result.reason == speechsdk.ResultReason.Canceled:
        details = result.cancellation_details
        print(f"Failed: {filename} ({details.error_details or details.reason})")
    else:
        print(f"Failed: {filename} (unexpected result: {result.reason})")
    return False


# Generate every test audio file
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    speech_config = get_speech_config()
    all_ok = True

    dialog_ssml = build_ssml([voice_element(voice, text, "800ms") for voice, text in DIALOG])
    all_ok &= synthesize_to_file(speech_config, dialog_ssml, "dialog.wav")

    for filename, voice, text in SINGLE_VOICE_FILES:
        ssml = build_ssml([voice_element(voice, text)], lang=voice[:5])
        all_ok &= synthesize_to_file(speech_config, ssml, filename)

    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
