"""Task 1.8 - Translation (French -> English) with pipeline()."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rich.text import Text  # noqa: E402
from shared import get_pipeline, run_standalone, table  # noqa: E402

TITLE = "TRANSLATION"
MODEL = "Helsinki-NLP/opus-mt-fr-en"
SOURCE = "Ce cours est produit par Hugging Face."


def inputs():
    return [("French", SOURCE)]


def load():
    return get_pipeline("translation", MODEL)


def run(translator):
    return translator(SOURCE)[0]["translation_text"]


def render(result):
    t = table("Language", "Text")
    t.add_row("French (input)", Text(SOURCE))
    t.add_row("English (output)", Text(result, style="bold green"))
    return t


if __name__ == "__main__":
    run_standalone(sys.modules[__name__])
