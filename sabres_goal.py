#!/usr/bin/env python3
"""
Sabres Goal — Random goal from every Buffalo Sabres season since 2010-11,
with a running leaderboard of goals/assists/points from all goals displayed.

First run fetches ~16 seasons of data (~1,300 API calls, ~15-20 min).
Progress is saved season-by-season, so you can Ctrl-C and resume anytime.
Every run after the initial fetch is instant.

Usage:
    python3 sabres_goal.py              # random goal + leaderboard
    python3 sabres_goal.py --refresh    # re-fetch ALL seasons from the API
    python3 sabres_goal.py --reset      # clear the leaderboard only
"""

import json
import random
import sys
import os
import ssl
import urllib.request
from datetime import datetime

# Fix for macOS Python SSL certificate issue
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE  = os.path.join(SCRIPT_DIR, "sabres_goals_cache.json")
STATS_FILE  = os.path.join(SCRIPT_DIR, "sabres_stats.json")
TEAM_ABBREV = "BUF"

# Every season from 1990-91 through 2025-26
SEASONS = [f"{y}{y+1}" for y in range(1990, 2026)]

# ── NHL API helpers ────────────────────────────────────────────────────────────

def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "python-sabres-goal/1.0"})
    with urllib.request.urlopen(req, timeout=15, context=SSL_CONTEXT) as resp:
        return json.loads(resp.read())

def get_schedule(season):
    return fetch_json(f"https://api-web.nhle.com/v1/club-schedule-season/{TEAM_ABBREV}/{season}")

def get_play_by_play(game_id):
    return fetch_json(f"https://api-web.nhle.com/v1/gamecenter/{game_id}/play-by-play")

# ── Goal extraction ────────────────────────────────────────────────────────────

def extract_goals(pbp):
    goals = []

    away   = pbp.get("awayTeam", {})
    home   = pbp.get("homeTeam", {})
    buf_id = (away if away.get("abbrev") == TEAM_ABBREV else home).get("id")
    if buf_id is None:
        return goals

    players = {}
    for p in pbp.get("rosterSpots", []):
        pid   = p.get("playerId")
        first = p.get("firstName", {}).get("default", "")
        last  = p.get("lastName",  {}).get("default", "")
        players[pid] = f"{first} {last}".strip()

    game_date        = pbp.get("gameDate", "")
    away_abbrev      = away.get("abbrev", "???")
    home_abbrev      = home.get("abbrev", "???")
    # Store logo URLs directly from API — gives correct historical logo per game
    away_logo_url    = away.get("logo", f"https://assets.nhle.com/logos/nhl/svg/{away_abbrev}_light.svg")
    home_logo_url    = home.get("logo", f"https://assets.nhle.com/logos/nhl/svg/{home_abbrev}_light.svg")
    final_away_score = away.get("score")
    final_home_score = home.get("score")
    buf_is_home      = (buf_id == home.get("id"))
    buf_final        = final_home_score if buf_is_home else final_away_score
    opp_final        = final_away_score if buf_is_home else final_home_score
    if buf_final is not None and opp_final is not None:
        result = "W" if buf_final > opp_final else "L"
        final_str = f"{away_abbrev} {final_away_score}-{final_home_score} {home_abbrev} ({result})"
    else:
        final_str = None

    for play in pbp.get("plays", []):
        if play.get("typeDescKey") != "goal":
            continue

        details = play.get("details", {})
        if details.get("eventOwnerTeamId") != buf_id:
            continue

        period_desc = play.get("periodDescriptor", {})
        period_num  = period_desc.get("number", 0)
        if period_desc.get("periodType") == "SO":
            continue

        if   period_num == 1: period_str = "1st"
        elif period_num == 2: period_str = "2nd"
        elif period_num == 3: period_str = "3rd"
        else:                 period_str = f"{'2' if period_num == 5 else ''}OT"

        scorer_id  = details.get("scoringPlayerId")
        assist1_id = details.get("assist1PlayerId")
        assist2_id = details.get("assist2PlayerId")

        scorer  = players.get(scorer_id, f"#{scorer_id}")
        assists = [players.get(a, f"#{a}") for a in [assist1_id, assist2_id] if a]

        goals.append({
            "season":      pbp.get("season", ""),
            "date":        game_date,
            "matchup":     f"{away_abbrev} @ {home_abbrev}",
            "away_abbrev": away_abbrev,
            "home_abbrev": home_abbrev,
            "away_logo":   away_logo_url,
            "home_logo":   home_logo_url,
            "period":      period_str,
            "time":        play.get("timeInPeriod", "?:??"),
            "scorer":      scorer,
            "assists":     assists,
            "away_score":  details.get("awayScore"),
            "home_score":  details.get("homeScore"),
            "final":       final_str,
        })

    return goals

# ── Cache management ───────────────────────────────────────────────────────────
# Cache structure: { "seasons": { "20102011": { "fetched_at": "...", "goals": [...] }, ... } }

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            data = json.load(f)
        # Migrate old single-season cache format
        if "seasons" not in data:
            return {"seasons": {}}
        return data
    return {"seasons": {}}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

def fetch_season(season, cache, force=False):
    """Fetch one season into cache if not already present. Returns goal count."""
    if not force and season in cache["seasons"]:
        goals = cache["seasons"][season]["goals"]
        print(f"  {season_label(season)}  (cached — {len(goals)} goals)")
        return len(goals)

    try:
        schedule  = get_schedule(season)
        completed = [
            g for g in schedule.get("games", [])
            if g.get("gameState") in ("OFF", "FINAL", "CRIT")
            and g.get("gameType") == 2
        ]
    except Exception as e:
        print(f"  {season_label(season)}  schedule ERROR: {e}")
        return 0

    all_goals = []
    for i, game in enumerate(completed, 1):
        gid = game["id"]
        try:
            pbp   = get_play_by_play(gid)
            goals = extract_goals(pbp)
            all_goals.extend(goals)
        except Exception as e:
            print(f"    game {gid}: ERROR – {e}", file=sys.stderr)

        # Print progress on same line
        print(f"\r  {season_label(season)}  [{i:>2}/{len(completed)}] games …  ", end="", flush=True)

    cache["seasons"][season] = {
        "fetched_at": datetime.now().isoformat(),
        "goals":      all_goals,
    }
    save_cache(cache)   # save after each season so Ctrl-C doesn't lose work
    print(f"\r  {season_label(season)}  ✓  {len(all_goals)} goals{' ' * 20}")
    return len(all_goals)

def season_label(season):
    """'20102011' → '2010-11'"""
    return f"{season[:4]}-{season[6:]}"

def ensure_all_seasons(force=False, test=False):
    cache   = load_cache()
    seasons = ["20252026"] if test else SEASONS
    missing = [s for s in seasons if force or s not in cache["seasons"]]
    if missing:
        total_seasons = len(SEASONS)
        print(f"Fetching {len(missing)} season(s) of Sabres data …\n")
        total_goals = 0
        for season in seasons:
            total_goals += fetch_season(season, cache, force=force)
        print(f"\nDone. {total_goals} total goals cached across {total_seasons} seasons.\n")
    return cache

def all_goals(cache, test=False):
    seasons = ["20252026"] if test else SEASONS
    goals   = []
    for season in seasons:
        if season in cache["seasons"]:
            goals.extend(cache["seasons"][season]["goals"])
    return goals

# ── Stats tracking ─────────────────────────────────────────────────────────────

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE) as f:
            return json.load(f)
    return {}

def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)

def update_stats(stats, goal):
    def add(player, g=0, a=0):
        if player not in stats:
            stats[player] = {"G": 0, "A": 0, "P": 0}
        stats[player]["G"] += g
        stats[player]["A"] += a
        stats[player]["P"] += g + a

    add(goal["scorer"], g=1)
    for assistant in goal["assists"]:
        add(assistant, a=1)

    return stats

# ── Display ────────────────────────────────────────────────────────────────────

SABRES_BLUE = "\033[38;5;27m"
SABRES_GOLD = "\033[38;5;178m"
BOLD        = "\033[1m"
DIM         = "\033[2m"
RESET       = "\033[0m"

def display_goal(goal):
    date_str = goal["date"]
    try:
        date_str = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %-d, %Y")
    except Exception:
        pass

    season_str = season_label(str(goal.get("season", ""))) if goal.get("season") else ""
    assists    = goal["assists"]
    assist_str = ", ".join(assists) if assists else "Unassisted"

    print()
    print(f"{SABRES_BLUE}{BOLD}╔══════════════════════════════════╗{RESET}")
    print(f"{SABRES_BLUE}{BOLD}║{RESET}  {SABRES_GOLD}{BOLD}🏒  SABRES GOAL{RESET}                  {SABRES_BLUE}{BOLD}║{RESET}")
    print(f"{SABRES_BLUE}{BOLD}╠══════════════════════════════════╣{RESET}")
    print(f"{SABRES_BLUE}{BOLD}║{RESET}  📅  {date_str:<28}{SABRES_BLUE}{BOLD}║{RESET}")
    print(f"{SABRES_BLUE}{BOLD}║{RESET}  📆  {'Season ' + season_str:<28}{SABRES_BLUE}{BOLD}║{RESET}")
    print(f"{SABRES_BLUE}{BOLD}║{RESET}  🏟   {goal['matchup']:<28}{SABRES_BLUE}{BOLD}║{RESET}")
    print(f"{SABRES_BLUE}{BOLD}║{RESET}  ⏱   {goal['period']} — {goal['time']}{' ' * (25 - len(goal['time']))}{SABRES_BLUE}{BOLD}║{RESET}")
    if goal.get("final"):
        final_display = goal['final']
        print(f"{SABRES_BLUE}{BOLD}║{RESET}  🏁  {final_display:<28}{SABRES_BLUE}{BOLD}║{RESET}")
    print(f"{SABRES_BLUE}{BOLD}╠══════════════════════════════════╣{RESET}")
    print(f"{SABRES_BLUE}{BOLD}║{RESET}  {BOLD}⚡  {goal['scorer']:<30}{RESET}{SABRES_BLUE}{BOLD}║{RESET}")
    print(f"{SABRES_BLUE}{BOLD}║{RESET}  🍎  {assist_str:<28}{SABRES_BLUE}{BOLD}║{RESET}")
    print(f"{SABRES_BLUE}{BOLD}╚══════════════════════════════════╝{RESET}")

def display_leaderboard(stats):
    if not stats:
        return

    ranked = sorted(stats.items(), key=lambda x: (-x[1]["P"], -x[1]["G"]))
    col_w  = 22

    print()
    print(f"{SABRES_GOLD}{BOLD}  LEADERBOARD  (this session){RESET}")
    print(f"{DIM}  {'Player':<{col_w}}  {'G':>4}  {'A':>4}  {'P':>4}{RESET}")
    print(f"{DIM}  {'-' * col_w}  {'----':>4}  {'----':>4}  {'----':>4}{RESET}")
    for name, s in ranked:
        print(f"  {name:<{col_w}}  {s['G']:>4}  {s['A']:>4}  {s['P']:>4}")
    print()

# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    if "--reset" in sys.argv:
        if os.path.exists(STATS_FILE):
            os.remove(STATS_FILE)
        print("Leaderboard cleared.")
        return

    force   = "--refresh" in sys.argv
    test    = "--test" in sys.argv
    cache   = ensure_all_seasons(force=force or test, test=test)
    goals   = all_goals(cache, test=test)

    if not goals:
        print("No goals found — something went wrong fetching data.", file=sys.stderr)
        sys.exit(1)

    goal  = random.choice(goals)
    stats = load_stats()
    update_stats(stats, goal)
    save_stats(stats)

    display_goal(goal)
    display_leaderboard(stats)

if __name__ == "__main__":
    main()
