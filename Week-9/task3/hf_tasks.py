"""Object-oriented wrappers around ten Hugging Face ``pipeline()`` tasks.

Architecture
------------
``BaseTask`` (abstract)
    Holds the model id and the device, loads the pipeline lazily (on the first
    ``run()``), and defines ``run()``, ``describe()`` and ``warm_up()``.
    Subclasses only implement ``_predict()`` and give an ``example`` input.
    Every subclass registers itself in ``BaseTask.registry`` under its ``key``.

Ten subclasses
    SentimentAnalysis, ZeroShotClassification, TextGeneration, FillMask,
    NamedEntityRecognition, QuestionAnswering, Summarization, Translation,
    ImageClassification, SpeechRecognition.

``HFToolkit``
    Creates one instance of every registered task and manages them together:
    ``toolkit["ner"].run(text)``, ``toolkit.load_all()``, ``toolkit.warm_up_all()``.

Example
-------
>>> from hf_tasks import HFToolkit
>>> kit = HFToolkit()
>>> kit["translation"].run("Ce cours est produit par Hugging Face.")
'This course is produced by Hugging Face.'
"""

from __future__ import annotations

import os
import re
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Iterator

# Models are pre-downloaded with Week-9/download_models.py, so stay offline (faster, no surprises).
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import numpy as np  # noqa: E402
import torch  # noqa: E402
from transformers import pipeline, set_seed  # noqa: E402
from transformers.utils import logging as hf_logging  # noqa: E402

hf_logging.set_verbosity_error()

ASSETS = Path(__file__).resolve().parents[1] / "assets"


class BaseTask(ABC):
    """One Hugging Face pipeline task with lazy loading.

    Class attributes set by every subclass:
        key:           short id used by ``HFToolkit`` (e.g. ``"ner"``)
        title:         human readable name (e.g. ``"Named entity recognition"``)
        task:          the ``pipeline()`` task name
        default_model: Hugging Face model id
        example:       keyword arguments for ``run()`` used by ``warm_up()`` and the UI examples
        gpu_fp16:      run on the GPU in float16 when CUDA is available
    """

    registry: ClassVar[dict[str, type[BaseTask]]] = {}

    key: ClassVar[str]
    title: ClassVar[str]
    task: ClassVar[str]
    default_model: ClassVar[str]
    example: ClassVar[dict[str, Any]] = {}
    gpu_fp16: ClassVar[bool] = False

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not getattr(cls, "__abstractmethods__", None):  # only concrete tasks are registered
            BaseTask.registry[cls.key] = cls

    def __init__(self, model: str | None = None) -> None:
        self.model_name: str = model or self.default_model
        self.use_gpu: bool = self.gpu_fp16 and torch.cuda.is_available()
        self.device: str = "cuda:0" if self.use_gpu else "cpu"
        self._pipe: Any | None = None
        self.load_seconds: float | None = None

    # ------------------------------------------------------------------ loading
    @property
    def is_loaded(self) -> bool:
        """True once the pipeline has been created."""
        return self._pipe is not None

    def load(self) -> BaseTask:
        """Create the pipeline if it does not exist yet (lazy loading). Returns ``self``."""
        if self._pipe is None:
            start = time.perf_counter()
            kwargs: dict[str, Any] = {"model": self.model_name, "device": self.device}
            if self.use_gpu:
                kwargs["dtype"] = torch.float16
            self._pipe = pipeline(self.task, **kwargs)
            self.load_seconds = time.perf_counter() - start
        return self

    @property
    def pipe(self) -> Any:
        """The underlying ``transformers`` pipeline (loaded on first access)."""
        return self.load()._pipe

    # ---------------------------------------------------------------- inference
    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Load the model if needed and run the task."""
        self.load()
        with torch.inference_mode():
            return self._predict(*args, **kwargs)

    @abstractmethod
    def _predict(self, *args: Any, **kwargs: Any) -> Any:
        """Task specific inference; implemented by every subclass."""

    def warm_up(self) -> float:
        """Run the task once on its example input; returns the time it took in seconds.

        The first call of a model is slower (memory allocation, CUDA kernels), so the
        app warms every task up before it starts serving requests.
        """
        start = time.perf_counter()
        self.run(**self.example)
        return time.perf_counter() - start

    def describe(self) -> str:
        """One line summary: title, pipeline task, model, device and load state."""
        state = f"loaded in {self.load_seconds:.1f} s" if self.is_loaded else "not loaded"
        precision = "fp16" if self.use_gpu else "fp32"
        return f"{self.title:<26} task={self.task:<29} model={self.model_name:<50} " \
               f"device={self.device} ({precision}), {state}"

    def __repr__(self) -> str:
        return f"{type(self).__name__}(model={self.model_name!r}, device={self.device!r}, loaded={self.is_loaded})"


# ============================================================================ tasks
class SentimentAnalysis(BaseTask):
    """Positive / negative sentiment of an English text."""

    key = "sentiment"
    title = "Sentiment analysis"
    task = "sentiment-analysis"
    default_model = "distilbert-base-uncased-finetuned-sst-2-english"
    example = {"text": "I've been waiting for a modern software practices course my whole life."}

    def _predict(self, text: str) -> dict[str, float]:
        """Return ``{label: score}`` for both labels."""
        scores = self.pipe(text, top_k=None)
        return {r["label"]: float(r["score"]) for r in scores}


class ZeroShotClassification(BaseTask):
    """Classify a text into labels that the model was never trained on."""

    key = "zero_shot"
    title = "Zero-shot classification"
    task = "zero-shot-classification"
    default_model = "facebook/bart-large-mnli"
    example = {"text": "Berkshire keeps their cash reserves at an extremely high level.",
               "labels": ["finance", "politics", "sports", "technology", "education"]}

    def _predict(self, text: str, labels: list[str] | str) -> dict[str, float]:
        """``labels`` may be a list or a comma separated string. Returns ``{label: score}``."""
        if isinstance(labels, str):
            labels = [label.strip() for label in labels.split(",") if label.strip()]
        if not labels:
            raise ValueError("Give at least one candidate label.")
        out = self.pipe(text, candidate_labels=labels)
        return dict(zip(out["labels"], map(float, out["scores"])))


class TextGeneration(BaseTask):
    """Continue a prompt with GPT-2; every alternative is limited to ``max_words`` words."""

    key = "text_generation"
    title = "Text generation"
    task = "text-generation"
    default_model = "gpt2"
    example = {"prompt": "If I continue to complete all in-class exercises in this modern software practices course,"}
    MAX_WORDS: ClassVar[int] = 35

    @staticmethod
    def limit_words(text: str, prompt: str, max_words: int) -> str:
        """Cut ``text`` to ``max_words`` words; end at the last full sentence after the prompt if possible."""
        words = text.split()[:max_words]
        cut = " ".join(words)
        prompt_len = len(" ".join(prompt.split()))
        ends = [m.end() for m in re.finditer(r"[.!?](?=\s|$)", cut) if m.end() > prompt_len]
        if ends and len(words) == max_words:
            cut = cut[: ends[-1]]
        return cut

    def _predict(self, prompt: str, max_words: int = 35, num_sequences: int = 2, seed: int = 42) -> list[str]:
        """Return ``num_sequences`` completions (prompt included), each with at most ``max_words`` words."""
        max_words = max(1, min(int(max_words), self.MAX_WORDS))
        set_seed(int(seed))
        prompt_words = len(prompt.split())
        new_tokens = max(8, int((max_words - prompt_words) * 1.4) + 2)  # ~1.3 tokens per word + margin
        outputs = self.pipe(prompt, max_new_tokens=new_tokens, num_return_sequences=int(num_sequences),
                            do_sample=True, top_k=50, top_p=0.95,
                            pad_token_id=self.pipe.tokenizer.eos_token_id)
        return [self.limit_words(o["generated_text"], prompt, max_words) for o in outputs]


class FillMask(BaseTask):
    """Predict the word hidden behind ``<mask>``."""

    key = "fill_mask"
    title = "Fill mask"
    task = "fill-mask"
    default_model = "distilroberta-base"
    example = {"text": "To understand generative AI, one must study <mask> well."}

    def _predict(self, text: str, top_k: int = 3) -> dict[str, float]:
        """Return ``{token: score}`` for the ``top_k`` best tokens."""
        mask = self.pipe.tokenizer.mask_token
        if mask not in text:
            raise ValueError(f"The text must contain the mask token {mask}.")
        return {r["token_str"].strip(): float(r["score"]) for r in self.pipe(text, top_k=int(top_k))}


class NamedEntityRecognition(BaseTask):
    """Find persons, organisations and locations (CoNLL-03 labels)."""

    key = "ner"
    title = "Named entity recognition"
    task = "ner"
    default_model = "dbmdz/bert-large-cased-finetuned-conll03-english"
    example = {"text": "I am Nate, a research assistant at Izmir Institute of Technology, and currently "
                       "living and working in the beautiful city İzmir in Türkiye."}

    def _predict(self, text: str) -> list[dict[str, Any]]:
        """Return the grouped entities: ``word`` (taken from the input), ``entity_group``, ``score``, ``start``, ``end``."""
        entities = self.pipe(text, aggregation_strategy="simple")
        return [{"word": text[e["start"]:e["end"]], "entity_group": e["entity_group"],
                 "score": float(e["score"]), "start": int(e["start"]), "end": int(e["end"])} for e in entities]


class QuestionAnswering(BaseTask):
    """Extract the answer to a question from a context text."""

    key = "qa"
    title = "Question answering"
    task = "question-answering"
    default_model = "distilbert-base-cased-distilled-squad"
    example = {"question": "Where do I work?", "context": NamedEntityRecognition.example["text"]}

    def _predict(self, question: str, context: str) -> dict[str, Any]:
        """Return ``answer``, ``score``, ``start`` and ``end``."""
        out = self.pipe(question=question, context=context)
        return {"answer": out["answer"], "score": float(out["score"]), "start": out["start"], "end": out["end"]}


class Summarization(BaseTask):
    """Abstractive summary of a longer English text."""

    key = "summarization"
    title = "Summarization"
    task = "summarization"
    default_model = "sshleifer/distilbart-cnn-12-6"
    example = {"text": (
        "The 2008 Global Financial Crisis stands as the most severe economic collapse of the 21st century, "
        "often compared to the Great Depression of the 1930s. Triggered by the bursting of the United States "
        "housing bubble, its effects rippled across the globe, leading to the collapse of major financial "
        "institutions and a deep international recession. The crisis began with the subprime mortgage market. "
        "In the early 2000s, low interest rates and a push for homeownership led banks to issue high-risk "
        "loans to borrowers with poor credit.")}

    def _predict(self, text: str, min_length: int = 20, max_length: int = 60) -> str:
        """Return the summary (2 beams: about twice as fast as the default 4 on a CPU)."""
        out = self.pipe(text, min_length=int(min_length), max_length=int(max_length), num_beams=2, do_sample=False)
        return re.sub(r"\s+([.,;:!?])", r"\1", " ".join(out[0]["summary_text"].split()))


class Translation(BaseTask):
    """Translate French to English with a MarianMT model."""

    key = "translation"
    title = "Translation (fr → en)"
    task = "translation"
    default_model = "Helsinki-NLP/opus-mt-fr-en"
    example = {"text": "Ce cours est produit par Hugging Face."}

    def _predict(self, text: str) -> str:
        """Return the English translation."""
        return self.pipe(text)[0]["translation_text"]


class ImageClassification(BaseTask):
    """Classify an image into the 1000 ImageNet classes with a Vision Transformer."""

    key = "image"
    title = "Image classification"
    task = "image-classification"
    default_model = "google/vit-base-patch16-224"
    example = {"image": str(ASSETS / "tiger.jpg")}

    def _predict(self, image: Any, top_k: int = 3) -> dict[str, float]:
        """``image`` is a file path, URL or PIL image. Returns ``{label: score}`` for the ``top_k`` classes."""
        if image is None:
            raise ValueError("Upload an image first.")
        return {r["label"]: float(r["score"]) for r in self.pipe(image, top_k=int(top_k))}


class SpeechRecognition(BaseTask):
    """English speech to text with Whisper large-v3 (GPU, fp16)."""

    key = "asr"
    title = "Speech recognition"
    task = "automatic-speech-recognition"
    default_model = "openai/whisper-large-v3"
    gpu_fp16 = True
    example = {"audio": str(ASSETS / "speech.flac")}
    SAMPLING_RATE: ClassVar[int] = 16_000

    @classmethod
    def read_audio(cls, audio: Any) -> dict[str, Any] | str:
        """Turn a file path or a ``(sample_rate, samples)`` tuple (Gradio microphone) into pipeline input."""
        if isinstance(audio, tuple):
            sr, data = audio
            data = np.asarray(data)
            if np.issubdtype(data.dtype, np.integer):
                data = data / np.iinfo(data.dtype).max
        else:
            try:
                import soundfile as sf
                data, sr = sf.read(str(audio), dtype="float32")
            except Exception:  # formats libsndfile cannot read: let the pipeline use ffmpeg
                return str(audio)
        data = np.asarray(data, dtype=np.float32)
        if data.ndim > 1:
            data = data.mean(axis=1)
        if sr != cls.SAMPLING_RATE:
            import librosa
            data = librosa.resample(data, orig_sr=sr, target_sr=cls.SAMPLING_RATE)
        return {"raw": np.ascontiguousarray(data, dtype=np.float32), "sampling_rate": cls.SAMPLING_RATE}

    def _predict(self, audio: Any, language: str = "english") -> str:
        """Return the transcription. Greedy decoding: the pipeline default of 5 beams does not fit in 4 GB."""
        if audio is None:
            raise ValueError("Upload or record an audio clip first.")
        out = self.pipe(self.read_audio(audio),
                        generate_kwargs={"language": language, "task": "transcribe", "num_beams": 1})
        return out["text"].strip()


# ========================================================================== toolkit
class HFToolkit:
    """Owns one instance of every registered task and manages them together."""

    def __init__(self, keys: list[str] | None = None) -> None:
        """Create the tasks (nothing is loaded yet). ``keys`` selects a subset; default: all ten."""
        keys = keys or list(BaseTask.registry)
        self.tasks: dict[str, BaseTask] = {key: BaseTask.registry[key]() for key in keys}

    def __getitem__(self, key: str) -> BaseTask:
        return self.tasks[key]

    def __iter__(self) -> Iterator[BaseTask]:
        return iter(self.tasks.values())

    def __len__(self) -> int:
        return len(self.tasks)

    def run(self, key: str, *args: Any, **kwargs: Any) -> Any:
        """Run one task by its key, e.g. ``kit.run("translation", "Bonjour")``."""
        return self.tasks[key].run(*args, **kwargs)

    def load_all(self, verbose: bool = True) -> float:
        """Load every pipeline; returns the total time in seconds."""
        start = time.perf_counter()
        for task in self:
            task.load()
            if verbose:
                print(f"  loaded  {task.title:<26} {task.load_seconds:5.1f} s  ({task.device})", flush=True)
        return time.perf_counter() - start

    def warm_up_all(self, verbose: bool = True) -> dict[str, float]:
        """Run every task once on its example input; returns ``{key: seconds}``."""
        times = {}
        for key, task in self.tasks.items():
            times[key] = task.warm_up()
            if verbose:
                print(f"  warm-up {task.title:<26} {times[key]:5.2f} s", flush=True)
        return times

    def describe(self) -> str:
        """Multi-line overview of all tasks."""
        return "\n".join(task.describe() for task in self)


if __name__ == "__main__":
    kit = HFToolkit()
    print(kit.describe())
    print(kit["translation"].run(**Translation.example))
