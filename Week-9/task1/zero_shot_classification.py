"""Task 1.2 - Zero-shot classification with pipeline()."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared import get_pipeline, run_standalone, score_bar, table  # noqa: E402

TITLE = "ZERO-SHOT CLASSIFICATION"
MODEL = "facebook/bart-large-mnli"
SEQUENCE = "Berkshire keeps their cash reserves at an extremely high level."
LABELS = ["finance", "politics", "sports", "technology", "education"]


def inputs():
    return [("Sequence", SEQUENCE), ("Candidate labels", ", ".join(LABELS))]


def load():
    return get_pipeline("zero-shot-classification", MODEL)


def run(classifier):
    return classifier(SEQUENCE, candidate_labels=LABELS)


def render(result):
    t = table("Rank", "Label", "Score")
    for rank, (label, score) in enumerate(zip(result["labels"], result["scores"]), 1):
        style = "bold green" if rank == 1 else ""
        t.add_row(str(rank), f"[{style}]{label}[/]" if style else label, score_bar(score))
    return t


if __name__ == "__main__":
    run_standalone(sys.modules[__name__])
