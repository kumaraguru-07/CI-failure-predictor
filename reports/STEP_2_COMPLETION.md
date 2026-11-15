# Step 2 completion — 2026-11-15

Status: complete for the eligible binary-outcome workflow-run cohort.

## Verified data

- Original file: 303,079 rows, 194,638,363 bytes; publisher SHA256 matches.
- Excluded unknown/nonbinary outcomes: 134,492 rows.
- Excluded missing/invalid execution times after outcome filtering: 22,477 rows.
- Other exclusions (identity, reversed time, conflicting or duplicate identity): 0.
- Eligible cleaned data: 146,110 rows across 32 repositories.
- Boundary purges: 962 rows, because labels were unavailable before the next split.
- Final usable split total: 145,148 rows.

| Partition | Rows | Failures | Failure rate |
|---|---:|---:|---:|
| Train | 102,664 | 6,777 | 6.60% |
| Validation | 20,409 | 1,024 | 5.02% |
| Test | 22,075 | 1,043 | 4.72% |

The low failure frequency and change in prevalence make accuracy alone unsuitable
for later evaluation. Use validation for model/threshold choice and reserve test
for final metrics. No model has been fit and no threshold has been chosen here.

## Completed work

- Source attribution and license, download checksum enforcement and schema mapping.
- UTC timestamp parsing, explicit label policy (including startup failures),
  outcome filtering, missing-value handling and invalid-metric handling.
- Build-attempt identity and duplicate/conflict checks with reconciled exclusion counts.
- Saved canonical cleaned dataset and chronological feature/target partitions.
- Saved separate aligned identity/timestamp metadata for future evaluations.
- Tied timestamps kept together; training and validation label-availability checks.
- Aggregate missingness, numeric distributions, class balance and provenance audit.
- Nine tests covering cleaning, cancellations, conflicts, time boundaries, feature
  leakage, missing paths, checksum rejection and an end-to-end fixture pipeline.
- Full real-output verification: numeric-only features, binary labels, aligned
  metadata, disjoint build identities, label availability and reconciled counts.

## Recorded limitations

The publisher describes mixed CI platforms. Individual platform provenance is not
verified, so these are not claimed to be modern GitHub Actions-only results.
Missing timestamps are excluded rather than fabricated. updated_at is a conservative
outcome-availability proxy and may be later than actual completion.

Changed-file paths are absent, so path-derived features are missing. Training-only
imputation and feature selection belong to the next phase. Raw author identifiers
and outcome metadata are excluded from model inputs.

Repeated commit SHA/repository pairs across partitions: 39 train/validation,
4 train/test, 33 validation/test. Workflow runs can share commits; evaluation is
therefore of future workflow-run attempts, not entirely unseen commits. Build-attempt
identities do not overlap. Historical outcomes are replayed only when observed,
including past evaluation outcomes, which simulates continuous online use.

Raw and processed row-level data remain local and ignored by Git. Source contract,
rebuild commands and column roles: docs/DATASET.md. Detailed machine-readable
evidence: reports/dataset_audit.json.
