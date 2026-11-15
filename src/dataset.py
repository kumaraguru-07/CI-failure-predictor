"""Explicit, audited adapter for Mendeley mggwn7rj9f version 1."""
import pandas as pd

OUTCOMES = {"success": 0, "passed": 0, "failure": 1, "failed": 1,
            "errored": 1, "error": 1, "startup_failure": 1}
REQUIRED = {"repo", "repo_name", "run_id", "conclusion", "run_started_at",
            "updated_at", "author_email", "author_name", "author",
            "additions", "deletions", "files_modified"}

def normalize(raw, return_audit=False):
    if not REQUIRED.issubset(raw):
        raise ValueError(f"Missing columns: {sorted(REQUIRED - set(raw))}")
    d = pd.DataFrame(index=raw.index)
    def text(s):
        return s.astype("string").str.strip().replace("", pd.NA)
    d["repository"] = text(raw.repo).fillna(text(raw.repo_name))
    d["build_id"] = text(raw.run_id)
    d["attempt"] = pd.to_numeric(raw.get("run_attempt", pd.Series(1, index=raw.index)), errors="coerce").fillna(1)
    d["started_at"] = pd.to_datetime(raw.run_started_at, utc=True, errors="coerce", format="mixed")
    d["completed_at"] = pd.to_datetime(raw.updated_at, utc=True, errors="coerce", format="mixed")
    outcome = text(raw.conclusion).str.lower()
    d["build_failed"] = outcome.map(OUTCOMES)
    d["author"] = text(raw.author_email).fillna(text(raw.author_name)).fillna(text(raw.author))
    d["commit_sha"] = text(raw.get("commit_sha", pd.Series(pd.NA, index=raw.index)))
    for source, dest in [("additions", "lines_added"), ("deletions", "lines_deleted"),
                         ("files_modified", "files_changed_total")]:
        d[dest] = pd.to_numeric(raw[source], errors="coerce")
        d.loc[(d[dest] < 0) | ~d[dest].map(lambda n: pd.isna(n) or abs(n) != float("inf")), dest] = float("nan")
    audit = {"input_rows": len(raw), "excluded": {},
             "raw_outcomes": outcome.fillna("<missing>").value_counts().to_dict()}
    def exclude(mask, reason):
        nonlocal d
        mask = mask.fillna(False)
        audit["excluded"][reason] = int(mask.sum())
        d = d.loc[~mask].copy()
    exclude(d.repository.isna() | d.build_id.isna(), "missing_build_identity")
    exclude(d.build_failed.isna(), "unknown_or_nonbinary_outcome")
    exclude(d.started_at.isna() | d.completed_at.isna(), "missing_or_invalid_execution_times")
    exclude(d.completed_at < d.started_at, "completion_before_start")
    keys = ["repository", "build_id", "attempt"]
    # Different snapshots of a rerun must not be mistaken for independent builds.
    signature = ["started_at", "completed_at", "build_failed", "commit_sha",
                 "lines_added", "lines_deleted", "files_changed_total"]
    conflicts = d.groupby(keys, dropna=False)[signature].transform("nunique").gt(1).any(axis=1)
    exclude(conflicts, "conflicting_duplicate_identity")
    exclude(d.duplicated(keys), "duplicate_identity")
    d["build_failed"] = d.build_failed.astype("int8")
    d = d.sort_values(["started_at", "repository", "build_id", "attempt"], kind="stable").reset_index(drop=True)
    audit["eligible_rows"] = len(d)
    assert len(d) + sum(audit["excluded"].values()) == len(raw)
    return (d, audit) if return_audit else d
