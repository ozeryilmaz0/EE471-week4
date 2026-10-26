import json
import os
import threading

import azure.cognitiveservices.speech as speechsdk
from dotenv import find_dotenv, load_dotenv

VOICE = "en-US-JennyNeural"
RECOGNITION_LANGUAGE = "en-US"

SOUNDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "sounds")

# Words spoken for the calculator buttons, saved as static/sounds/<word>.wav.
# The same words are given to the recognizer as a phrase list for voice commands.
SOUND_WORDS = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "point", "over", "times", "plus", "minus", "is",
)


# Build the Azure Speech configuration from SPEECH_KEY / SPEECH_REGION in the .env file
def get_speech_config():
    load_dotenv(find_dotenv())

    speech_key = os.getenv("SPEECH_KEY")
    speech_region = os.getenv("SPEECH_REGION")

    if not speech_key or not speech_region:
        raise RuntimeError(
            "Missing Azure credentials: SPEECH_KEY and SPEECH_REGION must be set "
            "in the .env file at the repository root (see .env.example)."
        )

    return speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)


# Convert text to speech and return the WAV file as bytes
def synthesize(text):
    speech_config = get_speech_config()
    speech_config.speech_synthesis_voice_name = VOICE
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
    )

    # audio_config=None keeps the audio in memory instead of playing it on the server
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return result.audio_data

    if result.reason == speechsdk.ResultReason.Canceled:
        details = result.cancellation_details
        raise RuntimeError(details.error_details or f"Synthesis canceled: {details.reason}")

    raise RuntimeError(f"Unexpected synthesis result: {result.reason}")


# Create the button sound files once; words that already have a file are skipped
def ensure_sounds():
    os.makedirs(SOUNDS_DIR, exist_ok=True)

    for word in SOUND_WORDS:
        path = os.path.join(SOUNDS_DIR, f"{word}.wav")
        if os.path.exists(path):
            continue

        audio = synthesize(word)
        with open(path, "wb") as f:
            f.write(audio)
        print(f"Created {path}")


# Recognize all speech in a 16 kHz mono WAV file and return it as spoken words.
# The Lexical form is used instead of result.text so "five" is not turned into "5".
def recognize(wav_path):
    speech_config = get_speech_config()
    speech_config.speech_recognition_language = RECOGNITION_LANGUAGE
    speech_config.output_format = speechsdk.OutputFormat.Detailed

    audio_config = speechsdk.audio.AudioConfig(filename=wav_path)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    # Make the calculator words more likely to be recognized
    phrase_list = speechsdk.PhraseListGrammar.from_recognizer(recognizer)
    for word in SOUND_WORDS:
        phrase_list.addPhrase(word)

    sentences = []
    errors = []
    done = threading.Event()

    # Collect the lexical text of each recognized sentence
    def on_recognized(evt):
        if evt.result.reason != speechsdk.ResultReason.RecognizedSpeech:
            return
        nbest = json.loads(evt.result.json).get("NBest") or []
        if nbest and nbest[0].get("Lexical"):
            sentences.append(nbest[0]["Lexical"])

    # Record Azure errors and stop waiting; reaching the end of the file is not an error
    def on_canceled(evt):
        details = evt.cancellation_details
        if details.reason == speechsdk.CancellationReason.Error:
            errors.append(details.error_details or "Speech recognition failed")
        done.set()

    # Stop waiting when the session ends
    def on_session_stopped(evt):
        done.set()

    recognizer.recognized.connect(on_recognized)
    recognizer.canceled.connect(on_canceled)
    recognizer.session_stopped.connect(on_session_stopped)

    recognizer.start_continuous_recognition()
    done.wait()
    recognizer.stop_continuous_recognition()

    if errors:
        raise RuntimeError(errors[0])

    return " ".join(sentences).strip()
