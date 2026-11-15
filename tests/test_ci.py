import hashlib
import json
from pathlib import Path
import zipfile
import pytest
from src.github_features import collect
from src.ci_predict import predict,target_from_environment,summary
from src.ci_history import record,rows,import_outcomes
from src.ci_bundle import load_bundle
from tests.test_explanations import fixture
from src.explain import PredictionExplainer

SHA = "a"*40
NOW = "2026-01-03T00:00:00+00:00"
class FakeGitHub:
    def __init__(self):
        self.requests=[]
    def get(self,path):
        self.requests.append(path)
        if "/commits/" in path:
            return {"sha":SHA,"commit":{"author":{"email":"u"},"committer":{"date":"2026-01-02T00:00:00Z"}},
                "stats":{"additions":12,"deletions":3},"files":[{"filename":"requirements.txt"},{"filename":".github/workflows/test.yml"}]},""
        def run(i,start,end,label,author="u"):
            return {"id":i,"run_attempt":1,"name":"Quality","status":"completed","conclusion":label,
                "run_started_at":start,"updated_at":end,"head_commit":{"author":{"email":author}}}
        return {"workflow_runs":[
            run(1,"2026-01-01T00:00Z","2026-01-01T01:00Z","failure"),
            run(2,"2026-01-02T00:00Z","2026-01-02T01:00Z","success"),
            run(3,"2026-01-02T00:00Z","2026-01-04T01:00Z","failure"),
            run(4,"2026-01-02T00:00Z","2026-01-03T00:00Z","failure"),
            run(5,"2026-01-02T00:00Z","2026-01-02T01:00Z","cancelled")]},""

def prediction_fixture():
    return {"status":"predicted","prediction_id":"test-id","repository":"owner/repo",
        "commit_sha":SHA,"as_of":NOW,"run_id":"7","run_attempt":1,
        "model_sha256":"b"*64,"prediction":{"failure_probability":.2,"risk_level":"HIGH"}}

def test_live_features_exclude_overlapping_equal_time_cancelled_and_current_runs():
    client=FakeGitHub()
    frame,coverage=collect(client,"owner/repo",SHA,NOW,current_run_id=2)
    row=frame.iloc[0]
    assert row.project_historical_failure_rate==1
    assert row.history_build_count==1 and row.author_history_count==1
    assert row.total_churn==15 and row.files_changed_total==2
    assert row.dependency_file_changed==1 and row.ci_workflow_changed==1
    assert coverage["history_rows"]==1 and "build_failed" not in frame

def test_history_pages_and_commit_file_pages_are_bounded():
    class Paged(FakeGitHub):
        def get(self,path):
            value,_=super().get(path)
            return value,'<next>; rel="next"'
    client=Paged()
    frame,coverage=collect(client,"owner/repo",SHA,NOW,max_history_pages=2)
    assert coverage["history_pages"]==2
    assert coverage["history_may_be_truncated"]
    assert not coverage["changed_paths_complete"]
    assert frame.files_changed_total.isna().all()
    assert frame.dependency_file_changed.isna().all()
    assert len(client.requests)==32

@pytest.mark.parametrize("repository,sha",[("../bad",SHA),("owner/repo","main"),("owner/repo","abc")])
def test_invalid_repository_or_nonimmutable_commit_rejected(repository,sha):
    with pytest.raises(ValueError):
        collect(FakeGitHub(),repository,sha,NOW)

def test_no_history_is_unknown_not_zero_failure_rate():
    class Empty(FakeGitHub):
        def get(self,path):
            if "/actions/" in path:
                return {"workflow_runs":[]},""
            return super().get(path)
    frame,coverage=collect(Empty(),"owner/repo",SHA,NOW)
    assert frame.project_historical_failure_rate.isna().all()
    assert frame.history_build_count.iloc[0]==0

def test_pr_uses_head_commit_and_unavailable_summary_requires_tests():
    _,sha=target_from_environment("owner/repo","b"*40,{"pull_request":{"head":{"sha":SHA}}})
    assert sha==SHA
    text=summary({"status":"unavailable","reason":"No configured model"})
    assert "Required tests still run" in text

def test_sqlite_prediction_then_outcome_join_and_conflict(tmp_path):
    db=tmp_path/"history.sqlite3"
    p=prediction_fixture()
    record(db,p)
    assert rows(db)[0]["actual_failed"] is None
    record(db,p,"failure","2026-01-03T01:00:00+00:00")
    record(db,p)  # Reimport must never erase an observed result.
    assert len(rows(db))==1 and rows(db)[0]["actual_failed"]==1
    with pytest.raises(ValueError):
        record(db,p,"success","2026-01-03T02:00:00+00:00")
    with pytest.raises(ValueError):
        record(db,{**p,"prediction_id":"other"},"failure","2026-01-02T00:00:00+00:00")
    assert record(db,{"status":"unavailable"}) is None

def test_package_checksum_and_member_limits(tmp_path):
    path=tmp_path/"unsafe.zip"
    with zipfile.ZipFile(path,"w") as z:
        z.writestr("../model.joblib","invalid")
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError,match="checksum"):
        load_bundle(path,"0"*64)
    with pytest.raises(ValueError,match="three expected"):
        load_bundle(path,digest)

def test_workflow_tests_are_not_conditioned_on_risk():
    workflow=(Path(__file__).resolve().parents[1]/".github/workflows/quality.yml").read_text()
    assert "needs: risk" in workflow
    assert "if: ${{ !cancelled() }}" in workflow
    assert "continue-on-error: true" in workflow
    assert "pull_request_target" not in workflow
    assert "CI_MODEL_SHA256" in workflow

def test_complete_prediction_with_real_service_contract():
    # The small forest is for testing, not a reported CI accuracy result.
    x,b=fixture()
    b["features"]=["files_changed_total","history_build_count"]
    x.columns=b["features"]
    # Train this test-only model against the same named inputs.
    b["pipeline"].fit(x,[0,0,0,0,1,1,1,1])
    engine=PredictionExplainer(b,x)
    result=predict(FakeGitHub(),engine,{"model_sha256":"b"*64},"owner/repo",SHA,NOW,9,1)
    assert result["status"]=="predicted"
    assert result["prediction"]["ci_recommendation"]["mandatory_checks_required"]
    assert not result["prediction"]["ci_recommendation"]["skip_tests"]
    assert "author" not in result and "build_failed" not in result["features"]

def test_outcome_import_is_idempotent_and_rejects_prediction_changes(tmp_path):
    db=tmp_path/"one.sqlite3"
    p=prediction_fixture()
    record(db,p,"success","2026-01-03T01:00:00+00:00")
    export=tmp_path/"outcomes.json"
    export.write_text(json.dumps(rows(db)))
    other=tmp_path/"two.sqlite3"
    import_outcomes(other,export)
    import_outcomes(other,export)
    assert len(rows(other))==1 and rows(other)[0]["actual_failed"]==0
    changed={**p,"commit_sha":"f"*40}
    with pytest.raises(ValueError,match="immutable"):
        record(other,changed)

def test_unconfigured_cli_degrades_without_logging_tokens(tmp_path,monkeypatch,capsys):
    import sys
    from src.ci_predict import main
    monkeypatch.delenv("CI_MODEL_SHA256",raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY",raising=False)
    monkeypatch.setenv("GITHUB_TOKEN","never-print-this-token")
    output=tmp_path/"unavailable.json"
    monkeypatch.setattr(sys,"argv",["ci_predict","--output",str(output)])
    main()
    report=json.loads(output.read_text())
    assert report["status"]=="unavailable" and report["mandatory_tests_required"]
    assert "never-print-this-token" not in output.read_text()+capsys.readouterr().out

def test_workflow_yaml_structure():
    import yaml
    text=(Path(__file__).resolve().parents[1]/".github/workflows/quality.yml").read_text()
    workflow=yaml.load(text,Loader=yaml.BaseLoader)
    assert set(workflow["on"])=={"push","pull_request","workflow_dispatch"}
    assert workflow["jobs"]["tests"]["needs"]=="risk"
    assert workflow["jobs"]["outcome"]["needs"]==["risk","tests"]
    assert workflow["permissions"]=={"contents":"read"}

def test_export_load_round_trip_excludes_targets_and_author_identifiers(tmp_path):
    from importlib.metadata import version
    import io
    import joblib
    import pandas as pd
    from src.ci_bundle import export_bundle
    x,b=fixture()
    modeldir=tmp_path/"model"
    modeldir.mkdir()
    model=modeldir/"model.joblib"
    joblib.dump(b,model)
    training=tmp_path/"train.parquet"
    pd.concat([x]*20,ignore_index=True).assign(build_failed=0,author="private@example.invalid").to_parquet(training,index=False)
    results={"model_sha256":hashlib.sha256(model.read_bytes()).hexdigest(),
        "data_sha256":{"train":hashlib.sha256(training.read_bytes()).hexdigest()},
        "environment":{n:version(n) for n in ("numpy","pandas","scikit-learn","joblib")}}
    (modeldir/"results.json").write_text(json.dumps(results))
    package=tmp_path/"package.zip"
    metadata=export_bundle(modeldir,training,package)
    engine,manifest=load_bundle(package,metadata["sha256"])
    assert len(engine.explain(x.iloc[:1]))==1
    with zipfile.ZipFile(package) as z:
        background=pd.read_parquet(io.BytesIO(z.read("background.parquet")))
        assert set(background)==set(b["features"])
    assert manifest["training_data_attribution"]["license"]=="CC BY 4.0"
    with pytest.raises(FileExistsError):
        export_bundle(modeldir,training,package)

def test_api_errors_redact_access_tokens(monkeypatch):
    from urllib.error import HTTPError
    import src.github_features as github
    def denied(*args,**kwargs):
        raise HTTPError("https://api.github.com",403,"sensitive token value",{},None)
    monkeypatch.setattr(github,"urlopen",denied)
    with pytest.raises(RuntimeError) as info:
        github.GitHubClient("sensitive token value").get("/repos/owner/repo/actions/runs")
    assert "sensitive" not in str(info.value)

def test_private_asset_redirect_strips_authorization():
    from urllib.request import Request
    from src.ci_predict import ReleaseRedirectHandler
    handler=ReleaseRedirectHandler()
    req=Request("https://api.github.com/repos/owner/repo/releases/assets/12",headers={"Authorization":"Bearer private-token"})
    redirected=handler.redirect_request(req,None,302,"",{},"https://release-assets.githubusercontent.com/file")
    assert redirected.get_header("Authorization") is None
    with pytest.raises(ValueError):
        handler.redirect_request(req,None,302,"",{},"http://example.com/file")

def test_private_release_download_uses_binary_api_and_redacts_other_hosts(tmp_path,monkeypatch):
    import io
    import src.ci_predict as ci
    received=[]
    class FakeOpener:
        def open(self,request,timeout):
            received.append(request)
            return io.BytesIO(b"zip-content")
    monkeypatch.setattr(ci,"build_opener",lambda *args:FakeOpener())
    monkeypatch.setenv("GITHUB_TOKEN","private-token")
    path=tmp_path/"asset.zip"
    ci.download_package("https://api.github.com/repos/owner/repo/releases/assets/12",path)
    assert received[-1].get_header("Authorization")=="Bearer private-token"
    assert received[-1].get_header("Accept")=="application/octet-stream"
    ci.download_package("https://github.com/owner/repo/releases/download/v1/model.zip",path)
    assert received[-1].get_header("Authorization") is None
    with pytest.raises(ValueError):
        ci.download_package("https://example.com/asset.zip",path)
