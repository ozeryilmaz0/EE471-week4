"""Recording helper: run the 22 MediaPipe demos one after another for one long screen recording.

For each demo it clears the terminal, shows a big title such as "3/22  TEXT-TO-SPEECH",
waits for Enter, runs the demo and then waits for Enter again.

The local time at which every title appears is saved in demo_timestamps.json,
so the long video can later be cut into 22 parts (audio_classifier.avi, ...).

Usage (from Week-8):
    .venv\\Scripts\\python.exe task1\\run_all_demos.py            # all 22 demos
    .venv\\Scripts\\python.exe task1\\run_all_demos.py --start 7  # continue from demo 7
    .venv\\Scripts\\python.exe task1\\run_all_demos.py --auto     # no Enter key needed (test run)
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
TIMESTAMPS = HERE / "demo_timestamps.json"

# Same order as in the assignment PDF.
DEMOS = [
    ("audio_classifier", "AUDIO CLASSIFIER"),
    ("audio_transcriber", "AUDIO TRANSCRIBER"),
    ("text_to_speech", "TEXT-TO-SPEECH"),
    ("decision_maker", "DECISION MAKER"),
    ("semantic_retriever", "SEMANTIC RETRIEVER"),
    ("universal_embedder", "UNIVERSAL EMBEDDER"),
    ("language_detector", "LANGUAGE DETECTOR"),
    ("text_classifier", "TEXT CLASSIFIER"),
    ("text_embedder", "TEXT EMBEDDER"),
    ("text_proofreader", "TEXT PROOFREADER"),
    ("text_summarizer", "TEXT SUMMARIZER"),
    ("face_detector", "FACE DETECTOR"),
    ("face_landmarker", "FACE LANDMARKER"),
    ("gesture_recognizer", "GESTURE RECOGNIZER"),
    ("hand_landmarker", "HAND LANDMARKER"),
    ("holistic_landmarker", "HOLISTIC LANDMARKER"),
    ("image_classifier", "IMAGE CLASSIFIER"),
    ("image_embedder", "IMAGE EMBEDDER"),
    ("image_segmenter", "IMAGE SEGMENTER"),
    ("interactive_segmenter", "INTERACTIVE SEGMENTER"),
    ("object_detector", "OBJECT DETECTOR"),
    ("pose_landmarker", "POSE LANDMARKER"),
]

# Native (C++) log lines from MediaPipe / LiteRT. They are hidden so the video stays readable.
# Python errors and "ERROR:" / "E0000" lines are still shown.
NOISE = re.compile(
    r"^(INFO|WARNING): |^[IW]\d{4} |^WARNING: All log messages before absl|"
    r"^All log messages before absl"
)

# A small 5-line block font for the big titles.
FONT = {
    "A": [" ### ", "#   #", "#####", "#   #", "#   #"], "B": ["#### ", "#   #", "#### ", "#   #", "#### "],
    "C": [" ####", "#    ", "#    ", "#    ", " ####"], "D": ["#### ", "#   #", "#   #", "#   #", "#### "],
    "E": ["#####", "#    ", "#### ", "#    ", "#####"], "F": ["#####", "#    ", "#### ", "#    ", "#    "],
    "G": [" ####", "#    ", "#  ##", "#   #", " ####"], "H": ["#   #", "#   #", "#####", "#   #", "#   #"],
    "I": ["#####", "  #  ", "  #  ", "  #  ", "#####"], "J": ["#####", "   # ", "   # ", "#  # ", " ##  "],
    "K": ["#   #", "#  # ", "###  ", "#  # ", "#   #"], "L": ["#    ", "#    ", "#    ", "#    ", "#####"],
    "M": ["#   #", "## ##", "# # #", "#   #", "#   #"], "N": ["#   #", "##  #", "# # #", "#  ##", "#   #"],
    "O": [" ### ", "#   #", "#   #", "#   #", " ### "], "P": ["#### ", "#   #", "#### ", "#    ", "#    "],
    "Q": [" ### ", "#   #", "# # #", "#  # ", " ## #"], "R": ["#### ", "#   #", "#### ", "#  # ", "#   #"],
    "S": [" ####", "#    ", " ### ", "    #", "#### "], "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  "],
    "U": ["#   #", "#   #", "#   #", "#   #", " ### "], "V": ["#   #", "#   #", "#   #", " # # ", "  #  "],
    "W": ["#   #", "#   #", "# # #", "## ##", "#   #"], "X": ["#   #", " # # ", "  #  ", " # # ", "#   #"],
    "Y": ["#   #", " # # ", "  #  ", "  #  ", "  #  "], "Z": ["#####", "   # ", "  #  ", " #   ", "#####"],
    "0": [" ### ", "#  ##", "# # #", "##  #", " ### "], "1": ["  #  ", " ##  ", "  #  ", "  #  ", " ### "],
    "2": [" ### ", "#   #", "  ## ", " #   ", "#####"], "3": ["#### ", "    #", " ### ", "    #", "#### "],
    "4": ["#   #", "#   #", "#####", "    #", "    #"], "5": ["#####", "#    ", "#### ", "    #", "#### "],
    "6": [" ### ", "#    ", "#### ", "#   #", " ### "], "7": ["#####", "    #", "   # ", "  #  ", "  #  "],
    "8": [" ### ", "#   #", " ### ", "#   #", " ### "], "9": [" ### ", "#   #", " ####", "    #", " ### "],
    "/": ["    #", "   # ", "  #  ", " #   ", "#    "], "-": ["     ", "     ", "#####", "     ", "     "],
    " ": ["   ", "   ", "   ", "   ", "   "],
}

CYAN, YELLOW, GREEN, RESET = "\033[96m", "\033[93m", "\033[92m", "\033[0m"


def big(text):
    """Return text drawn with the block font (5 lines)."""
    rows = ["", "", "", "", ""]
    for ch in text.upper():
        glyph = FONT.get(ch, FONT[" "])
        for i in range(5):
            rows[i] += glyph[i].replace("#", "█") + " "
    return "\n".join(rows)


def show_title(index, title):
    os.system("cls" if os.name == "nt" else "clear")
    print("\n" + CYAN + big(f"{index}/{len(DEMOS)}") + RESET + "\n")
    # Long titles are split over two lines so they fit in a normal terminal.
    words = title.split()
    lines = [title] if len(title) <= 14 else [" ".join(words[:-1]), words[-1]]
    for line in lines:
        print(YELLOW + big(line) + RESET + "\n")
    print(f"   {title.lower()}  ->  task1/{DEMOS[index - 1][0]}.py\n")


def save(data):
    TIMESTAMPS.write_text(json.dumps(data, indent=2), encoding="utf-8")


def run_demo(script):
    """Run one demo, hiding native log noise, and return its exit code."""
    env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
    proc = subprocess.Popen([sys.executable, str(HERE / f"{script}.py")], cwd=HERE, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", bufsize=1)
    for line in proc.stdout:
        if not NOISE.search(line):
            print(line, end="", flush=True)
    return proc.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", type=int, default=1, help="number of the first demo to run (1-22)")
    parser.add_argument("--auto", action="store_true", help="do not wait for Enter (test run)")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # block characters in any terminal
    os.system("")  # enables ANSI colours in the Windows console

    wait = (lambda msg: print(msg)) if args.auto else (lambda msg: input(msg))

    data = {"created": datetime.now().isoformat(timespec="seconds"), "demos": []}
    if args.start > 1 and TIMESTAMPS.exists():  # keep the earlier entries when resuming
        old = json.loads(TIMESTAMPS.read_text(encoding="utf-8"))
        data["demos"] = [d for d in old.get("demos", []) if d["index"] < args.start]

    failed = []
    for index in range(args.start, len(DEMOS) + 1):
        script, title = DEMOS[index - 1]
        show_title(index, title)
        data["demos"].append({
            "index": index,
            "script": f"{script}.py",
            "video": f"{script}.avi",
            "title": title,
            "title_shown_at": datetime.now().isoformat(timespec="seconds"),
        })
        save(data)
        wait(GREEN + "   Press Enter to run the demo ..." + RESET)
        print()
        code = run_demo(script)
        data["demos"][-1]["finished_at"] = datetime.now().isoformat(timespec="seconds")
        data["demos"][-1]["exit_code"] = code
        save(data)
        if code != 0:
            failed.append(script)
            print(f"\n   !!! {script}.py exited with code {code}")
        wait(GREEN + f"\n   [{index}/{len(DEMOS)} done]  Press Enter for next ..." + RESET)

    data["ended_at"] = datetime.now().isoformat(timespec="seconds")
    save(data)
    os.system("cls" if os.name == "nt" else "clear")
    print("\n" + GREEN + big("DONE") + RESET + "\n")
    print(f"   Timestamps saved to {TIMESTAMPS}")
    if failed:
        print("   Failed demos:", ", ".join(failed))
        sys.exit(1)


if __name__ == "__main__":
    main()
