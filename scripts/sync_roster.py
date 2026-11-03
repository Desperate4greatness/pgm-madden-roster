#!/usr/bin/env python3
"""
Pocket GM Football - Live 2026 Week 8 Roster Harmonizer
Pulls the active Week 8 NFL database and applies Madden attribute harmonization.
"""

import json
import urllib.request

# The official Week 8 live roster (released November 2026)
WEEKLY_2026_ROSTER_URL = "https://raw.githubusercontent.com/AaronsAron/pocket-gm-rosters/refs/heads/main/pocket-gm-3-football/2026/week-08/roster-01.json"
OUTPUT_FILE = "roster.json"

def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def harmonize_player(p: dict) -> dict:
    pos = p.get("position", "WR").upper()
    rating = int(p.get("rating", 75))

    # Wide Receivers: Protect route-running and release
    if pos == "WR":
        p["rushBlock"] = max(60, p.get("rushBlock", 55))
        p["passBlock"] = max(65, p.get("passBlock", 55))
        p["routeRun"] = max(p.get("routeRun", 70), rating - 4)
        p["releaseLine"] = max(p.get("releaseLine", 70), rating - 5)
        p["catching"] = max(p.get("catching", 70), rating - 4)

    # Quarterbacks: Protect short accuracy & decisions for scramblers
    elif pos == "QB":
        p["sPassAcc"] = max(p.get("sPassAcc", 70), rating - 8)
        p["mPassAcc"] = max(p.get("mPassAcc", 68), rating - 10)
        p["decisions"] = max(p.get("decisions", 75), rating - 6)

    # Running Backs: Prevent pass-blocking penalty
    elif pos == "RB":
        p["rushBlock"] = max(62, p.get("rushBlock", 60))
        p["passBlock"] = max(65, p.get("passBlock", 60))
        p["ballSecurity"] = max(p.get("ballSecurity", 75), rating - 6)

    # Tight Ends: Receiving / Blocking balance
    elif pos == "TE":
        p["rushBlock"] = max(68, p.get("rushBlock", 65))
        p["passBlock"] = max(70, p.get("passBlock", 65))
        p["catching"] = max(p.get("catching", 70), rating - 5)

    # Secondary: Prevent Man vs Zone split penalties
    elif pos in ["CB", "FS", "SS"]:
        cov = max(p.get("manCover", 70), p.get("zoneCover", 70))
        p["manCover"] = max(p.get("manCover", 65), cov - 8)
        p["zoneCover"] = max(p.get("zoneCover", 65), cov - 8)

    return p

def main():
    print("Downloading official Week 8 live NFL roster...")
    players = fetch_json(WEEKLY_2026_ROSTER_URL)
    print(f"Successfully loaded {len(players)} players from Week 8 database!")

    # Apply Madden attribute harmonization across all players
    for p in players:
        harmonize_player(p)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(players, f, indent=2)

    print(f"Harmonized Week 8 roster written to {OUTPUT_FILE}.")

if __name__ == "__main__":
    main()
