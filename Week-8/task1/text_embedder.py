"""Text Embedder: turn sentences into vectors and compare their meaning with cosine similarity."""

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.text import TextEmbedder, TextEmbedderOptions

import common

common.header("TEXT EMBEDDER", "Model: Universal Sentence Encoder  |  Input: 4 sentences")

anchor = "The weather is lovely today."
others = [
    "It is a sunny and beautiful day.",
    "Today the sky is clear and warm.",
    "I need to fix a bug in my Python code.",
]
options = TextEmbedderOptions(
    base_options=BaseOptions(model_asset_path=common.model("universal_sentence_encoder.tflite")))

with TextEmbedder.create_from_options(options) as embedder:
    a = embedder.embed(anchor).embeddings[0]
    print(f"Each sentence becomes a vector of {len(a.embedding)} numbers.")
    common.section(f"Similarity to: \"{anchor}\"")
    for s in others:
        sim = TextEmbedder.cosine_similarity(a, embedder.embed(s).embeddings[0])
        bar = "#" * max(0, int(sim * 30))
        print(f"  {sim:6.3f} {bar:<30} \"{s}\"")
print("\nHigher value = closer meaning. The two weather sentences score much higher than the bug sentence.")
common.done()
