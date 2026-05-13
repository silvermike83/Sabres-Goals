import streamlit as st
import json
import random
from datetime import datetime
from pathlib import Path

# ── Data loading ───────────────────────────────────────────────────────────────

@st.cache_data
def load_goals():
    cache_path = Path(__file__).parent / "sabres_goals_cache.json"
    with open(cache_path) as f:
        cache = json.load(f)

    goals = []
    # Support both the multi-season format and the old single-season format
    if "seasons" in cache:
        for season_data in cache["seasons"].values():
            goals.extend(season_data["goals"])
    elif "goals" in cache:
        goals = cache["goals"]
    return goals

def season_label(season):
    s = str(season)
    return f"{s[:4]}-{s[6:]}" if len(s) == 8 else s

# ── Session state init ─────────────────────────────────────────────────────────

if "stats" not in st.session_state:
    st.session_state.stats = {}
if "last_goal" not in st.session_state:
    st.session_state.last_goal = None

def update_stats(goal):
    stats = st.session_state.stats

    def add(player, g=0, a=0):
        if player not in stats:
            stats[player] = {"G": 0, "A": 0, "P": 0}
        stats[player]["G"] += g
        stats[player]["A"] += a
        stats[player]["P"] += g + a

    add(goal["scorer"], g=1)
    for assistant in goal["assists"]:
        add(assistant, a=1)

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Sabres Goal",
    page_icon="🏒",
    layout="centered",
)

st.markdown("""
<style>
    .goal-box {
        background: #003087;
        border-radius: 12px;
        padding: 1.5rem 2rem;
        margin: 1rem 0;
        color: white;
    }
    .goal-box .label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #fcb514;
        margin-bottom: 0.15rem;
    }
    .goal-box .value {
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 0.9rem;
    }
    .goal-box .scorer {
        font-size: 1.4rem;
        font-weight: 700;
        color: #fcb514;
        margin-bottom: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────

st.title("🏒 Sabres Goal")

goals = load_goals()
st.caption(f"Random goal from {len(goals):,} Sabres regular-season goals, 2010–11 through 2025–26.")

# ── Button ─────────────────────────────────────────────────────────────────────

if st.button("🎲  Random Goal", type="primary", use_container_width=True):
    goal = random.choice(goals)
    st.session_state.last_goal = goal
    update_stats(goal)

# ── Goal display ───────────────────────────────────────────────────────────────

goal = st.session_state.last_goal
if goal:
    date_str = goal.get("date", "")
    try:
        date_str = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %-d, %Y")
    except Exception:
        pass

    season_str  = season_label(goal.get("season", "")) if goal.get("season") else "—"
    assists     = goal.get("assists", [])
    assist_str  = ", ".join(assists) if assists else "Unassisted"
    strength    = goal.get("strength", "EV")
    period      = goal.get("period", "")
    time_str    = goal.get("time", "")
    matchup     = goal.get("matchup", "")

    st.markdown(f"""
    <div class="goal-box">
        <div class="label">Season</div>
        <div class="value">{season_str}</div>
        <div class="label">Date &amp; Matchup</div>
        <div class="value">{date_str} &nbsp;·&nbsp; {matchup}</div>
        <div class="label">Time</div>
        <div class="value">{period} &nbsp;·&nbsp; {time_str} &nbsp;·&nbsp; {strength}</div>
        <div class="label">Goal</div>
        <div class="scorer">⚡ {goal['scorer']}</div>
        <div class="label">Assists</div>
        <div class="value">🍎 {assist_str}</div>
    </div>
    """, unsafe_allow_html=True)

# ── Leaderboard ────────────────────────────────────────────────────────────────

if st.session_state.stats:
    st.markdown("---")
    st.subheader("Leaderboard")
    st.caption("Goals, assists, and points from goals shown this session.")

    ranked = sorted(
        st.session_state.stats.items(),
        key=lambda x: (-x[1]["P"], -x[1]["G"]),
    )

    # Build a simple HTML table (avoids pandas dependency)
    rows = "".join(
        f"<tr><td>{name}</td><td>{s['G']}</td><td>{s['A']}</td><td><strong>{s['P']}</strong></td></tr>"
        for name, s in ranked
    )
    st.markdown(f"""
    <table style="width:100%; border-collapse:collapse; font-size:0.9rem;">
        <thead>
            <tr style="border-bottom:2px solid #ccc; text-align:left;">
                <th style="padding:6px 8px;">Player</th>
                <th style="padding:6px 8px; text-align:center;">G</th>
                <th style="padding:6px 8px; text-align:center;">A</th>
                <th style="padding:6px 8px; text-align:center;">P</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    """, unsafe_allow_html=True)

    st.markdown("")
    if st.button("🗑  Reset Leaderboard"):
        st.session_state.stats = {}
        st.session_state.last_goal = None
        st.rerun()
