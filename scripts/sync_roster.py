#!/usr/bin/env python3
"""
Pocket GM Football - Fully Automated Dynamic Weekly Synchronizer
Auto-detects the newest week, harmonizes Madden stats, and enforces the 53-man active limit.
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
    """Auto-detects the highest week folder in the 2026 season."""
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

    # Wide Receivers
    if pos == "WR":
        p["rushBlock"] = max(60, p.get("rushBlock", 55))
        p["passBlock"] = max(65, p.get("passBlock", 55))
        p["routeRun"] = max(p.get("routeRun", 70), rating - 4)
        p["releaseLine"] = max(p.get("releaseLine", 70), rating - 5)
        p["catching"] = max(p.get("catching", 70), rating - 4)

    # Quarterbacks
    elif pos == "QB":
        p["sPassAcc"] = max(p.get("sPassAcc", 70), rating - 8)
        p["mPassAcc"] = max(p.get("mPassAcc", 68), rating - 10)
        p["decisions"] = max(p.get("decisions", 75), rating - 6)

    # Running Backs
    elif pos == "RB":
        p["rushBlock"] = max(62, p.get("rushBlock", 60))
        p["passBlock"] = max(65, p.get("passBlock", 60))
        p["ballSecurity"] = max(p.get("ballSecurity", 75), rating - 6)

    # Tight Ends
    elif pos == "TE":
        p["rushBlock"] = max(68, p.get("rushBlock", 65))
        p["passBlock"] = max(70, p.get("passBlock", 65))
        p["catching"] = max(p.get("catching", 70), rating - 5)

    # Secondary
    elif pos in ["CB", "FS", "SS"]:
        cov = max(p.get("manCover", 70), p.get("zoneCover", 70))
        p["manCover"] = max(p.get("manCover", 65), cov - 8)
        p["zoneCover"] = max(p.get("zoneCover", 65), cov - 8)

    return p

def enforce_53_man_cutdowns(players: list) -> list:
    """Guarantees strict 53-man active rosters across all 32 teams."""
    pos_targets = {
        "QB": 2, "RB": 3, "WR": 6, "TE": 3,
        "OT": 4, "OG": 4, "C": 2,
        "DE": 4, "DT": 4, "OLB": 4, "MLB": 4,
        "CB": 5, "FS": 2, "SS": 2,
        "K": 1, "P": 1
    }

    teams = {}
    free_agents = []

    for p in players:
        t = p.get("teamID", "FA").upper()
        if t in ["FA", "FREE AGENT", "FREEAGENT", "NONE", ""]:
            p["teamID"] = "FA"
            free_agents.append(p)
        else:
            teams.setdefault(t, []).append(p)

    final_roster = []

    for team_id, roster in teams.items():
        roster.sort(key=lambda x: x.get("rating", 0), reverse=True)

        active_53 = []
        by_pos = {}
        for p in roster:
            by_pos.setdefault(p.get("position", "WR"), []).append(p)

        # 1. Positional Minimums
        for pos, count in pos_targets.items():
            avail = by_pos.get(pos, [])
            active_53.extend(avail[:count])
            by_pos[pos] = avail[count:]

        # 2. Fill to 53 with best remaining players
        remaining = []
        for pos, leftovers in by_pos.items():
            if pos not in ["K", "P"]:
                remaining.extend(leftovers)

        remaining.sort(key=lambda x: x.get("rating", 0), reverse=True)
        spots_needed = 53 - len(active_53)
        if spots_needed > 0:
            active_53.extend(remaining[:spots_needed])
            cuts = remaining[spots_needed:]
        else:
            cuts = remaining

        for pos in ["K", "P"]:
            cuts.extend(by_pos.get(pos, []))

        for p in active_53:
            p["teamID"] = team_id
            final_roster.append(p)

        for p in cuts:
            p["teamID"] = "FA"
            final_roster.append(p)

    final_roster.extend(free_agents)
    return final_roster

def main():
    target_url = get_latest_weekly_url()
    print(f"Downloading live roster from: {target_url}")
    players = fetch_json(target_url)
    print(f"Loaded {len(players)} total players.")

    # 1. Enforce 53-man active limits across all teams
    players = enforce_53_man_cutdowns(players)

    # 2. Apply Madden attribute harmonization
    for p in players:
        harmonize_player(p)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(players, f, indent=2)

    print(f"Successfully harmonized and locked to 53-man active rosters. Saved to {OUTPUT_FILE}.")

if __name__ == "__main__":
    main()
