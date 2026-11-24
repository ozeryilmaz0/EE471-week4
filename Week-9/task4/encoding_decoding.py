"""Task 4.2 - Encoding and decoding: tokenize -> convert_tokens_to_ids -> decode."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rich.text import Text  # noqa: E402
from shared import get_tokenizer, run_standalone, stack, table, token_chips  # noqa: E402

TITLE = "ENCODING AND DECODING"
MODEL = "bert-base-cased"
SENTENCE = "Using a Transformer network is simple"


def inputs():
    return [("Sentence", SENTENCE), ("Tokenizer", "AutoTokenizer (WordPiece)")]


def load():
    return get_tokenizer(MODEL)


def run(tokenizer):
    tokens = tokenizer.tokenize(SENTENCE)
    ids = tokenizer.convert_tokens_to_ids(tokens)
    decoded = tokenizer.decode(ids)
    return {"tokens": tokens, "ids": ids, "decoded": decoded}


def render(result):
    t = table("Step", "Result")
    t.add_row("1. tokenize()", token_chips(result["tokens"]))
    t.add_row("2. convert_tokens_to_ids()", Text(str(result["ids"]), style="bold cyan"))
    t.add_row("3. decode()", Text(result["decoded"], style="bold green"))

    pairs = table(*[str(i) for i in range(len(result["tokens"]))], title="token → id")
    pairs.add_row(*[Text(tok, style="bold") for tok in result["tokens"]])
    pairs.add_row(*[Text(str(i), style="cyan") for i in result["ids"]])

    same = result["decoded"] == SENTENCE
    note = Text("decode(ids) == original sentence ✓" if same else "decoded text differs from the input",
                style="green" if same else "yellow")
    return stack(t, pairs, note)


if __name__ == "__main__":
    run_standalone(sys.modules[__name__])
