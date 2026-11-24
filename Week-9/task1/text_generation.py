"""Task 1.3 - Text generation with pipeline().

Two alternative completions are generated with a fixed seed, so every run gives
the same text. Each completion (prompt included) is cut to at most 35 words.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared import get_pipeline, run_standalone, table  # noqa: E402
from rich.text import Text  # noqa: E402
from transformers import set_seed  # noqa: E402

TITLE = "TEXT GENERATION"
MODEL = "gpt2"
PROMPT = "If I continue to complete all in-class exercises in this modern software practices course,"
MAX_WORDS = 35
NUM_SEQUENCES = 2
SEED = 42


def limit_words(text: str, max_words: int = MAX_WORDS) -> str:
    """Return ``text`` with at most ``max_words`` words.

    Whitespace is normalised first. If the cut leaves an unfinished sentence after the
    prompt, the text ends at the last full stop / ! / ? that comes after the prompt.
    """
    words = text.split()[:max_words]
    cut = " ".join(words)
    prompt_len = len(" ".join(PROMPT.split()))
    ends = [m.end() for m in re.finditer(r"[.!?](?=\s|$)", cut) if m.end() > prompt_len]
    if ends and len(words) == max_words:
        cut = cut[: ends[-1]]
    assert len(cut.split()) <= max_words
    return cut


def inputs():
    return [("Prompt", PROMPT),
            ("Settings", f"num_return_sequences={NUM_SEQUENCES}, max {MAX_WORDS} words, seed={SEED}")]


def load():
    return get_pipeline("text-generation", MODEL)


def run(generator):
    set_seed(SEED)
    # The prompt has 14 words, so 32 new tokens are always enough to reach the 35-word limit.
    outputs = generator(PROMPT, max_new_tokens=32, num_return_sequences=NUM_SEQUENCES,
                        do_sample=True, top_k=50, top_p=0.95,
                        pad_token_id=generator.tokenizer.eos_token_id)
    return [limit_words(o["generated_text"]) for o in outputs]


def render(result):
    t = table("#", "Generated text", "Words")
    for i, text in enumerate(result, 1):
        t.add_row(str(i), Text(PROMPT, style="bold") + Text(text[len(PROMPT):], style="green"),
                  str(len(text.split())))
    return t


if __name__ == "__main__":
    run_standalone(sys.modules[__name__])
