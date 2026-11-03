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

def balance_roster(players):
    """
    Directly compresses the exact PGM schema keys:
    - rating & potential
    - burst, power, agility, speed
    - rushBlock, passBlock, skillMove, releaseLine, ballStrip, blockShedding, etc.
    """
    print(f"Applying schema-exact balance to {len(players)} players...")

    # Attributes in your JSON that blow up overalls and gameplay stats
    trench_stats = [
        "rushBlock", "passBlock", "blockShedding", "skillMove", 
        "releaseLine", "ballStrip", "power", "burst"
    ]
    general_stats = [
        "speed", "agility", "jumping", "intelligence", 
        "vision", "decisions", "discipline", "routeRun", 
        "trucking", "elusiveness", "zoneCover", "manCover"
    ]

    o_line = {"OT", "OG", "C"}
    d_front = {"DE", "DT", "OLB", "MLB"}

    for p in players:
        pos = p.get("position", "")
        age = p.get("age", 25)
        r = p.get("rating")

        # 1. Compress 'rating' (Ceiling ~90-91 instead of 98)
        if isinstance(r, (int, float)):
            if r > 80:
                p["rating"] = min(91, int(round(80 + ((r - 80) * 0.45))))
            elif r < 72:
                p["rating"] = int(round(72 - ((72 - r) * 0.55)))

        # 2. Compress Trench Stats (Linemen & Edge Rushers)
        # Squeezes 94-95 rushBlock/skillMove down to 85-88
        for stat in trench_stats:
            val = p.get(stat)
            if isinstance(val, (int, float)) and val > 80:
                if pos in o_line or pos in d_front:
                    p[stat] = min(88, int(round(80 + ((val - 80) * 0.40))))
                else:
                    p[stat] = min(90, int(round(80 + ((val - 80) * 0.48))))

        # 3. Compress General Performance Attributes
        for stat in general_stats:
            val = p.get(stat)
            if isinstance(val, (int, float)) and val > 85:
                p[stat] = min(90, int(round(85 + ((val - 85) * 0.45))))

        # 4. QB Scramble nerf
        if pos == "QB":
            spd = p.get("speed")
            if isinstance(spd, (int, float)) and spd > 78:
                p["speed"] = int(round(78 + ((spd - 78) * 0.40)))

        # 5. Potential & Veteran Decay
        pot = p.get("potential")
        cur_rating = p.get("rating", pot)
        if isinstance(pot, (int, float)):
            if age >= 29:
                p["potential"] = min(pot, cur_rating)
            elif age <= 23 and pot < cur_rating:
                p["potential"] = min(95, cur_rating + 4)
            elif pot > 85:
                # Soft-compress young potential ceiling
                p["potential"] = min(94, int(round(85 + ((pot - 85) * 0.55))))

    return players

def calibrate_for_v162(players):
    """Adjust draftSeason for Pocket GM v1.6.2 (2) base season."""
    count = 0
    for p in players:
        ds = p.get("draftSeason")
        if ds is not None and isinstance(ds, (int, float)):
            p["draftSeason"] = int(ds) - 1
            count += 1
    print(f"Calibrated draft seasons for {count} players.")
    return players

def fetch_real_staff():
    staff_url = "https://raw.githubusercontent.com/TheeDestroyer72/PGM21/refs/heads/main/PGMStaff2025-06-12.json"
    print("Fetching verified NFL coaching staff...")
    data = fetch_url(staff_url)
    if not data or len(data) == 0:
        raise RuntimeError("Staff data was empty!")
    print(f"Successfully loaded {len(data)} real NFL coaches and staff members.")
    return data

def main():
    print("--- 1. Syncing & Schema-Exact Balancing ---")
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
