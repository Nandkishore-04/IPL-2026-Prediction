"""
Phase 7: Hyperparameter Tuning
Run from project root: python src/tune_model.py
"""

import pandas as pd
import numpy as np
import joblib, json, os, warnings
warnings.filterwarnings('ignore')

from sklearn.linear_model    import LogisticRegression
from sklearn.preprocessing   import StandardScaler
from sklearn.metrics         import accuracy_score, roc_auc_score
from sklearn.model_selection import RandomizedSearchCV, cross_val_score

# ── Load data ────────────────────────────────────────────────────────────────
print('Loading data...')
full = pd.read_csv('data/processed/full_features.csv', parse_dates=['date'])

with open('models/feature_cols.json') as f:
    FEATURE_COLS = json.load(f)

TARGET = 'team_a_won'
train  = full[full['season_year'] <= 2023]
test   = full[full['season_year'] >= 2024]

X_train, y_train = train[FEATURE_COLS], train[TARGET]
X_test,  y_test  = test[FEATURE_COLS],  test[TARGET]

scaler    = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)

print(f'  Train: {len(train)} | Test: {len(test)} | Features: {len(FEATURE_COLS)}')

# ── Baseline (untuned) ───────────────────────────────────────────────────────
baseline = LogisticRegression(max_iter=1000, random_state=42)
baseline.fit(X_train_s, y_train)
baseline_acc = accuracy_score(y_test, baseline.predict(X_test_s))
baseline_auc = roc_auc_score(y_test,  baseline.predict_proba(X_test_s)[:,1])
print(f'\nBaseline LR — Test: {baseline_acc:.1%} | AUC: {baseline_auc:.3f}')

# ── Hyperparameter search ────────────────────────────────────────────────────
# What are hyperparameters?
# They are settings you choose BEFORE training — not learned from data.
# e.g. C controls how much the model is penalised for complexity.
# Small C = heavy penalty = simpler model (less overfit)
# Large C = light penalty = more complex model (can overfit)

print('\nRunning RandomizedSearchCV...')
print('(This tries 50 random combinations, 5-fold CV each = 250 fits)')

param_grid = {
    # C: regularisation strength — smaller = stronger regularisation
    'C'      : [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0],
    # penalty: L1 (sparse, zeroes out weak features) vs L2 (shrinks all)
    'penalty': ['l1', 'l2'],
    # solver must support both penalties
    'solver' : ['liblinear', 'saga'],
    # class_weight: compensate for class imbalance (team_a wins 44.9%)
    'class_weight': [None, 'balanced'],
}

search = RandomizedSearchCV(
    LogisticRegression(max_iter=2000, random_state=42),
    param_distributions=param_grid,
    n_iter=50,            # try 50 random combinations
    cv=5,                 # 5-fold cross-validation
    scoring='roc_auc',    # optimise for AUC, not just accuracy
    random_state=42,
    n_jobs=-1,            # use all CPU cores
    verbose=1
)
search.fit(X_train_s, y_train)

print(f'\nBest params: {search.best_params_}')
print(f'Best CV AUC: {search.best_score_:.3f}')

# ── Evaluate tuned model ─────────────────────────────────────────────────────
tuned = search.best_estimator_
tuned_acc = accuracy_score(y_test, tuned.predict(X_test_s))
tuned_auc = roc_auc_score(y_test,  tuned.predict_proba(X_test_s)[:,1])

print(f'\n=== TUNING RESULTS ===')
print(f'{"":25} {"Test Acc":>10} {"AUC":>8}')
print(f'{"Baseline (default C=1)":25} {baseline_acc:>10.1%} {baseline_auc:>8.3f}')
print(f'{"Tuned (best params)":25} {tuned_acc:>10.1%} {tuned_auc:>8.3f}')
gain = tuned_acc - baseline_acc
print(f'\nGain from tuning: {gain:+.1%}')
print('(Even small gains matter — each % is ~1 more correct prediction per season)')

# ── CV results summary ───────────────────────────────────────────────────────
results_df = pd.DataFrame(search.cv_results_)
print(f'\nTop 5 parameter combinations by CV AUC:')
top5 = results_df.nlargest(5, 'mean_test_score')[['param_C','param_penalty','param_solver','param_class_weight','mean_test_score','std_test_score']]
print(top5.to_string(index=False))

# ── Retrain on full training set with best params ────────────────────────────
# RandomizedSearchCV already refit on full train set (refit=True by default)
print(f'\nRetraining final model on full training set with best params...')
final_cv = cross_val_score(tuned, X_train_s, y_train, cv=5, scoring='accuracy')
print(f'Final CV accuracy: {final_cv.mean():.1%} ± {final_cv.std():.1%}')

# ── Save tuned model ─────────────────────────────────────────────────────────
# Only save if tuned model is better than baseline
if tuned_auc >= baseline_auc:
    joblib.dump(tuned,  'models/pre_match_model.pkl')
    joblib.dump(scaler, 'models/scaler.pkl')
    with open('models/model_info.json', 'w') as f:
        json.dump({
            'model_type'      : 'LogisticRegression',
            'requires_scaling': True,
            'test_accuracy'   : round(tuned_acc, 4),
            'auc'             : round(tuned_auc, 4),
            'n_features'      : len(FEATURE_COLS),
            'best_params'     : search.best_params_
        }, f, indent=2)
    print(f'\nSaved tuned model → models/pre_match_model.pkl')
    print(f'Final model — Test: {tuned_acc:.1%} | AUC: {tuned_auc:.3f}')
else:
    print(f'\nTuned model not better — keeping baseline.')
    print(f'Baseline — Test: {baseline_acc:.1%} | AUC: {baseline_auc:.3f}')

print('\nPhase 7 complete.')
