# Step 6: local dashboard

## Open the dashboard

The easiest option on this PC is to double-click Start dashboard.cmd in the
project folder. It opens a browser and keeps a local server window available
for stopping the app. No server is started just by opening project files.

From D:\Balu project\failure-aware-ci:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open http://127.0.0.1:8501 in your browser. Stop with Ctrl+C in its terminal.
No Docker, cloud app, external account or API key is needed. The app uses the
existing local model and data; it never trains or changes the frozen test result.
Streamlit 1.63.0 is installed on this PC. Newer dashboard APIs require >=1.57.

## Views

- Explore builds: filter recorded validation builds by repository/risk, inspect
  the newest 200 matches, analyze a selected build, and download filtered predictions.
- Predict from CSV: download the feature template, upload up to 500 rows / 5 MB,
  get batch probabilities, and explain one selected row. UTF-8 CSV only.
- Model results: saved validation comparison, final test metrics, confusion counts,
  risk cutoffs and known limitations. This view does not reopen test targets.
- CI outcome history: read-only persistent history imported from completed GitHub
  Actions artifacts. Known outcomes are shown by default; pending/nonbinary
  records can be included. Downloads do not modify the ledger.
- Session history: latest 100 builds you explicitly analyzed, with known historical
  outcomes where available. Download CSV before closing; this is session memory,
  not permanent prediction tracking or a live outcome collector.

Each analysis shows probability, risk band, signed SHAP signals, imputed input
notes and CI recommendations. JSON and readable Markdown downloads are available.
Changing the selected row/input hides an old explanation until Analyze is clicked.
All mandatory tests remain required for every band.

## Input contract

The CSV template contains the saved model's exact feature names. Extra columns,
including outcomes, are excluded from prediction and disclosed as ignored.
Empty cells are allowed and use training medians; an all-missing row is explicitly
flagged in its explanation. Text values, infinities, negative metrics, invalid
rate/time values, duplicate headers, missing required columns and oversized files
are rejected. Optional dependency/configuration/workflow/container change flags
accept only 0, 1 or empty cells. Targeted advice needs explicit change evidence.

Only the fixed trusted local model is loaded. Model files cannot be uploaded.
The server binds to 127.0.0.1 and does not expose itself to your network.
The app displays no raw author names/emails. Uploads remain in memory and do not
modify project data. CSV downloads neutralize formula-like string cells.

## Required local files

- models/baseline_v1/model.joblib and results.json
- data/processed/train.parquet
- data/processed/validation.parquet and validation_metadata.parquet
- reports/dataset_audit.json

Missing/mismatched files produce a recovery message. Restore the corresponding
frozen files; do not retrain against the already inspected test result. The model,
training background and validation feature file are hash-checked. Keep aligned
validation metadata from the same preparation run.

Data/model loads are cached with bounded entries and file-change fingerprints.
SHAP work runs only on explicit Analyze clicks. The shared service uses a lock
for prediction/explanation calls. Per-user results/history live in session state.
The interface uses native responsive cards, tables and signed contribution charts,
with no custom CSS, external fonts or extra frontend framework.

## Verification

Run `.\.venv\Scripts\python.exe -m pytest -q`.
All 53 tests pass. Run `.\.venv\Scripts\python.exe -m src.verify_dashboard`
to repeat the real-model check; results are saved in reports/STEP_6_VERIFICATION.json.
Headless AppTest checks navigation, repository filtering, explanations, stale-result
hiding, history, clearing, saved-model results and missing-artifact recovery.
Pure tests check the upload parser, data integrity, history bounds and downloads.

AppTest cannot simulate selecting a file in the native browser upload dialog.
The CSV parser/service are tested directly. AppTest covers the no-file view and
valid/invalid uploaded-CSV branches using an in-memory replacement for the native
file selector. All five views pass headless checks with the real 20,409-row
validation cohort and frozen model. Final browser checks additionally covered
filtering, signed explanations, a readable-report download, native CSV upload,
the missing-history note, frozen metrics, persistent CI outcomes and session
history. See reports/BROWSER_QA.json. Restart the server after changing shared
Python modules; a browser refresh alone may retain imported modules.

## Remaining scope

GitHub commit collection and hosted outcome recording are implemented. The
dashboard itself does not fetch or schedule live runs; its prediction inputs are
historical validation rows and feature CSVs. Import completed outcome artifacts
to update persistent CI history. Model-score limits still apply; this is a
research dashboard.
