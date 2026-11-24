"""Task 4.4 - Truncation: a long sentence cut to max_length=8 tokens (truncation=True)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rich.text import Text  # noqa: E402
from shared import get_tokenizer, run_standalone, table, token_chips  # noqa: E402

TITLE = "TRUNCATION"
MODEL = "bert-base-cased"
SENTENCE = ("Hugging Face Transformers gives us thousands of pretrained models for text, "
            "vision and audio tasks in just a few lines of code.")
MAX_LENGTH = 8


def inputs():
    return [("Sentence", SENTENCE), ("Call", f"tokenizer(sentence, truncation=True, max_length={MAX_LENGTH})")]


def load():
    return get_tokenizer(MODEL)


def run(tokenizer):
    before = tokenizer(SENTENCE)["input_ids"]
    after = tokenizer(SENTENCE, truncation=True, max_length=MAX_LENGTH)["input_ids"]
    return {
        "before": {"ids": before, "tokens": tokenizer.convert_ids_to_tokens(before), "text": tokenizer.decode(before)},
        "after": {"ids": after, "tokens": tokenizer.convert_ids_to_tokens(after), "text": tokenizer.decode(after)},
    }


def render(result):
    t = table("", "Tokens", "Length", "decode()")
    for name, style in (("before", "yellow"), ("after", "green")):
        r = result[name]
        label = "Before (no truncation)" if name == "before" else f"After (max_length={MAX_LENGTH})"
        t.add_row(Text(label, style=f"bold {style}"), token_chips(r["tokens"]),
                  Text(str(len(r["ids"])), style=f"bold {style}"), Text(r["text"]))
    return t


if __name__ == "__main__":
    run_standalone(sys.modules[__name__])
