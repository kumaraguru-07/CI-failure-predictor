# Step 6 completion — local dashboard

Completed on 2026-11-15. Entry point: app.py. Open locally with Start dashboard.cmd.

## Delivered

- Historical validation-build explorer with repository/risk filters, known outcomes
  and CSV export; the newest 200 matches are shown with a build selector.
- Feature-template download and CSV prediction upload (500 rows / 5 MB maximum).
- Probability, risk band, signed contribution chart, full SHAP details, imputed-input
  notes and CI recommendations for a selected build.
- JSON/Markdown explanation downloads and batch prediction downloads.
- Saved model comparison, test metrics, confusion table and frozen risk cutoffs.
- Session-only history (latest 100 analyses), download and clear controls.
- Graceful missing-file and invalid-input errors; stale explanations are hidden
  when the selected input changes.
- Bounded data/model caches, serialized shared prediction/explanation calls, and
  per-session results. No new frontend framework or cloud dependency.
- A local-only server configuration, Windows launcher and user guide.

## Verification

All 32 tests pass. AppTest exercises navigation, filters, historical and CSV
analysis, invalid uploads, changed-row result handling, session history and saved
model results. Unit checks cover parser limits, numeric/rate/time constraints,
ignored outcomes, duplicate headers, hash validation and safe CSV export.

The real-artifact AppTest check loads 20,409 validation builds, analyzes a HIGH
risk build with a valid additive explanation, and visits every view. Model and
frozen evaluation hashes are unchanged. Evidence: reports/STEP_6_VERIFICATION.json.
No training, new test evaluation or live GitHub operations occur in the dashboard.

This verification is headless. Native browser file-dialog interactions, visual
layout and the server HTTP endpoint have not been separately inspected. The local
server is not left running; the launcher starts it when the user opens it.

## Handoff

User guide: docs/DASHBOARD.md. Open the app using Start dashboard.cmd.
Step 7 remains: live GitHub commit extraction, GitHub Actions integration and
persistent collection of actual CI outcomes. The current history is a session
view, and the current recommendations are advisory rather than a test scheduler.
