# 🏏 IPL 2026 Prediction Engine

[![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.2.4-20232a?style=for-the-badge&logo=react&logoColor=61dafb)](https://react.dev/)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-1.5.0-f7931e?style=for-the-badge&logo=scikitlearn&logoColor=white)](https://scikit-learn.org/)

A professional-grade machine learning platform for IPL 2026, delivering pre-match win projections and live ball-by-ball win probabilities. The system integrates 18 years of historical data with real-time 2026 season form using advanced ensemble models and credit-efficient data pipelines.

---

## 🏗 System Architecture

The project is built with a decoupled architecture focusing on data integrity and real-time responsiveness:

### 1. The Machine Learning Core
*   **Pre-Match Model**: A **Gradient Boosting Classifier** trained on 2008–2025 data. 
    *   **Feature Engineering**: Implements **42 differential features** (venue bias, H2H, team momentum) to eliminate multi-collinearity.
    *   **Recency Weighting**: Uses an exponential decay function to prioritize recent seasons (2023-2025) over older history.
    *   **Calibration**: Wrapped in **Isotonic Regression** (`CalibratedClassifierCV`) to ensure that a 70% probability forecast translates to a 70% actual win rate.
*   **Live Predictor**: A situational model (optimized via **XGBoost** / **Random Forest**) analyzing 18 real-time features like **RRR**, **Dot Ball %**, and **Partnership Momentum**.

### 2. Intelligent Data Pipeline (`LiveFeed.py`)
*   **Credit-Efficient Polling**: Instead of 24/7 polling, the system uses "Match Window Awareness." It sleeps until scheduled match times (3:30/7:30 PM IST), reducing API consumption by **90%**.
*   **Auto-Logging**: Automatically detects match endings, logs results to the `season_tracker`, and triggers a **Scorecard Backfill** to update 2026 player form.

### 3. Adaptive Form Engine (`FeatureEngine.py`)
*   **EMA Momentum**: Team form is calculated using an **Exponential Moving Average (α=0.3)**, allowing the model to adapt to 2026 season shifts faster than static averages.
*   **60/40 Form Blending**: Player quality is a weighted blend of **Career Stats (40%)** and **Current 2026 Season Form (60%)**, ensuring the model recognizes "in-form" players instantly.

---

## 📊 Technical Highlights

*   **Brier Score Monitoring**: Real-time accuracy evaluation using Brier scores (Standard for probability forecasting).
*   **Washout Handling**: Robust logic to handle "No Result" or Abandoned games—splitting points (1pt) in standings while excluding them from model accuracy metrics.
*   **Name Resolution**: Intelligent mapping between abbreviated player names (Cricsheet) and full names (CricAPI).
*   **Differential Features**: Uses `form_wr_diff` and `xi_exp_diff` instead of raw stats to help the model learn the *relative* advantage between two teams.

---

## 🚀 Deployment & Usage

### Backend (FastAPI)
The backend manages the polling loop and serves the ML models.
```bash
python -m uvicorn api.main:app --reload --port 8000
```

### Frontend (Vite + React)
A dark-themed dashboard featuring real-time win probability charts and an accuracy calibration view.
```bash
cd frontend && npm run dev
```

---

## 🛠 Tech Stack Summary
*   **Backend**: Python, FastAPI, Pydantic, Joblib, Scikit-learn, XGBoost.
*   **Frontend**: React 19, Vite, Recharts, Axios.
*   **Data**: Pandas, NumPy (Vectorized feature engineering).
*   **Integration**: CricAPI (Live Feeds), Cricsheet (Historical Data).

---

*This project is a demonstration of Applied Machine Learning, Full-Stack Engineering, and Systems Design in a sports analytics context.*
