import sqlite3
import pandas as pd

DB_PATH = "data/ipl_engine.db"

def cleanup():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("--- [CLEANUP] Deduplicating 2026 Season Data ---")
    
    # Get all records to analyze
    df = pd.read_sql_query("SELECT * FROM player_match_history_2026", conn)
    
    # Identify unique (player_name, date) pairs to see if they appear in multiple match_ids
    duplicates = df.groupby(['player_name', 'date']).filter(lambda x: len(x) > 1)
    
    if len(duplicates) > 0:
        print(f"Found {len(duplicates)} duplicate player-day entries. Purging...")
        
        # We want to keep the record that belongs to the 'better' match_id 
        # (usually the one with more total players or the canonical name)
        
        # Strategy: For each (player, date), if there are multiple entries, 
        # delete the one that doesn't belong to the 'Deepest' match_id for that day.
        
        # Find the counts per match_id
        counts = df.groupby('match_id').size().to_dict()
        
        # Iterate through unique (player, date) keys
        keys = df[['player_name', 'date']].drop_duplicates()
        ids_to_keep = []
        
        for _, row in keys.iterrows():
            subset = df[(df['player_name'] == row['player_name']) & (df['date'] == row['date'])]
            if len(subset) == 1:
                ids_to_keep.append(subset.iloc[0]['id'])
            else:
                # Keep the one whose match_id has the highest overall player count
                best_id = subset.loc[subset['match_id'].map(counts).idxmax()]['id']
                ids_to_keep.append(best_id)
        
        # Delete everything but the keepers
        cursor.execute(f"DELETE FROM player_match_history_2026 WHERE id NOT IN ({','.join(map(str, ids_to_keep))})")
        print(f"[SUCCESS] Deduplicated. Remaining records: {len(ids_to_keep)}")
    else:
        print("No duplicates found across player names and dates.")

    # Standardize Match IDs
    cursor.execute("SELECT DISTINCT date, match_id FROM player_match_history_2026 ORDER BY date")
    match_list = cursor.fetchall()
    for i, (date, mid) in enumerate(match_list, 1):
        clean_name = f"MATCH_{i:02d}_{date}"
        cursor.execute("UPDATE player_match_history_2026 SET match_id = ? WHERE match_id = ?", (clean_name, mid))
    
    conn.commit()
    conn.close()
    print("[SUCCESS] Match IDs standardized to MATCH_01, MATCH_02, etc.")

if __name__ == "__main__":
    cleanup()
