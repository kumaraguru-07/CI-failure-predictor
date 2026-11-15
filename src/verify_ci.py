"""Offline check of the portable model against an already collected live snapshot."""
import argparse
import json
from pathlib import Path
import pandas as pd
from src.ci_bundle import load_bundle
from src.explain import file_digest
from src.ci_history import rows

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--bundle",type=Path,default=Path("artifacts/ci-model-v1-attributed.zip"))
    p.add_argument("--snapshot",type=Path,default=Path("reports/ci_prediction.json"))
    a=p.parse_args()
    expected=a.bundle.with_suffix(".sha256").read_text().strip()
    frozen=Path("models/baseline_v1/results.json")
    before=file_digest(frozen)
    engine,manifest=load_bundle(a.bundle,expected)
    snapshot=json.loads(a.snapshot.read_text(encoding="utf-8"))
    if snapshot["status"]!="predicted":
        raise ValueError("A successful collected live snapshot is required")
    features=pd.DataFrame([snapshot["features"]],dtype=float)
    explanation=engine.explain(features)[0]
    difference=abs(explanation["failure_probability"]-snapshot["prediction"]["failure_probability"])
    assert difference<1e-12
    assert explanation["ci_recommendation"]["mandatory_checks_required"]
    assert not explanation["ci_recommendation"]["skip_tests"]
    assert file_digest(frozen)==before
    assert manifest["model_sha256"]==json.loads(frozen.read_text())["model_sha256"]
    local_records=rows("data/ci/predictions.sqlite3")
    matching=[r for r in local_records if r["prediction_id"]==snapshot["prediction_id"]]
    assert len(matching)==1 and matching[0]["result"] is None
    report={"status":"local_verification_passed","package_sha256":expected,
        "package_size_bytes":a.bundle.stat().st_size,"model_sha256":manifest["model_sha256"],
        "frozen_evaluation_unchanged":True,"package_prediction_difference":difference,
        "live_reference_snapshot":{"repository":snapshot["repository"],"commit_sha":snapshot["commit_sha"],
            "collected_at":snapshot["as_of"],"history_rows":snapshot["feature_coverage"]["history_rows"],
            "risk_level":explanation["risk_level"],"failure_probability":explanation["failure_probability"]},
        "local_ledger_pending_record_verified":True,"actual_ci_outcome_collected":False,
        "mandatory_tests_required":True,"github_hosted_workflow_executed":False,
        "activation_blocker":"No GitHub remote configured; repository URL and release/variable setup required"}
    Path("reports/STEP_7_VERIFICATION.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
