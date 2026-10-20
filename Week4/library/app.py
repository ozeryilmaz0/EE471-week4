"""Flask REST API for the library.

The routes only translate HTTP requests into LibraryCollection method calls.
All rules (validation, ids, allowed state changes) live in custom_classes.py.
"""

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
