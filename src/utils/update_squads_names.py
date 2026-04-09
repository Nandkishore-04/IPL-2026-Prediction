import json
import os

def update_squads():
    squad_path = r'd:\IPL Prediction\api\data\squads_2026.json'
    map_path = r'd:\IPL Prediction\data\processed\player_name_map.json'
    
    with open(squad_path, 'r') as f:
        squads = json.load(f)
    
    with open(map_path, 'r') as f:
        name_map = json.load(f)
    
    updated_count = 0
    for team, players in squads.items():
        for player in players:
            original_name = player['name']
            # If name is in the map and the mapped value is different, update it
            if original_name in name_map and name_map[original_name] != original_name:
                player['name'] = name_map[original_name]
                updated_count += 1
            # Special case: map might contain "MS Dhoni": "Mahendra Singh Dhoni"
            # but squad might already have "MS Dhoni"
    
    with open(squad_path, 'w') as f:
        json.dump(squads, f, indent=2)
    
    print(f"Updated {updated_count} player names in {squad_path}")

if __name__ == "__main__":
    update_squads()
