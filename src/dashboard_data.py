"""Dashboard data services; no training or test-set evaluation."""
import csv
import io
import json
import threading
from pathlib import Path
import numpy as np
import pandas as pd
from src.explain import load_verified_explainer,file_digest
from src.predict import predict_frame

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHANGE_FLAGS = ("dependency_file_changed","configuration_file_changed","ci_workflow_changed","docker_file_changed")
MAX_ROWS, MAX_BYTES = 500, 5*1024*1024

def fingerprint(root):
    root = Path(root)
    names = ["models/baseline_v1/model.joblib","models/baseline_v1/results.json",
             "data/processed/train.parquet","data/processed/validation.parquet",
             "data/processed/validation_metadata.parquet","reports/dataset_audit.json"]
    return tuple((name,(root/name).stat().st_mtime_ns,(root/name).stat().st_size) for name in names)

class DashboardService:
    def __init__(self,root):
        root = Path(root)
        self.engine,self.manifest = load_verified_explainer(root/"models/baseline_v1/model.joblib",root/"data/processed/train.parquet")
        self.lock = threading.RLock()
    def predict(self,frame):
        with self.lock:
            return predict_frame(self.engine.bundle,frame)
    def explain(self,frame):
        with self.lock:
            return self.engine.explain(frame)[0]

def validation_data(root,service):
    root = Path(root)
    if file_digest(root/"data/processed/validation.parquet")!=service.manifest["data_sha256"]["validation"]:
        raise ValueError("Validation data differs from the frozen training run")
    data = pd.read_parquet(root/"data/processed/validation.parquet").reset_index(drop=True)
    meta = pd.read_parquet(root/"data/processed/validation_metadata.parquet").reset_index(drop=True)
    if len(data)!=len(meta):
        raise ValueError("Validation features and metadata are not aligned")
    frame = data.drop(columns=["build_failed"])
    predictions = service.predict(frame)
    summary = meta[["repository","build_id","commit_sha","started_at"]].copy()
    summary["actual_outcome"] = data.build_failed.map({0:"Passed",1:"Failed"})
    summary["failure_probability"] = predictions.failure_probability
    summary["risk_level"] = predictions.risk_level
    summary["row_position"] = np.arange(len(summary))
    return frame,summary

def parse_feature_csv(content,features):
    if len(content)>MAX_BYTES:
        raise ValueError("Use a CSV smaller than 5 MB")
    try:
        text = content.decode("utf-8-sig")
        header = next(csv.reader(io.StringIO(text)))
        if len(header)!=len(set(header)):
            raise ValueError("CSV column names must be unique")
        d = pd.read_csv(io.StringIO(text),nrows=MAX_ROWS+1)
    except (UnicodeDecodeError,StopIteration,pd.errors.ParserError,pd.errors.EmptyDataError) as exc:
        raise ValueError("Upload a valid UTF-8 CSV with a header") from exc
    if not 1<=len(d)<=MAX_ROWS:
        raise ValueError("CSV must contain between 1 and 500 rows")
    missing = set(features)-set(d)
    if missing:
        raise ValueError("Missing required columns: "+", ".join(sorted(missing)))
    allowed = list(features)+[c for c in CHANGE_FLAGS if c in d and c not in features]
    ignored = sorted(set(d)-set(allowed))
    result = d[allowed].copy()
    for col in result:
        try:
            result[col] = pd.to_numeric(result[col],errors="raise").astype(float)
        except (ValueError,TypeError) as exc:
            raise ValueError(f"Column '{col}' must contain numbers or empty cells") from exc
        values = result[col].dropna()
        if np.isinf(values).any():
            raise ValueError(f"Column '{col}' contains an infinite value")
        if col in CHANGE_FLAGS and not values.isin([0,1]).all():
            raise ValueError(f"Column '{col}' must contain 0, 1 or empty cells")
        if col.endswith("failure_rate") and not values.between(0,1).all():
            raise ValueError(f"Column '{col}' must be between 0 and 1")
        if col in ("day_of_week","hour_of_day"):
            maximum = 6 if col=="day_of_week" else 23
            if not (values.between(0,maximum) & (values%1==0)).all():
                raise ValueError(f"Column '{col}' must be an integer from 0 to {maximum}")
        elif col not in CHANGE_FLAGS and (values<0).any():
            raise ValueError(f"Column '{col}' cannot be negative")
    return result,ignored

def csv_download(frame):
    # Keep string cells safe when opened by a spreadsheet program.
    safe = frame.copy()
    for col in safe.select_dtypes(include=["object","string"]):
        safe[col] = safe[col].map(lambda v:"'"+v if isinstance(v,str) and v.lstrip().startswith(("=","+","-","@")) else v)
    return safe.to_csv(index=False).encode("utf-8")

def add_history(history,record,source,actual_outcome="Unknown"):
    from datetime import datetime,timezone
    entry = {"recorded_at_utc":datetime.now(timezone.utc).isoformat(),
        "source":source,"failure_probability":record["failure_probability"],
        "risk_level":record["risk_level"],"actual_outcome":actual_outcome,
        "required_checks":"Run all mandatory checks"}
    return (list(history)+[entry])[-100:]

def ci_outcome_data(root):
    """Read imported CI history without creating or mutating a database."""
    import sqlite3
    path=Path(root)/"data/ci/predictions.sqlite3"
    if not path.exists():
        return pd.DataFrame()
    with sqlite3.connect(path.resolve().as_uri()+"?mode=ro",uri=True) as con:
        return pd.read_sql_query("SELECT repository, commit_sha, run_id, as_of, probability, risk, result, actual_failed FROM predictions ORDER BY as_of DESC",con)
