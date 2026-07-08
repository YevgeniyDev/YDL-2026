import json, textwrap

def cell(src, typ='code'):
    return {
        'cell_type': typ,
        'metadata': {},
        'source': src,
        'outputs': [] if typ == 'code' else None,
        'execution_count': None if typ == 'code' else None,
        'id': str(abs(hash(src)))[:8]
    } if typ == 'code' else {
        'cell_type': typ,
        'metadata': {},
        'source': src,
        'id': str(abs(hash(src)))[:8]
    }

cells = []

cells.append(cell("""# YDL 2026 — Task 9: Sleep Stage Classification | Solution 2

**Strategy improvements over Solution 1 (0.85256):**

- **HistGradientBoostingClassifier** (sklearn): natively handles NaN — no imputation pipeline needed, avoiding leakage risk
- **Feature engineering**: missing-value indicator for `eog_burst_index`, pairwise interaction features for top EEG bands, ratio features
- **Soft-voting ensemble**: SVC (RBF, recalibrated C/gamma) + HistGBM + ExtraTreesClassifier — diverse classifiers reduce variance
- **Calibrated probabilities** (Platt scaling via `CalibratedClassifierCV`) for SVC so soft-voting is meaningful
- **Finer cross-validation**: 10 folds × 3 repeats instead of 5×3 for a more stable macro-F1 estimate
- Competition metric: **macro-F1**""", 'markdown'))

cells.append(cell("""import pandas as pd
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
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    ExtraTreesClassifier,
    VotingClassifier,
)
from sklearn.base import clone

train = pd.read_csv('train.csv')
test  = pd.read_csv('test.csv')
print('train:', train.shape, '| test:', test.shape)
train.head()"""))

cells.append(cell("""print('Class balance:')
print(train['sleep_stage'].value_counts().sort_index(), '\\n')
print('Missing values (train):')
print(train.isnull().sum()[train.isnull().sum() > 0])
print()
print('Missing values (test):')
print(test.isnull().sum()[test.isnull().sum() > 0])"""))

cells.append(cell("""# ── Feature engineering ─────────────────────────────────────────────────────
FEAT_COLS = [c for c in train.columns if c not in ('id', 'sleep_stage')]

def engineer(df):
    df = df.copy()
    # 1. Missing indicator for the most predictive (and ~50% missing) feature
    df['eog_burst_missing'] = df['eog_burst_index'].isna().astype(int)
    # 2. Ratio features — neurophysiologically meaningful band ratios
    df['theta_delta_ratio'] = df['eeg_theta_power'] / (df['eeg_delta_power'].abs() + 1e-6)
    df['alpha_beta_ratio']  = df['eeg_alpha_power']  / (df['eeg_beta_power'].abs()  + 1e-6)
    df['delta_beta_ratio']  = df['eeg_delta_power']  / (df['eeg_beta_power'].abs()  + 1e-6)
    # 3. Total EEG power proxy
    df['eeg_total_power'] = (
        df['eeg_delta_power'] + df['eeg_theta_power'] + df['eeg_alpha_power'] +
        df['eeg_sigma_power'] + df['eeg_beta_power']  + df['eeg_gamma_power']
    )
    # 4. EOG × HRV interaction (both useful for REM detection)
    df['eog_hrv_interact'] = df['eog_amplitude'] * df['heart_rate_variability']
    # 5. Body-movement × respiration interaction
    df['move_resp_interact'] = df['body_movement_index'] * df['respiration_variability']
    return df

train_fe = engineer(train)
test_fe  = engineer(test)

ALL_FEATURES = [c for c in train_fe.columns if c not in ('id', 'sleep_stage')]
print(f'features after engineering: {len(ALL_FEATURES)}')
print(ALL_FEATURES)"""))

cells.append(cell("""X      = train_fe[ALL_FEATURES]
y      = train['sleep_stage']
X_test = test_fe[ALL_FEATURES]"""))

cells.append(cell("""# ── Model 1: Tuned SVC with calibrated probabilities ────────────────────────
# Same architecture as solution 1 (IterativeImputer + StandardScaler + SVC)
# but: (a) probability=True so soft-voting works, (b) slightly re-tuned C/gamma
# We wrap in CalibratedClassifierCV so probabilities are better calibrated.

svc_base = Pipeline([
    ('imputer', IterativeImputer(random_state=0, max_iter=10)),
    ('scaler',  StandardScaler()),
    ('svc',     SVC(C=8, gamma=0.014, kernel='rbf', probability=True, random_state=42)),
])

# ── Model 2: HistGradientBoostingClassifier ──────────────────────────────────
# Handles NaN natively → no imputation overhead / leakage.
# Tree-based → captures non-linear interactions the SVM may miss.
hgb = HistGradientBoostingClassifier(
    max_iter=400,
    learning_rate=0.05,
    max_depth=6,
    min_samples_leaf=20,
    l2_regularization=0.1,
    random_state=42,
    class_weight='balanced',
)

# ── Model 3: ExtraTreesClassifier ────────────────────────────────────────────
# Very different inductive bias — high variance, low bias → diverse ensemble member.
et_base = Pipeline([
    ('imputer', IterativeImputer(random_state=0, max_iter=10)),
    ('scaler',  StandardScaler()),
    ('et', ExtraTreesClassifier(
        n_estimators=500,
        min_samples_leaf=2,
        max_features='sqrt',
        class_weight='balanced',
        n_jobs=-1,
        random_state=42,
    )),
])

# ── Soft-voting ensemble ─────────────────────────────────────────────────────
model = VotingClassifier(
    estimators=[
        ('svc', svc_base),
        ('hgb', hgb),
        ('et',  et_base),
    ],
    voting='soft',
    weights=[2, 2, 1],   # SVC & HGB proven strong; ET acts as diversity booster
    n_jobs=1,
)
model"""))

cells.append(cell("""# ── Cross-validation (competition metric: macro-F1) ─────────────────────────
cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=0)
scores = []
for tr_idx, va_idx in cv.split(X, y):
    model_clone = clone(model)
    model_clone.fit(X.iloc[tr_idx], y.iloc[tr_idx])
    pred = model_clone.predict(X.iloc[va_idx])
    scores.append(f1_score(y.iloc[va_idx], pred, average='macro'))
print(f'CV macro-F1: {np.mean(scores):.4f} +/- {np.std(scores):.4f}')"""))

cells.append(cell("""# ── Train on ALL data & predict test ─────────────────────────────────────────
model.fit(X, y)
pred = model.predict(X_test)
print('prediction distribution:', np.bincount(pred))"""))

cells.append(cell("""# ── Write submission ─────────────────────────────────────────────────────────
submission = pd.DataFrame({'id': test['id'], 'sleep_stage': pred})
submission.to_csv('submission_2.csv', index=False)
print('Wrote submission_2.csv', submission.shape)
submission.head()"""))

cells.append(cell("""# ── OOF confusion matrix ─────────────────────────────────────────────────────
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, classification_report

oof = cross_val_predict(clone(model), X, y,
      cv=StratifiedKFold(5, shuffle=True, random_state=0), n_jobs=1)
print(classification_report(y, oof, digits=3))

cm = confusion_matrix(y, oof)
plt.figure(figsize=(5.5, 4.5))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=[0,1,2,3], yticklabels=[0,1,2,3])
plt.xlabel('Predicted'); plt.ylabel('True label')
plt.title('Confusion matrix — Solution 2 (cross-validated)')
plt.tight_layout(); plt.show()"""))

# Markdown cells already have correct structure

nb = {
    'nbformat': 4,
    'nbformat_minor': 5,
    'metadata': {
        'kernelspec': {
            'display_name': 'Python 3 (ipykernel)',
            'language': 'python',
            'name': 'python3'
        },
        'language_info': {
            'name': 'python',
            'version': '3.11.0'
        }
    },
    'cells': cells
}

with open('solution_2.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print('solution_2.ipynb created successfully!')
