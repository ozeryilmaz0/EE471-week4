"""Send the Task 1 test recordings to /api/voice-command and print the results.

Start the app first (python app.py), then run: python test_voice_command.py
"""

import os
import sys

import requests

URL = "http://127.0.0.1:5000/api/voice-command"

TEST_AUDIO_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "Week-5-Task-1", "test_audio"
)

FILES = (
    "five_plus_two.wav",
    "seven_minus_three.wav",
    "three_times_two.wav",
    "nine_over_three.wav",
)


# Upload one WAV file and print what the server understood
def send_file(filename):
    path = os.path.join(TEST_AUDIO_DIR, filename)
    print(filename)

    if not os.path.exists(path):
        print(f"  error:   file not found: {os.path.normpath(path)}")
        return

    with open(path, "rb") as f:
        try:
            response = requests.post(URL, files={"audio": (filename, f, "audio/wav")}, timeout=60)
        except requests.ConnectionError:
            print(f"  error:   could not connect to {URL}. Is the app running?")
            return

    try:
        data = response.json()
    except ValueError:
        print(f"  error:   HTTP {response.status_code}, response is not JSON")
        return

    if not response.ok:
        print(f"  error:   HTTP {response.status_code}: {data.get('error')}")
        return

    print(f"  heard:   {data['heard']}")
    print(f"  tokens:  {' '.join(data['tokens'])}")
    print(f"  ignored: {', '.join(data['ignored']) or '-'}")


if __name__ == "__main__":
    # Tokens such as "÷" and "−" fail on the default Windows code page when output is redirected
    sys.stdout.reconfigure(encoding="utf-8")

    for filename in FILES:
        send_file(filename)
        print()
