"""Decision Maker: answer choice and yes/no questions about text with an on-device embedding model."""

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.decision import (BooleanQuestion, ChoiceQuestion, DecisionMaker,
                                             DecisionMakerOptions)

import common

common.header("DECISION MAKER",
              "Model: EmbeddingGemma 2 text 270M (Apache-2.0)  |  Input: 3 customer messages")

# Three support messages. The app must decide how to route each one.
messages = [
    "My card was charged twice for the same order. Please refund me today!",
    "How do I change the language of the app to Turkish?",
    "The app crashes every time I open the camera page on my phone.",
]

questions = {
    # Pick one of several labels, each described in plain words.
    "department": ChoiceQuestion(criteria={
        "billing": "The message is about payments, charges, invoices or refunds.",
        "technical": "The message reports a bug, a crash or something that does not work.",
        "how_to": "The message asks how to use a feature or change a setting.",
    }),
    # Yes/no question. An embedding model gives low absolute probabilities,
    # so the threshold is lowered from the default 0.5 to 0.2.
    "urgent": BooleanQuestion(condition="The customer needs action today or right now.", threshold=0.2),
}

options = DecisionMakerOptions(
    base_options=BaseOptions(model_asset_path=common.model("embeddinggemma-2-text-270m.litertlm")))
print("Loading the model ...")
with DecisionMaker.create_from_options(options) as maker:
    results = maker.evaluate_batch(contexts=messages, questions=questions)

for msg, res in zip(messages, results):
    common.section(f"\"{msg}\"")
    dep = res["department"]
    probs = ", ".join(f"{k} {p:.2f}" for k, p in sorted(dep.probabilities.items(), key=lambda kv: -kv[1]))
    print(f"  department : {dep.selected_key:<10} ({probs})")
    urg = res["urgent"]
    print(f"  urgent     : {str(urg.value):<10} (P(true) = {urg.probability_true:.2f}, threshold 0.20)")
common.done()
