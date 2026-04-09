"""
GET  /api/accuracy     — overall prediction accuracy + calibration
GET  /api/standings    — live IPL 2026 points table
POST /api/log-result   — log a completed match result
"""

import json
import os
import threading
import math
from datetime import datetime
from fastapi import APIRouter, HTTPException
from api.schemas.live import LogResultRequest
import api.core.season_tracker as st

router = APIRouter()
LOG_PATH = "api/data/predictions_log.json"
_lock = threading.Lock()


def _read_log() -> list:
    with open(LOG_PATH) as f:
        return json.load(f)


def _write_log(data: list):
    with open(LOG_PATH, "w") as f:
        json.dump(data, f, indent=2)


def _brier_score(log: list) -> float | None:
    """
    Brier score = mean((winner_prob - correct)^2)
    predicted_probability is the probability of the PREDICTED WINNER (always ≥ 0.5).
    correct = 1 if prediction was right, 0 if wrong.
    Range: 0 (perfect) to 1 (worst). Below 0.25 is good.
    """
    entries = [r for r in log if r.get("predicted_probability") is not None]
    if not entries:
        return None
    total = sum(
        (r["predicted_probability"] - (1 if r["predicted_winner"] == r["actual_winner"] else 0)) ** 2
        for r in entries
    )
    return round(total / len(entries), 4)


def _calibration_buckets(log: list) -> list:
    """
    Confidence calibration: when we say X% confidence, are we right X% of the time?
    predicted_probability = confidence in the predicted winner (always 50-100%).
    Groups into buckets of 10pp width from 50% to 100%.
    A well-calibrated model has actual_win_rate ≈ predicted_prob for each bucket.
    """
    entries = [r for r in log if r.get("predicted_probability") is not None]
    if not entries:
        return []

    # Buckets: 50-60%, 60-70%, 70-80%, 80-90%, 90-100%
    bucket_defs = [(0.50, 0.60), (0.60, 0.70), (0.70, 0.80), (0.80, 0.90), (0.90, 1.01)]
    buckets = [{"range": f"{int(lo*100)}-{int(hi*100)}%",
                "mid": (lo + min(hi, 1.0)) / 2,
                "count": 0, "wins": 0}
               for lo, hi in bucket_defs]

    for r in entries:
        prob    = r["predicted_probability"]
        correct = r["predicted_winner"] == r["actual_winner"]
        for i, (lo, hi) in enumerate(bucket_defs):
            if lo <= prob < hi:
                buckets[i]["count"] += 1
                buckets[i]["wins"]  += 1 if correct else 0
                break

    return [
        {
            "range":           b["range"],
            "predicted_prob":  round(b["mid"], 3),
            "actual_win_rate": round(b["wins"] / b["count"], 4),
            "count":           b["count"],
        }
        for b in buckets if b["count"] > 0
    ]


@router.get("/accuracy")
def get_accuracy():
    log   = _read_log()
    total = len(log)

    if not log:
        return {
            "total_predictions": 0,
            "correct": 0,
            "accuracy": None,
            "brier_score": None,
            "calibration": [],
            "by_team": {},
            "recent": [],
        }

    # Only evaluate entries that have both a prediction and a result (exclude washouts)
    evaluated = [
        r for r in log 
        if r.get("predicted_winner") and r.get("actual_winner") 
        and r["actual_winner"].lower() not in ["no result", "washout", "abandoned"]
    ]
    correct   = sum(1 for r in evaluated if r["predicted_winner"] == r["actual_winner"])
    accuracy  = round(correct / len(evaluated), 4) if evaluated else None

    # Per-team accuracy (only evaluated entries)
    team_correct, team_total = {}, {}
    for r in evaluated:
        for team in [r["team_a"], r["team_b"]]:
            team_total[team]   = team_total.get(team, 0) + 1
            if r["predicted_winner"] == r["actual_winner"]:
                team_correct[team] = team_correct.get(team, 0) + 1

    by_team = {
        t: {
            "correct":  team_correct.get(t, 0),
            "total":    team_total[t],
            "accuracy": round(team_correct.get(t, 0) / team_total[t], 3),
        }
        for t in team_total
    }

    return {
        "total_predictions":  len(evaluated),
        "correct":            correct,
        "accuracy":           accuracy,
        "accuracy_percent":   f"{accuracy*100:.1f}%" if accuracy is not None else "—",
        "brier_score":        _brier_score(evaluated),
        "calibration":        _calibration_buckets(evaluated),
        "by_team":            by_team,
        "recent":             log,
    }


@router.delete("/prediction/{match_id}")
def delete_prediction(match_id: str):
    """Delete a prediction entry from the log by match_id."""
    with _lock:
        log = _read_log()
        new_log = [e for e in log if e.get("match_id") != match_id]
        if len(new_log) == len(log):
            raise HTTPException(404, f"match_id '{match_id}' not found")
        _write_log(new_log)
    return {"status": "deleted", "match_id": match_id}


@router.get("/standings")
def get_standings():
    """Live IPL 2026 points table, updated after every logged result."""
    return {
        "table":   st.get_table(),
        "matches": st.get_standings()["matches"],
    }


@router.post("/log-result")
def log_result(req: LogResultRequest):
    """
    Log a completed match result.
    1. Appends to predictions_log.json (for accuracy tracking)
    2. Updates ipl2026_standings.json (for rolling form — fed back into model)
    """
    with _lock:
        log = _read_log()
        entry = {
            "match_id":             req.match_id,
            "team_a":               req.team_a,
            "team_b":               req.team_b,
            "predicted_winner":     req.predicted_winner,
            "actual_winner":        req.actual_winner,
            "correct":              req.predicted_winner == req.actual_winner,
            "predicted_probability":getattr(req, "predicted_probability", None),
            "match_date":           req.match_date,
            "logged_at":            datetime.utcnow().isoformat(),
        }
        log.append(entry)
        _write_log(log)

    # Update 2026 season tracker (outside lock — tracker has its own lock)
    match_num = st.log_match(
        team_a     = req.team_a,
        team_b     = req.team_b,
        winner     = req.actual_winner,
        match_date = req.match_date,
    )

    return {
        "status":    "logged",
        "correct":   entry["correct"],
        "match_num": match_num,
        "message":   f"2026 standings updated. {req.actual_winner} win recorded. Model form stats refreshed.",
    }
