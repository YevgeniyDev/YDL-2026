import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.metrics import f1_score
from sklearn.svm import SVC
from sklearn.ensemble import HistGradientBoostingClassifier, VotingClassifier
from sklearn.base import clone

train = pd.read_csv("train.csv")
test  = pd.read_csv("test.csv")
print("train:", train.shape, "| test:", test.shape)

def engineer(df):
    df = df.copy()
    df["eog_burst_missing"] = df["eog_burst_index"].isna().astype(int)
    df["theta_delta_ratio"] = df["eeg_theta_power"] / (df["eeg_delta_power"].abs() + 1e-6)
    df["alpha_beta_ratio"]  = df["eeg_alpha_power"]  / (df["eeg_beta_power"].abs()  + 1e-6)
    df["delta_beta_ratio"]  = df["eeg_delta_power"]  / (df["eeg_beta_power"].abs()  + 1e-6)
    df["eeg_total_power"]   = (df["eeg_delta_power"] + df["eeg_theta_power"] +
                                df["eeg_alpha_power"] + df["eeg_sigma_power"] +
                                df["eeg_beta_power"]  + df["eeg_gamma_power"])
    return df

train_fe = engineer(train)
test_fe  = engineer(test)
ALL_FEATURES = [c for c in train_fe.columns if c not in ("id", "sleep_stage")]
print("Features:", len(ALL_FEATURES))

X      = train_fe[ALL_FEATURES]
y      = train["sleep_stage"]
X_test = test_fe[ALL_FEATURES]

svc_pipe = Pipeline([
    ("imputer", IterativeImputer(random_state=0, max_iter=10)),
    ("scaler",  StandardScaler()),
    ("svc",     SVC(C=7, gamma=0.015, kernel="rbf", probability=True, random_state=42)),
])

hgb = HistGradientBoostingClassifier(
    max_iter=500, learning_rate=0.04, max_depth=5,
    min_samples_leaf=15, l2_regularization=0.2,
    random_state=42, class_weight="balanced",
)

model = VotingClassifier(
    estimators=[("svc", svc_pipe), ("hgb", hgb)],
    voting="soft", weights=[3, 2], n_jobs=1,
)

cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=0)
scores = []
for tr_idx, va_idx in cv.split(X, y):
    m = clone(model)
    m.fit(X.iloc[tr_idx], y.iloc[tr_idx])
    pred = m.predict(X.iloc[va_idx])
    scores.append(f1_score(y.iloc[va_idx], pred, average="macro"))
print(f"CV macro-F1: {np.mean(scores):.4f} +/- {np.std(scores):.4f}")

model.fit(X, y)
pred = model.predict(X_test)
print("Prediction distribution:", np.bincount(pred))

submission = pd.DataFrame({"id": test["id"], "sleep_stage": pred})
submission.to_csv("submission_2.csv", index=False)
print("Wrote submission_2.csv", submission.shape)
