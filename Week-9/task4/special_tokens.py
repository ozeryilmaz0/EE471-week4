"""Task 4.5 - Special tokens: add_special_tokens=True vs False ([CLS] and [SEP])."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rich.text import Text  # noqa: E402
from shared import SPECIAL_STYLE, get_tokenizer, run_standalone, stack, table, token_chips  # noqa: E402

TITLE = "SPECIAL TOKENS"
MODEL = "bert-base-cased"
SENTENCE = "I hate software courses"


def inputs():
    return [("Sentence", SENTENCE), ("Compare", "add_special_tokens=True  vs  add_special_tokens=False")]


def load():
    return get_tokenizer(MODEL)


def run(tokenizer):
    out = {}
    for flag in (True, False):
        ids = tokenizer(SENTENCE, add_special_tokens=flag)["input_ids"]
        out[flag] = {"ids": ids, "tokens": tokenizer.convert_ids_to_tokens(ids), "text": tokenizer.decode(ids)}
    out["cls"] = (tokenizer.cls_token, tokenizer.cls_token_id)
    out["sep"] = (tokenizer.sep_token, tokenizer.sep_token_id)
    return out


def ids_text(ids: list[int], special: set[int]) -> Text:
    out = Text()
    for i, v in enumerate(ids):
        if i:
            out.append(", ")
        out.append(str(v), style=SPECIAL_STYLE if v in special else "cyan")
    return out


def render(result):
    special_ids = {result["cls"][1], result["sep"][1]}
    t = table("add_special_tokens", "Tokens", "input_ids", "decode()")
    for flag in (True, False):
        r = result[flag]
        t.add_row(Text(str(flag), style="bold green" if flag else "bold red"), token_chips(r["tokens"]),
                  ids_text(r["ids"], special_ids), Text(r["text"]))
    legend = Text()
    legend.append(f" {result['cls'][0]} ", style=SPECIAL_STYLE)
    legend.append(f" = id {result['cls'][1]}: start of the sequence (used for classification)    ")
    legend.append(f" {result['sep'][0]} ", style=SPECIAL_STYLE)
    legend.append(f" = id {result['sep'][1]}: end of a sentence / separator")
    return stack(t, legend)


if __name__ == "__main__":
    run_standalone(sys.modules[__name__])
