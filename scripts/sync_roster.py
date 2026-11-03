#!/usr/bin/env python3
"""
Pocket GM Football - Universal Positional Harmonizer & 53-Man Cutdown Engine
Synchronizes Madden ratings and trims all 32 teams to active 53-man rosters.
"""

import json
import re
import urllib.request

SOURCE_PGM_URL = "https://raw.githubusercontent.com/rgennat/PocketGM-2026-Wiz-Roster/refs/heads/main/2026%20v5.0"
OUTPUT_FILE = "roster.json"

def clean_name(name: str) -> str:
    name = re.sub(r"[\.\']", "", name.lower().strip())
    return re.sub(r"\s+(jr|sr|ii|iii|iv|v)$", "", name)

def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def harmonize_position_attributes(pos: str, madden: dict, pgm: dict, target_ovr: int):
    if pos == "QB":
        pgm["sPassAcc"] = max(pgm.get("sPassAcc", 70), target_ovr - 8)
        pgm["mPassAcc"] = max(pgm.get("mPassAcc", 68), target_ovr - 10)
        pgm["dPassAcc"] = max(pgm.get("dPassAcc", 65), target_ovr - 12)
        pgm["decisions"] = max(pgm.get("decisions", 75), target_ovr - 6)
        pgm["intelligence"] = max(pgm.get("intelligence", 75), target_ovr - 6)
        pgm["vision"] = max(pgm.get("vision", 75), target_ovr - 5)
    elif pos == "RB":
        pgm["rushBlock"] = max(62, pgm.get("rushBlock", 60))
        pgm["passBlock"] = max(65, pgm.get("passBlock", 60))
        pgm["ballSecurity"] = max(pgm.get("ballSecurity", 75), target_ovr - 6)
        pgm["elusiveness"] = max(pgm.get("elusiveness", 70), target_ovr - 8)
        pgm["skillMove"] = max(pgm.get("skillMove", 70), target_ovr - 6)
    elif pos == "WR":
        pgm["rushBlock"] = max(60, pgm.get("rushBlock", 55))
        pgm["passBlock"] = max(65, pgm.get("passBlock", 55))
        pgm["routeRun"] = max(pgm.get("routeRun", 70), target_ovr - 4)
        pgm["releaseLine"] = max(pgm.get("releaseLine", 70), target_ovr - 5)
        pgm["catching"] = max(pgm.get("catching", 70), target_ovr - 4)
        pgm["intelligence"] = max(pgm.get("intelligence", 70), target_ovr - 6)
    elif pos == "TE":
        pgm["rushBlock"] = max(68, pgm.get("rushBlock", 65))
        pgm["passBlock"] = max(70, pgm.get("passBlock", 65))
        pgm["catching"] = max(pgm.get("catching", 70), target_ovr - 5)
        pgm["routeRun"] = max(pgm.get("routeRun", 65), target_ovr - 8)
    elif pos in ["OT", "OG", "C"]:
        pgm["discipline"] = max(78, pgm.get("discipline", 75))
        pgm["passBlock"] = max(pgm.get("passBlock", 70), target_ovr - 3)
        pgm["rushBlock"] = max(pgm.get("rushBlock", 70), target_ovr - 3)
        pgm["power"] = max(pgm.get("power", 75), target_ovr - 4)
    elif pos in ["DE", "DT", "OLB"]:
        pwm = int(madden.get("powerMoves", 70))
        fnm = int(madden.get("finesseMoves", 70))
        best_move = max(pwm, fnm)
        pgm["blockShedding"] = max(pgm.get("blockShedding", 70), int(round(0.6 * best_move + 0.4 * target_ovr)))
        pgm["tackle"] = max(pgm.get("tackle", 65), target_ovr - 6)
        pgm["ballStrip"] = max(pgm.get("ballStrip", 65), target_ovr - 8)
        if pos == "OLB":
            pgm["zoneCover"] = max(62, pgm.get("zoneCover", 50))
    elif pos in ["CB", "FS", "SS"]:
        primary_cov = max(pgm.get("manCover", 70), pgm.get("zoneCover", 70))
        pgm["manCover"] = max(pgm.get("manCover", 65), primary_cov - 8, target_ovr - 6)
        pgm["zoneCover"] = max(pgm.get("zoneCover", 65), primary_cov - 8, target_ovr - 6)
        pgm["tackle"] = max(pgm.get("tackle", 60), target_ovr - 12)
        pgm["intelligence"] = max(pgm.get("intelligence", 70), target_ovr - 6)
    elif pos in ["K", "P"]:
        pgm["kickAccuracy"] = max(pgm.get("kickAccuracy", 70), target_ovr)
        pgm["power"] = max(pgm.get("power", 75), target_ovr)

def enforce_53_man_cutdowns(players: list) -> list:
    """Trims every NFL team down to a realistic 53-man active roster and moves cuts to FA."""
    pos_requirements = {
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
            if t not in teams:
                teams[t] = []
            teams[t].append(p)

    final_roster = []
    total_cut = 0

    for team_id, roster in teams.items():
        # Sort players on the team from highest to lowest rating
        roster.sort(key=lambda x: x.get("rating", 0), reverse=True)

        active_53 = []
        by_pos = {}
        for p in roster:
            pos = p.get("position", "WR")
            by_pos.setdefault(pos, []).append(p)

        # 1. Fill positional minimums
        for pos, count in pos_requirements.items():
            avail = by_pos.get(pos, [])
            active_53.extend(avail[:count])
            by_pos[pos] = avail[count:]

        # 2. Fill remaining spots up to 53 with the highest-rated remaining players
        remaining = []
        for pos, leftover in by_pos.items():
            if pos not in ["K", "P"]:
                remaining.extend(leftover)

        remaining.sort(key=lambda x: x.get("rating", 0), reverse=True)
        spots_open = 53 - len(active_53)
        if spots_open > 0:
            active_53.extend(remaining[:spots_open])
            cuts = remaining[spots_open:]
        else:
            cuts = remaining

        # Add any extra kickers or punters to cuts
        for pos in ["K", "P"]:
            cuts.extend(by_pos.get(pos, []))

        # Assign active 53
        for p in active_53:
            p["teamID"] = team_id
            final_roster.append(p)

        # Move cut players to Free Agency
        for p in cuts:
            p["teamID"] = "FA"
            final_roster.append(p)
            total_cut += 1

    final_roster.extend(free_agents)
    print(f"Enforced 53-man active limits across all 32 teams. Cut {total_cut} inactive/camp players to Free Agency.")
    return final_roster

def main():
    print("Fetching Pocket GM base roster...")
    pgm_players = fetch_json(SOURCE_PGM_URL)

    # 1. Apply 53-Man Cutdown to remove camp bodies & waived players
    pgm_players = enforce_53_man_cutdowns(pgm_players)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(pgm_players, f, indent=2)

    print(f"Successfully processed {len(pgm_players)} players. Active 53-man rosters ready!")

if __name__ == "__main__":
    main()
