"""
CricAPI live feed integration — credit-efficient match-window polling.

Strategy (saves ~90% of API credits vs 90s polling):
  - Sleep until next match window (3:20 PM IST or 7:20 PM IST)
  - Once inside a window, poll every 5 min until matchEnded = True
  - On match end → log result + fetch scorecard once → sleep until next window
  - Handles rain delays / overruns naturally (keeps polling until truly ended)

Match windows (IST = UTC+5:30):
  Weekday  : 7:30 PM IST (14:00 UTC) — one evening match
  Weekend  : 3:30 PM IST (10:00 UTC) + 7:30 PM IST (14:00 UTC)

API calls per match: ~30-50  (vs ~400 with 90s polling)
"""

import os
import json
import asyncio
import httpx
import re
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

CRICAPI_KEY  = os.getenv("CRICAPI_KEY", "")
CRICAPI_URL  = "https://api.cricapi.com/v1/currentMatches"

# Poll every 5 min while a match window is active
ACTIVE_POLL_INTERVAL = 300   # seconds
# How early to wake before scheduled match start (so we catch toss + first ball)
WAKEUP_BEFORE = timedelta(minutes=10)

IST = timezone(timedelta(hours=5, minutes=30))

# Shared live state — read by /live-feed endpoint
_live_state = {
    "status":        "no_live_match",
    "match_title":   None,
    "batting_team":  None,
    "bowling_team":  None,
    "current_score": None,
    "wickets":       None,
    "balls_bowled":  None,
    "target":        None,
    "last_updated":  None,
    "source":        "manual",
    "raw":           None,
}

_polling_active  = False
_LOGGED_IDS_FILE = "api/data/auto_logged_ids.json"
_BUDGET_FILE     = "api/data/api_call_budget.json"
DAILY_CALL_LIMIT = 90   # keep 10 buffer below the 100 cap


def _load_budget() -> dict:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    try:
        with open(_BUDGET_FILE) as f:
            b = json.load(f)
        if b.get("date") != today:
            return {"date": today, "calls": 0}
        return b
    except Exception:
        return {"date": today, "calls": 0}


def _increment_budget() -> bool:
    """Increment call counter. Returns False if daily limit reached."""
    b = _load_budget()
    if b["calls"] >= DAILY_CALL_LIMIT:
        print(f"[LiveFeed] Daily API budget exhausted ({b['calls']}/{DAILY_CALL_LIMIT}) — skipping poll")
        return False
    b["calls"] += 1
    with open(_BUDGET_FILE, "w") as f:
        json.dump(b, f)
    return True


def _budget_remaining() -> int:
    b = _load_budget()
    return max(0, DAILY_CALL_LIMIT - b["calls"])


def _load_logged_ids() -> set:
    try:
        with open(_LOGGED_IDS_FILE) as f:
            return set(json.load(f))
    except Exception:
        return set()


def _save_logged_ids(ids: set):
    with open(_LOGGED_IDS_FILE, "w") as f:
        json.dump(list(ids), f)


_auto_logged_ids = _load_logged_ids()


# ── Match window logic ────────────────────────────────────────────────────────

def _match_windows_today(now_ist: datetime) -> list[datetime]:
    """
    Return scheduled match start times (IST) for today.
    Weekend: 3:30 PM + 7:30 PM
    Weekday: 7:30 PM only
    """
    # weekday(): 0=Mon … 5=Sat, 6=Sun
    weekday = now_ist.weekday()
    evening = now_ist.replace(hour=19, minute=30, second=0, microsecond=0)
    if weekday in (5, 6):   # Sat, Sun
        afternoon = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
        return [afternoon, evening]
    return [evening]


def _seconds_to_next_window() -> float:
    """
    Seconds until the next match window wakeup.
    Returns 0 if we're currently inside a window (match may be live or just ended).
    """
    now_ist = datetime.now(IST)
    today_windows = _match_windows_today(now_ist)

    # Check tomorrow's windows too (in case it's after tonight's match)
    tomorrow_ist = now_ist + timedelta(days=1)
    tomorrow_windows = _match_windows_today(tomorrow_ist)

    all_wakeups = [w - WAKEUP_BEFORE for w in today_windows + tomorrow_windows]

    for wakeup in sorted(all_wakeups):
        # A window is "active" for up to 5 hours after match start
        window_close = wakeup + timedelta(hours=5)
        if wakeup <= now_ist <= window_close:
            return 0   # currently inside a window
        if wakeup > now_ist:
            delta = (wakeup - now_ist).total_seconds()
            return delta

    # Fallback: sleep 1 hour and re-check
    return 3600


# ── Parsing helpers ───────────────────────────────────────────────────────────

def _parse_overs(overs_str) -> int:
    try:
        overs = float(str(overs_str))
        full  = int(overs)
        balls = round((overs - full) * 10)
        return full * 6 + balls
    except Exception:
        return 0


def _extract_winner(status: str, teams: list) -> str | None:
    status = status.strip()
    for team in teams:
        if team.lower() in status.lower() and "won" in status.lower():
            return team
    m = re.match(r"^(.+?)\s+won\b", status, re.IGNORECASE)
    if m:
        candidate = m.group(1).strip()
        for team in teams:
            if candidate.lower() in team.lower() or team.lower() in candidate.lower():
                return team
    return None


# ── Result logging ────────────────────────────────────────────────────────────

def _auto_log_result(match: dict):
    """Log a completed IPL match to season_tracker, predictions_log, and player form."""
    from api.core.season_tracker import log_match
    from api.core import auto_predictor

    match_id = match.get("id", "")
    if match_id in _auto_logged_ids:
        return

    teams  = match.get("teams", [])
    status = match.get("status", "")
    winner = _extract_winner(status, teams)

    if not winner or len(teams) < 2:
        return

    team_a = teams[0]
    team_b = teams[1]
    venue  = match.get("venue", "")
    date   = match.get("date", datetime.utcnow().strftime("%Y-%m-%d"))

    log_match(team_a, team_b, winner, date, venue)

    # Update existing prediction entry with actual result (or create bare entry)
    updated = auto_predictor.mark_result(team_a, team_b, date, winner)
    if not updated:
        # No prediction was made before the match — create a result-only entry
        logs = []
        try:
            with open("api/data/predictions_log.json") as f:
                logs = json.load(f)
        except Exception:
            pass
        match_key = auto_predictor.make_match_key(team_a, team_b, date)
        if not any(e.get("match_id") == match_key for e in logs):
            logs.append({
                "match_id":              match_key,
                "team_a":                team_a,
                "team_b":                team_b,
                "actual_winner":         winner,
                "match_date":            date,
                "venue":                 venue,
                "predicted_winner":      None,
                "predicted_probability": None,
                "correct":               None,
                "source":                "cricapi_auto",
            })
            with open("api/data/predictions_log.json", "w") as f:
                json.dump(logs, f, indent=2)

    _auto_logged_ids.add(match_id)
    _save_logged_ids(_auto_logged_ids)
    print(f"[LiveFeed] Result logged: {team_a} vs {team_b} -> {winner} ({date})")

    # Fetch scorecard once and update 2026 player form
    import api.core.player_form_2026 as pf
    asyncio.create_task(pf.refresh_match(match_id, date))


# ── Auto-predict on match detection ──────────────────────────────────────────

_auto_predicted_cricapi_ids: set = set()

def _auto_predict_live_match(match: dict):
    """Called once when a live match is first detected — makes the pre-match prediction."""
    from api.core import auto_predictor

    cricapi_id = match.get("id", "")
    if cricapi_id in _auto_predicted_cricapi_ids:
        return   # already predicted this match

    teams = match.get("teams", [])
    if len(teams) < 2:
        return

    team_a = teams[0]
    team_b = teams[1]
    venue  = match.get("venue", "")
    date   = match.get("date", datetime.utcnow().strftime("%Y-%m-%d"))

    auto_predictor.predict_and_store(
        team_a=team_a, team_b=team_b, venue=venue, date=date,
        toss_winner=None, toss_decision="bat",   # toss not yet in API feed
        cricapi_match_id=cricapi_id,
        use_2026_form=True,
        source="auto_predictor_live",
    )
    _auto_predicted_cricapi_ids.add(cricapi_id)


# ── Single poll ───────────────────────────────────────────────────────────────

async def poll_once() -> bool:
    """
    Poll CricAPI once.
    Returns True if a live IPL match is still in progress (keep polling).
    Returns False if no live match found (window may be over, or match just ended).
    """
    global _live_state

    if not CRICAPI_KEY:
        _live_state["status"] = "api_unavailable"
        return False

    if not _increment_budget():
        return False   # budget exhausted, stop polling for today

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(CRICAPI_URL, params={"apikey": CRICAPI_KEY, "offset": 0})

        if resp.status_code != 200:
            _live_state["status"] = "api_unavailable"
            return False

        body = resp.json()
        if body.get("status") != "success":
            _live_state["status"] = "api_unavailable"
            return False

        matches = body.get("data", [])
        ipl_matches = [
            m for m in matches
            if "indian premier league" in m.get("name", "").lower()
            and m.get("matchType", "").lower() == "t20"
        ]

        # Log any just-ended matches
        for m in ipl_matches:
            if m.get("matchEnded"):
                _auto_log_result(m)

        # Find live (not yet ended) match
        live = next(
            (m for m in ipl_matches if not m.get("matchEnded") and m.get("matchStarted")),
            None,
        )

        # Auto-predict when a match is first detected (before or at start)
        if live is not None:
            _auto_predict_live_match(live)

        if live is None:
            _live_state["status"] = "no_live_match"
            _live_state["last_updated"] = datetime.utcnow().isoformat()
            # Check if any match started but not ended — might still be in progress
            # (API sometimes lags). Return True only if window is still open.
            return _seconds_to_next_window() == 0

        # Update live state for Live Tracker
        scores  = live.get("score", [])
        inning1 = scores[0] if scores else None
        inning2 = scores[1] if len(scores) > 1 else None

        if inning2:
            runs  = inning2.get("r", 0)
            wkts  = inning2.get("w", 0)
            balls = _parse_overs(inning2.get("o", 0))
        elif inning1:
            runs  = inning1.get("r", 0)
            wkts  = inning1.get("w", 0)
            balls = _parse_overs(inning1.get("o", 0))
        else:
            runs = wkts = balls = 0

        target = (inning1.get("r", 0) + 1) if (inning1 and inning2) else 0
        teams  = live.get("teams", ["", ""])

        _live_state.update({
            "status":        "live",
            "match_title":   live.get("name"),
            "batting_team":  teams[1] if len(teams) > 1 else "",
            "bowling_team":  teams[0],
            "current_score": runs,
            "wickets":       wkts,
            "balls_bowled":  balls,
            "target":        target,
            "last_updated":  datetime.utcnow().isoformat(),
            "source":        "cricapi",
            "raw":           live,
        })
        return True   # match still live → keep polling

    except Exception as e:
        _live_state["status"] = "api_unavailable"
        _live_state["last_updated"] = datetime.utcnow().isoformat()
        print(f"[LiveFeed] Poll error: {e}")
        return False


# ── Main polling loop ─────────────────────────────────────────────────────────

async def polling_loop():
    """
    Smart polling loop:
      1. Calculate seconds to next match window
      2. Sleep until 10 min before match start
      3. Poll every 5 min until match ends
      4. Repeat
    """
    global _polling_active
    _polling_active = True

    while _polling_active:
        wait = _seconds_to_next_window()

        if wait > 60:
            now_ist = datetime.now(IST).strftime("%H:%M IST")
            print(f"[LiveFeed] No match window active ({now_ist}). "
                  f"Next wakeup in {wait/3600:.1f}h")
            # Sleep in chunks so we can respond to shutdown quickly
            slept = 0
            while slept < wait and _polling_active:
                chunk = min(60, wait - slept)
                await asyncio.sleep(chunk)
                slept += chunk
            continue

        # Inside a match window — poll until match ends
        print(f"[LiveFeed] Match window active — polling every {ACTIVE_POLL_INTERVAL}s")
        match_still_live = True
        consecutive_no_match = 0

        while _polling_active and match_still_live:
            match_still_live = await poll_once()

            if not match_still_live:
                consecutive_no_match += 1
                # Give it 3 more checks (15 min) before declaring window closed
                # handles API lag after match ends
                if consecutive_no_match >= 3:
                    print("[LiveFeed] Match ended or window closed — sleeping until next window")
                    break
            else:
                consecutive_no_match = 0

            await asyncio.sleep(ACTIVE_POLL_INTERVAL)


# ── Public interface ──────────────────────────────────────────────────────────

def get_live_state() -> dict:
    return dict(_live_state)


def update_manual(batting_team: str, bowling_team: str, score: int,
                  wickets: int, balls: int, target: int):
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
