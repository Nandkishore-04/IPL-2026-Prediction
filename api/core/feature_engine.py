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
import api.core.season_tracker as st

# ── Precomputed lookup tables (loaded once at startup) ────────────────────────
_team_stats        = {}   # team_name -> {overall_wr, batfirst_wr, ...}
_venue_stats       = {}   # normalized_venue -> {batfirst_wr, avg_first_inn}
_team_venue_stats  = {}   # (team, normalized_venue) -> win_rate
_h2h_stats         = {}   # (team_a, team_b) -> win_rate
_full_df           = None
_career_df         = None  # player_career_ipl.csv indexed by player name
_career_fallbacks  = {}    # batter_sr, bowler_econ, league_exp
_name_map          = {}    # Abbr -> Full
_reverse_name_map  = {}    # Full -> Abbr


# Canonical home ground per team — first segment of the venue string
# (before the first ", ") to match normalized_venue keys
HOME_VENUES = {
    "Chennai Super Kings":          "MA Chidambaram Stadium",
    "Delhi Capitals":               "Arun Jaitley Stadium",
    "Gujarat Titans":               "Narendra Modi Stadium",
    "Kolkata Knight Riders":        "Eden Gardens",
    "Lucknow Super Giants":         "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium",
    "Mumbai Indians":               "Wankhede Stadium",
    "Punjab Kings":                 "Punjab Cricket Association IS Bindra Stadium",
    "Rajasthan Royals":             "Sawai Mansingh Stadium",
    "Royal Challengers Bengaluru":  "M Chinnaswamy Stadium",
    "Sunrisers Hyderabad":          "Rajiv Gandhi International Stadium",
}


def _normalize_venue(venue: str) -> str:
    """Strip city suffix so 'Wankhede Stadium, Mumbai' == 'Wankhede Stadium'."""
    return venue.split(",")[0].strip() if venue else venue


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

    # ── Venue stats (aggregate short + long name variants by normalized key) ────
    for venue in _full_df["venue"].unique():
        rows = _full_df[_full_df["venue"] == venue]
        nv   = _normalize_venue(venue)
        if nv not in _venue_stats:
            _venue_stats[nv] = {"batfirst_wr": [], "avg_first_inn": []}
        _venue_stats[nv]["batfirst_wr"].append(float(rows["venue_batfirst_wr"].mean()))
        _venue_stats[nv]["avg_first_inn"].append(float(rows["venue_avg_first_inn_score"].mean()))
    # Average across variants
    _venue_stats.update({
        nv: {
            "batfirst_wr":   float(np.mean(v["batfirst_wr"])),
            "avg_first_inn": float(np.mean(v["avg_first_inn"])),
        }
        for nv, v in _venue_stats.items()
    })

    # ── Team-venue win rates ──────────────────────────────────────────────────
    # For every match: team_a win (team_a_won=1) or team_b win (team_a_won=0)
    # Aggregate by (team, normalized_venue) across both orderings.
    wins  = {}  # (team, nv) -> wins
    total = {}  # (team, nv) -> total
    for _, row in _full_df.iterrows():
        nv = _normalize_venue(row["venue"])
        won_a = int(row["team_a_won"])
        for team, won in [(row["team_a"], won_a), (row["team_b"], 1 - won_a)]:
            k = (team, nv)
            wins[k]  = wins.get(k, 0) + won
            total[k] = total.get(k, 0) + 1
    for k in total:
        if total[k] >= 3:
            _team_venue_stats[k] = wins[k] / total[k]

    # ── H2H win rates ────────────────────────────────────────────────────────────
    for _, row in _full_df.iterrows():
        key = (row["team_a"], row["team_b"])
        _h2h_stats[key] = float(row["ta_h2h_wr"])

    # ── Player career stats (for runtime XI computation) ──────────────────────
    global _career_df, _career_fallbacks
    career_path = "data/processed/player_career_ipl.csv"
    if os.path.exists(career_path):
        _career_df = pd.read_csv(career_path).set_index("player")
        batters = _career_df[_career_df["career_balls_faced"] >= 100]
        bowlers = _career_df[_career_df["career_balls_bowled"] >= 100]
        _career_fallbacks = {
            "batter_sr":   float(batters["career_bat_sr"].median()) if len(batters) > 0 else 124.0,
            "bowler_econ": float(bowlers["career_bowl_econ"].median()) if len(bowlers) > 0 else 8.3,
            "league_exp":  float(_career_df["career_matches"].median()),
        }

    # ── Player name mapping ───────────────────────────────────────────────────
    global _name_map, _reverse_name_map
    map_path = "data/processed/player_name_map.json"
    if os.path.exists(map_path):
        with open(map_path, "r") as f:
            _name_map = json.load(f)
            # Reverse map: Full Name -> Abbreviated Name
            # If multiple abbreviations map to the same full name, the last one wins (usually correct)
            _reverse_name_map = {v: k for k, v in _name_map.items()}

    print(f"[FeatureEngine] Loaded. Teams: {len(_team_stats)}, Venues: {len(_venue_stats)}, Players: {len(_career_df) if _career_df is not None else 0}, Mappings: {len(_name_map)}")



def _get_team(team: str) -> dict:
    return _team_stats.get(team, {
        "overall_wr": 0.5, "batfirst_wr": 0.45, "last5_wr": 0.5,
        "last5_margin": 15.0, "streak": 1.0, "season_wr": 0.5,
    })


def _get_venue(venue: str) -> dict:
    """Lookup by normalized venue key so short/long forms both resolve."""
    nv = _normalize_venue(venue)
    return _venue_stats.get(nv, {
        "batfirst_wr": 0.47, "avg_first_inn": 165.0,
    })


def _get_team_venue_wr(team: str, venue: str) -> float | None:
    """Win rate for team at this venue. Returns None if < 3 matches."""
    nv = _normalize_venue(venue)
    return _team_venue_stats.get((team, nv))


def _compute_xi_quality(xi: list, use_2026_form: bool = True) -> dict:
    """
    Compute XI quality stats from player_career_ipl.csv.
    Mirrors build_player_features.py logic (rules 11-14) for runtime use.
    Returns xi_bat_sr, xi_bowl_econ, xi_experience, xi_ar_ratio.
    """
    if _career_df is None or not xi:
        return {
            "xi_bat_sr":    _career_fallbacks.get("batter_sr", 124.0),
            "xi_bowl_econ": _career_fallbacks.get("bowler_econ", 8.3),
            "xi_experience":_career_fallbacks.get("league_exp", 20.0),
            "xi_ar_ratio":  0.0,
        }

    fb_sr   = _career_fallbacks.get("batter_sr",   124.0)
    fb_econ = _career_fallbacks.get("bowler_econ",  8.3)
    fb_exp  = _career_fallbacks.get("league_exp",   20.0)
    MIN_MATCHES = 5

    def get_stat(player, col, fallback):
        # Normalize: if player is a full name, map back to abbreviation
        abbr = _reverse_name_map.get(player, player)
        if abbr not in _career_df.index:
            return fallback
        row = _career_df.loc[abbr]
        if row.get("career_matches", 0) < MIN_MATCHES:
            return fallback
        val = row.get(col, fallback)
        return fallback if (pd.isna(val) or np.isinf(val)) else float(val)

    # Normalize the entire XI list for sorting
    xi_normalized = [_reverse_name_map.get(p, p) for p in xi]

    # Rule 11: top-6 batters by career_balls_faced
    bat_sorted = sorted(
        xi_normalized,
        key=lambda p: float(_career_df.loc[p, "career_balls_faced"]) if p in _career_df.index else 0,
        reverse=True,
    )
    top6 = bat_sorted[:6]
    # Optionally blend in 2026 in-season form (weight: 60% 2026, 40% career)
    import api.core.player_form_2026 as pf2026

    def get_bat_sr(player):
        career_sr = get_stat(player, "blend_bat_sr", fb_sr)
        if not use_2026_form:
            return career_sr
        form = pf2026.get_form(player)
        if form and form["bat_sr_2026"] is not None and form["matches"] >= 2:
            return 0.6 * form["bat_sr_2026"] + 0.4 * career_sr
        return career_sr

    def get_bowl_econ(player):
        career_econ = get_stat(player, "blend_bowl_econ", fb_econ)
        if not use_2026_form:
            return career_econ
        form = pf2026.get_form(player)
        if form and form["bowl_econ_2026"] is not None and form["matches"] >= 2:
            return 0.6 * form["bowl_econ_2026"] + 0.4 * career_econ
        return career_econ

    bat_srs = [get_bat_sr(p) for p in top6]

    # Rule 12: top-5 bowlers by career_balls_bowled (who actually bowled)
    bowl_sorted = sorted(
        xi_normalized,
        key=lambda p: float(_career_df.loc[p, "career_balls_bowled"]) if p in _career_df.index else 0,
        reverse=True,
    )

    top5 = [p for p in bowl_sorted
            if p in _career_df.index and _career_df.loc[p, "career_balls_bowled"] > 0][:5]
    if not top5:
        top5 = bowl_sorted[:5]
    bowl_econs = [get_bowl_econ(p) for p in top5]

    # Rule 13: experience (all XI)
    exps = [get_stat(p, "career_matches", fb_exp) for p in xi_normalized]

    # Rule 14: allrounder ratio (≥60 career balls each role)
    ar_count = sum(
        1 for p in xi_normalized
        if p in _career_df.index
        and _career_df.loc[p, "career_balls_faced"]  >= 60
        and _career_df.loc[p, "career_balls_bowled"] >= 60
    )
    ar_ratio = ar_count / max(len(xi_normalized), 1)

    return {
        "xi_bat_sr":     float(np.mean(bat_srs))   if bat_srs   else fb_sr,
        "xi_bowl_econ":  float(np.mean(bowl_econs)) if bowl_econs else fb_econ,
        "xi_experience": float(np.mean(exps))       if exps      else fb_exp,
        "xi_ar_ratio":   ar_ratio,
    }



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
    use_2026_form: bool = True,
) -> dict:
    """
    Returns a dict of all features for a new match.
    Feature names match feature_cols.json exactly.

    use_2026_form=False: skip the 2026 season-tracker override (used for
    retroactive predictions where 2026 data wasn't available at match time).
    """
    ta = _get_team(team_a)
    tb = _get_team(team_b)
    v  = _get_venue(venue)

    # ── 2026 live form override ───────────────────────────────────────────────
    form_a = st.get_team_form(team_a) if use_2026_form else None
    form_b = st.get_team_form(team_b) if use_2026_form else None

    if form_a:
        ta = dict(ta)   # don't mutate the cached dict
        # Use EMA form as the primary form signal (recency-weighted)
        ta["last5_wr"]  = form_a.get("ema_form", form_a["last5_wr"])
        ta["season_wr"] = form_a["season_wr"]
        ta["streak"]    = form_a["streak"]
        match_num_in_season = form_a["match_num_in_season"]

    if form_b:
        tb = dict(tb)
        tb["last5_wr"]  = form_b.get("ema_form", form_b["last5_wr"])
        tb["season_wr"] = form_b["season_wr"]
        tb["streak"]    = form_b["streak"]

    toss_winner_is_ta = 1 if toss_winner == team_a else 0
    toss_decision_bat = 1 if toss_decision == "bat" else 0

    # Home ground flags — compare normalized venue keys
    nv = _normalize_venue(venue)
    ta_home = 1 if HOME_VENUES.get(team_a, "") == nv else 0
    tb_home = 1 if HOME_VENUES.get(team_b, "") == nv else 0

    # Venue-specific team win rates (fall back to overall if < 3 matches at venue)
    ta_venue_wr = _get_team_venue_wr(team_a, venue)
    if ta_venue_wr is None:
        ta_venue_wr = ta["overall_wr"]
    tb_venue_wr = _get_team_venue_wr(team_b, venue)
    if tb_venue_wr is None:
        tb_venue_wr = tb["overall_wr"]

    # ── XI quality (from player_career_ipl.csv) ───────────────────────────────
    qa = _compute_xi_quality(team_a_xi or [])
    qb = _compute_xi_quality(team_b_xi or [])

    xi_bat_sr_diff    = qa["xi_bat_sr"]    - qb["xi_bat_sr"]
    xi_bowl_econ_diff = qb["xi_bowl_econ"] - qa["xi_bowl_econ"]   # +ve = A cheaper
    xi_exp_diff       = qa["xi_experience"] - qb["xi_experience"]
    xi_ar_ratio_diff  = qa["xi_ar_ratio"]  - qb["xi_ar_ratio"]

    return {
        # Differential features (model v2 — fixes multicollinearity sign-flip)
        "form_wr_diff":       ta["last5_wr"]    - tb["last5_wr"],
        "form_margin_diff":   ta["last5_margin"] - tb["last5_margin"],
        "overall_wr_diff":    ta["overall_wr"]  - tb["overall_wr"],
        "venue_wr_diff":      ta_venue_wr       - tb_venue_wr,
        "batfirst_wr_diff":   ta["batfirst_wr"] - tb["batfirst_wr"],
        "season_wr_diff":     ta["season_wr"]   - tb["season_wr"],

        # XI quality differential
        "xi_bat_sr_diff":     xi_bat_sr_diff,
        "xi_bowl_econ_diff":  xi_bowl_econ_diff,
        "xi_exp_diff":        xi_exp_diff,
        "xi_ar_ratio_diff":   xi_ar_ratio_diff,

        # Singleton features
        "ta_h2h_wr":          _get_h2h(team_a, team_b),
        "tb_streak":          tb["streak"],
        "toss_winner_is_ta":  toss_winner_is_ta,
        "toss_decision_bat":  toss_decision_bat,
        "venue_batfirst_wr":  v["batfirst_wr"],
        "venue_avg_first_inn_score": v["avg_first_inn"],
        "ta_home":            ta_home,
        "tb_home":            tb_home,
        "match_num_in_season":match_num_in_season,
        "is_playoff":         is_playoff,
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
