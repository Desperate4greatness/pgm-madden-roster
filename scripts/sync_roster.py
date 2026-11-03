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

def compress_stat(val, baseline, factor, ceiling):
    """Monotonic soft-compression: preserves exact order, lowers the extreme ceiling."""
    if isinstance(val, (int, float)) and val > baseline:
        return min(ceiling, int(round(baseline + ((val - baseline) * factor))))
    return val

def balance_roster(players):
    """
    Applies tailored mathematical balance to every position group:
    QB, RB, WR, TE, OT/OG/C, DE/OLB, DT, MLB, CB, S, K, P.
    """
    print(f"Applying league-wide balance across all position groups for {len(players)} players...")

    for p in players:
        pos = p.get("position", "")
        age = p.get("age", 25)
        r = p.get("rating")

        # 1. League-wide Overall Rating normalization (Squeezes 98 down to 89-90)
        if isinstance(r, (int, float)):
            if r > 80:
                p["rating"] = min(90, int(round(80 + ((r - 80) * 0.45))))
            elif r < 72:
                p["rating"] = int(round(72 - ((72 - r) * 0.55)))

        # 2. Universal Physical Attributes
        for phys in ["burst", "power", "jumping", "agility"]:
            if phys in p:
                p[phys] = compress_stat(p[phys], baseline=84, factor=0.45, ceiling=89)

        # 3. Position-Specific Tuning

        # --- QUARTERBACKS (QB) ---
        if pos == "QB":
            for acc in ["sPassAcc", "mPassAcc", "dPassAcc", "throwOnRun"]:
                if acc in p:
                    p[acc] = compress_stat(p[acc], baseline=82, factor=0.45, ceiling=89)
            if "speed" in p:
                # Stops mobile QBs from accumulating 200+ scrambles
                p["speed"] = compress_stat(p["speed"], baseline=76, factor=0.40, ceiling=82)

        # --- RUNNING BACKS (RB) ---
        elif pos == "RB":
            for rb_stat in ["trucking", "elusiveness", "ballSecurity", "speed"]:
                if rb_stat in p:
                    p[rb_stat] = compress_stat(p[rb_stat], baseline=83, factor=0.45, ceiling=88)

        # --- WIDE RECEIVERS (WR) ---
        elif pos == "WR":
            for wr_stat in ["routeRun", "releaseLine", "catching", "speed"]:
                if wr_stat in p:
                    p[wr_stat] = compress_stat(p[wr_stat], baseline=83, factor=0.48, ceiling=90)

        # --- TIGHT ENDS (TE) ---
        elif pos == "TE":
            for te_stat in ["catching", "routeRun", "rushBlock", "passBlock"]:
                if te_stat in p:
                    p[te_stat] = compress_stat(p[te_stat], baseline=82, factor=0.45, ceiling=87)

        # --- OFFENSIVE LINE (OT, OG, C) ---
        elif pos in {"OT", "OG", "C"}:
            for ol_stat in ["rushBlock", "passBlock", "releaseLine"]:
                if ol_stat in p:
                    p[ol_stat] = compress_stat(p[ol_stat], baseline=80, factor=0.40, ceiling=87)

        # --- EDGE RUSHERS (DE, OLB) ---
        elif pos in {"DE", "OLB"}:
            for edge_stat in ["skillMove", "releaseLine", "ballStrip", "blockShedding", "tackle"]:
                if edge_stat in p:
                    p[edge_stat] = compress_stat(p[edge_stat], baseline=80, factor=0.45, ceiling=89)

        # --- INTERIOR DEFENSIVE LINE (DT) ---
        elif pos == "DT":
            for dt_stat in ["blockShedding", "tackle", "ballStrip"]:
                if dt_stat in p:
                    p[dt_stat] = compress_stat(p[dt_stat], baseline=80, factor=0.42, ceiling=87)

        # --- LINEBACKERS (MLB, LB) ---
        elif pos in {"MLB", "LB"}:
            for lb_stat in ["tackle", "blockShedding", "zoneCover", "manCover"]:
                if lb_stat in p:
                    p[lb_stat] = compress_stat(p[lb_stat], baseline=81, factor=0.44, ceiling=88)

        # --- SECONDARY: CORNERBACKS (CB) & SAFETIES (S) ---
        elif pos in {"CB", "S"}:
            for db_stat in ["manCover", "zoneCover", "ballStrip", "releaseLine", "tackle", "speed"]:
                if db_stat in p:
                    p[db_stat] = compress_stat(p[db_stat], baseline=83, factor=0.45, ceiling=89)

        # --- SPECIAL TEAMS: KICKERS & PUNTERS (K, P) ---
        elif pos in {"K", "P"}:
            if "kickAccuracy" in p:
                p["kickAccuracy"] = compress_stat(p["kickAccuracy"], baseline=82, factor=0.45, ceiling=88)

        # 4. Intelligence & Vision Sanity
        for mental in ["intelligence", "vision", "decisions", "discipline"]:
            if mental in p:
                p[mental] = compress_stat(p[mental], baseline=85, factor=0.45, ceiling=90)

        # 5. Potential & Veteran Progression Control
        pot = p.get("potential")
        cur_r = p.get("rating", pot)
        if isinstance(pot, (int, float)):
            if age >= 29:
                p["potential"] = min(pot, cur_r)
            elif age <= 23 and pot < cur_r:
                p["potential"] = min(94, cur_r + 4)
            elif pot > 85:
                p["potential"] = min(93, int(round(85 + ((pot - 85) * 0.52))))

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
    print("--- 1. Syncing & League-Wide Balancing ---")
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
