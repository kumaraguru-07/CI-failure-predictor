import json
import sys
import joblib
import numpy as np
import pandas as pd
import pytest
from tests.test_explanations import fixture
from src.explain import (PredictionExplainer,load_verified_explainer,file_digest,main,report_markdown)
from src.recommendations import recommend_ci

def verified_fixture(tmp_path):
    x,b = fixture()
    model,train = tmp_path/"model.joblib",tmp_path/"train.parquet"
    joblib.dump(b,model)
    x.to_parquet(train,index=False)
    (tmp_path/"results.json").write_text(json.dumps({
        "model_sha256":file_digest(model),"data_sha256":{"train":file_digest(train)}}))
    return model,train,x

def test_verified_loader_rejects_altered_background_and_model(tmp_path):
    model,train,x = verified_fixture(tmp_path)
    engine,_ = load_verified_explainer(model,train)
    assert len(engine.explain(x.iloc[:1]))==1
    x.assign(churn=999.).to_parquet(train,index=False)
    with pytest.raises(ValueError,match="background"):
        load_verified_explainer(model,train)
    model.write_bytes(b"tampered")
    with pytest.raises(ValueError,match="Model"):
        load_verified_explainer(model,train)

def test_change_advice_requires_explicit_evidence_and_preserves_tests():
    unknown = recommend_ci("HIGH")
    assert set(unknown["change_evidence"].values())=={"unknown"}
    assert not any("dependency resolution" in s for s in unknown["priority"])
    known = recommend_ci("LOW",{"dependency_file_changed":1,"configuration_file_changed":0})
    assert any("dependency resolution" in s for s in known["priority"])
    assert known["mandatory_checks_required"] and not known["skip_tests"]
    assert known["change_evidence"]["configuration_file_changed"]=="unchanged"
    for bad in ["yes",2,float("inf")]:
        with pytest.raises(ValueError):
            recommend_ci("LOW",{"dependency_file_changed":bad})
    assert recommend_ci("MEDIUM",{"dependency_file_changed":float("nan")})["change_evidence"]["dependency_file_changed"]=="unknown"

def test_all_missing_row_and_string_indices_are_supported():
    x,b = fixture()
    x.index = ["a"+str(i) for i in range(len(x))]
    engine = PredictionExplainer(b,x)
    row = engine.explain(pd.DataFrame({"churn":[np.nan],"history":[np.nan]}))[0]
    assert row["missing_input_features"]==["churn","history"]
    assert row["additivity_error"]<1e-6
    with pytest.raises(ValueError):
        PredictionExplainer(b,x,background_size=101)
    with pytest.raises(ValueError):
        engine.explain(x,top_k=1.5)
    report = report_markdown({"rows":[row]})
    assert "mandatory checks" in report
    assert "Some inputs" in report

def test_cli_exports_json_markdown_and_rejects_input_overwrite(tmp_path,monkeypatch):
    model,train,x = verified_fixture(tmp_path)
    source = tmp_path/"input.csv"
    x.iloc[:2].to_csv(source,index=False)
    output,markdown = tmp_path/"explanation.json",tmp_path/"explanation.md"
    args = ["explain","--model",str(model),"--training-background",str(train),
        "--input",str(source),"--limit","2"]
    monkeypatch.setattr(sys,"argv",args+["--output",str(output),"--markdown",str(markdown)])
    main()
    report = json.loads(output.read_text())
    assert len(report["rows"])==2 and markdown.exists()
    before = source.read_bytes()
    monkeypatch.setattr(sys,"argv",args+["--output",str(source)])
    with pytest.raises(SystemExit):
        main()
    assert source.read_bytes()==before

def test_failed_tree_additivity_uses_labeled_fallback_without_rescaling():
    from types import SimpleNamespace
    x,b = fixture()
    engine = PredictionExplainer(b,x)
    original = engine.explainer
    def invalid_tree(values,**kwargs):
        result = original(values,**kwargs)
        return SimpleNamespace(values=result.values+.1,base_values=result.base_values.copy())
    engine.explainer = invalid_tree
    rows = engine.explain(x.iloc[:2])
    assert all(r['attribution_method']=='permutation_shap_fallback' for r in rows)
    assert all(r['additivity_error']<1e-6 for r in rows)
