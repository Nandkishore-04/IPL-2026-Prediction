import pandas as pd
import json

def add_full_name():
    csv_path = r'd:\IPL Prediction\data\processed\player_career_ipl.csv'
    map_path = r'd:\IPL Prediction\data\processed\player_name_map.json'
    
    df = pd.read_csv(csv_path)
    with open(map_path, 'r') as f:
        name_map = json.load(f)
    
    df['full_name'] = df['player'].map(name_map)
    
    # Reorder columns to have full_name near player
    cols = df.columns.tolist()
    cols.insert(1, cols.pop(cols.index('full_name')))
    df = df[cols]
    
    df.to_csv(csv_path, index=False)
    print(f"Added full_name column to {csv_path}")

if __name__ == "__main__":
    add_full_name()
