# Prediction explanations

These signals explain model scores, not proven causes of CI failure.

## Input row 1

Estimated failure probability: 1.89%. Risk: LOW.

All required input features were supplied.

| Signal | Effect on score (percentage points) |
|---|---:|
| total churn | +0.079 |
| author historical failure rate | -1.212 |
| recent 10 build failure rate | -0.794 |
| author recent failure rate | -0.605 |

Background score: 6.77%. Full-contribution reconstruction error: 1.89e-09.

CI advice:

- Use the standard CI order.
- All mandatory checks must run and pass before merging.

## Input row 2

Estimated failure probability: 14.95%. Risk: HIGH.

All required input features were supplied.

| Signal | Effect on score (percentage points) |
|---|---:|
| history build count | +7.247 |
| recent 5 build failure rate | +1.501 |
| author recent failure rate | +1.464 |
| project historical failure rate | -1.739 |
| hour of day | -0.622 |
| author historical failure rate | -0.426 |

Background score: 6.77%. Full-contribution reconstruction error: 1.41e-09.

CI advice:

- Run fast failure-detecting checks early.
- Prioritize the full required test suite and integration checks.
- Review the prediction signals before merging.
- All mandatory checks must run and pass before merging.

## Input row 3

Estimated failure probability: 2.76%. Risk: MEDIUM.

All required input features were supplied.

| Signal | Effect on score (percentage points) |
|---|---:|
| recent 10 build failure rate | +0.211 |
| author history count | +0.019 |
| lines deleted | +0.004 |
| author historical failure rate | -1.287 |
| project historical failure rate | -0.768 |
| time since last failure hours | -0.522 |

Background score: 6.77%. Full-contribution reconstruction error: 1.76e-09.

CI advice:

- Run fast unit checks early.
- Run the remaining required checks in the normal pipeline.
- All mandatory checks must run and pass before merging.
