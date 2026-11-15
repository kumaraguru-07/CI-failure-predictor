# Step 7: GitHub commit collection and Actions integration

Status: local implementation and live read-only collection verified.
Hosted workflow activation is pending: this project has no configured GitHub remote.

## What is implemented

The Quality workflow now has three jobs:
1. Advisory failure prediction from the commit and prior completed workflow runs.
2. Required tests, which run after the advisory job even when prediction fails.
3. Prediction/outcome recording, using the required-tests job result.

The prediction writes a GitHub job summary and a JSON artifact. It never skips
checks or authorizes a merge. Outcome recording labels the tests job, not whether
the prediction script succeeded. Cancelled/skipped tests remain nonbinary/unknown.
Configure branch protection to require **Required tests**, not the advisory job.

## Activate on your GitHub repository

Use your project repository, not the reference author's repository.

1. Connect/publish this project to your own GitHub repository, preserving any
   existing repository work. The local chat has not pushed code or created a repo.
2. Create a GitHub release and upload:
   artifacts/ci-model-v1-attributed.zip
3. Add repository Actions variables (Settings > Secrets and variables > Actions):
   - CI_MODEL_URL: a public release download URL or the release-asset API URL
     for a private repository (recommended for the new private project).
   - CI_MODEL_SHA256: the exact contents of
     artifacts/ci-model-v1-attributed.sha256.
4. Push a commit or manually run the Quality workflow.
5. Inspect the prediction summary, required-tests result, and prediction/outcome artifacts.

Example URL format:
https://github.com/OWNER/REPOSITORY/releases/download/ci-model-v1/ci-model-v1-attributed.zip

For a private repository, use the release asset's API URL instead:
https://api.github.com/repos/OWNER/REPOSITORY/releases/assets/ASSET_ID

The exported package is about 4.9 MB. It contains only the frozen model, its
manifest and 100 numeric training-background rows. It excludes raw data, targets,
author identifiers and full training partitions. Dataset attribution is included
inside the manifest. Artifacts are ignored by Git: do not commit the 195 MB dataset.

Both public and private GitHub releases are supported. Private release-asset API
requests use the workflow's read-only GITHUB_TOKEN and request binary content.
Authentication is removed before cross-host storage redirects; HTTPS is required.
An external pinned SHA256 is required before deserializing the model; never use
a model package from an untrusted uploader even if it supplies its own checksum.

The workflow uses GitHub's automatic token with contents/actions read permissions.
No personal token, Docker, GPU, database server or additional cloud app is needed
for this workflow. Fork access/rate restrictions can make predictions unavailable;
the required test job still runs. No pull_request_target or repository write
permissions are used.

## Local commands

Re-export only to a NEW package path, since existing packages are not overwritten:

```powershell
.\.venv\Scripts\python.exe -m src.ci_bundle --output artifacts/ci-model-next.zip
```

For an actual repository/commit, pass a full immutable 40-character SHA:

```powershell
.\.venv\Scripts\python.exe -m src.ci_predict --repository OWNER/REPOSITORY --commit FULL_COMMIT_SHA --bundle artifacts/ci-model-v1-attributed.zip --bundle-sha256 PACKAGE_SHA256 --summary reports/ci_prediction.md
```

Use the actual package SHA from the .sha256 file. The local CLI writes a pending
SQLite prediction record, JSON and optional summary. This command only reads GitHub;
it does not run tests or invent an actual outcome. Missing config/API problems
produce an unavailable report; no zero-risk fallback is substituted. Tokens are
read from GITHUB_TOKEN and are not included in reports.

The snapshot verification can be repeated without new network requests:

```powershell
.\.venv\Scripts\python.exe -m src.verify_ci
.\.venv\Scripts\python.exe -m pytest -q
```

## Outcome history

The outcome job joins the prediction from the SAME workflow run to needs.tests.result.
Prediction identity includes repository, commit, run ID, attempt and prediction time.
The SQLite ledger preserves immutable prediction fields and rejects conflicting
outcomes. Parameterized database writes are used.

Each run uploads a prediction/outcome JSON export and SQLite artifact with 90-day
retention. These are per-run artifacts, not one automatically growing shared
database. Download their exports and merge locally for longer-term history:

```powershell
.\.venv\Scripts\python.exe -m src.ci_history --import-outcomes PATH_TO_prediction_outcome.json --database data/ci/predictions.sqlite3 --export reports/prediction_outcome.json
```

Imports are idempotent. Reimporting a pending record never erases an observed
outcome. A cancelled/skipped result is not counted as a pass or failure.
The dashboard's session history is separate; this stage provides the persistent
ledger and importer, not a new dashboard view.

## Feature availability and interpretation

Commit stats come from GitHub, with paginated changed paths (including old names
for renamed files). Incomplete path lists are marked unknown. History retrieval
is bounded to three pages of 100 completed runs by default (maximum five pages).
Only explicit success/failure/startup_failure conclusions completed STRICTLY
before prediction time contribute; current, overlapping, cancelled and unknown
runs are excluded. updated_at is a conservative availability proxy.

History rates/counts therefore describe the observed API window, not necessarily
lifetime repository history. That is a deployment distribution shift from the
training cohort. Author identity uses commit author email/name where available,
not the actor who clicked Run. Missing author/history fields stay missing.
Current build duration/outcome are not inputs.

Live changed-file flags can inform CI advice. They do not suddenly become learned
model features: the frozen training artifact had no paths. Historical touched-file
failure rates are not fabricated. Prediction timing uses UTC at collection start.
For PRs, use the head commit SHA rather than GitHub's synthetic merge commit.
The advisory job runs before this workflow's expensive test job.

The model has not been validated for a new live repository. Its risk bands and
precision/recall limits remain those in docs/TRAINING.md. The local reference
demo had no prior Actions history; it verified collection and cold-start handling,
not prediction accuracy.

## Evidence and remaining activation

Tests cover feature availability, pagination, author history, binary outcomes,
API error redaction, checksums, archive members, bundle export/load, job graph,
outcome recording and idempotent history import. Aggregate evidence is in
reports/STEP_7_VERIFICATION.json. The frozen model and test evaluation are unchanged.

No GitHub-hosted workflow has run for this project yet. Repository connection,
release upload, Actions variables and the first hosted run remain required before
claiming end-to-end GitHub deployment.

The user has authorized creating a new project repository and publishing the
required code/package. A private repository is the default. Account sign-in is
confirmed through the GitHub integration as kumaraguru-07. Repository creation
and release setup are not exposed by that connection, and the browser setup page
requires a separate sign-in by the account owner. It has been left open for that
handoff. No remote repository has been created yet.

Primary API references:
- https://docs.github.com/en/rest/commits/commits
- https://docs.github.com/en/rest/actions/workflow-runs
- https://docs.github.com/en/actions/tutorials/authenticate-with-github_token
