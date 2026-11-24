"""Test all ten tabs of the running Gradio app with gradio_client.

Start the app first (task3/app.py), then run (from Week-9):
    ..\\venv\\Scripts\\python.exe task3\\test_app_client.py
Exit code 0 means every check passed.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Callable

from gradio_client import Client, handle_file

URL = "http://127.0.0.1:7860/"
ASSETS = Path(__file__).resolve().parents[1] / "assets"
NER_TEXT = ("I am Nate, a research assistant at Izmir Institute of Technology, and currently living "
            "and working in the beautiful city İzmir in Türkiye.")
CRISIS = (
    "The 2008 Global Financial Crisis stands as the most severe economic collapse of the 21st century, "
    "often compared to the Great Depression of the 1930s. Triggered by the bursting of the United States "
    "housing bubble, its effects rippled across the globe, leading to the collapse of major financial "
    "institutions and a deep international recession. The crisis began with the subprime mortgage market. "
    "In the early 2000s, low interest rates and a push for homeownership led banks to issue high-risk "
    "loans to borrowers with poor credit.")


def top_label(out: Any) -> str:
    return out["label"]


def gen_ok(out: str) -> bool:
    blocks = [b for b in out.split("\n\n") if b.strip()]
    texts = [b.split("\n")[0].split(") ", 1)[1] for b in blocks]
    return len(texts) == 2 and all(len(t.split()) <= 35 for t in texts)


# (name, api_name, args, check, short description of what is expected)
CASES: list[tuple[str, str, tuple, Callable[[Any], bool], str]] = [
    ("Sentiment", "/sentiment", ("I hate software courses",),
     lambda o: top_label(o) == "NEGATIVE", "NEGATIVE"),
    ("Zero-shot", "/zero_shot",
     ("Berkshire keeps their cash reserves at an extremely high level.",
      "finance, politics, sports, technology, education"),
     lambda o: top_label(o) == "finance", "finance first"),
    ("Text generation", "/text_generation",
     ("If I continue to complete all in-class exercises in this modern software practices course,", 35, 2),
     gen_ok, "2 alternatives, <= 35 words each"),
    ("Fill mask", "/fill_mask", ("To understand generative AI, one must study <mask> well.", 3),
     lambda o: len(o["confidences"]) == 3, "3 tokens"),
    ("NER", "/ner", (NER_TEXT,),
     lambda o: all(w in o[1] for w in ("Nate", "Izmir Institute of Technology", "İzmir", "Türkiye")),
     "Nate / Izmir Institute of Technology / İzmir / Türkiye"),
    ("Question answering", "/question_answering", (NER_TEXT, "In which city do I live?"),
     lambda o: o.startswith("İzmir"), "İzmir"),
    ("Summarization", "/summarization", (CRISIS,),
     lambda o: "2008" in o and len(o.split("\n\n")[0].split()) < 60, "short summary about 2008"),
    ("Translation", "/translation", ("Ce cours est produit par Hugging Face.",),
     lambda o: o.strip() == "This course is produced by Hugging Face.", "This course is produced by Hugging Face."),
    ("Image classification", "/image_classification", (handle_file(str(ASSETS / "tiger.jpg")),),
     lambda o: o["label"].startswith("tiger"), "tiger"),
    ("Speech recognition", "/speech_recognition", (handle_file(str(ASSETS / "speech.flac")),),
     lambda o: "hugging face pipelines" in o.lower() and "python code" in o.lower(),
     "Hugging Face pipelines ... Python code"),
]


def short(out: Any) -> str:
    if isinstance(out, dict) and "label" in out:
        conf = out.get("confidences") or []
        return ", ".join(f"{c['label']} {c['confidence']:.1%}" for c in conf[:3]) or out["label"]
    if isinstance(out, (list, tuple)):
        return " | ".join(short(o) for o in out[1:]) if len(out) > 1 else short(out[0])
    return " ".join(str(out).split())


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    client = Client(URL, verbose=False)
    failed = 0
    for i, (name, api, args, check, expected) in enumerate(CASES, 1):
        start = time.perf_counter()
        try:
            out = client.predict(*args, api_name=api)
            ok = bool(check(out))
            text = short(out)
        except Exception as exc:  # report and continue with the next tab
            ok, text = False, f"{type(exc).__name__}: {exc}"
        seconds = time.perf_counter() - start
        failed += not ok
        print(f"{i:2}. {'PASS' if ok else 'FAIL'}  {name:21} {seconds:5.2f} s  expected: {expected}")
        print(f"      got: {text[:160]}")
    print(f"\n{len(CASES) - failed}/{len(CASES)} tabs passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
