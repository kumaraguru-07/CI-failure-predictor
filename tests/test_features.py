import pandas as pd
from src.features import build_features

def builds():
    return pd.DataFrame({
        "repository":["a","a","a","b"], "author":["u"]*4,
        "started_at":pd.to_datetime(["2026-01-01","2026-01-02","2026-01-03","2026-01-04"],utc=True),
        "completed_at":pd.to_datetime(["2026-01-02","2026-01-02T12:00Z","2026-01-05","2026-01-05"],utc=True,format="mixed"),
        "build_failed":[1,0,1,0], "changed_files":[["requirements.txt"]]*4})

def test_history_respects_completion_and_repository():
    x = build_features(builds())
    assert x.history_build_count.tolist() == [0,0,2,0]
    assert x.iloc[2].project_historical_failure_rate == .5
    assert x.iloc[2].touched_files_failure_rate == .5
    assert x.dependency_file_changed.tolist() == [1]*4

def test_current_and_future_labels_cannot_change_earlier_features():
    d = builds()
    x = build_features(d)
    d.loc[2:,"build_failed"] = 0
    pd.testing.assert_frame_equal(x.iloc[:3],build_features(d).iloc[:3])

def test_missing_files_are_unknown_not_negative():
    x = build_features(builds().drop(columns="changed_files"))
    assert x.dependency_file_changed.isna().all()
    assert x.file_history_available.eq(0).all()
