"""Text Proofreader: fix spelling and grammar with the on-device Proofread 200M model."""

import difflib

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.text import TextProofreader, TextProofreaderOptions

import common

common.header("TEXT PROOFREADER",
              "Model: Proofread 200M (Gemma Terms of Use)  |  Input: assets/proofreader.txt")

text = common.read_text("proofreader.txt")
options = TextProofreaderOptions(base_options=BaseOptions(model_asset_path=common.model("proofread_quant_200m.litertlm")))
with TextProofreader.create_from_options(options) as proofreader:
    result = proofreader.proofread(text)

common.section("Result")
print(f"  Before: {text}")
print(f"  After : {result.proofread_text.strip()}")

# The model returns character-level corrections; show them as word-level changes.
common.section("Corrected words")
before, after = text.split(), result.proofread_text.split()
matcher = difflib.SequenceMatcher(a=before, b=after)
for op, a1, a2, b1, b2 in matcher.get_opcodes():
    if op != "equal":
        print(f"  {' '.join(before[a1:a2]) or '(nothing)':>20}  ->  {' '.join(after[b1:b2]) or '(removed)'}")
print(f"\n  The model returned {len(result.corrections)} character-level edit blocks.")
common.done()
