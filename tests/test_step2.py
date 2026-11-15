import pandas as pd
import pytest
from src.dataset import normalize
from src.preprocess import clean_builds
from src.split import chronological_split
from src.prepare import prepare

def raw_fixture():
    return pd.DataFrame({
        "repo":["a"]*30, "repo_name":[None]*30,"run_id":list(range(30)),
        "conclusion":["failure" if i%4==0 else "success" for i in range(30)],
        "run_started_at":pd.date_range("2026-01-01",periods=30,tz="UTC").astype(str),
        "updated_at":(pd.date_range("2026-01-01",periods=30,tz="UTC")+pd.Timedelta(hours=1)).astype(str),
        "author_email":["u"]*30,"author_name":[None]*30,"author":[None]*30,
        "additions":[1]*30,"deletions":[1]*30,"files_modified":[1]*30,
    })

def test_cleaning_counts_reconcile_and_conflicts_are_quarantined():
    raw = raw_fixture()
    duplicate = raw.iloc[[0]].copy()
    conflict = raw.iloc[[1]].copy()
    conflict["conclusion"] = "failure"
    raw = pd.concat([raw,duplicate,conflict],ignore_index=True)
    raw.loc[2,"updated_at"] = "invalid"
    raw.loc[3,"conclusion"] = "cancelled"
    d,a = normalize(raw,True)
    assert a["excluded"]["duplicate_identity"] == 1
    assert a["excluded"]["conflicting_duplicate_identity"] == 2
    assert len(d)+sum(a["excluded"].values()) == len(raw)
    assert not d.build_id.eq("1").any()

def test_split_keeps_ties_and_purges_unavailable_labels():
    d = normalize(raw_fixture())
    d.loc[0,"completed_at"] = d.started_at.max()
    parts = chronological_split(d)
    assert 0 not in parts[0].index
    assert parts[0].completed_at.max() < parts[1].started_at.min()
    assert parts[1].completed_at.max() < parts[2].started_at.min()
    assert set(parts[0].index).isdisjoint(parts[1].index)
    tied = d.copy()
    tied.loc[20,"started_at"] = tied.loc[21,"started_at"]
    a,b,c = chronological_split(tied)
    assert set(a.started_at).isdisjoint(b.started_at)
    with pytest.raises(ValueError):
        chronological_split(d.iloc[:2])

def test_unknown_outcomes_cannot_become_success_and_metadata_is_excluded():
    d = pd.DataFrame({"build_started_at":["2026-01-01"]*3,
                      "build_outcome":["success","cancelled","startup_failure"],
                      "duration":[1,2,3],"conclusion":["success"]*3,"secret_field":["x"]*3})
    cleaned = clean_builds(d)
    assert cleaned.build_failed.tolist() == [0,1]
    assert cleaned.columns.tolist() == ["build_started_at","build_failed"]

def test_pipeline_outputs_and_checksum_guard(tmp_path):
    raw = tmp_path/"sample.csv"
    raw_fixture().to_csv(raw,index=False)
    with pytest.raises(ValueError,match="checksum"):
        prepare(raw,tmp_path/"bad",tmp_path/"bad.json")
    audit = prepare(raw,tmp_path/"processed",tmp_path/"audit.json",verify_checksum=False)
    assert audit["eligible_rows"] == 30
    for name in ("train","validation","test"):
        d = pd.read_parquet(tmp_path/"processed"/(name+".parquet"))
        meta = pd.read_parquet(tmp_path/"processed"/(name+"_metadata.parquet"))
        assert len(d) == len(meta) > 0
        assert not {"author","commit_sha","completed_at","duration"}.intersection(d)
        assert d.build_failed.isin([0,1]).all()
    assert (tmp_path/"interim"/"builds_clean.parquet").exists()
