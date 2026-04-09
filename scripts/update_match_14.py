import sqlite3
import json
import os

DB_PATH = "data/ipl_engine.db"
STANDINGS_FILE = "api/data/ipl2026_standings.json"
LOG_FILE = "api/data/predictions_log.json"

def apply_updates():
    # 1. Update SQLite with Player Stats
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    match_id = "DEL-GUJ-14"
    date = "2026-04-08"
    
    performances = [
        ("Shubman Gill", match_id, date, 70, 45, 0, 0, 0),
        ("Jos Buttler", match_id, date, 52, 27, 0, 0, 0),
        ("Washington Sundar", match_id, date, 55, 32, 0, 0, 0),
        ("Rashid Khan", match_id, date, 0, 0, 24, 17, 3),
        ("KL Rahul", match_id, date, 92, 52, 0, 0, 0),
        ("David Miller", match_id, date, 41, 20, 0, 0, 0)
    ]
    
    for p in performances:
        cursor.execute("""
            INSERT OR REPLACE INTO player_match_history_2026 
            (player_name, match_id, date, runs, balls_faced, balls_bowled, runs_conceded, wickets)
            VALUES (?,?,?,?,?,?,?,?)
        """, p)
    
    conn.commit()
    conn.close()
    print("[SUCCESS] SQLite database updated with Match 14 stats.")

    # 2. Update predictions_log.json
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            log = json.load(f)
        for entry in log:
            if entry["match_id"] == "DEL-GUJ-2026-04-08":
                entry["actual_winner"] = "Gujarat Titans"
                entry["correct"] = True
        with open(LOG_FILE, "w") as f:
            json.dump(log, f, indent=2)
        print("[SUCCESS] Prediction log marked as Correct.")

    # 3. Update Standings
    if os.path.exists(STANDINGS_FILE):
        with open(STANDINGS_FILE, "r") as f:
            standings = json.load(f)
        
        match_entry = {
            "match_num": 14,
            "date": "2026-04-08",
            "team_a": "Delhi Capitals",
            "team_b": "Gujarat Titans",
            "winner": "Gujarat Titans",
            "venue": "Arun Jaitley Stadium, Delhi"
        }
        if not any(m.get("match_num") == 14 for m in standings["matches"]):
            standings["matches"].append(match_entry)

        alpha = 0.3
        # GT Update
        gt = standings["team_stats"]["Gujarat Titans"]
        gt["matches"] += 1
        gt["wins"] += 1
        gt["points"] += 2
        gt["ema_form"] = round(gt["ema_form"] * (1 - alpha) + 1 * alpha, 4)
        
        # DC Update
        dc = standings["team_stats"]["Delhi Capitals"]
        dc.setdefault("losses", 0)
        dc["matches"] += 1
        dc["losses"] += 1
        dc["ema_form"] = round(dc["ema_form"] * (1 - alpha) + 0 * alpha, 4)

        with open(STANDINGS_FILE, "w") as f:
            json.dump(standings, f, indent=2)
        print("[SUCCESS] IPL 2026 Standings updated.")

if __name__ == "__main__":
    apply_updates()
