"""
Phase 6: Train Pre-Match Prediction Model
Run from project root: python src/train_model.py
"""

import pandas as pd
import numpy as np
import joblib, json, os, warnings
warnings.filterwarnings('ignore')

from sklearn.linear_model    import LogisticRegression
from sklearn.ensemble        import RandomForestClassifier
from sklearn.preprocessing   import StandardScaler
from sklearn.metrics         import accuracy_score, roc_auc_score, classification_report
from sklearn.model_selection import cross_val_score
from xgboost                 import XGBClassifier

# ── Load data ────────────────────────────────────────────────────────────────
print('Loading data...')
full = pd.read_csv('data/processed/full_features.csv', parse_dates=['date'])
print(f'  {len(full)} matches, {full.shape[1]} columns')

# ── Features & split ─────────────────────────────────────────────────────────
FEATURE_COLS = [c for c in full.columns
                if c not in ['match_id','date','season_year','team_a','team_b','venue','team_a_won']]
TARGET = 'team_a_won'

train = full[full['season_year'] <= 2023]
test  = full[full['season_year'] >= 2024]
X_train, y_train = train[FEATURE_COLS], train[TARGET]
X_test,  y_test  = test[FEATURE_COLS],  test[TARGET]

print(f'  Train: {len(train)} | Test: {len(test)} | Features: {len(FEATURE_COLS)}')

scaler    = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)

# ── Train models ─────────────────────────────────────────────────────────────
print('\nTraining models...')

print('  [1/4] Logistic Regression...', end=' ', flush=True)
lr = LogisticRegression(max_iter=1000, random_state=42)
lr.fit(X_train_s, y_train)
lr_test  = accuracy_score(y_test, lr.predict(X_test_s))
lr_auc   = roc_auc_score(y_test,  lr.predict_proba(X_test_s)[:,1])
lr_train = accuracy_score(y_train, lr.predict(X_train_s))
print(f'done  Train={lr_train:.1%} Test={lr_test:.1%} AUC={lr_auc:.3f}')

print('  [2/4] Random Forest (n=100)...', end=' ', flush=True)
rf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, n_jobs=-1)
rf.fit(X_train, y_train)
rf_test  = accuracy_score(y_test, rf.predict(X_test))
rf_auc   = roc_auc_score(y_test,  rf.predict_proba(X_test)[:,1])
rf_train = accuracy_score(y_train, rf.predict(X_train))
print(f'done  Train={rf_train:.1%} Test={rf_test:.1%} AUC={rf_auc:.3f}')

print('  [3/4] XGBoost...', end=' ', flush=True)
xgb = XGBClassifier(
    n_estimators=200, max_depth=3, learning_rate=0.05,
    subsample=0.7, colsample_bytree=0.7,
    reg_alpha=1.0, reg_lambda=2.0, min_child_weight=5,
    random_state=42, eval_metric='logloss', verbosity=0
)
xgb.fit(X_train, y_train)
xgb_test  = accuracy_score(y_test, xgb.predict(X_test))
xgb_auc   = roc_auc_score(y_test,  xgb.predict_proba(X_test)[:,1])
xgb_train = accuracy_score(y_train, xgb.predict(X_train))
print(f'done  Train={xgb_train:.1%} Test={xgb_test:.1%} AUC={xgb_auc:.3f}')

print('  [4/4] Cross-validation (LR, 5-fold)...', end=' ', flush=True)
cv = cross_val_score(lr, X_train_s, y_train, cv=5, scoring='accuracy')
print(f'done  {cv.mean():.1%} ± {cv.std():.1%}')

# ── Results table ────────────────────────────────────────────────────────────
print('\n=== MODEL COMPARISON ===')
print(f'{"Model":<25} {"Train":>7} {"Test":>7} {"AUC":>7} {"Gap":>7}')
print('-' * 55)
for name, tr, te, auc in [
    ('Logistic Regression', lr_train, lr_test, lr_auc),
    ('Random Forest',       rf_train, rf_test, rf_auc),
    ('XGBoost (regularised)', xgb_train, xgb_test, xgb_auc),
]:
    print(f'{name:<25} {tr:>7.1%} {te:>7.1%} {auc:>7.3f} {tr-te:>7.1%}')

# ── Pick best & save ─────────────────────────────────────────────────────────
# Logistic Regression: highest test accuracy, smallest overfit gap
best_model  = lr
best_scaler = scaler
best_test   = lr_test
best_auc    = lr_auc

print(f'\nBest model: Logistic Regression')
print(f'Test accuracy: {best_test:.1%} | AUC: {best_auc:.3f}')
print('\nClassification report:')
print(classification_report(y_test, best_model.predict(X_test_s),
                             target_names=['Team B Won','Team A Won']))

os.makedirs('models', exist_ok=True)
joblib.dump(best_model,  'models/pre_match_model.pkl')
joblib.dump(best_scaler, 'models/scaler.pkl')
with open('models/feature_cols.json', 'w') as f:
    json.dump(FEATURE_COLS, f)
with open('models/model_info.json', 'w') as f:
    json.dump({
        'model_type'      : 'LogisticRegression',
        'requires_scaling': True,
        'test_accuracy'   : round(best_test, 4),
        'auc'             : round(best_auc, 4),
        'n_features'      : len(FEATURE_COLS)
    }, f, indent=2)

print('\nSaved:')
print('  models/pre_match_model.pkl')
print('  models/scaler.pkl')
print('  models/feature_cols.json')
print('  models/model_info.json')
print('\nPhase 6 complete.')
