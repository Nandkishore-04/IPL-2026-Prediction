"""
Unit tests for feature_engine.py
Run from project root: python -m pytest tests/ -v
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import warnings
warnings.filterwarnings('ignore')

import api.core.model_loader   as ml
import api.core.feature_engine as fe
import api.core.player_stats   as ps


@pytest.fixture(scope='module', autouse=True)
def load_all():
    """Load models and data once for all tests."""
    ml.load_all()
    fe.load()
    ps.load()


class TestLiveFeatures:
    def test_basic_state(self):
        """Basic live feature computation."""
        f = fe.build_live_features(
            current_score=100, wickets=3, balls_bowled=72,
            target=180, batting_team='Mumbai Indians', venue=''
        )
        assert f['runs_remaining'] == 80
        assert f['balls_remaining'] == 48
        assert f['wickets_in_hand'] == 7
        assert f['cum_runs'] == 100
        assert f['target'] == 180

    def test_crr_rrr(self):
        """CRR and RRR calculated correctly."""
        f = fe.build_live_features(
            current_score=60, wickets=0, balls_bowled=36,
            target=161, batting_team='Chennai Super Kings', venue=''
        )
        # CRR = 60/36*6 = 10.0
        assert abs(f['crr'] - 10.0) < 0.1
        # RRR = 101 / (84/6) = 101/14 = 7.21
        assert abs(f['rrr'] - 7.21) < 0.2

    def test_run_rate_ratio(self):
        """run_rate_ratio = CRR / RRR, capped at 5."""
        f = fe.build_live_features(
            current_score=150, wickets=1, balls_bowled=100,
            target=160, batting_team='Mumbai Indians', venue=''
        )
        assert f['run_rate_ratio'] <= 5.0
        assert f['run_rate_ratio'] >= 0

    def test_rrr_capped(self):
        """RRR capped at 36 when very few balls remain."""
        f = fe.build_live_features(
            current_score=10, wickets=9, balls_bowled=119,
            target=200, batting_team='Mumbai Indians', venue=''
        )
        assert f['rrr'] <= 36.0

    def test_all_18_features_present(self):
        """All 18 expected feature keys are in output."""
        import json
        with open('models/live_feature_cols.json') as fh:
            expected = json.load(fh)
        f = fe.build_live_features(
            current_score=80, wickets=2, balls_bowled=60,
            target=160, batting_team='Mumbai Indians', venue=''
        )
        for col in expected:
            assert col in f, f"Missing live feature: {col}"


class TestPreMatchFeatures:
    def test_all_42_features_present(self):
        """All 42 expected feature keys are in output."""
        import json
        with open('models/feature_cols.json') as fh:
            expected = json.load(fh)
        f = fe.build_prematch_features(
            team_a='Mumbai Indians', team_b='Chennai Super Kings',
            venue='Wankhede Stadium, Mumbai', toss_winner='Mumbai Indians',
            toss_decision='bat', team_a_xi=[], team_b_xi=[]
        )
        for col in expected:
            assert col in f, f"Missing prematch feature: {col}"

    def test_toss_flag_correct(self):
        """toss_winner_is_ta = 1 when team_a wins toss."""
        f = fe.build_prematch_features(
            team_a='Mumbai Indians', team_b='Chennai Super Kings',
            venue='', toss_winner='Mumbai Indians',
            toss_decision='bat', team_a_xi=[], team_b_xi=[]
        )
        assert f['toss_winner_is_ta'] == 1
        assert f['toss_decision_bat'] == 1

    def test_toss_flag_team_b(self):
        """toss_winner_is_ta = 0 when team_b wins toss."""
        f = fe.build_prematch_features(
            team_a='Mumbai Indians', team_b='Chennai Super Kings',
            venue='', toss_winner='Chennai Super Kings',
            toss_decision='field', team_a_xi=[], team_b_xi=[]
        )
        assert f['toss_winner_is_ta'] == 0
        assert f['toss_decision_bat'] == 0

    def test_home_ground(self):
        """ta_home = 1 when team plays at their home venue."""
        f = fe.build_prematch_features(
            team_a='Chennai Super Kings', team_b='Mumbai Indians',
            venue='MA Chidambaram Stadium, Chepauk, Chennai',
            toss_winner='Chennai Super Kings', toss_decision='bat',
            team_a_xi=[], team_b_xi=[]
        )
        assert f['ta_home'] == 1
        assert f['tb_home'] == 0


class TestPredictions:
    def test_prematch_probabilities_sum_to_one(self):
        """Win probabilities for both teams must sum to 1.0."""
        import numpy as np
        import json

        model = ml.get_pre_match_model()
        scaler = ml.get_pre_match_scaler()
        feat_cols = ml.get_feature_cols()

        f = fe.build_prematch_features(
            team_a='Mumbai Indians', team_b='Chennai Super Kings',
            venue='Wankhede Stadium, Mumbai', toss_winner='Mumbai Indians',
            toss_decision='bat', team_a_xi=[], team_b_xi=[]
        )
        X = np.array([[f[c] for c in feat_cols]])
        proba = model.predict_proba(scaler.transform(X))[0]
        assert abs(proba.sum() - 1.0) < 1e-6

    def test_live_probabilities_in_range(self):
        """Live win prob must be between 0 and 1."""
        import numpy as np
        import json

        model = ml.get_live_model()
        feat_cols = ml.get_live_feature_cols()

        f = fe.build_live_features(
            current_score=100, wickets=3, balls_bowled=72,
            target=180, batting_team='Mumbai Indians', venue=''
        )
        X = np.array([[f[c] for c in feat_cols]])
        proba = model.predict_proba(X)[0]
        assert 0.0 <= proba[1] <= 1.0

    def test_symmetry_prematch(self):
        """
        Symmetry check: swap team_a and team_b — win probs should flip.
        CSK win% when CSK=team_a should equal CSK win% when CSK=team_b.
        """
        import numpy as np

        model = ml.get_pre_match_model()
        scaler = ml.get_pre_match_scaler()
        feat_cols = ml.get_feature_cols()

        f1 = fe.build_prematch_features(
            team_a='Mumbai Indians', team_b='Chennai Super Kings',
            venue='Wankhede Stadium, Mumbai', toss_winner='Mumbai Indians',
            toss_decision='bat', team_a_xi=[], team_b_xi=[]
        )
        f2 = fe.build_prematch_features(
            team_a='Chennai Super Kings', team_b='Mumbai Indians',
            venue='Wankhede Stadium, Mumbai', toss_winner='Mumbai Indians',
            toss_decision='bat', team_a_xi=[], team_b_xi=[]
        )
        p1 = model.predict_proba(scaler.transform(np.array([[f1[c] for c in feat_cols]])))[0]
        p2 = model.predict_proba(scaler.transform(np.array([[f2[c] for c in feat_cols]])))[0]
        # MI win prob in game 1 (team_a) ≈ 1 - MI win prob in game 2 (team_b)
        mi_p1 = p1[1]   # team_a (MI) wins
        mi_p2 = p2[0]   # team_b (MI) wins = 1 - team_a (CSK) wins
        # Allow 10% tolerance — feature engine uses same stats for both orderings
        assert abs(mi_p1 - mi_p2) < 0.15, f"Symmetry broken: {mi_p1:.3f} vs {mi_p2:.3f}"

    def test_sanity_csk_at_chepauk(self):
        """CSK at Chepauk should have a non-trivial win probability (>45%)."""
        import numpy as np

        model = ml.get_pre_match_model()
        scaler = ml.get_pre_match_scaler()
        feat_cols = ml.get_feature_cols()

        f = fe.build_prematch_features(
            team_a='Chennai Super Kings', team_b='Mumbai Indians',
            venue='MA Chidambaram Stadium, Chepauk, Chennai',
            toss_winner='Chennai Super Kings', toss_decision='bat',
            team_a_xi=[], team_b_xi=[]
        )
        X = np.array([[f[c] for c in feat_cols]])
        proba = model.predict_proba(scaler.transform(X))[0]
        csk_prob = proba[1]
        assert csk_prob > 0.45, f"CSK at Chepauk win prob unexpectedly low: {csk_prob:.3f}"
