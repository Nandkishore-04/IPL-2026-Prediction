"""Pydantic schemas for pre-match prediction requests/responses."""

from pydantic import BaseModel, Field
from typing import Optional, List


class MatchPredictionRequest(BaseModel):
    team_a: str = Field(..., example="Mumbai Indians")
    team_b: str = Field(..., example="Chennai Super Kings")
    venue: str = Field(..., example="Wankhede Stadium, Mumbai")
    toss_winner: str = Field(..., example="Mumbai Indians")
    toss_decision: str = Field(..., example="bat")  # "bat" or "field"
    team_a_xi: List[str] = Field(default=[], example=["Rohit Sharma", "Ishan Kishan"])
    team_b_xi: List[str] = Field(default=[], example=["MS Dhoni", "Ruturaj Gaikwad"])


class TeamPrediction(BaseModel):
    team: str
    win_probability: float
    win_percent: str


class MatchPredictionResponse(BaseModel):
    team_a: TeamPrediction
    team_b: TeamPrediction
    predicted_winner: str
    confidence: str          # "Low", "Medium", "High"
    key_factors: List[str]   # top reasons for prediction
