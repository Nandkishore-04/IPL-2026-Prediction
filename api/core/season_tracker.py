"""
2026 Season Tracker
====================
Maintains live IPL 2026 standings in ipl2026_standings.json.
Every time a match result is logged via POST /api/log-result,
this module updates:
  - wins / losses / matches played per team
  - win streak (positive = win streak, negative = losing streak)
  - last5 results (list of 1s and 0s, most recent last)
  - ema_form: exponential moving average of results (α=0.3)
      Formula: ema_t = α * result_t + (1-α) * ema_{t-1}
      Recent matches weighted more; converges faster than last5 average.
  - season win rate
  - match number in season (used as a feature)

The feature engine reads from this at prediction time, so the
model's form stats become more accurate as the 2026 season progresses.
"""

import json
import os
import threading

STANDINGS_PATH = "api/data/ipl2026_standings.json"
_lock = threading.Lock()

EMA_ALPHA = 0.3   # weight on the most recent match; 0.3 → last match counts 30%

_DEFAULT_TEAM = lambda: {
    "wins": 0, "losses": 0, "matches": 0,
    "streak": 0, "last5": [], "points": 0,
    "ema_form": 0.5,   # neutral prior before any matches
}


def _read() -> dict:
    with open(STANDINGS_PATH) as f:
        return json.load(f)


def _write(data: dict):
    with open(STANDINGS_PATH, "w") as f:
        json.dump(data, f, indent=2)


def log_match(team_a: str, team_b: str, winner: str, match_date: str, venue: str = ""):
    """
    Record a completed match result and update both teams' stats.
    Called automatically when POST /api/log-result is hit.
    """
    with _lock:
        data = _read()
        ts = data["team_stats"]

        # Ensure both teams exist (handles new franchises)
        for team in [team_a, team_b]:
            if team not in ts:
                ts[team] = _DEFAULT_TEAM()
            elif "ema_form" not in ts[team]:
                ts[team]["ema_form"] = 0.5   # migrate old entries

        match_num = len(data["matches"]) + 1

        # Record match
        data["matches"].append({
            "match_num": match_num,
            "date":      match_date,
            "team_a":    team_a,
            "team_b":    team_b,
            "winner":    winner,
            "venue":     venue,
        })

    # Update each team
    for team in [team_a, team_b]:
        is_no_result = (winner.lower() in ["no result", "washout", "abandoned"])
        won = (team == winner)
        
        ts[team]["matches"] += 1
        
        if is_no_result:
            ts[team]["points"]  += 1
            # Streak resets on washout
            ts[team]["streak"] = 0
            # Result for EMA: neutral 0.5
            result = 0.5
        else:
            ts[team]["wins"]    += 1 if won else 0
            ts[team]["losses"]  += 0 if won else 1
            ts[team]["points"]  += 2 if won else 0
            
            # last5: 1=win, 0=loss (only for completed matches)
            ts[team]["last5"].append(1 if won else 0)
            ts[team]["last5"] = ts[team]["last5"][-5:]
            
            # streak: +N = N-win streak, -N = N-loss streak
            if won:
                ts[team]["streak"] = max(ts[team]["streak"], 0) + 1
            else:
                ts[team]["streak"] = min(ts[team]["streak"], 0) - 1
            
            result = 1.0 if won else 0.0

        # ema_form: exponential moving average
        ts[team]["ema_form"] = round(
            EMA_ALPHA * result + (1 - EMA_ALPHA) * ts[team].get("ema_form", 0.5),
            4,
        )

    _write(data)

    # Back-fill 'correct' flag on any matching prediction
    _evaluate_prediction(team_a, team_b, winner, match_date)
    return match_num


_PREDICTIONS_LOG = "api/data/predictions_log.json"

def _evaluate_prediction(team_a: str, team_b: str, winner: str, match_date: str):
    """If a prediction exists for this match, mark it correct/incorrect."""
    try:
        with open(_PREDICTIONS_LOG) as f:
            logs = json.load(f)
    except Exception:
        return

    match_id = f"{team_a[:3].upper()}-{team_b[:3].upper()}-{match_date}"
    updated = False
    for entry in logs:
        if entry.get("match_id") == match_id:
            entry["actual_winner"] = winner
            if entry.get("predicted_winner"):
                entry["correct"] = entry["predicted_winner"] == winner
            updated = True

    if updated:
        with open(_PREDICTIONS_LOG, "w") as f:
            json.dump(logs, f, indent=2)


def get_standings() -> dict:
    """Return full standings dict."""
    return _read()


def get_team_form(team: str) -> dict | None:
    """
    Return current 2026 form for a team, or None if they haven't played yet.
    Keys match what feature_engine.py expects:
      season_wr, last5_wr, streak, match_num_in_season
    """
    data = _read()
    ts   = data["team_stats"]

    if team not in ts or ts[team]["matches"] == 0:
        return None   # No 2026 data yet — feature engine will use historical

    t = ts[team]
    matches_played = t["matches"]
    season_wr      = t["wins"] / matches_played if matches_played > 0 else 0.5
    last5_wr       = sum(t["last5"]) / len(t["last5"]) if t["last5"] else season_wr
    streak         = float(t["streak"])
    match_num      = len(data["matches"])   # total matches played so far in season

    ema_form = t.get("ema_form", last5_wr)   # fallback to last5_wr for old entries

    return {
        "season_wr":            round(season_wr, 4),
        "last5_wr":             round(last5_wr,  4),
        "ema_form":             round(ema_form,  4),
        "streak":               streak,
        "match_num_in_season":  match_num + 1,   # +1 because next match is match_num+1
        "matches_played":       matches_played,
    }


def recompute_ema():
    """
    Recompute ema_form for all teams from scratch using match history.
    Run once after adding EMA support to backfill existing standings.
    Safe to re-run: always resets to 0.5 prior then replays all matches.
    """
    with _lock:
        data = _read()
        ts   = data["team_stats"]

        # Reset all EMA values to neutral prior
        for team in ts:
            ts[team]["ema_form"] = 0.5

        # Replay matches in order (already sorted by match_num)
        for match in sorted(data["matches"], key=lambda m: m["match_num"]):
            for team in [match["team_a"], match["team_b"]]:
                if team not in ts:
                    ts[team] = _DEFAULT_TEAM()
                won = (team == match["winner"])
                result = 1.0 if won else 0.0
                ts[team]["ema_form"] = round(
                    EMA_ALPHA * result + (1 - EMA_ALPHA) * ts[team]["ema_form"],
                    4,
                )

        _write(data)

    print("[SeasonTracker] EMA backfill complete:")
    for team, s in data["team_stats"].items():
        print(f"  {team:<35} ema_form={s['ema_form']:.3f}  last5_wr={sum(s['last5'])/len(s['last5']) if s['last5'] else 0:.3f}")


def get_table() -> list:
    """Return sorted points table for display in frontend."""
    data = _read()
    ts   = data["team_stats"]
    rows = []
    for team, s in ts.items():
        rows.append({
            "team":    team,
            "matches": s["matches"],
            "wins":    s["wins"],
            "losses":  s["losses"],
            "points":  s["points"],
            "nrr":     0.0,   # Net Run Rate — not tracked yet
            "last5":   s["last5"],
            "streak":  s["streak"],
        })
    # Sort: points desc, then wins desc
    rows.sort(key=lambda r: (-r["points"], -r["wins"]))
    return rows
