# Step 7 status

Complete: local and hosted integration verified on 2026-11-15.
The user selected public repository kumaraguru-07/CI-failure-predictor and approved
publication of the model package and its 100 derived numeric background rows.

Delivered: read-only commit/history collector; leakage-safe feature snapshot;
portable frozen-model package with training-background attribution; advisory
prediction and job summary; required tests after prediction; actual-test outcome
join; persistent SQLite ledger and idempotent artifact import.

The portable package is artifacts/ci-model-v1-attributed.zip. Its SHA256 is in
the adjacent .sha256 file. Set CI_MODEL_URL and CI_MODEL_SHA256 as described in
docs/GITHUB_ACTIONS.md after publishing the asset to your own GitHub release.

A read-only public-reference demo succeeded using three API requests. It produced
a local prediction with unknown/cold-start history, not an actual CI outcome.
No code was copied or pushed to the reference repository.

The local test suite and the first hosted workflow both pass. The saved model
and frozen test evaluation are unchanged.
All 50 tests pass, including private release binary download and token stripping
on cross-host redirects. The final portable model package is 4,908,477 bytes.
Remote origin is configured. Source, the ci-model-v1 release and both Actions
variables are published. Workflow run 43699059875 passed all three jobs. The
MEDIUM prediction (10.05%) is joined to the actual successful test result and
imported into the local SQLite ledger.

Next: final-report work and continued observation of actual predictions versus
CI outcomes. A single successful CI run is not a new accuracy benchmark.
