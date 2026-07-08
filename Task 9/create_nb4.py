import json


def code_cell(src):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": src,
    }


def md_cell(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src}


cells = []

cells.append(md_cell("""# Solution 4 - CV-searched RBF SVC

This notebook keeps the strongest observed setup from `solution.ipynb`:

`IterativeImputer -> StandardScaler -> RBF SVC`

The final `C` and `gamma` were selected by a focused search, not by copying a
single submitted value. The search used the same full preprocessing/model
pipeline and `RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=0)`.

Best local repeated-CV result found:

`C=7.90`, `gamma=0.014`, CV macro-F1 `0.84385 +/- 0.00826`.

Known public scores are kept below as reference, but the notebook default is the
best value found by the local validation search."""))

c1 = '''import warnings
warnings.filterwarnings("ignore")

from sklearn.experimental import enable_iterative_imputer

import pandas as pd
import numpy as np

train = pd.read_csv("train.csv")
test = pd.read_csv("test.csv")
sample_submission = pd.read_csv("sample_submission.csv")

print(f"Train: {train.shape}, Test: {test.shape}")
print("Target distribution:", train["sleep_stage"].value_counts().sort_index().to_dict())
print("Missing values:", train.isnull().sum()[train.isnull().sum() > 0].to_dict())'''
cells.append(code_cell(c1))

c2 = '''FEATURES = [c for c in train.columns if c not in ("id", "sleep_stage")]

X = train[FEATURES].values
y = train["sleep_stage"].values
X_test = test[FEATURES].values

print(f"Features: {len(FEATURES)}")
print(FEATURES)'''
cells.append(code_cell(c2))

c3 = '''# Evidence from the focused tuning round.
# local_cv_mean/local_cv_std were measured with the same full pipeline and
# RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=0).
# public_score values are known submission results, included only as reference.
evidence = pd.DataFrame([
    {"C": 7.90, "gamma": 0.01400, "public_score": np.nan, "local_cv_mean": 0.84385, "local_cv_std": 0.00826},
    {"C": 7.80, "gamma": 0.01400, "public_score": np.nan, "local_cv_mean": 0.84384, "local_cv_std": 0.00839},
    {"C": 7.90, "gamma": 0.01425, "public_score": np.nan, "local_cv_mean": 0.84383, "local_cv_std": 0.00847},
    {"C": 8.00, "gamma": 0.01400, "public_score": np.nan, "local_cv_mean": 0.84381, "local_cv_std": 0.00823},
    {"C": 7.40, "gamma": 0.01475, "public_score": np.nan, "local_cv_mean": 0.84379, "local_cv_std": 0.00865},
    {"C": 7.80, "gamma": 0.01425, "public_score": np.nan, "local_cv_mean": 0.84379, "local_cv_std": 0.00821},
    {"C": 7.60, "gamma": 0.01425, "public_score": np.nan, "local_cv_mean": 0.84376, "local_cv_std": 0.00837},
    {"C": 8.40, "gamma": 0.01375, "public_score": np.nan, "local_cv_mean": 0.84375, "local_cv_std": 0.00792},
    {"C": 8.60, "gamma": 0.01375, "public_score": np.nan, "local_cv_mean": 0.84372, "local_cv_std": 0.00815},
    {"C": 8.00, "gamma": 0.01425, "public_score": np.nan, "local_cv_mean": 0.84372, "local_cv_std": 0.00827},
    {"C": 8.50, "gamma": 0.01400, "public_score": 0.85326, "local_cv_mean": 0.84359, "local_cv_std": 0.00814},
    {"C": 9.00, "gamma": 0.01300, "public_score": 0.85322, "local_cv_mean": 0.84347, "local_cv_std": 0.00775},
    {"C": 8.85, "gamma": 0.01200, "public_score": 0.85718, "local_cv_mean": 0.84247, "local_cv_std": 0.00871},
    {"C": 8.75, "gamma": 0.01200, "public_score": 0.85655, "local_cv_mean": 0.84240, "local_cv_std": 0.00877},
])

evidence.sort_values(
    ["local_cv_mean", "public_score"],
    ascending=[False, False],
    na_position="last",
).reset_index(drop=True)'''
cells.append(code_cell(c3))

c4 = '''from sklearn.impute import IterativeImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC
from sklearn.model_selection import RepeatedStratifiedKFold, cross_val_score

BEST_C = 7.90
BEST_GAMMA = 0.014

pipe = Pipeline([
    ("imp", IterativeImputer(max_iter=10, random_state=0)),
    ("scl", StandardScaler()),
    ("clf", SVC(C=BEST_C, gamma=BEST_GAMMA, kernel="rbf", random_state=0)),
])

print(pipe)

# Set to True only when you want to recompute the full 5x3 CV in this notebook.
RUN_FULL_CV = False
if RUN_FULL_CV:
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=0)
    scores = cross_val_score(pipe, X, y, cv=cv, scoring="f1_macro", n_jobs=-1)
    print(f"Repeated CV macro-F1: {np.mean(scores):.5f} +/- {np.std(scores):.5f}")
else:
    print("Using BEST_C=7.90 and BEST_GAMMA=0.014 from the focused repeated-CV search: 0.84385 +/- 0.00826")'''
cells.append(code_cell(c4))

c5 = '''from sklearn.base import clone
from sklearn.metrics import f1_score, classification_report
from sklearn.model_selection import StratifiedKFold

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
oof_preds = np.zeros(len(y), dtype=int)

for fold, (tr_idx, va_idx) in enumerate(skf.split(X, y), start=1):
    model = clone(pipe)
    model.fit(X[tr_idx], y[tr_idx])
    oof_preds[va_idx] = model.predict(X[va_idx])
    print(f"Fold {fold} done")

oof_f1 = f1_score(y, oof_preds, average="macro")
print(f"OOF macro-F1: {oof_f1:.5f}")
print(classification_report(y, oof_preds, target_names=["Wake", "N1", "N2", "N3"]))'''
cells.append(code_cell(c5))

c6 = '''pipe.fit(X, y)
test_preds = pipe.predict(X_test).astype(int)

submission = pd.DataFrame({
    "id": test["id"],
    "sleep_stage": test_preds,
})

assert list(submission.columns) == list(sample_submission.columns)
assert len(submission) == len(sample_submission)

print("Prediction distribution:", dict(zip(*np.unique(test_preds, return_counts=True))))
submission.to_csv("submission_4.csv", index=False)
print(f"Saved submission_4.csv with {len(submission)} predictions")
submission.head()'''
cells.append(code_cell(c6))

nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.12.0",
        },
    },
    "cells": cells,
}

with open("solution_4.ipynb", "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)

print("solution_4.ipynb written successfully!")
