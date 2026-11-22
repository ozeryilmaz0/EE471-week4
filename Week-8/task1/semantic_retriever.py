"""Semantic Retriever: store documents in a local vector database and search them by meaning."""

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.retrieval import (SemanticRetriever, SemanticRetrieverOptions,
                                              UniversalEmbedder, UniversalEmbedderOptions)

import common

common.header("SEMANTIC RETRIEVER",
              "Model: EmbeddingGemma 2 text 270M (Apache-2.0)  |  Input: 6 short notes + 3 questions")

documents = {
    "pose": "The Pose Landmarker finds 33 body points such as shoulders, elbows and wrists.",
    "face": "The Face Landmarker gives 478 face points and the head rotation matrix.",
    "audio": "YAMNet can tell apart speech, music, dogs barking and many other sounds.",
    "cog": "Cog packs a machine learning model into a Docker image with an HTTP API.",
    "pizza": "Preheat the oven to 250 degrees and bake the pizza for ten minutes.",
    "weather": "Tomorrow in Izmir it will be sunny with a light wind from the sea.",
}
queries = [
    "Which tool tells me if someone raised their arm?",
    "How do I put my model in a container?",
    "Will it rain tomorrow?",
]

embedder_options = UniversalEmbedderOptions(
    base_options=BaseOptions(model_asset_path=common.model("embeddinggemma-2-text-270m.litertlm")))

# The retriever uses a running UniversalEmbedder to turn text into vectors.
with UniversalEmbedder.create_from_options(embedder_options) as embedder, \
        SemanticRetriever.create_from_options(
            SemanticRetrieverOptions(embedder=embedder)) as retriever:  # database in memory
    common.section(f"Indexing {len(documents)} documents")
    for doc_id, text in documents.items():
        retriever.insert_document(doc_id=doc_id, text=text)
        print(f"  [{doc_id:>7}] {text}")

    for q in queries:
        common.section(f"Query: \"{q}\"")
        hits = retriever.retrieve(query=q, limit=2, min_similarity=0.0)
        for rank, hit in enumerate(hits, 1):
            print(f"  {rank}. [{hit.id:>7}] score {hit.score:.3f}  {hit.content}")
common.done()
