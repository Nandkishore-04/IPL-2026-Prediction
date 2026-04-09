import json
import sqlite3
import os

DB_PATH = "data/ipl_engine.db"
PLAYER_STATS_JSON = "api/data/player_stats.json"
PLAYER_FORM_JSON = "data/processed/player_form_2026.json"

import math

def safe_int(val, default=0):
    try:
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return default
        return int(float(val))
    except (ValueError, TypeError):
        return default

def safe_float(val, default=0.0):
    try:
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return default
        return float(val)
    except (ValueError, TypeError):
        return default

def migrate():
    print(f"📡 Starting migration to SQLite: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Create Tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS player_stats (
        name TEXT PRIMARY KEY,
        batting_runs REAL DEFAULT 0.0,
        balls_faced REAL DEFAULT 0.0,
        batting_sr REAL DEFAULT 120.0,
        batting_avg REAL DEFAULT 20.0,
        innings_played INTEGER DEFAULT 0,
        wickets REAL DEFAULT 0.0,
        bowling_econ REAL DEFAULT 8.5,
        bowling_sr REAL DEFAULT 20.0,
        innings_bowled INTEGER DEFAULT 0,
        ipl_caps INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS player_match_history_2026 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_name TEXT,
        match_id TEXT,
        date TEXT,
        runs INTEGER DEFAULT 0,
        balls_faced INTEGER DEFAULT 0,
        balls_bowled INTEGER DEFAULT 0,
        runs_conceded INTEGER DEFAULT 0,
        wickets INTEGER DEFAULT 0,
        UNIQUE(player_name, match_id)
    )
    """)

    # 2. Migrate Career Stats
    if os.path.exists(PLAYER_STATS_JSON):
        with open(PLAYER_STATS_JSON) as f:
            data = json.load(f)
            for name, p in data.items():
                stats = (
                    name, 
                    safe_float(p.get("batting_runs")),
                    safe_float(p.get("balls_faced")),
                    safe_float(p.get("batting_sr")),
                    safe_float(p.get("batting_avg")),
                    safe_int(p.get("innings_played")),
                    safe_float(p.get("wickets")),
                    safe_float(p.get("bowling_econ")),
                    safe_float(p.get("bowling_sr")),
                    safe_int(p.get("innings_bowled")),
                    safe_int(p.get("ipl_caps"))
                )
                cursor.execute("""
                INSERT OR REPLACE INTO player_stats VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, stats)
        print(f"✅ Migrated {len(data)} career player records.")

    # 3. Migrate 2026 Form
    if os.path.exists(PLAYER_FORM_JSON):
        with open(PLAYER_FORM_JSON) as f:
            form_data = json.load(f)
            count = 0
            for name, matches in form_data.items():
                for m in matches:
                    cursor.execute("""
                    INSERT OR IGNORE INTO player_match_history_2026 
                    (player_name, match_id, date, runs, balls_faced, balls_bowled, runs_conceded, wickets)
                    VALUES (?,?,?,?,?,?,?,?)
                    """, (
                        name, m["match_id"], m["date"], 
                        m.get("runs", 0), m.get("balls_faced", 0), 
                        m.get("balls_bowled", 0), m.get("runs_conceded", 0), 
                        m.get("wickets", 0)
                    ))
                    count += 1
        print(f"✅ Migrated {count} individual 2026 match performances.")

    conn.commit()
    conn.close()
    print("🚀 Migration Successful!")

if __name__ == "__main__":
    migrate()
