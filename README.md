# Failure-Aware Continuous Integration

Predict CI build-failure risk from commit metadata and **only** the history
available before a build starts.

## Open the dashboard

On this PC, double-click `Start dashboard.cmd` in the project folder. It opens
the local app at http://127.0.0.1:8501. Keep its window open while using the app;
press Ctrl+C in that window to stop it. No Docker or cloud account is needed.
See docs/DASHBOARD.md for the four views, input template and troubleshooting.

## Project scope (frozen)

### Must deliver

- Leakage-safe dataset preparation and chronological train/validation/test split.
- Commit and historical CI features: churn, changed files, recent project and author failure history, touched-file history, and dependency/configuration change flags.
- Logistic Regression and tree-based model comparison, selected on validation data only.
- Failure probability, Low/Medium/High risk band, explanation, and CI advice.
- A small local dashboard and a GitHub Actions demonstration after the model is trained.

### Explicitly out of scope for the MVP

- Skipping required tests, automatic merge decisions, test-level failure prediction, cloud deployment, Docker/Kubernetes, and a complex frontend.

## Architecture

```text
historical CI data + commit metadata
              |
      leakage-safe preprocessing
              |
       chronological split
              |
      train / validate / test
              |
saved model + feature contract
              |
commit feature extractor --> probability --> risk + explanation + CI advice
```

The prediction only recommends test prioritisation; mandatory checks still run.

## Getting started

1. Use the existing local `.venv` (Python 3.13 on this PC), or create a compatible Python environment.
2. For a fresh environment, install dependencies: `pip install -r requirements.txt`
3. Put an approved raw dataset in `data/raw/` (never commit it).
4. Copy/adapt `config/project.yaml` for the dataset schema.
5. Run preprocessing once a dataset is available:

   ```powershell
   python -m src.prepare --input data/raw/final_research_dataset_MASTER.csv
   ```

## Repository layout

- `src/` — reusable data, feature, training, and inference code.
- `config/` — versioned, dataset-independent settings.
- `data/` — local raw/interim/processed data; ignored by Git.
- `models/` — locally generated trained models; ignored by Git.
- `reports/` — generated metrics and figures; ignored by Git.
- `tests/` — small correctness tests, especially leakage prevention.
- `.github/workflows/` — CI validation and later prediction demo.

## Dataset rule

Use a GitHub Actions dataset if its columns and licence allow research use;
otherwise begin with a manageable TravisTorrent subset. Do not use current-build
outcome, duration, failed-test count, or logs as input features for that build.

## Status

Dataset preparation and available historical features are complete. See
PROJECT_STATUS.md and reports/dataset_audit.json for the verified cohort, splits,
missing feature limitations and next steps.
Step 2's full column contract is in docs/DATASET.md; the final verification and
counts are in reports/STEP_2_COMPLETION.md.

Model training is complete. The saved winner is
`models/baseline_v1/model.joblib` (enhanced Random Forest). See docs/TRAINING.md
and reports/TRAINING_RESULTS.json. The held-out test evaluation is frozen;
future model changes require a new held-out period.

Step 5 is complete: per-prediction SHAP explanations and CI recommendations.
Run `.\.venv\Scripts\python.exe -m src.explain --limit 3` for examples.
Add `--markdown reports/explanation_example.md` for a readable report.
Run `.\.venv\Scripts\python.exe -m src.verify_step5` for the full Step 5 check.
See docs/EXPLANATIONS.md. Run all tests with
`.\.venv\Scripts\python.exe -m pytest -q`.

Step 6 is complete: the local dashboard supports historical build exploration,
feature CSV predictions, SHAP explanations, CI advice, saved model results and
session history with downloads. All 32 tests pass. Real-artifact verification:
`.\.venv\Scripts\python.exe -m src.verify_dashboard`.

Step 7's local integration is ready: GitHub commit/history collection, advisory
prediction before required tests, a portable model package and a persistent
prediction/outcome ledger. All 50 tests pass. See docs/GITHUB_ACTIONS.md.
GitHub is connected as kumaraguru-07. Hosted activation is pending the browser
sign-in required for repository creation/release setup; no repository has been
created or workflow executed remotely yet.


