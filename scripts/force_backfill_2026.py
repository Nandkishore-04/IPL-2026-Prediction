import sqlite3

DB_PATH = "data/ipl_engine.db"

def fill_missing():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Data to add
    matches = [
        # Match 4: PBKS vs GT (2026-03-31)
        ("Cooper Connolly", "PBKS-GUA-4", "2026-03-31", 72, 44, 0, 0, 0),
        ("Prabhsimran Singh", "PBKS-GUA-4", "2026-03-31", 37, 24, 0, 0, 0),
        ("Shubman Gill", "PBKS-GUA-4", "2026-03-31", 39, 27, 0, 0, 0),
        ("Jos Buttler", "PBKS-GUA-4", "2026-03-31", 38, 33, 0, 0, 0),
        ("Vijaykumar Vyshak", "PBKS-GUA-4", "2026-03-31", 0, 0, 24, 34, 3),
        ("Yuzvendra Chahal", "PBKS-GUA-4", "2026-03-31", 0, 0, 24, 28, 2),
        ("Prasidh Krishna", "PBKS-GUA-4", "2026-03-31", 0, 0, 24, 29, 3),
        
        # Match 7: CSK vs PBKS (2026-04-03)
        ("Ayush Mhatre", "CHE-PBK-7", "2026-04-03", 73, 43, 0, 0, 0),
        ("Shivam Dube", "CHE-PBK-7", "2026-04-03", 45, 27, 0, 0, 0),
        ("Shreyas Iyer", "CHE-PBK-7", "2026-04-03", 50, 26, 0, 0, 0),
        ("Nehal Wadhera", "CHE-PBK-7", "2026-04-03", 46, 24, 0, 0, 0),
        ("Matt Henry", "CHE-PBK-7", "2026-04-03", 0, 0, 24, 30, 2),
        
        # Match 13: RR vs MI (2026-04-07)
        ("Yashasvi Jaiswal", "RAJ-MUM-13", "2026-04-07", 77, 32, 0, 0, 0),
        ("Vaibhav Suryavanshi", "RAJ-MUM-13", "2026-04-07", 39, 14, 0, 0, 0),
        ("Riyan Parag", "RAJ-MUM-13", "2026-04-07", 20, 10, 0, 0, 0),
        ("Naman Dhir", "RAJ-MUM-13", "2026-04-07", 25, 13, 0, 0, 0),
        ("Sherfane Rutherford", "RAJ-MUM-13", "2026-04-07", 25, 8, 0, 0, 0),
        ("Sandeep Sharma", "RAJ-MUM-13", "2026-04-07", 0, 0, 12, 15, 2),
        ("Nandre Burger", "RAJ-MUM-13", "2026-04-07", 0, 0, 12, 18, 2),
        ("Ravi Bishnoi", "RAJ-MUM-13", "2026-04-07", 0, 0, 12, 20, 2),
        ("AM Ghazanfar", "RAJ-MUM-13", "2026-04-07", 0, 0, 12, 21, 2)
    ]

    count = 0
    for m in matches:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO player_match_history_2026 
                (player_name, match_id, date, runs, balls_faced, balls_bowled, runs_conceded, wickets)
                VALUES (?,?,?,?,?,?,?,?)
            """, m)
            count += 1
        except Exception as e:
            print(f"Error: {e}")

    conn.commit()
    conn.close()
    print(f"✅ Forced backfill complete. Added/Updated {count} key 2026 performances.")

if __name__ == "__main__":
    fill_missing()
