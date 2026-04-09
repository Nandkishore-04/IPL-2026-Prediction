import json
import os

LOG_PATH = r'd:\IPL Prediction\api\data\predictions_log.json'
STANDINGS_PATH = r'd:\IPL Prediction\api\data\ipl2026_standings.json'

def update_results():
    # results = {match_id: winner}
    results = {
        "GUJ-RAJ-2026-04-04": "Rajasthan Royals",
        "DEL-MUM-2026-04-05": "Delhi Capitals",
        "SUN-LUC-2026-04-05": "Lucknow Super Giants"
    }

    # 1. Update predictions_log.json
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, 'r') as f:
            log = json.load(f)
        
        for entry in log:
            mid = entry.get('match_id')
            if mid in results:
                winner = results[mid]
                entry['actual_winner'] = winner
                if entry.get('predicted_winner'):
                    entry['correct'] = (entry['predicted_winner'] == winner)
                print(f"Updated log for {mid}: Winner {winner}")
        
        with open(LOG_PATH, 'w') as f:
            json.dump(log, f, indent=2)

    # 2. Update ipl2026_standings.json
    if os.path.exists(STANDINGS_PATH):
        with open(STANDINGS_PATH, 'r') as f:
            standings = json.load(f)
        
        # Add new matches if not already there
        existing_mids = [f"{m['team_a'][:3].upper()}-{m['team_b'][:3].upper()}-{m['date']}" for m in standings['matches']]
        # Wait, the match ids in standings matches are not there, I'll just check team/date
        
        new_matches = [
            {"date": "2026-04-04", "team_a": "Gujarat Titans", "team_b": "Rajasthan Royals", "winner": "Rajasthan Royals", "venue": "Narendra Modi Stadium, Ahmedabad"},
            {"date": "2026-04-05", "team_a": "Delhi Capitals", "team_b": "Mumbai Indians", "winner": "Delhi Capitals", "venue": "Arun Jaitley Stadium, Delhi"},
            {"date": "2026-04-05", "team_a": "Sunrisers Hyderabad", "team_b": "Lucknow Super Giants", "winner": "Lucknow Super Giants", "venue": "Rajiv Gandhi International Stadium, Hyderabad"}
        ]

        for nm in new_matches:
            # Check if exists
            exists = any(m['date'] == nm['date'] and m['team_a'] == nm['team_a'] for m in standings['matches'])
            if not exists:
                nm['match_num'] = len(standings['matches']) + 1
                standings['matches'].append(nm)
                
                # Update stats
                for team in [nm['team_a'], nm['team_b']]:
                    is_winner = (team == nm['winner'])
                    stats = standings['team_stats'].get(team)
                    if stats:
                        stats['matches'] += 1
                        if is_winner:
                            stats['wins'] += 1
                            stats['points'] += 2
                            stats['streak'] = stats['streak'] + 1 if stats['streak'] > 0 else 1
                            stats['last5'].append(1)
                        else:
                            stats['losses'] += 1
                            stats['streak'] = stats['streak'] - 1 if stats['streak'] < 0 else -1
                            stats['last5'].append(0)
                        
                        if len(stats['last5']) > 5:
                            stats['last5'].pop(0)
                
                print(f"Added match to standings: {nm['team_a']} vs {nm['team_b']} -> {nm['winner']}")

        with open(STANDINGS_PATH, 'w') as f:
            json.dump(standings, f, indent=2)

if __name__ == "__main__":
    update_results()
