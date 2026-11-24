"""Gradio web app: one tab per Hugging Face task, built on hf_tasks.HFToolkit.

Every tab is a gr.Interface (inputs, Clear / Submit buttons, output box and examples
taken from the assignment). All ten models are loaded and warmed up before the
server starts, so no request has to wait for a model.

Usage (from Week-9):
    ..\\venv\\Scripts\\python.exe task3\\app.py
then open http://127.0.0.1:7860
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Callable

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
sys.path.insert(0, str(Path(__file__).resolve().parent))

# hf_tasks sets HF_HUB_OFFLINE before huggingface_hub is imported, so import it before gradio.
from hf_tasks import ASSETS, HFToolkit  # noqa: E402, I001
import gradio as gr  # noqa: E402

HOST, PORT = "127.0.0.1", 7860

kit = HFToolkit()

NER_TEXT = kit["ner"].example["text"]
CRISIS_TEXT = kit["summarization"].example["text"]
LABELS = ", ".join(kit["zero_shot"].example["labels"])


def safe(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Show input problems as a friendly Gradio error instead of a stack trace."""
    def wrapper(*args: Any) -> Any:
        try:
            return fn(*args)
        except ValueError as exc:
            raise gr.Error(str(exc)) from exc
    wrapper.__name__ = fn.__name__
    return wrapper


# ------------------------------------------------------------- tab functions
@safe
def sentiment(text: str) -> dict[str, float]:
    return kit.run("sentiment", text)


@safe
def zero_shot(text: str, labels: str) -> dict[str, float]:
    return kit.run("zero_shot", text, labels)


@safe
def text_generation(prompt: str, max_words: float, alternatives: float) -> str:
    texts = kit.run("text_generation", prompt, max_words=int(max_words), num_sequences=int(alternatives))
    return "\n\n".join(f"{i}) {t}\n   ({len(t.split())} words)" for i, t in enumerate(texts, 1))


@safe
def fill_mask(text: str, top_k: float) -> dict[str, float]:
    return kit.run("fill_mask", text, top_k=int(top_k))


@safe
def ner(text: str) -> tuple[dict[str, Any], str]:
    entities = kit.run("ner", text)
    highlighted = {"text": text, "entities": [
        {"entity": e["entity_group"], "start": e["start"], "end": e["end"]} for e in entities]}
    names = {"PER": "Person", "ORG": "Organization", "LOC": "Location", "MISC": "Misc"}
    lines = [f"{names.get(e['entity_group'], e['entity_group']):<13} {e['word']}  ({e['score']:.1%})"
             for e in entities]
    return highlighted, "\n".join(lines) or "No entities found."


@safe
def question_answering(context: str, question: str) -> str:
    out = kit.run("qa", question, context)
    return f"{out['answer']}\n\n(score {out['score']:.1%}, characters {out['start']}-{out['end']})"


@safe
def summarization(text: str) -> str:
    summary = kit.run("summarization", text)
    return f"{summary}\n\n({len(text.split())} words → {len(summary.split())} words)"


@safe
def translation(text: str) -> str:
    return kit.run("translation", text)


@safe
def image_classification(image: str | None) -> dict[str, float]:
    return kit.run("image", image, top_k=3)


@safe
def speech_recognition(audio: str | None) -> str:
    return kit.run("asr", audio)


# ------------------------------------------------------------------- the UI
def model_note(key: str) -> str:
    task = kit[key]
    return f"**Model:** `{task.model_name}` · **pipeline:** `{task.task}` · **device:** `{task.device}`"


def build_demo() -> gr.Blocks:
    text = lambda label, lines=2, value=None: gr.Textbox(label=label, lines=lines, value=value)  # noqa: E731
    common = {"flagging_mode": "never"}

    tabs = {
        "Sentiment": gr.Interface(
            sentiment, text("Text"), gr.Label(label="Sentiment"),
            examples=[["I've been waiting for a modern software practices course my whole life."],
                      ["I hate software courses"]],
            description=model_note("sentiment"), api_name="sentiment", **common),
        "Zero-shot": gr.Interface(
            zero_shot, [text("Text"), text("Candidate labels (comma separated)", 1)],
            gr.Label(label="Scores"),
            examples=[["Berkshire keeps their cash reserves at an extremely high level.", LABELS]],
            description=model_note("zero_shot"), api_name="zero_shot", **common),
        "Text generation": gr.Interface(
            text_generation,
            [text("Prompt", 3), gr.Slider(5, 35, value=35, step=1, label="Max words per alternative"),
             gr.Slider(1, 3, value=2, step=1, label="Number of alternatives")],
            gr.Textbox(label="Generated text", lines=8),
            examples=[["If I continue to complete all in-class exercises in this modern software practices course,",
                       35, 2]],
            description=model_note("text_generation") + " · fixed seed 42, at most 35 words",
            api_name="text_generation", **common),
        "Fill mask": gr.Interface(
            fill_mask, [text("Text with <mask>"), gr.Slider(1, 10, value=3, step=1, label="top_k")],
            gr.Label(label="Best tokens"),
            examples=[["To understand generative AI, one must study <mask> well.", 3]],
            description=model_note("fill_mask"), api_name="fill_mask", **common),
        "NER": gr.Interface(
            ner, text("Text", 3),
            [gr.HighlightedText(label="Entities", combine_adjacent=False), gr.Textbox(label="Entity list", lines=5)],
            examples=[[NER_TEXT]],
            description=model_note("ner") + ' · aggregation_strategy="simple"', api_name="ner", **common),
        "Question answering": gr.Interface(
            question_answering, [text("Context", 4), text("Question", 1)], gr.Textbox(label="Answer", lines=3),
            examples=[[NER_TEXT, "What is my name?"], [NER_TEXT, "Where do I work?"],
                      [NER_TEXT, "In which city do I live?"]],
            description=model_note("qa"), api_name="question_answering", **common),
        "Summarization": gr.Interface(
            summarization, text("Text", 8), gr.Textbox(label="Summary", lines=6),
            examples=[[CRISIS_TEXT]],
            description=model_note("summarization"), api_name="summarization", **common),
        "Translation": gr.Interface(
            translation, text("French text"), gr.Textbox(label="English translation", lines=2),
            examples=[["Ce cours est produit par Hugging Face."]],
            description=model_note("translation"), api_name="translation", **common),
        "Image classification": gr.Interface(
            image_classification, gr.Image(type="filepath", label="Image", height=320),
            gr.Label(num_top_classes=3, label="Top-3 classes"),
            examples=[[str(ASSETS / "tiger.jpg")]],
            description=model_note("image"), api_name="image_classification", **common),
        "Speech recognition": gr.Interface(
            speech_recognition,
            gr.Audio(sources=["upload", "microphone"], type="filepath", label="Audio (upload or record)"),
            gr.Textbox(label="Transcription", lines=3),
            examples=[[str(ASSETS / "speech.flac")]],
            description=model_note("asr"), api_name="speech_recognition", **common),
    }
    return gr.TabbedInterface(list(tabs.values()), list(tabs.keys()),
                              title="Week 9 · Hugging Face Pipelines (Task 3)")


def main() -> None:
    print("Loading the models ...", flush=True)
    start = time.perf_counter()
    kit.load_all()
    print("Warming up ...", flush=True)
    kit.warm_up_all()
    print(f"All {len(kit)} models ready in {time.perf_counter() - start:.0f} s", flush=True)
    print(kit.describe(), flush=True)
    demo = build_demo()
    demo.queue().launch(server_name=HOST, server_port=PORT, allowed_paths=[str(ASSETS)],
                        show_api=True, inbrowser=False)


if __name__ == "__main__":
    main()
