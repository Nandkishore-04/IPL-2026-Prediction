"""
POST /api/predict-match   — pre-match winner prediction
POST /api/predict-live    — live ball-by-ball win probability
"""

import numpy as np
from fastapi import APIRouter, HTTPException

from api.schemas.match import MatchPredictionRequest, MatchPredictionResponse, TeamPrediction
from api.schemas.live  import LivePredictionRequest, LivePredictionResponse
import api.core.model_loader  as ml
import api.core.feature_engine as fe

router = APIRouter()


def _confidence_label(prob: float) -> str:
    """Map win probability to human-readable confidence level."""
    gap = abs(prob - 0.5)
    if gap < 0.08:
        return "Low"
    if gap < 0.18:
        return "Medium"
    return "High"


def _key_factors(features: dict, team_a: str, team_b: str) -> list:
    """Generate top 3 plain-English reasons for the prediction."""
    reasons = []

    wr_diff = features["ta_overall_wr"] - features["tb_overall_wr"]
    if abs(wr_diff) > 0.05:
        favoured = team_a if wr_diff > 0 else team_b
        reasons.append(f"{favoured} has a stronger overall win record")

    h2h = features["ta_h2h_wr"]
    if abs(h2h - 0.5) > 0.1:
        favoured = team_a if h2h > 0.5 else team_b
        reasons.append(f"{favoured} leads the head-to-head record")

    if features["ta_home"] == 1:
        reasons.append(f"{team_a} is playing at their home ground")
    elif features["tb_home"] == 1:
        reasons.append(f"{team_b} is playing at their home ground")

    # Toss advantage if venue favours bat-first
    if features["toss_winner_is_ta"] == 1 and features["toss_decision_bat"] == 1:
        if features["venue_batfirst_wr"] > 0.52:
            reasons.append(f"{team_a} won toss & chose to bat — venue favours batting first")
    elif features["toss_winner_is_ta"] == 0 and features["toss_decision_bat"] == 0:
        if features["venue_batfirst_wr"] < 0.48:
            reasons.append(f"{team_b} won toss & chose to field — venue favours chasing")

    form_a = features["ta_last5_wr"]
    form_b = features["tb_last5_wr"]
    if abs(form_a - form_b) > 0.2:
        favoured = team_a if form_a > form_b else team_b
        reasons.append(f"{favoured} is in better recent form (last 5 matches)")

    bowl_a = features["ta_avg_bowling_econ"]
    bowl_b = features["tb_avg_bowling_econ"]
    if abs(bowl_a - bowl_b) > 0.5:
        favoured = team_a if bowl_a < bowl_b else team_b
        reasons.append(f"{favoured}'s bowling attack has a better economy rate")

    return reasons[:4] if reasons else ["Closely matched teams — prediction is uncertain"]


@router.post("/predict-match", response_model=MatchPredictionResponse)
def predict_match(req: MatchPredictionRequest):
    """
    Pre-match prediction.
    Builds a 42-feature vector from the request, scales it, and runs
    the Logistic Regression model. Returns win probabilities for both teams.
    """
    model   = ml.get_pre_match_model()
    scaler  = ml.get_pre_match_scaler()
    feature_cols = ml.get_feature_cols()

    if model is None:
        raise HTTPException(500, "Models not loaded")

    # Build feature dict
    feat_dict = fe.build_prematch_features(
        team_a       = req.team_a,
        team_b       = req.team_b,
        venue        = req.venue,
        toss_winner  = req.toss_winner,
        toss_decision= req.toss_decision,
        team_a_xi    = req.team_a_xi,
        team_b_xi    = req.team_b_xi,
    )

    # Build ordered numpy array matching feature_cols
    X = np.array([[feat_dict[c] for c in feature_cols]])
    X_scaled = scaler.transform(X)

    proba = model.predict_proba(X_scaled)[0]
    ta_prob = float(proba[1])   # index 1 = team_a wins
    tb_prob = 1.0 - ta_prob

    predicted_winner = req.team_a if ta_prob >= 0.5 else req.team_b
    confidence = _confidence_label(ta_prob)
    factors = _key_factors(feat_dict, req.team_a, req.team_b)

    return MatchPredictionResponse(
        team_a=TeamPrediction(
            team=req.team_a,
            win_probability=round(ta_prob, 4),
            win_percent=f"{ta_prob*100:.1f}%",
        ),
        team_b=TeamPrediction(
            team=req.team_b,
            win_probability=round(tb_prob, 4),
            win_percent=f"{tb_prob*100:.1f}%",
        ),
        predicted_winner=predicted_winner,
        confidence=confidence,
        key_factors=factors,
    )


def _match_situation(runs_remaining: int, balls_remaining: int,
                     wickets_in_hand: int, rrr: float) -> str:
    if wickets_in_hand <= 2:
        return "critical"
    if rrr > 14 or (rrr > 12 and balls_remaining < 24):
        return "under pressure"
    if rrr < 8 and wickets_in_hand >= 6:
        return "comfortable"
    return "evenly poised"


@router.post("/predict-live", response_model=LivePredictionResponse)
def predict_live(req: LivePredictionRequest):
    """
    Live win probability.
    Builds 18 live features from current match state and runs Random Forest model.
    """
    model  = ml.get_live_model()
    scaler = ml.get_live_scaler()
    feat_cols = ml.get_live_feature_cols()

    if model is None:
        raise HTTPException(500, "Live model not loaded")

    feat_dict = fe.build_live_features(
        current_score    = req.current_score,
        wickets          = req.wickets,
        balls_bowled     = req.balls_bowled,
        target           = req.target,
        batting_team     = req.batting_team,
        venue            = req.venue,
        last6_runs       = req.last6_runs,
        last6_wickets    = req.last6_wickets,
        dot_pct_last12   = req.dot_pct_last12,
        partnership_balls= req.partnership_balls,
        last18_wickets   = req.last18_wickets,
        pp_vs_avg        = req.pp_vs_avg,
    )

    X = np.array([[feat_dict[c] for c in feat_cols]])

    # Live model is Random Forest — no scaling needed
    # (live_scaler is StandardScaler but RF doesn't need it; we keep it for LR fallback)
    from api.core.model_loader import get_live_model
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    if isinstance(model, LogisticRegression):
        X = scaler.transform(X)

    proba = model.predict_proba(X)[0]
    bat_prob  = float(proba[1])   # chasing team wins
    bowl_prob = 1.0 - bat_prob

    runs_remaining  = max(0, req.target - req.current_score)
    balls_remaining = max(0, 120 - req.balls_bowled)
    wickets_in_hand = max(0, 10  - req.wickets)
    crr = round(feat_dict["crr"], 2)
    rrr = round(feat_dict["rrr"], 2)

    situation = _match_situation(runs_remaining, balls_remaining, wickets_in_hand, rrr)

    return LivePredictionResponse(
        batting_team=req.batting_team,
        bowling_team=req.bowling_team,
        batting_team_win_prob=round(bat_prob,  4),
        bowling_team_win_prob=round(bowl_prob, 4),
        batting_team_win_percent=f"{bat_prob*100:.1f}%",
        bowling_team_win_percent=f"{bowl_prob*100:.1f}%",
        current_score=req.current_score,
        wickets=req.wickets,
        balls_bowled=req.balls_bowled,
        target=req.target,
        runs_remaining=runs_remaining,
        balls_remaining=balls_remaining,
        crr=crr,
        rrr=rrr,
        match_situation=situation,
    )
