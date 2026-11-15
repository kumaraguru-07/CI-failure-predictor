"""Local inference using the frozen training feature contract."""
import argparse
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

def risk_level(probability, thresholds):
    p = float(probability)
    if not np.isfinite(p) or not 0<=p<=1:
        raise ValueError("Probability must be between 0 and 1")
    if p < thresholds["low_upper"]:
        return "LOW"
    if p < thresholds["medium_upper"]:
        return "MEDIUM"
    return "HIGH"

def predict_frame(bundle, frame):
    missing = set(bundle["features"])-set(frame)
    if missing:
        raise ValueError(f"Missing required feature columns: {sorted(missing)}")
    x = frame[bundle["features"]]
    if not all(pd.api.types.is_numeric_dtype(x[c]) for c in x):
        raise ValueError("Required feature columns must be numeric")
    if np.isinf(x.to_numpy(dtype=float)).any():
        raise ValueError("Infinite values are invalid")
    p = bundle["pipeline"].predict_proba(x)[:,1]
    return pd.DataFrame({"failure_probability":p,
        "risk_level":[risk_level(v,bundle["thresholds"]) for v in p],
        "predicted_failure":(p>=bundle["thresholds"]["binary_threshold"]).astype(int)})

def main():
    p = argparse.ArgumentParser(description="Load trusted locally produced model artifacts only")
    p.add_argument("--model",type=Path,default=Path("models/baseline_v1/model.joblib"))
    p.add_argument("--input",type=Path,required=True)
    a = p.parse_args()
    frame = pd.read_parquet(a.input) if a.input.suffix == ".parquet" else pd.read_csv(a.input)
    # joblib is executable deserialization: never load an untrusted downloaded model.
    print(predict_frame(joblib.load(a.model),frame).to_json(orient="records",indent=2))

if __name__ == "__main__":
    main()
