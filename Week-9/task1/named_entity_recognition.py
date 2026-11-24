"""Task 1.5 - Named entity recognition with pipeline().

aggregation_strategy="simple" groups the word pieces of one entity together.
The CoNLL-03 model knows PER, ORG, LOC and MISC. It has no separate "city" label,
so the city is the first LOC in the sentence (the sentence names the city before
the country); the other LOC entities are listed as countries / other locations.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rich.text import Text  # noqa: E402
from shared import get_pipeline, run_standalone, score_bar, stack, table  # noqa: E402

TITLE = "NAMED ENTITY RECOGNITION"
MODEL = "dbmdz/bert-large-cased-finetuned-conll03-english"
SENTENCE = ("I am Nate, a research assistant at Izmir Institute of Technology, and currently living "
            "and working in the beautiful city İzmir in Türkiye.")

COLOURS = {"PER": "bold cyan", "ORG": "bold yellow", "LOC": "bold green", "MISC": "bold magenta"}


def inputs():
    return [("Sentence", SENTENCE), ("Strategy", 'aggregation_strategy="simple"')]


def load():
    return get_pipeline("ner", MODEL)


def entity_text(entity: dict) -> str:
    """Take the entity from the original sentence (keeps 'İ' and 'ü' exactly as written)."""
    return SENTENCE[entity["start"]:entity["end"]]


def split_entities(entities: list[dict]) -> dict[str, list[str]]:
    """Return the person, organisation, city and other locations as separate lists."""
    per = [entity_text(e) for e in entities if e["entity_group"] == "PER"]
    org = [entity_text(e) for e in entities if e["entity_group"] == "ORG"]
    loc = [entity_text(e) for e in entities if e["entity_group"] == "LOC"]
    return {"Person": per, "Organization": org, "City": loc[:1], "Country / other location": loc[1:]}


def run(ner):
    entities = ner(SENTENCE, aggregation_strategy="simple")
    return {"entities": entities, "groups": split_entities(entities)}


def highlighted_sentence(entities: list[dict]) -> Text:
    text = Text()
    pos = 0
    for e in entities:
        text.append(SENTENCE[pos:e["start"]])
        text.append(f"{entity_text(e)}", style=f"{COLOURS.get(e['entity_group'], 'bold')} underline")
        text.append(f"[{e['entity_group']}]", style="dim")
        pos = e["end"]
    text.append(SENTENCE[pos:])
    return text


def render(result):
    entities = result["entities"]
    t = table("Entity", "Type", "Score", "Position")
    for e in entities:
        t.add_row(Text(entity_text(e), style=COLOURS.get(e["entity_group"], "bold")),
                  e["entity_group"], score_bar(float(e["score"]), 10), f"{e['start']}-{e['end']}")

    g = table("Extracted", "Value")
    for name, values in result["groups"].items():
        g.add_row(name, Text(", ".join(values) or "-", style="bold"))

    return stack(highlighted_sentence(entities), t, g)


if __name__ == "__main__":
    run_standalone(sys.modules[__name__])
