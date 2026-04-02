"""
Phase C: End-of-Season Retrain Script
======================================
Run this after IPL 2026 ends to incorporate 2026 results into the model.

What it does:
  1. Reads api/data/ipl2026_standings.json (match results you logged)
  2. Appends 2026 match records to cleaned_matches.csv
  3. Re-runs feature engineering (team + player features)
  4. Retrains pre-match model on 2008-2025 data, tests on 2026
  5. Retrains live model on all ball-by-ball data
  6. Replaces models/*.pkl with new models

Run from project root:
  python src/retrain_2026.py
"""

import pandas as pd
import numpy as np
import json, joblib, os, warnings
warnings.filterwarnings('ignore')

from sklearn.linear_model  import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics       import accuracy_score, roc_auc_score
from sklearn.ensemble      import RandomForestClassifier

print("=" * 60)
print("IPL 2026 End-of-Season Retrain")
print("=" * 60)

# ── Step 1: Load 2026 logged results ─────────────────────────────────────────
print("\n[1/5] Loading 2026 season results...")

with open("api/data/ipl2026_standings.json") as f:
    standings = json.load(f)

matches_2026 = standings["matches"]
if not matches_2026:
    print("  No 2026 matches logged. Log match results first via POST /api/log-result")
    print("  Exiting — nothing to retrain on.")
    exit(0)

print(f"  Found {len(matches_2026)} logged 2026 matches")

# ── Step 2: Append 2026 results to cleaned_matches.csv ───────────────────────
print("\n[2/5] Appending 2026 results to cleaned_matches.csv...")

matches = pd.read_csv("data/processed/cleaned_matches.csv", parse_dates=["date"])
existing_ids = set(matches["match_id"].astype(str).tolist())

new_rows = []
for m in matches_2026:
    mid = f"2026_{m['match_num']}"
    if mid in existing_ids:
        continue   # already added in a previous retrain

    new_rows.append({
        "match_id":     mid,
        "date":         m["date"],
        "season_year":  2026,
        "venue":        m.get("venue", ""),
        "city":         "",
        "toss_winner":  "",          # not logged
        "toss_decision":"",
        "winner":       m["winner"],
        "win_outcome":  "",
        "stage":        "Group",
        "is_playoff":   0,
    })

if new_rows:
    new_df  = pd.DataFrame(new_rows)
    matches = pd.concat([matches, new_df], ignore_index=True)
    matches.to_csv("data/processed/cleaned_matches.csv", index=False)
    print(f"  Added {len(new_rows)} new 2026 rows → cleaned_matches.csv now has {len(matches)} matches")
else:
    print("  All 2026 matches already in CSV — nothing new to append")

# ── Step 3: Rebuild features ──────────────────────────────────────────────────
print("\n[3/5] Rebuilding team features with 2026 data...")
print("  Running: python src/build_features.py")
os.system("python src/build_features.py")

# Load updated features
ff_path = "data/processed/full_features.csv"
if not os.path.exists(ff_path):
    print("  full_features.csv not found — run src/build_features.py manually first")
    exit(1)

ff = pd.read_csv(ff_path, parse_dates=["date"])
print(f"  Features loaded: {len(ff)} matches")

# ── Step 4: Retrain pre-match model ──────────────────────────────────────────
print("\n[4/5] Retraining pre-match model (train: 2008-2025, test: 2026)...")

with open("models/feature_cols.json") as f:
    feature_cols = json.load(f)

train = ff[ff["season_year"] <= 2025]
test  = ff[ff["season_year"] == 2026]

print(f"  Train: {len(train)} matches | Test: {len(test)} matches")

if len(test) < 5:
    print(f"  Only {len(test)} 2026 test matches — accuracy estimate will be unreliable")
    print("  Proceeding anyway...")

X_train = train[feature_cols]
y_train = train["team_a_won"]
X_test  = test[feature_cols]
y_test  = test["team_a_won"]

scaler   = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)

lr = LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced", C=0.1, penalty="l1", solver="liblinear")
lr.fit(X_train_s, y_train)

train_acc = accuracy_score(y_train, lr.predict(X_train_s))
test_acc  = accuracy_score(y_test,  lr.predict(X_test_s))  if len(test) > 0 else None
test_auc  = roc_auc_score(y_test,   lr.predict_proba(X_test_s)[:,1]) if len(test) > 1 else None

print(f"  Train accuracy: {train_acc:.1%}")
if test_acc:
    print(f"  Test accuracy (2026): {test_acc:.1%} | AUC: {test_auc:.3f}" if test_auc else f"  Test accuracy (2026): {test_acc:.1%}")

# Save
joblib.dump(lr,     "models/pre_match_model.pkl")
joblib.dump(scaler, "models/scaler.pkl")

with open("models/model_info.json", "w") as f:
    json.dump({
        "model_type":      "LogisticRegression",
        "requires_scaling": True,
        "train_accuracy":  round(train_acc, 4),
        "test_accuracy":   round(test_acc, 4) if test_acc else None,
        "auc":             round(test_auc, 4) if test_auc else None,
        "n_features":      len(feature_cols),
        "train_seasons":   "2008-2025",
        "test_season":     "2026",
        "retrained_on":    f"{len(matches_2026)} logged 2026 matches",
    }, f, indent=2)

print("  Saved: models/pre_match_model.pkl, models/scaler.pkl, models/model_info.json")

# ── Step 5: Retrain live model ────────────────────────────────────────────────
print("\n[5/5] Retraining live model...")
print("  Running: python src/build_live_data.py && python src/train_live_model.py")
os.system("python src/build_live_data.py")
os.system("python src/train_live_model.py")

print("\n" + "=" * 60)
print("Retrain complete.")
print("Restart the API (Ctrl+C → python -m uvicorn api.main:app --reload)")
print("to load the updated models.")
print("=" * 60)
