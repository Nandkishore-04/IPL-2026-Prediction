"""
GET  /api/accuracy     — overall prediction accuracy tracker
POST /api/log-result   — log a completed match's actual result
"""

import json
import os
import threading
from datetime import datetime
from fastapi import APIRouter, HTTPException
from api.schemas.live import LogResultRequest

router = APIRouter()
LOG_PATH = "api/data/predictions_log.json"
_lock = threading.Lock()


def _read_log() -> list:
    with open(LOG_PATH) as f:
        return json.load(f)


def _write_log(data: list):
    with open(LOG_PATH, "w") as f:
        json.dump(data, f, indent=2)


@router.get("/accuracy")
def get_accuracy():
    """Return overall accuracy and per-team breakdown."""
    log = _read_log()
    if not log:
        return {
            "total_predictions": 0,
            "correct": 0,
            "accuracy": None,
            "by_team": {},
            "recent": [],
        }

    correct = sum(1 for r in log if r["predicted_winner"] == r["actual_winner"])
    total   = len(log)
    accuracy = round(correct / total, 4) if total > 0 else None

    # Per-team accuracy
    team_correct = {}
    team_total   = {}
    for r in log:
        for team in [r["team_a"], r["team_b"]]:
            team_total[team] = team_total.get(team, 0) + 1
            if r["predicted_winner"] == r["actual_winner"]:
                team_correct[team] = team_correct.get(team, 0) + 1

    by_team = {
        t: {
            "correct": team_correct.get(t, 0),
            "total":   team_total[t],
            "accuracy": round(team_correct.get(t, 0) / team_total[t], 3),
        }
        for t in team_total
    }

    return {
        "total_predictions": total,
        "correct": correct,
        "accuracy": accuracy,
        "accuracy_percent": f"{accuracy*100:.1f}%" if accuracy else None,
        "by_team": by_team,
        "recent": log[-10:],  # last 10 predictions
    }


@router.post("/log-result")
def log_result(req: LogResultRequest):
    """Log a completed match result to track prediction accuracy."""
    with _lock:
        log = _read_log()
        entry = {
            "match_id":        req.match_id,
            "team_a":          req.team_a,
            "team_b":          req.team_b,
            "predicted_winner":req.predicted_winner,
            "actual_winner":   req.actual_winner,
            "correct":         req.predicted_winner == req.actual_winner,
            "match_date":      req.match_date,
            "logged_at":       datetime.utcnow().isoformat(),
        }
        log.append(entry)
        _write_log(log)
    return {"status": "logged", "correct": entry["correct"]}
