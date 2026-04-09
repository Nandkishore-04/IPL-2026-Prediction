"""
player_form_2026.py
===================
Fetches and caches IPL 2026 player form from CricAPI scorecards.

Pipeline:
  1. On startup → fetch all completed IPL 2026 match scorecards
  2. After each match → refresh triggered by live_feed.py
  3. feature_engine._compute_xi_quality() → calls get_form() to override career stats

Storage: data/processed/player_form_2026.json
  {
    "V Kohli": [
      {"match_id": "...", "date": "2026-04-05",
       "runs": 72, "balls_faced": 48, "balls_bowled": 0,
       "runs_conceded": 0, "wickets": 0, "overs": 0},
      ...
    ],
    ...
  }
"""

import os
import json
import asyncio
import httpx
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

CRICAPI_KEY  = os.getenv("CRICAPI_KEY", "")
SERIES_ID    = "87c62aac-bc3c-4738-ab93-19da0690488f"   # IPL 2026
import sqlite3
import os

DB_PATH = "data/ipl_engine.db"
LOGGED_PATH = "api/data/scorecard_logged_ids.json"
BASE_URL    = "https://api.cricapi.com/v1"

def _load_logged() -> set:
    try:
        if os.path.exists(LOGGED_PATH):
            with open(LOGGED_PATH) as f:
                return set(json.load(f))
    except Exception:
        pass
    return set()

def _save_logged(ids: set):
    with open(LOGGED_PATH, "w") as f:
        json.dump(list(ids), f)

def get_form(player_key: str) -> dict | None:
    """
    Returns rolling-5 form stats for a player from the SQLite DB.
    """
    # 1. Resolve name
    from api.core.player_stats import get_player_stats
    search_name = player_key
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get last 5 matches for this player
        query = """
            SELECT runs, balls_faced, balls_bowled, runs_conceded, wickets 
            FROM player_match_history_2026 
            WHERE player_name = ? 
            ORDER BY date DESC LIMIT 5
        """
        cursor.execute(query, (search_name,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return None

        n = len(rows)
        total_runs         = sum(r["runs"] for r in rows)
        total_balls_faced  = sum(r["balls_faced"] for r in rows)
        total_balls_bowled = sum(r["balls_bowled"] for r in rows)
        total_conceded     = sum(r["runs_conceded"] for r in rows)
        total_wickets      = sum(r["wickets"] for r in rows)

        bat_sr = (total_runs / total_balls_faced * 100) if total_balls_faced > 0 else None
        bowl_econ = (total_conceded / (total_balls_bowled / 6)) if total_balls_bowled > 0 else None

        return {
            "matches": n,
            "bat_sr_2026": round(bat_sr, 2) if bat_sr is not None else None,
            "bowl_econ_2026": round(bowl_econ, 2) if bowl_econ is not None else None,
            "total_runs": total_runs,
            "total_wickets": total_wickets
        }
    except Exception as e:
        print(f"❌ [Form2026] Error fetching form for {player_key}: {e}")
        return None


# ── Name resolution ───────────────────────────────────────────────────────────

def _resolve_name(batsman_obj: dict) -> str:
    """
    Return the best key for the player dict.
    Prefer altnames that match our abbreviated format (e.g. 'RG Sharma').
    Falls back to full name.
    """
    full = batsman_obj.get("name", "")
    altnames = batsman_obj.get("altnames", [])

    for alt in altnames:
        parts = alt.split()
        # Abbreviated format: initials + last name (e.g. "RG Sharma", "JJ Bumrah")
        if len(parts) >= 2 and all(len(p) <= 2 for p in parts[:-1]):
            if full:
                _full_to_abbr[full] = alt
            return alt

    if full:
        _full_to_abbr[full] = full
    return full


# ── Scorecard parsing ─────────────────────────────────────────────────────────

def _parse_scorecard(match_id: str, date: str, scorecard: list):
    """Extract per-player batting + bowling and commit to SQLite."""
    seen = {}  # player_key → combined stats for this match

    for inning in scorecard:
        for b in inning.get("batting", []):
            key = _resolve_name(b.get("batsman", {}))
            if not key:
                continue
            entry = seen.setdefault(key, _blank_entry(match_id, date))
            entry["runs"]        += b.get("r", 0)
            entry["balls_faced"] += b.get("b", 0)

        for b in inning.get("bowling", []):
            key = _resolve_name(b.get("bowler", {}))
            if not key:
                continue
            entry = seen.setdefault(key, _blank_entry(match_id, date))
            overs  = float(b.get("o", 0))
            full   = int(overs)
            balls  = round((overs - full) * 10)
            entry["balls_bowled"]   += full * 6 + balls
            entry["runs_conceded"]  += b.get("r", 0)
            entry["wickets"]        += b.get("w", 0)

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for key, entry in seen.items():
            cursor.execute("""
                INSERT OR IGNORE INTO player_match_history_2026 
                (player_name, match_id, date, runs, balls_faced, balls_bowled, runs_conceded, wickets)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                key, match_id, date, entry["runs"], entry["balls_faced"], 
                entry["balls_bowled"], entry["runs_conceded"], entry["wickets"]
            ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ [Form2026] Database write error: {e}")


def _blank_entry(match_id: str, date: str) -> dict:
    return {
        "match_id":      match_id,
        "date":          date,
        "runs":          0,
        "balls_faced":   0,
        "balls_bowled":  0,
        "runs_conceded": 0,
        "wickets":       0,
    }


# ── CricAPI fetch ─────────────────────────────────────────────────────────────

async def _fetch_scorecard(client: httpx.AsyncClient, match_id: str) -> list:
    try:
        r = await client.get(f"{BASE_URL}/match_scorecard",
                             params={"apikey": CRICAPI_KEY, "id": match_id},
                             timeout=12)
        data = r.json()
        if data.get("status") == "success":
            return data.get("data", {}).get("scorecard", [])
    except Exception as e:
        print(f"[Form2026] Scorecard fetch error for {match_id}: {e}")
    return []


async def _fetch_series_matches() -> list:
    """Return all matches in the IPL 2026 series."""
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BASE_URL}/series_info",
                                 params={"apikey": CRICAPI_KEY, "id": SERIES_ID},
                                 timeout=12)
            data = r.json()
            return data.get("data", {}).get("matchList", [])
    except Exception as e:
        print(f"[Form2026] Series fetch error: {e}")
        return []


# ── Public API ────────────────────────────────────────────────────────────────

def get_form(player_key: str) -> dict | None:
    """
    Returns rolling-5 form stats for a player (last 5 IPL 2026 matches).
    player_key can be abbreviated ('V Kohli') or full name ('Virat Kohli').
    Returns None if fewer than 1 match found.
    """
    entries = _form.get(player_key)
    if not entries:
        # Try via full→abbr map
        abbr = _full_to_abbr.get(player_key)
        if abbr:
            entries = _form.get(abbr)
    if not entries:
        return None

    recent = entries[-5:]   # last 5 matches
    n = len(recent)

    total_runs         = sum(e["runs"]         for e in recent)
    total_balls_faced  = sum(e["balls_faced"]  for e in recent)
    total_balls_bowled = sum(e["balls_bowled"] for e in recent)
    total_conceded     = sum(e["runs_conceded"]for e in recent)
    total_wickets      = sum(e["wickets"]      for e in recent)

    bat_sr    = (total_runs / total_balls_faced * 100) if total_balls_faced > 0 else None
    bowl_econ = (total_conceded / (total_balls_bowled / 6)) if total_balls_bowled > 0 else None

    return {
        "matches":          n,
        "bat_sr_2026":      round(bat_sr,    2) if bat_sr    is not None else None,
        "bowl_econ_2026":   round(bowl_econ, 2) if bowl_econ is not None else None,
        "total_runs":       total_runs,
        "total_wickets":    total_wickets,
        "balls_faced":      total_balls_faced,
        "balls_bowled":     total_balls_bowled,
    }


def get_all_players() -> list[str]:
    """All player names currently in the 2026 DB."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT player_name FROM player_match_history_2026")
        names = [r[0] for r in cursor.fetchall()]
        conn.close()
        return names
    except Exception:
        return []


async def refresh_match(match_id: str, date: str):
    """Fetch and store scorecard for one match. Called by live_feed after match ends."""
    logged = _load_logged()
    if match_id in logged:
        return

    async with httpx.AsyncClient() as client:
        scorecard = await _fetch_scorecard(client, match_id)

    if scorecard:
        _parse_scorecard(match_id, date, scorecard)
        logged.add(match_id)
        _save_logged(logged)
        print(f"[Form2026] Logged scorecard {match_id} ({date}) to SQLite")
    else:
        print(f"[Form2026] No scorecard yet for {match_id}")


async def backfill_all():
    """
    On startup: fetch scorecards for all completed IPL 2026 matches not yet logged.
    Runs as a background task.
    """
    if not CRICAPI_KEY:
        print("[Form2026] No API key — skipping backfill")
        return

    matches = await _fetch_series_matches()
    logged  = _load_logged()
    today   = datetime.utcnow().strftime("%Y-%m-%d")

    to_fetch = [
        m for m in matches
        if m.get("id") not in logged
        and m.get("date", "9999") <= today
    ]

    if not to_fetch:
        count = len(logged)
        print(f"[Form2026] All {count} matches already logged")
        return

    print(f"[Form2026] Backfilling {len(to_fetch)} matches...")
    from api.core.live_feed import _increment_budget, _budget_remaining
    async with httpx.AsyncClient() as client:
        for m in to_fetch:
            if _budget_remaining() < 5:
                print(f"[Form2026] Budget low — pausing backfill, {len(to_fetch)} matches remain")
                break
            mid   = m["id"]
            date  = m.get("date", today)
            if not _increment_budget():
                break
            scorecard = await _fetch_scorecard(client, mid)
            if scorecard:
                _parse_scorecard(mid, date, scorecard)
                logged.add(mid)
            await asyncio.sleep(1.0)   # 1 req/sec — stay well under rate limit

    _save_logged(logged)
    print(f"[Form2026] Backfill complete")


def init():
    """Ensure DB exists and schedule backfill."""
    if not os.path.exists(DB_PATH):
        print(f"⚠️ [Form2026] DB missing at {DB_PATH}. Run migration script.")
    else:
        print(f"[Form2026] SQLite Engine Ready")
