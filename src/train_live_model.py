"""
Phase 9: Train Live Win Probability Model
Trains on ball-by-ball state snapshots from 2nd innings.
Run from project root: python src/train_live_model.py
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
live = pd.read_csv('data/processed/live_model_data.csv', parse_dates=['date'])
print(f'  {len(live):,} ball snapshots | {live["match_id"].nunique():,} matches')

LIVE_FEATURES = [
    'cum_runs', 'cum_wickets', 'cum_balls',
    'target', 'runs_remaining', 'balls_remaining', 'wickets_in_hand',
    'crr', 'rrr', 'run_rate_ratio',
    'venue_chase_wr', 'team_chase_wr',
    'last6_runs', 'last6_wickets',
    'dot_pct_last12', 'partnership_balls',
    'last18_wickets', 'pp_vs_avg',
]
TARGET = 'chasing_team_won'

# ── Time-based split (same logic as pre-match model) ─────────────────────────
# Extract season year from date for splitting
live['season_year'] = live['date'].dt.year
# Fix cross-year seasons: Jan-Apr belongs to the season that started previous year
# e.g. March 2021 = IPL 2021 (which started Apr 2021) — use April cutoff
live['season_year'] = live.apply(
    lambda r: r['season_year'] - 1 if r['date'].month < 4 else r['season_year'],
    axis=1
)

train = live[live['season_year'] <= 2023]
test  = live[live['season_year'] >= 2024]

X_train, y_train = train[LIVE_FEATURES], train[TARGET]
X_test,  y_test  = test[LIVE_FEATURES],  test[TARGET]

print(f'  Train: {len(train):,} snapshots ({train["season_year"].min()}–{train["season_year"].max()})')
print(f'  Test : {len(test):,} snapshots  ({test["season_year"].min()}–{test["season_year"].max()})')
print(f'  Features: {len(LIVE_FEATURES)}')
print(f'  Train chase win rate: {y_train.mean():.1%}')
print(f'  Test  chase win rate: {y_test.mean():.1%}')

scaler    = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)

# ── Train models ─────────────────────────────────────────────────────────────
print('\nTraining models...')

print('  [1/3] Logistic Regression...', end=' ', flush=True)
lr = LogisticRegression(max_iter=1000, random_state=42, class_weight='balanced')
lr.fit(X_train_s, y_train)
lr_test  = accuracy_score(y_test, lr.predict(X_test_s))
lr_auc   = roc_auc_score(y_test,  lr.predict_proba(X_test_s)[:,1])
lr_train = accuracy_score(y_train, lr.predict(X_train_s))
print(f'done  Train={lr_train:.1%} Test={lr_test:.1%} AUC={lr_auc:.3f}')

print('  [2/3] Random Forest (n=100)...', end=' ', flush=True)
rf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, n_jobs=-1)
rf.fit(X_train, y_train)
rf_test  = accuracy_score(y_test, rf.predict(X_test))
rf_auc   = roc_auc_score(y_test,  rf.predict_proba(X_test)[:,1])
rf_train = accuracy_score(y_train, rf.predict(X_train))
print(f'done  Train={rf_train:.1%} Test={rf_test:.1%} AUC={rf_auc:.3f}')

print('  [3/3] XGBoost (regularised)...', end=' ', flush=True)
xgb = XGBClassifier(
    n_estimators=200, max_depth=4, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8,
    reg_alpha=0.5, reg_lambda=1.0, min_child_weight=10,
    random_state=42, eval_metric='logloss', verbosity=0
)
xgb.fit(X_train, y_train)
xgb_test  = accuracy_score(y_test, xgb.predict(X_test))
xgb_auc   = roc_auc_score(y_test,  xgb.predict_proba(X_test)[:,1])
xgb_train = accuracy_score(y_train, xgb.predict(X_train))
print(f'done  Train={xgb_train:.1%} Test={xgb_test:.1%} AUC={xgb_auc:.3f}')

# ── Results table ────────────────────────────────────────────────────────────
print('\n=== LIVE MODEL COMPARISON ===')
print(f'{"Model":<28} {"Train":>7} {"Test":>7} {"AUC":>7} {"Gap":>7}')
print('-' * 58)
for name, tr, te, auc in [
    ('Logistic Regression',    lr_train,  lr_test,  lr_auc),
    ('Random Forest',          rf_train,  rf_test,  rf_auc),
    ('XGBoost (regularised)',  xgb_train, xgb_test, xgb_auc),
]:
    print(f'{name:<28} {tr:>7.1%} {te:>7.1%} {auc:>7.3f} {tr-te:>7.1%}')

# ── Pick best model ───────────────────────────────────────────────────────────
# With 100k+ samples, XGBoost and RF can generalise — compare AUC
models = [
    ('Logistic Regression',   lr,  X_test_s, lr_test,  lr_auc),
    ('Random Forest',         rf,  X_test,   rf_test,  rf_auc),
    ('XGBoost (regularised)', xgb, X_test,   xgb_test, xgb_auc),
]
best_name, best_model, best_X_test, best_test, best_auc = max(models, key=lambda x: x[4])

print(f'\nBest model by AUC: {best_name}')
print(f'Test accuracy: {best_test:.1%} | AUC: {best_auc:.3f}')

# Detailed report for best model
if best_model is lr:
    y_pred = best_model.predict(X_test_s)
else:
    y_pred = best_model.predict(X_test)

print('\nClassification report:')
print(classification_report(y_test, y_pred, target_names=['Chasing Lost','Chasing Won']))

# Feature importance for logistic regression
print('\nFeature coefficients (Logistic Regression):')
coef_df = pd.DataFrame({
    'feature': LIVE_FEATURES,
    'coefficient': lr.coef_[0]
}).reindex(pd.Series(lr.coef_[0]).abs().sort_values(ascending=False).index)
print(coef_df.head(10).to_string(index=False))

# ── Save ─────────────────────────────────────────────────────────────────────
os.makedirs('models', exist_ok=True)

# Always save logistic regression for interpretable live predictor
# Also save best model if different
joblib.dump(lr,     'models/live_model_lr.pkl')
joblib.dump(scaler, 'models/live_scaler.pkl')

if best_model is not lr:
    joblib.dump(best_model, 'models/live_model_best.pkl')
    print(f'\nSaved best model ({best_name}) -> models/live_model_best.pkl')

# Save as primary live model (use best AUC)
if best_model is lr:
    joblib.dump(lr, 'models/live_model.pkl')
    primary_type = 'LogisticRegression'
    requires_scaling = True
elif best_model is rf:
    joblib.dump(rf, 'models/live_model.pkl')
    primary_type = 'RandomForest'
    requires_scaling = False
else:
    joblib.dump(xgb, 'models/live_model.pkl')
    primary_type = 'XGBoost'
    requires_scaling = False

with open('models/live_feature_cols.json', 'w') as f:
    json.dump(LIVE_FEATURES, f)

with open('models/live_model_info.json', 'w') as f:
    json.dump({
        'model_type'      : primary_type,
        'requires_scaling': requires_scaling,
        'test_accuracy'   : round(best_test, 4),
        'auc'             : round(best_auc, 4),
        'n_features'      : len(LIVE_FEATURES),
        'train_samples'   : len(train),
        'test_samples'    : len(test),
    }, f, indent=2)

print(f'\nSaved:')
print(f'  models/live_model.pkl         ({primary_type})')
print(f'  models/live_model_lr.pkl      (Logistic Regression — always saved)')
print(f'  models/live_scaler.pkl')
print(f'  models/live_feature_cols.json')
print(f'  models/live_model_info.json')
print(f'\nFinal live model — Test: {best_test:.1%} | AUC: {best_auc:.3f}')
print('\nPhase 9 complete.')
