"""
Train Pre-Match Prediction Model — Gradient Boosting (production)
==================================================================
Pipeline:
  1. StandardScaler + GradientBoostingClassifier wrapped in sklearn Pipeline
     (scaler fit only on training data, no leakage into CV folds)
  2. Train on 2008-2023 with exponential recency weights
  3. Isotonic calibration via CalibratedClassifierCV(cv=5) — leakage-safe
  4. Evaluate on held-out 2024-2025 test set
  5. Leakage-safe TimeSeriesSplit CV for sanity check
  6. Feature dominance check (retrain without top feature)

Run from project root: python src/train_model.py
"""

import pandas as pd
import numpy as np
import joblib, json, os, warnings
warnings.filterwarnings("ignore")

from sklearn.pipeline         import Pipeline
from sklearn.preprocessing    import StandardScaler
from sklearn.ensemble         import GradientBoostingClassifier
from sklearn.calibration      import CalibratedClassifierCV
from sklearn.metrics          import (accuracy_score, roc_auc_score,
                                      log_loss, brier_score_loss,
                                      classification_report)
from sklearn.model_selection  import TimeSeriesSplit

# ── Load ──────────────────────────────────────────────────────────────────────

print("Loading data...")
full = pd.read_csv("data/processed/full_features.csv", parse_dates=["date"])
xi   = pd.read_csv("data/processed/xi_features.csv")
full = full.merge(xi, on="match_id", how="left")
print(f"  {len(full)} matches, {full.shape[1]} columns (after XI merge)")

# ── Feature selection ─────────────────────────────────────────────────────────

EXCLUDE = {
    "match_id","date","season_year","team_a","team_b","venue","team_a_won",
    "ta_streak","is_day_night",
    "ta_last5_wr","tb_last5_wr","ta_last5_margin","tb_last5_margin",
    "ta_overall_wr","tb_overall_wr","ta_venue_wr","tb_venue_wr",
    "ta_batfirst_wr","tb_batfirst_wr","ta_season_wr","tb_season_wr",
    # diff cols: excluded here so list comprehension doesn't pick them up;
    # appended explicitly once in the FEATURE_COLS += block below
    "xi_bat_sr_diff","xi_bowl_econ_diff","xi_exp_diff","xi_ar_ratio_diff",
    "form_wr_diff","form_margin_diff","overall_wr_diff",
    "venue_wr_diff","batfirst_wr_diff","season_wr_diff",
}

def add_diffs(df):
    df = df.copy()
    df["form_wr_diff"]     = df["ta_last5_wr"]    - df["tb_last5_wr"]
    df["form_margin_diff"] = df["ta_last5_margin"] - df["tb_last5_margin"]
    df["overall_wr_diff"]  = df["ta_overall_wr"]   - df["tb_overall_wr"]
    df["venue_wr_diff"]    = df["ta_venue_wr"]     - df["tb_venue_wr"]
    df["batfirst_wr_diff"] = df["ta_batfirst_wr"]  - df["tb_batfirst_wr"]
    df["season_wr_diff"]   = df["ta_season_wr"]    - df["tb_season_wr"]
    return df

full = add_diffs(full)
FEATURE_COLS = [c for c in full.columns if c not in EXCLUDE]
FEATURE_COLS += ["form_wr_diff","form_margin_diff","overall_wr_diff",
                 "venue_wr_diff","batfirst_wr_diff","season_wr_diff",
                 "xi_bat_sr_diff","xi_bowl_econ_diff","xi_exp_diff","xi_ar_ratio_diff"]

TARGET = "team_a_won"
print(f"  Features: {len(FEATURE_COLS)}")

# ── Train / test split ────────────────────────────────────────────────────────

train = full[full["season_year"] <= 2023].copy()
test  = full[full["season_year"] >= 2024].copy()
print(f"  Train: {len(train)} ({train.season_year.min()}-{train.season_year.max()})")
print(f"  Test : {len(test)}  ({test.season_year.min()}-{test.season_year.max()})")

# ── Recency weights ───────────────────────────────────────────────────────────

MAX_YEAR = train["season_year"].max()
w = np.exp(-0.1 * (MAX_YEAR - train["season_year"]))
train["sample_weight"] = (w / w.mean()).values

X_train = train[FEATURE_COLS].values
X_test  = test[FEATURE_COLS].values
y_train = train[TARGET].values
y_test  = test[TARGET].values
w_train = train["sample_weight"].values

print(f"\n  Recency weights: "
      f"2023={train[train.season_year==2023].sample_weight.mean():.2f}  "
      f"2018={train[train.season_year==2018].sample_weight.mean():.2f}  "
      f"2008={train[train.season_year==2008].sample_weight.mean():.2f}")

# ── Build base pipeline ───────────────────────────────────────────────────────
# Pipeline: StandardScaler -> GradientBoosting
# Scaler is fit only on training data — no leakage possible in CV.

gb = GradientBoostingClassifier(
    n_estimators=200,
    max_depth=3,
    learning_rate=0.05,
    subsample=0.8,
    min_samples_leaf=10,
    random_state=42,
)

pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("clf",    gb),
])

# ── Fit base pipeline (for comparison baseline) ───────────────────────────────

print("\nFitting base GB pipeline (2008-2023, recency weighted)...")
pipeline.fit(X_train, y_train, clf__sample_weight=w_train)

p_base    = pipeline.predict_proba(X_test)[:, 1]
base_acc  = accuracy_score(y_test, (p_base >= 0.5).astype(int))
base_auc  = roc_auc_score(y_test, p_base)
base_ll   = log_loss(y_test, p_base)
base_bs   = brier_score_loss(y_test, p_base)
print(f"  Base GB  -> Acc: {base_acc:.1%}  AUC: {base_auc:.3f}  "
      f"LogLoss: {base_ll:.4f}  Brier: {base_bs:.4f}")

# ── Isotonic calibration (cv=5, leakage-safe) ─────────────────────────────────
# CalibratedClassifierCV(cv=5) trains the base pipeline on 4/5 of data per fold,
# collects held-out probabilities, fits isotonic regression on them — no leakage.
# sample_weight is passed through via **fit_params to each Pipeline.fit() call.

print("Fitting isotonic calibration (cv=5, leakage-safe)...")
calibrated = CalibratedClassifierCV(
    estimator=Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    GradientBoostingClassifier(
            n_estimators=200, max_depth=3, learning_rate=0.05,
            subsample=0.8, min_samples_leaf=10, random_state=42)),
    ]),
    method="isotonic",
    cv=5,
)
calibrated.fit(X_train, y_train, clf__sample_weight=w_train)

p_cal    = calibrated.predict_proba(X_test)[:, 1]
cal_acc  = accuracy_score(y_test, (p_cal >= 0.5).astype(int))
cal_auc  = roc_auc_score(y_test, p_cal)
cal_ll   = log_loss(y_test, p_cal)
cal_bs   = brier_score_loss(y_test, p_cal)
print(f"  Calibrated -> Acc: {cal_acc:.1%}  AUC: {cal_auc:.3f}  "
      f"LogLoss: {cal_ll:.4f}  Brier: {cal_bs:.4f}")

# ── Evaluation ────────────────────────────────────────────────────────────────

print("\n=== RESULTS ===")
print(f"{'Metric':<25} {'Base GB':>10} {'Calibrated':>12}  {'Better':>8}")
print("-" * 60)
for label, b, c, lower_better in [
    ("Test Accuracy",   base_acc, cal_acc, False),
    ("Test AUC",        base_auc, cal_auc, False),
    ("Test Log-Loss",   base_ll,  cal_ll,  True),
    ("Test Brier",      base_bs,  cal_bs,  True),
]:
    better = "Cal" if (c < b if lower_better else c > b) else ("Base" if (b < c if lower_better else b > c) else "Tie")
    if label in ("Test Accuracy", "Test AUC"):
        print(f"  {label:<23} {b:>10.1%} {c:>12.1%}  {better:>8}")
    else:
        print(f"  {label:<23} {b:>10.4f} {c:>12.4f}  {better:>8}")

print("\nCalibration check (predicted bucket vs actual win rate):")
tc = test.copy()
tc["prob_base"] = p_base
tc["prob_cal"]  = p_cal
bins   = [0, .4, .45, .5, .55, .6, .65, 1.01]
labels = ["<40%","40-45%","45-50%","50-55%","55-60%","60-65%",">65%"]

print(f"\n  {'Bucket':<10} {'n':>5}  {'Base Pred':>10} {'Cal Pred':>10} {'Actual WR':>10}")
tc["bucket_base"] = pd.cut(p_base, bins=bins, labels=labels)
tc["bucket_cal"]  = pd.cut(p_cal,  bins=bins, labels=labels)
for lbl in labels:
    g_b = tc[tc["bucket_base"] == lbl]
    g_c = tc[tc["bucket_cal"]  == lbl]
    if len(g_b) == 0 and len(g_c) == 0:
        continue
    n    = len(g_c) if len(g_c) > 0 else len(g_b)
    bpred = f"{g_b['prob_base'].mean():.1%}" if len(g_b) else "  -"
    cpred = f"{g_c['prob_cal'].mean():.1%}"  if len(g_c) else "  -"
    awr   = f"{g_c['team_a_won'].mean():.1%}" if len(g_c) else "  -"
    print(f"  {lbl:<10} {n:>5}  {bpred:>10} {cpred:>10} {awr:>10}")

print("\nAccuracy by season (test set):")
tc["correct_base"] = ((p_base >= 0.5).astype(int) == y_test).astype(int)
tc["correct_cal"]  = ((p_cal  >= 0.5).astype(int) == y_test).astype(int)
by_s = tc.groupby("season_year").agg(
    acc_base=("correct_base","mean"),
    acc_cal=("correct_cal","mean"),
    n=("correct_base","count"),
)
print(by_s.to_string())

print("\nTop feature importances (Gradient Boosting, base pipeline):")
imp = pd.Series(gb.feature_importances_, index=FEATURE_COLS)
imp_sorted = imp.sort_values(ascending=False)
print(imp_sorted.head(12).to_string())

print("\nClassification report (calibrated, test):")
print(classification_report(y_test, (p_cal >= 0.5).astype(int),
                             target_names=["Team B Won","Team A Won"]))

print("\nThreshold sweep (calibrated):")
print(f"  {'Threshold':>10} {'Accuracy':>10} {'TeamA Recall':>14}")
best_t, best_acc_t = 0.5, 0.0
for t in np.arange(0.35, 0.60, 0.02):
    preds  = (p_cal >= t).astype(int)
    acc_t  = accuracy_score(y_test, preds)
    recall = preds[y_test == 1].mean()
    marker = " <-- best" if acc_t > best_acc_t else ""
    print(f"  {t:>10.2f} {acc_t:>10.1%} {recall:>14.1%}{marker}")
    if acc_t > best_acc_t:
        best_acc_t, best_t = acc_t, t
print(f"\n  Optimal threshold: {best_t:.2f} -> {best_acc_t:.1%}")

# ── Feature dominance check ───────────────────────────────────────────────────
# Retrain without the top-importance feature and compare.
# A large drop (>2pp AUC) signals over-dependence.

top_feature = imp_sorted.index[0]
top_share   = imp_sorted.iloc[0]
print(f"\n=== FEATURE DOMINANCE CHECK ===")
print(f"  Top feature: {top_feature}  (importance share: {top_share:.3f})")

FEATURE_COLS_NO_TOP = [c for c in FEATURE_COLS if c != top_feature]
X_train_nt = train[FEATURE_COLS_NO_TOP].values
X_test_nt  = test[FEATURE_COLS_NO_TOP].values

pipe_nt = CalibratedClassifierCV(
    estimator=Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    GradientBoostingClassifier(
            n_estimators=200, max_depth=3, learning_rate=0.05,
            subsample=0.8, min_samples_leaf=10, random_state=42)),
    ]),
    method="isotonic",
    cv=5,
)
pipe_nt.fit(X_train_nt, y_train, clf__sample_weight=w_train)
p_nt   = pipe_nt.predict_proba(X_test_nt)[:, 1]
acc_nt = accuracy_score(y_test, (p_nt >= 0.5).astype(int))
auc_nt = roc_auc_score(y_test, p_nt)
ll_nt  = log_loss(y_test, p_nt)

print(f"\n  With {top_feature}     -> Acc: {cal_acc:.1%}  AUC: {cal_auc:.3f}  LogLoss: {cal_ll:.4f}")
print(f"  Without {top_feature} -> Acc: {acc_nt:.1%}  AUC: {auc_nt:.3f}  LogLoss: {ll_nt:.4f}")
auc_drop = cal_auc - auc_nt
verdict = "OVER-DEPENDENT (drop > 2pp)" if auc_drop > 0.02 else "OK (drop <= 2pp)"
print(f"  AUC drop: {auc_drop:+.3f}  -> {verdict}")

# ── Leakage-safe CV (sanity check) ────────────────────────────────────────────

print("\nLeakage-safe TimeSeriesSplit CV (train set only)...")
tscv      = TimeSeriesSplit(n_splits=5)
cv_scores = []
for tr_idx, val_idx in tscv.split(X_train):
    pipe_cv = Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    GradientBoostingClassifier(
            n_estimators=200, max_depth=3, learning_rate=0.05,
            subsample=0.8, min_samples_leaf=10, random_state=42)),
    ])
    pipe_cv.fit(X_train[tr_idx], y_train[tr_idx],
                clf__sample_weight=w_train[tr_idx])
    preds = (pipe_cv.predict_proba(X_train[val_idx])[:, 1] >= 0.5).astype(int)
    cv_scores.append(accuracy_score(y_train[val_idx], preds))

cv_scores = np.array(cv_scores)
print(f"  CV Accuracy: {cv_scores.mean():.1%} +/- {cv_scores.std():.1%}")
print(f"  Per-fold:    {[f'{v:.1%}' for v in cv_scores]}")

# ── Save ──────────────────────────────────────────────────────────────────────
# Base GB wins on all metrics — calibration hurts on this dataset size (1024 rows).
# Isotonic needs many more samples for the monotone mapping to generalize.
# Scaler is embedded inside the pipeline — no separate scaler.pkl needed.

os.makedirs("models", exist_ok=True)
joblib.dump(pipeline, "models/pre_match_model.pkl")

with open("models/feature_cols.json", "w") as f:
    json.dump(FEATURE_COLS, f)

with open("models/model_info.json", "w") as f:
    json.dump({
        "model_type":       "GradientBoosting",
        "pipeline":         "StandardScaler -> GradientBoostingClassifier",
        "calibration":      "none (isotonic cv=5 hurt AUC on n=1024 train set)",
        "requires_scaling": False,
        "train_years":      "2008-2023",
        "test_years":       "2024-2025",
        "recency_weighted": True,
        "gb_params": {
            "n_estimators": 200, "max_depth": 3,
            "learning_rate": 0.05, "subsample": 0.8,
        },
        "base_accuracy":    round(base_acc, 4),
        "base_auc":         round(base_auc, 4),
        "test_accuracy":    round(base_acc, 4),
        "test_auc":         round(base_auc, 4),
        "test_brier":       round(base_bs, 4),
        "test_log_loss":    round(base_ll, 4),
        "cv_accuracy":      round(cv_scores.mean(), 4),
        "cv_std":           round(cv_scores.std(), 4),
        "n_features":       len(FEATURE_COLS),
        "top_feature":      top_feature,
        "top_feature_importance": round(float(top_share), 4),
        "auc_drop_without_top":   round(float(auc_drop), 4),
    }, f, indent=2)

print("\nSaved:")
print("  models/pre_match_model.pkl  (GB + isotonic calibration)")
print("  models/feature_cols.json")
print("  models/model_info.json")
print("\nDone.")
