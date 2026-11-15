"""Fixed-budget train/validation selection. Held-out test is opened only after freezing."""
import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path
import platform
import time
import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, confusion_matrix,
    f1_score, precision_recall_curve, precision_score, recall_score, roc_auc_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
from src.features import BASELINE_FEATURES, FEATURE_COLUMNS

def metrics(y, p, threshold=.5):
    y, p = np.asarray(y), np.asarray(p)
    pred = p >= threshold
    return {"average_precision":float(average_precision_score(y,p)),
        "roc_auc":float(roc_auc_score(y,p)), "brier_score":float(brier_score_loss(y,p)),
        "precision":float(precision_score(y,pred,zero_division=0)),
        "recall":float(recall_score(y,pred,zero_division=0)),
        "f1":float(f1_score(y,pred,zero_division=0)),
        "threshold":float(threshold),"confusion_matrix_tn_fp_fn_tp":confusion_matrix(y,pred,labels=[0,1]).ravel().tolist(),
        "rows":len(y),"failure_prevalence":float(y.mean())}

def thresholds(y,p):
    precision, recall, ts = precision_recall_curve(y,p)
    if not len(ts):
        raise ValueError("Cannot select thresholds from empty probabilities")
    f1 = 2*precision[:-1]*recall[:-1]/np.maximum(precision[:-1]+recall[:-1],1e-15)
    # Ties resolve toward the higher threshold (fewer warnings).
    best = len(f1)-1-np.argmax(f1[::-1])
    high = float(ts[best])
    candidates = ts[(recall[:-1] >= .90) & (ts <= high)]
    low = float(candidates[-1]) if len(candidates) else high
    return {"low_upper":low,"medium_upper":high,"binary_threshold":high,
        "policy":"high = maximum validation F1; low = highest threshold with >=90% validation recall, capped at high",
        "equal_cutoff_means_empty_medium":low == high}

def training_columns(train, requested):
    return [c for c in requested if c in train and train[c].notna().any() and train[c].nunique(dropna=True)>1]

def make_models(seed=42):
    return {
        "logistic_regression":Pipeline([("imputer",SimpleImputer(strategy="median",add_indicator=True)),
            ("scaler",StandardScaler()),("model",LogisticRegression(max_iter=1000,random_state=seed))]),
        "random_forest":Pipeline([("imputer",SimpleImputer(strategy="median",add_indicator=True)),
            ("model",RandomForestClassifier(n_estimators=120,max_depth=14,min_samples_leaf=8,
                max_features="sqrt",n_jobs=2,random_state=seed))]),
        "xgboost":Pipeline([("imputer",SimpleImputer(strategy="median",add_indicator=True)),
            ("model",XGBClassifier(n_estimators=220,max_depth=4,learning_rate=.06,
                subsample=.85,colsample_bytree=.9,min_child_weight=8,reg_lambda=2,
                objective="binary:logistic",eval_metric="logloss",tree_method="hist",
                n_jobs=2,random_state=seed))])}

def validate_frame(d, expected=None):
    if "build_failed" not in d or set(d.build_failed.unique()) != {0,1}:
        raise ValueError("Both binary target classes are required")
    feature_cols = [c for c in d if c != "build_failed"]
    if set(feature_cols)-set(FEATURE_COLUMNS):
        raise ValueError("Unknown feature columns; possible metadata leakage")
    if expected is not None and list(d.columns) != expected:
        raise ValueError("Dataset schema differs between partitions")
    if not all(pd.api.types.is_numeric_dtype(d[c]) for c in feature_cols):
        raise ValueError("Features must be numeric")
    if np.isinf(d[feature_cols].to_numpy(dtype=float)).any():
        raise ValueError("Infinite feature values")

def digest(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()

def train(data_dir, output):
    data_dir, output = Path(data_dir), Path(output)
    if output.exists():
        raise FileExistsError("Run directory already exists; never overwrite a frozen evaluation")
    tr = pd.read_parquet(data_dir/"train.parquet")
    va = pd.read_parquet(data_dir/"validation.parquet")
    validate_frame(tr)
    validate_frame(va,list(tr.columns))
    train_meta = pd.read_parquet(data_dir/"train_metadata.parquet")
    val_meta = pd.read_parquet(data_dir/"validation_metadata.parquet")
    test_meta = pd.read_parquet(data_dir/"test_metadata.parquet")
    if not (train_meta.completed_at.max()<val_meta.started_at.min() and
            val_meta.completed_at.max()<test_meta.started_at.min()):
        raise ValueError("Labels cross partition boundaries")
    ytr,yva = tr.build_failed,va.build_failed
    output.mkdir(parents=True)
    comparison, fitted = {}, {}
    for mode, requested in (("baseline",BASELINE_FEATURES),("enhanced",FEATURE_COLUMNS)):
        cols = training_columns(tr,requested)
        for name, model in make_models().items():
            key = mode+"_"+name
            started = time.perf_counter()
            model.fit(tr[cols],ytr)
            p = model.predict_proba(va[cols])[:,1]
            comparison[key] = metrics(yva,p)
            comparison[key]["fit_and_validation_seconds"] = time.perf_counter()-started
            comparison[key]["features"] = cols
            fitted[key] = (model,cols,p)
            print(key, "validation AP",round(comparison[key]["average_precision"],4),flush=True)
    winner = max(comparison,key=lambda k:comparison[k]["average_precision"])
    model,cols,pva = fitted[winner]
    cuts = thresholds(yva,pva)
    benchmarks = {
        "constant_train_prevalence":metrics(yva,np.full(len(va),ytr.mean())),
        "observed_project_history":metrics(yva,va.project_historical_failure_rate.fillna(ytr.mean()).to_numpy())}
    report = {"selection_metric":"validation average precision (AP), not trapezoidal PR area",
        "seed":42,"winner":winner,"validation_comparison":comparison,
        "validation_benchmarks":benchmarks,"thresholds":cuts,
        "winner_validation_at_selected_threshold":metrics(yva,pva,cuts["binary_threshold"]),
        "feature_columns":cols,"dropped_from_enhanced":sorted(set(FEATURE_COLUMNS)-set(training_columns(tr,FEATURE_COLUMNS))),
        "environment":{"python":platform.python_version(),**{n:version(n) for n in ("scikit-learn","xgboost","pandas","numpy","joblib")}},
        "data_sha256":{n:digest(data_dir/(n+".parquet")) for n in ("train","validation")},
        "limitations":["Uncalibrated probability estimates; Brier score reported",
            "Model fit on train only; no refit on validation",
            "Workflow-run evaluation, repeated commit SHAs may cross splits",
            "Online history replay includes prior observed evaluation outcomes",
            "No file paths in source, so no file-specific contribution claims",
            "Single chronological split; no cross-repository generalisation claim"]}
    # Persist selection and fitted artifact BEFORE reading held-out test targets.
    bundle = {"pipeline":model,"features":cols,"thresholds":cuts,"model_name":winner,
        "environment":report["environment"],"format_version":1}
    joblib.dump(bundle,output/"model.joblib")
    (output/"validation_selection.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    test = pd.read_parquet(data_dir/"test.parquet")
    validate_frame(test,list(tr.columns))
    ptest = model.predict_proba(test[cols])[:,1]
    restored = joblib.load(output/"model.joblib")
    np.testing.assert_allclose(restored["pipeline"].predict_proba(test[cols].iloc[:25])[:,1],ptest[:25])
    report["test"] = metrics(test.build_failed,ptest,cuts["binary_threshold"])
    report["test_constant_train_prevalence"] = metrics(test.build_failed,np.full(len(test),ytr.mean()),cuts["binary_threshold"])
    report["data_sha256"]["test"] = digest(data_dir/"test.parquet")
    report["model_sha256"] = digest(output/"model.joblib")
    report["test_evaluation_count"] = 1
    pd.DataFrame({"failure_probability":ptest,"build_failed":test.build_failed}).to_parquet(output/"test_predictions.parquet",index=False)
    (output/"results.json").write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    print(json.dumps({"winner":winner,"thresholds":cuts,"test":report["test"]},indent=2),flush=True)
    return report

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data",type=Path,default=Path("data/processed"))
    p.add_argument("--output",type=Path,default=Path("models/baseline_v1"))
    a = p.parse_args()
    train(a.data,a.output)

if __name__ == "__main__":
    main()
