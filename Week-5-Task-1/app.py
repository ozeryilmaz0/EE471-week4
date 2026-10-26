import io
import os

import azure.cognitiveservices.speech as speechsdk
from dotenv import find_dotenv, load_dotenv
from flask import Flask, jsonify, render_template, request, send_file

# Load SPEECH_KEY and SPEECH_REGION from the .env file in the repository root
load_dotenv(find_dotenv())

app = Flask(__name__)

DEFAULT_VOICE = "en-US-JennyNeural"
ALLOWED_VOICES = {
    "en-US-JennyNeural",
    "en-US-GuyNeural",
    "tr-TR-EmelNeural",
    "tr-TR-AhmetNeural",
}


# Build the Azure Speech configuration from environment variables
def get_speech_config(voice=DEFAULT_VOICE):
    speech_key = os.getenv("SPEECH_KEY")
    speech_region = os.getenv("SPEECH_REGION")

    if not speech_key or not speech_region:
        raise RuntimeError(
            "Missing Azure credentials: SPEECH_KEY and SPEECH_REGION must be set "
            "in the .env file at the repository root (see .env.example)."
        )

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    speech_config.speech_synthesis_voice_name = voice
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
    )
    return speech_config


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
        speech_config = get_speech_config(voice)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500

    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return send_file(io.BytesIO(result.audio_data), mimetype="audio/wav")

    if result.reason == speechsdk.ResultReason.Canceled:
        details = result.cancellation_details
        error = details.error_details or f"Synthesis canceled: {details.reason}"
        return jsonify({"error": error}), 500

    return jsonify({"error": f"Unexpected synthesis result: {result.reason}"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
