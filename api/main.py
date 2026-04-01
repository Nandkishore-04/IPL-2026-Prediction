"""
IPL 2026 Predictor — FastAPI Backend
Run from project root: uvicorn api.main:app --reload

Endpoints:
  POST /api/predict-match     — pre-match winner prediction
  POST /api/predict-live      — live ball-by-ball win probability
  GET  /api/teams             — list of IPL 2026 teams
  GET  /api/venues            — list of venues
  GET  /api/team/{name}/stats — team historical stats
  GET  /api/accuracy          — prediction accuracy tracker
  POST /api/log-result        — log actual match result
  GET  /api/live-feed         — current live match state
  POST /api/live-feed/manual  — manually update live score
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import api.core.model_loader  as ml
import api.core.feature_engine as fe
import api.core.player_stats   as ps
import api.core.live_feed      as lf

from api.routes import predict, teams, accuracy, live


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load models and data. Shutdown: stop polling."""
    print("Starting IPL Predictor API...")
    ml.load_all()
    fe.load()
    ps.load()
    # Start CricAPI polling loop as a background task
    task = asyncio.create_task(lf.polling_loop())
    yield
    # Shutdown
    lf._polling_active = False
    task.cancel()
    print("API shutdown.")


app = FastAPI(
    title="IPL 2026 Match Predictor",
    description="Pre-match and live win probability predictions for IPL 2026.",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow React dev server (port 3000) and any origin for portfolio use
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routes under /api prefix
app.include_router(predict.router,  prefix="/api", tags=["Predictions"])
app.include_router(teams.router,    prefix="/api", tags=["Teams & Venues"])
app.include_router(accuracy.router, prefix="/api", tags=["Accuracy"])
app.include_router(live.router,     prefix="/api", tags=["Live Feed"])


@app.get("/")
def root():
    return {
        "message": "IPL 2026 Predictor API",
        "docs": "/docs",
        "endpoints": [
            "POST /api/predict-match",
            "POST /api/predict-live",
            "GET  /api/teams",
            "GET  /api/venues",
            "GET  /api/team/{name}/stats",
            "GET  /api/accuracy",
            "POST /api/log-result",
            "GET  /api/live-feed",
        ],
    }


@app.get("/health")
def health():
    return {"status": "ok"}
