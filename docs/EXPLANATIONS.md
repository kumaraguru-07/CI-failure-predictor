# Step 5: prediction explanations and CI recommendations

No Docker, cloud deployment, API server or GPU is required. Use the local project
environment, which reuses installed base packages and adds SHAP 0.54.1 and
slicer 0.0.8 locally. The frozen model package versions are in
reports/TRAINING_RESULTS.json. This environment is not a fully isolated lockfile.

From the project folder:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m src.explain --limit 3
.\.venv\Scripts\python.exe -m src.explain --limit 3 --markdown reports/explanation_example.md
.\.venv\Scripts\python.exe -m src.verify_step5
```

Output: reports/explanation_example.json. The default input is the validation
partition, not the final test partition. The trained model and frozen test result
are not modified. The CLI accepts CSV/Parquet feature inputs with --input and a
different report path with --output. Interactive explanation batches are limited
to 100 rows; three rows are the default.

## Explanation contract

The supported artifact is the saved binary Random Forest pipeline. Its frozen
imputer transforms inputs without refitting. Tree SHAP explains failure-class
probability relative to 100 seeded training-background rows. The CLI verifies
both model and training-partition hashes against the frozen results manifest.
The reusable load_verified_explainer function performs these checks for the future
dashboard too. Direct PredictionExplainer construction requires its caller to
provide the actual training partition. Do not substitute validation/test as
background. Background sizes are restricted to 1..100; sampled row positions are
recorded independently of any custom DataFrame index labels.

Each report records the baseline probability, prediction, complete signed feature
contributions, top increasing/decreasing signals and reconstruction error. Signed
contributions are available both as probability units and percentage points. Their
sum plus baseline must match predict_proba for class 1. Top signals are only a
subset; use all_contributions for the full sum. Directions are relative to the
background, not simply high/low raw feature values.

Inputs to the tree calculation use the same float32 precision as sklearn's forest.
Every explanation is checked against the original pipeline probability. If the
installed Tree SHAP implementation fails this check on an edge case, the service
computes model-agnostic permutation SHAP against the same background, with a
seeded budget of 10*(2*feature_count+1) evaluations. The row explicitly records
permutation_shap_fallback; these attributions are estimates, not exact Tree SHAP.
Contributions are never rescaled to hide a mismatch. The final reconstruction
check is enforced for both methods. A synthetic all-missing-input case exposed
this issue and is now covered by a regression test.
Reference: https://shap.readthedocs.io/en/latest/generated/shap.PermutationExplainer.html.

Missing raw values are JSON null and marked as imputed. value_used records the
training-median replacement; missingness-indicator contributions are separately
identified. Features absent from the trained contract have no invented explanation.
The source has no file paths, so no claim about a specific unstable file is made.

SHAP explains the model, not the actual cause of failure. Correlated signals can
share attribution, and using a different background can change contributions.
An author-history signal is a repository-history association, not a judgment of
developer skill. The model probability remains an uncalibrated estimate with the
precision/recall limitations already recorded in reports/TRAINING_COMPLETION.md.

Reference: https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html.

## Recommendation contract

LOW uses the standard CI order. MEDIUM runs fast unit checks early. HIGH prioritizes
fast failure-detecting checks and the full required suite/integration checks, with
a suggestion to review the model signals. All bands require mandatory checks;
none skips tests or authorizes a merge. Optional numeric 0/1 change flags can add
dependency, configuration, workflow or container checks. Missing/NaN flags mean
unknown, not unchanged; invalid flag values are rejected. The current dataset
supplies no such evidence, so these targeted checks are not invented. These
recommendations are advisory text,
not an implemented scheduler or a claim that test runtime has been reduced.

## Verification

Twenty-four tests pass. Checks cover additivity, signed factors, imputation,
deterministic background, no refitting, invalid input, evidence-based advice,
artifact/background tampering, export collisions, CSV/JSON/Markdown export and the
explicit fallback path. Forty real validation rows (10 from each risk band plus
10 with missing inputs) and an all-missing boundary case pass; maximum error is
2.249e-8. No fallback was needed on this real-model verification batch.
The three-row readable example covers LOW, HIGH and MEDIUM. Report exports cannot
overwrite their model, manifest, background or input files. Missing features are
listed per row so users can see when training medians influenced the estimate.
Detailed verification: reports/STEP_5_VERIFICATION.json. The final test partition
was not accessed, and the frozen model checksum is unchanged.

Next: the dashboard can reuse PredictionExplainer and recommend_ci directly.
