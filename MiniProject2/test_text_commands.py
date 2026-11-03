"""Send typed voice commands to /api/voice/text and check the API status codes.

Start the server first (fresh, because data lives in memory):
    venv\\Scripts\\python.exe -m flask --app app run --port 5000
Then run:
    venv\\Scripts\\python.exe test_text_commands.py
"""

import sys

import requests

BASE_URL = "http://127.0.0.1:5000"

# (command, expected status or intent). "{NEW}" is replaced with the id
# returned by the first create command.
TESTS = [
    ("list items", 200),
    ("list available books", 200),
    ("list magazines", 400),
    ("create item, type book, title The Catcher in the Rye, author J.D. Salinger, pages 220", 201),
    ("create item, type DVD, title Arrival, director Denis Villeneuve, duration 116", 201),
    ("get item {NEW}", 200),
    ("get item 99", 404),
    ("update item {NEW}, pages 250", 200),
    ("replace item {NEW}, title Franny and Zooey, author J.D. Salinger, pages 200", 200),
    ("replace item {NEW}, title Test", 400),
    ("check out item {NEW}", 200),
    ("borrow item {NEW}", 409),
    ("delete item {NEW}", 409),
    ("return item {NEW}", 200),
    ("give back item {NEW}", 409),
    ("delete item {NEW}", 204),
    ("delete item {NEW}", 404),
    ("help", "help"),
    ("sing me a song", "unknown"),
]


def run():
    new_id = None
    rows = []
    for template, expected in TESTS:
        text = template.replace("{NEW}", str(new_id))
        reply = requests.post(f"{BASE_URL}/api/voice/text", json={"text": text}, timeout=60)
        data = reply.json()
        intent = data["command"]["intent"]
        status = data["status"]

        if new_id is None and intent == "create" and status == 201:
            new_id = data["result"]["id"]

        actual = intent if isinstance(expected, str) else status
        # Every reply must be HTTP 200, have the expected status and come with audio.
        ok = reply.status_code == 200 and actual == expected and bool(data["audio"])
        if ok and expected == 201:
            # Names must reach the API unchanged, including the J.D. initials.
            ok = data["result"]["author"] in ("J.D. Salinger", "Denis Villeneuve")
        rows.append((text, expected, actual, data["api_call"] or "-",
                     data["message"], bool(data["audio"]), ok))

    print(f"First new ID after the seed: {new_id}\n")
    print(f"{'#':>2}  {'Command':<82} {'Expected':>8} {'Actual':>8}  {'Audio':<5} Result")
    print("-" * 120)
    for number, (text, expected, actual, api_call, message, audio, ok) in enumerate(rows, 1):
        print(f"{number:>2}  {text:<82} {str(expected):>8} {str(actual):>8}  "
              f"{'yes' if audio else 'no':<5} {'PASS' if ok else 'FAIL'}")
        print(f"    {api_call}  ->  {message}")

    failures = sum(not row[-1] for row in rows)
    print("-" * 120)
    print(f"{len(rows) - failures}/{len(rows)} passed")
    return failures == 0


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
