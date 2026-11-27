"""Shared configuration for DreamCanvas AI."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"

# Models
IMAGE_MODEL = "stabilityai/sd-turbo"
CHAT_MODEL = "HuggingFaceTB/SmolLM2-360M-Instruct"
STT_MODEL = "openai/whisper-small"

# Image generation (sd-turbo: few steps, no classifier-free guidance)
IMAGE_SIZE = 512
IMAGE_STEPS = 2
IMAGE_GUIDANCE = 0.0

# Chat
CHAT_CONTEXT_MESSAGES = 6
CHAT_MAX_NEW_TOKENS = 120

# Server
HOST = "127.0.0.1"
PORT = 5000
