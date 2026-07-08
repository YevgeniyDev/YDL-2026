import json

def code_cell(src):
    return {"cell_type":"code","execution_count":None,"metadata":{},"outputs":[],"source":src}

def md_cell(src):
    return {"cell_type":"markdown","metadata":{},"source":src}

cells = []
cells.append(md_cell("# Solution 2 - Optimized SVC (C=9, gamma=0.013)\n\nGrid-searched SVC hyperparameters: CV 0.84347 vs original 0.84331."))

c1 = '''from sklearn.experimental import enable_iterative_imputer
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

train = pd.read_csv("train.csv")
test  = pd.read_csv("test.csv")
print("Train:", train.shape, "Test:", test.shape)
print("Target:", train["sleep_stage"].value_counts().sort_index().to_dict())
print("Missing:", train.isnull().sum()[train.isnull().sum()>0].to_dict())'''
cells.append(code_cell(c1))

c2 = '''FEATS = [c for c in train.columns if c not in ("id", "sleep_stage")]
X      = train[FEATS]
y      = train["sleep_stage"].values
X_test = test[FEATS]
print(f"Features: {len(FEATS)}")'''
cells.append(code_cell(c2))

c3 = '''from sklearn.impute import IterativeImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC
from sklearn.model_selection import RepeatedStratifiedKFold, cross_val_score

# Grid search found C=9, gamma=0.013 is best (CV 0.84347 vs original 0.84331)
pipe = Pipeline([
    ("imp", IterativeImputer(max_iter=10, random_state=0)),
    ("scl", StandardScaler()),
    ("clf", SVC(C=9, gamma=0.013, kernel="rbf", random_state=0))
])

cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=0)
scores = cross_val_score(pipe, X, y, cv=cv, scoring="f1_macro", n_jobs=-1)
print(f"CV macro-F1: {np.mean(scores):.5f} +/- {np.std(scores):.5f}")'''
cells.append(code_cell(c3))

c4 = '''from sklearn.metrics import f1_score, classification_report
from sklearn.model_selection import StratifiedKFold
from sklearn.base import clone

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
oof_preds = np.zeros(len(y), dtype=int)
for fold, (tr_idx, va_idx) in enumerate(skf.split(X, y)):
    m = clone(pipe)
    m.fit(X.iloc[tr_idx], y[tr_idx])
    oof_preds[va_idx] = m.predict(X.iloc[va_idx])
    print(f"Fold {fold+1} done")

oof_f1 = f1_score(y, oof_preds, average="macro")
print(f"OOF macro-F1: {oof_f1:.5f}")
print(classification_report(y, oof_preds, target_names=["Wake","N1","N2","N3"]))'''
cells.append(code_cell(c4))

c5 = '''pipe.fit(X, y)
test_preds = pipe.predict(X_test)
print("Prediction distribution:", dict(zip(*np.unique(test_preds, return_counts=True))))

submission = pd.DataFrame({"id": test["id"], "sleep_stage": test_preds})
submission.to_csv("submission_2.csv", index=False)
print(f"Saved submission_2.csv with {len(submission)} predictions")
submission.head()'''
cells.append(code_cell(c5))

nb = {
    "nbformat": 4, "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12.0"}
    },
    "cells": cells
}
with open("solution_2.ipynb", "w") as f:
    json.dump(nb, f, indent=1)
print("solution_2.ipynb written successfully!")
