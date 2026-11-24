"""Task 1.4 - Mask filling with pipeline()."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rich.text import Text  # noqa: E402
from shared import get_pipeline, run_standalone, score_bar, table  # noqa: E402

TITLE = "FILL MASK"
MODEL = "distilroberta-base"
SENTENCE = "To understand generative AI, one must study <mask> well."
TOP_K = 3


def inputs():
    return [("Sentence", SENTENCE), ("top_k", str(TOP_K))]


def load():
    return get_pipeline("fill-mask", MODEL)


def run(unmasker):
    return unmasker(SENTENCE, top_k=TOP_K)


def render(result):
    t = table("Rank", "Token", "Completed sentence", "Score")
    for rank, r in enumerate(result, 1):
        word = r["token_str"].strip()
        before, after = SENTENCE.split("<mask>")
        sentence = Text(before) + Text(word, style="bold green") + Text(after)
        t.add_row(str(rank), Text(word, style="bold"), sentence, score_bar(r["score"], 12))
    return t


if __name__ == "__main__":
    run_standalone(sys.modules[__name__])
