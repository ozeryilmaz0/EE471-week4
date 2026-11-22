"""Image Embedder: turn images into feature vectors and measure how similar they look."""

from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import ImageEmbedder, ImageEmbedderOptions

import common

common.header("IMAGE EMBEDDER", "Model: MobileNet-V3 Small  |  Input: assets/cat.jpg, cat_and_dog.jpg, burger.jpg")

names = ["cat.jpg", "cat_and_dog.jpg", "burger.jpg"]
options = ImageEmbedderOptions(
    base_options=BaseOptions(model_asset_path=common.model("mobilenet_v3_small.tflite")),
    l2_normalize=True, quantize=False)

images, embs = [], []
with ImageEmbedder.create_from_options(options) as embedder:
    for n in names:
        mp_img, rgb = common.load_mp(common.ASSETS / n)
        embs.append(embedder.embed(mp_img).embeddings[0])
        images.append(common.rgb2bgr(rgb))

print(f"Each image becomes a vector of {len(embs[0].embedding)} numbers.")
common.section("Cosine similarity to cat.jpg")
for n, img, e in zip(names, images, embs):
    sim = ImageEmbedder.cosine_similarity(embs[0], e)
    print(f"  {n:<16} {sim:.3f}")
    common.label(img, f"similarity to cat.jpg: {sim:.2f}", (10, 35), 0.9)
print("\nThe cat-and-dog photo is closer to the cat photo than the burger is.")
common.save_and_show(common.montage(images), "image_embedder.png")
common.done()
