import numpy as np
import pandas as pd
import pytest
from src.train import thresholds,training_columns,validate_frame,metrics
from src.predict import risk_level,predict_frame

def test_threshold_is_chosen_from_validation_scores_and_risk_boundaries_agree():
    y = [0,1,0,1]
    p = np.array([.1,.8,.2,.9])
    cuts = thresholds(y,p)
    assert cuts["binary_threshold"] == .8
    assert cuts["low_upper"] <= cuts["medium_upper"]
    assert risk_level(.8,cuts) == "HIGH"
    assert metrics(y,p,.8)["f1"] == 1
    with pytest.raises(ValueError):
        risk_level(float("nan"),cuts)

def test_feature_selection_uses_training_only():
    d = pd.DataFrame({"a":[1,2],"missing":[np.nan]*2,"constant":[1,1]})
    assert training_columns(d,["a","missing","constant"]) == ["a"]

def test_metadata_and_schema_mismatch_are_rejected():
    d = pd.DataFrame({"lines_added":[1,2],"build_failed":[0,1]})
    validate_frame(d)
    with pytest.raises(ValueError):
        validate_frame(d.assign(duration=[1,2]))
    with pytest.raises(ValueError):
        validate_frame(d,["wrong"])
    with pytest.raises(ValueError):
        predict_frame({"features":["missing"]},d)

def test_pipeline_imputer_is_fit_on_training_only():
    from src.train import make_models
    model = make_models()["logistic_regression"]
    x = pd.DataFrame({"a":[1.,3.,np.nan,5.],"b":[0.,1.,0.,1.]})
    model.fit(x,[0,1,0,1])
    before = model.named_steps["imputer"].statistics_.copy()
    model.predict_proba(pd.DataFrame({"a":[100000.,np.nan],"b":[1.,0.]}))
    np.testing.assert_array_equal(before,model.named_steps["imputer"].statistics_)
    assert before[0] == 3.
