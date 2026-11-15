"""Small persistent prediction/outcome ledger using Python's built-in SQLite."""
import argparse
import json
import sqlite3
import math
from datetime import datetime,timezone
from pathlib import Path

def record(db,prediction,result=None,completed_at=None):
    if prediction.get("status")!="predicted":
        return None
    if result not in (None,"success","failure","cancelled","skipped"):
        raise ValueError("Unknown CI job result")
    if result is not None and not completed_at:
        raise ValueError("Outcome availability time required")
    if completed_at and datetime.fromisoformat(completed_at)<datetime.fromisoformat(prediction["as_of"]):
        raise ValueError("Outcome cannot predate prediction")
    db = Path(db)
    db.parent.mkdir(parents=True,exist_ok=True)
    p = prediction
    key = p["prediction_id"]
    actual = {"success":0,"failure":1}.get(result)
    probability = p["prediction"]["failure_probability"]
    if not isinstance(probability,(int,float)) or not math.isfinite(probability) or not 0<=probability<=1:
        raise ValueError("Prediction probability must be finite and between zero and one")
    if p["prediction"]["risk_level"] not in ("LOW","MEDIUM","HIGH"):
        raise ValueError("Invalid risk level")
    if datetime.fromisoformat(p["as_of"]).tzinfo is None:
        raise ValueError("Prediction timestamp must be timezone aware")
    with sqlite3.connect(db) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS predictions (
            prediction_id TEXT PRIMARY KEY, repository TEXT, commit_sha TEXT,
            run_id TEXT, run_attempt INTEGER, as_of TEXT, probability REAL,
            risk TEXT, model_sha256 TEXT, result TEXT, actual_failed INTEGER,
            completed_at TEXT)""")
        values = (key,p["repository"],p["commit_sha"],str(p.get("run_id") or "local"),
            p.get("run_attempt",1),p["as_of"],p["prediction"]["failure_probability"],
            p["prediction"]["risk_level"],p["model_sha256"],result,actual,completed_at)
        existing = con.execute("SELECT * FROM predictions WHERE prediction_id=?",(key,)).fetchone()
        if existing and existing[:9]!=values[:9]:
            raise ValueError("Conflicting immutable prediction fields")
        if existing and existing[9] is not None and result not in (None,existing[9]):
            raise ValueError("Conflicting recorded outcome")
        con.execute("""INSERT INTO predictions VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(prediction_id) DO UPDATE SET
            result=COALESCE(excluded.result,predictions.result),
            actual_failed=COALESCE(excluded.actual_failed,predictions.actual_failed),
            completed_at=COALESCE(excluded.completed_at,predictions.completed_at)""",values)
    return key

def rows(db):
    with sqlite3.connect(db) as con:
        con.row_factory = sqlite3.Row
        return [dict(row) for row in con.execute("SELECT * FROM predictions ORDER BY as_of")]

def import_outcomes(db,path):
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(records,list):
        raise ValueError("Outcome export must be a list of ledger records")
    for r in records:
        p = {"status":"predicted","prediction_id":r["prediction_id"],
            "repository":r["repository"],"commit_sha":r["commit_sha"],"as_of":r["as_of"],
            "run_id":r["run_id"],"run_attempt":r["run_attempt"],"model_sha256":r["model_sha256"],
            "prediction":{"failure_probability":r["probability"],"risk_level":r["risk"]}}
        record(db,p,r["result"],r["completed_at"])
    return len(records)

def main():
    p = argparse.ArgumentParser()
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--prediction",type=Path)
    source.add_argument("--import-outcomes",type=Path)
    p.add_argument("--database",type=Path,default=Path("data/ci/predictions.sqlite3"))
    p.add_argument("--result",choices=["success","failure","cancelled","skipped"])
    p.add_argument("--completed-at")
    p.add_argument("--export",type=Path)
    a = p.parse_args()
    if a.import_outcomes:
        count = import_outcomes(a.database,a.import_outcomes)
        if a.export:
            a.export.parent.mkdir(parents=True,exist_ok=True)
            a.export.write_text(json.dumps(rows(a.database),indent=2),encoding="utf-8")
        print(json.dumps({"imported":count,"database":str(a.database)}))
        return
    prediction = json.loads(a.prediction.read_text(encoding="utf-8"))
    completed = a.completed_at or (datetime.now(timezone.utc).isoformat() if a.result else None)
    key = record(a.database,prediction,a.result,completed)
    if key and a.export:
        a.export.parent.mkdir(parents=True,exist_ok=True)
        a.export.write_text(json.dumps(rows(a.database),indent=2),encoding="utf-8")
    print(json.dumps({"recorded":key is not None,"database":str(a.database)}))

if __name__=="__main__":
    main()
