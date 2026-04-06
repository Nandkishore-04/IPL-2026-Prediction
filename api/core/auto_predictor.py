"""
auto_predictor.py
=================
Automated pre-match prediction and result logging.

Called by:
  live_feed.poll_once()        → predict_and_store() when a match is first detected
  live_feed._auto_log_result() → mark_result() when a match ends
  src/backfill_predictions.py  → predict_and_store() for retroactive entries
"""

import json
import os
import numpy as np
from datetime import datetime

_LOG_PATH        = "api/data/predictions_log.json"
_PREDICTED_PATH  = "api/data/auto_predicted_match_ids.json"


# ── Storage helpers ───────────────────────────────────────────────────────────

def _load_log() -> list:
    try:
        with open(_LOG_PATH) as f:
            return json.load(f)
    except Exception:
        return []


def _save_log(logs: list):
    os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
    with open(_LOG_PATH, "w") as f:
        json.dump(logs, f, indent=2)


def _load_predicted_ids() -> set:
    try:
        with open(_PREDICTED_PATH) as f:
            return set(json.load(f))
    except Exception:
        return set()


def _save_predicted_ids(ids: set):
    with open(_PREDICTED_PATH, "w") as f:
        json.dump(list(ids), f)


def make_match_key(team_a: str, team_b: str, date: str) -> str:
    return f"{team_a[:3].upper()}-{team_b[:3].upper()}-{date}"


# ── Core: predict ─────────────────────────────────────────────────────────────

def predict_and_store(
    team_a: str,
    team_b: str,
    venue: str,
    date: str,
    toss_winner: str = None,
    toss_decision: str = "bat",
    cricapi_match_id: str = None,
    use_2026_form: bool = True,
    source: str = "auto_predictor",
) -> dict | None:
    """
    Make a pre-match prediction and store it in predictions_log.json.
    Skips silently if a prediction already exists for this match key.
    Returns the log entry dict, or None on error.
    """
    import api.core.feature_engine as fe
    import api.core.model_loader as ml

    model        = ml.get_pre_match_model()
    feature_cols = ml.get_feature_cols()
    if model is None or not feature_cols:
        print("[AutoPredictor] Model not loaded — cannot predict")
        return None

    toss_winner   = toss_winner or team_a   # neutral default: team_a won toss
    toss_decision = toss_decision or "bat"

    try:
        feat = fe.build_prematch_features(
            team_a=team_a, team_b=team_b, venue=venue,
            toss_winner=toss_winner, toss_decision=toss_decision,
            team_a_xi=None, team_b_xi=None,
            use_2026_form=use_2026_form,
        )
        X     = np.array([[feat[c] for c in feature_cols]])
        proba = model.predict_proba(X)[0]
    except Exception as e:
        print(f"[AutoPredictor] Feature build error for {team_a} vs {team_b}: {e}")
        return None

    ta_prob          = float(proba[1])
    predicted_winner = team_a if ta_prob >= 0.5 else team_b
    # Store the probability of the PREDICTED WINNER (always ≥ 50%)
    winner_prob      = ta_prob if ta_prob >= 0.5 else 1.0 - ta_prob
    match_key        = make_match_key(team_a, team_b, date)

    logs     = _load_log()
    existing = next((e for e in logs if e.get("match_id") == match_key), None)

    if existing:
        if existing.get("predicted_winner") is not None:
            return existing   # prediction already made — skip
        # Fill in missing prediction on an already-logged entry
        existing["predicted_winner"]      = predicted_winner
        existing["predicted_probability"] = round(winner_prob, 4)
        existing["source"]                = source
        if existing.get("actual_winner"):
            existing["correct"] = (predicted_winner == existing["actual_winner"])
        _save_log(logs)
        print(f"[AutoPredictor] Filled prediction: {team_a} vs {team_b} "
              f"-> {predicted_winner} ({ta_prob:.1%})")
        return existing

    entry = {
        "match_id":              match_key,
        "team_a":                team_a,
        "team_b":                team_b,
        "actual_winner":         None,
        "match_date":            date,
        "venue":                 venue,
        "predicted_winner":      predicted_winner,
        "predicted_probability": round(winner_prob, 4),
        "correct":               None,
        "source":                source,
    }
    logs.append(entry)
    _save_log(logs)

    if cricapi_match_id:
        ids = _load_predicted_ids()
        ids.add(cricapi_match_id)
        _save_predicted_ids(ids)

    print(f"[AutoPredictor] Predicted: {team_a} vs {team_b} "
          f"-> {predicted_winner} ({ta_prob:.1%}) [{date}]")
    return entry


# ── Core: log result ──────────────────────────────────────────────────────────

def mark_result(
    team_a: str,
    team_b: str,
    date: str,
    actual_winner: str,
) -> bool:
    """
    After a match ends: update predictions_log with the actual winner and
    calculate whether the prediction was correct.
    Returns True if an existing prediction entry was updated.
    """
    match_key = make_match_key(team_a, team_b, date)
    logs      = _load_log()
    entry     = next((e for e in logs if e.get("match_id") == match_key), None)

    if entry is None:
        return False   # no entry to update (prediction may not have been made)

    if entry.get("actual_winner") == actual_winner:
        return False   # already logged

    entry["actual_winner"] = actual_winner
    if entry.get("predicted_winner"):
        entry["correct"] = (entry["predicted_winner"] == actual_winner)

    _save_log(logs)

    verdict = (
        "CORRECT" if entry.get("correct") is True
        else "WRONG" if entry.get("correct") is False
        else "no prediction"
    )
    print(f"[AutoPredictor] Result: {team_a} vs {team_b} -> "
          f"{actual_winner} [{verdict}]")
    return True


# ── Season summary ────────────────────────────────────────────────────────────

def season_summary() -> dict:
    """Return accuracy stats for all auto-predicted matches this season."""
    logs = _load_log()
    tracked = [e for e in logs if e.get("predicted_winner") and e.get("actual_winner")]
    correct  = [e for e in tracked if e.get("correct")]
    pending  = [e for e in logs if e.get("predicted_winner") and not e.get("actual_winner")]

    return {
        "total_predicted":  len(tracked) + len(pending),
        "results_known":    len(tracked),
        "correct":          len(correct),
        "wrong":            len(tracked) - len(correct),
        "pending":          len(pending),
        "accuracy":         round(len(correct) / len(tracked), 4) if tracked else None,
        "accuracy_percent": f"{len(correct)/len(tracked)*100:.1f}%" if tracked else "—",
        "target_matches":   74,
    }
