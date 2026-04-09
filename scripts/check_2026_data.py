import sqlite3
import json
import os

DB_PATH = "data/ipl_engine.db"

def check_and_fill():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check match distribution
    cursor.execute("SELECT match_id, COUNT(*) FROM player_match_history_2026 GROUP BY match_id")
    matches = cursor.fetchall()
    print("--- 2026 Match Records in DB ---")
    for mid, count in matches:
        print(f"Match {mid}: {count} players")
    
    # Check total players
    cursor.execute("SELECT COUNT(DISTINCT player_name) FROM player_match_history_2026")
    players = cursor.fetchone()[0]
    print(f"\nTotal 2026 Players Tracked: {players}")
    
    conn.close()

if __name__ == "__main__":
    check_and_fill()
