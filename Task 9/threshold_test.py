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
X = train.drop(columns=['id','sleep_stage']).values
y = train['sleep_stage'].values

pipe = Pipeline([('imp', IterativeImputer(max_iter=10, random_state=0)), ('scl', StandardScaler()), ('clf', SVC(C=8.5, gamma=0.014, kernel='rbf', probability=True, random_state=0))])

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
oof_proba = np.zeros((len(y), 4))
for fold, (tr_idx, va_idx) in enumerate(skf.split(X, y)):
    m = clone(pipe)
    m.fit(X[tr_idx], y[tr_idx])
    oof_proba[va_idx] = m.predict_proba(X[va_idx])
    print(f'Fold {fold+1} done')

oof_preds = np.argmax(oof_proba, axis=1)
print(f'Default OOF F1: {f1_score(y, oof_preds, average="macro"):.5f}')
print('Per-class F1:', f1_score(y, oof_preds, average=None))
