# Synthetic demo inputs

feature_input.csv contains three invented feature rows for exercising the upload
and explanation flow. They are not research dataset rows or real commits, and
have no actual CI labels. Row 3 demonstrates missing historical information.
Use these inputs for a software demonstration, never as model evaluation evidence.
Risk levels are produced by the saved model and are not fixed expected labels.

The first 15 columns are the current saved feature contract. The remaining four
are optional observed-change flags for advice; they are not trained model inputs.
