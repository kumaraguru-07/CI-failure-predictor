import hashlib
import json
import sys
from pathlib import Path
import pandas as pd
from tests.test_explanations import fixture
from src.explain import PredictionExplainer
from src.ci_history import record

def test_offline_verifier_preserves_hosted_evidence_and_accepts_observed_outcome(tmp_path,monkeypatch):
    import src.verify_ci as ci
    x,b=fixture()
    engine=PredictionExplainer(b,x)
    prediction=engine.explain(x.iloc[:1])[0]
    modeldir=tmp_path/"models/baseline_v1"
    modeldir.mkdir(parents=True)
    (modeldir/"results.json").write_text(json.dumps({"model_sha256":"b"*64}))
    reports=tmp_path/"reports"
    reports.mkdir()
    hosted=reports/"STEP_7_VERIFICATION.json"
    hosted.write_text('{"status":"hosted_verification_passed","proof":"preserve me"}')
    original=hosted.read_bytes()
    package=tmp_path/"package.zip"
    package.write_bytes(b"test-only-package")
    package.with_suffix(".sha256").write_text(hashlib.sha256(package.read_bytes()).hexdigest())
    snapshot={"status":"predicted","features":x.iloc[0].to_dict(),"prediction":prediction,
        "repository":"owner/repo","commit_sha":"a"*40,"run_id":"123","run_attempt":1,
        "model_sha256":"b"*64,"prediction_id":"fixture-id","as_of":"2026-01-01T00:00:00+00:00",
        "feature_coverage":{"history_rows":0}}
    source=reports/"ci_prediction.json"
    source.write_text(json.dumps(snapshot))
    record(tmp_path/"data/ci/predictions.sqlite3",snapshot,"success","2026-01-01T01:00:00+00:00")
    monkeypatch.setattr(ci,"load_bundle",lambda *args:(engine,{"model_sha256":"b"*64}))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys,"argv",["verify_ci","--bundle",str(package),"--snapshot",str(source)])
    ci.main()
    assert hosted.read_bytes()==original
    result=json.loads((reports/"CI_LOCAL_VERIFICATION.json").read_text())
    assert result["snapshot_outcome"]=="success"
    assert result["actual_outcomes_in_local_ledger"]==1
