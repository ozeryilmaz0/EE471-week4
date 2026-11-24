"""Task 1.6 - Question answering with pipeline().

The same sentence as the NER task is used as context. Every answer is compared with
the matching NER result (name -> Person, work -> Organization, city -> City) and
marked with a check or a cross.
"""

import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import named_entity_recognition as ner_task  # noqa: E402
from rich.text import Text  # noqa: E402
from shared import get_pipeline, run_standalone, score_bar, table  # noqa: E402

TITLE = "QUESTION ANSWERING"
MODEL = "distilbert-base-cased-distilled-squad"
CONTEXT = ner_task.SENTENCE
# question -> NER group that should contain the same answer
QUESTIONS = {
    "What is my name?": "Person",
    "Where do I work?": "Organization",
    "In which city do I live?": "City",
}


def inputs():
    return [("Context", CONTEXT)] + [(f"Question {i}", q) for i, q in enumerate(QUESTIONS, 1)]


def load():
    return get_pipeline("question-answering", MODEL), ner_task.load()


def normalise(text: str) -> str:
    """Lower-case, drop accents/dots (İzmir == Izmir) and punctuation at the ends."""
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.strip(" .,!?")


def same(answer: str, entities: list[str]) -> bool:
    a = normalise(answer)
    return any(a == normalise(e) or a in normalise(e) or normalise(e) in a for e in entities if e)


def run(models):
    qa, ner = models
    groups = ner_task.run(ner)["groups"]
    rows = []
    for question, group in QUESTIONS.items():
        answer = qa(question=question, context=CONTEXT)
        rows.append({"question": question, "answer": answer["answer"], "score": float(answer["score"]),
                     "ner_group": group, "ner_value": ", ".join(groups[group]),
                     "match": same(answer["answer"], groups[group])})
    return rows


def render(result):
    t = table("Question", "QA answer", "Score", "NER result", "Match")
    for r in result:
        mark = Text("✓", style="bold green") if r["match"] else Text("✗", style="bold red")
        t.add_row(r["question"], Text(r["answer"], style="bold"), score_bar(r["score"], 10),
                  Text(f"{r['ner_value'] or '-'} ({r['ner_group']})"), mark)
    return t


if __name__ == "__main__":
    run_standalone(sys.modules[__name__])
