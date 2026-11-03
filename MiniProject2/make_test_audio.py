"""Create spoken test commands in test_audio/ with Azure text-to-speech.

Run:
    venv\\Scripts\\python.exe make_test_audio.py
"""

import os

from speech_service import synthesize

AUDIO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_audio")

# file name -> sentence. test_voice_audio.py sends them in this order.
COMMANDS = {
    "01_list_available_books.wav": "List available books.",
    "02_tell_me_about_item_three.wav": "Tell me about item three.",
    "03_check_out_item_one.wav": "Check out item one.",
    "04_borrow_item_one.wav": "Borrow item one.",
    "05_create_dvd.wav": "Create item, type DVD, title Dune, director Denis Villeneuve, duration 155.",
    "06_get_item_ninety_nine.wav": "Get item ninety nine.",
}


def main():
    os.makedirs(AUDIO_DIR, exist_ok=True)
    for name, sentence in COMMANDS.items():
        path = os.path.join(AUDIO_DIR, name)
        with open(path, "wb") as file:
            file.write(synthesize(sentence))
        print(f"Created {path}  <- {sentence!r}")


if __name__ == "__main__":
    main()
