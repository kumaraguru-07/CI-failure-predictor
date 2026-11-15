import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from src.explain import PredictionExplainer
from src.recommendations import recommend_ci

def fixture():
    x = pd.DataFrame({"churn":[1.,2.,np.nan,4.,5.,6.,7.,8.],"history":[0.,0.,.1,.1,.5,.5,1.,1.]})
    p = Pipeline([("imputer",SimpleImputer(strategy="median",add_indicator=True)),
        ("model",RandomForestClassifier(n_estimators=8,max_depth=3,random_state=42))])
    p.fit(x,[0,0,0,0,1,1,1,1])
    return x,{"pipeline":p,"features":list(x),"model_name":"test_forest",
              "thresholds":{"low_upper":.2,"medium_upper":.6,"binary_threshold":.6}}

def test_shap_reconstructs_probability_and_excludes_target():
    x,b = fixture()
    e = PredictionExplainer(b,x,background_size=8)
    rows = e.explain(x.iloc[[0,2,7]].assign(build_failed=[0,0,1]))
    for r in rows:
        assert r["additivity_error"]<1e-6
        assert abs(r["base_probability"]+sum(f["contribution"] for f in r["all_contributions"])-r["failure_probability"])<1e-6
        assert all(f["feature"]!="build_failed" for f in r["all_contributions"])
        assert all(f["contribution"]>0 for f in r["top_increasing_signals"])
        assert all(f["contribution"]<0 for f in r["top_decreasing_signals"])
    factor = next(f for f in rows[1]["all_contributions"] if f["feature"]=="churn")
    assert factor["input_was_missing"] and factor["input_value"] is None
    assert factor["value_used"] == b["pipeline"].named_steps["imputer"].statistics_[0]

def test_background_is_seeded_and_does_not_refit():
    x,b = fixture()
    before = b["pipeline"].named_steps["imputer"].statistics_.copy()
    e1,e2 = PredictionExplainer(b,x,4),PredictionExplainer(b,x,4)
    assert e1.background_indices==e2.background_indices
    e1.explain(x)
    np.testing.assert_array_equal(before,b["pipeline"].named_steps["imputer"].statistics_)
    with pytest.raises(ValueError):
        e1.explain(x.drop(columns="history"))
    with pytest.raises(ValueError):
        e1.explain(x.iloc[:0])

@pytest.mark.parametrize("risk",["LOW","MEDIUM","HIGH"])
def test_ci_advice_never_skips_mandatory_checks(risk):
    r = recommend_ci(risk)
    assert r["mandatory_checks_required"] is True
    assert r["skip_tests"] is False

def test_unknown_risk_is_rejected():
    with pytest.raises(ValueError):
        recommend_ci("SAFE")
