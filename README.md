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

## Ensemble Phase Console (`./run_ensemble`)

The ensemble phase uses a second, self-contained UI. Start it with:

```
./run_ensemble
```

It opens `http://localhost:8091/ensemble.html` (port 8091 by default, so it can run alongside `./run`)
and serves `reviews/evaluation-data-ensemble.json` — reviews only, no harmonized variants and no
evaluator assignments.

On first visit the console asks for the evaluator's **name** and which **category** they will
evaluate (CT imaging / MRI imaging / Image analysis). Both are final: the paper list is limited to
that category and links to papers outside it are refused. They are written into the data file
itself — `evaluator_name`, `evaluator_category` and `evaluator_category_at` on every paper, plus the
existing `evaluators` list — so they survive into processing and cannot be re-entered by clearing
the browser.

The order of the papers and of the reviews within each paper is randomised per evaluator. A seed is
drawn once, when the evaluator is registered, and stored as `display_seed`; the shuffle uses a
32-bit integer PRNG (mulberry32), so the same seed reproduces the same order on any machine,
browser, or OS.

A guided tour runs once for a newly registered evaluator — first on the paper list, then again the
first time a paper is opened — and can be replayed from the **Tour** button in the header.

Each paper is evaluated in two stages, shown as tabs:

1. **Pre-task** — your own reading of the manuscript, before seeing any review:
   a provisional recommendation (Reject / Reject-Resubmit / Accept with Minor Revision / Accept),
   your confidence in it (1–7), up to three major concerns, and up to three major strengths.
   The reviews are not loaded into the page until this is submitted, and submitting locks the
   answers (they stay readable, but cannot be edited).
2. **Review Evaluation** — unlocked right after submitting the pre-task. Every review is rated on a
   7-point Likert scale against the Stage 3 rubric: Accuracy/Rigor, Specificity, Novelty,
   Decisiveness, and Integrity/Usefulness — plus a free-form comment. Everything is saved back
   to the JSON as you go.

PDFs are **never downloaded** in this phase — put the TMI PDFs in `AI4TMI_pdfs/` in the project
root (matching each paper's `url`) and the launcher reports how many it found at startup.

Timestamps are recorded per paper under `timing`: `pretask_started_at` /
`evaluation_started_at` are stamped by the first activity in each stage, and
`pretask_ended_at` / `evaluation_ended_at` are rewritten by every subsequent activity, so the last
one recorded is the real end.

A **Download JSON** button in the header of both pages saves the current results file, named after
the evaluator and category (e.g. `evaluation-jane-doe-ct-imaging.json`).

Options: `./run_ensemble --port 8100`, `--no-browser`.

Configuration (all optional, in `.env`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `WEBAPP_ENSEMBLE_REVIEWS_JSON` | `reviews/evaluation-data-ensemble.json` | Dataset served in this phase |
| `WEBAPP_ENSEMBLE_PORT` | `8091` | Server port |
| `WEBAPP_ENSEMBLE_PDFS_ROOT` | `.` (project root) | Directory the paper `url` values are relative to |
| `WEBAPP_ENSEMBLE_PDFS_SUBDIR` | `AI4TMI_pdfs` | Sub-directory holding the PDFs (checked at startup) |
| `WEBAPP_ENSEMBLE_ADMIN_MODE` | `false` | `true` shows reviewer labels (reveals AI vs human) |

## Evaluation & Analysis

To analyze the collected review data and generate performance reports (Human vs AI, Turing Tests, etc.):

**Generate Comprehensive Reports**:
Run the master evaluation script to generate reports (LaTeX and Markdown) across all normalization settings:

```bash
python -m eval.run_all_evaluations
```
Measurements and plots will be saved in `eval/report_output/` under subdirectories like `norm_none`, `norm_evaluator`, etc.

**Outputs to check**:
*   `eval/report_output/norm_<method>/report.md`: Readable Markdown report.
*   `eval/report_output/norm_<method>/report.tex`: Source for PDF report.
*   `eval/report_output/norm_<method>/plots/`: Visualization figures.
