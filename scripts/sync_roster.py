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

def balance_stat_dict(d, pos):
    """Compresses ratings whether they live directly on player or inside a nested dict."""
    o_line = {"OT", "OG", "C", "T", "G"}
    d_line = {"DE", "DT", "EDG", "EDGE", "DL", "NT"}

    # Lineman target attributes
    ol_keys = ["runblocking", "passblocking", "runblock", "passblock", "strength"]
    dl_keys = ["passrush", "blockshedding", "blockshed", "tackle", "strength"]
    high_impact_keys = [
        "speed", "acceleration", "strength", "agility",
        "catching", "throwingpower", "throwingaccuracy",
        "runblocking", "passblocking", "tackle", "passrush", "blockshedding", "coverage"
    ]

    for k in list(d.keys()):
        val = d[k]
        if not isinstance(val, (int, float)):
            continue

        k_lower = k.lower()

        # 1. Specialized OL check
        if pos in o_line and k_lower in ol_keys and val > 84:
            d[k] = int(round(84 + ((val - 84) * 0.40)))

        # 2. Specialized DL/Edge check
        elif pos in d_line and k_lower in dl_keys and val > 84:
            d[k] = int(round(84 + ((val - 84) * 0.40)))

        # 3. High impact attributes soft-cap
        elif k_lower in high_impact_keys and val > 86:
            d[k] = int(round(86 + ((val - 86) * 0.48)))

        # 4. QB Scramble nerf
        elif pos == "QB" and k_lower == "speed" and val > 80:
            d[k] = int(round(80 + ((val - 80) * 0.45)))

def balance_roster(data):
    # Extract players whether the root is a list, dict with 'players', or dict with 'teams'
    players = []
    if isinstance(data, list):
        players = data
    elif isinstance(data, dict):
        if "players" in data:
            players = data["players"]
        elif "teams" in data:
            for t in data["teams"]:
                players.extend(t.get("players", t.get("roster", [])))

    print(f"Applying deep trench & parity compression to {len(players)} players...")
    modified_count = 0

    for p in players:
        pos = p.get("position", "") or p.get("pos", "")
        age = p.get("age", 25)

        # A. Compress Overall rating
        for ovr_key in ["overall", "ovr", "Overall", "Ovr"]:
            if ovr_key in p and isinstance(p[ovr_key], (int, float)):
                orig = p[ovr_key]
                p[ovr_key] = int(round(78 + ((orig - 78) * 0.52)))
                if orig != p[ovr_key]:
                    modified_count += 1

        # B. Balance root-level attributes
        balance_stat_dict(p, pos)

        # C. Balance nested attribute containers if present
        for nested in ["attributes", "skills", "ratings", "stats"]:
            if nested in p and isinstance(p[nested], dict):
                balance_stat_dict(p[nested], pos)

        # D. Veteran Potential Decay
        for pot_key in ["potential", "pot", "Potential"]:
            if pot_key in p and isinstance(p[pot_key], (int, float)) and age >= 29:
                curr_ovr = p.get("overall", p.get("ovr", p[pot_key]))
                p[pot_key] = min(p[pot_key], curr_ovr)

    print(f"Successfully balanced attributes and overalls for {modified_count} players.")
    return data

def calibrate_for_v162(data):
    """Adjust draftSeason for Pocket GM v1.6.2 (2) base season."""
    players = []
    if isinstance(data, list):
        players = data
    elif isinstance(data, dict):
        if "players" in data:
            players = data["players"]
        elif "teams" in data:
            for t in data["teams"]:
                players.extend(t.get("players", t.get("roster", [])))

    count = 0
    for p in players:
        for ds_key in ["draftSeason", "draft_season", "DraftSeason"]:
            if ds_key in p and isinstance(p[ds_key], (int, float)):
                p[ds_key] = int(p[ds_key]) - 1
                count += 1
    print(f"Calibrated draft seasons for {count} players.")
    return data

def fetch_real_staff():
    staff_url = "https://raw.githubusercontent.com/TheeDestroyer72/PGM21/refs/heads/main/PGMStaff2025-06-12.json"
    print("Fetching verified NFL coaching staff...")
    data = fetch_url(staff_url)
    if not data or len(data) == 0:
        raise RuntimeError("Staff data was empty!")
    print(f"Successfully loaded {len(data)} real NFL coaches and staff members.")
    return data

def main():
    print("--- 1. Syncing & Deep Balancing Players ---")
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
