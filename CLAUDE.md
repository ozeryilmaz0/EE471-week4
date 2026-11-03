# Project rules for Claude

Always follow these rules in this repository.

## Environment
- OS is Windows; the terminal is PowerShell.
- Use the virtual environment at the repo root for Python: `venv\Scripts\python.exe`.
- If a package is missing, install it into this venv (`venv\Scripts\python.exe -m pip install <pkg>`), never globally.

## Secrets
- NEVER read, print, display, or commit the `.env` file.
- The apps load the Azure key themselves via `python-dotenv`; do not touch it.

## Git
- Always run `git status` before committing and review what is staged.
- Never commit: `.env`, `venv/`, `*.wav`, `*.avi`, `*.mp4`, `uploads/`, `test_audio/`, `hub/`, `payload.json`, `VIDEO_*.md`.
- All of the above must be listed in `.gitignore`; add any that are missing.

## Processes
- Stop any servers or containers started in the background once the task is done.
- Ports 5000-5003 must be left free.

## Language
- Code, code comments, and UI text: English.
- Explanations to the user: Turkish.

## Reporting
- At the end of every major task, summarize in Turkish as bullet points:
  - what was done,
  - test results,
  - whether the user needs to do anything.

## User intervention
- If something requires the user (password, admin rights, GUI, microphone), stop and tell the user exactly what they need to do.
