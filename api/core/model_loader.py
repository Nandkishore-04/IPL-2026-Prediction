"""
Loads ML models and scalers from disk at startup.
Both models are loaded once and reused for all requests.
"""

import joblib
import json
import os

# Paths relative to project root (where uvicorn is started from)
MODELS_DIR = "models"

_pre_match_model = None
_live_model = None
_live_scaler = None
_feature_cols = None
_live_feature_cols = None


def load_all():
    global _pre_match_model, _live_model, _live_scaler
    global _feature_cols, _live_feature_cols

    # Scaler is embedded inside the GB pipeline — no separate scaler.pkl needed
    _pre_match_model  = joblib.load(os.path.join(MODELS_DIR, "pre_match_model.pkl"))
    _live_model       = joblib.load(os.path.join(MODELS_DIR, "live_model.pkl"))
    _live_scaler      = joblib.load(os.path.join(MODELS_DIR, "live_scaler.pkl"))

    with open(os.path.join(MODELS_DIR, "feature_cols.json")) as f:
        _feature_cols = json.load(f)

    with open(os.path.join(MODELS_DIR, "live_feature_cols.json")) as f:
        _live_feature_cols = json.load(f)

    print(f"[ModelLoader] pre_match_model: {type(_pre_match_model).__name__} ({len(_feature_cols)} features)")
    print(f"[ModelLoader] live_model: {type(_live_model).__name__} ({len(_live_feature_cols)} features)")


def get_pre_match_model():
    return _pre_match_model

def get_live_model():
    return _live_model

def get_live_scaler():
    return _live_scaler

def get_feature_cols():
    return _feature_cols

def get_live_feature_cols():
    return _live_feature_cols
