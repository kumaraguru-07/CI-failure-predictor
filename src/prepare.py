"""Verified ingestion, auditable cleaning, features and time-ordered partitions."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import pandas as pd
from src.dataset import normalize, OUTCOMES
from src.features import build_features
from src.split import chronological_split

EXPECTED_SHA256 = "b6a89418e39e6144f4ac71496256474c7bc27651e099557fe074d7798da1e73e"

def prepare(input_path, output=Path("data/processed"), report=Path("reports/dataset_audit.json"),
            verify_checksum=True):
    input_path, output, report = Path(input_path), Path(output), Path(report)
    with input_path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if verify_checksum and digest != EXPECTED_SHA256:
        raise ValueError("Dataset checksum mismatch; original v1 file required")
    raw = pd.read_csv(input_path, low_memory=False, dtype={"run_id":"string"})
    d, cleaning = normalize(raw, return_audit=True)
    if len(d) < 20:
        raise ValueError("Insufficient eligible rows")
    partitions = chronological_split(d)
    x = build_features(d)
    output.mkdir(parents=True, exist_ok=True)
    interim = output.parent / "interim"
    interim.mkdir(parents=True, exist_ok=True)
    d.to_parquet(interim / "builds_clean.parquet", index=False)
    audit = {"raw_rows":len(raw), "eligible_rows":len(d), "sha256":digest,
        "checksum_verified":verify_checksum, "cleaning":cleaning,
        "source":"https://data.mendeley.com/datasets/mggwn7rj9f/1",
        "license":"CC BY 4.0", "authors":"Joshua Faruna; Funmilayo Sanusi",
        "label_mapping":OUTCOMES,
        "environment":{"python":platform.python_version(),"pandas":pd.__version__},
        "repositories":int(d.repository.nunique()),
        "raw_column_missing_fraction":raw.isna().mean().to_dict(),
        "commit_metrics_summary":d[["lines_added","lines_deleted","files_changed_total"]].describe().to_dict(),
        "limitations":[
            "Publisher describes mixed TravisTorrent/GitHub Actions data; no verified source discriminator",
            "updated_at is conservatively used as outcome availability time, not exact completion",
            "No file paths: file/configuration features remain missing",
            "History replay uses outcomes only after completion, including earlier evaluation outcomes",
            "No imputation, scaling, balancing or model selection has been fit on validation/test"],
        "splits":{}}
    metadata = ["repository","build_id","attempt","commit_sha","started_at","completed_at"]
    for name, part in zip(("train","validation","test"), partitions):
        out = x.loc[part.index].copy()
        out["build_failed"] = part.build_failed
        out.to_parquet(output / (name+".parquet"), index=False)
        part[metadata].to_parquet(output / (name+"_metadata.parquet"), index=False)
        audit["splits"][name] = {"rows":len(out),"failures":int(out.build_failed.sum()),
            "failure_rate":float(out.build_failed.mean()),
            "start":str(part.started_at.min()),"end":str(part.started_at.max()),
            "latest_label_available":str(part.completed_at.max())}
    audit["boundary_purged_rows"] = len(d)-sum(len(p) for p in partitions)
    audit["feature_missing_fraction"] = x.isna().mean().to_dict()
    train_x = x.loc[partitions[0].index]
    audit["training_all_missing_features"] = train_x.columns[train_x.isna().all()].tolist()
    # Diagnose repeated commit identities; workflow prediction may legitimately reuse a commit.
    def commits(part):
        return set(zip(part.repository[part.commit_sha.notna()],part.commit_sha.dropna()))
    a,b,c = map(commits, partitions)
    audit["cross_split_commit_overlap"] = {"train_validation":len(a & b),"train_test":len(a & c),"validation_test":len(b & c)}
    audit["evaluation_unit"] = "workflow run attempt; repeated commit SHAs may occur, not unseen-commit evaluation"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(audit,indent=2,allow_nan=False),encoding="utf-8")
    return audit

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output",type=Path,default=Path("data/processed"))
    p.add_argument("--report",type=Path,default=Path("reports/dataset_audit.json"))
    a = p.parse_args()
    audit = prepare(a.input,a.output,a.report)
    print(json.dumps({k:audit[k] for k in ("raw_rows","eligible_rows","cleaning","boundary_purged_rows","splits")},indent=2))

if __name__ == "__main__":
    main()
