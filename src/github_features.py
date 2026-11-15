"""Read-only, bounded GitHub REST collection of pre-build features."""
import json
import os
import re
from datetime import datetime,timezone
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request,urlopen
import pandas as pd
from src.features import build_features

REPO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")
SHA = re.compile(r"^[0-9a-fA-F]{40}$")
LABELS = {"success":0,"failure":1,"startup_failure":1}

def utc(value):
    result = pd.Timestamp(value)
    if result.tzinfo is None:
        raise ValueError("Timestamp must include timezone")
    return result.tz_convert("UTC")

class GitHubClient:
    def __init__(self,token=None):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.requests = 0
    def get(self,path):
        if not path.startswith("/repos/"):
            raise ValueError("Only repository read endpoints are supported")
        headers = {"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"failure-aware-ci"}
        if self.token:
            headers["Authorization"] = "Bearer "+self.token
        try:
            self.requests += 1
            with urlopen(Request("https://api.github.com"+path,headers=headers),timeout=30) as response:
                return json.load(response),response.headers.get("Link","")
        except HTTPError as exc:
            # Do not echo tokens, response bodies or raw request headers.
            raise RuntimeError(f"GitHub read failed (HTTP {exc.code}); check access/rate limits") from None

def author_key(commit):
    author = (commit.get("commit") or {}).get("author") or {}
    return author.get("email") or author.get("name")

def collect(client,repository,sha,as_of=None,current_run_id=None,max_history_pages=3):
    if not isinstance(repository,str) or not isinstance(sha,str) or not REPO.fullmatch(repository) or not SHA.fullmatch(sha):
        raise ValueError("Expected owner/repository and full 40-character commit SHA")
    if not isinstance(max_history_pages,int) or not 1<=max_history_pages<=5:
        raise ValueError("History page budget must be 1..5")
    cutoff = utc(as_of or datetime.now(timezone.utc))
    commit,link = client.get(f"/repos/{repository}/commits/{sha}?per_page=100&page=1")
    if commit.get("sha","").lower()!=sha.lower():
        raise ValueError("GitHub returned a different commit")
    authored = ((commit.get("commit") or {}).get("committer") or {}).get("date")
    if authored and utc(authored)>cutoff:
        raise ValueError("Commit postdates prediction time")
    files = list(commit.get("files") or [])
    page = 1
    while 'rel="next"' in link and page<30:
        page += 1
        extra,link = client.get(f"/repos/{repository}/commits/{sha}?per_page=100&page={page}")
        files.extend(extra.get("files") or [])
    paths_complete = not ('rel="next"' in link) and len(files)<3000
    stats = commit.get("stats") or {}
    for key in ("additions","deletions"):
        if not isinstance(stats.get(key),(int,float)) or stats[key]<0:
            raise ValueError("Commit diff statistics unavailable")
    history,seen = [],set()
    run_pages = 0
    has_more = False
    for page in range(1,max_history_pages+1):
        payload,link = client.get(f"/repos/{repository}/actions/runs?"+urlencode({"per_page":100,"page":page,"status":"completed"}))
        run_pages = page
        has_more = 'rel="next"' in link
        for run in payload.get("workflow_runs",[]):
            identity = (str(run.get("id")),int(run.get("run_attempt",1)))
            if identity in seen or str(run.get("id"))==str(current_run_id):
                continue
            seen.add(identity)
            if run.get("status")!="completed" or run.get("conclusion") not in LABELS:
                continue
            # Do not train history on prediction-only demonstration workflows.
            if run.get("name")=="Failure risk":
                continue
            try:
                start,end = utc(run["run_started_at"]),utc(run["updated_at"])
            except (KeyError,ValueError,TypeError):
                continue
            if end>=cutoff or end<start:
                continue
            a = ((run.get("head_commit") or {}).get("author") or {})
            history.append({"repository":repository,"started_at":start,"completed_at":end,
                "build_failed":LABELS[run["conclusion"]],"author":a.get("email") or a.get("name"),
                "changed_files":None})
        if not has_more:
            break
    current_paths = {f["filename"] for f in files if isinstance(f.get("filename"),str)}
    old_paths = {f["previous_filename"] for f in files if f.get("status")=="renamed" and isinstance(f.get("previous_filename"),str)}
    paths = sorted(current_paths|old_paths) if paths_complete else None
    current = {"repository":repository,"started_at":cutoff,"completed_at":cutoff,
        # A placeholder needed by the historical feature builder. It is NEVER
        # consumed: features are calculated before this row is queued.
        "build_failed":0,"author":author_key(commit),"changed_files":paths,
        "lines_added":stats["additions"],"lines_deleted":stats["deletions"],
        "files_changed_total":len(current_paths) if paths is not None else float("nan")}
    frame = pd.DataFrame(history+[current])
    result = build_features(frame).iloc[[-1]].reset_index(drop=True)
    coverage = {"history_rows":len(history),"history_pages":run_pages,
        "history_may_be_truncated":has_more,"history_is_bounded_window":True,
        "changed_paths_complete":paths_complete,"changed_paths_count":len(paths) if paths is not None else None,
        "author_identity_available":bool(author_key(commit)),
        "notes":["History features describe only the retrieved completed-run window, not lifetime repository history.",
            "updated_at is used conservatively for outcome availability.",
            "No current build outcome or duration is used.",
            "The model was evaluated on historical data, not validated for this live repository."]}
    return result,coverage
