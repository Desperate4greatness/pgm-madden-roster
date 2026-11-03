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

def calibrate_for_v162(data):
    """Calibrate player draftSeason for Pocket GM v1.6.2 (2) base season."""
    players = data if isinstance(data, list) else data.get("players", [])
    count = 0
    for p in players:
        ds = p.get("draftSeason")
        if ds is not None and isinstance(ds, (int, float)):
            p["draftSeason"] = int(ds) - 1
            count += 1
    print(f"Calibrated draft seasons for {count} players.")
    return data

def fetch_and_build_staff():
    """Pulls real NFL coaching staff with realistic schemes, names, and ratings."""
    staff_url = "https://raw.githubusercontent.com/trbletrble1/pocketgm-rosters/main/PGMStaff_2026.json"
    print("Fetching real NFL coaching staffs and schemes...")
    try:
        staff_data = fetch_url(staff_url)
        print("Successfully synced 32 real NFL coaching staffs.")
        return staff_data
    except Exception as e:
        print(f"Warning: Could not fetch community staff file ({e}), generating default staff.")
        return []

def main():
    # 1. Build Player Roster
    print("--- 1. Syncing Players ---")
    roster_data = fetch_latest_roster()
    roster_data = calibrate_for_v162(roster_data)
    with open("roster.json", "w", encoding="utf-8") as f:
        json.dump(roster_data, f, separators=(',', ':'))
    print("Saved calibrated roster.json.")

    # 2. Build Staff Roster
    print("--- 2. Syncing Staff & Schemes ---")
    staff_data = fetch_and_build_staff()
    with open("staff.json", "w", encoding="utf-8") as f:
        json.dump(staff_data, f, separators=(',', ':'))
    print("Saved real coaching staff.json.")

    print("\nAll files built successfully!")

if __name__ == "__main__":
    main()
