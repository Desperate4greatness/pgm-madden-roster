#!/usr/bin/env python3
"""
Pocket GM Football - Live 2026 Week 8 Roster Harmonizer
Auto-detects the newest week and applies Madden attribute harmonization.
Preserves all active rookies on their real NFL teams.
"""

import json
import urllib.request

REPO_API_URL = "https://api.github.com/repos/AaronsAron/pocket-gm-rosters/contents/pocket-gm-3-football/2026"
FALLBACK_URL = "https://raw.githubusercontent.com/AaronsAron/pocket-gm-rosters/refs/heads/main/pocket-gm-3-football/2026/week-08/roster-01.json"
OUTPUT_FILE = "roster.json"

def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get_latest_weekly_url() -> str:
    print("Checking for the latest available NFL week...")
    try:
        contents = fetch_json(REPO_API_URL)
        week_folders = [item["name"] for item in contents if item.get("type") == "dir" and item["name"].startswith("week-")]
        if week_folders:
            latest_week = sorted(week_folders)[-1]
            latest_url = f"https://raw.githubusercontent.com/AaronsAron/pocket-gm-rosters/refs/heads/main/pocket-gm-3-football/2026/{latest_week}/roster-01.json"
            print(f"Auto-detected newest release: {latest_week.upper()}!")
            return latest_url
    except Exception as e:
        print(f"Notice: Auto-detect encountered ({e}). Using verified fallback.")
    return FALLBACK_URL

def harmonize_player(p: dict) -> dict:
    pos = p.get("position", "WR").upper()
    rating = int(p.get("rating", 75))

    # WR: Protect route running and release
    if pos == "WR":
        p["rushBlock"] = max(60, p.get("rushBlock", 55))
        p["passBlock"] = max(65, p.get("passBlock", 55))
        p["routeRun"] = max(p.get("routeRun", 70), rating - 4)
        p["releaseLine"] = max(p.get("releaseLine", 70), rating - 5)
        p["catching"] = max(p.get("catching", 70), rating - 4)

    # QB: Protect short accuracy and decisions for scramblers
    elif pos == "QB":
        p["sPassAcc"] = max(p.get("sPassAcc", 70), rating - 8)
        p["mPassAcc"] = max(p.get("mPassAcc", 68), rating - 10)
        p["decisions"] = max(p.get("decisions", 75), rating - 6)

    # RB: Prevent pass-blocking penalties
    elif pos == "RB":
        p["rushBlock"] = max(62, p.get("rushBlock", 60))
        p["passBlock"] = max(65, p.get("passBlock", 60))
        p["ballSecurity"] = max(p.get("ballSecurity", 75), rating - 6)

    # TE: Receiving / blocking balance
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
    target_url = get_latest_weekly_url()
    print(f"Downloading live roster from: {target_url}")
    players = fetch_json(target_url)
    print(f"Loaded {len(players)} total players.")

    # Apply Madden attribute harmonization
    for p in players:
        harmonize_player(p)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(players, f, indent=2)

    print(f"Finished! Roster with active rookies written to {OUTPUT_FILE}.")

if __name__ == "__main__":
    main()
