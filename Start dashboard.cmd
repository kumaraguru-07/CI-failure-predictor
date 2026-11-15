@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo The local Python environment is missing. See docs\DASHBOARD.md.
  pause
  exit /b 1
)
echo Opening Failure-aware CI at http://127.0.0.1:8501
echo Keep this window open. Press Ctrl+C to stop the dashboard.
".venv\Scripts\python.exe" -m streamlit run app.py --server.headless false --server.address 127.0.0.1 --server.port 8501
if errorlevel 1 pause
