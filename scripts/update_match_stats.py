import json
import os

def update_data():
    # File Paths
    STANDINGS_FILE = "api/data/ipl2026_standings.json"
    STATS_FILE = "api/data/player_stats.json"
    LOG_FILE = "api/data/predictions_log.json"

    # Match Data
    match_data = {
        "match_num": 13,
        "date": "2026-04-07",
        "team_a": "Rajasthan Royals",
        "team_b": "Mumbai Indians",
        "winner": "Rajasthan Royals",
        "venue": "Barsapara Cricket Stadium, Guwahati"
    }

    # 1. Update Standings
    if os.path.exists(STANDINGS_FILE):
        with open(STANDINGS_FILE, "r") as f:
            standings = json.load(f)
        
        # Add match to history
        if not any(m.get("match_num") == 13 for m in standings["matches"]):
            standings["matches"].append(match_data)
        
        # Update team stats
        alpha = 0.3
        
        # RR
        rr = standings["team_stats"]["Rajasthan Royals"]
        rr["matches"] += 1
        rr["wins"] += 1
        rr["points"] += 2
        rr["streak"] = (rr["streak"] + 1) if rr["streak"] > 0 else 1
        rr["last5"].append(1)
        rr["ema_form"] = round(rr["ema_form"] * (1 - alpha) + 1 * alpha, 4)
        
        # MI
        mi = standings["team_stats"]["Mumbai Indians"]
        mi["matches"] += 1
        mi["losses"] += 1
        # mi["points"] stays same
        mi["streak"] = (mi["streak"] - 1) if mi["streak"] < 0 else -1
        mi["last5"].append(0)
        mi["ema_form"] = round(mi["ema_form"] * (1 - alpha) + 0 * alpha, 4)

        with open(STANDINGS_FILE, "w") as f:
            json.dump(standings, f, indent=2)
        print("Updated Standings.")

    # 2. Update Player Stats (Batting/Bowling increments)
    # We only update the key performers mentioned in search
    performers = {
        # RR Batters (name: [runs, balls_faced])
        "Yashasvi Jaiswal": {"runs": 77, "balls": 32, "type": "bat"},
        "Vaibhav Suryavanshi": {"runs": 39, "balls": 14, "type": "bat"},
        "Riyan Parag": {"runs": 20, "balls": 10, "type": "bat"},
        "Dhruv Jurel": {"runs": 2, "balls": 3, "type": "bat"},
        "Shimron Hetmyer": {"runs": 6, "balls": 7, "type": "bat"},
        # MI Batters
        "Naman Dhir": {"runs": 25, "balls": 13, "type": "bat"},
        "Sherfane Rutherford": {"runs": 25, "balls": 8, "type": "bat"},
        "Tilak Varma": {"runs": 14, "balls": 10, "type": "bat"},
        "Hardik Pandya": {"runs": 9, "balls": 6, "type": "bat"},
        "Ryan Rickelton": {"runs": 8, "balls": 4, "type": "bat"},
        # RR Bowlers (name: [wickets])
        "Sandeep Sharma": {"wickets": 2, "type": "bowl"},
        "Nandre Burger": {"wickets": 2, "type": "bowl"},
        "Ravi Bishnoi": {"wickets": 2, "type": "bowl"},
        "Jofra Archer": {"wickets": 1, "type": "bowl"},
        "Tushar Deshpande": {"wickets": 1, "type": "bowl"},
        # MI Bowlers
        "AM Ghazanfar": {"wickets": 2, "type": "bowl"},
        "Shardul Thakur": {"wickets": 1, "type": "bowl"},
    }

    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            stats = json.load(f)
        
        for name, data in performers.items():
            if name not in stats:
                # Add default if missing
                stats[name] = {
                    "batting_runs": 0.0, "balls_faced": 0.0, "batting_sr": 120.0, "batting_avg": 20.0,
                    "innings_played": 0, "wickets": 0.0, "bowling_econ": 8.5, "bowling_sr": 20.0,
                    "innings_bowled": 0, "ipl_caps": 0
                }
            
            p = stats[name]
            p["ipl_caps"] += 1
            if data["type"] == "bat":
                p["batting_runs"] += data["runs"]
                p["balls_faced"] += data["balls"]
                p["innings_played"] += 1
                if p["balls_faced"] > 0:
                    p["batting_sr"] = round((p["batting_runs"] / p["balls_faced"]) * 100, 2)
            elif data["type"] == "bowl":
                p["wickets"] += data["wickets"]
                p["innings_bowled"] += 1
                # Econ/SR updates would require more detailed ball data, 
                # but we increment wickets at least.

        with open(STATS_FILE, "w") as f:
            json.dump(stats, f, indent=2)
        print("Updated Player Stats.")

if __name__ == "__main__":
    update_data()
