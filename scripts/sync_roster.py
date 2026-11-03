import json
import urllib.request
import sys

def fetch_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        if resp.status == 200:
            return json.loads(resp.read().decode("utf-8"))
    raise RuntimeError(f"Failed to fetch {url}")

def fetch_latest_roster():
    weeks = [f"week-{w:02d}" for w in range(18, 0, -1)]
    base_url = "https://raw.githubusercontent.com/AaronsAron/pocket-gm-rosters/main/pocket-gm-3-football/2026"
    for week in weeks:
        url = f"{base_url}/{week}/roster-01.json"
        try:
            data = fetch_url(url)
            print(f"Downloaded active player roster from: {url}")
            return data
        except Exception:
            continue
    raise RuntimeError("Could not find an active weekly roster.")

def balance_roster(data):
    """
    1. Soft-compresses 88+ individual attributes to maintain realistic stats.
    2. Adjusts backup QBs so starting QB injuries matter.
    3. Normalizes team parity: compresses runaway 85+ teams (DET, SF, LAR)
       and supports contender floors (BAL, BUF).
    """
    players = data if isinstance(data, list) else data.get("players", [])
    print(f"Balancing team rosters and attributes for {len(players)} players...")

    # Team abbreviation mapping / targets
    # Soft limits on runaway teams vs depressed contenders
    TEAM_DOWNSCALE = {"DET", "SF", "LAR"}
    TEAM_UPSCALE = {"BAL", "BUF", "KC"}

    high_impact_stats = [
        "speed", "acceleration", "catching", 
        "throwingPower", "throwingAccuracy", 
        "passRush"
    ]

    for p in players:
        team = p.get("team", "") or p.get("teamID", "")
        pos = p.get("position", "")
        ovr = p.get("overall", 70)
        age = p.get("age", 25)

        # 1. Soft-compress individual peak ratings
        for stat in high_impact_stats:
            val = p.get(stat)
            if isinstance(val, (int, float)) and val > 87:
                p[stat] = int(round(87 + ((val - 87) * 0.52)))

        # 2. Scramble tuning for mobile QBs
        if pos == "QB":
            spd = p.get("speed")
            if isinstance(spd, (int, float)) and spd > 82:
                p["speed"] = int(round(82 + ((spd - 82) * 0.45)))

        # 3. Overall Rating Compression (Star players)
        if isinstance(ovr, (int, float)) and ovr > 87:
            p["overall"] = int(round(87 + ((ovr - 87) * 0.55)))
            ovr = p["overall"]

        # 4. Team-Specific Parity Compression:
        # Pull down runaway team rosters slightly (-2 to high-end starters)
        if team in TEAM_DOWNSCALE and isinstance(ovr, (int, float)) and ovr >= 80:
            p["overall"] = max(78, ovr - 2)

        # Lift the starting core floor on contenders depressed by Madden depth grading (+2 to 74-82 starters)
        if team in TEAM_UPSCALE and isinstance(ovr, (int, float)) and 74 <= ovr <= 82:
            p["overall"] = min(84, ovr + 2)

        # 5. Offensive Line Ceiling (Prevents runaway team OVR spikes)
        if pos in ["OT", "OG", "C"] and isinstance(ovr, (int, float)) and ovr > 84:
            p["overall"] = int(round(84 + ((ovr - 84) * 0.50)))

        # 6. Veteran Potential Regression
        pot = p.get("potential")
        if pot is not None and isinstance(pot, (int, float)) and age >= 29:
            p["potential"] = min(pot, p.get("overall", pot))

    return data

def calibrate_for_v162(data):
    """Adjust draftSeason for Pocket GM v1.6.2 (2) base season."""
    players = data if isinstance(data, list) else data.get("players", [])
    count = 0
    for p in players:
        ds = p.get("draftSeason")
        if ds is not None and isinstance(ds, (int, float)):
            p["draftSeason"] = int(ds) - 1
            count += 1
    print(f"Calibrated draft seasons for {count} players.")
    return data

def fetch_real_staff():
    """Pulls verified real NFL coaching staff with all HC, OC, DC, and schemes."""
    staff_url = "https://raw.githubusercontent.com/TheeDestroyer72/PGM21/refs/heads/main/PGMStaff2025-06-12.json"
    print("Fetching verified NFL coaching staff...")
    data = fetch_url(staff_url)
    if not data or len(data) == 0:
        raise RuntimeError("Staff data was empty!")
    print(f"Successfully loaded {len(data)} real NFL coaches and staff members.")
    return data

def main():
    print("--- 1. Syncing & Balancing Players ---")
    roster_data = fetch_latest_roster()
    roster_data = calibrate_for_v162(roster_data)
    roster_data = balance_roster(roster_data)

    with open("roster.json", "w", encoding="utf-8") as f:
        json.dump(roster_data, f, separators=(',', ':'))
    print("Saved calibrated and balanced roster.json.")

    print("--- 2. Syncing Staff & Schemes ---")
    staff_data = fetch_real_staff()
    with open("staff.json", "w", encoding="utf-8") as f:
        json.dump(staff_data, f, separators=(',', ':'))
    print("Saved real coaching staff.json.")

    print("\nAll files built successfully!")

if __name__ == "__main__":
    main()
