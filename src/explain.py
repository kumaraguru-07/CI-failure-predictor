"""Probability-space SHAP for the frozen Random Forest and its imputation pipeline."""
import argparse
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import RandomForestClassifier
from src.predict import predict_frame
from src.recommendations import recommend_ci

class PredictionExplainer:
    def __init__(self,bundle,training_features,background_size=100):
        if not isinstance(background_size,int) or not 1<=background_size<=100:
            raise ValueError("background_size must be an integer from 1 to 100")
        pipeline = bundle["pipeline"]
        if list(pipeline.named_steps) != ["imputer","model"] or not isinstance(pipeline.named_steps["model"],RandomForestClassifier):
            raise ValueError("This explanation contract supports the saved Random Forest pipeline only")
        if list(pipeline.named_steps["model"].classes_) != [0,1]:
            raise ValueError("Expected binary classes [0, 1]")
        if len(training_features)==0:
            raise ValueError("Training background cannot be empty")
        # Reuse validation from inference; transforms never refit.
        sample = training_features.reset_index(drop=True).sample(n=min(background_size,len(training_features)),random_state=42)
        predict_frame(bundle,sample)
        self.bundle = bundle
        self.imputer = pipeline.named_steps["imputer"]
        self.names = list(self.imputer.get_feature_names_out(bundle["features"]))
        self.background_rows = len(sample)
        self.background_indices = [int(i) for i in sample.index]
        # sklearn's forest predicts using float32. Match that precision at split
        # boundaries, including training-median values introduced by imputation.
        background = np.asarray(self.imputer.transform(sample[bundle["features"]]),dtype=np.float32)
        self.background = background
        self.forest = pipeline.named_steps["model"]
        self.explainer = shap.TreeExplainer(pipeline.named_steps["model"],data=background,
            feature_names=self.names,feature_perturbation="interventional",model_output="probability")

    def explain(self,frame,top_k=3):
        if not len(frame) or not isinstance(top_k,int) or top_k<1:
            raise ValueError("At least one row and positive top_k required")
        predictions = predict_frame(self.bundle,frame)
        transformed = np.asarray(self.imputer.transform(frame[self.bundle["features"]]),dtype=np.float32)
        result = self.explainer(transformed,check_additivity=True)
        values = np.asarray(result.values)
        bases = np.asarray(result.base_values)
        if values.ndim != 3 or values.shape[2] != 2 or bases.shape != (len(frame),2):
            raise ValueError("Unexpected binary Random Forest SHAP shape")
        contributions,baseline = values[:,:,1],bases[:,1]
        reconstructed = baseline+contributions.sum(axis=1)
        methods = ["interventional_tree_shap"]*len(frame)
        failed = ~np.isclose(reconstructed,predictions.failure_probability.to_numpy(),atol=1e-6,rtol=1e-5)
        if failed.any():
            # Some Tree SHAP/library edge cases fail local accuracy. Compute
            # model-agnostic permutation SHAP against the SAME background, never
            # alter/rescale contributions to conceal the mismatch.
            fallback = shap.PermutationExplainer(lambda x:self.forest.predict_proba(x)[:,1],
                self.background,feature_names=self.names,seed=42)
            fixed = fallback(transformed[failed],max_evals=10*(2*len(self.names)+1))
            contributions[failed] = fixed.values
            baseline[failed] = fixed.base_values
            for position in np.flatnonzero(failed):
                methods[position] = "permutation_shap_fallback"
            reconstructed = baseline+contributions.sum(axis=1)
        np.testing.assert_allclose(reconstructed,predictions.failure_probability.to_numpy(),
                                   atol=1e-6,rtol=1e-5,
                                   err_msg="SHAP contributions do not reconstruct failure probability")
        rows = []
        for i in range(len(frame)):
            factors = []
            for j,name in enumerate(self.names):
                is_indicator = name.startswith("missingindicator_")
                source = name.removeprefix("missingindicator_") if is_indicator else name
                raw = frame.iloc[i][source]
                missing = bool(pd.isna(raw))
                contribution = float(contributions[i,j])
                factors.append({"feature":name,"kind":"missing_indicator" if is_indicator else "feature",
                    "input_value":None if missing else float(raw),
                    "value_used":float(transformed[i,j]),"input_was_missing":missing,
                    "contribution":contribution,"contribution_percentage_points":100*contribution,
                    "direction":"increases" if contribution>0 else "decreases" if contribution<0 else "neutral"})
            positive = sorted((f for f in factors if f["contribution"]>0),key=lambda f:-f["contribution"])
            negative = sorted((f for f in factors if f["contribution"]<0),key=lambda f:f["contribution"])
            risk = str(predictions.iloc[i].risk_level)
            missing_inputs = [c for c in self.bundle["features"] if pd.isna(frame.iloc[i][c])]
            rows.append({"row_position":i,"model":self.bundle["model_name"],
                "attribution_method":methods[i],
                "failure_probability":float(predictions.iloc[i].failure_probability),
                "risk_level":risk,"base_probability":float(baseline[i]),
                "reconstructed_probability":float(reconstructed[i]),
                "additivity_error":float(abs(reconstructed[i]-predictions.iloc[i].failure_probability)),
                "missing_input_features":missing_inputs,
                "input_quality_note":"Some inputs were replaced using training medians; interpret this estimate with that limitation." if missing_inputs else "All required input features were supplied.",
                "top_increasing_signals":positive[:top_k],"top_decreasing_signals":negative[:top_k],
                "all_contributions":factors,"ci_recommendation":recommend_ci(risk,frame.iloc[i].to_dict()),
                "interpretation":"Contributions describe this model score relative to the training background; they are not proven failure causes."})
        return rows

def file_digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()

def load_verified_explainer(model_path,training_path):
    model_path,training_path = Path(model_path),Path(training_path)
    manifest = json.loads((model_path.parent/"results.json").read_text(encoding="utf-8"))
    if file_digest(model_path) != manifest["model_sha256"]:
        raise ValueError("Model does not match frozen training artifact")
    if file_digest(training_path) != manifest["data_sha256"]["train"]:
        raise ValueError("Explanation background must match frozen training partition")
    bundle = joblib.load(model_path)  # Trusted local artifact only.
    return PredictionExplainer(bundle,pd.read_parquet(training_path)),manifest

def report_markdown(report):
    lines = ["# Prediction explanations", "", "These signals explain model scores, not proven causes of CI failure.", ""]
    for row in report["rows"]:
        lines += [f"## Input row {row['row_position'] + 1}", "",
            f"Estimated failure probability: {row['failure_probability']:.2%}. Risk: {row['risk_level']}.",
            "", row["input_quality_note"], "",
            "| Signal | Effect on score (percentage points) |", "|---|---:|"]
        for factor in row["top_increasing_signals"]+row["top_decreasing_signals"]:
            label = factor["feature"].replace("_"," ")
            lines.append(f"| {label} | {factor['contribution_percentage_points']:+.3f} |")
        lines += ["", f"Background score: {row['base_probability']:.2%}. Full-contribution reconstruction error: {row['additivity_error']:.3g}.",
            "", "CI advice:", ""]
        lines += ["- "+action for action in row["ci_recommendation"]["priority"]]
        lines += ["- All mandatory checks must run and pass before merging.", ""]
    return "\n".join(lines)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model",type=Path,default=Path("models/baseline_v1/model.joblib"))
    p.add_argument("--training-background",type=Path,default=Path("data/processed/train.parquet"))
    p.add_argument("--input",type=Path,default=Path("data/processed/validation.parquet"))
    p.add_argument("--output",type=Path,default=Path("reports/explanation_example.json"))
    p.add_argument("--limit",type=int,default=3)
    p.add_argument("--markdown",type=Path,help="Optional readable report path")
    a = p.parse_args()
    if not 1<=a.limit<=100:
        p.error("--limit must be 1..100 for interactive explanations")
    protected = {path.resolve() for path in (a.model,a.training_background,a.input,a.model.parent/"results.json")}
    destinations = [a.output] + ([a.markdown] if a.markdown else [])
    if any(path.resolve() in protected for path in destinations) or len({path.resolve() for path in destinations}) != len(destinations):
        p.error("Report paths must differ from input/model/manifest paths and each other")
    engine,manifest = load_verified_explainer(a.model,a.training_background)
    frame = pd.read_parquet(a.input) if a.input.suffix.lower()==".parquet" else pd.read_csv(a.input)
    rows = engine.explain(frame.head(a.limit))
    report = {"method":"Failure-class probability SHAP; interventional Tree SHAP with explicit permutation fallback if additivity fails",
        "background_source":str(a.training_background),"background_rows":engine.background_rows,
        "background_training_row_indices":engine.background_indices,
        "shap_version":shap.__version__,"model_sha256":manifest["model_sha256"],
        "background_sha256":manifest["data_sha256"]["train"],
        "risk_thresholds":engine.bundle["thresholds"],"rows":rows}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    if a.markdown:
        a.markdown.parent.mkdir(parents=True,exist_ok=True)
        a.markdown.write_text(report_markdown(report),encoding="utf-8")
    print(json.dumps({"output":str(a.output),"rows":len(rows),
        "max_additivity_error":max(r["additivity_error"] for r in rows)},indent=2))

if __name__ == "__main__":
    main()
