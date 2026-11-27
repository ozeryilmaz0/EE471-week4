"""Text-to-image with Stable Diffusion Turbo (fp16 on the GPU)."""

from __future__ import annotations

import io
import re
import threading
import time
from datetime import datetime

import torch
from diffusers import AutoPipelineForText2Image

from config import IMAGE_GUIDANCE, IMAGE_MODEL, IMAGE_SIZE, IMAGE_STEPS, OUTPUT_DIR


class ImageService:
    """Loads sd-turbo once and turns prompts into 512x512 PNG images."""

    def __init__(self) -> None:
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.pipe = AutoPipelineForText2Image.from_pretrained(
            IMAGE_MODEL,
            torch_dtype=dtype,
            variant="fp16",
            use_safetensors=True,
        )
        self.pipe.set_progress_bar_config(disable=True)
        self.offloaded = False
        if self.device == "cuda":
            # sd-turbo fp16 (~2.6 GB) fits in 4 GB VRAM; slicing keeps attention peaks low.
            self.pipe.enable_attention_slicing()
            self.pipe.enable_vae_slicing()
            try:
                self.pipe.to("cuda")
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                self.pipe.enable_model_cpu_offload()
                self.offloaded = True
        self._lock = threading.Lock()  # one GPU job at a time
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def warm_up(self) -> float:
        start = time.perf_counter()
        self._run("a small red apple on a table", steps=1)
        return time.perf_counter() - start

    def _run(self, prompt: str, steps: int = IMAGE_STEPS, seed: int | None = None):
        generator = None
        if seed is not None:
            generator = torch.Generator(device="cpu").manual_seed(seed)
        with self._lock, torch.inference_mode():
            result = self.pipe(
                prompt=prompt,
                num_inference_steps=steps,
                guidance_scale=IMAGE_GUIDANCE,
                height=IMAGE_SIZE,
                width=IMAGE_SIZE,
                generator=generator,
            )
        return result.images[0]

    def generate(self, prompt: str, seed: int | None = None) -> tuple[bytes, float, str]:
        """Return (png_bytes, seconds, saved_filename)."""
        start = time.perf_counter()
        image = self._run(prompt, seed=seed)
        seconds = time.perf_counter() - start

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        png = buffer.getvalue()

        slug = re.sub(r"[^a-z0-9]+", "-", prompt.lower()).strip("-")[:40] or "image"
        now = datetime.now()
        filename = f"{now:%Y%m%d-%H%M%S}-{now.microsecond // 1000:03d}_{slug}.png"
        (OUTPUT_DIR / filename).write_bytes(png)
        return png, seconds, filename
