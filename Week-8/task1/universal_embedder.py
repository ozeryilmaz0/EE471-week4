"""Universal Embedder: put text and images into the same vector space and compare them."""

import cv2
import numpy as np
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.retrieval import UniversalEmbedder, UniversalEmbedderOptions

import common

common.header("UNIVERSAL EMBEDDER",
              "Model: EmbeddingGemma 2 text+vision 440M (Apache-2.0)  |  Input: 3 images, 3 captions")

images = ["cat.jpg", "burger.jpg", "woman_hands.jpg"]
captions = ["a photo of a cat", "a hamburger with cheese", "a person showing their hands"]

options = UniversalEmbedderOptions(
    base_options=BaseOptions(model_asset_path=common.model("embeddinggemma-2-text-vision-440m.litertlm")))
with UniversalEmbedder.create_from_options(options) as embedder:
    img_emb = [embedder.embed_image((common.ASSETS / f).read_bytes()).embeddings[0] for f in images]
    txt_emb = [embedder.embed_text(c).embeddings[0] for c in captions]
    sim = np.array([[UniversalEmbedder.cosine_similarity(i, t) for t in txt_emb] for i in img_emb])

print(f"Embedding size: {len(np.asarray(txt_emb[0].embedding))} numbers per input")
common.section("Cosine similarity: image (row) vs caption (column)")
print(" " * 18 + "".join(f"{c[:22]:>25}" for c in captions))
for name, row in zip(images, sim):
    print(f"  {name:<16}" + "".join(f"{v:25.3f}" for v in row))

common.section("Best caption for each image")
tiles = []
for name, row in zip(images, sim):
    best = int(row.argmax())
    print(f"  {name:<16} -> \"{captions[best]}\" ({row[best]:.3f})")
    img = cv2.resize(common.load_bgr(common.ASSETS / name), (360, 360))
    common.label(img, captions[best], (8, 340), 0.6, (0, 255, 0))
    common.label(img, f"similarity {row[best]:.3f}", (8, 28), 0.6)
    tiles.append(img)
common.save_and_show(common.montage(tiles, 360), "universal_embedder.png")
common.done()
