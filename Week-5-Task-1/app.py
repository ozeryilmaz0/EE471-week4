import io
import os
import subprocess
import threading
import uuid

import azure.cognitiveservices.speech as speechsdk
from dotenv import find_dotenv, load_dotenv
from flask import Flask, jsonify, render_template, request, send_file

# Load SPEECH_KEY and SPEECH_REGION from the .env file in the repository root
load_dotenv(find_dotenv())

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

DEFAULT_VOICE = "en-US-JennyNeural"
ALLOWED_VOICES = {
    "en-US-JennyNeural",
    "en-US-GuyNeural",
    "tr-TR-EmelNeural",
    "tr-TR-AhmetNeural",
}

DEFAULT_LANGUAGE = "en-US"
ALLOWED_LANGUAGES = {"en-US", "tr-TR"}

app = Flask(__name__)


# Build the shared Azure Speech configuration from environment variables
def get_speech_config():
    speech_key = os.getenv("SPEECH_KEY")
    speech_region = os.getenv("SPEECH_REGION")

    if not speech_key or not speech_region:
        raise RuntimeError(
            "Missing Azure credentials: SPEECH_KEY and SPEECH_REGION must be set "
            "in the .env file at the repository root (see .env.example)."
        )

    return speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)


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


# Start a recognizer, wait until its session stops or is canceled, then stop it
def run_until_stopped(recognizer, start, stop):
    done = threading.Event()
    errors = []

    # Record Azure errors and stop waiting
    def on_canceled(evt):
        details = evt.cancellation_details
        if details.reason == speechsdk.CancellationReason.Error:
            errors.append(details.error_details or "Speech recognition failed")
        done.set()

    # Stop waiting when the session ends
    def on_session_stopped(evt):
        done.set()

    recognizer.canceled.connect(on_canceled)
    recognizer.session_stopped.connect(on_session_stopped)

    start()
    done.wait()
    stop()

    if errors:
        raise RuntimeError(errors[0])


# Run continuous recognition on a WAV file and return the combined text
def transcribe(wav_path, language):
    speech_config = get_speech_config()
    speech_config.speech_recognition_language = language
    audio_config = speechsdk.audio.AudioConfig(filename=wav_path)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    sentences = []

    # Collect each recognized sentence
    def on_recognized(evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech and evt.result.text:
            sentences.append(evt.result.text)

    recognizer.recognized.connect(on_recognized)
    run_until_stopped(
        recognizer,
        recognizer.start_continuous_recognition,
        recognizer.stop_continuous_recognition,
    )

    return " ".join(sentences).strip()


# Run conversation transcription on a WAV file and return speaker-labeled segments
def diarize(wav_path, language):
    speech_config = get_speech_config()
    speech_config.speech_recognition_language = language
    audio_config = speechsdk.audio.AudioConfig(filename=wav_path)
    transcriber = speechsdk.transcription.ConversationTranscriber(
        speech_config=speech_config, audio_config=audio_config
    )

    segments = []

    # Collect each transcribed phrase together with its speaker ID
    def on_transcribed(evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech and evt.result.text:
            segments.append({
                "speaker": evt.result.speaker_id or "Unknown",
                "text": evt.result.text,
            })

    transcriber.transcribed.connect(on_transcribed)
    run_until_stopped(
        transcriber,
        lambda: transcriber.start_transcribing_async().get(),
        lambda: transcriber.stop_transcribing_async().get(),
    )

    return segments


# Validate the uploaded audio, convert it to WAV and pass it to the given processor.
# Returns (result, None) on success or (None, error_response) on failure.
def process_uploaded_audio(processor):
    audio_file = request.files.get("audio")
    if audio_file is None or not audio_file.filename:
        return None, (jsonify({"error": "No audio file provided"}), 400)

    language = request.form.get("language") or DEFAULT_LANGUAGE
    if language not in ALLOWED_LANGUAGES:
        language = DEFAULT_LANGUAGE

    wav_path = None
    try:
        wav_path = convert_to_wav(audio_file)
        return processor(wav_path, language), None
    except ValueError as e:
        return None, (jsonify({"error": str(e)}), 400)
    except RuntimeError as e:
        return None, (jsonify({"error": str(e)}), 500)
    finally:
        remove_file(wav_path)


# Serve the main page
@app.route("/")
def index():
    return render_template("index.html")


# Convert the given text to speech and return it as a WAV file
@app.route("/api/tts", methods=["POST"])
def tts():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    voice = data.get("voice") or DEFAULT_VOICE

    if not text:
        return jsonify({"error": "Text cannot be empty"}), 400

    if voice not in ALLOWED_VOICES:
        voice = DEFAULT_VOICE

    try:
        speech_config = get_speech_config()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500

    speech_config.speech_synthesis_voice_name = voice
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
    )

    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return send_file(io.BytesIO(result.audio_data), mimetype="audio/wav")

    if result.reason == speechsdk.ResultReason.Canceled:
        details = result.cancellation_details
        error = details.error_details or f"Synthesis canceled: {details.reason}"
        return jsonify({"error": error}), 500

    return jsonify({"error": f"Unexpected synthesis result: {result.reason}"}), 500


# Convert an uploaded or recorded audio file to text
@app.route("/api/stt", methods=["POST"])
def stt():
    text, error = process_uploaded_audio(transcribe)
    if error:
        return error

    if not text:
        return jsonify({"error": "No speech could be recognized"}), 422

    return jsonify({"text": text})


# Identify who spoke when in an uploaded or recorded audio file
@app.route("/api/diarize", methods=["POST"])
def diarize_audio():
    segments, error = process_uploaded_audio(diarize)
    if error:
        return error

    if not segments:
        return jsonify({"error": "No speech could be recognized"}), 422

    return jsonify({"segments": segments})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
