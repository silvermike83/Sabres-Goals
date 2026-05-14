#!/usr/bin/env python3
"""
Sabres Goal of the Day
Randomly outputs a goal scored by the Buffalo Sabres in the 2025-26 NHL season.

First run fetches and caches all goals (~82 API calls, takes ~1-2 min).
Every run after that is instant.

Usage:
    python3 sabres_goal.py           # random goal
    python3 sabres_goal.py --refresh # force re-fetch from NHL API
"""

import json
import random
import sys
import os
import urllib.request
from datetime import datetime

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sabres_goals_cache.json")
TEAM_ABBREV = "BUF"
SEASON = "20252026"

# ── NHL API helpers ────────────────────────────────────────────────────────────

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "python-sabres-goal/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

def get_schedule():
    url = f"https://api-web.nhle.com/v1/club-schedule-season/{TEAM_ABBREV}/{SEASON}"
    return fetch_json(url)

def get_play_by_play(game_id):
    url = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/play-by-play"
    return fetch_json(url)

# ── Goal extraction ────────────────────────────────────────────────────────────

def extract_goals(pbp):
    """Return a list of Sabres goal dicts from a play-by-play response."""
    goals = []

    away = pbp.get("awayTeam", {})
    home = pbp.get("homeTeam", {})
    buf_id = (away if away.get("abbrev") == TEAM_ABBREV else home).get("id")
    if buf_id is None:
        return goals

    # Player ID → display name
    players = {}
    for p in pbp.get("rosterSpots", []):
        pid = p.get("playerId")
        first = p.get("firstName", {}).get("default", "")
        last  = p.get("lastName",  {}).get("default", "")
        players[pid] = f"{first} {last}".strip()

    game_date = pbp.get("gameDate", "")
    away_abbrev = away.get("abbrev", "???")
    home_abbrev = home.get("abbrev", "???")

    for play in pbp.get("plays", []):
        if play.get("typeDescKey") != "goal":
            continue

        details = play.get("details", {})
        if details.get("eventOwnerTeamId") != buf_id:
            continue

        period_desc = play.get("periodDescriptor", {})
        period_num  = period_desc.get("number", 0)
        period_type = period_desc.get("periodType", "")

        # Skip shootout
        if period_type == "SO":
            continue

        if period_num == 1:   period_str = "1st"
        elif period_num == 2: period_str = "2nd"
        elif period_num == 3: period_str = "3rd"
        else:
            period_str = f"{'2' if period_num == 5 else ''}OT"

        scorer_id  = details.get("scoringPlayerId")
        assist1_id = details.get("assist1PlayerId")
        assist2_id = details.get("assist2PlayerId")

        scorer  = players.get(scorer_id,  f"#{scorer_id}")
        assists = [players.get(a, f"#{a}") for a in [assist1_id, assist2_id] if a]

        strength_map = {"ev": "EV", "pp": "PP", "sh": "SH"}
        strength = strength_map.get(details.get("strength", "ev"), "EV")

        goals.append({
            "date":     game_date,
            "matchup":  f"{away_abbrev} @ {home_abbrev}",
            "period":   period_str,
            "time":     play.get("timeInPeriod", "?:??"),
            "scorer":   scorer,
            "assists":  assists,
            "strength": strength,
        })

    return goals

# ── Cache management ───────────────────────────────────────────────────────────

def build_cache():
    print("Fetching Sabres 2025-26 schedule…", file=sys.stderr)
    schedule  = get_schedule()
    completed = [
        g for g in schedule.get("games", [])
        if g.get("gameState") in ("OFF", "FINAL", "CRIT")
        and g.get("gameType") == 2          # regular season only
    ]
    print(f"Found {len(completed)} completed regular-season games. Pulling goals…", file=sys.stderr)

    all_goals = []
    for i, game in enumerate(completed, 1):
        gid = game["id"]
        try:
            pbp   = get_play_by_play(gid)
            goals = extract_goals(pbp)
            all_goals.extend(goals)
            print(f"  [{i:>2}/{len(completed)}] {game.get('gameDate',gid)}  {len(goals)} goals", file=sys.stderr)
        except Exception as e:
            print(f"  [{i:>2}/{len(completed)}] {gid}: ERROR – {e}", file=sys.stderr)

    cache = {"season": SEASON, "fetched_at": datetime.now().isoformat(), "goals": all_goals}
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

    print(f"\nCached {len(all_goals)} goals → {CACHE_FILE}", file=sys.stderr)
    return all_goals

def load_goals(force_refresh=False):
    if not force_refresh and os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            data = json.load(f)
        if data.get("season") == SEASON:
            return data["goals"]
    return build_cache()

# ── Display ────────────────────────────────────────────────────────────────────

SABRES_BLUE  = "\033[38;5;27m"
SABRES_GOLD  = "\033[38;5;178m"
BOLD         = "\033[1m"
RESET        = "\033[0m"

def display(goal):
    date_str = goal["date"]
    try:
        date_str = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %-d, %Y")
    except Exception:
        pass

    assists = goal["assists"]
    assist_str = ", ".join(assists) if assists else "Unassisted"

    print()
    print(f"{SABRES_BLUE}{BOLD}╔══════════════════════════════════╗{RESET}")
    print(f"{SABRES_BLUE}{BOLD}║{RESET}  {SABRES_GOLD}{BOLD}🏒  SABRES GOAL{RESET}                  {SABRES_BLUE}{BOLD}║{RESET}")
    print(f"{SABRES_BLUE}{BOLD}╠══════════════════════════════════╣{RESET}")
    print(f"{SABRES_BLUE}{BOLD}║{RESET}  📅  {date_str:<28}{SABRES_BLUE}{BOLD}║{RESET}")
    print(f"{SABRES_BLUE}{BOLD}║{RESET}  🏟   {goal['matchup']:<28}{SABRES_BLUE}{BOLD}║{RESET}")
    print(f"{SABRES_BLUE}{BOLD}║{RESET}  ⏱   {goal['period']} — {goal['time']}  [{goal['strength']}]{' ' * (18 - len(goal['time']))}{SABRES_BLUE}{BOLD}║{RESET}")
    print(f"{SABRES_BLUE}{BOLD}╠══════════════════════════════════╣{RESET}")
    print(f"{SABRES_BLUE}{BOLD}║{RESET}  {BOLD}⚡  {goal['scorer']:<30}{RESET}{SABRES_BLUE}{BOLD}║{RESET}")
    print(f"{SABRES_BLUE}{BOLD}║{RESET}  🍎  {assist_str:<28}{SABRES_BLUE}{BOLD}║{RESET}")
    print(f"{SABRES_BLUE}{BOLD}╚══════════════════════════════════╝{RESET}")
    print()

# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    refresh = "--refresh" in sys.argv
    goals   = load_goals(force_refresh=refresh)

    if not goals:
        print("No Sabres goals found — something went wrong.", file=sys.stderr)
        sys.exit(1)

    display(random.choice(goals))

if __name__ == "__main__":
    main()
