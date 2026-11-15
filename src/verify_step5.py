"""Repeatable Step 5 validation checks; no test-set evaluation or refitting."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from src.explain import load_verified_explainer,file_digest
from src.predict import predict_frame

def main():
    model = Path("models/baseline_v1/model.joblib")
    train = Path("data/processed/train.parquet")
    validation = Path("data/processed/validation.parquet")
    before = file_digest(model)
    engine,manifest = load_verified_explainer(model,train)
    data = pd.read_parquet(validation)
    pred = predict_frame(engine.bundle,data)
    chosen = []
    counts = {}
    for risk in ("LOW","MEDIUM","HIGH"):
        positions = np.flatnonzero(pred.risk_level.eq(risk).to_numpy())
        if len(positions)<10:
            raise ValueError("Need at least 10 validation examples per band")
        indices = np.random.default_rng(42).choice(positions,10,replace=False)
        chosen.extend(indices.tolist())
        counts[risk] = len(indices)
    missing = data[engine.bundle["features"]].isna().any(axis=1)
    missing_positions = np.flatnonzero(missing.to_numpy())[:10].tolist()
    chosen = sorted(set(chosen+missing_positions))
    rows = engine.explain(data.iloc[chosen])
    for row in rows:
        advice = row["ci_recommendation"]
        assert advice["mandatory_checks_required"] and advice["skip_tests"] is False
        assert set(advice["change_evidence"].values())=={"unknown"}
        assert not any("file" in f["feature"] and "history" in f["feature"] for f in row["all_contributions"])
    # Include the fully imputed boundary case without assigning an actual outcome.
    empty = pd.DataFrame(np.nan,index=[0],columns=engine.bundle["features"])
    imputed = engine.explain(empty)[0]
    assert len(imputed["missing_input_features"])==len(engine.bundle["features"])
    assert file_digest(model)==before==manifest["model_sha256"]
    report = {"status":"passed","validation_rows_checked":len(rows),
        "risk_band_sampling":counts,"missing_input_rows_added":len(missing_positions),
        "all_missing_boundary_case_checked":True,
        "permutation_fallback_rows":sum(r["attribution_method"]=="permutation_shap_fallback" for r in rows+[imputed]),
        "max_additivity_error":max(r["additivity_error"] for r in rows+[imputed]),
        "model_sha256":before,"model_unchanged":True,
        "training_background_verified":True,"mandatory_checks_preserved":True,
        "unknown_file_changes_not_invented":True,"final_test_data_accessed":False,
        "validation_data_sha256":file_digest(validation)}
    Path("reports/STEP_5_VERIFICATION.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
