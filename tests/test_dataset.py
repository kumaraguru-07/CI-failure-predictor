import pandas as pd
from src.dataset import normalize

def test_adapter_excludes_unknown_outcomes_and_invalid_times():
    raw = pd.DataFrame({
        'repo':['a']*4, 'repo_name':[None]*4, 'run_id':[1,2,3,4],
        'conclusion':['success','cancelled','failure','failure'],
        'run_started_at':['2026-01-01']*4,
        'updated_at':['2026-01-02','2026-01-02','invalid','2026-01-02'],
        'author_email':['u']*4,'author_name':['u']*4,'author':['u']*4,
        'additions':[1]*4,'deletions':[1]*4,'files_modified':[1]*4,
        'duration':[20]*4,
    })
    out = normalize(raw)
    assert out.build_failed.tolist() == [0,1]
    assert 'duration' not in out
