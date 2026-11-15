# Step 7 completion — GitHub Actions integration

Verified on 2026-11-15 in the user-selected public repository:
https://github.com/kumaraguru-07/CI-failure-predictor

## Published and configured

- Project source, dashboard, documentation and tests on main.
- Research pre-release ci-model-v1 containing ci-model-v1-attributed.zip and checksum.
- Package SHA256: 3045161c051bd57d117151841da05b916296d595c8c6671e8a270c2e436c93e0.
- Actions variables CI_MODEL_URL and CI_MODEL_SHA256 verified in repository settings.
- Explicit user approval was received for public sharing of the model package
  and its 100 derived numeric training-background rows.
- Raw dataset, author identifiers, local environment and credentials excluded.

## First hosted verification

Run: https://github.com/kumaraguru-07/CI-failure-predictor/actions/runs/43699059875
Commit: c0f669fbb7d8c641693afb35664263eb6be63eb9

All three jobs succeeded: Advisory failure prediction, Required tests, and
Record required-test outcome. The hosted test suite reports 50 passed.
The advisory report status is predicted (not unavailable).

Predicted risk: 10.051957% (MEDIUM). Actual required-test result: success.
The run's prediction/outcome JSON and SQLite were saved as GitHub artifacts.
Its outcome export was downloaded and imported into data/ci/predictions.sqlite3.
The prediction was generated at 09:24:18 UTC, before the tests completed;
the actual outcome was recorded at 09:25:05 UTC. No required tests were skipped.

The local main branch tracks origin/main. Earlier local development history is
retained on local-development. Frozen model and test evaluation are unchanged.

## Limits and handoff

This verifies the deployment flow, not statistical predictive accuracy for this
repository. The new repository has little CI history. Model limits and bounded
live-history semantics remain documented in docs/GITHUB_ACTIONS.md.
Branch-protection settings have not been changed. The workflow runs its required
test job regardless of the advisory risk; enforcing merge gates is a separate
repository policy choice. Outcome artifacts have 90-day retention; local imports
support longer-term history.

Next: Step 8, final integration checks and project/report documentation.
