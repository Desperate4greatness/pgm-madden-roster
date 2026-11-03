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
    1. Normalizes all player overalls around a 78 starter median.
    2. Directly compresses offensive and defensive linemen blocking/shedding 
       attributes so the game engine stops generating 97-98 overalls.
    3. Retains ranking order: elite linemen stay #1, but peak at 89-91 instead of 98.
    """
    players = data if isinstance(data, list) else data.get("players", [])
    print(f"Applying trench and parity compression to {len(players)} players...")

    high_impact_stats = [
        "speed", "acceleration", "strength", "agility",
        "catching", "throwingPower", "throwingAccuracy",
        "runBlocking", "passBlocking",
        "tackle", "passRush", "blockShedding", "coverage"
    ]

    o_line = {"OT", "OG", "C"}
    d_line = {"DE", "DT", "EDG", "EDGE", "DL"}

    for p in players:
        ovr = p.get("overall")
        pos = p.get("position", "")
        age = p.get("age", 25)

        # 1. Base Overall Compression around 78 median
        if isinstance(ovr, (int, float)):
            delta = ovr - 78
            p["overall"] = int(round(78 + (delta * 0.52)))

        # 2. General Attribute Soft-Cap
        for stat in high_impact_stats:
            val = p.get(stat)
            if isinstance(val, (int, float)) and val > 86:
                p[stat] = int(round(86 + ((val - 86) * 0.48)))

        # 3. LINEMAN SPECIAL BALANCE:
        # Compresses specific OL/DL stats so PGM calculates 89-91 instead of 97-98
        if pos in o_line:
            for b_stat in ["runBlocking", "passBlocking", "strength"]:
                b_val = p.get(b_stat)
                if isinstance(b_val, (int, float)) and b_val > 84:
                    p[b_stat] = int(round(84 + ((b_val - 84) * 0.42)))

        if pos in d_line:
            for d_stat in ["passRush", "blockShedding", "tackle", "strength"]:
                d_val = p.get(d_stat)
                if isinstance(d_val, (int, float)) and d_val > 84:
                    p[d_stat] = int(round(84 + ((d_val - 84) * 0.42)))

        # 4. Mobile QB Scramble Tuning
        if pos == "QB":
            spd = p.get("speed")
            if isinstance(spd, (int, float)) and spd > 80:
                p["speed"] = int(round(80 + ((spd - 80) * 0.45)))

        # 5. Veteran Potential Ceiling (Natural regression)
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
    # 1. Build & Balance Player Roster
    print("--- 1. Syncing & Balancing Players ---")
    roster_data = fetch_latest_roster()
    roster_data = calibrate_for_v162(roster_data)
    roster_data = balance_roster(roster_data)

    with open("roster.json", "w", encoding="utf-8") as f:
        json.dump(roster_data, f, separators=(',', ':'))
    print("Saved calibrated and balanced roster.json.")

    # 2. Build Staff Roster
    print("--- 2. Syncing Staff & Schemes ---")
    staff_data = fetch_real_staff()
    with open("staff.json", "w", encoding="utf-8") as f:
        json.dump(staff_data, f, separators=(',', ':'))
    print("Saved real coaching staff.json.")

    print("\nAll files built successfully!")

if __name__ == "__main__":
    main()
