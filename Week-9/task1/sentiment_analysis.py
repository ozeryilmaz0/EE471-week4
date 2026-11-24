"""Task 1.1 - Sentiment analysis with pipeline()."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared import get_pipeline, run_standalone, score_bar, table  # noqa: E402

TITLE = "SENTIMENT ANALYSIS"
MODEL = "distilbert-base-uncased-finetuned-sst-2-english"
SENTENCES = [
    "I've been waiting for a modern software practices course my whole life.",
    "I hate software courses",
]


def inputs():
    return [(f"Sentence {i}", s) for i, s in enumerate(SENTENCES, 1)]


def load():
    return get_pipeline("sentiment-analysis", MODEL)


def run(classifier):
    return classifier(SENTENCES)


def render(result):
    t = table("Sentence", "Label", "Score")
    for sentence, r in zip(SENTENCES, result):
        colour = "green" if r["label"] == "POSITIVE" else "red"
        t.add_row(sentence, f"[bold {colour}]{r['label']}[/]", score_bar(r["score"]))
    return t


if __name__ == "__main__":
    run_standalone(sys.modules[__name__])
