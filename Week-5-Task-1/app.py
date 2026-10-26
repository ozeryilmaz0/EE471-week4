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

# Languages for Speech to Text and Diarization (code -> label)
DEFAULT_LANGUAGE = "en-US"
ALLOWED_LANGUAGES = {
    "en-US": "English (en-US)",
    "tr-TR": "Türkçe (tr-TR)",
}

# Spoken source languages for Translation (code -> label)
TRANSLATION_SOURCES = {
    "tr-TR": "Türkçe (tr-TR)",
    "en-US": "English (en-US)",
    "de-DE": "Deutsch (de-DE)",
    "fr-FR": "Français (fr-FR)",
    "es-ES": "Español (es-ES)",
}

# Target languages for Translation and the voice used to speak each one
TRANSLATION_TARGETS = {
    "en": {"name": "English", "voice": "en-US-JennyNeural"},
    "tr": {"name": "Türkçe", "voice": "tr-TR-EmelNeural"},
    "de": {"name": "Deutsch", "voice": "de-DE-KatjaNeural"},
    "fr": {"name": "Français", "voice": "fr-FR-DeniseNeural"},
    "es": {"name": "Español", "voice": "es-ES-ElviraNeural"},
}

DEFAULT_VOICE = "en-US-JennyNeural"
ALLOWED_VOICES = {
    "en-US-JennyNeural",
    "en-US-GuyNeural",
    "tr-TR-EmelNeural",
    "tr-TR-AhmetNeural",
} | {target["voice"] for target in TRANSLATION_TARGETS.values()}

app = Flask(__name__)


# Read the Azure key and region from environment variables
def get_azure_credentials():
    speech_key = os.getenv("SPEECH_KEY")
    speech_region = os.getenv("SPEECH_REGION")

    if not speech_key or not speech_region:
        raise RuntimeError(
            "Missing Azure credentials: SPEECH_KEY and SPEECH_REGION must be set "
            "in the .env file at the repository root (see .env.example)."
        )

    return speech_key, speech_region


# Build the shared Azure Speech configuration from environment variables
def get_speech_config():
    speech_key, speech_region = get_azure_credentials()
    return speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)


# Build the Azure speech translation configuration for one source and target language
def get_translation_config(source, target):
    speech_key, speech_region = get_azure_credentials()
    translation_config = speechsdk.translation.SpeechTranslationConfig(
        subscription=speech_key, region=speech_region
    )
    translation_config.speech_recognition_language = source
    translation_config.add_target_language(target)
    return translation_config


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


# Run continuous speech translation on a WAV file and return (original, translation)
def translate(wav_path, source, target):
    translation_config = get_translation_config(source, target)
    audio_config = speechsdk.audio.AudioConfig(filename=wav_path)
    recognizer = speechsdk.translation.TranslationRecognizer(
        translation_config=translation_config, audio_config=audio_config
    )

    originals = []
    translations = []

    # Collect each recognized sentence and its translation
    def on_recognized(evt):
        if evt.result.reason == speechsdk.ResultReason.TranslatedSpeech and evt.result.text:
            originals.append(evt.result.text)
            translations.append(evt.result.translations.get(target, ""))

    recognizer.recognized.connect(on_recognized)
    run_until_stopped(
        recognizer,
        recognizer.start_continuous_recognition,
        recognizer.stop_continuous_recognition,
    )

    original = " ".join(originals).strip()
    translation = " ".join(text for text in translations if text).strip()
    return original, translation


# Score how well the audio matches the reference text; return None if no speech was heard
def assess_pronunciation(wav_path, reference_text, language):
    speech_config = get_speech_config()
    speech_config.speech_recognition_language = language
    audio_config = speechsdk.audio.AudioConfig(filename=wav_path)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    assessment_config = speechsdk.PronunciationAssessmentConfig(
        reference_text=reference_text,
        grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
        granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
        enable_miscue=True,
    )
    assessment_config.apply_to(recognizer)

    result = recognizer.recognize_once_async().get()

    if result.reason == speechsdk.ResultReason.NoMatch:
        return None

    if result.reason == speechsdk.ResultReason.Canceled:
        details = result.cancellation_details
        raise RuntimeError(details.error_details or f"Recognition canceled: {details.reason}")

    assessment = speechsdk.PronunciationAssessmentResult(result)
    return {
        "recognized": result.text,
        "scores": {
            "pronunciation": assessment.pronunciation_score,
            "accuracy": assessment.accuracy_score,
            "fluency": assessment.fluency_score,
            "completeness": assessment.completeness_score,
        },
        "words": [
            {
                "word": word.word,
                "accuracy_score": word.accuracy_score,
                "error_type": word.error_type,
            }
            for word in assessment.words
        ],
    }


# Read the recognition language from the form, falling back to the default
def get_form_language():
    language = request.form.get("language") or DEFAULT_LANGUAGE
    return language if language in ALLOWED_LANGUAGES else DEFAULT_LANGUAGE


# Validate the uploaded audio, convert it to WAV and pass the WAV path to the processor.
# Returns (result, None) on success or (None, error_response) on failure.
def process_uploaded_audio(processor):
    audio_file = request.files.get("audio")
    if audio_file is None or not audio_file.filename:
        return None, (jsonify({"error": "No audio file provided"}), 400)

    wav_path = None
    try:
        wav_path = convert_to_wav(audio_file)
        return processor(wav_path), None
    except ValueError as e:
        return None, (jsonify({"error": str(e)}), 400)
    except RuntimeError as e:
        return None, (jsonify({"error": str(e)}), 500)
    finally:
        remove_file(wav_path)


# Serve the main page
@app.route("/")
def index():
    return render_template(
        "index.html",
        languages=ALLOWED_LANGUAGES,
        translation_sources=TRANSLATION_SOURCES,
        translation_targets=TRANSLATION_TARGETS,
    )


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
    language = get_form_language()
    text, error = process_uploaded_audio(lambda wav_path: transcribe(wav_path, language))
    if error:
        return error

    if not text:
        return jsonify({"error": "No speech could be recognized"}), 422

    return jsonify({"text": text})


# Identify who spoke when in an uploaded or recorded audio file
@app.route("/api/diarize", methods=["POST"])
def diarize_audio():
    language = get_form_language()
    segments, error = process_uploaded_audio(lambda wav_path: diarize(wav_path, language))
    if error:
        return error

    if not segments:
        return jsonify({"error": "No speech could be recognized"}), 422

    return jsonify({"segments": segments})


# Recognize speech in one language and translate it into another
@app.route("/api/translate", methods=["POST"])
def translate_audio():
    source = request.form.get("source")
    target = request.form.get("target")

    if source not in TRANSLATION_SOURCES:
        return jsonify({"error": f"Unsupported source language: {source}"}), 400
    if target not in TRANSLATION_TARGETS:
        return jsonify({"error": f"Unsupported target language: {target}"}), 400

    result, error = process_uploaded_audio(lambda wav_path: translate(wav_path, source, target))
    if error:
        return error

    original, translation = result
    if not original:
        return jsonify({"error": "No speech could be recognized"}), 422

    return jsonify({"original": original, "translation": translation})


# Compare a recording against a reference text and return pronunciation scores
@app.route("/api/pronunciation", methods=["POST"])
def pronunciation():
    reference_text = (request.form.get("reference_text") or "").strip()
    if not reference_text:
        return jsonify({"error": "Reference text cannot be empty"}), 400

    language = get_form_language()
    assessment, error = process_uploaded_audio(
        lambda wav_path: assess_pronunciation(wav_path, reference_text, language)
    )
    if error:
        return error

    if not assessment:
        return jsonify({"error": "No speech could be recognized"}), 422

    return jsonify(assessment)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
