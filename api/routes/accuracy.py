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
    Brier score = mean((predicted_prob - actual_outcome)^2)
    Range: 0 (perfect) to 1 (worst). Below 0.25 is good.
    Only computed when predicted_probability is stored in the log.
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
    Groups predictions into 10 probability buckets (0-10%, 10-20%, …, 90-100%).
    For each bucket returns: predicted_mid, actual_win_rate, count.
    A well-calibrated model has actual_win_rate ≈ predicted_mid.
    """
    entries = [r for r in log if r.get("predicted_probability") is not None]
    if not entries:
        return []

    buckets = [{
        "range": f"{i*10}-{(i+1)*10}%",
        "mid":   (i * 10 + 5) / 100,
        "count": 0,
        "wins":  0,
    } for i in range(10)]

    for r in entries:
        prob    = r["predicted_probability"]
        correct = r["predicted_winner"] == r["actual_winner"]
        idx     = min(int(prob * 10), 9)
        buckets[idx]["count"] += 1
        buckets[idx]["wins"]  += 1 if correct else 0

    result = []
    for b in buckets:
        if b["count"] > 0:
            result.append({
                "range":            b["range"],
                "predicted_prob":   b["mid"],
                "actual_win_rate":  round(b["wins"] / b["count"], 4),
                "count":            b["count"],
            })
    return result


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

    correct  = sum(1 for r in log if r["predicted_winner"] == r["actual_winner"])
    accuracy = round(correct / total, 4)

    # Per-team accuracy
    team_correct, team_total = {}, {}
    for r in log:
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
        "total_predictions":  total,
        "correct":            correct,
        "accuracy":           accuracy,
        "accuracy_percent":   f"{accuracy*100:.1f}%",
        "brier_score":        _brier_score(log),
        "calibration":        _calibration_buckets(log),
        "by_team":            by_team,
        "recent":             log[-10:],
    }


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
