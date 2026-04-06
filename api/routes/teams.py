"""
GET /api/teams         — list of IPL 2026 teams
GET /api/venues        — list of IPL venues
GET /api/team/{name}/stats — historical stats for one team
"""

import json
import os
import pandas as pd
from fastapi import APIRouter, HTTPException

router = APIRouter()

CURRENT_TEAMS = [
    "Chennai Super Kings",
    "Delhi Capitals",
    "Gujarat Titans",
    "Kolkata Knight Riders",
    "Lucknow Super Giants",
    "Mumbai Indians",
    "Punjab Kings",
    "Rajasthan Royals",
    "Royal Challengers Bengaluru",
    "Sunrisers Hyderabad",
]

_team_stats  = None
_venues_list = None
_squads      = None
_players_list = None   # [{abbr, full_name, ...stats}]


def _load():
    global _team_stats, _venues_list, _squads
    with open("api/data/team_stats.json") as f:
        _team_stats = json.load(f)
    with open("api/data/venues.json") as f:
        _venues_list = json.load(f)
    with open("api/data/squads_2026.json") as f:
        _squads = json.load(f)


@router.get("/players")
def get_players(q: str = "", min_matches: int = 5):
    """
    Returns player list for XI autocomplete.
    q: optional search string (matches full_name or abbr)
    min_matches: filter by minimum career matches
    """
    global _players_list
    if _players_list is None:
        career_path = "data/processed/player_career_ipl.csv"
        if os.path.exists(career_path):
            df = pd.read_csv(career_path)
            _players_list = df[["player", "full_name", "career_matches",
                                 "career_balls_faced", "career_balls_bowled",
                                 "career_bat_sr", "career_bowl_econ"]].to_dict(orient="records")
        else:
            _players_list = []

    results = [
        p for p in _players_list
        if p["career_matches"] >= min_matches
        and (not q or q.lower() in p["full_name"].lower() or q.lower() in p["player"].lower())
    ]
    # Sort by matches descending (most experienced first)
    results = sorted(results, key=lambda x: x["career_matches"], reverse=True)
    return {"players": results[:50]}   # cap at 50 for autocomplete


@router.get("/teams")
def get_teams():
    return {"teams": CURRENT_TEAMS}


@router.get("/venues")
def get_venues():
    if _venues_list is None:
        _load()
    return {"venues": _venues_list}


@router.get("/squads")
def get_squads():
    if _squads is None:
        _load()
    return _squads


@router.get("/team/{name}/stats")
def get_team_stats(name: str):
    if _team_stats is None:
        _load()
    # Normalise URL-encoded spaces
    team = name.replace("%20", " ")
    if team not in _team_stats:
        raise HTTPException(404, f"Team '{team}' not found")
    return {"team": team, "stats": _team_stats[team]}
