import json
import os

STANDINGS_PATH = r'd:\IPL Prediction\api\data\ipl2026_standings.json'
LOG_PATH = r'd:\IPL Prediction\api\data\predictions_log.json'

def fix_dc_stats():
    if not os.path.exists(STANDINGS_PATH):
        return

    with open(STANDINGS_PATH, 'r') as f:
        standings = json.load(f)

    # Find the duplicate/extra DC vs MI match on April 5th (Match 10)
    match_to_remove = None
    for i, m in enumerate(standings['matches']):
        if m['date'] == '2026-04-05' and m['team_a'] == 'Delhi Capitals' and m['team_b'] == 'Mumbai Indians':
            match_to_remove = i
            break
    
    if match_to_remove is not None:
        removed_match = standings['matches'].pop(match_to_remove)
        print(f"Removed extra match: {removed_match}")
        
        # Update match numbers for subsequent matches
        for j in range(match_to_remove, len(standings['matches'])):
            standings['matches'][j]['match_num'] = j + 1
            
        # Re-calculate stats for DC and MI
        for team in ['Delhi Capitals', 'Mumbai Indians']:
            stats = standings['team_stats'][team]
            # Reset and re-calculate from matches list
            stats['wins'] = 0
            stats['losses'] = 0
            stats['matches'] = 0
            stats['points'] = 0
            stats['last5'] = []
            
            for m in standings['matches']:
                if m['team_a'] == team or m['team_b'] == team:
                    stats['matches'] += 1
                    if m['winner'] == team:
                        stats['wins'] += 1
                        stats['points'] += 2
                        stats['last5'].append(1)
                    else:
                        stats['losses'] += 1
                        stats['last5'].append(0)
            
            # Recalculate streak from last5
            if not stats['last5']:
                stats['streak'] = 0
            else:
                curr = stats['last5'][-1]
                streak = 0
                for x in reversed(stats['last5']):
                    if x == curr:
                        streak = streak + 1 if curr == 1 else streak - 1
                    else:
                        break
                stats['streak'] = streak

    with open(STANDINGS_PATH, 'w') as f:
        json.dump(standings, f, indent=2)
    print("Standings fixed.")

    # Also fix predictions_log.json if necessary (optional but good for consistency)
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, 'r') as f:
            log = json.load(f)
        # Find DEL-MUM-2026-04-05 and reset actual_winner to null
        for entry in log:
            if entry.get('match_id') == 'DEL-MUM-2026-04-05':
                entry['actual_winner'] = None
                entry['correct'] = None
        with open(LOG_PATH, 'w') as f:
            json.dump(log, f, indent=2)
        print("Log fixed.")

if __name__ == "__main__":
    fix_dc_stats()
