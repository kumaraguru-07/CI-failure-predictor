# Step 2: dataset and preprocessing contract

## Source and reproducibility

Dataset: Joshua Faruna and Funmilayo Sanusi, *A comprehensive GitHub Actions
dataset for CI/CD pipeline failure forecasting*, version 1,
https://doi.org/10.17632/mggwn7rj9f.1
License: CC BY 4.0, https://creativecommons.org/licenses/by/4.0/.
Changes: filtered, normalized, deduplicated and transformed into numeric features.
The publisher describes a mixture of historical TravisTorrent and GitHub Actions
records; platform membership has not been verified for individual rows.

Raw file: final_research_dataset_MASTER.csv (194,638,363 bytes).
SHA256: b6a89418e39e6144f4ac71496256474c7bc27651e099557fe074d7798da1e73e.
The pipeline refuses a different checksum. Tests explicitly disable this check
only for generated fixtures. Keep original data unchanged and outside Git.

## Column mapping

| Raw column | Canonical column / role |
|---|---|
| repo, fallback repo_name | repository; history grouping, never model input |
| run_id + run_attempt (default 1) | identity within repository |
| run_started_at | started_at, UTC prediction time |
| updated_at | completed_at; conservative outcome availability proxy |
| conclusion | build_failed target, never an input |
| author_email, author_name, author | history key, never model input |
| additions | lines_added |
| deletions | lines_deleted |
| files_modified | files_changed_total |
| commit_sha | metadata for overlap diagnostics, never model input |
| All remaining raw columns | excluded from the model matrix |

Outcome policy: success/passed = 0; failure/failed/error/errored/startup_failure = 1.
Cancelled, skipped, pending, missing and unknown outcomes are excluded, never
treated as successes. This is binary prediction conditional on an eligible final
outcome, not a predictor of cancellation or scheduling problems.

Missing numeric inputs stay missing for training-only imputation. Negative or
infinite metrics are invalid. Missing author history uses the unknown-history
state. No outcome, duration, log, status, identity or author strings enter the
feature matrix. No file paths exist in this source; path-derived features stay
missing rather than being reported as no change.

## Cleaning, splitting and saved outputs

All exclusions are sequential and mutually exclusive in reports/dataset_audit.json.
Input rows equal retained rows plus exclusions. Conflicting duplicate identities
are quarantined; redundant consistent snapshots are collapsed. A build identity
includes the attempt number. Missing times are excluded rather than substituting
commit times or estimating completion from a duration field.

Distinct start timestamps determine approximate 70/15/15 cutoffs. Ties remain in
one partition. Training labels must be available before validation starts;
validation labels must be available before test starts. Rows crossing those
boundaries are purged from fitting/selection sets. Test labels are used only for
the eventual final evaluation, not model choice.

- data/interim/builds_clean.parquet: eligible canonical rows and history keys.
- data/processed/{train,validation,test}.parquet: numeric features plus target.
- data/processed/{train,validation,test}_metadata.parquet: aligned row identity,
  commit SHA and execution timestamps; never train on these files.
- reports/dataset_audit.json: checksum, exclusion counts, missingness, distributions,
  repository count, split sizes and ranges, boundary purges and commit overlap.

Raw data and row-level outputs are ignored by Git. The audit is aggregate only.
Historical features replay outcomes only after their availability time, across
partition boundaries. This represents continuous online prediction. The unit is
a workflow-run attempt; repeated commit SHAs across partitions are measured and
must not be described as an unseen-commit experiment.

## Rebuild and verify

From the project directory:

```powershell
py -3.13 -m src.prepare --input data/raw/final_research_dataset_MASTER.csv
.\.venv\Scripts\python.exe -m pytest -q
```

The checksum is verified before parsing. Outputs are deterministically ordered.
No imputation, scaling, resampling, model training or test-based tuning occurs
during Step 2. Those belong to training and must fit on training data only.
