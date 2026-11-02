#!/usr/bin/env python3
"""
Pocket GM Football - Automated Madden Roster Synchronizer
Fetches the base PGM roster and merges live Madden ratings from EA's API.
"""

import json
import re
import time
import urllib.request
import uuid

# Base Pocket GM 2026 v5.0 roster
SOURCE_PGM_URL = "https://raw.githubusercontent.com/rgennat/PocketGM-2026-Wiz-Roster/refs/heads/main/2026%20v5.0"
# Official EA Madden Ratings API (paginated)
MADDEN_API_TEMPLATE = "https://ratings-api.ea.com/v2/entities/m25-ratings?limit={limit}&offset={offset}"
OUTPUT_FILE = "roster.json"

def clean_name(name: str) -> str:
    """Normalize player names for reliable cross-game matching."""
    name = re.sub(r"[\.\']", "", name.lower().strip())
    name = re.sub(r"\s+(jr|sr|ii|iii|iv|v)$", "", name)
    return name

def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def fetch_madden_database() -> dict:
    """Pulls all active NFL players from EA's public ratings API."""
    madden_players = {}
    limit = 100
    offset = 0

    print("Connecting to EA Sports Madden Ratings API...")
    while True:
        url = MADDEN_API_TEMPLATE.format(limit=limit, offset=offset)
        try:
            data = fetch_json(url)
            docs = data.get("docs", [])
            if not docs:
                break
            for doc in docs:
                fn = clean_name(doc.get("firstName", ""))
                ln = clean_name(doc.get("lastName", ""))
                if fn and ln:
                    madden_players[(fn, ln)] = doc
            offset += limit
            time.sleep(0.15)
        except Exception as e:
            print(f"API fetch notice at offset {offset}: {e}")
            break

    print(f"Retrieved {len(madden_players)} players from Madden.")
    return madden_players

def convert_player_stats(madden_doc: dict, pgm_player: dict) -> dict:
    pos = madden_doc.get("position", pgm_player.get("position", "WR")).upper()

    # Core Athleticism
    pgm_player["speed"] = int(madden_doc.get("speed", pgm_player.get("speed", 75)))
    agi = madden_doc.get("agility", pgm_player.get("agility", 75))
    cod = madden_doc.get("changeOfDirection", agi)
    pgm_player["agility"] = int(round(0.6 * agi + 0.4 * cod))
    pgm_player["burst"] = int(madden_doc.get("acceleration", pgm_player.get("burst", 75)))
    pgm_player["jumping"] = int(madden_doc.get("jumping", pgm_player.get("jumping", 70)))
    pgm_player["stamina"] = int(madden_doc.get("stamina", pgm_player.get("stamina", 75)))

    # Contextual Power: Throw Power (QB), Kick Power (K/P), or Strength (Others)
    if pos == "QB":
        pgm_player["power"] = int(madden_doc.get("throwPower", pgm_player.get("power", 85)))
    elif pos in ["K", "P"]:
        pgm_player["power"] = int(madden_doc.get("kickPower", pgm_player.get("power", 85)))
    else:
        pgm_player["power"] = int(madden_doc.get("strength", pgm_player.get("power", 70)))

    # Passing Attributes
    if pos == "QB":
        pgm_player["sPassAcc"] = int(madden_doc.get("shortThrowAccuracy", pgm_player.get("sPassAcc", 70)))
        pgm_player["mPassAcc"] = int(madden_doc.get("mediumThrowAccuracy", pgm_player.get("mPassAcc", 68)))
        pgm_player["dPassAcc"] = int(madden_doc.get("deepThrowAccuracy", pgm_player.get("dPassAcc", 65)))
        pgm_player["throwOnRun"] = int(madden_doc.get("throwOnRun", pgm_player.get("throwOnRun", 65)))
        pgm_player["vision"] = int(round(0.7 * madden_doc.get("awareness", 75) + 0.3 * madden_doc.get("throwUnderPressure", 70)))
    else:
        pgm_player["sPassAcc"] = pgm_player["mPassAcc"] = pgm_player["dPassAcc"] = pgm_player["throwOnRun"] = 0
        pgm_player["vision"] = int(madden_doc.get("ballCarrierVision", madden_doc.get("awareness", pgm_player.get("vision", 60))))

    # Rushing, Receiving & Ball Handling
    pgm_player["catching"] = int(round(0.6 * madden_doc.get("catching", pgm_player.get("catching", 50)) +
                                       0.4 * madden_doc.get("catchInTraffic", pgm_player.get("catching", 50))))
    srr = madden_doc.get("shortRouteRunning", 50)
    mrr = madden_doc.get("mediumRouteRunning", 50)
    drr = madden_doc.get("deepRouteRunning", 50)
    pgm_player["routeRun"] = int(round((srr + mrr + drr) / 3.0)) if any([srr, mrr, drr]) else pgm_player.get("routeRun", 50)
    pgm_player["releaseLine"] = int(madden_doc.get("release", pgm_player.get("releaseLine", 50)))

    spm = madden_doc.get("spinMove", 60)
    jkm = madden_doc.get("jukeMove", 60)
    sfa = madden_doc.get("stiffArm", 60)
    pgm_player["skillMove"] = int(round((spm + jkm + sfa) / 3.0))
    pgm_player["trucking"] = int(round(0.6 * madden_doc.get("trucking", 50) + 0.4 * madden_doc.get("breakTackle", 50)))
    pgm_player["elusiveness"] = int(round(0.6 * madden_doc.get("elusiveness", 50) + 0.4 * cod))
    pgm_player["ballSecurity"] = int(madden_doc.get("carrying", pgm_player.get("ballSecurity", 65)))

    # Blocking
    pgm_player["passBlock"] = int(round(0.5 * madden_doc.get("passBlock", pgm_player.get("passBlock", 50)) +
                                         0.25 * madden_doc.get("passBlockPower", 50) +
                                         0.25 * madden_doc.get("passBlockFinesse", 50)))
    pgm_player["rushBlock"] = int(round(0.5 * madden_doc.get("runBlock", pgm_player.get("rushBlock", 50)) +
                                         0.25 * madden_doc.get("runBlockPower", 50) +
                                         0.25 * madden_doc.get("runBlockFinesse", 50)))

    # Defense & Tackling
    pgm_player["tackle"] = int(round(0.7 * madden_doc.get("tackle", pgm_player.get("tackle", 50)) + 0.3 * madden_doc.get("pursuit", 50)))
    pwm = madden_doc.get("powerMoves", 50)
    fnm = madden_doc.get("finesseMoves", 50)
    bsh = madden_doc.get("blockShedding", pgm_player.get("blockShedding", 50))
    pgm_player["blockShedding"] = int(round(0.5 * bsh + 0.25 * pwm + 0.25 * fnm))
    pgm_player["manCover"] = int(madden_doc.get("manCoverage", pgm_player.get("manCover", 40)))
    pgm_player["zoneCover"] = int(madden_doc.get("zoneCoverage", pgm_player.get("zoneCover", 40)))
    pgm_player["ballStrip"] = int(round(0.6 * madden_doc.get("hitPower", 50) + 0.4 * madden_doc.get("playRecognition", 50)))
    pgm_player["kickAccuracy"] = int(madden_doc.get("kickAccuracy", pgm_player.get("kickAccuracy", 0)))

    # Inverted Durability: (High in PGM = Injury Prone)
    m_inj = madden_doc.get("injury", 85)
    pgm_player["injuryProne"] = max(10, min(95, int(105 - m_inj)))

    # Overall Rating & Potential
    raw_ovr = int(madden_doc.get("overall_rating", madden_doc.get("overallRating", pgm_player.get("rating", 75))))
    pgm_player["rating"] = raw_ovr
    dev = madden_doc.get("developmentTrait", "Normal")
    dev_bonus = {"X-Factor": 8, "Superstar": 5, "Star": 3}.get(dev, 1)
    pgm_player["potential"] = max(pgm_player["rating"], min(99, pgm_player["rating"] + dev_bonus))

    # Team updates
    team = madden_doc.get("team", "")
    if team and len(team) <= 3:
        pgm_player["teamID"] = team.upper()

    return pgm

def main():
    print("Downloading Pocket GM base roster...")
    pgm_players = fetch_json(SOURCE_PGM_URL)
    madden_db = fetch_madden_database()

    updated = 0
    for p in pgm_players:
        key = (clean_name(p.get("forename", "")), clean_name(p.get("surname", "")))
        if key in madden_db:
            convert_player_stats(madden_db[key], p)
            updated += 1

    print(f"Synchronized {updated} of {len(pgm_players)} players with current Madden data.")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(pgm_players, f, indent=2)
    print(f"Wrote updated roster to {OUTPUT_FILE}.")

if __name__ == "__main__":
    main()
