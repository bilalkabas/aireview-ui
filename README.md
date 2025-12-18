# Review Evaluation Console

This repository hosts the reviewer evaluation console used to inspect papers, assign metrics, and leave evaluator comments.

## Quick Start for Evaluators

1. Clone or download the repository.

```
git clone https://github.com/bilalkabas/aireview-ui.git
```

2. Open up a terminal window and go into the project directory.
3. Run the below command (this will install requirements, download PDFs, and open the app)

```
./run
```

4. **Wait for the browser tab** to open at `http://localhost:8090/index.html`. You can quit any time with `Ctrl+C` in the terminal.  

5. **Resume later** by running `./run` again; your virtualenv and data persist between sessions.

> **macOS note:** If Homebrew isn’t installed, the script stops and asks you to install Python 3 manually (from https://www.python.org/downloads/) before rerunning.

## Troubleshooting

**macOS: SSL certificate verify failed**
- Error: `urllib.error.URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] ...>`.
- Fix (python.org build): in Terminal run `open "/Applications/Python 3.11/Install Certificates.command"` (adjust `3.11` according to your Python version under `/Applications`).

## What the `run` Script Does
- Loads configuration from `.env` (paths, port, etc.) so the server finds reviews and PDFs no matter where the repo lives.
- Detects Python 3.8+; if it is missing, it calls the platform package manager (Homebrew, apt, winget, …) and may prompt for admin rights.
- Creates or reuses a virtual environment at `.venv`, upgrades `pip`, and installs dependencies from `webapp/requirements.txt`.
- **Downloads PDFs** from GitHub releases (configured via `WEBAPP_GITHUB_RELEASES_PDF_URL` in `.env`) - automatically skips if files already exist.
- Exports the resolved paths for the backend, starts `server.py`, and opens the evaluation console in your default browser.
- Supports overrides like `./run --port 8100`, `./run --no-browser`, or `./run --skip-download` when you need a custom setup.

If the automated installer cannot add Python on your machine, install Python 3 manually, and re-run the script.
