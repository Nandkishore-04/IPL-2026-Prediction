"""
Loads precomputed player career stats from JSON.
Used at prediction time to look up stats for a given playing XI.
"""

import json
import os

import api.core.feature_engine as fe

import sqlite3
import os

DB_PATH = "data/ipl_engine.db"

# In-memory cache for frequently accessed players
_player_cache = {}

def load():
    """Initial check of the database."""
    if not os.path.exists(DB_PATH):
        print(f"⚠️ [PlayerStats] Database not found at {DB_PATH}")
        return
    print(f"[PlayerStats] Using SQLite Engine: {DB_PATH}")


def get_player_stats(name: str) -> dict:
    """Return stats dict for a player from the SQLite database."""
    if name in _player_cache:
        return _player_cache[name]
    
    # Try via full name mapping if needed
    from api.core.feature_engine import _reverse_name_map
    search_name = _reverse_name_map.get(name, name)

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Returns dict-like objects
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM player_stats WHERE name = ?", (search_name,))
        row = cursor.fetchone()
        conn.close()

        if row:
            stats = dict(row)
            _player_cache[name] = stats
            return stats
    except Exception as e:
        print(f"❌ [PlayerStats] Error querying player {name}: {e}")
    
    return None


def get_all() -> dict:
    """Loads all stats into memory (for dashboard/bulk ops)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM player_stats")
        rows = cursor.fetchall()
        conn.close()
        return {r["name"]: dict(r) for r in rows}
    except Exception:
        return {}


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
