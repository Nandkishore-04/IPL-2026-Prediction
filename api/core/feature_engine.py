"""
Feature engine: computes the 42-feature vector for a new match prediction.

For a live prediction, we only need the 18 live features (simpler).
For a pre-match prediction, we need the full 42 features.

Historical stats (win rates, H2H, etc.) are loaded from full_features.csv
and indexed by team/venue for fast O(1) lookup.
"""

import pandas as pd
import numpy as np
import json
import os
from functools import lru_cache

import api.core.player_stats as ps

# ── Precomputed lookup tables (loaded once at startup) ────────────────────────
_team_stats   = {}   # team_name -> {overall_wr, batfirst_wr, ...}
_venue_stats  = {}   # venue -> {batfirst_wr, avg_first_inn}
_h2h_stats    = {}   # (team_a, team_b) -> win_rate
_full_df      = None

HOME_VENUES = {
    "Chennai Super Kings":       "MA Chidambaram Stadium, Chepauk, Chennai",
    "Delhi Capitals":            "Arun Jaitley Stadium, Delhi",
    "Gujarat Titans":            "Narendra Modi Stadium, Ahmedabad",
    "Kolkata Knight Riders":     "Eden Gardens, Kolkata",
    "Lucknow Super Giants":      "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow",
    "Mumbai Indians":            "Wankhede Stadium, Mumbai",
    "Punjab Kings":              "Punjab Cricket Association IS Bindra Stadium, Mohali, Chandigarh",
    "Rajasthan Royals":          "Sawai Mansingh Stadium, Jaipur",
    "Royal Challengers Bengaluru": "M Chinnaswamy Stadium, Bengaluru",
    "Sunrisers Hyderabad":       "Rajiv Gandhi International Stadium, Uppal, Hyderabad",
}


def load():
    """Load historical data and build lookup tables. Called once at startup."""
    global _full_df, _team_stats, _venue_stats, _h2h_stats

    _full_df = pd.read_csv("data/processed/full_features.csv", parse_dates=["date"])

    # ── Team stats ─────────────────────────────────────────────────────────────
    # Use the last 3 seasons worth of data as "current" stats (recency-weighted)
    recent = _full_df[_full_df["season_year"] >= 2022]

    for team in _full_df["team_a"].unique():
        rows = recent[recent["team_a"] == team]
        if len(rows) == 0:
            rows = _full_df[_full_df["team_a"] == team]
        _team_stats[team] = {
            "overall_wr":  float(rows["ta_overall_wr"].iloc[-1])  if len(rows) > 0 else 0.5,
            "batfirst_wr": float(rows["ta_batfirst_wr"].iloc[-1]) if len(rows) > 0 else 0.45,
            "last5_wr":    float(rows["ta_last5_wr"].iloc[-1])    if len(rows) > 0 else 0.5,
            "last5_margin":float(rows["ta_last5_margin"].iloc[-1])if len(rows) > 0 else 15.0,
            "streak":      float(rows["ta_streak"].iloc[-1])      if len(rows) > 0 else 1.0,
            "season_wr":   float(rows["ta_season_wr"].iloc[-1])   if len(rows) > 0 else 0.5,
        }

    # ── Venue stats ─────────────────────────────────────────────────────────────
    for venue in _full_df["venue"].unique():
        rows = _full_df[_full_df["venue"] == venue]
        _venue_stats[venue] = {
            "batfirst_wr":      float(rows["venue_batfirst_wr"].mean()),
            "avg_first_inn":    float(rows["venue_avg_first_inn_score"].mean()),
        }

    # ── H2H win rates ────────────────────────────────────────────────────────────
    for _, row in _full_df.iterrows():
        key = (row["team_a"], row["team_b"])
        _h2h_stats[key] = float(row["ta_h2h_wr"])

    print(f"[FeatureEngine] Loaded. Teams: {len(_team_stats)}, Venues: {len(_venue_stats)}")


def _get_team(team: str) -> dict:
    return _team_stats.get(team, {
        "overall_wr": 0.5, "batfirst_wr": 0.45, "last5_wr": 0.5,
        "last5_margin": 15.0, "streak": 1.0, "season_wr": 0.5,
    })


def _get_venue(venue: str) -> dict:
    return _venue_stats.get(venue, {
        "batfirst_wr": 0.451, "avg_first_inn": 156.0,
    })


def _get_h2h(team_a: str, team_b: str) -> float:
    """Get H2H win rate for team_a vs team_b. Check both orderings."""
    if (team_a, team_b) in _h2h_stats:
        return _h2h_stats[(team_a, team_b)]
    if (team_b, team_a) in _h2h_stats:
        return 1.0 - _h2h_stats[(team_b, team_a)]
    return 0.5


def build_prematch_features(
    team_a: str,
    team_b: str,
    venue: str,
    toss_winner: str,
    toss_decision: str,   # "bat" or "field"
    team_a_xi: list,
    team_b_xi: list,
    match_num_in_season: int = 36,
    is_playoff: int = 0,
    is_day_night: int = 1,
) -> dict:
    """
    Returns a dict of all 42 features for a new match.
    Feature names match feature_cols.json exactly.
    """
    ta = _get_team(team_a)
    tb = _get_team(team_b)
    v  = _get_venue(venue)

    toss_winner_is_ta = 1 if toss_winner == team_a else 0
    toss_decision_bat = 1 if toss_decision == "bat" else 0

    # Home ground flags
    ta_home = 1 if HOME_VENUES.get(team_a, "") == venue else 0
    tb_home = 1 if HOME_VENUES.get(team_b, "") == venue else 0

    # Player features — if XI supplied, compute from stats; else use team defaults
    if team_a_xi:
        bat_a  = ps.aggregate_batting(team_a_xi)
        bowl_a = ps.aggregate_bowling(team_a_xi)
        exp_a  = ps.aggregate_experience(team_a_xi)
    else:
        bat_a  = {"avg_batting_sr": 124.0, "avg_batting_avg": 22.5, "best_batting_avg": 38.8}
        bowl_a = {"avg_bowling_econ": 8.3, "avg_bowling_sr": 22.4, "best_bowling_econ": 7.3}
        exp_a  = {"total_caps": 1025}

    if team_b_xi:
        bat_b  = ps.aggregate_batting(team_b_xi)
        bowl_b = ps.aggregate_bowling(team_b_xi)
        exp_b  = ps.aggregate_experience(team_b_xi)
    else:
        bat_b  = {"avg_batting_sr": 124.0, "avg_batting_avg": 22.5, "best_batting_avg": 38.8}
        bowl_b = {"avg_bowling_econ": 8.3, "avg_bowling_sr": 22.4, "best_bowling_econ": 7.3}
        exp_b  = {"total_caps": 1025}

    # Matchup features — simplified: favorable = batters with high SR
    ta_fav = sum(1 for n in team_a_xi if ps.get_player_stats(n)
                 and ps.get_player_stats(n).get("batting_sr", 0) > 140)
    tb_fav = sum(1 for n in team_b_xi if ps.get_player_stats(n)
                 and ps.get_player_stats(n).get("batting_sr", 0) > 140)
    ta_avg_matchup_sr = bat_a["avg_batting_sr"]
    tb_avg_matchup_sr = bat_b["avg_batting_sr"]

    return {
        "ta_overall_wr":      ta["overall_wr"],
        "tb_overall_wr":      tb["overall_wr"],
        "ta_venue_wr":        ta["overall_wr"],   # venue-specific not precomputed per prediction; use overall as proxy
        "tb_venue_wr":        tb["overall_wr"],
        "ta_h2h_wr":          _get_h2h(team_a, team_b),
        "ta_batfirst_wr":     ta["batfirst_wr"],
        "tb_batfirst_wr":     tb["batfirst_wr"],
        "ta_last5_wr":        ta["last5_wr"],
        "tb_last5_wr":        tb["last5_wr"],
        "ta_last5_margin":    ta["last5_margin"],
        "tb_last5_margin":    tb["last5_margin"],
        "ta_streak":          ta["streak"],
        "tb_streak":          tb["streak"],
        "toss_winner_is_ta":  toss_winner_is_ta,
        "toss_decision_bat":  toss_decision_bat,
        "venue_batfirst_wr":  v["batfirst_wr"],
        "ta_home":            ta_home,
        "tb_home":            tb_home,
        "ta_season_wr":       ta["season_wr"],
        "tb_season_wr":       tb["season_wr"],
        "match_num_in_season":match_num_in_season,
        "is_playoff":         is_playoff,
        "is_day_night":       is_day_night,
        "venue_avg_first_inn_score": v["avg_first_inn"],
        # Team A player features
        "ta_avg_batting_sr":   bat_a["avg_batting_sr"],
        "ta_avg_batting_avg":  bat_a["avg_batting_avg"],
        "ta_best_batting_avg": bat_a["best_batting_avg"],
        "ta_avg_bowling_econ": bowl_a["avg_bowling_econ"],
        "ta_avg_bowling_sr":   bowl_a["avg_bowling_sr"],
        "ta_best_bowling_econ":bowl_a["best_bowling_econ"],
        "ta_total_caps":       exp_a["total_caps"],
        "ta_favorable_matchups": ta_fav,
        "ta_avg_matchup_sr":   ta_avg_matchup_sr,
        # Team B player features
        "tb_avg_batting_sr":   bat_b["avg_batting_sr"],
        "tb_avg_batting_avg":  bat_b["avg_batting_avg"],
        "tb_best_batting_avg": bat_b["best_batting_avg"],
        "tb_avg_bowling_econ": bowl_b["avg_bowling_econ"],
        "tb_avg_bowling_sr":   bowl_b["avg_bowling_sr"],
        "tb_best_bowling_econ":bowl_b["best_bowling_econ"],
        "tb_total_caps":       exp_b["total_caps"],
        "tb_favorable_matchups": tb_fav,
        "tb_avg_matchup_sr":   tb_avg_matchup_sr,
    }


def build_live_features(
    current_score: int,
    wickets: int,
    balls_bowled: int,
    target: int,
    batting_team: str,
    venue: str,
    last6_runs: int = None,
    last6_wickets: int = None,
    dot_pct_last12: float = None,
    partnership_balls: int = None,
    last18_wickets: int = None,
    pp_vs_avg: float = None,
) -> dict:
    """
    Returns dict of 18 live features matching live_feature_cols.json.
    Computes CRR, RRR, run_rate_ratio from the provided match state.
    Momentum features use provided values or sensible defaults.
    """
    runs_remaining  = max(0, target - current_score)
    balls_remaining = max(0, 120 - balls_bowled)
    wickets_in_hand = max(0, 10 - wickets)

    crr = (current_score / balls_bowled * 6) if balls_bowled > 0 else 0.0
    rrr = (runs_remaining / (balls_remaining / 6)) if balls_remaining > 0 else 36.0
    rrr = min(rrr, 36.0)
    run_rate_ratio = min((crr / rrr) if rrr > 0 else 5.0, 5.0)

    # Venue & team chase win rates from precomputed lookup
    vstat = _get_venue(venue)
    venue_chase_wr = 1.0 - vstat["batfirst_wr"]   # if batfirst wins 45%, chase wins 55%

    team_data = _get_team(batting_team)
    # Use last5_wr as proxy for chase win rate (not perfect but reasonable)
    team_chase_wr = team_data["last5_wr"]

    # Momentum defaults based on current state
    if last6_runs is None:
        last6_runs = round(crr * 1.0)   # assume current rate
    if last6_wickets is None:
        last6_wickets = 1 if wickets > 0 else 0
    if dot_pct_last12 is None:
        dot_pct_last12 = 0.30
    if partnership_balls is None:
        partnership_balls = 12
    if last18_wickets is None:
        last18_wickets = min(wickets, 3)
    if pp_vs_avg is None:
        pp_vs_avg = 0.0

    return {
        "cum_runs":         current_score,
        "cum_wickets":      wickets,
        "cum_balls":        balls_bowled,
        "target":           target,
        "runs_remaining":   runs_remaining,
        "balls_remaining":  balls_remaining,
        "wickets_in_hand":  wickets_in_hand,
        "crr":              round(crr, 3),
        "rrr":              round(rrr, 3),
        "run_rate_ratio":   round(run_rate_ratio, 3),
        "venue_chase_wr":   round(venue_chase_wr, 3),
        "team_chase_wr":    round(team_chase_wr, 3),
        "last6_runs":       last6_runs,
        "last6_wickets":    last6_wickets,
        "dot_pct_last12":   dot_pct_last12,
        "partnership_balls":partnership_balls,
        "last18_wickets":   last18_wickets,
        "pp_vs_avg":        pp_vs_avg,
    }
