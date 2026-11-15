import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from tests.test_explanations import fixture
from src.explain import file_digest
import src.dashboard_data as data

APP = Path(__file__).resolve().parents[1]/"app.py"

@pytest.fixture
def dashboard_root(tmp_path,monkeypatch):
    x,b = fixture()
    modeldir = tmp_path/"models/baseline_v1"
    processed = tmp_path/"data/processed"
    reports = tmp_path/"reports"
    for p in (modeldir,processed,reports):
        p.mkdir(parents=True)
    model = modeldir/"model.joblib"
    joblib.dump(b,model)
    train,val = processed/"train.parquet",processed/"validation.parquet"
    x.to_parquet(train,index=False)
    x.assign(build_failed=[0,0,0,0,1,1,1,1]).to_parquet(val,index=False)
    pd.DataFrame({"repository":["repo/a"]*4+["repo/b"]*4,
        "build_id":range(8),"commit_sha":[f"sha{i}" for i in range(8)],
        "started_at":pd.date_range("2026-01-01",periods=8,tz="UTC")}).to_parquet(processed/"validation_metadata.parquet",index=False)
    report = {"model_sha256":file_digest(model),
        "data_sha256":{"train":file_digest(train),"validation":file_digest(val)},
        "test":{"recall":.4,"precision":.2,"average_precision":.15,"rows":8,
                "confusion_matrix_tn_fp_fn_tp":[3,1,2,2]},
        "thresholds":b["thresholds"],"limitations":["Synthetic test fixture"],
        "validation_comparison":{"example":{"average_precision":.2}}}
    (modeldir/"results.json").write_text(json.dumps(report))
    (reports/"dataset_audit.json").write_text(json.dumps({"raw_rows":8,"eligible_rows":8}))
    monkeypatch.setattr(data,"PROJECT_ROOT",tmp_path)
    return tmp_path

def test_csv_parser_and_ignored_targets():
    content = b"lines_added,project_historical_failure_rate,build_failed\n1,0.2,1\n2,,0\n"
    d,ignored = data.parse_feature_csv(content,["lines_added","project_historical_failure_rate"])
    assert ignored==["build_failed"]
    assert "build_failed" not in d
    assert pd.isna(d.iloc[1].project_historical_failure_rate)
    invalid = [
        b"lines_added,lines_added\n1,2\n",
        b"wrong\n1\n",b"lines_added\n-1\n",b"lines_added\ninf\n",
        b"lines_added\nhello\n", b"lines_added\n",
        ("lines_added\n"+"1\n"*501).encode(),
        b"\xff\xfe"
    ]
    for content in invalid:
        with pytest.raises(ValueError):
            data.parse_feature_csv(content,["lines_added"])
    with pytest.raises(ValueError):
        data.parse_feature_csv(b"x"* (data.MAX_BYTES+1),["lines_added"])

def test_csv_ranges_flags_and_history_limits():
    for content,cols in [
        (b"hour_of_day\n24\n",["hour_of_day"]),
        (b"day_of_week\n1.2\n",["day_of_week"]),
        (b"recent_5_build_failure_rate\n1.2\n",["recent_5_build_failure_rate"]),
        (b"lines_added,dependency_file_changed\n1,2\n",["lines_added"])]:
        with pytest.raises(ValueError):
            data.parse_feature_csv(content,cols)
    result={"failure_probability":.2,"risk_level":"HIGH"}
    history=[]
    for i in range(101):
        history=data.add_history(history,result,str(i))
    assert len(history)==100 and history[0]["source"]=="1"
    escaped = data.csv_download(pd.DataFrame({"name":["=cmd","+cmd","normal"]})).decode()
    assert "'=cmd" in escaped and "'+cmd" in escaped

def test_historical_filters_explanation_history_and_clear(dashboard_root):
    at = AppTest.from_file(str(APP),default_timeout=30).run()
    assert not at.exception
    assert at.metric[0].value=="8"
    at.selectbox(key="repository").select("repo/b").run()
    assert not at.exception
    assert at.metric[0].value=="4"
    at.button(key="analyze").click().run()
    assert not at.exception
    assert at.session_state["last_explanation"]["result"]["ci_recommendation"]["mandatory_checks_required"]
    assert len(at.session_state["prediction_history"])==1
    at.selectbox(key="repository").select("repo/a").run()
    assert not at.exception
    # The selected build changed; the prior explanation is not displayed.
    assert not any(m.label=="Estimated failure probability" for m in at.metric)
    at.selectbox(key="view").select("Session history").run()
    assert not at.exception
    assert len(at.dataframe[0].value)==1
    at.button(key="clear_history").click().run()
    assert not at.exception
    assert len(at.session_state["prediction_history"])==0

def test_results_and_csv_empty_state(dashboard_root):
    at = AppTest.from_file(str(APP),default_timeout=30).run()
    at.selectbox(key="view").select("Model results").run()
    assert not at.exception
    assert any(m.label=="Warning precision" for m in at.metric)
    at.selectbox(key="view").select("Predict from CSV").run()
    assert not at.exception
    assert any("Download the template" in i.value for i in at.info)

def test_missing_artifacts_show_recovery_message(tmp_path,monkeypatch):
    monkeypatch.setattr(data,"PROJECT_ROOT",tmp_path)
    at = AppTest.from_file(str(APP),default_timeout=30).run()
    assert not at.exception
    assert at.error and "could not load" in at.error[0].value

def test_real_validation_alignment_and_hash_guard(dashboard_root):
    service=data.DashboardService(dashboard_root)
    frame,summary=data.validation_data(dashboard_root,service)
    assert len(frame)==len(summary)==8
    assert "build_failed" not in frame
    path=dashboard_root/"data/processed/validation.parquet"
    changed=pd.read_parquet(path)
    changed.loc[0,"churn"]=999.
    changed.to_parquet(path,index=False)
    with pytest.raises(ValueError,match="Validation data"):
        data.validation_data(dashboard_root,service)

def test_uploaded_csv_prediction_explanation_and_stale_result(dashboard_root,monkeypatch):
    import io
    import streamlit as st
    monkeypatch.setattr(st,"file_uploader",lambda *a,**k:io.BytesIO(b"churn,history,build_failed\n1,0,1\n8,1,0\n"))
    at = AppTest.from_file(str(APP),default_timeout=30).run()
    at.selectbox(key="view").select("Predict from CSV").run()
    assert not at.exception
    assert len(at.dataframe[0].value)==2
    assert at.info and "build_failed" in at.info[0].value
    at.button(key="analyze").click().run()
    assert not at.exception
    assert at.session_state["prediction_history"][-1]["actual_outcome"]=="Unknown"
    at.number_input(key="upload_row").set_value(2).run()
    assert not at.exception
    assert not any(m.label=="Estimated failure probability" for m in at.metric)
    at.button(key="analyze").click().run()
    assert not at.exception
    assert len(at.session_state["prediction_history"])==2

def test_bad_upload_is_an_error_message_not_an_exception(dashboard_root,monkeypatch):
    import io
    import streamlit as st
    monkeypatch.setattr(st,"file_uploader",lambda *a,**k:io.BytesIO(b"wrong\nhello\n"))
    at = AppTest.from_file(str(APP),default_timeout=30).run()
    at.selectbox(key="view").select("Predict from CSV").run()
    assert not at.exception
    assert at.error and "Missing required columns" in at.error[0].value
