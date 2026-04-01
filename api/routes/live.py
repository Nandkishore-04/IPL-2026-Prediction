"""
GET  /api/live-feed          — current live match state (from CricAPI or manual)
POST /api/live-feed/manual   — manually update live score (fallback)
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import api.core.live_feed as lf

router = APIRouter()


class ManualScoreUpdate(BaseModel):
    batting_team: str
    bowling_team: str
    current_score: int
    wickets: int
    balls_bowled: int
    target: int


@router.get("/live-feed")
def get_live_feed():
    """Returns current live match state. Frontend polls this every 15s."""
    return lf.get_live_state()


@router.post("/live-feed/manual")
def manual_update(req: ManualScoreUpdate):
    """Manually update score when CricAPI is unavailable."""
    lf.update_manual(
        batting_team=req.batting_team,
        bowling_team=req.bowling_team,
        score=req.current_score,
        wickets=req.wickets,
        balls=req.balls_bowled,
        target=req.target,
    )
    return {"status": "updated", "source": "manual"}
