"""Flask REST API for the library, with a voice interface on top.

The routes only translate HTTP requests into LibraryCollection method calls.
All rules (validation, ids, allowed state changes) live in custom_classes.py.
The voice routes turn a spoken sentence into a call to one of these same
REST routes (through app.test_client()), so they follow the same rules.
"""

import base64
import traceback
from urllib.parse import urlencode

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from speech_service import (
    FFMPEG,
    NoSpeechError,
    SpeechError,
    convert_to_wav,
    remove_file,
    synthesize,
    transcribe,
)
from voice_commands import build_message, parse_command

from custom_classes import (
    DVD,
    Book,
    ItemNotFoundError,
    ItemStateError,
    LibraryCollection,
)

app = Flask(__name__, static_folder="static", static_url_path="")
library = LibraryCollection()


def seed(collection):
    """Fill the collection with a few mixed items for testing."""
    collection.add_item(Book("The Great Gatsby", "F. Scott Fitzgerald", 180))
    inception_id = collection.add_item(DVD("Inception", "Christopher Nolan", 148))
    collection.add_item(Book("1984", "George Orwell", 328))
    collection.add_item(DVD("Arrival", "Denis Villeneuve", 116))
    # One item starts checked out so the 409 cases can be tried right away.
    collection.get_item(inception_id).checkout()


seed(library)


# ---------- Error translation: Python exceptions -> HTTP status codes ----------

@app.errorhandler(ValueError)
def handle_bad_request(error):
    """Invalid input -> 400."""
    return jsonify(error=str(error)), 400


@app.errorhandler(ItemNotFoundError)
def handle_not_found(error):
    """Unknown item id -> 404."""
    return jsonify(error=str(error)), 404


@app.errorhandler(ItemStateError)
def handle_conflict(error):
    """Action not allowed in the item's current state -> 409."""
    return jsonify(error=str(error)), 409


@app.errorhandler(HTTPException)
def handle_http_error(error):
    """Keep Flask's own errors (unknown URL, wrong method) in JSON too."""
    return jsonify(error=error.description), error.code


def read_json_body():
    """Return the request body as a dict, or raise ValueError."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object")
    return data


def parse_available(value):
    """Turn the ?available= query text into True, False or None."""
    if value is None:
        return None
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    raise ValueError("available must be true or false")


# ---------- Routes ----------

@app.get("/")
def index():
    """Serve the frontend page."""
    return app.send_static_file("index.html")


@app.post("/api/items")
def create_item():
    """Create a Book or DVD from the JSON body."""
    data = read_json_body()
    item_type = data.pop("type", None)
    item = library.create_item(item_type, **data)
    return jsonify(item.to_dict()), 201


@app.get("/api/items")
def list_items():
    """List items, optionally filtered with ?available= and ?type=."""
    available = parse_available(request.args.get("available"))
    item_type = request.args.get("type")
    if item_type is not None:
        item_type = item_type.lower()
    items = library.list_items(available=available, item_type=item_type)
    return jsonify([item.to_dict() for item in items]), 200


@app.get("/api/items/<int:item_id>")
def get_item(item_id):
    """Return one item."""
    return jsonify(library.get_item(item_id).to_dict()), 200


@app.put("/api/items/<int:item_id>")
def replace_item(item_id):
    """Replace all editable fields of an item."""
    item = library.replace_item(item_id, **read_json_body())
    return jsonify(item.to_dict()), 200


@app.patch("/api/items/<int:item_id>")
def update_item(item_id):
    """Change some editable fields of an item."""
    item = library.update_item(item_id, **read_json_body())
    return jsonify(item.to_dict()), 200


@app.delete("/api/items/<int:item_id>")
def delete_item(item_id):
    """Remove an item."""
    library.remove_item(item_id)
    return "", 204


@app.post("/api/items/<int:item_id>/checkout")
def checkout_item(item_id):
    """Check an item out."""
    item = library.get_item(item_id)
    message = item.checkout()
    return jsonify(message=message, item=item.to_dict()), 200


@app.post("/api/items/<int:item_id>/return")
def return_item(item_id):
    """Return a checked-out item."""
    item = library.get_item(item_id)
    message = item.return_item()
    return jsonify(message=message, item=item.to_dict()), 200


# ---------- Voice routes ----------

# Intents that act on one existing item; it is fetched first so the reply
# can mention its title (e.g. after a delete the item is gone).
ITEM_INTENTS = ("delete", "checkout", "return", "replace", "update")


def speak(text):
    """Return the spoken reply as base64 WAV, or None if speech synthesis fails."""
    try:
        return base64.b64encode(synthesize(text)).decode("ascii")
    except SpeechError as error:
        app.logger.warning("Text-to-speech failed: %s", error)
        return None


def voice_reply(transcript, command=None, api_call=None, status=None,
                result=None, message="", with_audio=True):
    """Build the JSON reply shared by both voice routes (always HTTP 200)."""
    return jsonify(
        transcript=transcript,
        command=command,
        api_call=api_call,
        status=status,
        result=result,
        message=message,
        audio=speak(message) if with_audio and message else None,
    ), 200


def handle_text_command(text, with_audio=True):
    """Parse a sentence, call the real REST route and describe the result."""
    command = parse_command(text)
    api_call = status = result = item = None

    if command["method"]:
        client = app.test_client()
        if command["intent"] in ITEM_INTENTS:
            before = client.get(f"/api/items/{command['item_id']}")
            if before.status_code == 200:
                item = before.get_json()

        response = client.open(
            command["path"],
            method=command["method"],
            json=command["body"] if command["body"] is not None else None,
            query_string=command["query"] or None,
        )
        status = response.status_code
        result = response.get_json(silent=True)
        api_call = f"{command['method']} {command['path']}"
        if command["query"]:
            api_call += "?" + urlencode(command["query"])

    message = build_message(command, status, result, item)
    return voice_reply(text, command, api_call, status, result, message, with_audio)


def current_phrases():
    """Return item titles and authors as hints for the speech recognizer."""
    phrases = []
    for item in library.list_items():
        phrases += [item.title, item.author]
    return phrases


@app.post("/api/voice/text")
def voice_text():
    """Run a typed command: JSON {"text": "..."}; {"speak": false} skips audio."""
    data = request.get_json(silent=True) or {}
    text = data.get("text")
    with_audio = data.get("speak", True) is not False
    if not isinstance(text, str) or not text.strip():
        return voice_reply("", status=400, message="Please type a command.",
                           with_audio=with_audio)
    return handle_text_command(text.strip(), with_audio)


@app.post("/api/voice")
def voice_audio():
    """Run a spoken command sent as multipart form field 'audio'."""
    audio = request.files.get("audio")
    if audio is None or not audio.filename:
        return voice_reply("", status=400, message="Please send a recording.")

    wav_path = None
    try:
        wav_path = convert_to_wav(audio)
        transcript = transcribe(wav_path, current_phrases())
    except NoSpeechError as error:
        app.logger.info("Nothing to recognize: %s", error)
        return voice_reply("", status=422, result={"error": str(error)},
                           message="I didn't hear anything. Please try again.")
    except SpeechError as error:
        app.logger.error("Speech recognition failed: %s", error)
        traceback.print_exc()
        return voice_reply("", status=500, result={"error": str(error)},
                           message="Sorry, speech recognition is not working right now.")
    finally:
        if wav_path:
            remove_file(wav_path)

    if not transcript:
        return voice_reply("", status=422,
                           message="I didn't hear anything. Please try again.")
    return handle_text_command(transcript)


if __name__ == "__main__":
    print(f" * ffmpeg: {FFMPEG or 'NOT FOUND - voice commands will fail'}")
    app.run(host="127.0.0.1", port=5000, debug=True)
