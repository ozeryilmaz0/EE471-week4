# Week 6 — Containers and Cog

Two tasks:

1. **Task 1:** run the two Week 5 Azure Speech apps (speech studio and voice
   calculator) in Docker containers with one `docker compose` command.
2. **Task 2:** a **cat-kind classifier**. A pretrained ResNet-50 is packaged
   with [Cog](https://github.com/replicate/cog) as an HTTP model server, with a
   small Flask website in front of it.

| Port | Service | Container |
|---|---|---|
| 5000 | Speech studio (Week 5 Task 1) | `speech-studio` |
| 5001 | Voice calculator (Week 5 Task 2) | `voice-calculator` |
| 5002 | Cog model API (`/health-check`, `/predictions`) | `cat-cog` |
| 5003 | Cat classifier website | `cat-web` |

## Prerequisites

- **Docker Desktop** for Windows with the WSL 2 backend. The `docker` command
  works in both PowerShell and Ubuntu.
- **WSL 2 with Ubuntu.** Cog only runs on Linux, so all `cog` commands are run
  in Ubuntu.
- **Cog** installed inside Ubuntu (`cog --version`). This project was tested
  with Cog 0.23.1.
- **`.env`** at the repository root with your Azure Speech key (only needed for
  Task 1):

  ```powershell
  Copy-Item .env.example .env   # then put your key into .env
  ```

## Task 1 — Speech studio and voice calculator

`Week-6/docker-compose.yml` builds both apps from their Week 5 folders. Each one
has a `Dockerfile` (`python:3.11-slim-bookworm` + ffmpeg + the native libraries
of the Azure Speech SDK) and a `.dockerignore`.

```powershell
cd Week-6
docker compose up -d --build     # build both images and start them
docker compose ps                # speech-studio on 5000, voice-calculator on 5001
docker compose logs -f           # follow the logs (Ctrl+C to stop following)
docker compose down              # stop and remove the containers
```

- Speech studio: <http://localhost:5000>
- Voice calculator: <http://localhost:5001>

### How the Azure key stays out of the image

- Both `.dockerignore` files list `.env`, so `COPY . .` never copies it into an
  image.
- The key is given **at run time** with `env_file: ../.env` in
  `docker-compose.yml`. Docker passes it to the container as environment
  variables, and the image itself contains no key.
- You can check this: `docker run --rm week-6-speech-studio ls -a /app` shows
  no `.env`.
- `.env` is also in the repository `.gitignore`.

## Task 2 — Cat-kind classifier (Cog)

```
Week-6/cat-classifier/
├── cog.yaml                 # Python 3.13, requirements.txt, run: "run.py:Runner"
├── requirements.txt         # pillow, torch, torchvision (pinned)
├── run.py                   # Runner: setup() loads ResNet-50, run() classifies
├── .dockerignore            # keeps web/, postman/, *.json, caches out of the Cog image
├── make_payload.py          # photo -> payload.json for curl
├── docker-compose.yml       # cog (5002) + web (5003)
├── input.jpg                # the "mystery" photo from the Cog getting-started guide
├── test_images/             # Siamese, Persian, tabby, dog (+ CREDITS.md)
├── postman/cat-classifier.postman_collection.json
├── hub/                     # ResNet-50 weights, downloaded on first run (git-ignored)
└── web/                     # Flask site: app.py, static/, Dockerfile, .dockerignore
```

### What the model returns

`run.py` uses ImageNet classes 281–285 (Tabby, Tiger, Persian, Siamese and
Egyptian cat):

```json
{
  "is_cat": true,
  "cat_kind": "Siamese cat",
  "cat_confidence": 0.9994,
  "cat_probabilities": {"Tabby cat": 0.0001, "Tiger cat": 0.0, "Persian cat": 0.0,
                        "Siamese cat": 0.9846, "Egyptian cat": 0.0004},
  "top3_imagenet": [{"label": "Siamese cat", "probability": 0.9846},
                    {"label": "space heater", "probability": 0.0013},
                    {"label": "backpack", "probability": 0.0009}]
}
```

- `is_cat` is true when the five cat classes together have at least 0.3.
- `cat_confidence` is the best cat kind's share of that total.
- `cat_kind` and `cat_confidence` are `null` when the photo is not a cat.
- Every prediction is logged as `PREDICTION {json}` to stdout and to
  `/tmp/predictions.log` inside the container.

### 1. Try the model with `cog run` (Ubuntu)

```bash
cd /mnt/c/Users/<you>/Desktop/EE471/EE471-week4/Week-6/cat-classifier
cog run --use-cog-base-image=false -i image=@test_images/siamese.jpg
```

The first run builds an image, installs torch and downloads the weights into
`hub/`, so it takes several minutes. Later runs are fast.

### 2. Build the image (Ubuntu)

```bash
cog build --use-cog-base-image=false -t cat-classifier
```

The weights in `hub/` are copied into the image, because `.dockerignore` does
**not** exclude `hub/`. The container can then start without internet access.

### 3. Start the model server and the website (PowerShell or Ubuntu)

```bash
cd Week-6/cat-classifier
docker compose up -d --build
docker compose ps
```

- Website: <http://localhost:5003>. Drop a photo and click **Classify**.
- Cog API: <http://localhost:5002/health-check> shows `{"status": "READY", ...}`
  when the model is loaded.

Inside the compose network the website calls the model at `http://cog:5000`
(`COG_URL`). If the model is not `READY` yet, the website answers 503 and the
page shows "The cat model is not ready yet".

Send a photo to the Cog API directly:

```bash
python make_payload.py test_images/persian.jpg        # writes payload.json (git-ignored)
curl -X POST http://localhost:5002/predictions \
     -H "Content-Type: application/json" -d @payload.json
```

### 4. Watch the prediction log live

Open a second terminal:

```bash
docker exec -it cat-cog sh
tail -f /tmp/predictions.log
```

Each classification adds one `PREDICTION {...}` line. Leave with `Ctrl+C`, then
`exit`. For a one-time look use `docker exec cat-cog cat /tmp/predictions.log`.

### 5. Postman

In Postman, choose **Import**, select
`Week-6/cat-classifier/postman/cat-classifier.postman_collection.json`, and
**Send**:

- **Health check:** `GET http://localhost:5002/health-check`
- **Predict cat kind:** `POST http://localhost:5002/predictions`. The body
  already contains `test_images/siamese.jpg` as a base64 data URI.

### 6. Stop everything

```bash
docker compose down
```

## Common problems

| Problem | Fix |
|---|---|
| `cog build` / `cog run` fails with `tls: server did not echo the legacy session ID` while pulling `r8.im/cog-base` | The prebuilt Cog base image is downloaded from `us-docker.pkg.dev`, and some networks or antivirus HTTPS scanners break that download. Add `--use-cog-base-image=false` (used in all commands above) to build from the standard Python image instead. |
| `cog: command not found` in PowerShell | Cog is installed in Ubuntu. Run it in Ubuntu, or from PowerShell with `wsl -d Ubuntu -e bash -lc "cd /mnt/c/.../cat-classifier && cog ..."`. |
| `docker compose up` says `pull access denied for cat-classifier` | The Cog image is not built yet. Run `cog build ... -t cat-classifier` first. |
| The website shows "The cat model is not ready yet" | The model takes a few seconds to load after the container starts. Wait until `/health-check` says `READY`. |
| `port is already allocated` | Another app is using 5000–5003. Stop it, or run `docker compose down` in the other folder. |
| Task 1 apps say the Azure key is missing | `.env` must exist at the repository root (next to `.env.example`) before `docker compose up`. |
| The first `cog run` is very slow | It installs torch and downloads about 100 MB of weights only once. |
