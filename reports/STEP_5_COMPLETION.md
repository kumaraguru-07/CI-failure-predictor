# Step 5 final completion

Completed on 2026-11-15. No Docker or cloud service is required.

- Probability, risk band, signed SHAP contributors and missing-input notes are available per prediction.
- The full contribution sum is checked against the original model's probability.
- A clearly labeled permutation-SHAP fallback handles tree-explainer edge cases;
  no contributions are rescaled or fabricated.
- Recommendations cover all risk levels and optionally verified change flags.
  All mandatory checks remain required; predictions never authorize a merge.
- Unknown dependency/configuration/file changes remain unknown.
- Shared model/background verification checks hashes before loading the artifact.
- JSON and readable Markdown reports are generated; source-file collisions are rejected.
- All 24 tests pass, including fully missing input, tampering, fallback and export checks.
- Forty real validation rows across every risk level plus the all-missing boundary
  case pass, with maximum reconstruction error 2.249e-8. No fallback was needed
  for this batch using the actual saved model.
- The frozen model is unchanged; no test-set evaluation or retraining occurred.

Readable example: reports/explanation_example.md.
Full numerical example: reports/explanation_example.json.
Repeatable verification evidence: reports/STEP_5_VERIFICATION.json.
Commands and interpretation limits: docs/EXPLANATIONS.md.

The recommendation service returns advice. Actual scheduling of CI jobs belongs
to the later GitHub Actions stage. Explanations describe model behavior rather
than proven failure causes. The underlying precision/recall limitations remain
as documented in reports/TRAINING_COMPLETION.md.

Next phase: Step 6, dashboard.
