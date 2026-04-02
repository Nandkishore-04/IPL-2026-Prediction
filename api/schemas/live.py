"""Pydantic schemas for live win probability requests/responses."""

from pydantic import BaseModel, Field
from typing import Optional


class LivePredictionRequest(BaseModel):
    batting_team: str = Field(..., example="Mumbai Indians")
    bowling_team: str = Field(..., example="Chennai Super Kings")
    venue: str = Field(..., example="Wankhede Stadium, Mumbai")
    current_score: int = Field(..., ge=0, example=98)
    wickets: int = Field(..., ge=0, le=10, example=3)
    balls_bowled: int = Field(..., ge=0, le=120, example=66)
    target: int = Field(..., ge=1, example=185)
    last6_runs: Optional[int] = Field(default=None, ge=0, example=42)
    last6_wickets: Optional[int] = Field(default=None, ge=0, example=1)
    dot_pct_last12: Optional[float] = Field(default=None, ge=0.0, le=1.0, example=0.33)
    partnership_balls: Optional[int] = Field(default=None, ge=0, example=18)
    last18_wickets: Optional[int] = Field(default=None, ge=0, example=2)
    pp_vs_avg: Optional[float] = Field(default=None, example=5.0)


class LivePredictionResponse(BaseModel):
    batting_team: str
    bowling_team: str
    batting_team_win_prob: float
    bowling_team_win_prob: float
    batting_team_win_percent: str
    bowling_team_win_percent: str
    current_score: int
    wickets: int
    balls_bowled: int
    target: int
    runs_remaining: int
    balls_remaining: int
    crr: float    # current run rate
    rrr: float    # required run rate
    match_situation: str   # "comfortable", "evenly poised", "under pressure", "critical"


class LogResultRequest(BaseModel):
    match_id: str
    team_a: str
    team_b: str
    predicted_winner: str
    actual_winner: str
    match_date: str
    predicted_probability: Optional[float] = None   # e.g. 0.67 — stored for calibration
