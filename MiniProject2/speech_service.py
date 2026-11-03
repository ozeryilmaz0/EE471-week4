"""Azure Speech helpers: audio conversion, speech-to-text and text-to-speech.

The Azure key and region are read from SPEECH_KEY / SPEECH_REGION in the
.env file at the repository root (found with python-dotenv).
"""

import os
import subprocess
import threading
import uuid

import azure.cognitiveservices.speech as speechsdk
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

SPEECH_KEY = os.getenv("SPEECH_KEY")
SPEECH_REGION = os.getenv("SPEECH_REGION")

LANGUAGE = "en-US"
VOICE = "en-US-JennyNeural"

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")

# Words and phrases used in voice commands; they are given to the recognizer
# as hints so it prefers them over similar-sounding words.
COMMAND_PHRASES = (
    "help", "item", "item number", "list items", "list available books",
    "show DVDs", "checked out", "available", "books", "DVDs",
    "check out item", "checkout", "borrow item", "return item", "give back item",
    "bring back item", "delete item", "remove item", "replace item",
    "update item", "change item", "edit item", "set item",
    "create item", "add a book", "add a DVD", "get item", "show item",
    "describe item", "tell me about item",
    "type book", "type DVD", "title", "author", "director", "pages",
    "page count", "duration", "minutes",
)


class SpeechError(RuntimeError):
    """Raised when audio conversion or an Azure Speech call fails."""


def get_speech_config():
    """Return a SpeechConfig built from the .env credentials."""
    if not SPEECH_KEY or not SPEECH_REGION:
        raise SpeechError(
            "SPEECH_KEY and SPEECH_REGION must be set in the .env file "
            "at the repository root.")
    return speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)


def remove_file(path):
    """Delete a file, ignoring errors if it is missing or still locked."""
    try:
        os.remove(path)
    except OSError:
        pass


def convert_to_wav(file_storage):
    """Save an uploaded file and convert it to a 16 kHz mono WAV with ffmpeg.

    The uploaded original is deleted after conversion. The caller owns the
    returned WAV path and should delete it with remove_file() when done.
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    unique_id = uuid.uuid4().hex
    extension = os.path.splitext(file_storage.filename or "")[1] or ".bin"
    input_path = os.path.join(UPLOAD_DIR, f"{unique_id}_input{extension}")
    output_path = os.path.join(UPLOAD_DIR, f"{unique_id}.wav")

    file_storage.save(input_path)
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", input_path, "-ar", "16000", "-ac", "1", output_path],
            check=True, capture_output=True,
        )
    except FileNotFoundError as error:
        remove_file(output_path)
        raise SpeechError(
            "ffmpeg was not found. Install ffmpeg and make sure it is on your PATH."
        ) from error
    except subprocess.CalledProcessError as error:
        remove_file(output_path)
        raise SpeechError("ffmpeg could not convert the uploaded audio.") from error
    finally:
        remove_file(input_path)
    return output_path


def transcribe(wav_path, extra_phrases=()):
    """Recognize all speech in a WAV file and return the display text.

    Display text is used (not the lexical form) so that numbers come back as
    digits, e.g. "item 4" instead of "item four". Continuous recognition is
    used so that long commands with pauses are not cut after one sentence.
    """
    speech_config = get_speech_config()
    speech_config.speech_recognition_language = LANGUAGE

    audio_config = speechsdk.audio.AudioConfig(filename=wav_path)
    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config, audio_config=audio_config)

    phrase_list = speechsdk.PhraseListGrammar.from_recognizer(recognizer)
    for phrase in (*COMMAND_PHRASES, *extra_phrases):
        if phrase:
            phrase_list.addPhrase(phrase)

    sentences = []
    errors = []
    done = threading.Event()

    def on_recognized(evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech and evt.result.text:
            sentences.append(evt.result.text)

    def on_canceled(evt):
        # Reaching the end of the file also cancels; only real errors are kept.
        details = evt.cancellation_details
        if details.reason == speechsdk.CancellationReason.Error:
            errors.append(details.error_details or "Speech recognition failed")
        done.set()

    def on_session_stopped(evt):
        done.set()

    recognizer.recognized.connect(on_recognized)
    recognizer.canceled.connect(on_canceled)
    recognizer.session_stopped.connect(on_session_stopped)

    recognizer.start_continuous_recognition()
    done.wait(timeout=60)
    recognizer.stop_continuous_recognition()

    if errors:
        raise SpeechError(errors[0])
    return " ".join(sentences).strip()


def synthesize(text):
    """Convert text to speech with Jenny and return the WAV file as bytes."""
    speech_config = get_speech_config()
    speech_config.speech_synthesis_voice_name = VOICE
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm)

    # audio_config=None keeps the audio in memory instead of playing it on the server.
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=None)
    result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return result.audio_data
    if result.reason == speechsdk.ResultReason.Canceled:
        details = result.cancellation_details
        raise SpeechError(details.error_details or f"Synthesis canceled: {details.reason}")
    raise SpeechError(f"Unexpected synthesis result: {result.reason}")
