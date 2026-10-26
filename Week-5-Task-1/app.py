import os
import subprocess
import threading
import uuid

import azure.cognitiveservices.speech as speechsdk
from dotenv import find_dotenv, load_dotenv
from flask import Flask, jsonify, render_template, request

# Load SPEECH_KEY and SPEECH_REGION from the .env file in the repository root
load_dotenv(find_dotenv())

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

DEFAULT_LANGUAGE = "en-US"
ALLOWED_LANGUAGES = {"en-US", "tr-TR"}

app = Flask(__name__)


# Build the Azure Speech configuration from environment variables
def get_speech_config(language=DEFAULT_LANGUAGE):
    speech_key = os.getenv("SPEECH_KEY")
    speech_region = os.getenv("SPEECH_REGION")

    if not speech_key or not speech_region:
        raise RuntimeError(
            "Missing Azure credentials: SPEECH_KEY and SPEECH_REGION must be set "
            "in the .env file at the repository root (see .env.example)."
        )

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    speech_config.speech_recognition_language = language
    return speech_config


# Delete a file, ignoring errors if it is missing or still locked
def remove_file(path):
    if not path:
        return
    try:
        os.remove(path)
    except OSError:
        pass


# Save the uploaded file and convert it to a 16 kHz mono WAV with ffmpeg
def convert_to_wav(file_storage):
    unique_id = uuid.uuid4().hex
    extension = os.path.splitext(file_storage.filename or "")[1] or ".bin"
    input_path = os.path.join(UPLOAD_DIR, f"{unique_id}_input{extension}")
    output_path = os.path.join(UPLOAD_DIR, f"{unique_id}.wav")

    file_storage.save(input_path)
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", input_path, "-ar", "16000", "-ac", "1", output_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True,
        )
    except FileNotFoundError:
        remove_file(output_path)
        raise RuntimeError(
            "ffmpeg was not found. Install ffmpeg and make sure it is on your PATH."
        )
    except subprocess.CalledProcessError:
        remove_file(output_path)
        raise ValueError("The uploaded file could not be converted. Is it a valid audio file?")
    finally:
        remove_file(input_path)

    return output_path


# Run continuous recognition on a WAV file and return the combined text
def transcribe(wav_path, language):
    speech_config = get_speech_config(language)
    audio_config = speechsdk.audio.AudioConfig(filename=wav_path)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    done = threading.Event()
    sentences = []
    errors = []

    # Collect each recognized sentence
    def on_recognized(evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech and evt.result.text:
            sentences.append(evt.result.text)

    # Record Azure errors and stop waiting
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


# Serve the main page
@app.route("/")
def index():
    return render_template("index.html")


# Convert an uploaded or recorded audio file to text
@app.route("/api/stt", methods=["POST"])
def stt():
    audio_file = request.files.get("audio")
    if audio_file is None or not audio_file.filename:
        return jsonify({"error": "No audio file provided"}), 400

    language = request.form.get("language") or DEFAULT_LANGUAGE
    if language not in ALLOWED_LANGUAGES:
        language = DEFAULT_LANGUAGE

    wav_path = None
    try:
        wav_path = convert_to_wav(audio_file)
        text = transcribe(wav_path, language)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    finally:
        remove_file(wav_path)

    if not text:
        return jsonify({"error": "No speech could be recognized"}), 422

    return jsonify({"text": text})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
