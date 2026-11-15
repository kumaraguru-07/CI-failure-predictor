import pandas as pd

from src.preprocess import clean_builds


def test_clean_builds_removes_current_build_leakage_and_sorts_time():
    frame = pd.DataFrame({
        "build_started_at": ["2026-02-02T10:00:00Z", "2026-02-01T10:00:00Z"],
        "build_outcome": ["passed", "failed"],
        "build_duration": [20, 10],
    })
    result = clean_builds(frame)
    assert "build_duration" not in result
    assert result["build_failed"].tolist() == [1, 0]

