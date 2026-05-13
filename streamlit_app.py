import streamlit as st
import streamlit.components.v1 as components
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
if "sort_by" not in st.session_state:
    st.session_state.sort_by = "P"
if "show_all" not in st.session_state:
    st.session_state.show_all = False
if "rob_ray" not in st.session_state:
    st.session_state.rob_ray = False

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
st.caption(f"Random goal from {len(goals):,} Sabres regular-season goals, 1990–91 through 2025–26.")

# ── Button ─────────────────────────────────────────────────────────────────────

if st.button("🎲  Random Goal", type="primary", use_container_width=True):
    goal = random.choice(goals)
    st.session_state.last_goal = goal
    st.session_state.rob_ray = (goal["scorer"].strip().lower() == "rob ray")
    update_stats(goal)

# ── Goal display ───────────────────────────────────────────────────────────────

ROB_RAY_FIREWORKS = """
<canvas id="fireworks" style="position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:9999;"></canvas>
<script>
(function() {
  const canvas = document.getElementById('fireworks');
  const ctx    = canvas.getContext('2d');
  canvas.width  = window.innerWidth;
  canvas.height = window.innerHeight;

  const particles = [];
  const COLORS = ['#fcb514','#003087','#ffffff','#ff4444','#44ff44','#ff44ff'];

  function explode(x, y) {
    for (let i = 0; i < 120; i++) {
      const angle    = Math.random() * Math.PI * 2;
      const speed    = Math.random() * 6 + 2;
      const color    = COLORS[Math.floor(Math.random() * COLORS.length)];
      const size     = Math.random() * 4 + 1;
      particles.push({
        x, y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        alpha: 1,
        color, size,
        decay: Math.random() * 0.015 + 0.01,
        gravity: 0.12,
      });
    }
  }

  // Fire several bursts
  const bursts = 10;
  let fired = 0;
  const interval = setInterval(() => {
    explode(
      Math.random() * canvas.width * 0.8 + canvas.width * 0.1,
      Math.random() * canvas.height * 0.5 + canvas.height * 0.05
    );
    fired++;
    if (fired >= bursts) clearInterval(interval);
  }, 250);

  function loop() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];
      p.x  += p.vx;
      p.y  += p.vy;
      p.vy += p.gravity;
      p.vx *= 0.98;
      p.alpha -= p.decay;
      if (p.alpha <= 0) { particles.splice(i, 1); continue; }
      ctx.globalAlpha = p.alpha;
      ctx.fillStyle   = p.color;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
    if (particles.length > 0 || fired < bursts) requestAnimationFrame(loop);
    else canvas.remove();
  }
  loop();
})();
</script>
"""

if st.session_state.rob_ray:
    components.html(ROB_RAY_FIREWORKS, height=0)

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

    # Sort controls
    col_g, col_a, col_p, col_reset = st.columns([1, 1, 1, 2])
    with col_g:
        if st.button("Sort: G", type="primary" if st.session_state.sort_by == "G" else "secondary", use_container_width=True):
            st.session_state.sort_by = "G"
            st.session_state.show_all = False
            st.rerun()
    with col_a:
        if st.button("Sort: A", type="primary" if st.session_state.sort_by == "A" else "secondary", use_container_width=True):
            st.session_state.sort_by = "A"
            st.session_state.show_all = False
            st.rerun()
    with col_p:
        if st.button("Sort: P", type="primary" if st.session_state.sort_by == "P" else "secondary", use_container_width=True):
            st.session_state.sort_by = "P"
            st.session_state.show_all = False
            st.rerun()
    with col_reset:
        if st.button("🗑  Reset Leaderboard", use_container_width=True):
            st.session_state.stats = {}
            st.session_state.last_goal = None
            st.session_state.show_all = False
            st.rerun()

    sort_key = st.session_state.sort_by
    ranked = sorted(
        st.session_state.stats.items(),
        key=lambda x: (-x[1][sort_key], -x[1]["P"]),
    )

    visible    = ranked if st.session_state.show_all else ranked[:10]
    remaining  = len(ranked) - len(visible)

    def header_arrow(col):
        return " ▼" if col == sort_key else ""

    rows = "".join(
        f"<tr><td style='padding:6px 8px;'>{name}</td>"
        f"<td style='padding:6px 8px; text-align:center;'>{'<strong>' if sort_key=='G' else ''}{s['G']}{'</strong>' if sort_key=='G' else ''}</td>"
        f"<td style='padding:6px 8px; text-align:center;'>{'<strong>' if sort_key=='A' else ''}{s['A']}{'</strong>' if sort_key=='A' else ''}</td>"
        f"<td style='padding:6px 8px; text-align:center;'>{'<strong>' if sort_key=='P' else ''}{s['P']}{'</strong>' if sort_key=='P' else ''}</td></tr>"
        for name, s in visible
    )
    st.markdown(f"""
    <table style="width:100%; border-collapse:collapse; font-size:0.9rem;">
        <thead>
            <tr style="border-bottom:2px solid #ccc; text-align:left;">
                <th style="padding:6px 8px;">Player</th>
                <th style="padding:6px 8px; text-align:center;">G{header_arrow('G')}</th>
                <th style="padding:6px 8px; text-align:center;">A{header_arrow('A')}</th>
                <th style="padding:6px 8px; text-align:center;">P{header_arrow('P')}</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    """, unsafe_allow_html=True)

    if remaining > 0:
        st.markdown("")
        if st.button(f"Show {remaining} more player{'s' if remaining != 1 else ''} ▼"):
            st.session_state.show_all = True
            st.rerun()
    elif st.session_state.show_all and len(ranked) > 10:
        st.markdown("")
        if st.button("Show less ▲"):
            st.session_state.show_all = False
            st.rerun()
