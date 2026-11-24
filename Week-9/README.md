# Week 9 – Hugging Face Transformers pipelines

In-class exercise based on the [Hugging Face LLM Course](https://huggingface.co/learn/llm-course),
chapters 1 and 2.

| Task | Folder | What it is |
|---|---|---|
| Task 1 | [`task1/`](task1) | Ten `pipeline()` demos in the style of chapter 1, one script per task |
| Task 2 | [`task2/quiz_answers.md`](task2/quiz_answers.md) | Answers and short explanations for the chapter 1 quiz |
| Task 3 | [`task3/`](task3) | Object-oriented toolkit (`hf_tasks.py`) and a Gradio app with one tab per task |
| Task 4 | [`task4/`](task4) | Chapter 2 basics with `bert-base-cased`: save/load, encode/decode, padding, truncation, special tokens |
| Recording | [`run_task1_task4.py`](run_task1_task4.py) | Runs the 15 Task 1 + Task 4 steps one by one for a screen recording |

## 1. Setup

Windows, PowerShell, the virtual environment in the repository root (PyTorch with CUDA is
already installed there). Tested on an RTX 3050 Ti Laptop GPU (4 GB) with 16 GB RAM.

```powershell
cd EE471-week4                       # repository root
venv\Scripts\python.exe -m pip install -r Week-9\requirements.txt
```

`transformers` is pinned to **4.x**: version 5 removed the `summarization`, `translation` and
`question-answering` pipelines that chapter 1 uses. `gradio` 5.x is the line that works with
the `huggingface-hub` version of transformers 4.x.

## 2. Download the models

```powershell
venv\Scripts\python.exe Week-9\download_models.py
```

The script downloads only the files PyTorch needs (config, tokenizer and safetensors weights;
no TF/Flax/ONNX copies) for the 11 models below, about 9.8 GB, into the normal Hugging Face
cache. It also fetches the sample image. Afterwards every script runs **offline**
(`HF_HUB_OFFLINE=1`), so loading is fast and nothing is downloaded during a demo.

| Model | Used for | Device |
|---|---|---|
| `distilbert-base-uncased-finetuned-sst-2-english` | sentiment analysis | CPU |
| `facebook/bart-large-mnli` | zero-shot classification | CPU |
| `gpt2` | text generation | CPU |
| `distilroberta-base` | fill-mask | CPU |
| `dbmdz/bert-large-cased-finetuned-conll03-english` | named entity recognition | CPU |
| `distilbert-base-cased-distilled-squad` | question answering | CPU |
| `sshleifer/distilbart-cnn-12-6` | summarization | CPU |
| `Helsinki-NLP/opus-mt-fr-en` | translation (fr → en) | CPU |
| `google/vit-base-patch16-224` | image classification | CPU |
| `openai/whisper-large-v3` | speech recognition | **GPU, fp16** |
| `bert-base-cased` | Task 4 | CPU |

**Memory plan (4 GB VRAM):** Whisper large-v3 in fp16 needs about 3.1 GB for the weights and
peaks at about 3.4 GB, so it gets the GPU alone; the other models are small enough to be fast
on the CPU. Two settings keep every inference under 2 s after warm-up:

* the ASR pipeline defaults to beam search with 5 beams (peak 4.4 GB → spills into shared
  memory, 15 s per clip); `num_beams=1` gives the same text in about 1 s;
* distilbart uses 2 beams instead of its default 4 (1.2 s instead of 2.7 s on the CPU).

### Sample inputs (`assets/`)

* `tiger.jpg` – one of the widget examples of `google/vit-base-patch16-224`.
* `speech.flac` – 6.0 s of clear English speech, made with Azure Text-to-Speech
  (`make_speech_sample.py`, same approach as Week 5; the key is read from `.env` by
  python-dotenv). Text: *"Hugging Face pipelines let us use powerful AI models with only a few
  lines of Python code."*

## 3. Task 1 – pipelines

Run any script on its own (from the repository root):

```powershell
venv\Scripts\python.exe Week-9\task1\sentiment_analysis.py
venv\Scripts\python.exe Week-9\task1\zero_shot_classification.py
venv\Scripts\python.exe Week-9\task1\text_generation.py
venv\Scripts\python.exe Week-9\task1\fill_mask.py
venv\Scripts\python.exe Week-9\task1\named_entity_recognition.py
venv\Scripts\python.exe Week-9\task1\question_answering.py
venv\Scripts\python.exe Week-9\task1\summarization.py
venv\Scripts\python.exe Week-9\task1\translation.py
venv\Scripts\python.exe Week-9\task1\image_classification.py
venv\Scripts\python.exe Week-9\task1\speech_recognition.py
```

Every script has the same small interface (`TITLE`, `MODEL`, `inputs()`, `load()`, `run()`,
`render()`), so it can run alone and inside the recording helper. Common code is in
[`shared.py`](shared.py).

### Input → output

| # | Task | Input | Output |
|---|---|---|---|
| 1 | Sentiment analysis | "I've been waiting for a modern software practices course my whole life." / "I hate software courses" | **NEGATIVE 98.8 %** / **NEGATIVE 99.9 %** – the first one is a real model mistake: SST-2 reads "waiting … my whole life" as a complaint. |
| 2 | Zero-shot classification | "Berkshire keeps their cash reserves at an extremely high level." + 5 labels | **finance 91.1 %**, technology 4.6 %, sports 1.8 %, politics 1.5 %, education 1.1 % |
| 3 | Text generation (seed 42, 2 alternatives, ≤ 35 words) | "If I continue to complete all in-class exercises in this modern software practices course," | 1) "… I'll be in the position to make mistakes, and if I continue to do what I'm doing at home, then I'll" (35 words) · 2) "… I will be asked to pass the exam." The teachers said they were shocked by the decision." (31 words) |
| 4 | Fill-mask (top_k=3) | "To understand generative AI, one must study &lt;mask&gt; well." | **AI 56.6 %**, it 6.4 %, them 3.6 % |
| 5 | NER (`aggregation_strategy="simple"`) | "I am Nate, … Izmir Institute of Technology, … the beautiful city İzmir in Türkiye." | Person: **Nate** · Organization: **Izmir Institute of Technology** · City: **İzmir** · Country: Türkiye |
| 6 | Question answering | What is my name? / Where do I work? / In which city do I live? | **Nate** ✓ · **Izmir Institute of Technology** ✓ · **İzmir** ✓ (all three match the NER result) |
| 7 | Summarization | 2008 Global Financial Crisis text (85 words) | "The 2008 Global Financial Crisis stands as the most severe economic collapse of the 21st century. The crisis was triggered by the bursting of the U.S. housing bubble." |
| 8 | Translation fr → en | "Ce cours est produit par Hugging Face." | "This course is produced by Hugging Face." |
| 9 | Image classification (top-3) | `assets/tiger.jpg` | **tiger, Panthera tigris 88.6 %**, tiger cat 10.9 %, jaguar 0.1 % |
| 10 | Speech recognition (Whisper large-v3) | `assets/speech.flac` (6.0 s) | "Hugging face pipelines let us use powerful AI models with only a few lines of Python code." |

Warm inference times on the test laptop: 0.03 s (sentiment) to 1.3 s (text generation / Whisper).

## 4. Task 4 – chapter 2 with `bert-base-cased`

```powershell
venv\Scripts\python.exe Week-9\task4\load_and_save.py      # from_pretrained → save_pretrained("saved_model") → list files → reload
venv\Scripts\python.exe Week-9\task4\encoding_decoding.py  # tokenize → convert_tokens_to_ids → decode
venv\Scripts\python.exe Week-9\task4\padding.py            # two sentences, padding=True, aligned input_ids / attention_mask
venv\Scripts\python.exe Week-9\task4\truncation.py         # truncation=True, max_length=8 (29 → 8 tokens)
venv\Scripts\python.exe Week-9\task4\special_tokens.py     # add_special_tokens=True vs False, [CLS] = 101, [SEP] = 102
```

`task4/saved_model/` (≈ 414 MB: `config.json`, `model.safetensors`, tokenizer files) is
git-ignored. Saving and reloading it takes 1.5–4 s, depending on the disk.

## 5. Recording helper (Task 1 + Task 4)

```powershell
cd Week-9
..\venv\Scripts\python.exe run_task1_task4.py              # all 15 steps
..\venv\Scripts\python.exe run_task1_task4.py --start 11   # continue from step 11
..\venv\Scripts\python.exe run_task1_task4.py --auto       # test run without Enter
```

* Loads and warms up all models, then prints **"All models loaded. Press Enter to start."**
* Each step: full-screen big title (`Task 1 · 3/10 · TEXT GENERATION`), the input, and a
  timer in the top-right corner (turns red after 12 s). **Enter** runs the task and shows the
  result; **Enter** again goes to the next step. **q / Esc** stops.
* The local time (ms precision) when each title appears is written to
  `demo_timestamps.json` (git-ignored), to cut the long recording into one clip per task.
* Use a maximised terminal of at least 150 × 40 characters.

## 6. Task 3 – OOP toolkit and Gradio app

### Architecture of `task3/hf_tasks.py`

```text
                         ┌───────────────────────────────────────────────┐
                         │ BaseTask (ABC)                                │
                         │  key, title, task, default_model, example     │
                         │  registry  ← filled by __init_subclass__      │
                         │  load()  (lazy)   pipe   is_loaded            │
                         │  run() → _predict()  (abstract)               │
                         │  warm_up()   describe()                       │
                         └───────────────────────┬───────────────────────┘
                                                 │ inherits (10 subclasses)
                         ┌───────────────────────┴───────────────────────┐
                         │ SentimentAnalysis       ZeroShotClassification│
                         │ TextGeneration          FillMask              │
                         │ NamedEntityRecognition  QuestionAnswering     │
                         │ Summarization           Translation           │
                         │ ImageClassification    SpeechRecognition (GPU)│
                         └───────────────────────────────────────────────┘

                         ┌───────────────────────────────────────────────┐
                         │ HFToolkit                                     │
                         │  tasks: {key → BaseTask instance}  (all 10)   │
                         │  kit["ner"]  kit.run(key, …)  len(kit)        │
                         │  load_all()  warm_up_all()  describe()        │
                         └───────────────────────────────────────────────┘
                                   ▲ used by task3/app.py (Gradio)
```

* A subclass only sets its class attributes and implements `_predict()`. It registers itself
  in `BaseTask.registry`, so `HFToolkit()` automatically creates every task.
* `run()` loads the pipeline on first use (lazy loading) and runs under `torch.inference_mode()`.
* `SpeechRecognition` sets `gpu_fp16 = True`; all other tasks run on the CPU.

```python
from hf_tasks import HFToolkit
kit = HFToolkit()
kit["translation"].run("Ce cours est produit par Hugging Face.")   # 'This course is produced by Hugging Face.'
kit.run("qa", "What is my name?", "I am Nate, ...")                # {'answer': 'Nate', ...}
print(kit.describe())
```

### Gradio app

```powershell
cd Week-9
..\venv\Scripts\python.exe task3\app.py
```

Open <http://127.0.0.1:7860>. All ten models are loaded and warmed up before the server starts
(about 25 s), so no request waits for a model.

* One tab per task (a `gr.Interface` each): inputs, **Clear / Submit** buttons, the output box
  and **Examples** with the sentences from the assignment.
* Zero-shot: text + comma-separated labels · Text generation: max-words slider (≤ 35) and number
  of alternatives (default 2) · QA: context + question · Image classification: image upload ·
  Speech recognition: file upload **or microphone**.
* Each tab also has a named API endpoint (`/sentiment`, `/zero_shot`, … `/speech_recognition`).

Test all ten tabs with `gradio_client` while the app is running (second terminal):

```powershell
cd Week-9
..\venv\Scripts\python.exe task3\test_app_client.py
```

Result: **10/10 tabs passed**, each request 0.1–1.4 s.

## 7. Task 2 – quiz

See [`task2/quiz_answers.md`](task2/quiz_answers.md). Question 1: the
[roberta-large-mnli](https://huggingface.co/FacebookAI/roberta-large-mnli) model page shows the
**Text Classification** task (natural language inference on MultiNLI).
