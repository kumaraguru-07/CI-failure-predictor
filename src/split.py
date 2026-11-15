"""Time-ordered splits with tied timestamps and label availability enforced."""
import pandas as pd

def chronological_split(frame, train_fraction=.70, validation_fraction=.15,
                        timestamp_column="started_at", completion_column="completed_at"):
    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1 or train_fraction + validation_fraction >= 1:
        raise ValueError("Fractions must leave a test split")
    d = frame.sort_values(timestamp_column, kind="stable")
    times = d[timestamp_column].drop_duplicates().sort_values()
    if len(times) < 3 or times.isna().any():
        raise ValueError("At least three distinct, valid timestamps are required")
    i = max(1, int(len(times)*train_fraction))
    j = max(i+1, int(len(times)*(train_fraction+validation_fraction)))
    if j >= len(times):
        raise ValueError("Insufficient timestamps for requested split")
    cut1, cut2 = times.iloc[i], times.iloc[j]
    train = d[d[timestamp_column] < cut1]
    validation = d[(d[timestamp_column] >= cut1) & (d[timestamp_column] < cut2)]
    test = d[d[timestamp_column] >= cut2]
    if completion_column in d:
        train = train[train[completion_column] < cut1]
        validation = validation[validation[completion_column] < cut2]
    if any(len(s) == 0 for s in (train, validation, test)):
        raise ValueError("Empty split after enforcing label availability")
    return train.copy(), validation.copy(), test.copy()
