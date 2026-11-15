"""Exercise the actual local app with real artifacts, without a browser or retraining."""
import json
from pathlib import Path
from streamlit.testing.v1 import AppTest
from src.explain import file_digest

def main():
    root = Path(__file__).resolve().parents[1]
    model = root/"models/baseline_v1/model.joblib"
    before = file_digest(model)
    evaluation = root/"models/baseline_v1/results.json"
    test_report_before = file_digest(evaluation)
    at = AppTest.from_file(str(root/"app.py"),default_timeout=60).run()
    assert not at.exception and not at.error
    initial_count = at.metric[0].value
    at.selectbox(key="risk_filter").select("HIGH").run()
    assert not at.exception and not at.error
    at.button(key="analyze").click().run()
    assert not at.exception and not at.error
    explanation = at.session_state["last_explanation"]["result"]
    assert explanation["risk_level"]=="HIGH"
    assert explanation["ci_recommendation"]["mandatory_checks_required"]
    for page in ("Model results","Predict from CSV","CI outcome history","Session history"):
        at.selectbox(key="view").select(page).run()
        assert not at.exception and not at.error
    assert len(at.session_state["prediction_history"])==1
    assert file_digest(model)==before
    assert file_digest(evaluation)==test_report_before
    report = {"status":"passed","validation_builds":initial_count,
        "views_checked":["Explore builds","Model results","Predict from CSV","CI outcome history","Session history"],
        "real_high_risk_explanation_checked":True,
        "explanation_additivity_error":explanation["additivity_error"],
        "session_history_recorded":True,"model_sha256":before,
        "frozen_model_unchanged":True,"frozen_evaluation_unchanged":True,
        "verification_method":"Streamlit AppTest with real local artifacts"}
    (root/"reports/STEP_6_VERIFICATION.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
