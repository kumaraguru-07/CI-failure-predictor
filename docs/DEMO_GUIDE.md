# Demo and handover guide

## Open the project

Project folder: D:\Balu project\failure-aware-ci.
Repository: https://github.com/kumaraguru-07/CI-failure-predictor.

Double-click Start dashboard.cmd. Keep the opened window running. Open
http://127.0.0.1:8501 if the browser does not open automatically. Press Ctrl+C
in that server window when finished. Do not start another copy on the same port.

No Docker or separate cloud application is required. The local model and prepared
data are already present on this PC. A fresh checkout requires those local
artifacts to be restored or rebuilt as documented in DATASET.md and TRAINING.md;
the raw research dataset is deliberately not part of Git.

## Suggested five-minute presentation

1. Explain the goal: estimate risk before required tests, then keep all checks.
2. In Explore builds, filter a repository/risk band and analyze one recorded build.
   Point out the probability, recorded outcome, signed signals and imputation note.
3. In Predict from CSV, upload docs/examples/feature_input.csv and explain one row.
   These are invented demonstration features, not measured real commits.
4. Open Model results. Show the six-model validation comparison and frozen test
   precision/recall. State that false alarms and missed failures remain substantial.
5. Open CI outcome history. Show the imported real prediction and actual outcome.
   This is durable local history, not the temporary Session history page.
6. Open the repository's Actions page. Show prediction before required tests and
   the actual-outcome artifact. The job result must come from tests, not prediction.
7. Download an explanation or history export. End with the limitations and future work.

Do not promise an exact risk band for a synthetic example. Use the current model
output. A LOW band does not guarantee success. Do not retrain or change thresholds
during a presentation, since the test evaluation has already been inspected.

## Commands for technical verification

Run from the project folder:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m src.final_audit
.\.venv\Scripts\python.exe -m src.verify_ci
.\.venv\Scripts\python.exe -m src.verify_dashboard
```

The final audit checks artifact integrity without generating new test predictions.
The offline CI command writes reports/CI_LOCAL_VERIFICATION.json; it preserves
the hosted evidence in reports/STEP_7_VERIFICATION.json.

For the complete dependency snapshot used locally, see requirements-tested.txt.
It pins tested direct packages, not every transitive dependency. GitHub CI uses
requirements-ci.txt plus the application requirements. Run tests after installing
dependencies in a new environment rather than assuming identical behavior.

## Show or repeat hosted CI

Open https://github.com/kumaraguru-07/CI-failure-predictor/actions.
The Quality workflow runs for pushes and pull requests; it can also be run
manually on GitHub. It uses the already configured model URL and SHA256 variables.
A manual hosted run consumes runner resources and creates another real record.

Prediction failure produces an unavailable report and does not suppress required
tests. HIGH risk also does not skip checks or merge code. No branch-protection
policy was changed by this project; required-merge gates are a separate setting.

## Refresh persistent CI history

Download the outcome artifact from a completed workflow and locate
prediction_outcome.json. Import it from the project folder:

```powershell
.\.venv\Scripts\python.exe -m src.ci_history --import-outcomes PATH_TO_prediction_outcome.json --database data/ci/predictions.sqlite3
```

Then refresh CI outcome history in the dashboard. Imports are idempotent and cannot
silently replace a conflicting actual outcome. Cancelled/skipped jobs do not become
successful builds. Per-run GitHub artifacts retain their configured 90-day lifetime;
local imports provide longer-term history. The dashboard does not poll GitHub.

## Recovery

- Port already in use: use the existing app, stop its own server window, or choose
  a different port. Do not stop unrelated Python applications.
- Missing local data/model: restore the frozen artifacts. Do not casually rerun
  training to recreate a score after the test has been inspected.
- CSV rejected: use the template's exact feature headers; numeric values or empty
  cells only; check 0..1 rates, valid time ranges, 500 rows and 5 MB limits.
- Model/package mismatch: use the trusted released package and its published SHA.
- GitHub access/rate failure: inspect the advisory status and retry collection
  when access is restored; the required tests still run.
- Empty persistent history: import an outcome export. Session history is separate.

## Files to present

- PROJECT_REPORT.md: complete methodology, results and limitations.
- VIVA_QA.md: concise questions and answers.
- reports/TRAINING_RESULTS.json: exact recorded metrics and environment.
- reports/FINAL_ACCEPTANCE.json: final integrity checks.
- reports/STEP_7_VERIFICATION.json: hosted deployment evidence.
- reports/STEP_8_COMPLETION.md: final acceptance and known boundaries.
