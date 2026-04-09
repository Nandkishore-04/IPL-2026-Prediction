"""
Build a proper full-name player database.
Combines:
  1. Auto-resolved names from player performance dataset
  2. Hardcoded mapping for all major IPL players (current squads + legends)
  3. Keeps abbreviated names for fringe/retired players where full name unknown

Output: data/processed/player_name_map.json  (abbrev -> full name)
        data/processed/player_career_stats_fullnames.json (full name -> stats)
        api/data/player_stats.json (same, used by API)

Run from project root: python src/build_player_names.py
"""

import json, os
from collections import defaultdict
import pandas as pd

# ── Step 1: Auto-resolve from performance datasets ────────────────────────────
print("Collecting full names from player performance datasets...")
full_names = set()
for root, dirs, files in os.walk("data/raw/player_performance"):
    for f in files:
        if f.endswith(".csv"):
            try:
                df = pd.read_csv(os.path.join(root, f))
                if "Player" in df.columns:
                    full_names.update(df["Player"].dropna().str.strip().unique())
            except:
                pass
auction = pd.read_csv("data/raw/IPL_Auction_2026_Sold_Player.csv")
full_names.update(auction["Name"].dropna().str.strip().unique())

print(f"  Found {len(full_names)} full names in reference datasets")

# ── Step 2: Hardcoded mapping — current IPL 2026 squads + all-time legends ───
# Format: "abbreviated (as in ball-by-ball data)" -> "Full Name"
MANUAL_MAP = {
    # ── Current stars ────────────────────────────────────────────────────────
    "V Kohli":        "Virat Kohli",
    "RG Sharma":      "Rohit Sharma",
    "MS Dhoni":       "MS Dhoni",
    "JJ Bumrah":      "Jasprit Bumrah",
    "R Jadeja":       "Ravindra Jadeja",
    "RA Jadeja":      "Ravindra Jadeja",
    "HH Pandya":      "Hardik Pandya",
    "KH Pandya":      "Krunal Pandya",
    "KL Rahul":       "KL Rahul",
    "PP Shaw":        "Prithvi Shaw",
    "IS Sodhi":       "Ish Sodhi",
    "RD Gaikwad":     "Ruturaj Gaikwad",
    "AT Rayudu":      "Ambati Rayudu",
    "SR Watson":      "Shane Watson",
    "SK Raina":       "Suresh Raina",
    "G Gambhir":      "Gautam Gambhir",
    "V Sehwag":       "Virender Sehwag",
    "YK Pathan":      "Yusuf Pathan",
    "IK Pathan":      "Irfan Pathan",
    "S Dhawan":       "Shikhar Dhawan",
    "CH Gayle":       "Chris Gayle",
    "AB de Villiers": "AB de Villiers",
    "DA Warner":      "David Warner",
    "AC Gilchrist":   "Adam Gilchrist",
    "BB McCullum":    "Brendon McCullum",
    "MEK Hussey":     "Mike Hussey",
    "SR Tendulkar":   "Sachin Tendulkar",
    "SC Ganguly":     "Sourav Ganguly",
    "ML Hayden":      "Matthew Hayden",
    "JH Kallis":      "Jacques Kallis",
    "TM Dilshan":     "Tillakaratne Dilshan",
    "KC Sangakkara":  "Kumar Sangakkara",
    "DPMD Jayawardena": "Mahela Jayawardena",
    "MV Boucher":     "Mark Boucher",
    "M Morkel":       "Morne Morkel",
    "DW Steyn":       "Dale Steyn",
    "Harbhajan Singh":"Harbhajan Singh",
    "P Kumar":        "Praveen Kumar",
    "A Nehra":        "Ashish Nehra",
    "Z Khan":         "Zaheer Khan",
    "RP Singh":       "RP Singh",
    "PP Ojha":        "Pragyan Ojha",
    "A Mishra":       "Amit Mishra",
    "A Kumble":       "Anil Kumble",
    "M Vijay":        "Murali Vijay",
    "SS Tiwary":      "Saurabh Tiwary",
    "NV Ojha":        "Naman Ojha",
    "WP Saha":        "Wriddhiman Saha",
    "MK Tiwary":      "Manoj Tiwary",
    "Yuvraj Singh":   "Yuvraj Singh",

    # ── IPL 2026 current squad players ───────────────────────────────────────
    # Mumbai Indians
    "SA Yadav":       "Suryakumar Yadav",
    "TA Boult":       "Trent Boult",
    "JM Bumrah":      "Jasprit Bumrah",
    "IK Kishan":      "Ishan Kishan",
    "TH David":       "Tim David",
    "JC Buttler":     "Jos Buttler",
    "KA Pollard":     "Kieron Pollard",
    "Romario Shepherd": "Romario Shepherd",
    "Jitesh Sharma":  "Jitesh Sharma",
    "Tilak Varma":    "Tilak Varma",

    # Chennai Super Kings
    "DP Conway":      "Devon Conway",
    "MM Ali":         "Moeen Ali",
    "DL Chahar":      "Deepak Chahar",
    "TU Deshpande":   "Tushar Deshpande",
    "Simarjeet Singh":"Simarjeet Singh",
    "SN Thakur":      "Shardul Thakur",
    "AM Rahane":      "Ajinkya Rahane",
    "MS Stoinis":     "Marcus Stoinis",

    # Royal Challengers Bengaluru
    "FH du Plessis":  "Faf du Plessis",
    "GJ Maxwell":     "Glenn Maxwell",
    "MA Starc":       "Mitchell Starc",
    "JR Hazlewood":   "Josh Hazlewood",
    "Mohammed Siraj":  "Mohammed Siraj",
    "Yash Dayal":     "Yash Dayal",
    "RM Patidar":     "Rajat Patidar",
    "Bhuvneshwar Kumar": "Bhuvneshwar Kumar",
    "Liam Livingstone": "Liam Livingstone",
    "Phil Salt":      "Phil Salt",
    "Krunal Pandya":  "Krunal Pandya",

    # Kolkata Knight Riders
    "SP Narine":      "Sunil Narine",
    "AD Russell":     "Andre Russell",
    "NM Rana":        "Nitish Rana",
    "RK Singh":       "Rinku Singh",
    "Varun Chakravarthy": "Varun Chakravarthy",
    "MM Starc":       "Mitchell Starc",
    "PJ Cummins":     "Pat Cummins",
    "TM Head":        "Travis Head",
    "Harshit Rana":   "Harshit Rana",

    # Sunrisers Hyderabad
    "Abhishek Sharma":"Abhishek Sharma",
    "HE van der Dussen": "Rassie van der Dussen",
    "H Klaasen":      "Heinrich Klaasen",
    "Nitish Kumar Reddy": "Nitish Kumar Reddy",
    "Pat Cummins":    "Pat Cummins",
    "A Zampa":        "Adam Zampa",
    "Jaydev Unadkat": "Jaydev Unadkat",
    "HV Patel":       "Harshal Patel",
    "Harshal Patel":  "Harshal Patel",
    "Mohammed Shami":  "Mohammed Shami",
    "Anmolpreet Singh":"Anmolpreet Singh",

    # Rajasthan Royals
    "JC Buttler":     "Jos Buttler",
    "SV Samson":      "Sanju Samson",
    "YBK Jaiswal":    "Yashasvi Jaiswal",
    "R Parag":        "Riyan Parag",
    "Shimron Hetmyer":"Shimron Hetmyer",
    "Trent Boult":    "Trent Boult",
    "Sandeep Sharma": "Sandeep Sharma",
    "Dhruv Jurel":    "Dhruv Jurel",

    # Delhi Capitals
    "DA Marsh":       "David Warner",
    "PP Shaw":        "Prithvi Shaw",
    "Axar Patel":     "Axar Patel",
    "KK Nair":        "Karun Nair",
    "Kuldeep Yadav":  "Kuldeep Yadav",
    "Ishant Sharma":  "Ishant Sharma",
    "Anrich Nortje":  "Anrich Nortje",
    "Jake Fraser-McGurk": "Jake Fraser-McGurk",
    "Tristan Stubbs": "Tristan Stubbs",

    # Gujarat Titans
    "Shubman Gill":   "Shubman Gill",
    "Wriddhiman Saha":"Wriddhiman Saha",
    "HH Pandya":      "Hardik Pandya",
    "Rashid Khan":    "Rashid Khan",
    "Mohammed Shami":  "Mohammed Shami",
    "Vijay Shankar":  "Vijay Shankar",
    "David Miller":   "David Miller",
    "Alzarri Joseph": "Alzarri Joseph",
    "Spencer Johnson":"Spencer Johnson",
    "Noor Ahmad":     "Noor Ahmad",

    # Punjab Kings
    "Shikhar Dhawan": "Shikhar Dhawan",
    "Prabhsimran Singh": "Prabhsimran Singh",
    "Liam Livingstone": "Liam Livingstone",
    "Sam Curran":     "Sam Curran",
    "Kagiso Rabada":  "Kagiso Rabada",
    "Arshdeep Singh": "Arshdeep Singh",
    "Rilee Rossouw":  "Rilee Rossouw",
    "Jonny Bairstow": "Jonny Bairstow",

    # Lucknow Super Giants
    "KL Rahul":       "KL Rahul",
    "Quinton de Kock":"Quinton de Kock",
    "Marcus Stoinis":  "Marcus Stoinis",
    "Deepak Hooda":   "Deepak Hooda",
    "Ravi Bishnoi":   "Ravi Bishnoi",
    "Avesh Khan":     "Avesh Khan",
    "Mark Wood":      "Mark Wood",
    "Nicholas Pooran":"Nicholas Pooran",
    "Kyle Mayers":    "Kyle Mayers",

    "KD Karthik":     "Dinesh Karthik",
    "Nithish Kumar Reddy": "Nitish Kumar Reddy",
    "JD Unadkat":     "Jaydev Unadkat",
    "PWH de Silva":   "Wanindu Hasaranga",

    # Conflicts resolved manually
    "A Nortje":       "Anrich Nortje",
    "A Singh":        "Arshdeep Singh",
    "C Green":        "Cameron Green",
    "K Yadav":        "Kuldeep Yadav",
    "L Ngidi":        "Lungi Ngidi",
    "M Pathirana":    "Matheesha Pathirana",
    "M Rawat":        "Mahesh Rawat",
    "N Saini":        "Navdeep Saini",
    "R Bishnoi":      "Ravi Bishnoi",
    "R Sharma":       "Rohit Sharma",
    "T Banton":       "Tom Banton",

    # More legends and frequent players
    "SR Tendulkar":   "Sachin Tendulkar",
    "VVS Laxman":     "VVS Laxman",
    "DR Smith":       "Dwayne Smith",
    "KA Pollard":     "Kieron Pollard",
    "DJ Bravo":       "Dwayne Bravo",
    "MJ McClenaghan": "Mitchell McClenaghan",
    "JP Faulkner":    "James Faulkner",
    "GD Phillips":    "Glenn Phillips",
    "AD Hales":       "Alex Hales",
    "JM Bairstow":    "Jonny Bairstow",
    "EJG Morgan":     "Eoin Morgan",
    "BA Stokes":      "Ben Stokes",
    "CR Woakes":      "Chris Woakes",
    "SCJ Broad":      "Stuart Broad",
    "JE Root":        "Joe Root",
    "LS Livingstone": "Liam Livingstone",
    "MJ Clarke":      "Michael Clarke",
    "SPD Smith":      "Steve Smith",
    "DA Warner":      "David Warner",
    "GJ Bailey":      "George Bailey",
    "XJ Doherty":     "Xavier Doherty",
    "CJ McKay":       "Clint McKay",
    "AC Voges":       "Adam Voges",
    "NM Coulter-Nile":"Nathan Coulter-Nile",
    "JW Hastings":    "John Hastings",
    "CJ Ferguson":    "Cameron Ferguson",
    "MR Marsh":       "Mitchell Marsh",
    "SE Marsh":       "Shaun Marsh",
    "Imran Tahir":    "Imran Tahir",
    "Imran Nazir":    "Imran Nazir",
    "SP Fleming":     "Stephen Fleming",
    "LL Tsotsobe":    "Lonwabo Tsotsobe",
    "RE van der Merwe":"Roelof van der Merwe",
    "JA Morkel":      "Albie Morkel",
    "JP Duminy":      "Jean-Paul Duminy",
    "RJ Peterson":    "Robin Peterson",
    "HM Amla":        "Hashim Amla",
    "F du Plessis":   "Faf du Plessis",
    "Q de Kock":      "Quinton de Kock",
    "R McLaren":      "Ryan McLaren",
    "B McCullum":     "Brendon McCullum",
    "JDP Oram":       "Jacob Oram",
    "SE Bond":        "Shane Bond",
    "MJ Guptill":     "Martin Guptill",
    "CJ Anderson":    "Corey Anderson",
    "AF Milne":       "Adam Milne",
    "NL McCullum":    "Nathan McCullum",
    "KS Williamson":  "Kane Williamson",
    "TWM Latham":     "Tom Latham",
    "LRPL Taylor":    "Ross Taylor",
    "MJ Santner":     "Mitchell Santner",
    "TR Southee":     "Tim Southee",
    "TG Southee":     "Tim Southee",
    "BJ Watling":     "BJ Watling",
    "Shahid Afridi":  "Shahid Afridi",
    "Shoaib Akhtar":  "Shoaib Akhtar",
    "Mohammad Hafeez":"Mohammad Hafeez",
    "Sohail Tanvir":  "Sohail Tanvir",
    "Kamran Akmal":   "Kamran Akmal",
    "Umar Gul":       "Umar Gul",
    "Shakib Al Hasan":"Shakib Al Hasan",
}

# ── Step 3: Auto-resolve remaining using last name matching ───────────────────
lastname_to_full = defaultdict(list)
for name in full_names:
    parts = name.strip().split()
    if parts:
        lastname_to_full[parts[-1].lower()].append(name.strip())

def try_auto_match(abbrev):
    parts = abbrev.strip().split()
    if len(parts) < 2:
        return None
    initials = parts[0]
    last_name = parts[-1]
    candidates = lastname_to_full.get(last_name.lower(), [])
    def matches(full, inits):
        name_parts = full.strip().split()
        if len(name_parts) < 2:
            return False
        first_initials = "".join(p[0].upper() for p in name_parts[:-1])
        return first_initials.startswith(inits.upper())
    matched = [c for c in candidates if matches(c, initials)]
    return matched[0].strip() if len(matched) == 1 else None

# ── Step 4: Build final name map ──────────────────────────────────────────────
with open("data/processed/player_career_stats.json") as f:
    stats = json.load(f)

name_map = {}
for abbrev in stats.keys():
    if abbrev in MANUAL_MAP:
        name_map[abbrev] = MANUAL_MAP[abbrev]
    elif abbrev in full_names:
        name_map[abbrev] = abbrev.strip()
    else:
        auto = try_auto_match(abbrev)
        if auto:
            name_map[abbrev] = auto
        else:
            name_map[abbrev] = abbrev   # keep abbreviated — fringe/retired player

# ── Step 5: Rebuild player stats with full names as keys ─────────────────────
fullname_stats = {}
duplicates = []

for abbrev, player_data in stats.items():
    full = name_map.get(abbrev, abbrev)
    if full in fullname_stats:
        # Merge by keeping higher caps (more complete record)
        if player_data.get("ipl_caps", 0) > fullname_stats[full].get("ipl_caps", 0):
            fullname_stats[full] = player_data
        duplicates.append((abbrev, full))
    else:
        fullname_stats[full] = player_data

# ── Step 6: Also build reverse map (full -> abbrev) for lookup ────────────────
reverse_map = {v: k for k, v in name_map.items()}

# ── Save ──────────────────────────────────────────────────────────────────────
with open("data/processed/player_name_map.json", "w") as f:
    json.dump(name_map, f, indent=2, ensure_ascii=False)

with open("data/processed/player_career_stats_fullnames.json", "w") as f:
    json.dump(fullname_stats, f, indent=2, ensure_ascii=False)

with open("api/data/player_stats.json", "w") as f:
    json.dump(fullname_stats, f, indent=2, ensure_ascii=False)

# ── Summary ───────────────────────────────────────────────────────────────────
resolved   = sum(1 for k, v in name_map.items() if k != v)
still_abbr = sum(1 for k, v in name_map.items() if k == v)

print(f"\n=== Player Name Database Built ===")
print(f"Total players:          {len(stats)}")
print(f"Resolved to full name:  {resolved}")
print(f"Still abbreviated:      {still_abbr} (fringe/retired players)")
print(f"Final DB size:          {len(fullname_stats)} unique players")
print(f"Duplicates merged:      {len(duplicates)}")
print()
print("Key player check:")
for name in ["Virat Kohli", "Rohit Sharma", "MS Dhoni", "Jasprit Bumrah",
             "Ravindra Jadeja", "Hardik Pandya", "Ruturaj Gaikwad",
             "Josh Hazlewood", "Pat Cummins", "Travis Head",
             "Yashasvi Jaiswal", "Shubman Gill", "Rashid Khan",
             "Kuldeep Yadav", "Arshdeep Singh", "Mohammed Shami"]:
    found = name in fullname_stats
    caps  = fullname_stats[name]["ipl_caps"] if found else 0
    print(f"  {'FOUND' if found else 'MISSING':6}  {name} {'(caps: ' + str(caps) + ')' if found else ''}")

print()
print("Saved:")
print("  data/processed/player_name_map.json")
print("  data/processed/player_career_stats_fullnames.json")
print("  api/data/player_stats.json  (used by API)")
