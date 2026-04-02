"""
2026 Season Tracker
====================
Maintains live IPL 2026 standings in ipl2026_standings.json.
Every time a match result is logged via POST /api/log-result,
this module updates:
  - wins / losses / matches played per team
  - win streak (positive = win streak, negative = losing streak)
  - last5 results (list of 1s and 0s, most recent last)
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
                ts[team] = {"wins": 0, "losses": 0, "matches": 0, "streak": 0, "last5": [], "points": 0}

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
            won = (team == winner)
            ts[team]["matches"] += 1
            ts[team]["wins"]    += 1 if won else 0
            ts[team]["losses"]  += 0 if won else 1
            ts[team]["points"]  += 2 if won else 0

            # last5: keep only the 5 most recent results (1=win, 0=loss)
            ts[team]["last5"].append(1 if won else 0)
            ts[team]["last5"] = ts[team]["last5"][-5:]

            # streak: +N = N-win streak, -N = N-loss streak
            if won:
                ts[team]["streak"] = max(ts[team]["streak"], 0) + 1
            else:
                ts[team]["streak"] = min(ts[team]["streak"], 0) - 1

        _write(data)
    return match_num


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

    return {
        "season_wr":            round(season_wr, 4),
        "last5_wr":             round(last5_wr,  4),
        "streak":               streak,
        "match_num_in_season":  match_num + 1,   # +1 because next match is match_num+1
        "matches_played":       matches_played,
    }


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
