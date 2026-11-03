#!/usr/bin/env python3
"""
Pocket GM Football - Universal Positional Harmonizer
Performs smooth, archetype-balanced attribute transitions from Madden to Pocket GM.
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
    """
    Applies position-specific attribute smoothing so Madden stars
    translate cleanly into Pocket GM without formula blind spots.
    """
    
    # ----------------------------------------------------
    # 1. QUARTERBACKS (QB)
    # ----------------------------------------------------
    if pos == "QB":
        # Ensure scrambling QBs don't have their PGM overall tanked by accuracy formulas
        pgm["sPassAcc"] = max(pgm.get("sPassAcc", 70), target_ovr - 8)
        pgm["mPassAcc"] = max(pgm.get("mPassAcc", 68), target_ovr - 10)
        pgm["dPassAcc"] = max(pgm.get("dPassAcc", 65), target_ovr - 12)
        pgm["decisions"] = max(pgm.get("decisions", 75), target_ovr - 6)
        pgm["intelligence"] = max(pgm.get("intelligence", 75), target_ovr - 6)
        pgm["vision"] = max(pgm.get("vision", 75), target_ovr - 5)

    # ----------------------------------------------------
    # 2. RUNNING BACKS (RB)
    # ----------------------------------------------------
    elif pos == "RB":
        # Prevent low Madden blocking from tanking elite rushers
        pgm["rushBlock"] = max(62, pgm.get("rushBlock", 60))
        pgm["passBlock"] = max(65, pgm.get("passBlock", 60))
        # Ensure primary ball-carrier traits match their overall
        pgm["ballSecurity"] = max(pgm.get("ballSecurity", 75), target_ovr - 6)
        pgm["elusiveness"] = max(pgm.get("elusiveness", 70), target_ovr - 8)
        pgm["skillMove"] = max(pgm.get("skillMove", 70), target_ovr - 6)

    # ----------------------------------------------------
    # 3. WIDE RECEIVERS (WR)
    # ----------------------------------------------------
    elif pos == "WR":
        # Run-blocking floor so blocking doesn't penalize pass-catchers
        pgm["rushBlock"] = max(60, pgm.get("rushBlock", 55))
        pgm["passBlock"] = max(65, pgm.get("passBlock", 55))
        # Anchor route running, release, and catching to star tier
        pgm["routeRun"] = max(pgm.get("routeRun", 70), target_ovr - 4)
        pgm["releaseLine"] = max(pgm.get("releaseLine", 70), target_ovr - 5)
        pgm["catching"] = max(pgm.get("catching", 70), target_ovr - 4)
        pgm["intelligence"] = max(pgm.get("intelligence", 70), target_ovr - 6)

    # ----------------------------------------------------
    # 4. TIGHT ENDS (TE)
    # ----------------------------------------------------
    elif pos == "TE":
        # Receiving TEs need solid baseline blocking in PGM
        pgm["rushBlock"] = max(68, pgm.get("rushBlock", 65))
        pgm["passBlock"] = max(70, pgm.get("passBlock", 65))
        # Anchor hands and route running
        pgm["catching"] = max(pgm.get("catching", 70), target_ovr - 5)
        pgm["routeRun"] = max(pgm.get("routeRun", 65), target_ovr - 8)

    # ----------------------------------------------------
    # 5. OFFENSIVE LINE (OT, OG, C)
    # ----------------------------------------------------
    elif pos in ["OT", "OG", "C"]:
        # PGM severely punishes low discipline on offensive linemen
        pgm["discipline"] = max(78, pgm.get("discipline", 75))
        pgm["passBlock"] = max(pgm.get("passBlock", 70), target_ovr - 3)
        pgm["rushBlock"] = max(pgm.get("rushBlock", 70), target_ovr - 3)
        pgm["power"] = max(pgm.get("power", 75), target_ovr - 4)

    # ----------------------------------------------------
    # 6. EDGE & DEFENSIVE LINE (DE, DT, OLB)
    # ----------------------------------------------------
    elif pos in ["DE", "DT", "OLB"]:
        # Blend Power Moves & Finesse Moves into Block Shedding
        pwm = int(madden.get("powerMoves", 70))
        fnm = int(madden.get("finesseMoves", 70))
        best_move = max(pwm, fnm)
        pgm["blockShedding"] = max(pgm.get("blockShedding", 70), int(round(0.6 * best_move + 0.4 * target_ovr)))
        pgm["tackle"] = max(pgm.get("tackle", 65), target_ovr - 6)
        pgm["ballStrip"] = max(pgm.get("ballStrip", 65), target_ovr - 8)
        # If an OLB is in a pass-coverage front, ensure coverage isn't 0
        if pos == "OLB":
            pgm["zoneCover"] = max(62, pgm.get("zoneCover", 50))

    # ----------------------------------------------------
    # 7. SECONDARY (CB, FS, SS)
    # ----------------------------------------------------
    elif pos in ["CB", "FS", "SS"]:
        # Prevent huge Man vs Zone split penalties in PGM schemes
        primary_cov = max(pgm.get("manCover", 70), pgm.get("zoneCover", 70))
        pgm["manCover"] = max(pgm.get("manCover", 65), primary_cov - 8, target_ovr - 6)
        pgm["zoneCover"] = max(pgm.get("zoneCover", 65), primary_cov - 8, target_ovr - 6)
        pgm["tackle"] = max(pgm.get("tackle", 60), target_ovr - 12)
        pgm["intelligence"] = max(pgm.get("intelligence", 70), target_ovr - 6)

    # ----------------------------------------------------
    # 8. SPECIAL TEAMS (K, P)
    # ----------------------------------------------------
    elif pos in ["K", "P"]:
        pgm["kickAccuracy"] = max(pgm.get("kickAccuracy", 70), target_ovr)
        pgm["power"] = max(pgm.get("power", 75), target_ovr)

def convert_player_stats(madden_doc: dict, pgm_player: dict) -> dict:
    pos = madden_doc.get("position", pgm_player.get("position", "WR")).upper()
    target_ovr = int(madden_doc.get("overall_rating", madden_doc.get("overallRating", pgm_player.get("rating", 75))))

    # 1. Base Physicals
    pgm_player["speed"] = int(madden_doc.get("speed", pgm_player.get("speed", 75)))
    agi = int(madden_doc.get("agility", pgm_player.get("agility", 75)))
    cod = int(madden_doc.get("changeOfDirection", agi))
    pgm_player["agility"] = int(round(0.6 * agi + 0.4 * cod))
    pgm_player["burst"] = int(madden_doc.get("acceleration", pgm_player.get("burst", 75)))
    pgm_player["jumping"] = int(madden_doc.get("jumping", pgm_player.get("jumping", 70)))
    pgm_player["stamina"] = int(madden_doc.get("stamina", pgm_player.get("stamina", 75)))

    # Power Context
    if pos == "QB":
        pgm_player["power"] = int(madden_doc.get("throwPower", pgm_player.get("power", 85)))
    elif pos in ["K", "P"]:
        pgm_player["power"] = int(madden_doc.get("kickPower", pgm_player.get("power", 85)))
    else:
        pgm_player["power"] = int(madden_doc.get("strength", pgm_player.get("power", 70)))

    # Passing
    if pos == "QB":
        pgm_player["sPassAcc"] = int(madden_doc.get("shortThrowAccuracy", pgm_player.get("sPassAcc", 70)))
        pgm_player["mPassAcc"] = int(madden_doc.get("mediumThrowAccuracy", pgm_player.get("mPassAcc", 68)))
        pgm_player["dPassAcc"] = int(madden_doc.get("deepThrowAccuracy", pgm_player.get("dPassAcc", 65)))
        pgm_player["throwOnRun"] = int(madden_doc.get("throwOnRun", pgm_player.get("throwOnRun", 65)))
        pgm_player["vision"] = int(round(0.7 * madden_doc.get("awareness", 75) + 0.3 * madden_doc.get("throwUnderPressure", 70)))
    else:
        pgm_player["sPassAcc"] = pgm_player["mPassAcc"] = pgm_player["dPassAcc"] = pgm_player["throwOnRun"] = 0
        pgm_player["vision"] = int(madden_doc.get("ballCarrierVision", madden_doc.get("awareness", pgm_player.get("vision", 60))))

    # Rushing & Receiving
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
    pgm_player["passBlock"] = int(round(0.5 * madden_doc.get("passBlock", 50) + 0.25 * madden_doc.get("passBlockPower", 50) + 0.25 * madden_doc.get("passBlockFinesse", 50)))
    pgm_player["rushBlock"] = int(round(0.5 * madden_doc.get("runBlock", 50) + 0.25 * madden_doc.get("runBlockPower", 50) + 0.25 * madden_doc.get("runBlockFinesse", 50)))

    # Defense
    pgm_player["tackle"] = int(round(0.7 * madden_doc.get("tackle", 50) + 0.3 * madden_doc.get("pursuit", 50)))
    bsh = madden_doc.get("blockShedding", 50)
    pwm = madden_doc.get("powerMoves", 50)
    fnm = madden_doc.get("finesseMoves", 50)
    pgm_player["blockShedding"] = int(round(0.5 * bsh + 0.25 * pwm + 0.25 * fnm))
    pgm_player["manCover"] = int(madden_doc.get("manCoverage", pgm_player.get("manCover", 40)))
    pgm_player["zoneCover"] = int(madden_doc.get("zoneCoverage", pgm_player.get("zoneCover", 40)))
    pgm_player["ballStrip"] = int(round(0.6 * madden_doc.get("hitPower", 50) + 0.4 * madden_doc.get("playRecognition", 50)))
    pgm_player["kickAccuracy"] = int(madden_doc.get("kickAccuracy", pgm_player.get("kickAccuracy", 0)))

    # Mental & Injury
    m_inj = int(madden_doc.get("injury", 85))
    pgm_player["injuryProne"] = max(10, min(95, int(105 - m_inj)))
    pgm_player["discipline"] = int(madden_doc.get("disciplineScore", pgm_player.get("discipline", 75)))
    awr = int(madden_doc.get("awareness", 75))
    pgm_player["intelligence"] = awr
    pgm_player["decisions"] = int(round(0.7 * awr + 0.3 * pgm_player["discipline"]))

    # Overall & Potential
    pgm_player["rating"] = target_ovr
    dev = madden_doc.get("developmentTrait", "Normal")
    bonus = {"X-Factor": 8, "Superstar": 5, "Star": 3}.get(dev, 1)
    pgm_player["potential"] = max(pgm_player["rating"], min(99, pgm_player["rating"] + bonus))

    # Apply Positional Harmonization Guardrails
    harmonize_position_attributes(pos, madden_doc, pgm_player, target_ovr)

    # Team Update
    team = madden_doc.get("team", madden_doc.get("team_short", ""))
    if team and len(team) <= 3:
        pgm_player["teamID"] = team.upper()

    return pgm_player

def main():
    print("Fetching Pocket GM base roster...")
    pgm_players = fetch_json(SOURCE_PGM_URL)
    
    # Example mid-season updates across multiple position groups
    madden_updates = [
        # QBs
        {"firstName": "Josh", "lastName": "Allen", "position": "QB", "team": "BUF", "overallRating": 99, "developmentTrait": "X-Factor", "throwPower": 99, "awareness": 97},
        {"firstName": "Lamar", "lastName": "Jackson", "position": "QB", "team": "BAL", "overallRating": 97, "developmentTrait": "X-Factor", "throwPower": 94, "awareness": 95},
        {"firstName": "Matthew", "lastName": "Stafford", "position": "QB", "team": "LAR", "overallRating": 99, "developmentTrait": "X-Factor", "throwPower": 95, "awareness": 98},
        # RBs
        {"firstName": "Saquon", "lastName": "Barkley", "position": "RB", "team": "PHI", "overallRating": 94, "developmentTrait": "Superstar", "speed": 93, "carrying": 92},
        {"firstName": "Derrick", "lastName": "Henry", "position": "RB", "team": "BAL", "overallRating": 95, "developmentTrait": "Superstar", "trucking": 98, "speed": 91},
        {"firstName": "Jahmyr", "lastName": "Gibbs", "position": "RB", "team": "DET", "overallRating": 89, "developmentTrait": "Star", "speed": 95, "elusiveness": 94},
        # WRs
        {"firstName": "Ja'Marr", "lastName": "Chase", "position": "WR", "team": "CIN", "overallRating": 99, "developmentTrait": "X-Factor", "speed": 96, "catching": 98},
        {"firstName": "Jaxon", "lastName": "Smith-Njigba", "position": "WR", "team": "SEA", "overallRating": 99, "developmentTrait": "X-Factor", "speed": 93, "routeRun": 98},
        {"firstName": "Davante", "lastName": "Adams", "position": "WR", "team": "NYJ", "overallRating": 93, "developmentTrait": "Superstar", "release": 96, "catching": 95},
        # TEs
        {"firstName": "Trey", "lastName": "McBride", "position": "TE", "team": "ARI", "overallRating": 99, "developmentTrait": "X-Factor", "catching": 96, "speed": 87},
        # OL
        {"firstName": "Penei", "lastName": "Sewell", "position": "OT", "team": "DET", "overallRating": 98, "developmentTrait": "Superstar", "passBlock": 97, "runBlock": 98},
        # Edge / DL
        {"firstName": "Myles", "lastName": "Garrett", "position": "DE", "team": "LAR", "overallRating": 99, "developmentTrait": "X-Factor", "powerMoves": 99, "finesseMoves": 93},
        {"firstName": "Micah", "lastName": "Parsons", "position": "DE", "team": "DAL", "overallRating": 98, "developmentTrait": "X-Factor", "speed": 93, "finesseMoves": 98},
        # Secondary
        {"firstName": "Christian", "lastName": "Gonzalez", "position": "CB", "team": "NE", "overallRating": 98, "developmentTrait": "Superstar", "manCoverage": 98, "zoneCoverage": 92}
    ]

    update_lookup = {(clean_name(u["firstName"]), clean_name(u["lastName"])): u for u in madden_updates}

    updated_count = 0
    for p in pgm_players:
        key = (clean_name(p.get("forename", "")), clean_name(p.get("surname", "")))
        if key in update_lookup:
            convert_player_stats(update_lookup[key], p)
            updated_count += 1

    print(f"Harmonized and updated {updated_count} players across all positional formulas!")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(pgm_players, f, indent=2)

if __name__ == "__main__":
    main()
