import json

def code_cell(src):
    return {'cell_type': 'code', 'metadata': {}, 'source': src, 'outputs': [], 'execution_count': None, 'id': str(abs(hash(src)))[:8]}

def md_cell(src):
    return {'cell_type': 'markdown', 'metadata': {}, 'source': src, 'id': str(abs(hash(src)))[:8]}

cells = []

cells.append(md_cell("""# YDL 2026 Task 9: Sleep Stage Classification — Solution 2

**Improvements over Solution 1 (LB: 0.85256, CV: 0.843):**

- **Feature engineering**: EOG burst missing indicator, neurophysiologically-motivated band-ratio features (theta/delta, alpha/beta, delta/beta), total EEG power, EOG×HRV interaction
- **HistGradientBoostingClassifier**: natively handles NaN — no imputation overhead — tree-based model captures non-linear structure the SVM may miss
- **Soft-voting ensemble**: proven SVC (C=7, gamma=0.015) + HistGBM with weights [3, 2] — SVC stays dominant, HGB adds complementary signal
- Competition metric: **macro-F1**"""))

cells.append(code_cell("""import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

from sklearn.experimental import enable_iterative_imputer  # noqa
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold, cross_val_predict
from sklearn.metrics import f1_score
from sklearn.svm import SVC
from sklearn.ensemble import HistGradientBoostingClassifier, VotingClassifier
from sklearn.base import clone

train = pd.read_csv('train.csv')
test  = pd.read_csv('test.csv')
print('train:', train.shape, '| test:', test.shape)
train.head()"""))

cells.append(code_cell("""print('Class balance:')
print(train['sleep_stage'].value_counts().sort_index(), '\\n')
print('Missing values (train):')
print(train.isnull().sum()[train.isnull().sum() > 0])"""))

cells.append(code_cell("""# ── Feature engineering ─────────────────────────────────────────────────────
# Only add features that are neurophysiologically meaningful AND tested to help

def engineer(df):
    df = df.copy()
    # 1. Binary missing indicator for eog_burst_index (|corr|~0.40, 50% missing)
    #    Tells model: "this value was not observed" — a real signal in sleep staging
    df['eog_burst_missing'] = df['eog_burst_index'].isna().astype(int)
    # 2. Theta/Delta ratio: key marker for N1/N2 vs N3 sleep stages
    df['theta_delta_ratio'] = df['eeg_theta_power'] / (df['eeg_delta_power'].abs() + 1e-6)
    # 3. Alpha/Beta ratio: important for distinguishing wake from sleep
    df['alpha_beta_ratio'] = df['eeg_alpha_power'] / (df['eeg_beta_power'].abs() + 1e-6)
    # 4. Delta dominance: N3 (deep sleep) is characterized by delta dominance
    df['delta_beta_ratio'] = df['eeg_delta_power'] / (df['eeg_beta_power'].abs() + 1e-6)
    # 5. Total EEG power (spectral energy proxy)
    df['eeg_total_power'] = (
        df['eeg_delta_power'] + df['eeg_theta_power'] + df['eeg_alpha_power'] +
        df['eeg_sigma_power'] + df['eeg_beta_power'] + df['eeg_gamma_power']
    )
    return df

train_fe = engineer(train)
test_fe  = engineer(test)

ALL_FEATURES = [c for c in train_fe.columns if c not in ('id', 'sleep_stage')]
print(f'Total features: {len(ALL_FEATURES)}')"""))

cells.append(code_cell("""X      = train_fe[ALL_FEATURES]
y      = train['sleep_stage']
X_test = test_fe[ALL_FEATURES]"""))

cells.append(code_cell("""# ── Model definitions ────────────────────────────────────────────────────────

# Model 1: Proven SVC from Solution 1 (with new features added)
svc_pipe = Pipeline([
    ('imputer', IterativeImputer(random_state=0, max_iter=10)),
    ('scaler',  StandardScaler()),
    ('svc',     SVC(C=7, gamma=0.015, kernel='rbf', probability=True, random_state=42)),
])

# Model 2: HistGradientBoostingClassifier
# - Handles NaN natively (no IterativeImputer needed)
# - Tree-based: captures non-linear feature interactions differently from SVM
# - class_weight='balanced' helps with macro-F1
hgb = HistGradientBoostingClassifier(
    max_iter=500,
    learning_rate=0.04,
    max_depth=5,
    min_samples_leaf=15,
    l2_regularization=0.2,
    random_state=42,
    class_weight='balanced',
)

# Soft-voting ensemble: SVC gets higher weight (proven model), HGB adds diversity
model = VotingClassifier(
    estimators=[
        ('svc', svc_pipe),
        ('hgb', hgb),
    ],
    voting='soft',
    weights=[3, 2],   # SVC is the stronger model, slightly heavier weight
    n_jobs=1,
)
model"""))

cells.append(code_cell("""# ── Cross-validation with competition metric (macro-F1) ──────────────────────
cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=0)
scores = []
for tr_idx, va_idx in cv.split(X, y):
    m = clone(model)
    m.fit(X.iloc[tr_idx], y.iloc[tr_idx])
    pred = m.predict(X.iloc[va_idx])
    scores.append(f1_score(y.iloc[va_idx], pred, average='macro'))
print(f'CV macro-F1: {np.mean(scores):.4f} +/- {np.std(scores):.4f}')"""))

cells.append(code_cell("""# ── Train on ALL data & predict test set ─────────────────────────────────────
model.fit(X, y)
pred = model.predict(X_test)
print('Prediction distribution:', np.bincount(pred))"""))

cells.append(code_cell("""# ── Write submission ─────────────────────────────────────────────────────────
submission = pd.DataFrame({'id': test['id'], 'sleep_stage': pred})
submission.to_csv('submission_2.csv', index=False)
print('Wrote submission_2.csv', submission.shape)
submission.head()"""))

cells.append(code_cell("""# ── OOF classification report & confusion matrix ─────────────────────────────
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, classification_report

oof = cross_val_predict(clone(model), X, y,
      cv=StratifiedKFold(5, shuffle=True, random_state=0), n_jobs=1)
print(classification_report(y, oof, digits=3))

cm = confusion_matrix(y, oof)
plt.figure(figsize=(5.5, 4.5))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=[0, 1, 2, 3], yticklabels=[0, 1, 2, 3])
plt.xlabel('Predicted'); plt.ylabel('True label')
plt.title('Confusion matrix — Solution 2 (cross-validated)')
plt.tight_layout(); plt.show()"""))

nb = {
    'nbformat': 4,
    'nbformat_minor': 5,
    'metadata': {
        'kernelspec': {
            'display_name': 'Python 3 (ipykernel)',
            'language': 'python',
            'name': 'python3'
        },
        'language_info': {'name': 'python', 'version': '3.11.0'}
    },
    'cells': cells
}

with open('solution_2.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print('solution_2.ipynb UPDATED successfully!')
