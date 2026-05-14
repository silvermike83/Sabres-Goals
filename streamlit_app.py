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

# Sabres color eras:
#   Classic        1970-71 – 1995-96  royal blue + gold
#   Red & Black    1996-97 – 2005-06  black + red
#   Modern         2006-07 – present  royal blue + gold
ERA_COLORS = {
    "classic": {"bg": "#003087", "accent": "#FCB514", "label": "Classic (pre-1996)"},
    "red":     {"bg": "#111111", "accent": "#CC0000", "label": "Red & Black Era (1996–2006)"},
    "modern":  {"bg": "#003087", "accent": "#FCB514", "label": "Modern (2006–present)"},
}

def era_for_season(season):
    start = int(str(season)[:4]) if season else 9999
    if start < 1996:
        return ERA_COLORS["classic"]
    elif start < 2006:
        return ERA_COLORS["red"]
    else:
        return ERA_COLORS["modern"]

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
if "hat_trick_player" not in st.session_state:
    st.session_state.hat_trick_player = None
if "hat_trick_celebrated" not in st.session_state:
    st.session_state.hat_trick_celebrated = []

def update_stats(goal):
    stats  = st.session_state.stats
    scorer = goal["scorer"]

    def add(player, g=0, a=0):
        if player not in stats:
            stats[player] = {"G": 0, "A": 0, "P": 0}
        stats[player]["G"] += g
        stats[player]["A"] += a
        stats[player]["P"] += g + a

    add(scorer, g=1)
    for assistant in goal["assists"]:
        add(assistant, a=1)

    if stats[scorer]["G"] == 3 and scorer not in st.session_state.hat_trick_celebrated:
        st.session_state.hat_trick_player = scorer
        st.session_state.hat_trick_celebrated.append(scorer)
    else:
        st.session_state.hat_trick_player = None

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Sabres Goal",
    page_icon="🏒",
    layout="centered",
)

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
<script>
(function() {
  const pdoc = window.parent.document;
  const canvas = pdoc.createElement('canvas');
  canvas.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:99999;';
  pdoc.body.appendChild(canvas);

  const pw  = window.parent.innerWidth;
  const ph  = window.parent.innerHeight;
  canvas.width  = pw;
  canvas.height = ph;
  const ctx = canvas.getContext('2d');

  const particles = [];
  const COLORS = ['#FCB514','#003087','#ffffff','#ff4444','#44ff44','#ff44ff'];

  function explode(x, y) {
    for (let i = 0; i < 120; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = Math.random() * 6 + 2;
      particles.push({
        x, y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        alpha: 1,
        color: COLORS[Math.floor(Math.random() * COLORS.length)],
        size: Math.random() * 4 + 1,
        decay: Math.random() * 0.015 + 0.01,
        gravity: 0.12,
      });
    }
  }

  const bursts = 10;
  let fired = 0;
  const interval = setInterval(() => {
    explode(
      Math.random() * pw * 0.8 + pw * 0.1,
      Math.random() * ph * 0.5 + ph * 0.05
    );
    if (++fired >= bursts) clearInterval(interval);
  }, 250);

  function loop() {
    ctx.clearRect(0, 0, pw, ph);
    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];
      p.x += p.vx;  p.y += p.vy;
      p.vy += p.gravity;  p.vx *= 0.98;
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

if st.session_state.hat_trick_player:
    _player = st.session_state.hat_trick_player
    st.session_state.hat_trick_player = None   # clear immediately so it never re-fires
    components.html(f"""
    <script>
    (function() {{
      const pdoc   = window.parent.document;
      const banner = pdoc.createElement('div');
      banner.textContent = '🎩 HAT TRICK — {_player} 🎩';
      banner.style.cssText = `
        position:fixed; top:50%; left:50%;
        transform:translate(-50%, -50%) scale(0.5);
        z-index:99998;
        background: linear-gradient(135deg, #FCB514, #FFD966, #FCB514);
        color:#003087; text-align:center;
        font-size:52px; font-weight:900; letter-spacing:3px;
        padding:40px 60px; border-radius:20px;
        box-shadow:0 12px 48px rgba(0,0,0,0.6);
        opacity:0; font-family:sans-serif; line-height:1.3; white-space:nowrap;
        transition: transform 0.3s cubic-bezier(0.34,1.56,0.64,1), opacity 0.3s ease-out;
      `;
      pdoc.body.appendChild(banner);
      requestAnimationFrame(() => {{
        banner.style.transform = 'translate(-50%, -50%) scale(1)';
        banner.style.opacity = '1';
      }});
      function dismiss() {{
        banner.style.transition = 'opacity 0.4s';
        banner.style.opacity = '0';
        setTimeout(() => banner.remove(), 400);
      }}
      setTimeout(dismiss, 1000);
      pdoc.addEventListener('click', dismiss, {{ once: true }});
    }})();
    </script>
    """, height=0)

goal = st.session_state.last_goal
if goal:
    date_str = goal.get("date", "")
    try:
        date_str = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %-d, %Y")
    except Exception:
        pass

    season_str   = season_label(goal.get("season", "")) if goal.get("season") else "—"
    assists      = goal.get("assists", [])
    assist_str   = ", ".join(assists) if assists else "Unassisted"
    period       = goal.get("period", "")
    time_str     = goal.get("time", "")
    away_abbrev  = goal.get("away_abbrev") or goal.get("matchup", "@ ").split(" @ ")[0]
    home_abbrev  = goal.get("home_abbrev") or goal.get("matchup", "@ ").split(" @ ")[-1]
    away_score   = goal.get("away_score")
    home_score   = goal.get("home_score")
    era          = era_for_season(goal.get("season"))
    bg           = era["bg"]
    accent       = era["accent"]

    # Use logo URLs stored in cache (historically accurate); fall back to CDN pattern
    away_logo = goal.get("away_logo") or f"https://assets.nhle.com/logos/nhl/svg/{away_abbrev}_light.svg"
    home_logo = goal.get("home_logo") or f"https://assets.nhle.com/logos/nhl/svg/{home_abbrev}_light.svg"

    # White badge wrapping ensures logo visibility on any background colour
    badge = 'background:white; border-radius:6px; padding:3px 5px; display:inline-block; line-height:0; vertical-align:middle;'

    lbl = f'font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color:{accent}; margin-bottom:0.15rem;'
    val = 'font-size:1.1rem; font-weight:600; margin-bottom:0.9rem;'

    h = []
    h.append(f'<div style="background:{bg}; border-radius:12px; padding:1.5rem 2rem; margin:1rem 0; color:white;">')

    # Season + date
    h.append(f'<div style="{lbl}">Season</div>')
    h.append(f'<div style="{val}">{season_str} &middot; {date_str}</div>')

    # Logos + matchup
    h.append(f'<div style="{lbl}">Matchup</div>')
    h.append('<div style="margin-bottom:0.9rem;">')
    h.append(f'<span style="{badge}"><img src="{away_logo}" height="36"></span>')
    h.append(f'<strong style="font-size:1.1rem; margin:0 10px;">{away_abbrev} @ {home_abbrev}</strong>')
    h.append(f'<span style="{badge}"><img src="{home_logo}" height="36"></span>')
    h.append('</div>')

    # Score at time of goal
    if away_score is not None and home_score is not None:
        h.append(f'<div style="{lbl}">Score at Goal</div>')
        h.append(f'<div style="{val}">{away_abbrev} {away_score} &ndash; {home_score} {home_abbrev}</div>')

    # Period + time
    h.append(f'<div style="{lbl}">Time</div>')
    h.append(f'<div style="{val}">{period} &middot; {time_str}</div>')

    # Final result — always show row, use em-dash fallback if not in cache
    h.append(f'<div style="{lbl}">Final</div>')
    h.append(f'<div style="{val}">{goal.get("final") or "&mdash;"}</div>')

    # Scorer
    h.append(f'<div style="{lbl}">Goal</div>')
    h.append(f'<div style="font-size:1.4rem; font-weight:700; color:{accent}; margin-bottom:0.25rem;">&#9889; {goal["scorer"]}</div>')

    # Assists
    h.append(f'<div style="{lbl}">Assists</div>')
    h.append(f'<div style="font-size:1.1rem; font-weight:600; margin-bottom:0;">&#127822; {assist_str}</div>')

    h.append('</div>')

    st.markdown("".join(h), unsafe_allow_html=True)

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
