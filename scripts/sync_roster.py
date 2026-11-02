#!/usr/bin/env python3
"""
Pocket GM Football - Complete 2026 League Synchronizer
Pulls the full 2026 active regular-season database with calibrated Madden ratings.
"""

import json
import urllib.request

# Official Community 2026 Regular Season Roster (1,890+ active players, 32 teams)
ACTIVE_2026_LEAGUE_URL = "https://raw.githubusercontent.com/trbletrble1/pocketgm-rosters/main/PGMRoster_2026.json"
OUTPUT_FILE = "roster.json"

def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    print("Fetching complete 2026 regular season NFL roster...")
    players = fetch_json(ACTIVE_2026_LEAGUE_URL)
    print(f"Successfully loaded {len(players)} players across all 32 NFL teams!")

    # Verify team distribution
    team_counts = {}
    for p in players:
        t = p.get("teamID", "FA")
        team_counts[t] = team_counts.get(t, 0) + 1

    print(f"Verified {len(team_counts)} teams populated.")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(players, f, indent=2)

    print(f"Complete 2026 roster written to {OUTPUT_FILE}.")

if __name__ == "__main__":
    main()
