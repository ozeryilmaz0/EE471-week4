import io
import math
import os
import re
import string
import subprocess
import uuid

from flask import Flask, jsonify, request, send_file

from custom_classes import Calculator
from speech_utils import ensure_sounds, recognize, synthesize

app = Flask(__name__, static_folder="static", static_url_path="")

OPERATIONS = ("add", "subtract", "multiply", "divide")

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Spoken words and typed symbols -> calculator key symbols (same as on the buttons)
COMMAND_TOKENS = {
    "zero": "0", "oh": "0",
    "one": "1", "won": "1",
    "two": "2", "to": "2", "too": "2",
    "three": "3",
    "four": "4", "for": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8", "ate": "8",
    "nine": "9",
    "point": ".", "dot": ".",
    "over": "÷", "divided": "÷",
    "times": "×", "multiplied": "×", "x": "×",
    "plus": "+",
    "minus": "−",
    "is": "=", "equals": "=",
    ".": ".",
    "/": "÷", "÷": "÷",
    "*": "×", "×": "×",
    "+": "+",
    "-": "−", "−": "−",
    "=": "=",
}

NUMBER_PATTERN = re.compile(r"\d+(\.\d+)?")


def is_number(value):
    # bool is a subclass of int, so it has to be excluded explicitly.
    # Python's JSON parser accepts NaN/Infinity, so floats must also be finite.
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, float) and math.isfinite(value)


def error(message):
    return jsonify({"error": message}), 400


# Delete a file, ignoring errors if it is missing or still locked
def remove_file(path):
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
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except FileNotFoundError:
        remove_file(output_path)
        raise RuntimeError("ffmpeg was not found. Install ffmpeg and make sure it is on your PATH.")
    except subprocess.CalledProcessError:
        remove_file(output_path)
        raise ValueError("The recording could not be converted. Is it a valid audio file?")
    finally:
        remove_file(input_path)

    return output_path


# Turn recognized words into calculator key symbols; unknown words go to "ignored"
def parse_command(text):
    tokens = []
    ignored = []

    for raw in text.lower().split():
        # Lone symbols such as "+" or "." would disappear when punctuation is removed
        if raw in COMMAND_TOKENS:
            tokens.append(COMMAND_TOKENS[raw])
            continue

        word = raw.strip(string.punctuation)
        if word in COMMAND_TOKENS:
            tokens.append(COMMAND_TOKENS[word])
        elif NUMBER_PATTERN.fullmatch(word):
            tokens.extend(word)  # "12" -> "1", "2"
        elif word:
            ignored.append(word)

    return tokens, ignored


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error("Request body must be a JSON object")

    for name in ("x", "y", "operation"):
        if name not in data:
            return error(f"Missing field '{name}'")

    x = data["x"]
    y = data["y"]
    operation = data["operation"]

    if not is_number(x):
        return error("'x' must be a number")
    if not is_number(y):
        return error("'y' must be a number")
    if operation not in OPERATIONS:
        return error("'operation' must be one of: " + ", ".join(OPERATIONS))

    calc = Calculator()
    method = getattr(calc, operation)  # safe: operation is one of OPERATIONS

    try:
        result = method(x, y)
    except ValueError:
        return error("Cannot divide by zero")
    except OverflowError:
        return error("Result is too large")

    if isinstance(result, float):
        # e.g. 1e308 * 10 gives inf, which is not valid JSON
        if not math.isfinite(result):
            return error("Result is too large")
        # Remove floating-point noise (0.1 + 0.2 = 0.30000000000000004 -> 0.3)
        result = float(f"{result:.15g}")

    return jsonify({"result": result}), 200


@app.route("/api/speak", methods=["POST"])
def api_speak():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error("Request body must be a JSON object")

    text = data.get("text")
    if not isinstance(text, str) or not text.strip():
        return error("'text' must be a non-empty string")

    try:
        audio = synthesize(text.strip())
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500

    return send_file(io.BytesIO(audio), mimetype="audio/wav")


@app.route("/api/voice-command", methods=["POST"])
def api_voice_command():
    audio = request.files.get("audio")
    if audio is None:
        return error("Missing audio file 'audio'")

    try:
        wav_path = convert_to_wav(audio)
    except ValueError as e:
        return error(str(e))
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500

    try:
        heard = recognize(wav_path)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
    finally:
        remove_file(wav_path)

    tokens, ignored = parse_command(heard)
    if not tokens:
        return jsonify({"error": "Command not understood"}), 422

    return jsonify({"heard": heard, "tokens": tokens, "ignored": ignored}), 200


if __name__ == "__main__":
    # The calculator still works without sounds, so a speech error only prints a warning
    try:
        ensure_sounds()
    except RuntimeError as e:
        print(f"Warning: could not create sound files: {e}")

    app.run(host="127.0.0.1", port=5000, debug=True)
