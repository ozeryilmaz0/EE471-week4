"""Task 4.3 - Padding: two sentences of different length in one batch (padding=True)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rich.text import Text  # noqa: E402
from shared import PAD_STYLE, SPECIAL_STYLE, get_tokenizer, run_standalone, stack, table  # noqa: E402

TITLE = "PADDING"
MODEL = "bert-base-cased"
SENTENCES = [
    "I've been waiting for a modern software practices course my whole life.",
    "I hate software courses",
]


def inputs():
    return [(f"Sentence {i}", s) for i, s in enumerate(SENTENCES, 1)] + [("Call", "tokenizer(sentences, padding=True)")]


def load():
    return get_tokenizer(MODEL)


def run(tokenizer):
    batch = tokenizer(SENTENCES, padding=True)
    rows = []
    for ids, mask in zip(batch["input_ids"], batch["attention_mask"]):
        rows.append({"tokens": tokenizer.convert_ids_to_tokens(ids), "ids": ids, "mask": mask})
    return {"rows": rows, "length": len(batch["input_ids"][0]), "pad_id": tokenizer.pad_token_id}


def cell(value, token: str) -> Text:
    if token == "[PAD]":
        return Text(str(value), style=PAD_STYLE)
    if token in ("[CLS]", "[SEP]"):
        return Text(str(value), style=SPECIAL_STYLE)
    return Text(str(value))


def render(result):
    n = result["length"]
    t = table("", *[str(i) for i in range(n)], title=f"Aligned batch (every row has {n} positions)",
              show_lines=False, padding=(0, 0))
    for c in t.columns[1:]:
        c.justify = "center"
    for i, r in enumerate(result["rows"], 1):
        t.add_row(Text(f"S{i} token", style="bold magenta"), *[cell(tok, tok) for tok in r["tokens"]])
        t.add_row(Text(f"S{i} input_ids", style="bold cyan"),
                  *[cell(v, tok) for v, tok in zip(r["ids"], r["tokens"])])
        t.add_row(Text(f"S{i} attention_mask", style="bold green"),
                  *[Text(str(m), style="bold red" if m == 0 else "green") for m in r["mask"]],
                  end_section=i < len(result["rows"]))
    pads = sum(r["mask"].count(0) for r in result["rows"])
    note = Text(f"{pads} [PAD] tokens (id {result['pad_id']}) were added to the shorter sentence; "
                "attention_mask = 0 tells the model to ignore them.", style="dim")
    return stack(t, note)


if __name__ == "__main__":
    run_standalone(sys.modules[__name__])
