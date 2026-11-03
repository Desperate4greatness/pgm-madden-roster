import json
import urllib.request
import sys

def fetch_latest_roster():
    # Automatically scan from newest week backwards
    weeks = [f"week-{w:02d}" for w in range(18, 0, -1)]
    base_url = "https://raw.githubusercontent.com/AaronsAron/pocket-gm-rosters/main/pocket-gm-3-football/2026"
    
    for week in weeks:
        url = f"{base_url}/{week}/roster-01.json"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    print(f"Successfully downloaded roster from: {url}")
                    return json.loads(resp.read().decode("utf-8"))
        except Exception:
            continue
            
    raise RuntimeError("Could not find an active weekly roster.")

def calibrate_for_v162(data):
    """
    Pocket GM v1.6.2 (2) starts in the 2025 season.
    Shift draftSeason down by 1 so 2026 rookies become 2025 (active rookies with 'R' badge)
    and 2025 sophomores become 2024 (2nd-year players).
    """
    players = data if isinstance(data, list) else data.get("players", [])
    count = 0
    for p in players:
        ds = p.get("draftSeason")
        if ds is not None and isinstance(ds, (int, float)):
            p["draftSeason"] = int(ds) - 1
            count += 1
    print(f"Calibrated draft seasons for {count} players to match Pocket GM v1.6.2 (2).")
    return data

def main():
    print("Fetching latest community NFL roster...")
    data = fetch_latest_roster()
    
    print("Calibrating for Pocket GM v1.6.2 (2)...")
    data = calibrate_for_v162(data)
    
    print("Writing output to roster.json...")
    with open("roster.json", "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(',', ':'))
        
    print("Done! roster.json is ready.")

if __name__ == "__main__":
    main()
