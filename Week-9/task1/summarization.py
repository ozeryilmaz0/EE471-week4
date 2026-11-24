"""Task 1.7 - Summarization with pipeline()."""

import re
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rich.text import Text  # noqa: E402
from shared import get_pipeline, run_standalone, stack  # noqa: E402

TITLE = "SUMMARIZATION"
MODEL = "sshleifer/distilbart-cnn-12-6"
TEXT = (
    "The 2008 Global Financial Crisis stands as the most severe economic collapse of the 21st century, "
    "often compared to the Great Depression of the 1930s. Triggered by the bursting of the United States "
    "housing bubble, its effects rippled across the globe, leading to the collapse of major financial "
    "institutions and a deep international recession. The crisis began with the subprime mortgage market. "
    "In the early 2000s, low interest rates and a push for homeownership led banks to issue high-risk "
    "loans to borrowers with poor credit."
)
MIN_LENGTH, MAX_LENGTH = 20, 60  # summary length in tokens


def inputs():
    return [("Text", TEXT), ("Words", str(len(TEXT.split())))]


def load():
    return get_pipeline("summarization", MODEL)


def run(summarizer):
    # The model's default is 4 beams; 2 beams give the same kind of summary about 2x faster on a CPU.
    out = summarizer(TEXT, min_length=MIN_LENGTH, max_length=MAX_LENGTH, num_beams=2, do_sample=False)
    # distilbart-cnn writes " ." (a space before punctuation); tidy that up.
    return re.sub(r"\s+([.,;:!?])", r"\1", " ".join(out[0]["summary_text"].split()))


def render(result):
    ratio = len(result.split()) / len(TEXT.split())
    return stack(Text("\n".join(textwrap.wrap(result, 100)), style="bold green"),
                 Text(f"{len(TEXT.split())} words  →  {len(result.split())} words "
                      f"({ratio:.0%} of the original)", style="dim"))


if __name__ == "__main__":
    run_standalone(sys.modules[__name__])
