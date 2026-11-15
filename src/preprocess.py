"""Compatibility cleaner for small canonical tables; use src.prepare for Mendeley."""
import argparse
from pathlib import Path
import pandas as pd
from src.dataset import OUTCOMES

def read_table(path):
    path = Path(path)
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)

def clean_builds(frame, timestamp_column="build_started_at"):
    if timestamp_column not in frame or "build_outcome" not in frame:
        raise ValueError("Required timestamp and build_outcome columns are missing")
    safe = [timestamp_column] + [c for c in ("repository","build_id","author",
            "lines_added","lines_deleted","files_changed_total") if c in frame]
    cleaned = frame[safe].copy()
    cleaned[timestamp_column] = pd.to_datetime(frame[timestamp_column], utc=True, errors="coerce", format="mixed")
    cleaned["build_failed"] = frame.build_outcome.astype("string").str.strip().str.lower().map(OUTCOMES)
    cleaned = cleaned.dropna(subset=[timestamp_column,"build_failed"])
    cleaned["build_failed"] = cleaned.build_failed.astype("int8")
    return cleaned.sort_values(timestamp_column,kind="stable").reset_index(drop=True)

def main():
    p = argparse.ArgumentParser(description="Canonical table cleaner; use src.prepare for Mendeley")
    p.add_argument("--input",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a = p.parse_args()
    d = clean_builds(read_table(a.input))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    d.to_parquet(a.output,index=False)

if __name__ == "__main__":
    main()
