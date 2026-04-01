"""
Phase 8: Build Live Model Training Data
Reconstructs match state after every ball in the 2nd innings.
Run from project root: python src/build_live_data.py
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

print('Loading data...')
balls = pd.read_csv('data/processed/cleaned_balls.csv',
                    parse_dates=['date'], low_memory=False)

# Only use regular innings (1 and 2) — exclude super overs (innings 3+)
balls = balls[balls['innings'].isin([1, 2])].copy()

# ── Step 1: Compute first innings total per match ────────────────────────────
print('Computing first innings totals...')
first_inn = (
    balls[balls['innings'] == 1]
    .groupby('match_id')['runs_total']
    .sum()
    .reset_index()
    .rename(columns={'runs_total': 'first_inn_total'})
)

# ── Step 2: Get venue chase win rates (historical, for feature 11) ───────────
print('Computing venue chase win rates...')
matches = pd.read_csv('data/processed/cleaned_matches.csv', parse_dates=['date'])

# Get innings1 team (batted first) per match
inn1_teams = (
    balls[balls['innings'] == 1][['match_id','batting_team']]
    .drop_duplicates(subset='match_id')
    .rename(columns={'batting_team': 'batting_first_team'})
)
matches = matches.merge(inn1_teams, on='match_id', how='left')
# Chase win = team that batted second won
matches['chase_win'] = (matches['winner'] != matches['batting_first_team']).astype(int)

venue_chase_wr = (
    matches.groupby('venue')['chase_win']
    .mean()
    .reset_index()
    .rename(columns={'chase_win': 'venue_chase_wr'})
)

# ── Step 3: Get team chase win rates (historical) ────────────────────────────
print('Computing team chase win rates...')
# Team that chased = team that batted in innings 2
inn2_teams = (
    balls[balls['innings'] == 2][['match_id','batting_team']]
    .drop_duplicates(subset='match_id')
    .rename(columns={'batting_team': 'chasing_team'})
)
matches = matches.merge(inn2_teams, on='match_id', how='left')
matches['chasing_team_won'] = (matches['winner'] == matches['chasing_team']).astype(int)

team_chase_wr = (
    matches.groupby('chasing_team')['chasing_team_won']
    .mean()
    .reset_index()
    .rename(columns={'chasing_team': 'batting_team', 'chasing_team_won': 'team_chase_wr'})
)

# ── Step 4: Build ball-by-ball state for 2nd innings ────────────────────────
print('Building ball-by-ball states...')

inn2 = balls[balls['innings'] == 2].copy()

# Merge in target (first innings total)
inn2 = inn2.merge(first_inn, on='match_id', how='left')

# Merge venue and date from matches
# drop venue from inn2 first to avoid _x/_y suffix conflict (cleaned_balls already has venue)
inn2 = inn2.drop(columns=['venue', 'date'], errors='ignore')
match_meta = matches[['match_id','date','venue','winner','chasing_team','chasing_team_won']].copy()
inn2 = inn2.merge(match_meta, on='match_id', how='left')

# Merge venue chase win rate
inn2 = inn2.merge(venue_chase_wr, on='venue', how='left')
inn2['venue_chase_wr'] = inn2['venue_chase_wr'].fillna(0.5)

# Merge team chase win rate
inn2 = inn2.merge(team_chase_wr, on='batting_team', how='left')
inn2['team_chase_wr'] = inn2['team_chase_wr'].fillna(0.5)

# Sort by match and ball order
inn2 = inn2.sort_values(['match_id', 'over', 'ball']).reset_index(drop=True)

# ── Step 5: Compute cumulative stats per match ───────────────────────────────
print('Computing cumulative match state per ball...')

# Cumulative runs and wickets within each match's 2nd innings
inn2['cum_runs']    = inn2.groupby('match_id')['runs_total'].cumsum()
inn2['cum_wickets'] = inn2.groupby('match_id')['is_wicket'].cumsum()
inn2['cum_balls']   = inn2.groupby('match_id')['valid_ball'].cumsum()

# ── Step 6: Compute momentum features ───────────────────────────────────────
print('Computing momentum features...')

# Last 6 balls runs (rolling window within each match)
inn2['last6_runs'] = (
    inn2.groupby('match_id')['runs_total']
    .transform(lambda x: x.rolling(6, min_periods=1).sum())
)

# Last 6 balls wickets
inn2['last6_wickets'] = (
    inn2.groupby('match_id')['is_wicket']
    .transform(lambda x: x.rolling(6, min_periods=1).sum())
)

# Dot ball % in last 12 balls
inn2['is_dot'] = ((inn2['runs_total'] == 0) & (inn2['valid_ball'] == 1)).astype(int)
inn2['last12_dots'] = (
    inn2.groupby('match_id')['is_dot']
    .transform(lambda x: x.rolling(12, min_periods=1).sum())
)
inn2['last12_balls'] = (
    inn2.groupby('match_id')['valid_ball']
    .transform(lambda x: x.rolling(12, min_periods=1).sum())
)
inn2['dot_pct_last12'] = (inn2['last12_dots'] / inn2['last12_balls'].replace(0, 1)).round(3)

# Current partnership length (balls since last wicket)
def partnership_balls(wicket_series):
    """Count balls since the last wicket for each ball."""
    result = []
    count  = 0
    for w in wicket_series:
        count += 1
        if w == 1:
            count = 0
        result.append(count)
    return result

inn2['partnership_balls'] = inn2.groupby('match_id')['is_wicket'].transform(
    lambda x: partnership_balls(x.tolist())
)

# Wickets in last 3 overs (18 balls)
inn2['last18_wickets'] = (
    inn2.groupby('match_id')['is_wicket']
    .transform(lambda x: x.rolling(18, min_periods=1).sum())
)

# Powerplay score vs venue average (over 1-6 = balls 1-36)
pp_avg = (
    inn2[inn2['cum_balls'] <= 36]
    .groupby(['match_id','venue'])['runs_total']
    .sum()
    .reset_index()
    .rename(columns={'runs_total': 'pp_score'})
)
venue_pp_avg = pp_avg.groupby('venue')['pp_score'].mean().reset_index()
venue_pp_avg.columns = ['venue', 'venue_avg_pp']
pp_avg = pp_avg.merge(venue_pp_avg, on='venue', how='left')
pp_avg['pp_vs_avg'] = pp_avg['pp_score'] - pp_avg['venue_avg_pp']

# Merge powerplay comparison back — it's per match, broadcast after over 6
inn2 = inn2.merge(pp_avg[['match_id','pp_vs_avg']].drop_duplicates(), on='match_id', how='left')
inn2['pp_vs_avg'] = inn2['pp_vs_avg'].fillna(0)

# ── Step 7: Derive all live features ────────────────────────────────────────
print('Building feature rows...')

# Only snapshot after each VALID ball (ignore wides/no-balls for state)
snapshot = inn2[inn2['valid_ball'] == 1].copy()

snapshot['target']           = snapshot['first_inn_total'] + 1
snapshot['runs_remaining']   = snapshot['target'] - snapshot['cum_runs']
snapshot['balls_remaining']  = 120 - snapshot['cum_balls']
snapshot['wickets_in_hand']  = 10  - snapshot['cum_wickets']
snapshot['crr']              = (snapshot['cum_runs'] /
                                 snapshot['cum_balls'].replace(0, np.nan) * 6).round(3)
snapshot['rrr']              = (snapshot['runs_remaining'] /
                                 (snapshot['balls_remaining'] / 6).replace(0, np.nan)).round(3)
snapshot['run_rate_ratio']   = (snapshot['crr'] /
                                 snapshot['rrr'].replace(0, np.nan)).round(3)

# Clip extreme values
snapshot['rrr']            = snapshot['rrr'].clip(0, 36)
snapshot['run_rate_ratio'] = snapshot['run_rate_ratio'].clip(0, 5)

# Drop rows where match is already won/lost (target already reached or 10 wickets)
snapshot = snapshot[
    (snapshot['runs_remaining'] > 0) &
    (snapshot['wickets_in_hand'] > 0) &
    (snapshot['balls_remaining'] > 0)
].copy()

# ── Step 8: Build final dataset ──────────────────────────────────────────────
live_data = snapshot[[
    # Base features
    'match_id', 'date', 'cum_runs', 'cum_wickets', 'cum_balls',
    'target', 'runs_remaining', 'balls_remaining', 'wickets_in_hand',
    'crr', 'rrr', 'run_rate_ratio',
    'venue_chase_wr', 'team_chase_wr',
    # Momentum features
    'last6_runs', 'last6_wickets',
    'dot_pct_last12', 'partnership_balls',
    'last18_wickets', 'pp_vs_avg',
    # Target
    'chasing_team_won'
]].copy()

# Drop rows with any nulls
live_data = live_data.dropna().reset_index(drop=True)

print(f'\n=== LIVE MODEL DATA SUMMARY ===')
print(f'Total ball snapshots : {len(live_data):,}')
print(f'Unique matches       : {live_data["match_id"].nunique():,}')
print(f'Avg balls per match  : {len(live_data)/live_data["match_id"].nunique():.0f}')
print(f'Chase win rate       : {live_data["chasing_team_won"].mean():.1%}')
print(f'Features             : {live_data.shape[1] - 3} (excl. match_id, date, target)')

# Class imbalance check
print(f'\nClass distribution:')
print(live_data['chasing_team_won'].value_counts())

live_data.to_csv('data/processed/live_model_data.csv', index=False)
print(f'\nSaved: data/processed/live_model_data.csv')
print('Phase 8 complete.')
