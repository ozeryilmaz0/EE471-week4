# Task 2 – LLM Course Chapter 1 quiz: answers

Quiz page: <https://huggingface.co/learn/llm-course/chapter1/7> ("Ungraded quiz", 11 questions).
Background pages: [chapter1/4](https://huggingface.co/learn/llm-course/chapter1/4) (How do Transformers work?),
[chapter1/5](https://huggingface.co/learn/llm-course/chapter1/5) (How 🤗 Transformers solve tasks),
[chapter1/6](https://huggingface.co/learn/llm-course/chapter1/6) (Transformer Architectures).

The answers were checked against the quiz source (`chapters/en/chapter1/7.mdx` in the
[huggingface/course](https://github.com/huggingface/course) repository, options marked `correct: true`).

| # | Question (short) | Correct answer(s) | Why |
|---|---|---|---|
| 1 | Task of the `roberta-large-mnli` checkpoint? | **Text classification** | The model page shows the **Text Classification** task tag. More precisely it decides whether two sentences are logically linked (contradiction / neutral / entailment) – natural language inference (MNLI). |
| 2 | What does `pipeline("ner", …)("My name is Sylvain and I work at Hugging Face in Brooklyn.")` return? | **The words representing persons, organizations or locations** | It is a NER pipeline; with entity grouping, the pieces of one entity ("Hugging Face") are returned together. Positive/negative scores would be sentiment analysis, a completion would be text generation. |
| 3 | What replaces `...` in `pipeline("fill-mask", model="bert-base-cased")`? | **`This [MASK] has been waiting for you.`** | BERT's mask token is `[MASK]` (`<mask>` is RoBERTa's), and a fill-mask pipeline needs a mask token in the input. |
| 4 | Why does `classifier("This is a course about the Transformers library")` with zero-shot fail? | **The pipeline requires that labels be given to classify this text** | Zero-shot classification needs `candidate_labels=[...]`. One sentence and short inputs are fine. |
| 5 | What does "transfer learning" mean? | **Initializing the second model with the first model's weights** | The new model starts from the pretrained weights and is trained on a new task, so the knowledge is transferred. Same dataset = same model; same architecture alone shares no knowledge. |
| 6 | A language model usually does not need labels for pretraining? | **True** | Pretraining is self-supervised: labels come from the input itself (next word, masked words). |
| 7 | Best description of model / architecture / weights? | **An architecture is a succession of mathematical functions to build a model and its weights are those functions' parameters** | The same functions (architecture) with different parameters (weights) give different models – e.g. BERT is the architecture, `bert-base-cased` is a checkpoint. |
| 8 | Model type for completing prompts with generated text? | **A decoder model** | Decoders (GPT-2, Llama) are auto-regressive: they predict the next token from the previous ones. |
| 9 | Model type for summarizing texts? | **A sequence-to-sequence model** | The encoder reads the whole text, the decoder writes the summary (BART, T5) – our `distilbart-cnn-12-6`. |
| 10 | Model type for classifying text inputs by labels? | **An encoder model** | The encoder builds a representation of the whole sentence, ideal for classification (BERT, RoBERTa). |
| 11 | Possible sources of bias in a model? *(multiple answers)* | **All three:** the pretrained model it was fine-tuned from · the training data · the metric it was optimized for | Bias from pretraining survives fine-tuning; biased data is the most obvious source; the model also blindly optimizes whatever metric was chosen. |

## Question 1 – model page

- Link: <https://huggingface.co/FacebookAI/roberta-large-mnli>
  (the old link <https://huggingface.co/roberta-large-mnli> redirects here)
- Task tag at the top of the page: **Text Classification** (`pipeline_tag: text-classification`),
  trained on the MultiNLI dataset (natural language inference).
