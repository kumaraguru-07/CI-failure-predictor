"""Final integrity checks. No fitting, threshold tuning or test prediction."""
import argparse
import json
from importlib.metadata import version
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq
from src.explain import file_digest
from src.ci_history import rows

ROOT=Path(__file__).resolve().parents[1]

def audit(root=ROOT):
    root=Path(root)
    training=json.loads((root/"reports/TRAINING_RESULTS.json").read_text(encoding="utf-8"))
    frozen=json.loads((root/"models/baseline_v1/results.json").read_text(encoding="utf-8"))
    dataset=json.loads((root/"reports/dataset_audit.json").read_text(encoding="utf-8"))
    if training!=frozen:
        raise ValueError("Published training report differs from frozen evaluation")
    if file_digest(root/"models/baseline_v1/model.joblib")!=training["model_sha256"]:
        raise ValueError("Frozen model changed")
    raw=root/"data/raw/final_research_dataset_MASTER.csv"
    if file_digest(raw)!=dataset["sha256"]:
        raise ValueError("Raw dataset checksum mismatch")
    meta={}
    counts={}
    for name in ("train","validation","test"):
        path=root/("data/processed/"+name+".parquet")
        if file_digest(path)!=training["data_sha256"][name]:
            raise ValueError(name+" partition changed")
        counts[name]=pq.ParquetFile(path).metadata.num_rows
        meta[name]=pd.read_parquet(root/("data/processed/"+name+"_metadata.parquet"))
        if len(meta[name])!=counts[name] or counts[name]!=dataset["splits"][name]["rows"]:
            raise ValueError("Partition/metadata/audit counts differ")
        if meta[name].duplicated(["repository","build_id","attempt"]).any():
            raise ValueError("Duplicate build identity")
    if not (meta["train"].completed_at.max()<meta["validation"].started_at.min()
        and meta["validation"].completed_at.max()<meta["test"].started_at.min()):
        raise ValueError("Labels cross partition boundaries")
    keys=[set(map(tuple,m[["repository","build_id","attempt"]].to_numpy())) for m in meta.values()]
    if keys[0]&keys[1] or keys[0]&keys[2] or keys[1]&keys[2]:
        raise ValueError("Build identities overlap")
    hosted=json.loads((root/"reports/STEP_7_VERIFICATION.json").read_text(encoding="utf-8"))
    if not hosted.get("github_hosted_workflow_executed") or hosted["hosted"]["conclusion"]!="success":
        raise ValueError("Successful hosted verification is required")
    ledger=rows(root/"data/ci/predictions.sqlite3")
    known=[r for r in ledger if r["result"] in ("success","failure")]
    if not any(r["run_id"]==str(hosted["hosted"]["run_id"]) for r in known):
        raise ValueError("Verified hosted outcome is missing from local history")
    bundle=root/"artifacts/ci-model-v1-attributed.zip"
    expected=bundle.with_suffix(".sha256").read_text().strip()
    if file_digest(bundle)!=expected:
        raise ValueError("Published CI package changed")
    browser=json.loads((root/"reports/BROWSER_QA.json").read_text(encoding="utf-8"))
    if browser.get("status")!="passed":
        raise ValueError("Browser acceptance is incomplete")
    return {"status":"passed","scope":"Local integrity and existing hosted evidence; no new test evaluation",
        "raw_rows":dataset["raw_rows"],"eligible_rows":dataset["eligible_rows"],"partitions":counts,
        "boundary_labels_available":True,"build_identities_disjoint":True,
        "raw_model_partition_checksums_match":True,"frozen_evaluation_unchanged":True,
        "hosted_workflow_url":hosted["hosted"]["url"],"local_observed_ci_outcomes":len(known),
        "model_sha256":training["model_sha256"],"package_sha256":expected,
        "browser_qa":browser["status"],
        "tested_direct_dependencies":{n:version(n) for n in
            ("numpy","pandas","scikit-learn","scipy","xgboost","joblib","pyarrow","shap","streamlit","pytest","PyYAML")}}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=ROOT/"reports/FINAL_ACCEPTANCE.json")
    a=p.parse_args()
    report=audit()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
