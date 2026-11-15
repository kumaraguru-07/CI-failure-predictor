# Viva questions and concise answers

**1. What is the project?**  
A research MVP that estimates CI failure risk from commit measurements and
previously available outcomes, explains the score and records the actual CI result.

**2. What is different from the reference repository?**  
An explicit availability-time audit, validation-only selection, extra recent/author
history, per-prediction explanations, a dashboard and hosted prediction/outcome flow.
The work is an engineering enhancement, not a claim of a new best algorithm.

**3. Did you copy the reference project?**  
No whole-project cloning/renaming was used. Its pipeline concepts informed an
independent implementation, with attribution in the report.

**4. Is the dataset entirely GitHub Actions?**  
The publisher describes mixed TravisTorrent/GitHub Actions data. Individual
platform membership was not verified; the report does not claim a modern-only cohort.

**5. Why were many records excluded?**  
Unknown/nonbinary outcomes and missing execution availability times do not support
the defined experiment. The exclusions are counted and reconcile with the source.

**6. How is leakage prevented?**  
No current duration, outcome or logs enter features. History must finish strictly
before prediction time. Training-only transforms and boundary-label purging prevent
future information entering model fitting/selection.

**7. Why not random splitting?**  
The intended use predicts future runs. Chronological splits better respect that
direction and expose temporal changes in failure frequency.

**8. Why are labels purged at the split boundary?**  
A build may start in training but finish after validation begins. Its outcome
would not be available when the model needs to be trained, so it cannot be used.

**9. What happens with overlapping builds?**  
An outcome contributes only after its availability time. Equal-time and unfinished
runs are excluded from the current feature snapshot.

**10. Which models were compared?**  
Logistic Regression, Random Forest and XGBoost, each with baseline/enhanced features.
Six fixed candidates were compared using validation average precision.

**11. Why did Random Forest win instead of XGBoost?**  
It had the highest observed validation AP, 0.2059. The project selects on evidence
for this split rather than assuming the more complex model must win.

**12. Why average precision rather than accuracy?**  
Failures are rare. Predicting every run as passing would look accurate while
detecting no failures. AP measures ranking across precision/recall tradeoffs.

**13. What are the final results?**  
Frozen test AP 0.1466, ROC-AUC 0.7631, precision 15.02%, recall 45.16%, F1 0.2255.
The model detects 471 failures, misses 572, and generates 2,664 false warnings.

**14. Is the model production-ready?**  
No such claim is made. False alarms, missed failures, temporal change and limited
external validation remain. It is a working research/integration prototype.

**15. How were LOW/MEDIUM/HIGH cutoffs selected?**  
On validation data. HIGH maximizes F1; LOW seeks at least 90% validation recall,
capped at HIGH. The actual frozen boundaries are about 2.56% and 13.07%.

**16. Are the scores calibrated probabilities?**  
They are model probability estimates without a separate calibration study.
Brier score is reported; risk bands are not safety guarantees.

**17. What does SHAP explain?**  
How features move the model score relative to a training background. It does not
prove the real cause of a failure, and correlated features can share attribution.

**18. What if SHAP does not add up?**  
The service checks reconstruction. A clearly labeled permutation-SHAP fallback
handles failed tree explanations; it does not rescale fabricated contributions.

**19. What happens with missing history?**  
Rates remain missing, counts identify the cold start, and training medians are
applied by the saved pipeline. The explanation tells the user which inputs were missing.

**20. Are file failure histories part of the trained model?**  
The code supports them, but the research source lacks file paths. They were not
learned or empirically validated. Live path flags can inform advice only.

**21. Does the system judge developers?**  
Author history is a repository-history signal, not a developer-skill assessment.
Raw author identities are excluded from model inputs and the dashboard.

**22. Does a LOW score skip tests?**  
No. All mandatory tests remain required. Recommendations are advice, not an
implemented test scheduler or automatic merge permission.

**23. How is the CI deployment verified?**  
Real hosted runs completed prediction, required tests and actual-result recording.
The outcome artifact was imported into persistent local history.

**24. What is the difference between session and CI history?**  
Session history lasts for one browser session. CI outcomes are stored in SQLite
and can be refreshed by importing completed workflow artifacts.

**25. Why does the live deployment need more evaluation?**  
It uses a bounded API history window and records a test-job outcome, while training
used workflow-run labels. New repositories and these semantic shifts need new data.

**26. What would you improve next?**  
Verified source provenance, real file histories, consistent target labels,
calibration, alert-budget studies, grouped/cross-repository validation and a new
untouched future period. The existing test set must not be reused for tuning.
