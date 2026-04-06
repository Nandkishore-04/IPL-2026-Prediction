"""
backfill_predictions.py
=======================
Retroactively predict IPL 2026 matches that were logged without a prediction.

Uses use_2026_form=False so predictions reflect what the model would have
output using only pre-season historical data (fair — 2026 results were
unknown at match time).

Run from project root: python src/backfill_predictions.py
"""

import sys
import os
sys.path.insert(0, os.getcwd())

import json
import numpy as np

# Bootstrap the API modules (normally loaded by uvicorn lifespan)
import api.core.model_loader as ml
import api.core.feature_engine as fe
import api.core.season_tracker as st
from api.core.auto_predictor import predict_and_store, mark_result, season_summary

def main():
    print("Loading model and feature engine...")
    ml.load_all()
    fe.load()
    # season_tracker loads lazily from disk — no explicit init needed

    log_path = "api/data/predictions_log.json"
    with open(log_path) as f:
        logs = json.load(f)

    missing = [e for e in logs if not e.get("predicted_winner")]
    if not missing:
        print("No entries missing predictions — nothing to backfill.")
        _print_summary()
        return

    print(f"\nBackfilling {len(missing)} matches (no 2026 form — using historical data only):\n")
    print(f"  {'Match':<35} {'Predicted':<28} {'Prob':>6}  {'Actual':<28} {'Result'}")
    print("  " + "-" * 105)

    for e in missing:
        team_a = e["team_a"]
        team_b = e["team_b"]
        venue  = e["venue"]
        date   = e["match_date"]

        entry = predict_and_store(
            team_a=team_a,
            team_b=team_b,
            venue=venue,
            date=date,
            toss_winner=None,       # unknown — defaults to team_a
            toss_decision="bat",
            use_2026_form=False,    # season hadn't started yet — use historical only
            source="backfill",
        )

        # Mark the result if we have it
        if e.get("actual_winner"):
            mark_result(team_a, team_b, date, e["actual_winner"])

        # Re-read to show final state
        with open(log_path) as f:
            logs_fresh = json.load(f)
        final = next((x for x in logs_fresh if x["match_id"] == entry["match_id"]), entry)

        pred    = final.get("predicted_winner", "—")
        prob    = final.get("predicted_probability")
        actual  = final.get("actual_winner", "—")
        correct = final.get("correct")
        result  = "CORRECT" if correct is True else "WRONG" if correct is False else "pending"

        match_str = f"{team_a[:20]} vs {team_b[:20]}"
        prob_str  = f"{prob*100:.0f}%" if prob is not None else "—"
        print(f"  {match_str:<35} {pred:<28} {prob_str:>6}  {actual:<28} {result}")

    print()
    _print_summary()


def _print_summary():
    s = season_summary()
    print("=== IPL 2026 Prediction Summary ===")
    print(f"  Total predicted : {s['total_predicted']} / {s['target_matches']} matches")
    print(f"  Results known   : {s['results_known']}")
    print(f"  Correct         : {s['correct']}")
    print(f"  Wrong           : {s['wrong']}")
    print(f"  Pending result  : {s['pending']}")
    print(f"  Accuracy so far : {s['accuracy_percent']}")


if __name__ == "__main__":
    main()
