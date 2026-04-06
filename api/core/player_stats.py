"""
Loads precomputed player career stats from JSON.
Used at prediction time to look up stats for a given playing XI.
"""

import json
import os

import api.core.feature_engine as fe

_player_stats = None

def load():
    global _player_stats
    path = os.path.join("api", "data", "player_stats.json")
    with open(path) as f:
        _player_stats = json.load(f)
    print(f"[PlayerStats] Loaded stats for {len(_player_stats)} players")


def get_player_stats(name: str) -> dict:
    """Return stats dict for a player, or None if not found."""
    if _player_stats is None:
        return None
    
    # Try abbreviation directly
    stats = _player_stats.get(name)
    if stats:
        return stats
        
    # Try mapping full name back to abbreviation
    abbr = fe._reverse_name_map.get(name, name)
    return _player_stats.get(abbr)



def get_all() -> dict:
    return _player_stats or {}


def aggregate_batting(xi: list) -> dict:
    """
    Given a list of 11 player names, return aggregated batting features:
    avg_batting_sr, avg_batting_avg, best_batting_avg
    Uses top 7 batters by batting average (excludes tailenders).
    Falls back to team-average stats for players not found.
    """
    stats = []
    for name in xi:
        p = get_player_stats(name)
        if p:
            stats.append(p)

    if not stats:
        return {"avg_batting_sr": 125.0, "avg_batting_avg": 25.0, "best_batting_avg": 40.0}

    # Sort by batting_avg descending, take top 7
    stats_sorted = sorted(stats, key=lambda x: x.get("batting_avg", 0), reverse=True)
    top7 = stats_sorted[:7]

    avg_sr  = sum(p.get("batting_sr",  125.0) for p in top7) / len(top7)
    avg_avg = sum(p.get("batting_avg",  25.0) for p in top7) / len(top7)
    best    = max(p.get("batting_avg",   0.0) for p in top7)

    return {
        "avg_batting_sr":  round(avg_sr,  2),
        "avg_batting_avg": round(avg_avg, 2),
        "best_batting_avg": round(best,   2),
    }


def aggregate_bowling(xi: list) -> dict:
    """
    Given a list of 11 player names, return aggregated bowling features:
    avg_bowling_econ, avg_bowling_sr, best_bowling_econ
    Uses top 5 bowlers by economy (lowest = best).
    """
    stats = []
    for name in xi:
        p = get_player_stats(name)
        if p and p.get("bowling_econ", 0) > 0:
            stats.append(p)

    if not stats:
        return {"avg_bowling_econ": 8.5, "avg_bowling_sr": 20.0, "best_bowling_econ": 7.0}

    # Sort by bowling_econ ascending (lower = better), take top 5
    stats_sorted = sorted(stats, key=lambda x: x.get("bowling_econ", 99))
    top5 = stats_sorted[:5]

    avg_econ = sum(p.get("bowling_econ", 8.5) for p in top5) / len(top5)
    avg_sr   = sum(p.get("bowling_sr",  20.0) for p in top5) / len(top5)
    best     = min(p.get("bowling_econ",  99) for p in top5)

    return {
        "avg_bowling_econ":  round(avg_econ, 2),
        "avg_bowling_sr":    round(avg_sr,   2),
        "best_bowling_econ": round(best,     2),
    }


def aggregate_experience(xi: list) -> dict:
    """Sum of IPL caps for all 11 players."""
    stats = [get_player_stats(name) for name in xi if get_player_stats(name)]
    total_caps = sum(p.get("ipl_caps", 0) for p in stats)
    return {"total_caps": int(total_caps)}
