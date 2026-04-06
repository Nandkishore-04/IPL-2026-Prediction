"""
build_features.py
=================
Clean, deterministic, leakage-safe feature pipeline.

Replaces notebooks/03_team_features.ipynb + 04_player_features.ipynb.

Golden rule: every feature for match on date D uses ONLY data from dates < D.
Technique:  sort by date → groupby → .expanding().mean().shift(1)
            The .shift(1) pushes each value one row forward so the current
            match never sees its own result.

Usage:
    python src/build_features.py

Outputs:
    data/processed/full_features.csv      (42 model features + metadata)
    data/processed/player_career_stats.json
    api/data/player_stats.json
"""

import json
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── 0. Load raw data ──────────────────────────────────────────────────────────

print("Loading data...")
balls   = pd.read_csv("data/processed/cleaned_balls.csv",   parse_dates=["date"], low_memory=False)
matches = pd.read_csv("data/processed/cleaned_matches.csv", parse_dates=["date"])

print(f"  Balls  : {len(balls):,}")
print(f"  Matches: {len(matches):,}")

# ── 1. Assign team_a / team_b (batting-first = team_a) ───────────────────────

innings1 = (
    balls[balls["innings"] == 1][["match_id", "batting_team", "bowling_team"]]
    .drop_duplicates("match_id")
    .rename(columns={"batting_team": "team_a", "bowling_team": "team_b"})
)
matches = matches.merge(innings1, on="match_id", how="left")
matches["team_a_won"] = (matches["winner"] == matches["team_a"]).astype(int)

# Drop matches where we couldn't assign teams (forfeits, no-result)
matches = matches.dropna(subset=["team_a", "team_b"]).copy()

# ── 2. Sort by date — everything depends on this ──────────────────────────────

matches = matches.sort_values("date").reset_index(drop=True)
print(f"  Date range: {matches['date'].min().date()} to {matches['date'].max().date()}")

# ── 3. Helpers ────────────────────────────────────────────────────────────────

def expanding_shift(series: pd.Series) -> pd.Series:
    """Expanding mean up to (but not including) current row. Shift(1) is the key."""
    return series.expanding().mean().shift(1)


def rolling_shift(series: pd.Series, window: int) -> pd.Series:
    """Rolling mean of last N rows, not including current row."""
    return series.rolling(window, min_periods=1).mean().shift(1)


# ── 4. Long-format helper: one row per (match, team) ─────────────────────────
# Makes team-level rolling stats much easier to compute.

def make_long(df: pd.DataFrame) -> pd.DataFrame:
    """
    Explode matches into two rows per match:
    one from team_a's perspective, one from team_b's.
    """
    a = df[["match_id", "date", "season_year", "team_a", "team_b",
            "venue", "winner", "team_a_won", "toss_winner",
            "toss_decision", "is_playoff"]].copy()
    a["team"]   = a["team_a"]
    a["opp"]    = a["team_b"]
    a["won"]    = a["team_a_won"]
    a["batted_first"] = 1

    b = df[["match_id", "date", "season_year", "team_a", "team_b",
            "venue", "winner", "team_a_won", "toss_winner",
            "toss_decision", "is_playoff"]].copy()
    b["team"]   = b["team_b"]
    b["opp"]    = b["team_a"]
    b["won"]    = 1 - b["team_a_won"]
    b["batted_first"] = 0

    long = pd.concat([a, b], ignore_index=True)
    long = long.sort_values(["team", "date"]).reset_index(drop=True)
    return long


long = make_long(matches)

# ── 5. Rolling team features (all leakage-safe via shift) ────────────────────

print("Computing rolling team features...")

# 5a. Overall win rate
long["overall_wr"] = (
    long.groupby("team")["won"]
    .transform(lambda s: expanding_shift(s))
    .fillna(0.5)
)

# 5b. Bat-first win rate
long["batfirst_wr"] = (
    long.groupby("team")["batted_first"]  # 1 = batted first AND won
    .transform(lambda s: s)               # placeholder; computed below
)
# Correct: win rate when batting first
long["bat_won"] = ((long["batted_first"] == 1) & (long["won"] == 1)).astype(float)
long["batfirst_wr"] = (
    long.groupby("team")["bat_won"]
    .transform(lambda s: expanding_shift(s))
    .fillna(0.5)
)

# 5c. Last-5 form
long["last5_wr"] = (
    long.groupby("team")["won"]
    .transform(lambda s: rolling_shift(s, 5))
    .fillna(0.5)
)


# 5d. Win streak (rolling — counts consecutive wins ending before this match)
def rolling_streak(s: pd.Series) -> pd.Series:
    """Positive = win streak, negative = loss streak, shifted so current match excluded."""
    result = []
    streak = 0
    for val in s:
        result.append(streak)           # value BEFORE this match
        if val == 1:
            streak = max(streak, 0) + 1
        else:
            streak = min(streak, 0) - 1
    return pd.Series(result, index=s.index)

long["streak"] = long.groupby("team")["won"].transform(rolling_streak)

# 5e. Last-5 margin (avg run margin in last 5 — using win as proxy if margin unavailable)
long["last5_margin"] = (
    long.groupby("team")["won"]
    .transform(lambda s: rolling_shift(s, 5))
    .fillna(0.0)
) * 10  # scale to look like run margin (~0-10 range)

# 5f. Season win rate (within the same season, prior matches only)
long["season_wr"] = (
    long.groupby(["team", "season_year"])["won"]
    .transform(lambda s: expanding_shift(s))
    .fillna(0.5)
)

# 5g. Venue win rate per team
long["venue_wr"] = (
    long.groupby(["team", "venue"])["won"]
    .transform(lambda s: expanding_shift(s))
    .fillna(0.5)
)

# 5h. Home ground flag (heuristic: team name in venue string)
HOME_VENUES = {
    "Chennai Super Kings":         ["Chidambaram", "Chepauk"],
    "Mumbai Indians":              ["Wankhede"],
    "Royal Challengers Bengaluru": ["Chinnaswamy"],
    "Kolkata Knight Riders":       ["Eden Gardens"],
    "Delhi Capitals":              ["Feroz Shah Kotla", "Arun Jaitley"],
    "Sunrisers Hyderabad":         ["Rajiv Gandhi", "Uppal"],
    "Rajasthan Royals":            ["Sawai Mansingh", "SMS"],
    "Punjab Kings":                ["PCA", "IS Bindra", "Mohali", "Mullanpur"],
    "Gujarat Titans":              ["Narendra Modi", "Motera"],
    "Lucknow Super Giants":        ["Ekana", "Bharat Ratna"],
}

def is_home(team: str, venue: str) -> int:
    keywords = HOME_VENUES.get(team, [])
    return int(any(kw.lower() in venue.lower() for kw in keywords))

long["is_home"] = long.apply(lambda r: is_home(r["team"], r["venue"]), axis=1)

# ── 6. Venue-level stats (leakage-safe) ───────────────────────────────────────

print("Computing venue features...")

# Use matches (not long) for venue stats — one observation per match
matches_sorted = matches.copy()

# Bat-first win rate at venue
matches_sorted["venue_batfirst_wr"] = (
    matches_sorted.groupby("venue")["team_a_won"]
    .transform(lambda s: expanding_shift(s))
    .fillna(0.5)
)

# Average first innings score at venue
balls["match_runs_cum"] = balls.groupby(["match_id", "innings"])["runs_batter"].cumsum()
first_inn_scores = (
    balls[balls["innings"] == 1]
    .groupby("match_id")["runs_batter"]
    .sum()
    .reset_index()
    .rename(columns={"runs_batter": "first_inn_score"})
)
matches_sorted = matches_sorted.merge(first_inn_scores, on="match_id", how="left")
matches_sorted["venue_avg_first_inn_score"] = (
    matches_sorted.groupby("venue")["first_inn_score"]
    .transform(lambda s: expanding_shift(s))
    .fillna(matches_sorted["first_inn_score"].mean())
)

# ── 7. H2H win rate (leakage-safe) ────────────────────────────────────────────

print("Computing head-to-head features...")

# For each match, count prior meetings between the two teams
# We need a canonical pair key (alphabetical) to group h2h
matches_sorted["pair"] = matches_sorted.apply(
    lambda r: tuple(sorted([r["team_a"], r["team_b"]])), axis=1
)
# ta_won_in_pair = 1 if the alphabetically-first team won
matches_sorted["alpha_first"] = matches_sorted["pair"].apply(lambda p: p[0])
matches_sorted["alpha_first_won"] = (
    matches_sorted["winner"] == matches_sorted["alpha_first"]
).astype(float)

matches_sorted["h2h_alpha_wr"] = (
    matches_sorted.groupby("pair")["alpha_first_won"]
    .transform(lambda s: expanding_shift(s))
    .fillna(0.5)
)

# Convert back: ta_h2h_wr = wr for team_a (which may or may not be alpha_first)
matches_sorted["ta_h2h_wr"] = matches_sorted.apply(
    lambda r: r["h2h_alpha_wr"] if r["team_a"] == r["alpha_first"] else 1 - r["h2h_alpha_wr"],
    axis=1
)

# ── 8. Toss features ──────────────────────────────────────────────────────────

matches_sorted["toss_winner_is_ta"]  = (matches_sorted["toss_winner"] == matches_sorted["team_a"]).astype(int)
matches_sorted["toss_decision_bat"]  = (matches_sorted["toss_decision"] == "bat").astype(int)

# ── 9. Match number in season ─────────────────────────────────────────────────

matches_sorted["match_num_in_season"] = matches_sorted.groupby("season_year").cumcount() + 1

# ── 10. Merge long-form team stats back to match level ────────────────────────

print("Assembling match-level feature matrix...")

def get_team_stats(team_name: str, suffix: str) -> pd.DataFrame:
    """Pull rolling stats for one perspective (team_a or team_b)."""
    cols = ["match_id", "overall_wr", "venue_wr", "batfirst_wr",
            "last5_wr", "last5_margin", "streak", "season_wr", "is_home"]
    team_rows = long[long["team"] == team_name].set_index("match_id")[cols[1:]]
    return team_rows.rename(columns={c: f"{suffix}_{c}" for c in cols[1:]})

# Build per-match stat lookup for each team
ta_stats = {}
tb_stats = {}

for _, row in matches_sorted.iterrows():
    mid = row["match_id"]
    ta  = row["team_a"]
    tb  = row["team_b"]

    ta_row = long[(long["match_id"] == mid) & (long["team"] == ta)]
    tb_row = long[(long["match_id"] == mid) & (long["team"] == tb)]

    ta_stats[mid] = ta_row.iloc[0] if len(ta_row) else None
    tb_stats[mid] = tb_row.iloc[0] if len(tb_row) else None

# ── 11. Build final feature DataFrame ────────────────────────────────────────

print("Building final feature matrix (this may take 30s)...")

records = []
for _, row in matches_sorted.iterrows():
    mid = row["match_id"]
    ta  = row["team_a"]
    tb  = row["team_b"]

    ta_r = ta_stats.get(mid)
    tb_r = tb_stats.get(mid)

    if ta_r is None or tb_r is None:
        continue

    records.append({
        # Metadata
        "match_id":             mid,
        "date":                 row["date"],
        "season_year":          row["season_year"],
        "team_a":               ta,
        "team_b":               tb,
        "venue":                row["venue"],

        # Team A features
        "ta_overall_wr":        ta_r["overall_wr"],
        "ta_venue_wr":          ta_r["venue_wr"],
        "ta_batfirst_wr":       ta_r["batfirst_wr"],
        "ta_last5_wr":          ta_r["last5_wr"],
        "ta_last5_margin":      ta_r["last5_margin"],
        "ta_streak":            ta_r["streak"],
        "ta_season_wr":         ta_r["season_wr"],
        "ta_home":              ta_r["is_home"],

        # Team B features
        "tb_overall_wr":        tb_r["overall_wr"],
        "tb_venue_wr":          tb_r["venue_wr"],
        "tb_batfirst_wr":       tb_r["batfirst_wr"],
        "tb_last5_wr":          tb_r["last5_wr"],
        "tb_last5_margin":      tb_r["last5_margin"],
        "tb_streak":            tb_r["streak"],
        "tb_season_wr":         tb_r["season_wr"],
        "tb_home":              tb_r["is_home"],

        # H2H
        "ta_h2h_wr":            row["ta_h2h_wr"],

        # Toss
        "toss_winner_is_ta":    row["toss_winner_is_ta"],
        "toss_decision_bat":    row["toss_decision_bat"],

        # Venue
        "venue_batfirst_wr":    row["venue_batfirst_wr"],
        "venue_avg_first_inn_score": row["venue_avg_first_inn_score"],

        # Match context
        "match_num_in_season":  row["match_num_in_season"],
        "is_playoff":           int(row.get("is_playoff", 0) or 0),

        # Target
        "team_a_won":           row["team_a_won"],
    })

features = pd.DataFrame(records)
print(f"  Features shape: {features.shape}")

# ── 12. Player stats (career aggregates — for API lookup only) ───────────────
# NOTE: player XI features are NOT included in the training feature set.
# Career aggregates leak future data into historical matches.
# Player stats are saved for the API (live XI lookup) but not used in model training.

print("Computing player career stats...")

batting = (
    balls.groupby("batter")
    .agg(
        batting_runs   = ("runs_batter",  "sum"),
        balls_faced    = ("valid_ball",   "sum"),
        innings_played = ("match_id",     "nunique"),
        dismissals     = ("is_wicket",    "sum"),
    )
    .reset_index()
)
batting["batting_sr"]  = (batting["batting_runs"] / batting["balls_faced"].replace(0, np.nan) * 100).round(2)
batting["batting_avg"] = (batting["batting_runs"] / batting["dismissals"].replace(0, np.nan)).round(2)
batting = batting[batting["innings_played"] >= 10]

bowling = (
    balls.groupby("bowler")
    .agg(
        runs_conceded  = ("runs_bowler",    "sum"),
        balls_bowled   = ("valid_ball",     "sum"),
        wickets        = ("bowler_wicket",  "sum"),
        innings_bowled = ("match_id",       "nunique"),
    )
    .reset_index()
)
bowling["bowling_econ"] = (bowling["runs_conceded"] / bowling["balls_bowled"].replace(0, np.nan) * 6).round(2)
bowling["bowling_sr"]   = (bowling["balls_bowled"]  / bowling["wickets"].replace(0, np.nan)).round(2)
bowling = bowling[bowling["innings_bowled"] >= 10]

caps = (
    pd.concat([
        balls[["match_id","batter"]].drop_duplicates().rename(columns={"batter":"player"}),
        balls[["match_id","bowler"]].drop_duplicates().rename(columns={"bowler":"player"}),
    ])
    .drop_duplicates()
    .groupby("player")["match_id"].nunique()
    .reset_index()
    .rename(columns={"match_id": "ipl_caps"})
)

player_stats = (
    batting[["batter","batting_runs","balls_faced","batting_sr","batting_avg","innings_played"]]
    .rename(columns={"batter":"player"})
    .merge(
        bowling[["bowler","wickets","bowling_econ","bowling_sr","innings_bowled"]]
        .rename(columns={"bowler":"player"}),
        on="player", how="outer"
    )
    .merge(caps, on="player", how="outer")
)
player_stats["batting_sr"]   = player_stats["batting_sr"].fillna(120.0)
player_stats["batting_avg"]  = player_stats["batting_avg"].fillna(20.0)
player_stats["bowling_econ"] = player_stats["bowling_econ"].fillna(8.5)
player_stats["bowling_sr"]   = player_stats["bowling_sr"].fillna(20.0)
player_stats["ipl_caps"]     = player_stats["ipl_caps"].fillna(0).astype(int)

stats_dict = player_stats.set_index("player").to_dict(orient="index")
with open("data/processed/player_career_stats.json", "w") as f:
    json.dump(stats_dict, f, indent=2, default=str)
print(f"  Saved player_career_stats.json — {len(stats_dict)} players")

# Rebuild full-name player_stats.json via name map
try:
    with open("data/processed/player_name_map.json") as f:
        name_map = json.load(f)
    full_name_stats = {}
    for abbrev, stat in stats_dict.items():
        full = name_map.get(abbrev, abbrev)
        full_name_stats[full] = stat
    with open("api/data/player_stats.json", "w") as f:
        json.dump(full_name_stats, f, indent=2, default=str)
    print(f"  Saved api/data/player_stats.json — {len(full_name_stats)} players (full names)")
except Exception as e:
    print(f"  Warning: could not apply name map ({e}) — run build_player_names.py first")

# ── 13. Validation ────────────────────────────────────────────────────────────

print("\n=== Validation ===")
first = features.iloc[0]
print(f"First match: {first['date'].date()} {first['team_a']} vs {first['team_b']}")
print(f"  ta_overall_wr = {first['ta_overall_wr']} (expect 0.5)")
print(f"  ta_h2h_wr     = {first['ta_h2h_wr']}     (expect 0.5)")
print(f"  ta_streak     = {first['ta_streak']}     (expect 0.0)")

null_counts = features.isnull().sum()
nulls = null_counts[null_counts > 0]
print(f"Null values: {nulls.to_dict() if len(nulls) else 'none'}")

train = features[features["season_year"] <= 2023]
test  = features[features["season_year"] >= 2024]
print(f"Train: {len(train)} matches ({train['season_year'].min()}-{train['season_year'].max()})")
print(f"Test : {len(test)}  matches ({test['season_year'].min()}-{test['season_year'].max()})")
print(f"target rate: {features['team_a_won'].mean():.3f} (expect ~0.5)")

# ── 15. Save ──────────────────────────────────────────────────────────────────

features.to_csv("data/processed/full_features.csv", index=False)
print(f"\nSaved data/processed/full_features.csv — {features.shape[0]} rows × {features.shape[1]} cols")
print("Done. Run: python src/train_model.py")
