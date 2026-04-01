"""
GET /api/teams         — list of IPL 2026 teams
GET /api/venues        — list of IPL venues
GET /api/team/{name}/stats — historical stats for one team
"""

import json
import os
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


def _load():
    global _team_stats, _venues_list
    with open("api/data/team_stats.json") as f:
        _team_stats = json.load(f)
    with open("api/data/venues.json") as f:
        _venues_list = json.load(f)


@router.get("/teams")
def get_teams():
    return {"teams": CURRENT_TEAMS}


@router.get("/venues")
def get_venues():
    if _venues_list is None:
        _load()
    return {"venues": _venues_list}


@router.get("/team/{name}/stats")
def get_team_stats(name: str):
    if _team_stats is None:
        _load()
    # Normalise URL-encoded spaces
    team = name.replace("%20", " ")
    if team not in _team_stats:
        raise HTTPException(404, f"Team '{team}' not found")
    return {"team": team, "stats": _team_stats[team]}
