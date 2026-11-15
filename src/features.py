"""Features at prediction time; only strictly earlier completed builds count."""
from collections import defaultdict, deque
import heapq
import json
from pathlib import PurePosixPath
import numpy as np
import pandas as pd

BASELINE_FEATURES = (
    "files_changed_total", "lines_added", "lines_deleted", "total_churn",
    "day_of_week", "hour_of_day", "project_historical_failure_rate",
)
ENHANCED_FEATURES = (
    "recent_5_build_failure_rate", "recent_10_build_failure_rate", "consecutive_failures",
    "time_since_last_failure_hours", "author_historical_failure_rate",
    "author_recent_failure_rate", "touched_files_failure_rate", "dependency_file_changed",
    "configuration_file_changed", "ci_workflow_changed", "docker_file_changed",
    "directories_changed", "history_build_count", "author_history_count", "file_history_available",
)
FEATURE_COLUMNS = BASELINE_FEATURES + ENHANCED_FEATURES

def file_paths(value):
    if isinstance(value, str):
        value = json.loads(value)  # Contract: JSON list, never comma splitting paths.
    if not isinstance(value, list) or any(not isinstance(p, str) for p in value):
        raise ValueError("changed_files must be a JSON list of path strings")
    return sorted(set(p.replace("\\\\", "/") for p in value))

def build_features(builds):
    required = {"repository", "started_at", "completed_at", "build_failed", "author"}
    if not required.issubset(builds):
        raise ValueError(f"Missing columns: {sorted(required - set(builds))}")
    d = builds.sort_values("started_at", kind="stable").reset_index(drop=True)
    for c in ("started_at", "completed_at"):
        d[c] = pd.to_datetime(d[c], utc=True, errors="raise", format="mixed")
    if d[["repository", "started_at", "completed_at", "build_failed"]].isna().any().any():
        raise ValueError("Missing identity, times or labels")
    if not d.build_failed.isin([0, 1]).all() or (d.completed_at < d.started_at).any():
        raise ValueError("Invalid labels or completion times")
    # Histories are scoped to repository, including author/file histories.
    project, authors, files = defaultdict(list), defaultdict(list), defaultdict(list)
    failures, author_failures, last_failures, streaks = defaultdict(int), defaultdict(int), {}, defaultdict(int)
    pending, rows = [], []
    for i, r in d.iterrows():
        now = r.started_at
        while pending and pending[0][0] < now:
            end, j, repo, author, paths, label = heapq.heappop(pending)
            project[repo].append((end, label))
            failures[repo] += label
            streaks[repo] = streaks[repo] + 1 if label else 0
            if label:
                last_failures[repo] = end
            if pd.notna(author):
                authors[(repo, author)].append(label)
                author_failures[(repo, author)] += label
            if paths is not None:
                for path in paths:
                    files[(repo, path)].append(label)
        repo, author = r.repository, r.author
        ph = project[repo]
        ah = authors[(repo, author)] if pd.notna(author) else []
        labels = [x[1] for x in ph[-10:]]
        mean = lambda x: float(np.mean(x)) if len(x) else np.nan
        streak = streaks[repo]
        last_failure = last_failures.get(repo)
        paths = file_paths(r.changed_files) if "changed_files" in d and not (r.changed_files is None or isinstance(r.changed_files, float)) else None
        row = {c: np.nan for c in FEATURE_COLUMNS}
        for c in ("lines_added", "lines_deleted", "files_changed_total"):
            if c in d:
                row[c] = r[c]
        row.update(total_churn=row["lines_added"] + row["lines_deleted"],
            day_of_week=now.dayofweek, hour_of_day=now.hour,
            project_historical_failure_rate=failures[repo]/len(ph) if ph else np.nan,
            recent_5_build_failure_rate=mean(labels[-5:]),
            recent_10_build_failure_rate=mean(labels),
            consecutive_failures=streak, history_build_count=len(ph),
            time_since_last_failure_hours=(now-last_failure).total_seconds()/3600 if last_failure is not None else np.nan,
            author_historical_failure_rate=author_failures[(repo,author)]/len(ah) if ah else np.nan, author_recent_failure_rate=mean(ah[-10:]),
            author_history_count=len(ah), file_history_available=int(paths is not None))
        if paths is not None:
            names = [PurePosixPath(p).name for p in paths]
            row.update(
                touched_files_failure_rate=mean([mean(files[(repo,p)]) for p in paths if files[(repo,p)]]),
                dependency_file_changed=int(any(n in {"requirements.txt","pyproject.toml","package.json","package-lock.json","pom.xml","build.gradle","poetry.lock"} for n in names)),
                ci_workflow_changed=int(any(p.startswith(".github/workflows/") for p in paths)),
                docker_file_changed=int(any(n == "Dockerfile" or n.startswith("docker-compose") for n in names)),
                configuration_file_changed=int(any(PurePosixPath(p).suffix in {".yaml",".yml",".toml",".ini",".cfg"} or PurePosixPath(p).name == "Dockerfile" for p in paths)),
                directories_changed=len({str(PurePosixPath(p).parent) for p in paths}))
        rows.append(row)
        heapq.heappush(pending, (r.completed_at, i, repo, author, paths, int(r.build_failed)))
    return pd.DataFrame(rows, columns=FEATURE_COLUMNS)
