"""Advisory pre-test GitHub prediction. Never returns a decision to skip CI."""
import argparse
import hashlib
import json
import os
import re
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request,HTTPRedirectHandler,build_opener
from src.github_features import GitHubClient,collect,utc
from src.ci_bundle import load_bundle
from src.ci_history import record

class ReleaseRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if urlparse(newurl).scheme!="https":
            raise ValueError("Release download redirects must use HTTPS")
        redirected=super().redirect_request(req,fp,code,msg,headers,newurl)
        if redirected and urlparse(req.full_url).hostname!=urlparse(newurl).hostname:
            redirected.remove_header("Authorization")
        return redirected

def download_package(url,destination):
    parsed = urlparse(url)
    api_asset=parsed.hostname=="api.github.com" and re.fullmatch(r"/repos/[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*/releases/assets/[0-9]+",parsed.path)
    public_asset=parsed.hostname=="github.com" and "/releases/download/" in parsed.path
    if parsed.scheme!="https" or not (api_asset or public_asset) or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.port not in (None,443):
        raise ValueError("Model URL must be a GitHub release download or release-asset API URL")
    headers={"User-Agent":"failure-aware-ci"}
    if api_asset:
        headers["Accept"]="application/octet-stream"
        headers["X-GitHub-Api-Version"]="2022-11-28"
        token=os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"]="Bearer "+token
    opener=build_opener(ReleaseRedirectHandler())
    with opener.open(Request(url,headers=headers),timeout=60) as response:
        size = 0
        with Path(destination).open("wb") as stream:
            while chunk:=response.read(1024*1024):
                size += len(chunk)
                if size>64*1024*1024:
                    raise ValueError("Model download exceeds 64 MB")
                stream.write(chunk)

def target_from_environment(repository,sha,event):
    repository = repository or os.environ.get("GITHUB_REPOSITORY")
    sha = sha or os.environ.get("GITHUB_SHA")
    if event and event.get("pull_request"):
        sha = event["pull_request"]["head"]["sha"]
    return repository,sha

def predict(client,engine,manifest,repository,sha,as_of,run_id=None,run_attempt=1):
    features,coverage = collect(client,repository,sha,as_of,current_run_id=run_id)
    detail = engine.explain(features)[0]
    moment = utc(as_of).isoformat()
    identity = f"{repository}:{sha}:{run_id or 'local'}:{run_attempt}:{moment}"
    return {"status":"predicted","prediction_id":hashlib.sha256(identity.encode()).hexdigest(),
        "repository":repository,"commit_sha":sha,"as_of":moment,"run_id":run_id,
        "run_attempt":run_attempt,"model_sha256":manifest["model_sha256"],
        "prediction":detail,"feature_coverage":coverage,
        "features":json.loads(features.to_json(orient="records"))[0],
        "target_outcome":"Required tests job of this Quality workflow run; not the advisory prediction job" if run_id else "Local read-only demonstration; no actual CI result attached"}

def summary(report):
    if report["status"]!="predicted":
        return "# Failure-aware CI\n\nPrediction unavailable. Required tests still run.\n\n"+report["reason"]+"\n"
    p = report["prediction"]
    lines = ["# Failure-aware CI","",f"Estimated failure risk: {p['failure_probability']:.1%} ({p['risk_level']}).","",
        "All mandatory checks remain required.","","Top signals:"]
    for f in p["top_increasing_signals"]:
        lines.append(f"- {f['feature'].replace('_',' ')}: {f['contribution_percentage_points']:+.2f} percentage points")
    lines += ["","CI advice:"]+["- "+a for a in p["ci_recommendation"]["priority"]]
    lines += ["","History is a bounded observed window; this model has not been validated for this live repository."]
    return "\n".join(lines)+"\n"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repository")
    p.add_argument("--commit")
    p.add_argument("--bundle",type=Path)
    p.add_argument("--bundle-sha256")
    p.add_argument("--output",type=Path,default=Path("reports/ci_prediction.json"))
    p.add_argument("--database",type=Path,default=Path("data/ci/predictions.sqlite3"))
    p.add_argument("--summary",type=Path)
    a = p.parse_args()
    as_of = datetime.now(timezone.utc)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    try:
        expected = a.bundle_sha256 or os.environ.get("CI_MODEL_SHA256","")
        if not re.fullmatch("[a-fA-F0-9]{64}",expected):
            raise ValueError("Configure CI_MODEL_SHA256 from the exported package")
        bundle_path = a.bundle
        if bundle_path is None:
            url = os.environ.get("CI_MODEL_URL","")
            if not url:
                raise ValueError("Configure CI_MODEL_URL with your published GitHub release asset")
            bundle_path = a.output.parent/"downloaded-ci-model.zip"
            download_package(url,bundle_path)
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        event = json.loads(Path(event_path).read_text()) if event_path else {}
        repository,sha = target_from_environment(a.repository,a.commit,event)
        engine,manifest = load_bundle(bundle_path,expected)
        report = predict(GitHubClient(),engine,manifest,repository,sha,as_of,
            os.environ.get("GITHUB_RUN_ID"),int(os.environ.get("GITHUB_RUN_ATTEMPT","1")))
        record(a.database,report)
    except Exception as exc:
        # The advisory job degrades without changing test requirements.
        # Deliberately avoid echoing exception strings that could include tokens.
        report = {"status":"unavailable","reason":f"Prediction setup or collection failed ({type(exc).__name__}). Check configuration, package checksum and GitHub API access.",
            "mandatory_tests_required":True,"exception_type":type(exc).__name__}
    a.output.write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    destination = a.summary or (Path(os.environ["GITHUB_STEP_SUMMARY"]) if os.environ.get("GITHUB_STEP_SUMMARY") else None)
    if destination:
        with destination.open("a",encoding="utf-8") as stream:
            stream.write(summary(report))
    print(json.dumps({"status":report["status"],"output":str(a.output)}))

if __name__=="__main__":
    main()
