"""
CricAPI live feed integration.
Polls the CricAPI every 90 seconds during match hours to get live score.
Stores the latest score state so the frontend can poll /api/live-feed.
"""

import os
import json
import asyncio
import httpx
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

CRICAPI_KEY = os.getenv("CRICAPI_KEY", "")
CRICAPI_URL = "https://api.cricapi.com/v1/currentMatches"
POLL_INTERVAL = 90  # seconds (keeps usage under 100 calls/day for one match)

# Shared state — updated by the background task, read by the /live-feed endpoint
_live_state = {
    "status": "no_live_match",   # "no_live_match" | "live" | "api_unavailable"
    "match_title": None,
    "batting_team": None,
    "bowling_team": None,
    "current_score": None,
    "wickets": None,
    "balls_bowled": None,
    "target": None,
    "last_updated": None,
    "source": "manual",          # "cricapi" | "manual"
    "raw": None,                 # last raw API response for debugging
}

_polling_active = False


def _is_match_hour() -> bool:
    """Only poll during likely IPL match windows (IST 14:00–23:59)."""
    now = datetime.utcnow()
    # IST = UTC+5:30 → 14:00 IST = 08:30 UTC, 24:00 IST = 18:30 UTC
    hour_utc = now.hour
    return 8 <= hour_utc <= 18


def _parse_score(score_str: str) -> tuple:
    """Parse '98/3' into (98, 3). Returns (0, 0) on failure."""
    try:
        runs, wkts = score_str.strip().split("/")
        return int(runs), int(wkts)
    except Exception:
        return 0, 0


def _parse_overs(overs_str) -> int:
    """Parse '11.2' overs into balls bowled = 68."""
    try:
        overs = float(str(overs_str))
        full  = int(overs)
        balls = round((overs - full) * 10)
        return full * 6 + balls
    except Exception:
        return 0


def _extract_ipl_match(data: list) -> dict | None:
    """Find the first live IPL T20 match in the API response."""
    for match in data:
        name = match.get("name", "").lower()
        if "indian premier" not in name and "ipl" not in name:
            continue
        if match.get("matchType", "").lower() != "t20":
            continue
        return match
    return None


async def poll_once():
    """Fetch live score from CricAPI and update _live_state."""
    global _live_state

    if not CRICAPI_KEY:
        _live_state["status"] = "api_unavailable"
        _live_state["source"] = "manual"
        return

    params = {"apikey": CRICAPI_KEY, "offset": 0}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(CRICAPI_URL, params=params)
        if resp.status_code != 200:
            _live_state["status"] = "api_unavailable"
            return

        body = resp.json()
        if body.get("status") != "success":
            _live_state["status"] = "api_unavailable"
            return

        matches = body.get("data", [])
        ipl = _extract_ipl_match(matches)
        if ipl is None:
            _live_state["status"] = "no_live_match"
            _live_state["last_updated"] = datetime.utcnow().isoformat()
            return

        # Parse score
        scores = ipl.get("score", [])
        # Find the 2nd innings score (index 1 if it exists)
        inning2 = scores[1] if len(scores) > 1 else (scores[0] if scores else None)
        if inning2:
            runs, wkts = _parse_score(f"{inning2.get('r', 0)}/{inning2.get('w', 0)}")
            balls = _parse_overs(inning2.get("o", 0))
        else:
            runs, wkts, balls = 0, 0, 0

        # Target = 1st innings score + 1
        inning1 = scores[0] if scores else None
        target = (inning1.get("r", 0) + 1) if inning1 else 0

        _live_state.update({
            "status":       "live",
            "match_title":  ipl.get("name"),
            "batting_team": ipl.get("t2", ""),   # team batting in 2nd innings
            "bowling_team": ipl.get("t1", ""),
            "current_score":runs,
            "wickets":      wkts,
            "balls_bowled": balls,
            "target":       target,
            "last_updated": datetime.utcnow().isoformat(),
            "source":       "cricapi",
            "raw":          ipl,
        })

    except Exception as e:
        _live_state["status"] = "api_unavailable"
        _live_state["last_updated"] = datetime.utcnow().isoformat()
        print(f"[LiveFeed] Poll error: {e}")


async def polling_loop():
    """Background loop — polls every 90 seconds during match hours."""
    global _polling_active
    _polling_active = True
    print("[LiveFeed] Polling loop started")
    while _polling_active:
        if _is_match_hour():
            await poll_once()
        await asyncio.sleep(POLL_INTERVAL)


def get_live_state() -> dict:
    return dict(_live_state)


def update_manual(batting_team: str, bowling_team: str, score: int,
                  wickets: int, balls: int, target: int):
    """Allow manual score update (fallback when API is unavailable)."""
    _live_state.update({
        "status":        "live",
        "batting_team":  batting_team,
        "bowling_team":  bowling_team,
        "current_score": score,
        "wickets":       wickets,
        "balls_bowled":  balls,
        "target":        target,
        "last_updated":  datetime.utcnow().isoformat(),
        "source":        "manual",
    })
