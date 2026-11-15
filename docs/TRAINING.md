# Model training and prediction

Run from the project folder:

```powershell
py -3.13 -m src.train --output models/baseline_v1
py -3.13 -m src.predict --model models/baseline_v1/model.joblib --input data/processed/validation.parquet
```

Training refuses an existing output directory to protect a completed experiment.
Do not rerun experiments to improve the already inspected test score. Future model
changes need a new held-out period before they support new final test claims.

## Frozen experiment design

Compare Logistic Regression, Random Forest and XGBoost on two feature sets:
the baseline commit/project-history set and the expanded history set. Each model
has fixed, lightweight parameters and seed 42. All six candidates fit only the
training partition. There is no grid search, resampling, class weighting or GPU.

Remove all-missing and constant features using training data only. Fit median
imputation (with missing indicators) on train only; standardize inputs only for
Logistic Regression. All learned transformations remain inside the saved pipeline.
No file-based feature can be learned from the current dataset because paths are absent.

Choose the candidate with greatest validation average precision (AP). AP summarizes
the precision-recall curve without trapezoidal interpolation. It is the selection
metric because failures are rare. Record ROC-AUC, Brier score, precision, recall,
F1 and confusion matrix as additional diagnostics. Constant training prevalence
and the observed project-history score are validation benchmarks.

Select the HIGH/binary threshold by maximum validation F1, resolving ties toward
the higher threshold. Select the LOW boundary as the highest validation threshold
retaining at least 90% recall, capped at the HIGH boundary. If equal, the MEDIUM
band is empty. Risk levels are relative model-score bands; a LOW score does not
guarantee a successful build. Mandatory tests still run.

Freeze model, feature list, thresholds, environment versions and validation report
before reading test targets. Evaluate only the winner on test once. Do not refit
on train+validation: the saved artifact is exactly the model that was evaluated.
Verify saved-model reload predictions match the original fitted model.

## Artifacts

- models/baseline_v1/model.joblib: pipeline, feature order, thresholds and versions.
- models/baseline_v1/validation_selection.json: frozen pre-test selection record.
- models/baseline_v1/results.json: validation comparisons and single final test result.
- models/baseline_v1/test_predictions.parquet: test probabilities/targets aligned
  by row to data/processed/test_metadata.parquet.
- reports/TRAINING_RESULTS.json: aggregate copy for review and Git history.

Model artifacts and row-level predictions are ignored by Git. The aggregate
report records SHA256 hashes for partitions and model. Load only trusted local
joblib artifacts; their deserialization executes code. Reuse the saved package
versions recorded in results.json when loading the model elsewhere.

## Limits

Scores are probability estimates without a separate calibration stage. Brier score
is reported; neither operational calibration nor confidence intervals are claimed.
The dataset contract and exclusions in docs/DATASET.md still apply: workflow-run
attempt evaluation, repeated commits across partitions, one chronological split,
unknown individual platform provenance, and online replay of earlier completed
outcomes. This is not evidence of performance on a new repository.
