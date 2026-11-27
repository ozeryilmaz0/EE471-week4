"""Chatbot replies with SmolLM2-360M-Instruct (CPU)."""

from __future__ import annotations

import re
import threading
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from config import CHAT_CONTEXT_MESSAGES, CHAT_MAX_NEW_TOKENS, CHAT_MODEL

SYSTEM_PROMPT = (
    "You are DreamCanvas, a short and friendly assistant inside an image generation app "
    "that paints pictures with Stable Diffusion, a text-to-image AI model. "
    "Answer in English in one to three short sentences. "
    "If the user asks for an image prompt, reply with ONLY one vivid, detailed English "
    "image prompt of at most 40 words, without quotes and without any introduction."
)

# Extra guidance (with a one-shot example) used when the user asks for an image prompt.
# A 360M model follows an example much better than an instruction alone.
PROMPT_EXAMPLE_USER = "Give me a prompt for an image of a city."
PROMPT_EXAMPLE_REPLY = (
    "A neon-lit futuristic city at night, flying cars between glass skyscrapers, "
    "rain reflections on the streets, cinematic lighting, ultra detailed digital art"
)

PROMPT_REQUEST = re.compile(
    r"\b(prompt|image|picture|photo|drawing|draw|paint|painting|illustration|wallpaper|artwork)\b",
    re.IGNORECASE,
)
ASKING = re.compile(r"\b(give|write|create|make|suggest|need|want|another|can you|could you|idea)\b", re.IGNORECASE)
INTRO = re.compile(r"^(sure|here('s| is)|of course|okay|ok|absolutely|certainly)[^:\n]*[:\n]\s*", re.IGNORECASE)

VALID_ROLES = {"user", "assistant"}


def is_prompt_request(text: str) -> bool:
    return bool(PROMPT_REQUEST.search(text) and ASKING.search(text))


def trim_to_sentence(text: str, max_sentences: int = 3) -> str:
    """Cut an unfinished reply back to its last complete sentence (max `max_sentences`)."""
    text = " ".join(text.split())
    if not text:
        return text
    if text[-1] not in ".!?":
        cut = max(text.rfind(". "), text.rfind("! "), text.rfind("? "))
        text = text[: cut + 1] if cut > 0 else text.rstrip(",;:- ") + "."
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:max_sentences])


def clean_image_prompt(text: str, max_words: int = 40) -> str:
    """Strip intros/quotes and keep a single prompt of at most `max_words` words."""
    text = INTRO.sub("", text.strip())
    text = text.split("\n\n")[0].replace("\n", " ")
    text = text.strip().strip("\"'“”‘’*").strip()
    text = re.sub(r"^(prompt|image prompt)\s*:\s*", "", text, flags=re.IGNORECASE)
    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words])
        # end on a clean phrase boundary
        cut = max(text.rfind(","), text.rfind("."))
        if cut > len(text) // 2:
            text = text[:cut]
    return text.rstrip(",;:- ").strip("\"'“”")


class ChatService:
    def __init__(self) -> None:
        torch.set_num_threads(max(1, torch.get_num_threads()))
        self.tokenizer = AutoTokenizer.from_pretrained(CHAT_MODEL)
        self.model = AutoModelForCausalLM.from_pretrained(CHAT_MODEL, torch_dtype=torch.float32)
        self.model.eval()
        self._lock = threading.Lock()

    def warm_up(self) -> float:
        start = time.perf_counter()
        self.reply([{"role": "user", "content": "Hi!"}], max_new_tokens=8)
        return time.perf_counter() - start

    def build_messages(self, history: list[dict]) -> list[dict]:
        cleaned = [
            {"role": m["role"], "content": str(m["content"]).strip()}
            for m in history
            if isinstance(m, dict) and m.get("role") in VALID_ROLES and str(m.get("content", "")).strip()
        ][-CHAT_CONTEXT_MESSAGES:]
        # Chat templates expect the conversation to start with a user turn.
        while cleaned and cleaned[0]["role"] != "user":
            cleaned.pop(0)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if cleaned and is_prompt_request(cleaned[-1]["content"]):
            messages += [
                {"role": "user", "content": PROMPT_EXAMPLE_USER},
                {"role": "assistant", "content": PROMPT_EXAMPLE_REPLY},
            ]
        return messages + cleaned

    def reply(self, history: list[dict], max_new_tokens: int = CHAT_MAX_NEW_TOKENS) -> str:
        messages = self.build_messages(history)
        if len(messages) == 1 or messages[-1]["role"] != "user":
            raise ValueError("The last message must come from the user.")
        prompt_mode = is_prompt_request(messages[-1]["content"])

        inputs = self.tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, return_tensors="pt", return_dict=True
        )
        with self._lock, torch.inference_mode():
            output = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=0.6,
                top_p=0.9,
                repetition_penalty=1.1,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        new_tokens = output[0, inputs["input_ids"].shape[1]:]
        text = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        if prompt_mode:
            text = clean_image_prompt(text)
        else:
            text = trim_to_sentence(text)
        return text or "Sorry, I could not think of an answer. Could you say that again?"
