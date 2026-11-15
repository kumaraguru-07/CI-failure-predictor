# Failure-Aware Continuous Integration
## Predicting build and pipeline failures from commit and historical signals

**Final implementation report — 15 November 2026**

Repository: https://github.com/kumaraguru-07/CI-failure-predictor

### Abstract

This project implements a research prototype that estimates CI failure risk before
a required test job executes. It combines commit-change measurements with only
the build outcomes available at prediction time, compares three model families,
and presents a failure probability, a risk band, per-prediction explanations and
advisory CI recommendations. A local Streamlit dashboard supports historical
exploration, feature-CSV prediction and recorded prediction/outcome review.
GitHub Actions runs prediction before required tests and preserves the actual
test result in downloadable artifacts and a local SQLite ledger.

From a 303,079-record research dataset, 146,110 records passed the specified
identity, label and execution-time checks. After removing 962 rows whose labels
crossed training/validation boundaries, 145,148 records formed chronological
partitions. Six baseline/enhanced candidates were compared using validation
average precision. Enhanced Random Forest was selected. Its single held-out
evaluation yielded average precision 0.1466, ROC-AUC 0.7631, precision 0.1502,
recall 0.4516 and F1 0.2255 at a validation-selected threshold. These results
support an initial warning prototype, with substantial false alarms and missed
failures. They do not establish production readiness or accuracy on new
repositories. The hosted integration has been demonstrated without skipping
mandatory tests.

### 1. Problem and objectives

CI normally reports an outcome after executing build and test work. Early risk
estimation may help developers review changes and arrange fast feedback. The
project asks whether commit measurements and already-observed repository history
can provide useful ranking and explanations before a new execution finishes.

The objectives are to:

1. Prepare an auditable binary-outcome dataset without current-build leakage.
2. Compare simple and tree-based models using chronological evaluation.
3. Derive interpretable warning bands using validation data.
4. Explain individual model scores and provide advisory CI guidance.
5. Connect a frozen model to a dashboard and a real GitHub Actions workflow.
6. Store predictions with subsequent actual outcomes for monitoring.

The implementation predicts workflow-run-style binary failure risk. It does not
predict failure root causes, individual test failures or pipeline-stage labels.
Recommendations do not implement an automatic test scheduler, skip required tests,
or approve merges.

### 2. Reference approach and contribution

The methodological reference is shriyachoksi/build-failure-predictor [1].
Useful concepts include pre-execution features, historical failure signals,
chronological splitting and comparison of Logistic Regression, Random Forest and
XGBoost. The present code was written independently rather than cloning and
renaming that implementation.

The implemented contributions are an explicit label-availability audit, exclusion
accounting, training-only preprocessing, validation-only model selection,
completion-time history replay, additional author/recent-history signals,
per-prediction SHAP explanations, a local dashboard, and a portable model with
hosted prediction/outcome collection.

The experiment is an internal baseline/enhanced comparison on this project's
audited cohort. It is not an exact reproduction of all the reference repository's
features, and its scores must not be directly compared with scores obtained on a
different dataset or split. No claim of a new state-of-the-art algorithm is made.

### 3. Scope and technology choices

| Component | Choice | Purpose |
|---|---|---|
| Runtime | Python 3.13 on the development PC and CI | One language for the pipeline |
| Tables | pandas, NumPy, Parquet/PyArrow | Cleaning and feature storage |
| Models | scikit-learn, XGBoost | Fixed-budget model comparison |
| Artifact | joblib with an externally pinned checksum | Frozen pipeline and feature contract |
| Explanations | SHAP | Signed score contributions |
| Dashboard | Streamlit | Local interactive interface |
| Outcome storage | SQLite | Persistent local prediction/result ledger |
| CI | GitHub Actions | Prediction, required tests and outcome recording |
| Tests | pytest and Streamlit AppTest | Logic and application behavior |

No separate API server, React frontend, Docker, database server or cloud deployment
platform is required. The dashboard runs locally; the CI demonstration uses
GitHub-hosted runners. Exact tested direct package versions are recorded in
requirements-tested.txt. The development environment reuses base packages and is
not claimed to be a fully isolated transitive lock.

### 4. Architecture and module responsibilities

Offline preparation follows:

    Original research CSV
      -> schema/label/time validation and exclusion audit
      -> canonical cleaned rows
      -> completion-aware historical features
      -> chronological train / validation / test
      -> training-only transformations and six candidate models
      -> validation selection and frozen thresholds
      -> one held-out test evaluation
      -> saved model and portable CI package

The operational flow is:

    Commit metadata + prior completed workflow runs
      -> feature snapshot
      -> verified frozen model
      -> probability + risk band + explanation + CI advice
      -> mandatory tests
      -> actual outcome artifact
      -> persistent local ledger and dashboard history

| Module | Responsibility |
|---|---|
| src/dataset.py | Dataset-specific normalization and exclusion accounting |
| src/features.py | Features using only previously available outcomes |
| src/split.py | Time ordering, timestamp ties and boundary-label purging |
| src/prepare.py | Canonical data, partitions, metadata and audit |
| src/train.py | Fixed experiment, validation selection and frozen evaluation |
| src/predict.py | Saved feature-contract inference |
| src/explain.py | Additive explanations and readable exports |
| src/recommendations.py | Risk/evidence-based advisory guidance |
| src/dashboard_data.py, app.py | Dashboard services and user interface |
| src/github_features.py | Bounded read-only GitHub collection |
| src/ci_bundle.py | Portable model package export and verification |
| src/ci_predict.py | Pre-test operational prediction and summary |
| src/ci_history.py | Prediction/outcome recording and import |
| src/final_audit.py | Final artifact-integrity and boundary checks |

### 5. Dataset, target and preparation

The source is Faruna and Sanusi's dataset, version 1, published on Mendeley Data
under CC BY 4.0 [2]. The publisher describes a combination of TravisTorrent and
GitHub Actions records. A reliable platform discriminator has not been verified
for each retained row; therefore this study does not describe the entire cohort
as GitHub Actions-only.

The original file checksum is:

    b6a89418e39e6144f4ac71496256474c7bc27651e099557fe074d7798da1e73e

The outcome mapping accepts success/passed as 0 and
failure/failed/error/errored/startup_failure as 1. Missing, cancelled, skipped,
action-required and other unsupported outcomes are excluded, rather than counted
as successes. The target is conditional on an eligible binary final outcome.

| Preparation stage | Rows |
|---|---:|
| Original source | 303,079 |
| Excluded unknown/nonbinary outcomes | 134,492 |
| Excluded missing/invalid execution times after label filtering | 22,477 |
| Eligible cleaned cohort across 32 repositories | 146,110 |
| Additional boundary-label purges | 962 |
| Final partition total | 145,148 |

Other exclusion checks cover missing identities, reversed execution times and
conflicting/redundant duplicate identities; none removed additional rows in this
specific retained cohort. Identity includes repository, run ID and attempt.
All timestamps are normalized to UTC. updated_at is treated conservatively as
outcome availability, not asserted to be exact execution completion.

| Partition | Rows | Failures | Failure rate |
|---|---:|---:|---:|
| Train | 102,664 | 6,777 | 6.60% |
| Validation | 20,409 | 1,024 | 5.02% |
| Test | 22,075 | 1,043 | 4.72% |

Approximate 70/15/15 cutoffs are chosen from distinct start timestamps; ties stay
together. Training labels must be available before validation starts, and
validation labels before test starts. Boundary-crossing rows are removed from
fitting/selection. Metadata and identities are stored separately from numeric
model inputs.

Substantial filtering limits the study: conclusions concern the eligible cohort,
not every source record. The aggregate audit and column mapping are in
reports/dataset_audit.json and docs/DATASET.md.

### 6. Features and leakage controls

The baseline contains changed-file count, added/deleted lines, total churn,
weekday/hour and observed project failure rate. The enhanced saved model uses
15 nonconstant, nonempty numeric features: the baseline plus recent 5/10
failure rates, consecutive failures, elapsed time since last failure, author
overall/recent failure rates, and project/author history counts.

A history outcome contributes only when its recorded availability time is
strictly earlier than prediction time. Overlapping and equal-time completions
cannot leak labels. Historical state is scoped by repository; author keys do
not cross repositories. Raw author names/emails are not model inputs.

Cold starts use missing rates and explicit history counts. Missing values are
imputed with medians learned on training rows only. Missingness indicators remain
part of the saved transformation. Scaling is applied only to Logistic Regression.
All-missing and constant feature removal uses training evidence only.

The optional file-path contract implements touched-file history and
dependency/configuration/workflow/container change indicators. However, the
research source does not include changed-file paths. These features were not
empirically evaluated or learned by the frozen model. Live changed-file flags
can guide advice; no historically unstable file is invented as an explanation.

History is replayed continuously across partition boundaries after outcomes become
available. Thus evaluation simulates online observation of past outcomes, not a
single batch whose history is permanently frozen at the training cutoff.

### 7. Training, selection and risk bands

Three fixed-budget model families were fit on each feature set, using seed 42.
All six candidates fit training rows only. There is no grid search, resampling,
class weighting or GPU requirement. Validation average precision (AP) selects the
winner; AP is not presented as trapezoidally interpolated precision-recall area.

| Candidate | Validation AP |
|---|---:|
| Baseline Logistic Regression | 0.1388 |
| Baseline Random Forest | 0.1685 |
| Baseline XGBoost | 0.1698 |
| Enhanced Logistic Regression | 0.1633 |
| Enhanced Random Forest | 0.2059 |
| Enhanced XGBoost | 0.1982 |

Enhanced Random Forest won this comparison. This supports the engineering choice
for this split, not a significance or general superiority claim.

The HIGH/binary warning cutoff maximizes validation F1. The LOW boundary is the
highest validation cutoff maintaining at least 90% recall, capped at HIGH.
The frozen values are:

- LOW: probability below 0.025552616731219203.
- MEDIUM: at or above LOW and below 0.1306823416597925.
- HIGH: at or above 0.1306823416597925.

These are relative warning bands from validation scores, not calibrated safety
guarantees. The early planning examples of 30%/60% are not the implemented cutoffs.
The model and cutoffs were saved before opening final test targets. The artifact
was not refit on train+validation after selection.

### 8. Frozen evaluation and interpretation

| Held-out metric | Result |
|---|---:|
| Average precision | 0.1466 |
| ROC-AUC | 0.7631 |
| Brier score | 0.04360 |
| Precision at frozen cutoff | 15.02% |
| Recall at frozen cutoff | 45.16% |
| F1 at frozen cutoff | 0.2255 |

| Actual outcome | No warning | Warning |
|---|---:|---:|
| Passed | 18,368 | 2,664 |
| Failed | 572 | 471 |

The model catches 471 of 1,043 failures and misses 572. It emits 2,664 false
warnings. Most warnings are therefore false positives. An all-pass rule would
already have high accuracy because only 4.72% of test runs failed; accuracy alone
would hide the failure-detection problem.

Validation AP is higher than test AP, indicating temporal generalization limits.
The score is an uncalibrated estimate. There are no reported confidence intervals,
multiple chronological folds or cross-repository holdouts. Repeated commits can
have distinct workflow executions across splits, so this is future workflow-run
evaluation, not an unseen-commit benchmark. The final checks preserve the frozen
evaluation rather than rerunning models to improve its test score.

### 9. Explanations and recommendations

Probability-space SHAP uses a seeded background of 100 training feature rows.
Each explanation records the baseline score, full signed contributions, top
increasing/decreasing signals and reconstruction error. Imputed inputs and
missingness indicators are identified explicitly.

Inputs use the forest's numeric precision. Every contribution sum is checked
against the original pipeline probability. If a tree-explainer edge case fails
that check, an explicitly labeled seeded permutation-SHAP fallback is computed
against the same background. Contributions are never rescaled to conceal an
error. Approximate fallback attributions are not described as exact Tree SHAP.

Contributions explain model associations, not proven causes of failure.
Correlated signals and background selection affect attribution. Author history
must not be interpreted as a judgment of developer ability.

LOW uses the standard CI order; MEDIUM suggests fast unit checks early; HIGH
suggests early failure-detecting checks and prioritizing the required full suite
and integration checks. Verified change flags may add configuration or dependency
validation advice. Missing flags remain unknown. All mandatory tests remain
required, and predictions do not authorize merges.

### 10. Dashboard and hosted CI demonstration

The local dashboard provides historical exploration, feature-CSV predictions,
frozen model results, persistent imported CI outcomes, and temporary session
history. Explanations run only on explicit analysis requests. Invalid uploads,
unknown inputs and missing artifacts have recovery messages. Reports can be
downloaded as CSV, JSON or Markdown. Session history and durable CI history are
clearly distinguished.

The Quality workflow executes advisory prediction, required tests and outcome
recording. Prediction problems do not suppress the required test job. The actual
recorded label comes from the required-tests job, not the advisory script's exit
status. A portable checksummed model package avoids uploading the raw dataset.
The repository's normal token has read-only contents/actions access.

The first hosted run [3] completed all three jobs and 50 tests. It produced a
MEDIUM estimate of 10.05% and the actual required-test result was success. The
record was downloaded and imported into SQLite. A subsequent synced run also
passed [4]. These runs prove the integration path, not new predictive accuracy.
The project uses GitHub-hosted runners; no dashboard cloud deployment is claimed.

Live history is a bounded API window (three pages of up to 100 completed runs by
default), so live history counts/rates differ from lifetime-history training
semantics. The operational demonstration records a test-job outcome, whereas
training labels are workflow-run outcomes. Both are deployment shifts requiring
future consistent data collection and evaluation.

### 11. Final verification and reproducibility

Verification covers cleaning and label filtering, time boundaries, current/future
outcome exclusion, model-feature isolation, missing inputs, SHAP additivity,
artifact checksums, safe downloads, dashboard interactions, upload validation,
persistent outcome imports and the workflow graph.

Final acceptance rechecks original/model/partition hashes, partition metadata
alignment, build-identity disjointness, boundary label availability and the
observed hosted outcome in local history. It does not fit a model, retune cutoffs
or generate new test predictions. The offline CI replay now writes its own report
and cannot replace the hosted-run evidence.

Use docs/DEMO_GUIDE.md to run the demonstration and docs/VIVA_QA.md for concise
technical explanations. reports/FINAL_ACCEPTANCE.json records the integrity
checks; reports/STEP_7_VERIFICATION.json preserves hosted evidence. Final suite
counts and browser checks are recorded in reports/STEP_8_COMPLETION.md.

### 12. Limitations, future work and conclusion

The delivered system is a working research MVP. Its strongest evidence is a
reproducible audited pipeline and a functioning prediction-to-outcome integration.
It does not justify replacing mandatory checks or relying on predictions alone.

Future work includes verified platform provenance, real changed-file history,
consistent workflow/job labels, larger observed live histories, new held-out time
periods, calibration studies, recall/alert-budget policies, grouped-commit and
cross-repository evaluation, and background-sensitivity analysis for explanations.
Any new model improvement requires a new untouched evaluation period; the existing
test results remain frozen.

The project demonstrates how CI risk estimation can be operationalized with
transparent data handling and explanations. Its performance limitations are
explicit, and the workflow preserves mandatory testing regardless of the score.

### References

[1] Shriya Choksi, Build Failure Predictor:
https://github.com/shriyachoksi/build-failure-predictor.
Used as methodological reference; no whole-project copying.

[2] Joshua Faruna and Funmilayo Sanusi, A comprehensive GitHub Actions dataset for
CI/CD pipeline failure forecasting, version 1, Mendeley Data, 2026.
https://doi.org/10.17632/mggwn7rj9f.1.
CC BY 4.0: https://creativecommons.org/licenses/by/4.0/.
This project cleans, filters and transforms the data; source authors do not endorse
this implementation.

[3] First hosted integration:
https://github.com/kumaraguru-07/CI-failure-predictor/actions/runs/43699059875.

[4] Synced hosted verification:
https://github.com/kumaraguru-07/CI-failure-predictor/actions/runs/43699625093.

[5] SHAP TreeExplainer and PermutationExplainer documentation:
https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html
and https://shap.readthedocs.io/en/latest/generated/shap.PermutationExplainer.html.

[6] GitHub workflow-run and commit APIs:
https://docs.github.com/en/rest/actions/workflow-runs
and https://docs.github.com/en/rest/commits/commits.
