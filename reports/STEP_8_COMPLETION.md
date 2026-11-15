# Step 8: final verification and handover

Completed locally on 2026-11-15. The research MVP's planned implementation phases
are complete, subject to the explicit model/data limitations below.

## Acceptance

- All 53 automated tests pass, including data/label availability, leakage guards,
  saved inference, SHAP edge cases, dashboard flows, upload handling, CI package
  integrity, workflow structure and persistent outcome imports.
- Final artifact checks pass: original dataset, model and all partition hashes
  match; metadata is aligned; build identities are disjoint; training/validation
  labels are available before the next partition.
- Browser QA passes across all five views. A native synthetic CSV upload yields
  three predictions; the missing-history row displays its imputation note.
  A historical HIGH prediction shows signed SHAP signals and mandatory-test advice.
  A readable report downloads successfully. Persistent CI history shows the
  recorded successful outcome; session history preserves both analyses.
- The local HTTP server and real saved-model dashboard startup were exercised.
- The offline CI verifier no longer overwrites the hosted evidence. Its regression
  test also accepts an already-observed outcome without erasing it.
- GitHub Actions use verified current Node 24 action releases. The final published
  commit triggers the hosted suite; see the repository Actions page for that run.
- No model fitting, threshold tuning or new test prediction was performed during
  these final checks. Frozen experiment metrics are unchanged.

Evidence: FINAL_ACCEPTANCE.json, BROWSER_QA.json, CI_LOCAL_VERIFICATION.json,
STEP_6_VERIFICATION.json, and STEP_7_VERIFICATION.json. Hosted integration already
passed prediction, 50 tests and outcome recording before the final-stage additions.
Final local suite count is 53; hosted checks are linked from the repository.

## Delivered documentation

- docs/PROJECT_REPORT.md: methodology, architecture, feature/data contracts,
  validation comparison, exact held-out metrics, hosted demonstration and limitations.
- docs/DEMO_GUIDE.md: startup, five-minute demonstration, verification and recovery.
- docs/VIVA_QA.md: 26 concise project questions and answers.
- docs/examples/feature_input.csv: invented examples, never evaluation evidence.
- requirements-tested.txt: the direct package versions used locally, not a fully
  isolated transitive lock.

## Boundaries

The held-out model has 15.02% precision and 45.16% recall at the frozen cutoff.
It remains a research baseline with false alarms and missed failures. File-path
history was not empirically evaluated; platform provenance is not verified per
row. Live history windows and operational test-job labels differ from training.
There is no automatic merge approval, test skipping, implemented test scheduler,
dashboard cloud deployment or automatic dashboard polling of GitHub history.
These are disclosed limits, not claimed completed capabilities.

The dashboard's CI history is persistent but refreshed by importing artifacts;
session history is temporary. Existing branch-protection settings were preserved.
Further model development needs a new untouched future evaluation period.

## Open and maintain

Double-click Start dashboard.cmd in D:\Balu project\failure-aware-ci.
Keep its window open while using the app. The short-lived test preview on port
8502 is separate from the normal launcher on port 8501.
Source: https://github.com/kumaraguru-07/CI-failure-predictor.
Actions: https://github.com/kumaraguru-07/CI-failure-predictor/actions.
