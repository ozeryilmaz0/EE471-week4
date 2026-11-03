"""Send the WAV files from test_audio/ to /api/voice and check the results.

Create the audio with make_test_audio.py, start a fresh server, then run:
    venv\\Scripts\\python.exe test_voice_audio.py
"""

import difflib
import os
import re
import sys

import requests

from make_test_audio import AUDIO_DIR, COMMANDS

BASE_URL = "http://127.0.0.1:5000"

# Expected API status and REST call for each file, on a freshly seeded server.
EXPECTED = {
    "01_list_available_books.wav": (200, "GET /api/items?available=true&type=book"),
    "02_tell_me_about_item_three.wav": (200, "GET /api/items/3"),
    "03_check_out_item_one.wav": (200, "POST /api/items/1/checkout"),
    "04_borrow_item_one.wav": (409, "POST /api/items/1/checkout"),
    "05_create_dvd.wav": (201, "POST /api/items"),
    "06_get_item_ninety_nine.wav": (404, "GET /api/items/99"),
}

NUMBER_WORDS = {"one": "1", "three": "3", "ninety nine": "99", "155": "155"}


def simplify(text):
    """Lowercase, drop punctuation and write numbers as digits for comparing."""
    text = text.lower().replace("checkout", "check out")
    for word, digits in NUMBER_WORDS.items():
        text = re.sub(rf"\b{word}\b", digits, text)
    return " ".join(re.findall(r"[a-z0-9]+", text))


def run():
    rows = []
    for name, sentence in COMMANDS.items():
        with open(os.path.join(AUDIO_DIR, name), "rb") as file:
            reply = requests.post(f"{BASE_URL}/api/voice",
                                  files={"audio": (name, file, "audio/wav")}, timeout=120)
        data = reply.json()
        expected_status, expected_call = EXPECTED[name]
        similarity = difflib.SequenceMatcher(
            None, simplify(sentence), simplify(data["transcript"])).ratio()
        ok = (reply.status_code == 200 and data["status"] == expected_status
              and data["api_call"] == expected_call and similarity >= 0.85
              and bool(data["audio"]))
        rows.append((name, data["transcript"], similarity, expected_status,
                     data["status"], data["api_call"], data["message"], ok))

    print(f"{'File':<34} {'Expected':>8} {'Actual':>6} {'Match':>6}  Result")
    print("-" * 120)
    for name, transcript, similarity, expected, actual, api_call, message, ok in rows:
        print(f"{name:<34} {expected:>8} {str(actual):>6} {similarity:>6.0%}  "
              f"{'PASS' if ok else 'FAIL'}")
        print(f"    heard: {transcript!r}")
        print(f"    {api_call}  ->  {message}")

    failures = sum(not row[-1] for row in rows)
    print("-" * 120)
    print(f"{len(rows) - failures}/{len(rows)} passed")
    return failures == 0


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
