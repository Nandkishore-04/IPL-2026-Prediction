# 🏏 IPL 2026 Engine: Prediction & Analytics

[![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.2.4-20232a?style=for-the-badge&logo=react&logoColor=61dafb)](https://react.dev/)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-1.5.0-f7931e?style=for-the-badge&logo=scikitlearn&logoColor=white)](https://scikit-learn.org/)

A full-stack predictive platform delivering pre-match winner forecasts and live ball-by-ball win probabilities for the IPL 2026 season. Built with a focus on system design, data calibration, and real-time inference.

---

## ⚡ Quick Demo

The platform provides two primary interfaces:

### 1. Pre-Match Predictor
*   **Input**: Team A squad, Team B squad, Venue, and Toss details.
*   **Output**: Calibrated win probability based on 42 historical and situational features.

### 2. Live Match Tracker
*   **Update Frequency**: Every ball (via smart polling).
*   **Visualization**: Dynamic win-probability trends and situational momentum shifts.

> [!TIP]
> Use the **Accuracy Dashboard** to see the model's performance in real-time as the 2026 season progresses.

---

## 📈 Model Performance

The pre-match model was trained on historical IPL data (2008–2023) and validated on the 2024–2025 seasons.

| Metric | Value | Interpretation |
| :--- | :--- | :--- |
| **Accuracy** | 58.6% | Strong for high-variance sports forecasting |
| **AUC** | 0.626 | Indicates solid discriminative power |
| **Brier Score** | 0.238 | Measures the quality of probability forecasts |
| **Calibration** | Isotonic | Ensures predicted 70% win rate matches reality |

---

## 🧠 Feature Engineering

Rather than using raw cumulative totals, the engine focuses on **differential features** to eliminate team-order bias and capture relative strength:

*   **`xi_exp_diff`**: The gap in match experience between the selected Playing XIs.
*   **`form_wr_diff`**: Momentum difference calculated via **Exponential Moving Average (EMA)**.
*   **`venue_wr_diff`**: Historical win-rate advantage specialized to the specific venue.
*   **`ar_ratio_diff`**: Difference in "All-rounder density"—a key factor in T20 depth.

---

## 🏗 System Architecture

### Pre-Match Model
*   **Algorithm**: Gradient Boosting Classifier (Scikit-Learn).
*   **Training**: Recency-weighted training (2008–2025) favoring modern T20 dynamics.
*   **Inference**: Processes 42 engineered features at runtime.

### Live Model
*   **Algorithm**: XGBoost / Logistic Regression ensemble choice.
*   **Context**: 18 real-time situational signals (RRR, Dot %, Wickets in hand).
*   **Optimization**: Calibrated using isotonic regression for reliable betting/analysis metrics.

### Data Infrastructure
*   **Credit-Aware Polling**: Smart "match window" logic reduces API credit usage by **90%**.
*   **Form Blending Engine**: Blends 2026 season-to-date form (60%) with career stats (40%) dynamically.
*   **Auto-Logging**: background tasks handle scorecard logging and standings updates instantly upon match completion.

---

## ⚙️ Design Decisions

*   **Decoupled Architecture**: Strictly separated ML, API, and UI layers for independent scalability.
*   **Isotonic Calibration**: Prioritized probability reliability over raw accuracy to support strategic analysis.
*   **Normalization**: Implemented custom name-matching and venue-normalization logic to handle inconsistent data sources.
*   **State Management**: Real-time React dashboard with background polling for live match states.

---

## 🎯 Why This Matters

This project demonstrates proficiency in the full data product lifecycle:
1.  **Data Science**: Handling non-stationary data (team form) and ensuring model calibration.
2.  **Engineering**: Building a production-ready API with background task orchestration.
3.  **Product**: Creating a user-centric dashboard for complex statistical insights.

---

## 🔮 Future Improvements

*   **Player-level Embeddings**: Moving from hand-crafted features to deep learning-based player vectors.
*   **Match Simulation Engine**: Monte Carlo simulations for hypothetical squad compositions.
*   **Cloud Streaming**: Migrating to a Kafka-based real-time match event pipeline.

---


