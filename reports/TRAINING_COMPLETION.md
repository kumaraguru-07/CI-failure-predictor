# Model training completion — 2026-11-15

Status: initial model training and saved-model inference complete.

| Candidate | Validation average precision |
|---|---:|
| Baseline Logistic Regression | 0.1388 |
| Baseline Random Forest | 0.1685 |
| Baseline XGBoost | 0.1698 |
| Enhanced Logistic Regression | 0.1633 |
| Enhanced Random Forest | 0.2059 |
| Enhanced XGBoost | 0.1982 |

Enhanced Random Forest won on validation AP only. Six fixed candidates provide
an initial feature comparison, not evidence of statistical significance.
All-missing/constant feature removal and imputation use training rows only;
standardization is used only for LR. No class weighting or resampling is applied.

## Frozen risk cutoffs

LOW: probability below 0.025552616731219203. MEDIUM: at or above that value,
below 0.1306823416597925. HIGH/binary warning: at or above 0.1306823416597925.
HIGH maximizes validation F1; LOW retains at least 90% validation recall, capped
at HIGH. These are score bands, not calibrated probability guarantees. Required
CI checks still run.

## Single held-out test evaluation

22,075 runs, 1,043 failures (4.72%). AP 0.1466; ROC-AUC 0.7631; Brier 0.04360;
precision 15.02%; recall 45.16%; F1 0.2255 at the frozen cutoff.
Confusion counts: TN 18,368, FP 2,664, FN 572, TP 471.

The model catches 471 failures and misses 572. Most warnings are false positives.
Test performance is lower than validation performance. This is an initial research
baseline, not a production-readiness or calibration claim. Do not tune against
this test result. Future model changes require a new held-out period.

## Verification and handoff

Thirteen tests pass. Saved artifact reload predictions match the fitted pipeline.
Inference returns probability, risk band and binary warning using the exact saved
numeric feature contract. Metadata and labels are excluded from inputs.

Artifact: models/baseline_v1/model.joblib. Frozen pre-test selection and row-level
test predictions remain beside it, ignored by Git. Aggregate comparisons, metrics,
hashes and environment versions: reports/TRAINING_RESULTS.json. Reproduction and
inference instructions: docs/TRAINING.md.

Next: explanations/recommendations, dashboard, live GitHub/Actions integration,
integration tests and final documentation. Dataset provenance, missing paths,
repeated commits and online-history limits from docs/DATASET.md still apply.
