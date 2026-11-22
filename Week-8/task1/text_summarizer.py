"""Text Summarizer: summarize a paragraph with the on-device Summarization 200M model."""

import textwrap

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.text import TextSummarizer, TextSummarizerMode, TextSummarizerOptions

import common

common.header("TEXT SUMMARIZER",
              "Model: Summarization 200M (Gemma Terms of Use)  |  Input: assets/summarizer.txt")

text = common.read_text("summarizer.txt")
common.section(f"Input text ({len(text.split())} words)")
print(textwrap.fill(text, 90, initial_indent="  ", subsequent_indent="  "))

model_path = common.model("summarization_quant_200m_2modes.litertlm")
for mode in (TextSummarizerMode.TLDR, TextSummarizerMode.KEYPOINTS):
    options = TextSummarizerOptions(base_options=BaseOptions(model_asset_path=model_path), mode=mode)
    with TextSummarizer.create_from_options(options) as summarizer:
        result = summarizer.summarize(text)
    common.section(f"Summary, mode {mode.name}")
    for line in result.summary.strip().splitlines():
        print(textwrap.fill(line, 90, initial_indent="  ", subsequent_indent="    "))
common.done()
