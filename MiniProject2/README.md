# Mini Project 2 — Voice-Activated Library

The Week 4 library REST API (books and DVDs) with a **voice librarian** on top.
You click the microphone, say a command such as *"check out item 3"*, and the
app calls the real REST endpoint, then answers you out loud with Azure
text-to-speech. Commands can also be typed.

## Architecture

```
 Browser mic (MediaRecorder, webm)
        │  POST /api/voice  (multipart "audio")
        ▼
 ffmpeg  →  16 kHz mono WAV                       speech_service.convert_to_wav
        ▼
 Azure Speech-to-Text (en-US, continuous,          speech_service.transcribe
   display text, phrase list)
        ▼
 "Check out item 4."
        ▼
 parse_command  →  POST /api/items/4/checkout      voice_commands.parse_command
        ▼
 app.test_client()  →  the real REST route         app.handle_text_command
   (same validation and status codes as Postman)
        ▼
 build_message  →  "Item 4, 'Dune', has been       voice_commands.build_message
                    checked out."
        ▼
 Azure Text-to-Speech (en-US-JennyNeural)  →  WAV  speech_service.synthesize
        ▼
 JSON reply  →  page shows the result card and plays the audio
```

Typed commands (`POST /api/voice/text`) skip the first three steps.

| File | Role |
|---|---|
| `custom_classes.py` | Library model and **all business rules** (unchanged from Week 4) |
| `app.py` | The 8 REST endpoints + the 2 voice routes |
| `speech_service.py` | ffmpeg conversion, Azure STT and TTS |
| `voice_commands.py` | Pure functions: sentence → REST call, result → reply sentence |
| `static/` | Web page: item table and Voice Librarian panel |
| `main.py` | Week 4 console demo of the model |

The voice routes never change items directly. They send a request to the
normal REST route through `app.test_client()`, so every rule in
`custom_classes.py` (validation, 404, 409, 400) applies to voice commands too.

## Setup (Windows, PowerShell)

Run from the repository root:

```powershell
python -m venv venv
venv\Scripts\python.exe -m pip install -r MiniProject2\requirements.txt
```

Install **ffmpeg** (needed to convert browser recordings) and open a new
terminal so it is on the PATH:

```powershell
winget install --id Gyan.FFmpeg -e --scope user
ffmpeg -version
```

When the server starts it prints the ffmpeg it found (` * ffmpeg: ...`). If a
terminal was opened before the install, the app still finds ffmpeg through
the PATH saved in the registry or the winget folder. You can also point to it
directly with the `FFMPEG_PATH` environment variable.

Create your `.env` from the template and put your Azure Speech key in it:

```powershell
Copy-Item .env.example .env
notepad .env
```

```
SPEECH_KEY=your_key_here
SPEECH_REGION=eastus
```

## Keeping the key safe

- `.env` is listed in `.gitignore`, so it is never committed.
  Check it with `git check-ignore -v .env`.
- Only `.env.example` (with a placeholder) is in the repository.
- The code never prints the key. `speech_service.py` loads it with
  `load_dotenv(find_dotenv())`, which finds `.env` at the repository root.
- Recordings (`uploads/`, `*.wav`) and generated test audio (`test_audio/`)
  are also ignored. Uploaded files are deleted right after recognition.

## Running

```powershell
cd MiniProject2
..\venv\Scripts\python.exe app.py
```

Open <http://127.0.0.1:5000>. Click the microphone once to start recording
(it turns red and pulses), speak, and click again to send. You can also type a
command in the box. Data is kept in memory and is reset on every restart; the
seed has 4 items, so the first new item gets **ID 5**.

## Voice commands

Item numbers can be digits or words (`item 3`, `item number 3`, `item three`).
Fields are read between the keywords `type`, `title`, `author` / `director` /
`by`, `pages` / `page count`, and `duration` / `minutes`.

| Endpoint | Example sentences | Success reply | Error reply |
|---|---|---|---|
| `GET /api/items` | "list items", "list available books", "show DVDs", "list checked out items" | 200 — "I found 2 items: 'The Great Gatsby' and '1984'." | 400 ("list magazines") — "Sorry, I couldn't do that: type must be one of: item, book, dvd." |
| `GET /api/items/<id>` | "get item 5", "show item 5", "describe item 5", "tell me about item five" | 200 — "Item 5 is the book 'The Catcher in the Rye' by J.D. Salinger, 220 pages, and it is available." | 404 — "Sorry, item 99 was not found." |
| `POST /api/items` | "create item, type book, title The Catcher in the Rye, author J.D. Salinger, pages 220"; "add a DVD, title Arrival, director Denis Villeneuve, duration 116" | 201 — "Successfully created book 'The Catcher in the Rye' with ID 5." | 400 — "Sorry, I couldn't do that: Missing field(s): page_count." |
| `PUT /api/items/<id>` | "replace item 5, title Franny and Zooey, author J.D. Salinger, pages 200" | 200 — "Item 5 has been replaced: it is now the book 'Franny and Zooey' by J.D. Salinger, 200 pages." | 400 ("replace item 5, title Test") — "Sorry, I couldn't do that: Missing field(s): author, page_count." · 404 |
| `PATCH /api/items/<id>` | "update item 5, pages 250", "change item 5, title Dune", "set item 3 title to Animal Farm" | 200 — "Item 5 has been updated: pages is now 250." | 400 — "Sorry, I couldn't do that: page_count must be a positive integer." · 404 |
| `DELETE /api/items/<id>` | "delete item 5", "remove item 5" | 204 — "Item 5, 'Franny and Zooey', has been deleted." | 409 — "Sorry, item 5 is checked out and cannot be deleted." · 404 |
| `POST /api/items/<id>/checkout` | "check out item 5", "checkout item 5", "borrow item 5" | 200 — "Item 5, 'Franny and Zooey', has been checked out." (DVDs add "Handle with care: Do not scratch the disc.") | 409 — "Sorry, item 5 is already checked out." · 404 |
| `POST /api/items/<id>/return` | "return item 5", "give back item 5", "bring back item 5" | 200 — "Item 5, 'Franny and Zooey', has been returned. Thank you!" | 409 — "Sorry, item 5 is not checked out." · 404 |

Other phrases:

- **"help"**: the librarian lists the commands.
- Anything else, e.g. "sing me a song": *"Sorry, I didn't understand that. Say 'help' to hear what I can do."*

### Voice API

Both routes always answer HTTP 200; the real API status is in `status`.

```http
POST /api/voice          multipart/form-data, field "audio"
POST /api/voice/text     {"text": "check out item 4"}
```

```json
{
  "transcript": "Check out item 4.",
  "command": {"intent": "checkout", "method": "POST", "path": "/api/items/4/checkout",
              "body": null, "query": {}, "item_id": 4},
  "api_call": "POST /api/items/4/checkout",
  "status": 200,
  "result": {"message": "Successful checkout. Handle with care: Do not scratch the disc.", "item": {"...": "..."}},
  "message": "Item 4, 'Arrival', has been checked out. Handle with care: Do not scratch the disc.",
  "audio": "<base64 WAV>"
}
```

`status` is `422` when no speech was recognized or the recording is empty or
shorter than 0.5 s ("I didn't hear anything"), `500` when ffmpeg or Azure
fails (the full traceback is printed in the server console), and `null` for "help" and
unknown commands (no API call is made).

## Tests

Start a **fresh** server before each test run (data lives in memory):

```powershell
cd MiniProject2
..\venv\Scripts\python.exe -m flask --app app run --port 5000
```

In a second terminal:

| Script | What it does |
|---|---|
| `test_text_commands.py` | Sends 19 typed commands to `/api/voice/text` (list, create, get, update, replace, check out, return, delete, help, unknown) and prints expected vs. actual status. `NEW` is the ID from the first create (5). |
| `make_test_audio.py` | Uses Azure TTS to create 6 spoken commands in `test_audio/`. |
| `test_voice_audio.py` | Sends those WAV files to `/api/voice` and checks the transcript, the REST call and the status. |

```powershell
..\venv\Scripts\python.exe test_text_commands.py     # 19/19 passed
..\venv\Scripts\python.exe make_test_audio.py
# restart the server, then:
..\venv\Scripts\python.exe test_voice_audio.py       # 6/6 passed
```
