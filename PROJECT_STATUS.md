# Project status

## Phase 1: planning and repository

Scope and architecture frozen. Local Git repository initialized. Python 3.13
is available. A local .venv reuses installed base packages and adds SHAP locally;
it is not a fully isolated dependency lock. No remote repository is configured.

## Phase 2: dataset and preprocessing

Completed and audited on 2026-11-15: verified download checksum; 303,079 input
rows, 146,110 eligible rows from 32 repositories. Final partitions contain
102,664 train / 20,409 validation / 22,075 test rows; 962 boundary-crossing
rows are purged from fitting/selection. Nine correctness tests and full saved-file
verification pass. See reports/STEP_2_COMPLETION.md and docs/DATASET.md.
Filtering is substantial: results apply only to the eligible timestamped binary
outcome cohort, not the full dataset. Startup failures count as failures.

Dataset: Joshua Faruna and Funmilayo Sanusi, Mendeley version 1,
https://data.mendeley.com/datasets/mggwn7rj9f/1 (CC BY 4.0).
The publisher describes a mixture of TravisTorrent and GitHub Actions data.
Do not describe all records as GitHub Actions. The raw download is ignored by Git.
Expected raw SHA256: b6a89418e39e6144f4ac71496256474c7bc27651e099557fe074d7798da1e73e.

Run from the project folder:

```powershell
py -3.13 -m src.prepare --input data/raw/final_research_dataset_MASTER.csv
.\.venv\Scripts\python.exe -m pytest -q
```

The pipeline normalizes timestamps to UTC, accepts only explicit binary
success/failure labels, drops invalid timestamps, excludes nonterminal/unknown
outcomes, deduplicates repository/build IDs, and writes an audit plus 70/15/15
chronological partitions. Fractions apply to distinct start timestamps, keeping
ties together. Actual split sizes and missingness are in reports/dataset_audit.json.
Metadata and identifiers are separate from the numeric feature matrix.
Train/validation labels must also be available before the next partition starts.
The cleaned canonical table is saved in data/interim/builds_clean.parquet.

## Phase 3: feature engineering

Implemented commit churn, file count, time of day/week, project failure history,
last 5/10 completed outcomes, failure streak, elapsed time since last failure,
author history and recent author history. Only builds completed strictly before
prediction time contribute; overlapping or simultaneous builds cannot leak labels.
History crosses split boundaries by sequential replay of already observed outcomes.
Evaluation therefore represents continuous online use, not a frozen-history batch.

The optional changed_files JSON-list contract enables touched-file history,
dependency/config/workflow/Docker flags and directory counts. The selected dataset
has no paths, so these features remain missing. There is no fabricated file history.
Cold starts use missing rates plus history counts. Imputation is fit on train
only; scaling is included only for Logistic Regression. Author identifiers are
never model inputs.

## Phase 4: model training — complete

Six fixed-budget candidates (LR, RF, XGBoost with baseline/enhanced features) were
compared on validation average precision. Enhanced Random Forest won (0.2059).
The model, feature contract and thresholds were frozen before test evaluation.
Artifact: models/baseline_v1/model.joblib; it remains fit on train only.

Single held-out test: AP 0.1466, ROC-AUC 0.7631, precision 0.1502, recall 0.4516,
F1 0.2255. These are initial research results with substantial false alarms.
Full results: reports/TRAINING_RESULTS.json and reports/TRAINING_COMPLETION.md.
Thirteen tests and saved-model inference pass.

## Phase 5: explanations and recommendations — complete

Step 5 is complete: probability-space SHAP explanations and advisory CI
recommendations are fully audited. All 24 tests pass. Forty real validation records
and an all-missing-input boundary case pass, with maximum reconstruction error
2.249e-8. Readable report: reports/explanation_example.md; verification evidence:
reports/STEP_5_VERIFICATION.json. A labeled permutation-SHAP fallback covers library
edge cases, and optional change flags add only evidence-supported advice.
The model/test results remain frozen. See docs/EXPLANATIONS.md and
reports/explanation_example.json. Docker/cloud apps are not required.

## Phase 6: local dashboard — complete

app.py provides build exploration, CSV predictions, per-build SHAP/CI advice,
saved model evaluation and session history. The Windows launcher is
Start dashboard.cmd. Data/model caching is bounded; explanations compute on
Analyze clicks only. Uploaded files are validated and remain in memory.

All 32 tests pass, including UI navigation, historical/CSV explanation flows,
stale-result hiding, history clearing, invalid uploads and missing-file recovery.
AppTest also exercised all four views with 20,409 real validation builds and
the frozen model. Evidence: reports/STEP_6_VERIFICATION.json. The model and
frozen evaluation checksums are unchanged. Native browser dialog/layout behavior
has not been visually inspected; see docs/DASHBOARD.md for verification limits.

## Phase 7: CI integration — complete and hosted

Implemented the GitHub read-only collector, portable model package (about 4.9 MB),
advisory prediction job, unconditional required tests after prediction, and
required-tests outcome collection into SQLite/per-run artifacts. Outcome imports
are idempotent. Private release-asset downloads are supported without exposing
authorization on storage redirects.

All 50 tests pass. A real read-only reference-repository snapshot was collected
in three API requests; the model package reproduces its probability exactly.
That reference repository had zero prior Actions records. Subsequently, the
project's own hosted workflow completed prediction, all 50 required tests and
actual-outcome recording. The frozen model/evaluation are unchanged. See
docs/GITHUB_ACTIONS.md and reports/STEP_7_VERIFICATION.json.

The user selected the existing public repository kumaraguru-07/CI-failure-predictor
and explicitly approved publication of the model and its 100 derived numeric
background rows. Code, the ci-model-v1 release and both Actions variables are
published. Workflow run 43699059875 succeeded. Its MEDIUM prediction (10.05%)
was joined to the successful required-test result and imported into the local
SQLite ledger. Earlier local development history is preserved on local-development;
main tracks origin/main. This single successful run is integration evidence,
not new model-accuracy evidence.

## Remaining final work

- The Step 2 audit is complete. Confirm platform provenance before claiming
  modern-only results; missing execution times exclude many legacy rows.
- Complete integration tests, user documentation and the final report. The test
  evaluation is frozen; future model changes require a new held-out period.

Performance claims apply only to the audited eligible workflow-run cohort.
