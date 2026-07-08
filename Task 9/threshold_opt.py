import warnings; warnings.filterwarnings('ignore')
import pandas as pd, numpy as np
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import f1_score
from sklearn.base import clone

train = pd.read_csv('train.csv')
test = pd.read_csv('test.csv')
FEATS = [c for c in train.columns if c not in ['id','sleep_stage']]
X = train[FEATS].values
y = train['sleep_stage'].values
X_test = test[FEATS].values

pipe = Pipeline([('imp', IterativeImputer(max_iter=10, random_state=0)), ('scl', StandardScaler()), ('clf', SVC(C=8.5, gamma=0.014, kernel='rbf', probability=True, random_state=0))])

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
oof_proba = np.zeros((len(y), 4))
for fold, (tr_idx, va_idx) in enumerate(skf.split(X, y)):
    m = clone(pipe)
    m.fit(X[tr_idx], y[tr_idx])
    oof_proba[va_idx] = m.predict_proba(X[va_idx])
    print(f'Fold {fold+1} done')

# Default
oof_preds = np.argmax(oof_proba, axis=1)
print(f'Default OOF F1: {f1_score(y, oof_preds, average="macro"):.5f}')
print('Per-class:', f1_score(y, oof_preds, average=None))

# Try scaling probabilities for each class (effectively threshold adjustment)
best_f1 = 0
best_weights = None
for w0 in [0.9, 1.0, 1.1]:
    for w1 in [0.9, 1.0, 1.1]:
        for w2 in [1.0, 1.1, 1.2, 1.3]:
            for w3 in [0.9, 1.0, 1.1]:
                weights = np.array([w0, w1, w2, w3])
                preds = np.argmax(oof_proba * weights, axis=1)
                f1 = f1_score(y, preds, average="macro")
                if f1 > best_f1:
                    best_f1 = f1
                    best_weights = weights

print(f'Best threshold-adjusted OOF F1: {best_f1:.5f}')
print('Best weights:', best_weights)
if best_weights is not None:
    preds = np.argmax(oof_proba * best_weights, axis=1)
    print('Per-class:', f1_score(y, preds, average=None))
