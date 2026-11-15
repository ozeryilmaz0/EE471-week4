# Week 7 — PyTorch, Hyperparameter Optimization and Cog

Two image classifiers, each trained twice:

1. **Baseline** — the official PyTorch tutorial, unchanged.
2. **Optimized** — hyperparameters found with [Optuna](https://optuna.org/), then a longer training run.

Both models of a dataset are packaged with [Cog](https://github.com/replicate/cog) as HTTP
model servers, and one Flask website shows their predictions **side by side**.

| Dataset | Baseline | Optimized |
|---|---|---|
| **Fashion-MNIST** (garments, 28x28 grayscale) | Quickstart MLP (784→512→512→10) | Same MLP, tuned width/dropout/optimizer |
| **CIFAR-10** (objects, 32x32 colour) | "Training a Classifier" CNN (conv 6/16, fc 120/84/10) | Configurable VGG-style CNN |

## Results

Measured on the **test set** (never used during the search). Trained on an RTX 3050 Ti laptop GPU.

| | Fashion baseline | Fashion optimized | CIFAR baseline | CIFAR optimized |
|---|---|---|---|---|
| Test accuracy | 64.15% | **89.58%** | 54.26% | **81.07%** |
| Test loss | 1.090 | 0.316 | 1.274 | 0.650 |
| Epochs | 5 | 15 (best 15) | 2 | 15 of max 20 (best 10, early stop) |
| Training time | 1.7 min | 4.4 min | 2.6 min | 15.5 min |
| Parameters | 669,706 | 1,863,690 | 62,006 | 2,197,706 |
| HPO | – | 20 trials x 3 epochs, 8.5 min | – | 12 trials x 3 epochs, 22.6 min |

Best hyperparameters (validation split):

- **Fashion-MNIST:** Adam, lr 1.61e-4, batch 32, hidden 1024, dropout 0.12, weight decay 1.3e-6
  (val acc 87.53%). Most important (fANOVA): dropout 0.34, lr 0.31.
- **CIFAR-10:** width 64, batch norm on, augmentation off, dropout 0.12, Adam, lr 1.49e-4,
  batch 128, weight decay 5.5e-4 (val acc 72.94%). Most important (fANOVA): lr 0.38, width 0.29.

The one-page performance report is [`REPORT.pdf`](REPORT.pdf) (same content in [`REPORT.md`](REPORT.md)).

## Folder structure

```
Week-7/
├── basics/basics.ipynb            # PyTorch basics: tensors, datasets, transforms, network
├── fashion-mnist/
│   ├── model.py                   # NeuralNetwork (tutorial defaults) + CLASSES
│   ├── common.py                  # data loading, train/test loops, optimizer factory
│   ├── train_baseline.py          # Quickstart: SGD lr=1e-3, batch 64, 5 epochs
│   ├── hpo.py                     # Optuna: TPE, MedianPruner, 20 trials x 3 epochs
│   ├── train_optimized.py         # best params, 15 epochs, keep best validation epoch
│   ├── make_samples.py            # 2 test images per class -> sample_images/
│   ├── models/                    # baseline.pth, optimized.pth (state_dicts)
│   ├── metrics/                   # *.json, hpo_trials.csv, *.png, training logs
│   ├── sample_images/             # 03_dress_1.png ... (true class in the file name)
│   ├── cog-baseline/              # cog.yaml, requirements.txt, run.py, model.py, model_info.json, .pth
│   └── cog-optimized/             # same files for the optimized model
├── cifar10/                       # same layout (12 trials x 3 epochs, up to 20 final epochs)
├── web/                           # Flask comparison site (app.py, static/, Dockerfile)
├── docker-compose.fashion.yml     # fashion-baseline 5010, fashion-optimized 5011, fashion-web 5012
├── docker-compose.cifar.yml       # cifar-baseline 5020, cifar-optimized 5021, cifar-web 5022
├── postman/                       # two Postman v2.1 collections (+ the script that builds them)
├── make_report.py                 # metrics -> REPORT.md + one-page REPORT.pdf
├── REPORT.md / REPORT.pdf
└── README.md
```

Datasets are downloaded into `*/data/` on first use (git-ignored). The `.pth` files are
committed because `cog build` copies them into the images.

## 1. Setup (Windows, PowerShell)

Use the virtual environment at the repository root.

```powershell
cd <repo>
python -m venv venv                       # only if venv/ does not exist yet
# NVIDIA GPU (CUDA 12.8 wheels); for CPU only use: venv\Scripts\python.exe -m pip install torch torchvision
venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
venv\Scripts\python.exe -m pip install optuna scikit-learn pandas matplotlib pillow ipykernel nbconvert reportlab requests
```

`scikit-learn` is needed by Optuna's fANOVA parameter importance and `pandas` by
`study.trials_dataframe()`. The scripts use the GPU when `torch.cuda.is_available()`, otherwise the CPU.

Other tools:

- **Docker Desktop** with the WSL 2 backend (`docker` works in PowerShell and Ubuntu).
- **Cog** inside WSL Ubuntu (tested with Cog 0.23.1). Cog only runs on Linux.

## 2. PyTorch basics notebook

```powershell
cd Week-7\basics
..\..\venv\Scripts\python.exe -m ipykernel install --sys-prefix --name ee471-venv --display-name "Python 3 (EE471 venv)"
..\..\venv\Scripts\python.exe -m nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name=ee471-venv basics.ipynb
```

Or open `basics.ipynb` in VS Code / Jupyter and pick the **Python 3 (EE471 venv)** kernel.

## 3. Train, optimize, export (PowerShell)

Run the scripts from the dataset folder. Each training script also copies `model.py`, the
weights and a `model_info.json` (model name, architecture, kwargs, test accuracy) into its
`cog-*` folder.

```powershell
cd Week-7\fashion-mnist
..\..\venv\Scripts\python.exe train_baseline.py      # models/baseline.pth, metrics/baseline.json
..\..\venv\Scripts\python.exe hpo.py                 # metrics/hpo_trials.csv, best_params.json, *.png
..\..\venv\Scripts\python.exe train_optimized.py     # models/optimized.pth, metrics/optimized.json
..\..\venv\Scripts\python.exe make_samples.py        # sample_images/

cd ..\cifar10
..\..\venv\Scripts\python.exe train_baseline.py
..\..\venv\Scripts\python.exe hpo.py                 # --trials 12 --epochs 3 by default
..\..\venv\Scripts\python.exe train_optimized.py     # --epochs 20 --patience 5 by default
..\..\venv\Scripts\python.exe make_samples.py

cd ..
..\venv\Scripts\python.exe make_report.py            # REPORT.md + REPORT.pdf (fails if > 1 page)
..\venv\Scripts\python.exe postman\make_collections.py
```

### How the HPO works

- **Validation only:** 10% of the training set (fixed seed 42) is the validation split. The
  test set is never used during the search; it is measured once, after the final training.
- **Fashion-MNIST search space:** optimizer {SGD+momentum 0.9, Adam, AdamW}, lr (log 1e-4…1e-1),
  batch {32, 64, 128, 256}, hidden {128, 256, 512, 1024}, dropout (0…0.5), weight decay (log 1e-6…1e-3).
- **CIFAR-10 search space:** the same optimizer/lr/batch/weight decay, plus channel width
  {16, 32, 64}, dropout, batch norm on/off and augmentation (RandomCrop + HorizontalFlip) on/off.
- **Sampler and pruner:** TPE (seed 42) and MedianPruner, 3 epochs per trial.
- **Final training:** Fashion-MNIST 15 epochs, CIFAR-10 up to 20 epochs with early stopping
  (patience 5). The epoch with the best validation accuracy is kept.

## 4. Cog images (Ubuntu / WSL)

`cog.yaml` and `requirements.txt` are the same as in `Week-6/cat-classifier`
(Python 3.13, torch 2.6.0, torchvision 0.21.0), so Docker reuses the cached torch layer and the
builds take seconds. `--use-cog-base-image=false` avoids downloading the Cog base image (see
Week 6).

```bash
cd /mnt/c/Users/<you>/Desktop/EE471/EE471-week4/Week-7

# try a model once without building an image
cd fashion-mnist/cog-baseline
cog run --use-cog-base-image=false -i image=@../sample_images/03_dress_1.png

# build the four images
cd ../cog-baseline  && cog build --use-cog-base-image=false -t fashion-baseline
cd ../cog-optimized && cog build --use-cog-base-image=false -t fashion-optimized
cd ../../cifar10/cog-baseline  && cog build --use-cog-base-image=false -t cifar-baseline
cd ../cog-optimized            && cog build --use-cog-base-image=false -t cifar-optimized
```

From PowerShell the same works with
`wsl -d Ubuntu -e bash -lc "cd /mnt/c/.../Week-7/fashion-mnist/cog-baseline && cog build --use-cog-base-image=false -t fashion-baseline"`.

### What a Cog model returns

```json
{
  "predicted_class": "Dress",
  "confidence": 0.9512,
  "top3": {"Dress": 0.9512, "Coat": 0.0301, "Shirt": 0.0102},
  "model_name": "fashion-optimized",
  "model_test_accuracy": 0.8958
}
```

- **Fashion-MNIST pre-processing:** grayscale; if the background is light (mean of the border
  pixels > 127) the colours are inverted, because Fashion-MNIST shows light garments on black;
  padded to a square with black and resized to 28x28. The border is used instead of the whole
  image, so a big bright garment on a black background is not inverted by mistake.
- **CIFAR-10 pre-processing:** RGB, resized to 32x32, `Normalize((0.5,0.5,0.5), (0.5,0.5,0.5))`
  as in the tutorial.
- Both runners resize with the **BOX** (area average) filter: it is anti-aliased for photos, and
  it gives back exactly the original dataset pixels for the upscaled `sample_images` (checked:
  20/20 identical tensors for each dataset).
- `setup()` logs `Model loaded: <model name>`. Every prediction is logged as
  `PREDICTION {json}` to stdout and to `/tmp/predictions.log` inside the container.

## 5. Run the comparison website (PowerShell)

```powershell
cd Week-7
docker compose -f docker-compose.fashion.yml up -d --build
docker ps
# open http://localhost:5012
docker compose -f docker-compose.fashion.yml down

docker compose -f docker-compose.cifar.yml up -d --build
# open http://localhost:5022
docker compose -f docker-compose.cifar.yml down
```

| Port | Container | What |
|---|---|---|
| 5010 | `fashion-baseline` | Cog API, Fashion-MNIST baseline |
| 5011 | `fashion-optimized` | Cog API, Fashion-MNIST optimized |
| 5012 | `fashion-web` | Garment Classifier 👕 website |
| 5020 | `cifar-baseline` | Cog API, CIFAR-10 baseline |
| 5021 | `cifar-optimized` | Cog API, CIFAR-10 optimized |
| 5022 | `cifar-web` | CIFAR-10 Classifier 🚗 website |

The website (`web/app.py`) is configured with environment variables: `APP_TITLE`,
`BASELINE_URL`, `OPTIMIZED_URL` and `SAMPLES_DIR` (the sample images are mounted read-only as
a volume). `POST /api/classify` turns the upload into a base64 data URI and sends it to both Cog
containers **in parallel**; the page shows both predictions, confidence, top-3 bars, response
time, each model's test accuracy and an **Agree / Disagree** badge. Click an image in
**Try a sample** to classify it.

Watch the predictions live in a second terminal:

```powershell
docker exec -it fashion-optimized sh
tail -f /tmp/predictions.log
```

## 6. Postman

**Import** `postman/fashion.postman_collection.json` or `postman/cifar.postman_collection.json`
and **Send** the requests (the containers must be running):

- `GET http://localhost:5010/health-check` / `5011` (CIFAR: `5020` / `5021`)
- `POST http://localhost:5010/predictions` / `5011` with body
  `{"input": {"image": "data:image/png;base64,..."}}`. A sample image is already embedded.

Each request has tests (status 200, `READY`, `succeeded`, three top-3 entries).

## Common problems

| Problem | Fix |
|---|---|
| `pull access denied for fashion-baseline` on `docker compose up` | Build the Cog images first (section 4). |
| The website card says "Model server is not reachable" | The Cog container is still starting. Wait until `http://localhost:5010/health-check` says `READY`. |
| `port is already allocated` | Another stack uses the port. Run `docker compose -f ... down` for the other file. |
| `cog: command not found` in PowerShell | Run Cog in Ubuntu or through `wsl -d Ubuntu -e bash -lc "..."`. |
| `ImportError: ... 'sklearn'` or `'pandas'` in `hpo.py` | `venv\Scripts\python.exe -m pip install scikit-learn pandas`. |
| A photo of a white shirt on a dark background is misclassified | Fashion-MNIST images are centred, light garments on black. Crop the garment and use a plain background. |
