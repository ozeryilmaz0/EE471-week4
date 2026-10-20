import math

from flask import Flask, jsonify, request

from custom_classes import Calculator

app = Flask(__name__, static_folder="static", static_url_path="")

OPERATIONS = ("add", "subtract", "multiply", "divide")


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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
