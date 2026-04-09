import sqlite3
import json
import os

DB_PATH = "data/ipl_engine.db"
MAP_PATH = "data/processed/player_name_map.json"

def normalize_and_consolidate():
    if not os.path.exists(MAP_PATH):
        print(f"Error: {MAP_PATH} not found.")
        return

    with open(MAP_PATH, "r") as f:
        name_map = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("--- [NORMALIZATION] Syncing Names and Merging Matches ---")

    # 1. Update all names to their full version if they exist in the map
    for abbr, full in name_map.items():
        cursor.execute("UPDATE player_match_history_2026 SET player_name = ? WHERE player_name = ?", (full, abbr))
    
    conn.commit()
    print("[SUCCESS] All player names normalized to full format.")

    # 2. Re-run deduplication logic now that names are identical
    cursor.execute("SELECT id, player_name, date, match_id FROM player_match_history_2026 ORDER BY date")
    rows = cursor.fetchall()
    
    seen = {} # (name, date) -> (id, match_id)
    to_delete = []
    
    for rid, name, date, mid in rows:
        key = (name, date)
        if key in seen:
            prev_id, prev_mid = seen[key]
            if "MATCH_" in str(mid):
                to_delete.append(prev_id)
                seen[key] = (rid, mid)
            else:
                to_delete.append(rid)
        else:
            seen[key] = (rid, mid)
            
    if to_delete:
        cursor.execute(f"DELETE FROM player_match_history_2026 WHERE id IN ({','.join(map(str, to_delete))})")
        print(f"[SUCCESS] Merged {len(to_delete)} records into their canonical matches.")

    # 3. Final standardized ID reset
    cursor.execute("SELECT DISTINCT date FROM player_match_history_2026 ORDER BY date")
    dates = [r[0] for r in cursor.fetchall()]
    
    for date in dates:
        if date not in ["2026-04-04", "2026-04-05"]:
            target_id = f"MATCH_{date}"
            cursor.execute("UPDATE player_match_history_2026 SET match_id = ? WHERE date = ?", (target_id, date))

    conn.commit()
    conn.close()
    print("[SUCCESS] Database is now lean, normalized, and unified!")

if __name__ == "__main__":
    normalize_and_consolidate()
