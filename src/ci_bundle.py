"""Export/load a compact trusted inference bundle; no raw dataset or labels."""
import argparse
import io
import json
import zipfile
from importlib.metadata import version
from pathlib import Path
import joblib
import pandas as pd
from src.explain import file_digest,PredictionExplainer

FILES = {"model.joblib","manifest.json","background.parquet"}

def export_bundle(model_dir,training_path,output):
    model_dir,training_path,output = Path(model_dir),Path(training_path),Path(output)
    if output.exists():
        raise FileExistsError("Refusing to overwrite a published model package")
    results = json.loads((model_dir/"results.json").read_text())
    model = model_dir/"model.joblib"
    if file_digest(model)!=results["model_sha256"] or file_digest(training_path)!=results["data_sha256"]["train"]:
        raise ValueError("Model/training partition differ from frozen experiment")
    bundle = joblib.load(model)
    background = pd.read_parquet(training_path)[bundle["features"]].sample(n=100,random_state=42).reset_index(drop=True)
    buffer = io.BytesIO()
    background.to_parquet(buffer,index=False)
    import hashlib
    data = buffer.getvalue()
    manifest = {"format_version":1,"model_sha256":results["model_sha256"],
        "background_sha256":hashlib.sha256(data).hexdigest(),
        "training_partition_sha256":results["data_sha256"]["train"],
        "features":bundle["features"],"thresholds":bundle["thresholds"],
        "model_name":bundle["model_name"],"environment":results["environment"],
        "shap_version":version("shap"),"background_rows":100,
        "training_data_attribution":{"authors":"Joshua Faruna; Funmilayo Sanusi",
            "source":"https://doi.org/10.17632/mggwn7rj9f.1","license":"CC BY 4.0",
            "license_url":"https://creativecommons.org/licenses/by/4.0/",
            "changes":"Cleaned, filtered and transformed; 100 numeric training-feature rows used as SHAP background"}}
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(model,"model.joblib")
        archive.writestr("manifest.json",json.dumps(manifest,indent=2))
        archive.writestr("background.parquet",data)
    digest = file_digest(output)
    output.with_suffix(".sha256").write_text(digest+"\n",encoding="utf-8")
    return {"package":str(output),"sha256":digest,"size_bytes":output.stat().st_size}

def load_bundle(path,expected_sha256):
    import hashlib
    path = Path(path)
    if len(expected_sha256)!=64 or file_digest(path)!=expected_sha256.lower():
        raise ValueError("CI model package checksum mismatch")
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if len(members)!=3 or {i.filename for i in members}!=FILES:
            raise ValueError("CI package must contain only the three expected files")
        if sum(i.file_size for i in members)>64*1024*1024:
            raise ValueError("CI package exceeds uncompressed size limit")
        model = archive.read("model.joblib")
        background = archive.read("background.parquet")
        manifest = json.loads(archive.read("manifest.json"))
    if hashlib.sha256(model).hexdigest()!=manifest["model_sha256"] or hashlib.sha256(background).hexdigest()!=manifest["background_sha256"]:
        raise ValueError("Internal CI package hash mismatch")
    for name in ("scikit-learn","numpy","pandas","joblib"):
        if version(name)!=manifest["environment"][name]:
            raise ValueError(f"Use the pinned CI version of {name}")
    bundle = joblib.load(io.BytesIO(model))  # Only AFTER externally pinned package hash verification.
    if bundle["features"]!=manifest["features"] or bundle["thresholds"]!=manifest["thresholds"]:
        raise ValueError("CI package feature/threshold contract mismatch")
    engine = PredictionExplainer(bundle,pd.read_parquet(io.BytesIO(background)))
    return engine,manifest

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model-dir",type=Path,default=Path("models/baseline_v1"))
    p.add_argument("--training",type=Path,default=Path("data/processed/train.parquet"))
    p.add_argument("--output",type=Path,default=Path("artifacts/ci-model-v1.zip"))
    a = p.parse_args()
    print(json.dumps(export_bundle(a.model_dir,a.training,a.output),indent=2))

if __name__=="__main__":
    main()
