
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import os
import re
import html
import base64
import hashlib
from pathlib import Path

# --- PAGE SETUP ---
st.set_page_config(page_title="ISPN College Football Gameday", layout="wide", page_icon="🏈")
st.title("📺 ISPN College Football Gameday")

CURRENT_WEEK_NUMBER = 16   # Bowl Week 1 (post-season)
CURRENT_YEAR        = 2041  # Active dynasty season — increment each new year
IS_BOWL_WEEK       = True
BOWL_ROUND         = 1    # 1 = Bowl Week 1, 2 = Bowl Week 2 (semis/natty)

st.markdown("""
<style>
/* ── BASE ─────────────────────────────────────────────────────────────── */
.block-container {padding-top: 1rem; padding-bottom: 1rem; padding-left: 0.8rem; padding-right: 0.8rem;}
[data-testid="stHorizontalBlock"] {gap: 0.75rem;}

/* ── TABS: wrap on small screens ─────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {gap: 0.2rem; flex-wrap: wrap;}
.stTabs [data-baseweb="tab"] {
  height: auto; white-space: normal;
  padding: 0.3rem 0.55rem;
  font-size: 0.82rem;
}

/* ── DATAFRAMES: always scroll horizontally, never overflow ──────────── */
[data-testid="stDataFrame"] > div {overflow-x: auto !important;}
.stDataFrame {max-width: 100% !important;}

/* ── METRICS: allow natural wrapping ────────────────────────────────── */
[data-testid="metric-container"] {
  background: #1f2937;
  border: 1px solid #374151;
  border-radius: 10px;
  padding: 10px 12px;
}

/* ── MOBILE (<640px) ─────────────────────────────────────────────────── */
@media (max-width: 640px) {
  .block-container {padding-left: 0.4rem; padding-right: 0.4rem;}
  h1 {font-size: 1.35rem !important;}
  h2 {font-size: 1.15rem !important;}
  h3 {font-size: 1rem !important;}

  /* Stack ALL Streamlit columns vertically on phone */
  [data-testid="stHorizontalBlock"] {
    flex-direction: column !important;
    gap: 0.5rem !important;
  }
  [data-testid="stHorizontalBlock"] > [data-testid="column"] {
    width: 100% !important;
    min-width: 100% !important;
    flex: 1 1 100% !important;
  }

  /* Tabs font smaller */
  .stTabs [data-baseweb="tab"] {font-size: 0.72rem; padding: 0.25rem 0.35rem;}

  /* Plotly charts full width */
  .js-plotly-plot {max-width: 100% !important;}

  /* Expander headers easier to tap */
  [data-testid="stExpander"] summary {padding: 0.6rem 0.5rem !important;}

  /* Selectbox full width */
  [data-testid="stSelectbox"] {width: 100% !important;}

  /* Buttons easier to tap */
  [data-testid="stButton"] button {width: 100%; padding: 0.6rem;}

  /* File uploader full width */
  [data-testid="stFileUploader"] {width: 100% !important;}
}

/* ── TABLET (641–1024px) ─────────────────────────────────────────────── */
@media (min-width: 641px) and (max-width: 1024px) {
  h1 {font-size: 1.5rem !important;}
  .stTabs [data-baseweb="tab"] {font-size: 0.78rem; padding: 0.28rem 0.45rem;}
}
</style>
""", unsafe_allow_html=True)


TEAM_VISUALS = {
    "Florida": {"slug": "florida", "primary": "#0021A5", "secondary": "#FA4616"},
    "Florida State": {"slug": "florida-state", "primary": "#782F40", "secondary": "#CEB888"},
    "Texas Tech": {"slug": "texas-tech", "primary": "#CC0000", "secondary": "#000000"},
    "USF": {"slug": "south-florida", "primary": "#006747", "secondary": "#CFC493"},
    "South Florida": {"slug": "south-florida", "primary": "#006747", "secondary": "#CFC493"},
    "San Jose State": {"slug": "san-jose-state", "primary": "#0055A2", "secondary": "#E5A823"},
    "Bowling Green": {"slug": "bowling-green", "primary": "#FE5000", "secondary": "#4F2C1D"},
    "Rapid City": {"slug": "rapid-city", "primary": "#14B8A6", "secondary": "#F472B6"},
    "Panama City": {"slug": "panama-city", "primary": "#F97316", "secondary": "#000000"},
    "Hammond": {"slug": "hammond", "primary": "#16A34A", "secondary": "#14532D"},
    "Alabaster": {"slug": "alabaster", "primary": "#DC2626", "secondary": "#FACC15"},
    "Death Valley": {"slug": "death-valley", "primary": "#7C3AED", "secondary": "#000000"},
    "Gate City": {"slug": "gate-city", "primary": "#FACC15", "secondary": "#000000"},
    "Oklahoma State": {"slug": "oklahoma-state", "primary": "#FF7300", "secondary": "#000000"},
    "South Carolina": {"slug": "south-carolina", "primary": "#73000A", "secondary": "#000000"},
    "Appalachian State": {"slug": "app-state", "primary": "#FFCC00", "secondary": "#000000"},
    "San Diego State": {"slug": "san-diego-state", "primary": "#A6192E", "secondary": "#000000"},
    "Georgia Tech": {"slug": "georgia-tech", "primary": "#B3A369", "secondary": "#003057"},
    "NC State": {"slug": "nc-state", "primary": "#CC0000", "secondary": "#000000"},
    "Texas A&M": {"slug": "texas-am", "primary": "#500000", "secondary": "#FFFFFF"},
    "Alabama": {"slug": "alabama", "primary": "#9E1B32", "secondary": "#FFFFFF"},
    "Georgia": {"slug": "georgia", "primary": "#BA0C2F", "secondary": "#000000"},
    "Ohio State": {"slug": "ohio-state", "primary": "#BB0000", "secondary": "#666666"},
    "Michigan": {"slug": "michigan", "primary": "#00274C", "secondary": "#FFCB05"},
    "Notre Dame": {"slug": "notre-dame", "primary": "#0C2340", "secondary": "#C99700"},
    "Oregon": {"slug": "oregon", "primary": "#154733", "secondary": "#FEE123"},
    "Texas": {"slug": "texas", "primary": "#BF5700", "secondary": "#FFFFFF"},
    "Oklahoma": {"slug": "oklahoma", "primary": "#841617", "secondary": "#FDF9D8"},
    "Penn State": {"slug": "penn-state", "primary": "#041E42", "secondary": "#FFFFFF"},
    "LSU": {"slug": "lsu", "primary": "#461D7C", "secondary": "#FDD023"},
    "Miami": {"slug": "miami", "primary": "#F47321", "secondary": "#005030"},
    "Clemson": {"slug": "clemson", "primary": "#F56600", "secondary": "#522D80"},
    "Tennessee": {"slug": "tennessee", "primary": "#FF8200", "secondary": "#FFFFFF"},
    "USC": {"slug": "southern-california", "primary": "#990000", "secondary": "#FFC72C"},
    "Ole Miss": {"slug": "ole-miss", "primary": "#CE1126", "secondary": "#14213D"},
    "Auburn": {"slug": "auburn", "primary": "#0C2340", "secondary": "#E87722"},
    "Nebraska": {"slug": "nebraska", "primary": "#E41C38", "secondary": "#FFFFFF"},
    "Wisconsin": {"slug": "wisconsin", "primary": "#C5050C", "secondary": "#FFFFFF"},
    "Washington": {"slug": "washington", "primary": "#4B2E83", "secondary": "#B7A57A"},
    "UCLA": {"slug": "ucla", "primary": "#2774AE", "secondary": "#FFD100"},
    "TCU": {"slug": "tcu", "primary": "#4D1979", "secondary": "#A3A9AC"},
    "Utah": {"slug": "utah", "primary": "#CC0000", "secondary": "#000000"},
    "Rapid City": {"slug": "rapid-city", "primary": "#00B8B8", "secondary": "#FF4FA3"},
    "Panama City": {"slug": "panama-city", "primary": "#FF7A00", "secondary": "#000000"},
    "Hammond": {"slug": "hammond", "primary": "#1F8F4E", "secondary": "#0B4F2A"},
    "Alabaster": {"slug": "alabaster", "primary": "#D72638", "secondary": "#FFD23F"},
    "Death Valley": {"slug": "death-valley", "primary": "#6A0DAD", "secondary": "#000000"},
    "Gate City": {"slug": "gate-city", "primary": "#FFD23F", "secondary": "#000000"},
}

TEAM_ALIASES = {
    "Florida": ["florida", "florida gators"],
    "Florida State": ["florida state", "florida state seminoles", "fsu"],
    "Texas Tech": ["texas tech", "texas tech red raiders"],
    "USF": ["usf", "south florida", "south florida bulls"],
    "South Florida": ["usf", "south florida", "south florida bulls"],
    "San Jose State": ["san jose state", "san jose state spartans", "sjsu"],
    "Bowling Green": ["bowling green", "bowling green falcons"],
    "Rapid City": ["rapid city"],
    "Panama City": ["panama city"],
    "Hammond": ["hammond"],
    "Alabaster": ["alabaster"],
    "Death Valley": ["death valley"],
    "Gate City": ["gate city"],
    "Oklahoma State": ["oklahoma state", "oklahoma state cowboys", "oklahoma st"],
    "South Carolina": ["south carolina", "south carolina gamecocks", "scar", "sc"],
    "Rapid City": ["rapid city"],
    "Panama City": ["panama city"],
    "Hammond": ["hammond"],
    "Alabaster": ["alabaster"],
    "Death Valley": ["death valley"],
    "Gate City": ["gate city"],
    "Oklahoma State": ["oklahoma state", "oklahoma state cowboys", "oklahoma st"],
    "South Carolina": ["south carolina", "south carolina gamecocks", "scar", "sc"],
}

def normalize_key(value):
    return re.sub(r'[^a-z0-9]+', '', str(value).strip().lower())

def get_team_slug(team):
    team = str(team).strip()
    if not team or team.lower() == 'nan':
        return ""
    slug = TEAM_VISUALS.get(team, {}).get("slug")
    if not slug:
        slug = team.lower().replace("&", "and").replace(".", "").replace("'", "").replace(" ", "-")
    return slug

def get_team_aliases(team):
    team = str(team).strip()
    aliases = TEAM_ALIASES.get(team, [team])
    aliases = [a for a in aliases if a]
    slug = get_team_slug(team)
    if slug:
        aliases.append(slug.replace("-", " "))
        aliases.append(slug)
    aliases.append(team)
    normalized = []
    seen = set()
    for alias in aliases:
        n = normalize_key(alias)
        if n and n not in seen:
            normalized.append(alias)
            seen.add(n)
    return normalized

def build_logo_file_index():
    candidate_dirs = [
        Path('logos'),
        Path('/mnt/data/logos'),
        Path('/mount/src/cfb_dynasty_app/logos'),
        Path('/mount/src/cfb_dynasty_app/assets/logos'),
        Path('/mount/src/cfb_dynasty_app'),
    ]
    found = {}
    for d in candidate_dirs:
        if d.exists():
            for fp in d.rglob('*'):
                if fp.is_file() and fp.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}:
                    stem_key = normalize_key(fp.stem)
                    name_key = normalize_key(fp.name)
                    for k in {stem_key, name_key}:
                        if k and k not in found:
                            found[k] = fp
    return found

LOGO_FILE_INDEX = build_logo_file_index()

def get_team_slug(team):
    team = str(team).strip()
    if not team or team.lower() == 'nan':
        return ""
    slug = TEAM_VISUALS.get(team, {}).get("slug")
    if not slug:
        slug = team.lower().replace("&", "and").replace(".", "").replace("'", "").replace(" ", "-")
    return slug

def get_team_logo_url(team):
    slug = get_team_slug(team)
    return f"https://a.espncdn.com/i/teamlogos/ncaa/500/{slug}.png" if slug else ""

def get_local_logo_path(team):
    aliases = get_team_aliases(team)
    exact_keys = [normalize_key(a) for a in aliases]
    for key in exact_keys:
        if key in LOGO_FILE_INDEX:
            return str(LOGO_FILE_INDEX[key])

    # fuzzy match: look for alias inside filename or filename inside alias
    for key, fp in LOGO_FILE_INDEX.items():
        for alias in exact_keys:
            if alias and (alias in key or key in alias):
                return str(fp)
    return ""

def get_logo_source(team):
    local = get_local_logo_path(team)
    if local:
        return local
    return ""

def get_team_primary_color(team):
    team = str(team).strip()
    if team in TEAM_VISUALS:
        return TEAM_VISUALS[team].get("primary", "#1f77b4")
    # fallback: try normalized alias match
    nteam = normalize_key(team)
    for name, meta in TEAM_VISUALS.items():
        if normalize_key(name) == nteam:
            return meta.get("primary", "#1f77b4")
    return "#1f77b4"

def get_team_secondary_color(team):
    team = str(team).strip()
    if team in TEAM_VISUALS:
        return TEAM_VISUALS[team].get("secondary", "#ffffff")
    return "#ffffff"


def hex_to_rgba(hex_color, alpha=0.25):
    """Convert any hex color (#RGB or #RRGGBB) to an rgba() string safe for Plotly."""
    try:
        h = str(hex_color).strip().lstrip("#")
        if len(h) == 3:
            h = h[0]*2 + h[1]*2 + h[2]*2
        if len(h) != 6:
            return f"rgba(100,100,100,{alpha})"
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"
    except Exception:
        return f"rgba(100,100,100,{alpha})"

def build_user_color_map(model_df):
    if model_df is None or model_df.empty:
        return {}
    return {str(r["USER"]).strip().title(): get_team_primary_color(r["TEAM"]) for _, r in model_df[["USER", "TEAM"]].drop_duplicates().iterrows()}

def build_team_color_map(model_df):
    if model_df is None or model_df.empty:
        return {}
    return {str(r["TEAM"]).strip(): get_team_primary_color(r["TEAM"]) for _, r in model_df[["TEAM"]].drop_duplicates().iterrows()}

def image_file_to_data_uri(path_str):
    try:
        if path_str and os.path.exists(path_str):
            ext = Path(path_str).suffix.lower().replace('.', '') or 'png'
            with open(path_str, 'rb') as f:
                encoded = base64.b64encode(f.read()).decode('ascii')
            return f"data:image/{ext};base64,{encoded}"
    except Exception:
        return ""
    return ""

def render_logo(src, width=56):
    try:
        if isinstance(src, str) and src.strip() and os.path.exists(src):
            st.image(src, width=width)
        else:
            st.markdown("<div style='font-size:2rem;line-height:1;'>🏈</div>", unsafe_allow_html=True)
    except Exception:
        st.markdown("<div style='font-size:2rem;line-height:1;'>🏈</div>", unsafe_allow_html=True)

def render_war_room_table(board_df):
    rows_html = []
    for _, row in board_df.iterrows():
        team = str(row.get('TEAM', ''))
        user = str(row.get('USER', ''))
        primary = get_team_primary_color(team)
        secondary = get_team_secondary_color(team)
        logo_path = get_logo_source(team)
        logo_uri = image_file_to_data_uri(logo_path)
        logo_html = f"<img src='{logo_uri}' style='width:40px;height:40px;object-fit:contain;'/>" if logo_uri else "<div style='font-size:24px;'>🏈</div>"
        cells = []
        team_cell = f"""
        <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;white-space:nowrap;">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:44px;text-align:center;">{logo_html}</div>
            <div>
              <div style="font-weight:800;color:{primary};">{html.escape(team)}</div>
              <div style="font-size:12px;color:#cbd5e1;">{html.escape(user)}</div>
            </div>
          </div>
        </td>
        """
        cells.append(team_cell)
        for col in ['CFP Rank','SOS','QB Tier','Power Index','Natty Odds','CFP Odds',
                    'Natty if Lose to Unranked','Natty if Lose to Ranked',
                    'CFP if Lose to Unranked','CFP if Lose to Ranked',
                    'Collapse Risk','Program Stock']:
            val = row.get(col, '')
            if col in {'Natty Odds','CFP Odds','Natty if Lose to Unranked','Natty if Lose to Ranked','CFP if Lose to Unranked','CFP if Lose to Ranked','Collapse Risk'}:
                disp = format_pct(val, digits=1)
            elif col in {'SOS','Power Index'}:
                try:
                    disp = f"{float(val):.1f}"
                except Exception:
                    disp = str(val)
            elif col == 'CFP Rank':
                disp = '—' if pd.isna(val) or str(val).strip() in {'nan',''} else str(int(float(val)))
            else:
                disp = str(val)
            if col == 'Program Stock':
                disp = html.escape(disp)
            cells.append(f"<td style='padding:10px 12px;border-bottom:1px solid #e5e7eb;text-align:center;white-space:nowrap;'>{html.escape(disp)}</td>")
        row_html = f"<tr style='border-left:6px solid {primary};background:linear-gradient(90deg,{primary}12,transparent 14%);'>{''.join(cells)}</tr>"
        rows_html.append(row_html)

    table_html = f"""
    <div style="overflow-x:auto;border:1px solid #e5e7eb;border-radius:14px;">
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead>
          <tr style="background:#f8fafc;color:#111827;">
            <th style="text-align:left;padding:10px 12px;color:#111827;font-weight:800;">Team</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">CFP Rank</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">SOS</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">QB Tier</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">Power Index</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">Natty Odds</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">CFP Odds</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">Natty if Lose to Unranked</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">Natty if Lose to Ranked</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">CFP if Lose to Unranked</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">CFP if Lose to Ranked</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">Collapse Risk</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">Program Stock</th>
          </tr>
        </thead>
        <tbody>{''.join(rows_html)}</tbody>
      </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)

def ensure_columns(df, defaults):
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default
    return df



def format_pct(val, digits=1):
    try:
        if pd.isna(val):
            return "—"
        num = float(val)
        if digits == 0:
            return f"{int(round(num))}%"
        return f"{round(num, digits):.{digits}f}%"
    except Exception:
        return "—"


def mobile_metrics(metrics, cols_desktop=4):
    """
    Render a row of metric cards as a responsive CSS grid.
    Uses auto-fit so it naturally reflows to 2-per-row on small screens.
    """
    cards_html = ""
    for m in metrics:
        label = html.escape(str(m.get("label", "")))
        value = html.escape(str(m.get("value", "")))
        delta = m.get("delta", None)
        delta_html = ""
        if delta is not None:
            delta_str = str(delta)
            delta_color_mode = m.get("delta_color", "normal")
            is_positive = delta_str.startswith("+") or (not delta_str.startswith("-") and delta_str not in ["0", "0.0", "0%"])
            if delta_color_mode == "off":
                dc = "#9ca3af"
            elif delta_color_mode == "inverse":
                dc = "#f87171" if is_positive else "#4ade80"
            else:
                dc = "#4ade80" if is_positive else "#f87171"
            arrow = "&#9650;" if is_positive else "&#9660;"
            delta_html = f"<div style='font-size:0.72rem;color:{dc};font-weight:600;margin-top:2px;'>{arrow} {html.escape(delta_str)}</div>"
        cards_html += (
            "<div style='background:#1f2937;border:1px solid #374151;border-radius:10px;"
            "padding:10px 12px;min-width:0;'>"
            f"<div style='font-size:0.72rem;color:#9ca3af;font-weight:600;text-transform:uppercase;"
            f"letter-spacing:.04em;margin-bottom:4px;white-space:nowrap;overflow:hidden;"
            f"text-overflow:ellipsis;'>{label}</div>"
            f"<div style='font-size:1.15rem;font-weight:800;color:#f3f4f6;line-height:1.2;'>{value}</div>"
            f"{delta_html}"
            "</div>"
        )
    # auto-fit with minmax: naturally goes 2-per-row on mobile, cols_desktop-per-row on wide screens
    min_card = "140px"
    grid_html = (
        f"<div style='display:grid;"
        f"grid-template-columns:repeat(auto-fit,minmax({min_card},1fr));"
        f"gap:8px;margin-bottom:1rem;'>"
        f"{cards_html}"
        f"</div>"
    )
    st.markdown(grid_html, unsafe_allow_html=True)

def normalize_history_team_name(team):
    t = str(team).strip()
    lower = t.lower()
    aliases = {
        'south florida': 'USF',
        'usf': 'USF',
        'texas a&m': 'Texas A&M',
        'san jose st': 'San Jose State',
        'bowling green state': 'Bowling Green',
    }
    return aliases.get(lower, t)


def recruiting_value_means_coached(val):
    if pd.isna(val):
        return False
    s = str(val).strip()
    if s == '' or s.lower() in {'nan', 'none', 'na', 'n/a', '-', '--', '-*'}:
        return False
    return not pd.isna(clean_rank_value(val))


def get_program_history_cards(user, ratings_df, champs_df, rec_df):
    user_clean = str(user).strip().title()
    team_years = {}

    # Recruiting is the source of truth for coaching stops and year spans.
    if rec_df is not None and not rec_df.empty and 'USER' in rec_df.columns and 'Teams' in rec_df.columns:
        rec_user = rec_df[rec_df['USER'].astype(str).str.strip().str.title() == user_clean].copy()
        year_cols = [c for c in rec_user.columns if str(c).isdigit()]
        for _, r in rec_user.iterrows():
            team = normalize_history_team_name(r.get('Teams', ''))
            if not team or str(team).lower() == 'nan':
                continue
            active_years = [int(col) for col in year_cols if recruiting_value_means_coached(r.get(col))]
            if active_years:
                team_years.setdefault(team, set()).update(active_years)

    # Fallback to ratings only if recruiting has nothing for this user.
    if not team_years and ratings_df is not None and not ratings_df.empty and 'USER' in ratings_df.columns and 'TEAM' in ratings_df.columns and 'YEAR' in ratings_df.columns:
        history = ratings_df[ratings_df['USER'].astype(str).str.strip().str.title() == user_clean].copy()
        history['YEAR'] = pd.to_numeric(history['YEAR'], errors='coerce')
        for _, r in history.dropna(subset=['YEAR']).iterrows():
            team = normalize_history_team_name(r.get('TEAM', ''))
            if team and str(team).lower() != 'nan':
                team_years.setdefault(team, set()).add(int(r['YEAR']))

    if not team_years:
        return []

    champs_local = champs_df.copy()
    champs_local['user'] = champs_local['user'].astype(str).str.strip().str.title()
    champs_local['Team'] = champs_local['Team'].astype(str).str.strip().map(normalize_history_team_name)
    champs_local['YEAR'] = pd.to_numeric(champs_local['YEAR'], errors='coerce')

    cards = []
    for team, years_set in sorted(team_years.items(), key=lambda kv: min(kv[1]) if kv[1] else 9999):
        years = sorted(int(y) for y in years_set if pd.notna(y))
        title_count = int(champs_local[
            (champs_local['user'] == user_clean) &
            (champs_local['Team'] == team) &
            (champs_local['YEAR'].isin(years))
        ].shape[0])

        if years:
            ranges = []
            start = prev = years[0]
            for y in years[1:]:
                if y == prev + 1:
                    prev = y
                else:
                    ranges.append(f"{start}-{prev}" if start != prev else str(start))
                    start = prev = y
            ranges.append(f"{start}-{prev}" if start != prev else str(start))
            years_display = ', '.join(ranges)
        else:
            years_display = '—'

        cards.append({
            'team': team,
            'logo': get_logo_source(team),
            'years': years_display,
            'titles': title_count,
            'first_year': years[0] if years else 9999,
        })

    cards = sorted(cards, key=lambda x: (x.get('first_year', 9999), x['team']))
    for c in cards:
        c.pop('first_year', None)
    return cards


def render_history_cards(cards):
    if not cards:
        st.caption("No prior school history found.")
        return
    cols = st.columns(min(4, len(cards)))
    for i, card in enumerate(cards):
        with cols[i % len(cols)]:
            render_logo(card['logo'], width=44)
            st.caption(card['team'])
            st.caption(card['years'])
            trophies = "🏆" * max(1, int(card['titles'])) if int(card['titles']) > 0 else "—"
            st.caption(f"Titles: {trophies}")

def _mini_stat_chip(label, value, color='#94a3b8'):
    """Compact stat chip for season-in-numbers bars."""
    return (f"<div style='background:#0a1628;border:1px solid #1e293b;border-radius:8px;"
            f"padding:8px 10px;text-align:center;'>"
            f"<div style='font-weight:900;font-size:1.0rem;color:{color};'>{html.escape(str(value))}</div>"
            f"<div style='font-size:0.6rem;color:#475569;letter-spacing:.05em;margin-top:2px;'>{html.escape(label)}</div>"
            f"</div>")


def render_speed_freaks_table(df):
    """Mobile-first ranked speed cards — one card per team, stacks cleanly on phone."""
    RANK_MEDALS = {1: '🥇', 2: '🥈', 3: '🥉'}
    TIER_COLORS = {
        'Non-Existent': '#374151',
        'Balanced':     '#0369a1',
        'Offense':      '#b45309',
        'Defense':      '#065f46',
        'Off & Def':    '#7c3aed',
    }

    cards_html = "<div style='display:flex;flex-direction:column;gap:10px;'>"
    for _, row in df.iterrows():
        team     = str(row.get('TEAM', ''))
        user     = str(row.get('USER', ''))
        rank     = int(row.get('TEAM SPEED Rank', 0))
        primary  = get_team_primary_color(team)
        logo_uri = image_file_to_data_uri(get_logo_source(team))
        logo_tag = (f"<img src='{logo_uri}' style='width:52px;height:52px;object-fit:contain;flex-shrink:0;'/>"
                    if logo_uri else "<span style='font-size:32px;'>🏈</span>")

        mph        = float(row.get('Speedometer', 0))
        score      = float(row.get('Team Speed Score', 0))
        total_spd  = int(row.get('Team Speed (90+ Speed Guys)', 0))
        quad_90    = int(row.get('Quad 90 (90+ SPD, ACC, AGI & COD)', 0))
        gen        = int(row.get('Generational (96+ speed or 96+ Acceleration)', 0))
        off_spd    = int(row.get('Off Speed (90+ speed)', 0))
        def_spd    = int(row.get('Def Speed (90+ speed)', 0))
        where      = str(row.get('Where is the Speed?', '—'))
        where_col  = TIER_COLORS.get(where, '#64748b')
        medal      = RANK_MEDALS.get(rank, f'#{rank}')

        # speed bar: fill proportional to top score in table (index 0)
        max_score  = float(df.iloc[0].get('Team Speed Score', 100)) or 100
        bar_pct    = min(100, round(score / max_score * 100))
        bar_fill   = f"linear-gradient(90deg,{primary}cc,{primary}55)"

        # stat chips
        def chip(label, val, accent='#94a3b8'):
            return (f"<div style='display:flex;flex-direction:column;align-items:center;"
                    f"background:#0a1628;border:1px solid #1e293b;border-radius:7px;"
                    f"padding:5px 10px;min-width:52px;'>"
                    f"<span style='color:{accent};font-weight:900;font-size:0.95rem;'>{val}</span>"
                    f"<span style='color:#475569;font-size:0.6rem;letter-spacing:.05em;margin-top:1px;'>{label}</span>"
                    f"</div>")

        chips = (
            chip('90+ SPD', str(total_spd), primary)
            + chip('QUAD 90', str(quad_90), '#60a5fa')
            + chip('GEN', str(gen), '#fbbf24')
            + chip('OFF', str(off_spd), '#34d399')
            + chip('DEF', str(def_spd), '#f87171')
        )

        cards_html += f"""
        <div style="background:linear-gradient(135deg,{primary}18 0%,#0f172a 40%);
                    border:1px solid {primary}55;border-radius:14px;padding:14px 16px;
                    border-left:5px solid {primary};">
          <!-- header row: medal + logo + name + mph -->
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
            <span style="font-size:1.5rem;min-width:32px;">{medal}</span>
            {logo_tag}
            <div style="flex:1;min-width:0;">
              <div style="font-weight:900;font-size:1rem;color:{primary};
                          white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                {html.escape(team)}
              </div>
              <div style="font-size:0.72rem;color:#64748b;">{html.escape(user)}</div>
            </div>
            <div style="text-align:right;flex-shrink:0;">
              <div style="font-weight:900;font-size:1.15rem;color:#f1f5f9;">{mph:.0f}<span style="font-size:0.7rem;color:#64748b;"> MPH</span></div>
              <div style="font-size:0.65rem;color:#475569;">score {score:.1f}</div>
            </div>
          </div>
          <!-- speed bar -->
          <div style="background:#1e293b;border-radius:4px;height:6px;margin-bottom:10px;overflow:hidden;">
            <div style="width:{bar_pct}%;height:100%;background:{bar_fill};border-radius:4px;"></div>
          </div>
          <!-- stat chips -->
          <div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;">
            {chips}
            <div style="margin-left:auto;background:{where_col}22;border:1px solid {where_col}55;
                        border-radius:20px;padding:3px 10px;font-size:0.68rem;color:{where_col};
                        font-weight:700;white-space:nowrap;">
              {html.escape(where)}
            </div>
          </div>
        </div>"""

    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)


def smart_col(df, target_names):
    for target in target_names:
        for col in df.columns:
            if col.strip().lower() == target.lower():
                return col
    return None


def get_pop_culture_speed_comp(gens):
    gens = int(max(0, gens))
    one_refs = [
        "Neo bending the code of the Matrix",
        "Sonic hitting turbo with zero respect for physics",
        "The Flash turning the corner before the defense blinks",
        "Mario grabbing a Starman and refusing to be tackled",
        "John Wick with a clean lane and a personal grudge"
    ]
    multi_refs = {
        2: [
            "Batman and Robin",
            "Mario and Luigi",
            "Han Solo and Chewbacca",
            "Abbott and Costello in shoulder pads",
            "Shawn Michaels and Triple H, a.k.a. D-Generation X"
        ],
        3: [
            "the Three Hunters from Halo 3 co-op",
            "the Powerpuff Girls on a sugar rush",
            "Destiny's Child harmonizing in open space",
            "the Three Amigos riding into your secondary"
        ],
        4: [
            "the Teenage Mutant Ninja Turtles",
            "the Ghostbusters pulling up with proton packs",
            "the A-Team if every member ran a 4.2",
            "the Fantastic Four with track spikes"
        ],
        5: [
            "the Avengers core lineup assembling in the slot",
            "the Fellowship's fastest five skipping the walking montage",
            "the Jackson 5 but all of them are vertical threats"
        ],
        6: [
            "the Sinister Six if they majored in yards after catch",
            "the original Mighty Morphin Power Rangers plus the Green Ranger",
            "a six-man ladder match where everyone somehow runs sub-4.4"
        ],
        7: [
            "the Seven from The Boys if every one of them played skill positions",
            "the Seven Dwarfs after a suspicious offseason speed program",
            "Seven Samurai in spread formation"
        ],
        8: [
            "the Ocean's Eleven scouting department trimmed down to its fastest eight",
            "the eight gym leaders before your badge case is full",
            "a Mario Kart lobby where nobody lifts off the gas"
        ]
    }
    if gens == 0:
        return "No crossover event here. This roster is light on comic-book speed and has to win the old-fashioned way."
    if gens == 1:
        return f"This team has one true superweapon: think {one_refs[gens % len(one_refs)]}. Everything dangerous starts with that one mutant."
    if gens in multi_refs:
        ref = multi_refs[gens][gens % len(multi_refs[gens])]
        return f"This is no longer one problem. It's {ref} showing up on the same depth chart."
    return f"{gens} generational freaks is basically an Avengers-level crossover event. The scouting report just says 'good luck.'"





def generate_mvp_backstory(row):
    player = str(row.get('⭐ STAR SKILL GUY (Top OVR)', 'Unknown Weapon')).strip()
    team = str(row.get('TEAM', 'Unknown Team')).strip()
    user = str(row.get('USER', 'Unknown User')).strip()
    generational_flag = str(row.get('Star Skill Guy is Generational Speed?', 'No')).strip().lower()
    qb_tier = str(row.get('QB Tier', 'Unknown')).strip()
    off = int(pd.to_numeric(row.get('OFFENSE', 0), errors='coerce') or 0)
    deff = int(pd.to_numeric(row.get('DEFENSE', 0), errors='coerce') or 0)
    freaks = int(pd.to_numeric(row.get('Generational (96+ speed or 96+ Acceleration)', 0), errors='coerce') or 0)
    speed_side = str(row.get('Where is the Speed?', 'Balanced')).strip()

    origin_pool = [
        "grew up torching grown men in dusty seven-on-seven tournaments and talking shit the whole time",
        "was a zero-star rumor until one camp clocked him moving like the simulation bugged out",
        "came from a tiny town where the only two landmarks were a water tower and a scoreboard he kept breaking",
        "used to return kicks in high school because the coaches were too scared to leave the ball in anyone else's hands",
        "started as a track kid, then realized defenders hate being embarrassed on national television",
        "spent an offseason catching tennis balls off a jugs machine because normal drills were too boring",
        "was the kind of recruit old coaches called 'too flashy' right before he cooked their corners anyway",
        "got his first nickname because nobody on the scout team could get a clean angle on him",
        "was allegedly late to practice once and still got there before everybody else",
        "made his name in backyard games where the only rule was don't let him touch the damn ball",
        "turned a state title game into a personal mixtape and never looked back",
        "showed up to camp looking ordinary until the first rep, then all hell broke loose",
        "learned route running from YouTube, street football, and pure disrespect",
        "built his confidence by humiliating older cousins who swore they knew how to tackle",
        "made one recruiting coordinator say, on record, 'that kid moves like a tax write-off waiting to happen'",
        "got labeled high-maintenance because he expected defensive backs to keep up, which was unrealistic as hell",
        "came into the program with a chip on his shoulder and enough juice to power the whole damn offense",
        "used to race the school bus home and, according to local legend, won twice",
        "was the scouting report that kept assistants awake at 2 a.m. muttering about leverage and pursuit angles",
        "entered college as a curiosity and became a full-blown problem by the second scrimmage",
        "was the one prospect every rival board pretended was overrated right up until film day",
        "grew up in a football family that treated every backyard rep like a televised grudge match",
        "didn't start talking until game week, then usually backed it up in the first quarter",
        "made special teams coaches weep happy tears because the first cut looked unfair in real time",
        "got recruited off a grainy highlight tape that somehow still looked faster than everybody else",
        "was called raw as hell by scouts, which usually means they had no idea how to guard him"
    ]

    style_pool = [
        "Now he plays like a man trying to settle old debts in one cut.",
        "Now the whole offense tilts toward him because pretending he isn't the main character would be stupid.",
        "Every touch feels like it could turn into a funeral for pursuit angles.",
        "He doesn't just stress defenses — he makes them start bullshitting themselves.",
        "When the ball finds him, the geometry of the field gets real weird real fast.",
        "The film says explosive. The box score usually says holy shit.",
        "He plays with the swagger of somebody who has never once doubted the ending.",
        "The scary part is how casual it looks when he's ruining a game plan.",
        "He has the body language of a guy who already knows who missed the tackle.",
        "Even his decoys feel disrespectful.",
        "You can tell when the stadium notices him, because the defense suddenly starts making business decisions.",
        "His best trait might be that he turns safe calls into deeply unsafe situations for everybody else.",
        "The dude has that nasty habit of making good defenders look like unpaid interns.",
        "He's built for the exact moment a defense starts thinking it finally has the game under control.",
        "He turns one crease into a police report."
    ]

    role_pool = {
        'Offense': [
            "He's the offensive fuse. Give him daylight and somebody's safeties are getting cussed out on the sideline.",
            "All that speed lives on offense, so this dude is basically the panic button with shoulder pads.",
            "This roster's juice is front-loaded on offense, and he's the bastard most likely to cash it in."
        ],
        'Defense': [
            "The defense carries the speed here, so his vibe is less highlight tape and more crime scene investigator.",
            "On a defense-loaded speed roster, he feels like the enforcer the offense keeps trying to avoid.",
            "This team's juice lives on defense, and he's usually at the center of the chaos."
        ],
        'Off & Def': [
            "This team has speed everywhere, so he's not carrying the whole circus — he's just the ringmaster.",
            "Because the roster is juiced on both sides, he gets to play free and mean.",
            "The speed is everywhere, which somehow makes his role even nastier."
        ],
        'Balanced': [
            "The roster isn't lopsided, which lets him pick his spots and still wreck afternoons.",
            "This is a balanced build, so he doesn't have to force hero ball to be the scariest guy on the field."
        ],
        'Non-Existent': [
            "The speed around him isn't exactly overflowing, so his job is to manufacture panic the hard way.",
            "On a roster without much pure track speed, he has to create the fireworks himself."
        ]
    }

    gen_pool = [
        "The generational speed tag means once he hits the second level, the rest is mostly paperwork.",
        "And yes, the generational speed marker means the pursuit chart is basically decorative.",
        "If the generational tag is real, then one bad angle turns into six points and some screaming.",
        "That generational burst means defenders don't really lose — they just run out of road.",
        "When a guy this good also has generational wheels, you're basically praying for drops and penalties."
    ]

    non_gen_pool = [
        "He isn't flagged as generational speed, but that doesn't stop him from playing like a recurring problem.",
        "No generational speed tag, but he's still a pain in the ass because instincts and timing count too.",
        "He may not have comic-book wheels, but he clearly knows how to make enough space to be dangerous.",
        "He's not tagged generational, which just means the damage comes from polish instead of pure lightning."
    ]

    qb_spice = {
        'Elite': "With an elite QB in the building, the whole ecosystem around him gets even nastier.",
        'Leader': "A leader-level QB means the touches are usually on time and the bullshit stays minimal.",
        'Average Joe': "An Average Joe QB puts a cap on the glamour, so the star often has to do extra dirty work.",
        'Ass': "Unfortunately, the quarterback situation can still drag this whole opera into the mud if it gets stupid.",
        'Unknown': "The quarterback picture is murky, so this poor bastard may have to improvise greatness."
    }

    seed = int(hashlib.md5(f"{user}|{team}|{player}".encode()).hexdigest(), 16)
    origin = origin_pool[seed % len(origin_pool)]
    style = style_pool[(seed // 3) % len(style_pool)]
    role_lines = role_pool.get(speed_side, role_pool['Balanced'])
    role_line = role_lines[(seed // 5) % len(role_lines)]
    gen_line = gen_pool[(seed // 7) % len(gen_pool)] if generational_flag == 'yes' else non_gen_pool[(seed // 7) % len(non_gen_pool)]
    qb_line = qb_spice.get(qb_tier, qb_spice['Unknown'])

    intensity = "He's the kind of player who makes a coordinator look smart and a defender look unemployed."
    if off >= 88 and generational_flag == 'yes':
        intensity = "This is the kind of asshole who turns a normal Saturday into a season-defining headache."
    elif deff >= 88 and speed_side == 'Defense':
        intensity = "He plays with the energy of somebody who thinks every snap is a personal insult."
    elif freaks >= 3:
        intensity = "On a roster already packed with freaks, he still finds a way to feel like the center of the damn storm."

    return (
        f"{player} at {team} {origin}. {style} {role_line} "
        f"{gen_line} {qb_line} {intensity}"
    )



def generate_coach_profile(row, stats_row):
    user = str(row.get('USER', 'Unknown Coach')).strip()
    team = str(row.get('TEAM', 'Unknown Team')).strip()
    natties = int(pd.to_numeric(stats_row.get('Natties', 0), errors='coerce') or 0)
    natty_apps = int(pd.to_numeric(stats_row.get('Natty Apps', 0), errors='coerce') or 0)
    cfp_wins = int(pd.to_numeric(stats_row.get('CFP Wins', 0), errors='coerce') or 0)
    conf_titles = int(pd.to_numeric(stats_row.get('Conf Titles', 0), errors='coerce') or 0)
    drafted = int(pd.to_numeric(stats_row.get('Drafted', 0), errors='coerce') or 0)
    win_pct = float(pd.to_numeric(stats_row.get('Career Win %', 50.0), errors='coerce') or 50.0)
    recruit_score = float(pd.to_numeric(row.get('Recruit Score', 50.0), errors='coerce') or 50.0)
    bcr = float(pd.to_numeric(row.get('BCR_Val', 0), errors='coerce') or 0.0)
    speed = float(pd.to_numeric(row.get('Team Speed Score', 0), errors='coerce') or 0.0)
    qbt = str(row.get('QB Tier', 'Unknown')).strip()

    if natties >= 3:
        archetype = 'Empire builder'
    elif natties >= 1 or natty_apps >= 2:
        archetype = 'Big-game shark'
    elif win_pct >= 70:
        archetype = 'Program surgeon'
    elif recruit_score >= 78 and bcr >= 45:
        archetype = 'Roster architect'
    elif speed >= 65:
        archetype = 'Chaos mechanic'
    else:
        archetype = 'Grinder with a whistle'

    tone_lines = [
        f"{user} runs {team} like every Saturday is a boardroom coup. The vibe is {archetype.lower()}, and the résumé already has {natties} natties, {natty_apps} title appearances, and {cfp_wins} CFP wins hanging off it.",
        f"{user}'s coaching profile screams {archetype.lower()}. The man has stacked {conf_titles} conference titles, pushed {drafted} players into the league, and built a roster with a {bcr:.1f}% blue-chip ratio.",
        f"This is {user} in full character: {archetype.lower()}, a {win_pct:.1f}% career winner, and absolutely willing to win ugly if that's what the room calls for."
    ]

    if qbt == 'Elite':
        qb_line = 'The elite QB gives him the luxury of calling games like a rich asshole with options.'
    elif qbt == 'Leader':
        qb_line = 'The leader-level QB keeps the operation on schedule and cuts down the dumb shit.'
    elif qbt == 'Average Joe':
        qb_line = 'The quarterback room is usable, but some Saturdays still feel like the coach is doing extra labor.'
    elif qbt == 'Ass':
        qb_line = 'The quarterback situation is ass, which means some of this profile is being held together with spit, rage, and halftime adjustments.'
    else:
        qb_line = 'Quarterback uncertainty means the coach still has to keep one hand on the fire extinguisher.'

    build_line = 'The recruiting profile says this program is loading talent the right way.' if recruit_score >= 78 and bcr >= 45 else 'The recruiting pipeline is still uneven, so the coach has to manufacture edges instead of just buying them with talent.'
    speed_line = 'And the speed profile is nasty enough to let his mistakes survive contact.' if speed >= 65 else 'The speed profile is decent, but not enough to bail out every bad Saturday.'

    idx = int(hashlib.md5(f"coach|{user}|{team}".encode()).hexdigest(), 16) % len(tone_lines)
    return f"{tone_lines[idx]} {qb_line} {build_line} {speed_line}"


def team_speed_to_mph(team_speed_score):
    team_speed_score = float(max(0, team_speed_score))
    # 40 points is the posted 65 MPH speed limit. Above that, the program is officially speeding.
    return round((team_speed_score / 40.0) * 65.0, 1)


def get_speeding_label(team_speed_score, gens=0):
    mph = team_speed_to_mph(team_speed_score)
    over = round(mph - 65.0, 1)
    gens = int(max(0, gens))

    freak_flair = {
        0: "No generational freaks under the hood, so this is more tuned machine than nitrous dragster.",
        1: "One generational freak is riding shotgun like the hero in the third act.",
        2: "Two freaks means this is a buddy-cop chase scene with both leads outrunning helicopters.",
        3: "Three freaks turns this into a full-on superteam convoy.",
        4: "Four freaks means the whole crew just jumped into the van together.",
        5: "Five freaks means the road is basically full of boss-fight energy.",
        6: "Six freaks means this roster is running a Fast & Furious crossover under the hood.",
    }
    freak_note = freak_flair.get(gens, f"{gens} freaks means this is less a car and more a comic-book pursuit sequence.")

    if over <= 0:
        base = f"{mph} MPH in a 65 — technically legal, but the engine is humming."
    elif over <= 10:
        base = f"{mph} MPH in a 65 — light speeding, officer is taking a second look."
    elif over <= 20:
        base = f"{mph} MPH in a 65 — this team is getting pulled over on sight."
    elif over <= 35:
        base = f"{mph} MPH in a 65 — reckless acceleration with no regard for public safety."
    else:
        base = f"{mph} MPH in a 65 — felony-level speed. Defensive coordinators should call a lawyer."
    return f"{base} {freak_note}"

def get_speed_tier(team_speed_score):
    if team_speed_score >= 92:
        return "🛸 WARP-DRIVE CHAOS"
    if team_speed_score >= 82:
        return "⚡ BLACKTOP BURNERS"
    if team_speed_score >= 72:
        return "🔥 AFTERBURNER DEPTH"
    if team_speed_score >= 62:
        return "💨 NITRO NIGHTMARE"
    if team_speed_score >= 52:
        return "🏁 OPEN-FIELD OUTLAWS"
    if team_speed_score >= 42:
        return "🎯 STRIKE-FIRST SPEED"
    return "🧱 MUD-TIRE FOOTBALL"


def clean_rank_value(val):
    if pd.isna(val):
        return np.nan
    s = str(val).strip().replace('*', '')
    try:
        return float(s)
    except Exception:
        return np.nan


def safe_title_series(series):
    return series.astype(str).str.strip().str.title()


def yes_no_flag(val):
    return str(val).strip().lower() == 'yes'

def normalize_yes_no_columns(df, cols):
    for col in cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()
    return df

def qb_label(row):
    # Bad QB should win ties. If the source sheet says 'ass', we trust it.
    if yes_no_flag(row.get('Qb is Ass (under 80)', 'No')):
        return 'Ass'
    if yes_no_flag(row.get('QB is Elite (90+)', 'No')):
        return 'Elite'
    if yes_no_flag(row.get('QB is Leader (85+)', 'No')):
        return 'Leader'
    if yes_no_flag(row.get('QB is Average Joe (between 80 and 84)', 'No')):
        return 'Average Joe'
    qb_ovr = pd.to_numeric(row.get('QB OVR', np.nan), errors='coerce')
    if pd.isna(qb_ovr):
        return 'Unknown'
    if qb_ovr < 80:
        return 'Ass'
    if qb_ovr >= 90:
        return 'Elite'
    if qb_ovr >= 85:
        return 'Leader'
    if qb_ovr >= 80:
        return 'Average Joe'
    return 'Ass'

def cfp_rank_bonus(rank_value):
    rank = pd.to_numeric(rank_value, errors='coerce')
    if pd.isna(rank):
        return 0.0
    rank = max(1.0, float(rank))
    return max(0.0, 28.0 - rank) * 2.2


def get_record_parts(record_str):
    try:
        wins, losses = str(record_str).split('-')
        return int(wins), int(losses)
    except Exception:
        return 0, 0



def render_roster_matchup_tab():
    import plotly.graph_objects as go

    st.header("🎯 Roster Matchup Analyzer")
    st.caption("Full depth charts, positional battles, injury resilience, redshirt-aware eligibility, and future value pipeline analysis.")

    try:
        roster = pd.read_csv('cfb26_rosters_full.csv')
    except Exception:
        try:
            roster = pd.read_csv('cfb26_rosters_top30.csv')
            st.info("ℹ️ Using top-30 roster data. Upload cfb26_rosters_full.csv for full depth analysis.")
        except Exception as e2:
            st.error(f"Could not load roster data: {e2}")
            return

    teams = sorted(roster['Team'].unique().tolist())

    POS_GROUPS = {
        "QB":            ["QB"],
        "Backfield":     ["HB", "FB"],
        "Pass Catchers": ["WR", "TE"],
        "O-Line":        ["LT", "LG", "C", "RG", "RT"],
        "D-Line":        ["DT", "LEDG", "REDG"],
        "Linebackers":   ["MIKE", "WILL", "SAM"],
        "Secondary":     ["CB", "FS", "SS"],
    }
    ATTRS = ["OVR", "SPD", "ACC", "AGI", "COD", "STR", "AWR"]

    col1, col2 = st.columns(2)
    with col1:
        team_a = st.selectbox("🏈 Team A", teams, index=0, key="matchup_team_a")
    with col2:
        team_b = st.selectbox("🏈 Team B", teams, index=1, key="matchup_team_b")

    if team_a == team_b:
        st.warning("Select two different teams to see a comparison.")
        return

    roster_a = roster[roster['Team'] == team_a].copy()
    roster_b = roster[roster['Team'] == team_b].copy()
    color_a  = get_team_primary_color(team_a)
    color_b  = get_team_primary_color(team_b)

    logo_uri_a  = image_file_to_data_uri(get_logo_source(team_a))
    logo_uri_b  = image_file_to_data_uri(get_logo_source(team_b))
    logo_html_a = f"<img src='{logo_uri_a}' style='width:72px;height:72px;object-fit:contain;display:block;margin:0 auto 6px auto;'/>" if logo_uri_a else "<div style='font-size:48px;text-align:center;'>🏈</div>"
    logo_html_b = f"<img src='{logo_uri_b}' style='width:72px;height:72px;object-fit:contain;display:block;margin:0 auto 6px auto;'/>" if logo_uri_b else "<div style='font-size:48px;text-align:center;'>🏈</div>"

    # ── YEAR / REDSHIRT HELPERS ──────────────────────────────────────────────
    def parse_year_info(yr_str):
        """
        Returns (base_class, is_redshirt, yrs_in_program, eligibility_remaining)
        Eligibility: FR=4, SO=3, JR=2, SR=1  |  RS adds 1 yr in program, not eligibility
        FR(RS)  = in program 2 yrs, 4 eligibility yrs left (hasn't burned one yet)
        SO(RS)  = in program 3 yrs, 3 eligibility yrs left
        JR(RS)  = in program 4 yrs, 2 eligibility yrs left
        SR(RS)  = in program 5 yrs, 1 eligibility yr  left (grad year)
        """
        s = str(yr_str).upper().strip()
        is_rs = "(RS)" in s
        base = s.replace("(RS)", "").strip()
        elig_map = {"FR": 4, "SO": 3, "JR": 2, "SR": 1}
        prog_map  = {"FR": 1, "SO": 2, "JR": 3, "SR": 4}
        elig = elig_map.get(base, 2)
        prog = prog_map.get(base, 2) + (1 if is_rs else 0)
        label_map = {"FR": "Freshman", "SO": "Sophomore", "JR": "Junior", "SR": "Senior"}
        label = label_map.get(base, "Unknown")
        return label, is_rs, prog, elig

    def enrich_roster(df):
        df = df.copy()
        parsed = df['Year'].apply(parse_year_info)
        df['YrClass']   = parsed.apply(lambda x: x[0])
        df['IsRS']      = parsed.apply(lambda x: x[1])
        df['YrsInProg'] = parsed.apply(lambda x: x[2])
        df['EligLeft']  = parsed.apply(lambda x: x[3])

        # Future Value Score:
        # OVR at current age weighted by years remaining + athleticism upside
        # Athletes with high SPD/ACC/AGI but moderate OVR = high ceiling (they just need reps)
        # Formula: OVR * 0.55 + AthlScore * 0.25 + EligLeft * 3.0
        # AthlScore = avg of SPD, ACC, AGI, COD
        df['AthlScore'] = (df['SPD'] + df['ACC'] + df['AGI'] + df['COD']) / 4.0
        df['FV'] = (df['OVR'] * 0.55 + df['AthlScore'] * 0.25 + df['EligLeft'] * 3.0).round(1)

        # Ceiling flag: young + high athleticism but OVR not yet caught up
        df['HighCeiling'] = (df['EligLeft'] >= 3) & (df['AthlScore'] >= 82) & (df['OVR'] < 85)

        # Experience tag for display
        def exp_tag(row):
            rs_tag = " 🔄" if row['IsRS'] else ""
            return f"{row['YrClass']}{rs_tag} ({row['EligLeft']}yr left)"
        df['ExpTag'] = df.apply(exp_tag, axis=1)

        return df

    roster_a = enrich_roster(roster_a)
    roster_b = enrich_roster(roster_b)

    # ── TEAM HEADER ──────────────────────────────────────────────────────────
    h1, hm, h2 = st.columns([5, 1, 5])
    h1.markdown(f"<div style='text-align:center;padding:12px 0;'>{logo_html_a}<span style='color:{color_a};font-size:1.4rem;font-weight:900;'>{team_a}</span></div>", unsafe_allow_html=True)
    hm.markdown("<div style='text-align:center;padding-top:28px;color:#6b7280;font-size:1.5rem;font-weight:700;'>vs</div>", unsafe_allow_html=True)
    h2.markdown(f"<div style='text-align:center;padding:12px 0;'>{logo_html_b}<span style='color:{color_b};font-size:1.4rem;font-weight:900;'>{team_b}</span></div>", unsafe_allow_html=True)

    # ── MAIN TABS ────────────────────────────────────────────────────────────
    tab_overview, tab_depth, tab_resilience, tab_class, tab_pipeline = st.tabs([
        "📊 Athletic Profile",
        "📋 Depth Chart",
        "🩺 Injury Resilience",
        "🎓 Roster Composition",
        "🚀 Future Value",
    ])

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1 — ATHLETIC PROFILE
    # ════════════════════════════════════════════════════════════════════════
    with tab_overview:
        st.subheader("📊 Team Athletic Profile")

        def team_summary(df):
            return {
                "Avg OVR":       round(df["OVR"].mean(), 1),
                "Top OVR":       int(df["OVR"].max()),
                "90+ OVR Count": int((df["OVR"] >= 90).sum()),
                "Avg SPD":       round(df["SPD"].mean(), 1),
                "90+ SPD Count": int((df["SPD"] >= 90).sum()),
                "Avg AGI":       round(df["AGI"].mean(), 1),
                "Avg AWR":       round(df["AWR"].mean(), 1),
                "Roster Size":   len(df),
            }

        summ_a = team_summary(roster_a)
        summ_b = team_summary(roster_b)

        metric_rows = [
            ("Roster Size",    "👥 Total Roster Size"),
            ("Avg OVR",        "📈 Roster Avg Overall"),
            ("Top OVR",        "⭐ Best Player OVR"),
            ("90+ OVR Count",  "💎 Players 90+ OVR"),
            ("Avg SPD",        "💨 Roster Avg Speed"),
            ("90+ SPD Count",  "⚡ Players 90+ Speed"),
            ("Avg AGI",        "🐍 Roster Avg Agility"),
            ("Avg AWR",        "🧠 Roster Avg Awareness"),
        ]
        hdr_a, hdr_mid, hdr_b = st.columns([3, 3, 3])
        hdr_a.markdown(f"<div style='text-align:center;font-weight:800;color:{color_a};font-size:0.95rem;padding-bottom:4px;'>{team_a}</div>", unsafe_allow_html=True)
        hdr_mid.markdown("<div style='text-align:center;color:#9ca3af;font-size:0.75rem;padding-bottom:4px;'>METRIC</div>", unsafe_allow_html=True)
        hdr_b.markdown(f"<div style='text-align:center;font-weight:800;color:{color_b};font-size:0.95rem;padding-bottom:4px;'>{team_b}</div>", unsafe_allow_html=True)
        st.markdown("<hr style='margin:2px 0 8px 0;border-color:#e5e7eb;'>", unsafe_allow_html=True)
        for key, label in metric_rows:
            va, vb = summ_a[key], summ_b[key]
            col_a, col_mid, col_b = st.columns([3, 3, 3])
            col_a.markdown(f"<div style='text-align:center;font-size:1.05rem;color:{color_a};'>{'🏆 ' if va > vb else ''}<strong>{va}</strong></div>", unsafe_allow_html=True)
            col_mid.markdown(f"<div style='text-align:center;color:#6b7280;font-size:0.78rem;font-weight:600;'>{label}</div>", unsafe_allow_html=True)
            col_b.markdown(f"<div style='text-align:center;font-size:1.05rem;color:{color_b};'><strong>{vb}</strong>{' 🏆' if vb > va else ''}</div>", unsafe_allow_html=True)
        st.markdown("<hr style='margin:8px 0;border-color:#e5e7eb;'>", unsafe_allow_html=True)

        # Radar
        st.subheader("🕸️ Attribute Spider Chart")
        avg_a = [round(roster_a[a].mean(), 1) for a in ATTRS]
        avg_b = [round(roster_b[a].mean(), 1) for a in ATTRS]
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=avg_a+[avg_a[0]], theta=ATTRS+[ATTRS[0]], fill="toself", name=team_a, line=dict(color=color_a, width=2), fillcolor=hex_to_rgba(color_a, 0.27)))
        fig.add_trace(go.Scatterpolar(r=avg_b+[avg_b[0]], theta=ATTRS+[ATTRS[0]], fill="toself", name=team_b, line=dict(color=color_b, width=2), fillcolor=hex_to_rgba(color_b, 0.27)))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[60, 100], tickfont=dict(size=10))), showlegend=True, height=430, margin=dict(t=50, b=50, l=60, r=60), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5))
        st.plotly_chart(fig, use_container_width=True)

        # Positional battles
        st.markdown("---")
        st.subheader("⚔️ Positional Battle Breakdown")
        st.caption("Top 3 players per group. Composite score = 70% OVR + 30% Speed.")
        group_results = []
        for group_name, positions in POS_GROUPS.items():
            grp_a = roster_a[roster_a["Pos"].isin(positions)].nlargest(3, "OVR")
            grp_b = roster_b[roster_b["Pos"].isin(positions)].nlargest(3, "OVR")
            if grp_a.empty and grp_b.empty:
                continue
            score_a = round((grp_a["OVR"].mean() if not grp_a.empty else 0) * 0.70 + (grp_a["SPD"].mean() if not grp_a.empty else 0) * 0.30, 1)
            score_b = round((grp_b["OVR"].mean() if not grp_b.empty else 0) * 0.70 + (grp_b["SPD"].mean() if not grp_b.empty else 0) * 0.30, 1)
            margin = abs(score_a - score_b)
            winner_team  = team_a if score_a >= score_b else team_b
            winner_color = color_a if score_a >= score_b else color_b
            group_results.append({"group": group_name, "winner": winner_team if margin >= 0.5 else "EVEN", "margin": margin, "score_a": score_a, "score_b": score_b})
            if margin < 0.5:    plain_label = f"{group_name}  --  = EVEN"
            elif margin < 2.0:  plain_label = f"{group_name}  --  Slight Edge: {winner_team}"
            elif margin < 4.0:  plain_label = f"{group_name}  --  Edge: {winner_team} ✅"
            else:               plain_label = f"{group_name}  --  BIG ADVANTAGE: {winner_team} 🔥"
            with st.expander(plain_label, expanded=False):
                if margin < 0.5:
                    st.markdown("🟰 <span style='color:#9ca3af;'>EVEN</span>", unsafe_allow_html=True)
                else:
                    badge_weight = "900" if margin >= 4.0 else ("700" if margin >= 2.0 else "400")
                    st.markdown(f"<span style='color:{winner_color};font-weight:{badge_weight};'>{'BIG ADVANTAGE' if margin >= 4.0 else ('EDGE' if margin >= 2.0 else 'SLIGHT EDGE')}: {html.escape(winner_team)}{' 🔥' if margin >= 4.0 else ''}</span>", unsafe_allow_html=True)
                sc1, sc2, sc3 = st.columns([2, 3, 2])
                sc1.metric(f"{team_a} Score", score_a)
                sc3.metric(f"{team_b} Score", score_b)
                sc2.markdown("<div style='text-align:center;padding-top:0.6rem;color:#6b7280;font-size:0.8rem;'>composite score</div>", unsafe_allow_html=True)
                pa, pb = st.columns(2)
                disp_cols = ["Name", "Pos", "Year", "OVR", "SPD", "ACC", "AGI", "STR", "AWR"]
                sm_logo_a = f"<img src='{logo_uri_a}' style='width:28px;height:28px;object-fit:contain;vertical-align:middle;margin-right:6px;'/>" if logo_uri_a else "🏈 "
                sm_logo_b = f"<img src='{logo_uri_b}' style='width:28px;height:28px;object-fit:contain;vertical-align:middle;margin-right:6px;'/>" if logo_uri_b else "🏈 "
                with pa:
                    st.markdown(f"<div style='display:flex;align-items:center;gap:6px;margin-bottom:4px;'>{sm_logo_a}<span style='color:{color_a};font-weight:800;font-size:0.95rem;'>{team_a}</span></div>", unsafe_allow_html=True)
                    if not grp_a.empty:
                        st.dataframe(grp_a[disp_cols].reset_index(drop=True), hide_index=True, use_container_width=True)
                    else:
                        st.caption("No players.")
                with pb:
                    st.markdown(f"<div style='display:flex;align-items:center;gap:6px;margin-bottom:4px;'>{sm_logo_b}<span style='color:{color_b};font-weight:800;font-size:0.95rem;'>{team_b}</span></div>", unsafe_allow_html=True)
                    if not grp_b.empty:
                        st.dataframe(grp_b[disp_cols].reset_index(drop=True), hide_index=True, use_container_width=True)
                    else:
                        st.caption("No players.")

        # Scorecard
        st.markdown("---")
        st.subheader("🏟️ Battle Scorecard")
        wins_a = sum(1 for r in group_results if r["winner"] == team_a)
        wins_b = sum(1 for r in group_results if r["winner"] == team_b)
        ties   = sum(1 for r in group_results if r["winner"] == "EVEN")
        total  = len(group_results)
        sc1, sc2, sc3 = st.columns(3)
        sc1.markdown(f"<div style='text-align:center;'>{logo_html_a}<span style='font-size:0.8rem;color:{color_a};font-weight:700;'>{team_a}</span></div>", unsafe_allow_html=True)
        sc1.metric("Group Wins", wins_a)
        sc2.metric("Even Matchups", ties)
        sc3.markdown(f"<div style='text-align:center;'>{logo_html_b}<span style='font-size:0.8rem;color:{color_b};font-weight:700;'>{team_b}</span></div>", unsafe_allow_html=True)
        sc3.metric("Group Wins", wins_b)

        # Scouting report
        st.markdown("---")
        st.subheader("📋 Scouting Report")
        adv_a = sorted([r for r in group_results if r["winner"] == team_a], key=lambda x: x["margin"], reverse=True)
        adv_b = sorted([r for r in group_results if r["winner"] == team_b], key=lambda x: x["margin"], reverse=True)
        lines = []
        if adv_a:
            lines.append(f"**{team_a}** has the roster advantage at **{', '.join([r['group'] for r in adv_a[:2]])}**{' and ' + str(len(adv_a)-2) + ' more groups' if len(adv_a) > 2 else ''}.")
        if adv_b:
            lines.append(f"**{team_b}** counters with the edge at **{', '.join([r['group'] for r in adv_b[:2]])}**{' and ' + str(len(adv_b)-2) + ' more groups' if len(adv_b) > 2 else ''}.")
        spd_a, spd_b = summ_a["90+ SPD Count"], summ_b["90+ SPD Count"]
        if spd_a > spd_b + 1:
            lines.append(f"The speed gap is real -- **{team_a}** has **{spd_a}** players at 90+ SPD vs {team_b}'s **{spd_b}**.")
        elif spd_b > spd_a + 1:
            lines.append(f"**{team_b}** brings the burners -- **{spd_b}** players at 90+ SPD vs {team_a}'s **{spd_a}**.")
        else:
            lines.append(f"Speed depth is essentially equal -- **{spd_a}** vs **{spd_b}** players at 90+ SPD.")
        awr_a, awr_b = summ_a["Avg AWR"], summ_b["Avg AWR"]
        if abs(awr_a - awr_b) >= 3:
            smarter = team_a if awr_a > awr_b else team_b
            lines.append(f"**{smarter}** has the awareness edge ({max(awr_a, awr_b)} avg AWR) -- fewer blown assignments, faster reads.")
        for r in [r for r in adv_a if r["margin"] >= 4]:
            lines.append(f"The **{r['group']}** unit for **{team_a}** is a genuine mismatch.")
        for r in [r for r in adv_b if r["margin"] >= 4]:
            lines.append(f"**{team_b}** has a dominant edge at **{r['group']}**.")
        if wins_a > wins_b:
            verdict_team, verdict_color, verdict_desc = team_a, color_a, f"wins {wins_a} of {total} positional battles"
        elif wins_b > wins_a:
            verdict_team, verdict_color, verdict_desc = team_b, color_b, f"wins {wins_b} of {total} positional battles"
        else:
            verdict_team, verdict_color, verdict_desc = "Neither team", "#9ca3af", "-- this matchup is an absolute coin flip on paper"
        for line in lines:
            st.markdown(line)
        st.markdown(f"""<div style="padding:1rem 1.25rem;border-left:6px solid {verdict_color};background:{verdict_color}18;border-radius:8px;margin-top:1rem;"><strong>Roster Verdict:</strong> <span style="color:{verdict_color};font-size:1.05rem;font-weight:800;">{html.escape(verdict_team)}</span> {verdict_desc}. Paper never plays the game, but this one matters.</div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2 -- DEPTH CHART
    # ════════════════════════════════════════════════════════════════════════
    with tab_depth:
        st.subheader("📋 Full Depth Chart Comparison")
        st.caption("True 2-deep by position. 🔄 = redshirt. EligLeft = eligibility years remaining.")
        ALL_POSITIONS = {
            "Quarterback": ["QB"], "Halfback": ["HB", "FB"], "Wide Receiver": ["WR"],
            "Tight End": ["TE"], "Left Tackle": ["LT"], "Left Guard": ["LG"],
            "Center": ["C"], "Right Guard": ["RG"], "Right Tackle": ["RT"],
            "Defensive Tackle": ["DT"], "Left Edge": ["LEDG"], "Right Edge": ["REDG"],
            "MIKE LB": ["MIKE"], "WILL LB": ["WILL"], "SAM LB": ["SAM"],
            "Cornerback": ["CB"], "Free Safety": ["FS"], "Strong Safety": ["SS"],
        }
        for pos_label, pos_codes in ALL_POSITIONS.items():
            grp_a = roster_a[roster_a["Pos"].isin(pos_codes)].sort_values("OVR", ascending=False).reset_index(drop=True)
            grp_b = roster_b[roster_b["Pos"].isin(pos_codes)].sort_values("OVR", ascending=False).reset_index(drop=True)

            def fmt_player(df, idx):
                if len(df) > idx:
                    r = df.iloc[idx]
                    rs_tag = " 🔄" if r['IsRS'] else ""
                    return f"{r['Name']}{rs_tag} ({r['EligLeft']}yr) | {int(r['OVR'])} OVR / {int(r['SPD'])} SPD"
                return "—"

            st_a, bk_a = fmt_player(grp_a, 0), fmt_player(grp_a, 1)
            st_b, bk_b = fmt_player(grp_b, 0), fmt_player(grp_b, 1)
            ovr_a = grp_a.iloc[0]["OVR"] if len(grp_a) > 0 else 0
            ovr_b = grp_b.iloc[0]["OVR"] if len(grp_b) > 0 else 0
            edge = "A" if ovr_a > ovr_b + 1 else ("B" if ovr_b > ovr_a + 1 else "=")
            if edge == "A":   edge_html = f"<span style='color:{color_a};font-weight:700;font-size:0.75rem;'>▶ {team_a}</span>"
            elif edge == "B": edge_html = f"<span style='color:{color_b};font-weight:700;font-size:0.75rem;'>{team_b} ◀</span>"
            else:             edge_html = "<span style='color:#9ca3af;font-size:0.75rem;'>EVEN</span>"

            with st.expander(f"**{pos_label}**  |  {('▶ ' + team_a) if edge == 'A' else ((team_b + ' ◀') if edge == 'B' else 'Even')}", expanded=False):
                ca, cm, cb = st.columns([5, 2, 5])
                with ca:
                    st.markdown(f"<span style='color:{color_a};font-weight:700;font-size:0.85rem;'>{team_a}</span>", unsafe_allow_html=True)
                    st.markdown(f"**Starter:** {st_a}")
                    st.markdown(f"<span style='color:#9ca3af;font-size:0.8rem;'>Backup: {bk_a}</span>", unsafe_allow_html=True)
                with cm:
                    st.markdown(f"<div style='text-align:center;padding-top:1.2rem;'>{edge_html}</div>", unsafe_allow_html=True)
                with cb:
                    st.markdown(f"<span style='color:{color_b};font-weight:700;font-size:0.85rem;'>{team_b}</span>", unsafe_allow_html=True)
                    st.markdown(f"**Starter:** {st_b}")
                    st.markdown(f"<span style='color:#9ca3af;font-size:0.8rem;'>Backup: {bk_b}</span>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 3 -- INJURY RESILIENCE
    # ════════════════════════════════════════════════════════════════════════
    with tab_resilience:
        st.subheader("🩺 Injury Resilience Score")
        st.caption("Score drop when each group's best player is removed. 🟢 Solid depth  🟡 Some risk  🔴 One injury from disaster.")

        def resilience_score(df, positions):
            grp = df[df["Pos"].isin(positions)].nlargest(5, "OVR")
            if grp.empty:
                return 0, 0, None
            with_star   = grp["OVR"].mean() * 0.70 + grp["SPD"].mean() * 0.30
            star_row    = grp.iloc[0]
            without     = grp.iloc[1:]
            without_star = (without["OVR"].mean() * 0.70 + without["SPD"].mean() * 0.30) if not without.empty else 0
            drop = round(with_star - without_star, 1)
            rs_tag = " 🔄" if star_row['IsRS'] else ""
            elig_tag = f"({int(star_row['EligLeft'])}yr left)"
            return round(with_star, 1), drop, f"{star_row['Name']}{rs_tag} {elig_tag} | {int(star_row['OVR'])} OVR"

        hdr_cols = st.columns([3, 2, 2, 1, 2, 2])
        for col, label in zip(hdr_cols, ["Position Group", f"{team_a} Star", f"{team_a} Drop", "vs", f"{team_b} Star", f"{team_b} Drop"]):
            col.markdown(f"**{label}**")
        st.markdown("---")

        total_drop_a, total_drop_b = 0, 0
        for group_name, positions in POS_GROUPS.items():
            w_a, drop_a, star_a = resilience_score(roster_a, positions)
            w_b, drop_b, star_b = resilience_score(roster_b, positions)
            total_drop_a += drop_a
            total_drop_b += drop_b
            dc_a = "#ef4444" if drop_a >= 5 else ("#f59e0b" if drop_a >= 2.5 else "#22c55e")
            dc_b = "#ef4444" if drop_b >= 5 else ("#f59e0b" if drop_b >= 2.5 else "#22c55e")
            row_cols = st.columns([3, 2, 2, 1, 2, 2])
            row_cols[0].markdown(f"**{group_name}**")
            row_cols[1].markdown(f"<span style='font-size:0.78rem;color:#d1d5db;'>{star_a or '--'}</span>", unsafe_allow_html=True)
            row_cols[2].markdown(f"<span style='color:{dc_a};font-weight:700;'>-{drop_a}</span>", unsafe_allow_html=True)
            row_cols[3].markdown("<div style='text-align:center;color:#6b7280;'>|</div>", unsafe_allow_html=True)
            row_cols[4].markdown(f"<span style='font-size:0.78rem;color:#d1d5db;'>{star_b or '--'}</span>", unsafe_allow_html=True)
            row_cols[5].markdown(f"<span style='color:{dc_b};font-weight:700;'>-{drop_b}</span>", unsafe_allow_html=True)

        st.markdown("---")
        r1, r2, r3 = st.columns([3, 1, 3])
        with r1:
            st.markdown(f"<div style='text-align:center;'>{logo_html_a}</div>", unsafe_allow_html=True)
            st.metric(f"{team_a} Total Fragility", f"-{round(total_drop_a, 1)}", help="Lower = more resilient")
        with r3:
            st.markdown(f"<div style='text-align:center;'>{logo_html_b}</div>", unsafe_allow_html=True)
            st.metric(f"{team_b} Total Fragility", f"-{round(total_drop_b, 1)}", help="Lower = more resilient")
        more_fragile  = team_a if total_drop_a > total_drop_b else team_b
        more_resilient = team_b if total_drop_a > total_drop_b else team_a
        res_color = color_a if total_drop_a > total_drop_b else color_b
        st.markdown(f"""<div style="padding:0.8rem 1.25rem;border-left:5px solid {res_color};background:{res_color}15;border-radius:8px;margin-top:0.8rem;font-size:0.9rem;"><strong>{html.escape(more_fragile)}</strong> is more depth-dependent. <strong>{html.escape(more_resilient)}</strong> has the more resilient roster if stars go down.</div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 4 -- ROSTER COMPOSITION
    # ════════════════════════════════════════════════════════════════════════
    with tab_class:
        st.subheader("🎓 Roster Composition Breakdown")
        st.caption("Class distribution with redshirt-aware eligibility. 🔄 = currently redshirting.")

        def class_breakdown(df):
            total = len(df)
            rs_count   = int(df['IsRS'].sum())
            elig_avg   = round(df['EligLeft'].mean(), 1)
            young      = int((df['EligLeft'] >= 3).sum())
            veteran    = int((df['EligLeft'] <= 2).sum())
            class_counts = df['YrClass'].value_counts()
            return {
                "Freshmen": class_counts.get("Freshman", 0),
                "Sophomores": class_counts.get("Sophomore", 0),
                "Juniors": class_counts.get("Junior", 0),
                "Seniors": class_counts.get("Senior", 0),
                "Total": total,
                "Redshirts": rs_count,
                "Avg Elig": elig_avg,
                "Young (3-4yr elig)": young,
                "Veteran (1-2yr elig)": veteran,
            }

        cb_a = class_breakdown(roster_a)
        cb_b = class_breakdown(roster_b)

        classes = ["Freshmen", "Sophomores", "Juniors", "Seniors"]
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(name=team_a, x=classes, y=[cb_a[c] for c in classes], marker_color=color_a, opacity=0.85))
        fig2.add_trace(go.Bar(name=team_b, x=classes, y=[cb_b[c] for c in classes], marker_color=color_b, opacity=0.85))
        fig2.update_layout(barmode="group", height=320, margin=dict(t=30, b=30, l=20, r=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig2, use_container_width=True)

        mobile_metrics([
            {"label": f"{team_a} Redshirts", "value": str(cb_a["Redshirts"])},
            {"label": f"{team_a} Avg Elig",  "value": str(cb_a["Avg Elig"])},
            {"label": f"{team_a} Young",     "value": str(cb_a["Young (3-4yr elig)"])},
            {"label": f"{team_b} Redshirts", "value": str(cb_b["Redshirts"])},
            {"label": f"{team_b} Avg Elig",  "value": str(cb_b["Avg Elig"])},
            {"label": f"{team_b} Young",     "value": str(cb_b["Young (3-4yr elig)"])},
        ], cols_desktop=6)

        st.markdown("---")
        st.markdown("#### 🌟 Top Young Talent (3-4 eligibility years remaining)")
        young_cols = ["Name", "Pos", "ExpTag", "OVR", "SPD", "FV"]
        young_a = roster_a[roster_a["EligLeft"] >= 3].nlargest(8, "OVR")[young_cols].reset_index(drop=True)
        young_b = roster_b[roster_b["EligLeft"] >= 3].nlargest(8, "OVR")[young_cols].reset_index(drop=True)
        yc1, yc2 = st.columns(2)
        with yc1:
            st.markdown(f"<span style='color:{color_a};font-weight:800;'>{team_a}</span>", unsafe_allow_html=True)
            st.dataframe(young_a.rename(columns={"ExpTag": "Status", "FV": "FV Score"}), hide_index=True, use_container_width=True)
        with yc2:
            st.markdown(f"<span style='color:{color_b};font-weight:800;'>{team_b}</span>", unsafe_allow_html=True)
            st.dataframe(young_b.rename(columns={"ExpTag": "Status", "FV": "FV Score"}), hide_index=True, use_container_width=True)

        st.markdown("#### 🏆 Senior Leaders (final year)")
        vets_a = roster_a[roster_a["EligLeft"] == 1].nlargest(6, "OVR")[["Name", "Pos", "ExpTag", "OVR", "SPD", "AWR"]].reset_index(drop=True)
        vets_b = roster_b[roster_b["EligLeft"] == 1].nlargest(6, "OVR")[["Name", "Pos", "ExpTag", "OVR", "SPD", "AWR"]].reset_index(drop=True)
        vc1, vc2 = st.columns(2)
        with vc1:
            st.markdown(f"<span style='color:{color_a};font-weight:800;'>{team_a}</span>", unsafe_allow_html=True)
            if not vets_a.empty:
                st.dataframe(vets_a.rename(columns={"ExpTag": "Status"}), hide_index=True, use_container_width=True)
            else:
                st.caption("No seniors.")
        with vc2:
            st.markdown(f"<span style='color:{color_b};font-weight:800;'>{team_b}</span>", unsafe_allow_html=True)
            if not vets_b.empty:
                st.dataframe(vets_b.rename(columns={"ExpTag": "Status"}), hide_index=True, use_container_width=True)
            else:
                st.caption("No seniors.")

        # Redshirt breakdown
        st.markdown("---")
        st.markdown("#### 🔄 Redshirt Inventory")
        st.caption("Redshirts = players who gained a year in the program without burning eligibility. These players have more development than their class label suggests.")
        rs_a = roster_a[roster_a['IsRS']].sort_values("OVR", ascending=False)[["Name", "Pos", "ExpTag", "OVR", "SPD", "FV"]].reset_index(drop=True)
        rs_b = roster_b[roster_b['IsRS']].sort_values("OVR", ascending=False)[["Name", "Pos", "ExpTag", "OVR", "SPD", "FV"]].reset_index(drop=True)
        rc1, rc2 = st.columns(2)
        with rc1:
            st.markdown(f"<span style='color:{color_a};font-weight:800;'>{team_a} — {len(rs_a)} redshirts</span>", unsafe_allow_html=True)
            if not rs_a.empty:
                st.dataframe(rs_a.rename(columns={"ExpTag": "Status", "FV": "FV Score"}), hide_index=True, use_container_width=True)
            else:
                st.caption("No redshirts.")
        with rc2:
            st.markdown(f"<span style='color:{color_b};font-weight:800;'>{team_b} — {len(rs_b)} redshirts</span>", unsafe_allow_html=True)
            if not rs_b.empty:
                st.dataframe(rs_b.rename(columns={"ExpTag": "Status", "FV": "FV Score"}), hide_index=True, use_container_width=True)
            else:
                st.caption("No redshirts.")

    # ════════════════════════════════════════════════════════════════════════
    # TAB 5 -- FUTURE VALUE / PIPELINE
    # ════════════════════════════════════════════════════════════════════════
    with tab_pipeline:
        st.subheader("🚀 Future Value & Pipeline Analysis")
        st.caption("Future Value (FV) = OVR x 0.55 + Athleticism x 0.25 + Eligibility Years x 3.0. High FV + low OVR = high-ceiling athlete who hasn't peaked yet. 🌠 = High Ceiling flag (young + 82+ athleticism + sub-85 OVR).")

        # FV scatter plot: OVR vs FV, bubble size = SPD
        fv_cols = ["Name", "Pos", "ExpTag", "OVR", "SPD", "AthlScore", "EligLeft", "FV", "HighCeiling"]

        fig3 = go.Figure()
        for df, color, name in [(roster_a, color_a, team_a), (roster_b, color_b, team_b)]:
            ceiling_mask = df["HighCeiling"]
            # Regular players
            reg = df[~ceiling_mask]
            fig3.add_trace(go.Scatter(
                x=reg["OVR"], y=reg["FV"],
                mode="markers",
                name=name,
                marker=dict(color=color, size=reg["SPD"].apply(lambda s: max(6, int((s-60)/3))), opacity=0.65, line=dict(width=0)),
                text=reg.apply(lambda r: f"{r['Name']} ({r['Pos']}) | {int(r['EligLeft'])}yr left | FV:{r['FV']}", axis=1),
                hoverinfo="text",
            ))
            # High ceiling players
            ceil_players = df[ceiling_mask]
            if not ceil_players.empty:
                fig3.add_trace(go.Scatter(
                    x=ceil_players["OVR"], y=ceil_players["FV"],
                    mode="markers+text",
                    name=f"{name} 🌠 High Ceiling",
                    marker=dict(color=color, size=14, symbol="star", line=dict(width=1.5, color="white")),
                    text=ceil_players["Name"],
                    textposition="top center",
                    textfont=dict(size=9, color=color),
                    hovertext=ceil_players.apply(lambda r: f"{r['Name']} ({r['Pos']}) | {int(r['EligLeft'])}yr left | FV:{r['FV']}", axis=1),
                    hoverinfo="text",
                ))

        fig3.update_layout(
            xaxis_title="Current OVR", yaxis_title="Future Value Score",
            height=460, margin=dict(t=40, b=40, l=40, r=40),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="#374151"), yaxis=dict(gridcolor="#374151"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        )
        st.plotly_chart(fig3, use_container_width=True)
        st.caption("Bubble size = Speed rating. Stars (🌠) = High Ceiling players. Upper-left quadrant = low OVR but high future value -- the gems.")

        # Top 10 FV players each team
        st.markdown("---")
        st.markdown("#### 🏆 Top 10 Future Value Players")
        fv_disp = ["Name", "Pos", "ExpTag", "OVR", "SPD", "AthlScore", "EligLeft", "FV", "HighCeiling"]
        top_fv_a = roster_a.nlargest(10, "FV")[fv_disp].reset_index(drop=True)
        top_fv_b = roster_b.nlargest(10, "FV")[fv_disp].reset_index(drop=True)
        top_fv_a["HighCeiling"] = top_fv_a["HighCeiling"].apply(lambda x: "🌠" if x else "")
        top_fv_b["HighCeiling"] = top_fv_b["HighCeiling"].apply(lambda x: "🌠" if x else "")
        fv1, fv2 = st.columns(2)
        with fv1:
            st.markdown(f"<span style='color:{color_a};font-weight:800;'>{team_a}</span>", unsafe_allow_html=True)
            st.dataframe(top_fv_a.rename(columns={"ExpTag": "Status", "AthlScore": "Athl", "EligLeft": "Elig", "HighCeiling": "🌠"}), hide_index=True, use_container_width=True)
        with fv2:
            st.markdown(f"<span style='color:{color_b};font-weight:800;'>{team_b}</span>", unsafe_allow_html=True)
            st.dataframe(top_fv_b.rename(columns={"ExpTag": "Status", "AthlScore": "Athl", "EligLeft": "Elig", "HighCeiling": "🌠"}), hide_index=True, use_container_width=True)

        # High ceiling sleepers specifically
        st.markdown("---")
        st.markdown("#### 🌠 High Ceiling Sleepers")
        st.caption("Young athletes (3-4yr eligibility) with elite athleticism (82+ avg SPD/ACC/AGI/COD) but current OVR still under 85. These are the breakout candidates.")
        sleepers_a = roster_a[roster_a["HighCeiling"]].sort_values("FV", ascending=False)[["Name", "Pos", "ExpTag", "OVR", "SPD", "AthlScore", "EligLeft", "FV"]].reset_index(drop=True)
        sleepers_b = roster_b[roster_b["HighCeiling"]].sort_values("FV", ascending=False)[["Name", "Pos", "ExpTag", "OVR", "SPD", "AthlScore", "EligLeft", "FV"]].reset_index(drop=True)
        sl1, sl2 = st.columns(2)
        with sl1:
            st.markdown(f"<span style='color:{color_a};font-weight:800;'>{team_a} — {len(sleepers_a)} sleepers</span>", unsafe_allow_html=True)
            if not sleepers_a.empty:
                st.dataframe(sleepers_a.rename(columns={"ExpTag": "Status", "AthlScore": "Athl", "EligLeft": "Elig"}), hide_index=True, use_container_width=True)
            else:
                st.caption("No high-ceiling sleepers found.")
        with sl2:
            st.markdown(f"<span style='color:{color_b};font-weight:800;'>{team_b} — {len(sleepers_b)} sleepers</span>", unsafe_allow_html=True)
            if not sleepers_b.empty:
                st.dataframe(sleepers_b.rename(columns={"ExpTag": "Status", "AthlScore": "Athl", "EligLeft": "Elig"}), hide_index=True, use_container_width=True)
            else:
                st.caption("No high-ceiling sleepers found.")

        # Pipeline summary
        st.markdown("---")
        avg_fv_a = round(roster_a["FV"].mean(), 1)
        avg_fv_b = round(roster_b["FV"].mean(), 1)
        ceiling_a = int(roster_a["HighCeiling"].sum())
        ceiling_b = int(roster_b["HighCeiling"].sum())
        better_pipeline = team_a if avg_fv_a > avg_fv_b else team_b
        pipeline_color  = color_a if avg_fv_a > avg_fv_b else color_b
        st.markdown(f"""<div style="padding:0.9rem 1.25rem;border-left:6px solid {pipeline_color};background:{pipeline_color}15;border-radius:8px;font-size:0.92rem;">
        <strong>Pipeline Verdict:</strong> <span style="color:{pipeline_color};font-weight:800;">{html.escape(better_pipeline)}</span> has the stronger future value roster
        (avg FV: <strong>{avg_fv_a}</strong> vs <strong>{avg_fv_b}</strong>). High-ceiling sleepers: <strong style="color:{color_a};">{team_a} {ceiling_a}</strong> vs <strong style="color:{color_b};">{team_b} {ceiling_b}</strong>.
        The team with more sleepers is one progression cycle away from a significant talent jump.
        </div>""", unsafe_allow_html=True)


def load_data():
    try:
        # LOAD ALL CORE FILES
        scores = pd.read_csv('scores.csv')
        rec = pd.read_csv('recruiting.csv')
        champs = pd.read_csv('champs.csv')
        draft = pd.read_csv('UserDraftPicks.csv')
        ratings = pd.read_csv('TeamRatingsHistory.csv')
        heisman = pd.read_csv('Heisman_History.csv')
        try:
            heisman_fin = pd.read_csv('Heisman_Finalists.csv')
            heisman_fin['USER'] = safe_title_series(heisman_fin['USER'])
            heisman_fin['TEAM'] = heisman_fin['TEAM'].astype(str).str.strip()
        except Exception:
            heisman_fin = None
        coty = pd.read_csv('COTY.csv')

        # STANDARDIZE MAJOR TEXT FIELDS
        draft['USER'] = safe_title_series(draft['USER'])
        rec['USER'] = safe_title_series(rec['USER'])
        if 'Teams' in rec.columns:
            rec['Teams'] = rec['Teams'].astype(str).str.strip()
        champs['user'] = safe_title_series(champs['user'])
        champs['Team'] = champs['Team'].astype(str).str.strip()
        ratings['USER'] = safe_title_series(ratings['USER'])
        ratings['TEAM'] = ratings['TEAM'].astype(str).str.strip()
        heisman['USER'] = safe_title_series(heisman['USER'])
        heisman['TEAM'] = heisman['TEAM'].astype(str).str.strip()
        coty['User'] = safe_title_series(coty['User'])
        coty['Team'] = coty['Team'].astype(str).str.strip()

        # STANDARDIZE KEYS
        v_user_key = smart_col(scores, ['Vis_User', 'Visitor User', 'Vis User'])
        h_user_key = smart_col(scores, ['Home_User', 'Home User'])
        v_score_key = smart_col(scores, ['Vis Score', 'Vis_Score'])
        h_score_key = smart_col(scores, ['Home Score', 'Home_Score'])
        yr_key = smart_col(scores, ['YEAR', 'Year'])
        champ_user_key = smart_col(champs, ['user', 'User', 'User of team'])

        # STANDARDIZE KEYS FOR AWARDS
        h_yr_key = smart_col(heisman, ['Year', 'YEAR'])
        h_player_key = smart_col(heisman, ['Player', 'Winner', 'Name', 'NAME'])
        h_school_key = smart_col(heisman, ['School', 'Team', 'University', 'TEAM'])
        h_user_key_award = smart_col(heisman, ['User', 'USER'])
        c_yr_key = smart_col(coty, ['Year', 'YEAR'])
        c_coach_key = smart_col(coty, ['Coach', 'Winner', 'Name'])
        c_school_key = smart_col(coty, ['School', 'Team', 'University'])
        c_user_key_award = smart_col(coty, ['User', 'USER'])

        # CLEAN SCORES
        scores['V_User_Final'] = safe_title_series(scores[v_user_key])
        scores['H_User_Final'] = safe_title_series(scores[h_user_key])
        scores['Visitor_Final'] = scores[smart_col(scores, ['Visitor'])].astype(str).str.strip()
        scores['Home_Final'] = scores[smart_col(scores, ['Home'])].astype(str).str.strip()
        scores['V_Pts'] = pd.to_numeric(scores[v_score_key], errors='coerce')
        scores['H_Pts'] = pd.to_numeric(scores[h_score_key], errors='coerce')
        scores = scores.dropna(subset=['V_Pts', 'H_Pts']).copy()
        scores['Margin'] = (scores['H_Pts'] - scores['V_Pts']).abs()
        scores['Total Points'] = scores['H_Pts'] + scores['V_Pts']
        scores['Winner_User'] = np.where(scores['H_Pts'] > scores['V_Pts'], scores['H_User_Final'], scores['V_User_Final'])
        scores['Loser_User'] = np.where(scores['H_Pts'] > scores['V_Pts'], scores['V_User_Final'], scores['H_User_Final'])
        scores['Winner_Team'] = np.where(scores['H_Pts'] > scores['V_Pts'], scores['Home_Final'], scores['Visitor_Final'])
        scores['Loser_Team'] = np.where(scores['H_Pts'] > scores['V_Pts'], scores['Visitor_Final'], scores['Home_Final'])

        all_users = sorted([
            u for u in pd.concat([scores['V_User_Final'], scores['H_User_Final']]).dropna().unique()
            if str(u).upper() != 'CPU' and str(u).lower() != 'nan'
        ])
        years_available = sorted(pd.to_numeric(scores[yr_key], errors='coerce').dropna().astype(int).unique(), reverse=True)

        # MASTER STATS ENGINE
        stats_list, h2h_rows, h2h_numeric, rivalry_rows = [], [], [], []
        natty_counts = champs[champs[champ_user_key].str.upper() != 'CPU'][champ_user_key].value_counts().to_dict()

        for user in all_users:
            h_games = scores[scores['H_User_Final'] == user]
            v_games = scores[scores['V_User_Final'] == user]
            all_u_games = pd.concat([h_games, v_games], ignore_index=True)

            wins = len(h_games[h_games['H_Pts'] > h_games['V_Pts']]) + len(v_games[v_games['V_Pts'] > v_games['H_Pts']])
            losses = len(all_u_games) - wins

            u_draft = draft[draft['USER'] == user]
            n_sent = int(u_draft['Guys Sent to NFL'].iloc[0]) if not u_draft.empty else 0
            n_1st = int(u_draft['1st Rounders'].iloc[0]) if not u_draft.empty else 0
            conf_t = int(u_draft['Conference Titles'].iloc[0]) if not u_draft.empty else 0
            cfp_w = int(u_draft['CFP Wins'].iloc[0]) if not u_draft.empty else 0
            cfp_l = int(u_draft['CFP Losses'].iloc[0]) if not u_draft.empty else 0
            natty_a = int(u_draft['National Title Appearances'].iloc[0]) if not u_draft.empty else 0
            career_wins = int(u_draft['Career Wins'].iloc[0]) if not u_draft.empty else wins
            career_losses = int(u_draft['Career Losses'].iloc[0]) if not u_draft.empty else losses
            career_win_pct = round((career_wins / max(1, career_wins + career_losses)) * 100, 1)

            hof_points = (natty_counts.get(user, 0) * 50) + (n_1st * 10)
            goat_score = (
                natty_counts.get(user, 0) * 200
                + natty_a * 80
                + cfp_w * 40
                + conf_t * 25
                + n_1st * 12
                + n_sent * 4
            )
            dynasty_score = (
                natty_counts.get(user, 0) * 100
                + natty_a * 40
                + cfp_w * 25
                + conf_t * 15
                + n_1st * 8
                + n_sent * 3
            )

            stats_list.append({
                'User': user,
                'HoF Points': int(hof_points),
                'GOAT Score': int(goat_score),
                'Dynasty Score': int(dynasty_score),
                'Record': f"{wins}-{losses}",
                'Career Record': f"{career_wins}-{career_losses}",
                'Career Win %': career_win_pct,
                'Natties': natty_counts.get(user, 0),
                'Drafted': n_sent,
                '1st Rounders': n_1st,
                'Conf Titles': conf_t,
                'CFP Wins': cfp_w,
                'CFP Losses': cfp_l,
                'Natty Apps': natty_a,
            })

            h2h_row = {'User': user}
            h2h_num_row = []
            for opp in all_users:
                if user == opp:
                    h2h_row[opp] = "-"
                    h2h_num_row.append(0)
                else:
                    vs = scores[
                        ((scores['V_User_Final'] == user) & (scores['H_User_Final'] == opp)) |
                        ((scores['V_User_Final'] == opp) & (scores['H_User_Final'] == user))
                    ]
                    vw = len(vs[
                        ((vs['V_User_Final'] == user) & (vs['V_Pts'] > vs['H_Pts'])) |
                        ((vs['H_User_Final'] == user) & (vs['H_Pts'] > vs['V_Pts']))
                    ])
                    vl = len(vs) - vw
                    h2h_row[opp] = f"{vw}-{vl}"
                    h2h_num_row.append(vw - vl)

                    if user < opp and len(vs) > 0:
                        balance = 1 - (abs(vw - vl) / max(1, len(vs)))
                        rivalry_score = round((len(vs) * 2.5) + (balance * 10), 1)
                        rivalry_rows.append({
                            'Matchup': f"{user} vs {opp}",
                            'Games': int(len(vs)),
                            user: vw,
                            opp: vl,
                            'Balance': round(balance, 2),
                            'Avg Margin': round(vs['Margin'].mean(), 1),
                            'Rivalry Score': rivalry_score
                        })

            h2h_rows.append(h2h_row)
            h2h_numeric.append(h2h_num_row)

        stats_df = pd.DataFrame(stats_list)
        h2h_df = pd.DataFrame(h2h_rows)
        h2h_heat = pd.DataFrame(h2h_numeric, index=all_users, columns=all_users)
        rivalry_df = pd.DataFrame(rivalry_rows).sort_values(['Rivalry Score', 'Games'], ascending=[False, False]) if rivalry_rows else pd.DataFrame()

        # Ratings prep
        r_2041 = ratings[ratings['YEAR'] == 2041].copy()
        r_2040 = ratings[ratings['YEAR'] == 2040].copy()
        r_2041['USER'] = safe_title_series(r_2041['USER'])
        r_2040['USER'] = safe_title_series(r_2040['USER'])
        r_2041['TEAM'] = r_2041['TEAM'].astype(str).str.strip()
        r_2040['TEAM'] = r_2040['TEAM'].astype(str).str.strip()

        bcr_col = 'Blue Chip Ratio (4 & 5 star recruit ratio on roster)'
        r_2041['BCR_Val'] = pd.to_numeric(r_2041[bcr_col].astype(str).str.replace('%', '', regex=False), errors='coerce').fillna(0)
        r_2040['BCR_Val'] = pd.to_numeric(r_2040[bcr_col].astype(str).str.replace('%', '', regex=False), errors='coerce').fillna(0)

        yes_no_cols = [
            'QB is Elite (90+)',
            'QB is Leader (85+)',
            'QB is Average Joe (between 80 and 84)',
            'Qb is Ass (under 80)',
            'Star Skill Guy is Generational Speed?'
        ]
        r_2041 = normalize_yes_no_columns(r_2041, yes_no_cols)
        r_2040 = normalize_yes_no_columns(r_2040, yes_no_cols)

        # Rename legacy column name from TeamRatingsHistory.csv before any processing
        _gb_old = 'Game Breakers (90+ Speed & 90+ Acceleration)'
        _gb_new = 'Quad 90 (90+ SPD, ACC, AGI & COD)'
        if _gb_old in r_2041.columns:
            r_2041 = r_2041.rename(columns={_gb_old: _gb_new})
        if _gb_old in r_2040.columns:
            r_2040 = r_2040.rename(columns={_gb_old: _gb_new})

        for num_col in [
            'OVERALL', 'OFFENSE', 'DEFENSE', 'Team Speed (90+ Speed Guys)',
            'Def Speed (90+ speed)', 'Off Speed (90+ speed)',
            'Quad 90 (90+ SPD, ACC, AGI & COD)',
            'Generational (96+ speed or 96+ Acceleration)',
            'Current CFP Ranking', 'QB OVR'
        ]:
            if num_col in r_2041.columns:
                r_2041[num_col] = pd.to_numeric(r_2041[num_col], errors='coerce')
            if num_col in r_2040.columns:
                r_2040[num_col] = pd.to_numeric(r_2040[num_col], errors='coerce')

        def get_improvement(row):
            prev = r_2040[r_2040['TEAM'].str.lower() == str(row['TEAM']).strip().lower()]
            return int(row['OVERALL'] - prev['OVERALL'].values[0]) if not prev.empty else 0

        r_2041['Improvement'] = r_2041.apply(get_improvement, axis=1)

        meta = {
            'yr': yr_key,
            'vt': smart_col(scores, ['Visitor']),
            'vs': v_score_key,
            'ht': smart_col(scores, ['Home']),
            'hs': h_score_key,
            'h_yr': h_yr_key,
            'h_player': h_player_key,
            'h_school': h_school_key,
            'h_user': h_user_key_award,
            'c_yr': c_yr_key,
            'c_coach': c_coach_key,
            'c_school': c_school_key,
            'c_user': c_user_key_award,
        }

        return {
            'scores': scores,
            'stats': stats_df,
            'all_users': all_users,
            'years': years_available,
            'meta': meta,
            'r_2041': r_2041,
            'h2h_df': h2h_df,
            'h2h_heat': h2h_heat,
            'rivalry_df': rivalry_df,
            'coty': coty,
            'heisman': heisman,
            'heisman_fin': heisman_fin,
            'rec': rec,
            'draft': draft,
            'champs': champs,
            'ratings': ratings,
        }
    except Exception as e:
        st.error(f"⚠️ Load Error: {e}")
        return None


def get_recent_recruiting_score(rec_df, user, team=None, current_year=2041, lookback=3):
    user = str(user).strip().title()
    rows = rec_df[rec_df['USER'] == user].copy()

    if team is not None and 'Teams' in rec_df.columns:
        rows_team = rows[rows['Teams'].astype(str).str.strip().str.lower() == str(team).strip().lower()]
        if not rows_team.empty:
            rows = rows_team

    if rows.empty:
        return 50.0

    vals = []
    for y in range(current_year - lookback + 1, current_year + 1):
        col = str(y)
        if col in rows.columns:
            for _, row in rows.iterrows():
                v = clean_rank_value(row[col])
                if not pd.isna(v):
                    vals.append(v)

    if not vals:
        historic_cols = [c for c in rows.columns if str(c).isdigit()]
        for col in historic_cols[-lookback:]:
            for _, row in rows.iterrows():
                v = clean_rank_value(row[col])
                if not pd.isna(v):
                    vals.append(v)

    if not vals:
        return 50.0

    avg_rank = float(np.mean(vals))
    return float(max(1, min(100, 101 - avg_rank)))




def get_ranked_schedule_counts(scores_df, user, rank_map):
    user = str(user).strip().title()
    games = scores_df[(scores_df['V_User_Final'] == user) | (scores_df['H_User_Final'] == user)].copy()
    ranked = 0
    top10 = 0
    for _, g in games.iterrows():
        opp = g['Home_Final'] if g['V_User_Final'] == user else g['Visitor_Final']
        rank = rank_map.get(str(opp).strip())
        if rank is not None and not pd.isna(rank):
            ranked += 1
            if float(rank) <= 10:
                top10 += 1
    return ranked, top10


def render_recruiting_snapshot_table(df):
    rows_html = []
    for _, row in df.sort_values('Rank').head(25).iterrows():
        team = str(row.get('Team', ''))
        primary = get_team_primary_color(team)
        logo_uri = image_file_to_data_uri(get_logo_source(team))
        logo_html = f"<img src='{logo_uri}' style='width:34px;height:34px;object-fit:contain;'/>" if logo_uri else "<div style='font-size:20px;'>🏈</div>"
        cells = [f"""
        <td style="padding:10px 12px;border-bottom:1px solid #334155;white-space:nowrap;">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="font-weight:800;min-width:24px;text-align:center;color:#e5e7eb;">#{int(row.get('Rank', 0))}</div>
            <div style="width:38px;text-align:center;">{logo_html}</div>
            <div style="font-weight:800;color:{primary};">{html.escape(team)}</div>
          </div>
        </td>
        """]
        vals = [
            str(int(row.get('Total', 0))),
            str(int(row.get('5★', 0))),
            str(int(row.get('4★', 0))),
            str(int(row.get('3★', 0))),
            f"{float(row.get('Points', 0)):.2f}",
            f"{float(row.get('Blue Chip Ratio', 0)):.3f}",
        ]
        for disp in vals:
            cells.append(f"<td style='padding:10px 12px;border-bottom:1px solid #334155;text-align:center;white-space:nowrap;color:#e5e7eb;'>{html.escape(disp)}</td>")
        rows_html.append(f"<tr style='border-left:6px solid {primary};background:linear-gradient(90deg,{primary}22,rgba(15,23,42,.95) 14%);'>{''.join(cells)}</tr>")
    table_html = f"""
    <div style="overflow-x:auto;border:1px solid #334155;border-radius:14px;background:#0f172a;">
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead>
          <tr style="background:#111827;color:#f8fafc;">
            <th style="text-align:left;padding:10px 12px;color:#f8fafc;font-weight:800;">Top 25 Snapshot</th>
            <th style="padding:10px 12px;color:#f8fafc;font-weight:800;">Total</th>
            <th style="padding:10px 12px;color:#f8fafc;font-weight:800;">5★</th>
            <th style="padding:10px 12px;color:#f8fafc;font-weight:800;">4★</th>
            <th style="padding:10px 12px;color:#f8fafc;font-weight:800;">3★</th>
            <th style="padding:10px 12px;color:#f8fafc;font-weight:800;">Points</th>
            <th style="padding:10px 12px;color:#f8fafc;font-weight:800;">Blue Chip Ratio</th>
          </tr>
        </thead>
        <tbody>{''.join(rows_html)}</tbody>
      </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)


# ── Conference strength tiers ─────────────────────────────────────────────────
# Calibrated to THIS dynasty's actual conference power — not real-world 2024.
# Updated by league consensus. Scale: A+=12 down to D+=0.5
CONF_STRENGTH = {
    'Big 12':       12.0,  # A+ — co-king of the dynasty
    'B1G':          12.0,  # A+ — co-king of the dynasty
    'SEC':          10.0,  # A  — still a murderers row, just a tick behind
    'ACC':           8.0,  # A- — real teeth, not a pushover
    'Independents':  6.5,  # B+ — FBS Independents, no conf games to hide in
    'American':      5.0,  # B
    'MWC':           4.0,  # B-
    'Pac-12':        3.0,  # C+
    'MAC':           2.0,  # C
    'Sun Belt':      1.0,  # C-
    'CUSA':          0.5,  # D+
    'Other':         0.0,
}

def conf_bonus(conference):
    return CONF_STRENGTH.get(str(conference).strip(), 0.0)

def build_2041_model_table(r_2041, stats_df, rec_df):
    df = r_2041.copy()

    # TeamRatingsHistory.csv still uses the old column name — alias it to the new one.
    # The live roster computation will overwrite these values for the Speed Freaks tab,
    # but we need the column to exist under the new name throughout the model build.
    _old_gb = 'Game Breakers (90+ Speed & 90+ Acceleration)'
    _new_q90 = 'Quad 90 (90+ SPD, ACC, AGI & COD)'
    if _old_gb in df.columns and _new_q90 not in df.columns:
        df = df.rename(columns={_old_gb: _new_q90})
    if _new_q90 not in df.columns:
        df[_new_q90] = 0
    df[_new_q90] = pd.to_numeric(df[_new_q90], errors='coerce').fillna(0)

    # Pull conference from TeamRatingsHistory if present
    if 'CONFERENCE' not in df.columns:
        try:
            _rat_conf = pd.read_csv('TeamRatingsHistory.csv')[['TEAM','CONFERENCE']].drop_duplicates('TEAM')
            df = df.merge(_rat_conf, on='TEAM', how='left')
        except Exception:
            pass
    if 'CONFERENCE' not in df.columns:
        df['CONFERENCE'] = 'Other'
    df['CONFERENCE'] = df['CONFERENCE'].fillna('Other')

    stats_lookup = stats_df[['User', 'Career Win %', 'Career Record', 'Natties', 'Natty Apps', 'CFP Wins', 'CFP Losses', 'Conf Titles']].copy()
    stats_lookup = stats_lookup.rename(columns={'User': 'USER'})
    df = df.merge(stats_lookup, on='USER', how='left')

    df['Career Win %'] = pd.to_numeric(df['Career Win %'], errors='coerce').fillna(50.0)
    df['Recruit Score'] = df.apply(lambda x: get_recent_recruiting_score(rec_df, x['USER'], x['TEAM']), axis=1)
    df['QB Tier'] = df.apply(qb_label, axis=1)

    # --- schedule strength / resume inputs from latest TeamRatingsHistory ---
    for col in ['Combined Opponent Wins', 'Combined Opponent Losses', 'Current Record Wins', 'Current Record Losses']:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df['Opponent Games'] = df['Combined Opponent Wins'] + df['Combined Opponent Losses']
    df['Current Games'] = df['Current Record Wins'] + df['Current Record Losses']

    df['Opponent Win %'] = np.where(
        df['Opponent Games'] > 0,
        (df['Combined Opponent Wins'] / df['Opponent Games']) * 100,
        50.0
    )
    df['Current Win %'] = np.where(
        df['Current Games'] > 0,
        (df['Current Record Wins'] / df['Current Games']) * 100,
        50.0
    )

    max_opp_games = max(1.0, float(df['Opponent Games'].max()))
    opp_volume_pct = (df['Opponent Games'] / max_opp_games) * 100
    rank_map = dict(get_cfp_rankings_snapshot()[['Team', 'Rank']].values)
    ranked_counts = df['USER'].apply(lambda u: get_ranked_schedule_counts(scores, u, rank_map))
    df['Ranked Teams Faced'] = ranked_counts.apply(lambda x: x[0])
    df['Top 10 Teams Faced'] = ranked_counts.apply(lambda x: x[1])
    max_ranked = max(1.0, float(df['Ranked Teams Faced'].max()))
    max_top10 = max(1.0, float(df['Top 10 Teams Faced'].max()))
    ranked_pct = (df['Ranked Teams Faced'] / max_ranked) * 100
    top10_pct = (df['Top 10 Teams Faced'] / max_top10) * 100
    df['SOS'] = (
        df['Opponent Win %'] * 0.56
        + opp_volume_pct * 0.14
        + ranked_pct * 0.18
        + top10_pct * 0.12
    ).round(1)
    df['Resume Score'] = (df['Current Win %'] * 0.58 + df['SOS'] * 0.42).round(1)

    def qb_natty_bonus(row):
        if row['QB Tier'] == 'Elite':
            return 34.0
        if row['QB Tier'] == 'Leader':
            return 20.0
        if row['QB Tier'] == 'Average Joe':
            return -12.0
        if row['QB Tier'] == 'Ass':
            return -30.0
        return 0.0

    def qb_cfp_bonus(row):
        if row['QB Tier'] == 'Elite':
            return 24.0
        if row['QB Tier'] == 'Leader':
            return 15.0
        if row['QB Tier'] == 'Average Joe':
            return -9.0
        if row['QB Tier'] == 'Ass':
            return -22.0
        return 0.0

    def raw_contender_score(row):
        _u_s_rows = stats_df[stats_df['User'] == row['USER']]
        u_s = _u_s_rows.iloc[0] if not _u_s_rows.empty else pd.Series({
            'Natties': 0, 'Natty Apps': 0, 'CFP Wins': 0, 'Conf Titles': 0,
            'CFP Losses': 0, 'Career Win %': 0.5
        })

        # Pedigree: first 3 natties = coaching credibility (proven closer).
        # Beyond 3 it stops mattering — you still have to field a team this year.
        # Old formula gave 7-title coaches 168 pts before a single roster stat counted.
        # Hard cap prevents dynasty history from drowning out current team quality.
        natty_cred    = min(int(u_s.get('Natties', 0)), 3)
        pedigree_bonus = (
            natty_cred * 8
            + min(int(u_s.get('Natty Apps', 0)), 4) * 4
            + u_s['CFP Wins'] * 2.0
            + u_s['Conf Titles'] * 0.8
        )
        heartbreak_penalty = max(0, u_s['Natty Apps'] - u_s['Natties']) * 0.5
        cfp_fail_penalty = u_s['CFP Losses'] * 0.8

        team_speed_component = (
            row['Team Speed (90+ Speed Guys)'] * 3.0
            + row['Off Speed (90+ speed)'] * 1.55
            + row['Def Speed (90+ speed)'] * 1.55
        )
        cfp_bonus = cfp_rank_bonus(row.get('Current CFP Ranking', np.nan))

        raw = (
            row['OVERALL'] * 3.7
            + row['OFFENSE'] * 0.68
            + row['DEFENSE'] * 0.68
            + team_speed_component
            + row['Quad 90 (90+ SPD, ACC, AGI & COD)'] * 1.65
            + row['Generational (96+ speed or 96+ Acceleration)'] * 7.2
            + row['BCR_Val'] * 0.52
            + row['Recruit Score'] * 0.58
            + row['Career Win %'] * 0.26
            + row['Current Win %'] * 0.45
            + row['SOS'] * 0.40
            + row['Resume Score'] * 0.28
            + cfp_bonus * 1.15
            + qb_natty_bonus(row)
            + pedigree_bonus
            - heartbreak_penalty
            - cfp_fail_penalty
        )

        if row['OVERALL'] < 88:
            raw -= 24
        if row['OFFENSE'] < 85:
            raw -= 6
        if row['DEFENSE'] < 85:
            raw -= 6
        if row['BCR_Val'] < 35:
            raw -= 6
        if row['Team Speed (90+ Speed Guys)'] < 10:
            raw -= 6
        if row['Current Record Losses'] >= 2:
            raw -= 3.5 * (row['Current Record Losses'] - 1)

        # ── INJURY PENALTY ──────────────────────────────────────────────────────
        # Injuries that affect Bowl Week 1 eligibility (weeks remaining > 0 at bowl time).
        # Week penalties are relative to current bowl round.
        # QB down = brutal. Skill/OL = moderate. DL = small.
        INJURY_IMPACT = {
            # (team_name): [(pos, ovr, weeks_remaining, status)]
            'San Jose State': [
                ('QB',   85, 27, 'Injured'),   # Shorter — out all bowls
                ('LT',   86,  4, 'Injured'),   # Caplan — out Bowl 1
            ],
            'Texas Tech': [
                ('LT',   82,  2, 'Injured'),   # Cota — back for Bowl 2
            ],
            'USF': [
                ('RG',   76,  4, 'Injured'),   # Christmas — out Bowl 1
            ],
            'Bowling Green': [
                ('DT',   84, 24, 'Injured'),   # Franco — out all bowls
            ],
            'Florida': [
                ('LEDG', 80,  1, 'Injured'),   # Ivie — likely back Bowl 1
                ('MIKE', 87, 14, 'Injured'),   # Casey — out Bowl 1
            ],
            'Florida State': [
                ('QB',   80,  3, 'Injured'),   # Winterswyk — back Bowl 1
                ('WR',   90, 20, 'Injured'),   # Fe'esago — out all bowls
            ],
        }

        team_name = row.get('TEAM', '')
        injuries  = INJURY_IMPACT.get(team_name, [])
        inj_penalty = 0.0
        for pos, ovr, weeks, status in injuries:
            if status != 'Injured' or weeks <= 0:
                continue
            ovr_mult = (ovr - 75) / 20.0  # scale: 75 OVR=0.0, 95 OVR=1.0
            ovr_mult = max(0.1, min(1.0, ovr_mult))
            if pos in ('QB',):
                base = 38.0 if weeks >= 8 else (18.0 if weeks >= 3 else 8.0)
            elif pos in ('WR', 'HB', 'TE'):
                base = 14.0 if weeks >= 8 else (8.0 if weeks >= 3 else 3.0)
            elif pos in ('LT', 'RT', 'LG', 'RG', 'C', 'MIKE', 'LEDG', 'REDG'):
                base = 10.0 if weeks >= 8 else (5.0 if weeks >= 3 else 2.0)
            else:  # DT, DE, CB, S, etc.
                base = 6.0 if weeks >= 8 else (3.0 if weeks >= 3 else 1.0)
            inj_penalty += base * ovr_mult

        raw -= inj_penalty
        return raw

    df['Contender Raw'] = df.apply(raw_contender_score, axis=1)

    temp = max(10.5, df['Contender Raw'].std() * 0.92)
    raw_shift = df['Contender Raw'] - df['Contender Raw'].max()
    exp_scores = np.exp(raw_shift / temp)
    natty_probs = (exp_scores / exp_scores.sum()) * 100
    df['Natty Odds'] = natty_probs.round(1)

    def stock_label(row):
        if row['Natty Odds'] >= 24 and row['Improvement'] >= 0:
            return "🚀 Surging"
        if row['Natty Odds'] >= 17:
            return "📈 Rising"
        if row['Improvement'] <= -2 or row['OVERALL'] < 82:
            return "📉 In Trouble"
        return "➖ Stable"

    df['Program Stock'] = df.apply(stock_label, axis=1)

    # ── PRESEASON VERSIONS (Dynasty News only) ────────────────────────────────
    # Uses only inputs known before the season starts — no win%, no CFP rank,
    # no resume, no current losses, no injuries. Pure roster + history.
    def preseason_contender_score(row):
        _u_s_rows = stats_df[stats_df['User'] == row['USER']]
        u_s = _u_s_rows.iloc[0] if not _u_s_rows.empty else pd.Series({
            'Natties': 0, 'Natty Apps': 0, 'CFP Wins': 0, 'Conf Titles': 0,
            'CFP Losses': 0, 'Career Win %': 0.5
        })
        natty_cred = min(int(u_s.get('Natties', 0)), 3)
        pedigree_bonus = (
            natty_cred * 8
            + min(int(u_s.get('Natty Apps', 0)), 4) * 4
            + u_s['CFP Wins'] * 2.0
            + u_s['Conf Titles'] * 0.8
        )
        heartbreak_penalty = max(0, u_s['Natty Apps'] - u_s['Natties']) * 0.5
        cfp_fail_penalty = u_s['CFP Losses'] * 0.8
        team_speed_component = (
            row['Team Speed (90+ Speed Guys)'] * 3.0
            + row['Off Speed (90+ speed)'] * 1.55
            + row['Def Speed (90+ speed)'] * 1.55
        )
        raw = (
            row['OVERALL'] * 3.7
            + row['OFFENSE'] * 0.68
            + row['DEFENSE'] * 0.68
            + team_speed_component
            + row['Quad 90 (90+ SPD, ACC, AGI & COD)'] * 1.65
            + row['Generational (96+ speed or 96+ Acceleration)'] * 7.2
            + row['BCR_Val'] * 0.52
            + row['Recruit Score'] * 0.58
            + row['Career Win %'] * 0.26
            + row['SOS'] * 0.40
            + qb_natty_bonus(row)
            + pedigree_bonus
            - heartbreak_penalty
            - cfp_fail_penalty
            + conf_bonus(row.get('CONFERENCE', 'Other'))
            # ── intentionally excluded ──
            # Current Win %   — unknown preseason
            # Resume Score    — built from game results
            # CFP Rank bonus  — doesn't exist preseason
            # Current losses  — unknown preseason
            # Injury penalty  — happened during season
        )
        if row['OVERALL'] < 88:
            raw -= 24
        if row['OFFENSE'] < 85:
            raw -= 6
        if row['DEFENSE'] < 85:
            raw -= 6
        if row['BCR_Val'] < 35:
            raw -= 6
        if row['Team Speed (90+ Speed Guys)'] < 10:
            raw -= 6
        return raw

    _pre_raw = df.apply(preseason_contender_score, axis=1)
    _pre_temp = max(10.5, _pre_raw.std() * 0.92)
    _pre_shift = _pre_raw - _pre_raw.max()
    _pre_exp = np.exp(_pre_shift / _pre_temp)
    df['Preseason Natty Odds'] = (_pre_exp / _pre_exp.sum() * 100).round(1)

    def preseason_power_index(row):
        _u_s_pi_rows = stats_df[stats_df['User'] == row['USER']]
        u_s_pi = _u_s_pi_rows.iloc[0] if not _u_s_pi_rows.empty else pd.Series({'Natties': 0})
        coaching_cred = min(int(u_s_pi.get('Natties', 0)), 2) * 2.5
        return round(
            row['OVERALL'] * 2.25
            + row['OFFENSE'] * 0.82
            + row['DEFENSE'] * 0.82
            + row['Team Speed (90+ Speed Guys)'] * 2.1
            + row['Quad 90 (90+ SPD, ACC, AGI & COD)'] * 1.6
            + row['Generational (96+ speed or 96+ Acceleration)'] * 5.2
            + row['BCR_Val'] * 0.56
            + row['Recruit Score'] * 0.50
            + row['Improvement'] * 4.0
            + row['Career Win %'] * 0.60
            + row['SOS'] * 0.38
            + qb_cfp_bonus(row) * 0.95
            + row['CFP Wins'] * 1.2
            - row['CFP Losses'] * 1.2
            + coaching_cred
            + conf_bonus(row.get('CONFERENCE', 'Other')),
            1
        )

    df['Preseason PI'] = df.apply(preseason_power_index, axis=1)

    _pre_cfp_raw = (
        df['Preseason PI'] * 0.66
        + df['OVERALL'] * 1.35
        + df['Team Speed (90+ Speed Guys)'] * 1.95
        + df['Off Speed (90+ speed)'] * 0.75
        + df['Def Speed (90+ speed)'] * 0.75
        + df['Quad 90 (90+ SPD, ACC, AGI & COD)'] * 1.25
        + df['Generational (96+ speed or 96+ Acceleration)'] * 3.1
        + df['Recruit Score'] * 0.46
        + df['Career Win %'] * 0.18
        + df['SOS'] * 0.58
        + df.apply(qb_cfp_bonus, axis=1)
        + df['CONFERENCE'].apply(conf_bonus)
    )
    _pre_cfp_min = _pre_cfp_raw.min()
    _pre_cfp_spread = max(1, _pre_cfp_raw.max() - _pre_cfp_min)
    df['Preseason CFP %'] = (16 + ((_pre_cfp_raw - _pre_cfp_min) / _pre_cfp_spread * 66)).round(1)
    df['Preseason CFP %'] = df['Preseason CFP %'].clip(lower=12, upper=82)

    def power_index(row):
        # Coaching credibility: first 2 natties prove you can execute.
        # Beyond that your roster matters more than your trophy case. Hard cap at 2.
        _u_s_pi_rows = stats_df[stats_df['User'] == row['USER']]
        u_s_pi = _u_s_pi_rows.iloc[0] if not _u_s_pi_rows.empty else pd.Series({'Natties': 0})
        coaching_cred = min(int(u_s_pi.get('Natties', 0)), 2) * 2.5
        return round(
            row['OVERALL'] * 2.25
            + row['OFFENSE'] * 0.82
            + row['DEFENSE'] * 0.82
            + row['Team Speed (90+ Speed Guys)'] * 2.1
            + row['Quad 90 (90+ SPD, ACC, AGI & COD)'] * 1.6
            + row['Generational (96+ speed or 96+ Acceleration)'] * 5.2
            + row['BCR_Val'] * 0.56
            + row['Recruit Score'] * 0.50
            + row['Improvement'] * 4.0
            + row['Career Win %'] * 0.60
            + row['Current Win %'] * 0.50
            + row['SOS'] * 0.38
            + cfp_rank_bonus(row.get('Current CFP Ranking', np.nan)) * 0.86
            + qb_cfp_bonus(row) * 0.95
            + row['CFP Wins'] * 1.2
            - row['CFP Losses'] * 1.2
            + coaching_cred,
            1
        )

    df['Power Index'] = df.apply(power_index, axis=1)
    df['Team Speed Score'] = (
        df['Team Speed (90+ Speed Guys)'] * 2.2
        + df['Off Speed (90+ speed)'] * 1.0
        + df['Def Speed (90+ speed)'] * 1.0
        + df['Quad 90 (90+ SPD, ACC, AGI & COD)'] * 2.5
    ) * (1 + df['Generational (96+ speed or 96+ Acceleration)'] * 0.16
           + df['Quad 90 (90+ SPD, ACC, AGI & COD)'] * 0.07)
    df['Team Speed Score'] = df['Team Speed Score'].round(1)
    df['Speedometer'] = df['Team Speed Score'].apply(team_speed_to_mph)

    def where_is_the_speed(row):
        off_fast = row['Off Speed (90+ speed)'] > 5
        def_fast = row['Def Speed (90+ speed)'] > 5
        mph = pd.to_numeric(row.get('Speedometer', np.nan), errors='coerce')
        if (not off_fast) and (not def_fast) and (not pd.isna(mph)) and mph < 65:
            return 'Non-Existent'
        if off_fast and def_fast:
            return 'Off & Def'
        if off_fast:
            return 'Offense'
        if def_fast:
            return 'Defense'
        return 'Balanced'

    df['Where is the Speed?'] = df.apply(where_is_the_speed, axis=1)

    cfp_raw = (
        df['Power Index'] * 0.66
        + df['OVERALL'] * 1.35
        + df['Team Speed (90+ Speed Guys)'] * 1.95
        + df['Off Speed (90+ speed)'] * 0.75
        + df['Def Speed (90+ speed)'] * 0.75
        + df['Quad 90 (90+ SPD, ACC, AGI & COD)'] * 1.25
        + df['Generational (96+ speed or 96+ Acceleration)'] * 3.1
        + df['Recruit Score'] * 0.46
        + df['Career Win %'] * 0.18
        + df['Current Win %'] * 0.70
        + df['SOS'] * 0.58
        + df['Resume Score'] * 0.42
        + df['Current CFP Ranking'].apply(cfp_rank_bonus) * 1.95
        + df.apply(qb_cfp_bonus, axis=1)
        # Natties/NattyApps removed — consistent with Power Index & Natty Odds fix
    )
    cfp_min = cfp_raw.min()
    cfp_spread = max(1, cfp_raw.max() - cfp_min)
    df['CFP Odds'] = (16 + ((cfp_raw - cfp_min) / cfp_spread * 66)).round(0).astype(int)
    df['CFP Odds'] = df['CFP Odds'].clip(lower=12, upper=82)

    power_min = df['Power Index'].min()
    power_max = df['Power Index'].max()
    power_spread = max(1, power_max - power_min)
    df['Projected Wins'] = (6.2 + ((df['Power Index'] - power_min) / power_spread * 5.3)).round(1)
    df['Projected Wins'] = df['Projected Wins'].clip(lower=5.5, upper=11.5)

    df['Collapse Risk'] = (
        66
        - (df['OVERALL'] - 80) * 2.0
        - df['Improvement'] * 4.5
        - df['BCR_Val'] * 0.35
        - df['Recruit Score'] * 0.12
        - df['Generational (96+ speed or 96+ Acceleration)'] * 3.0
        - df['SOS'] * 0.18
        - df['Current Win %'] * 0.10
        - df['Current CFP Ranking'].apply(cfp_rank_bonus) * 0.25
        - df.apply(qb_cfp_bonus, axis=1) * 0.4
    ).round(0).astype(int)
    df['Collapse Risk'] = df['Collapse Risk'].clip(lower=8, upper=72)

    return df.sort_values(['Power Index', 'Natty Odds'], ascending=False).reset_index(drop=True)


def project_loss_scenarios(row):
    natty = float(pd.to_numeric(row.get('Natty Odds', 0), errors='coerce'))
    cfp = float(pd.to_numeric(row.get('CFP Odds', 0), errors='coerce'))
    overall = float(pd.to_numeric(row.get('OVERALL', 0), errors='coerce'))
    team_speed = float(pd.to_numeric(row.get('Team Speed (90+ Speed Guys)', 0), errors='coerce'))
    qb_tier = str(row.get('QB Tier', '')).strip()
    cfp_rank = row.get('Current CFP Ranking', np.nan)
    ranked_now = pd.notna(cfp_rank)

    base_unranked_natty_drop = 7.5
    base_ranked_natty_drop = 4.0
    base_unranked_cfp_drop = 16.0
    base_ranked_cfp_drop = 8.0

    if overall >= 90:
        base_unranked_natty_drop += 2.0
        base_unranked_cfp_drop += 2.5
    elif overall <= 84:
        base_ranked_natty_drop += 1.0
        base_ranked_cfp_drop += 2.0

    if team_speed >= 12:
        base_unranked_natty_drop += 1.5
        base_unranked_cfp_drop += 1.5

    if qb_tier == 'Elite':
        base_unranked_natty_drop += 1.8
        base_ranked_natty_drop += 0.8
        base_unranked_cfp_drop += 1.8
        base_ranked_cfp_drop += 0.8
    elif qb_tier == 'Leader':
        base_unranked_natty_drop += 1.0
        base_ranked_natty_drop += 0.4
        base_unranked_cfp_drop += 1.0
        base_ranked_cfp_drop += 0.4
    elif qb_tier == 'Ass':
        base_unranked_natty_drop -= 1.0
        base_ranked_natty_drop -= 0.5
        base_unranked_cfp_drop -= 1.5
        base_ranked_cfp_drop -= 1.0

    if ranked_now:
        base_unranked_natty_drop += 1.8
        base_unranked_cfp_drop += 3.0

    natty_unranked = max(0.1, round(natty - base_unranked_natty_drop, 1))
    natty_ranked = max(0.1, round(natty - base_ranked_natty_drop, 1))
    cfp_unranked = max(1, int(round(cfp - base_unranked_cfp_drop, 0)))
    cfp_ranked = max(1, int(round(cfp - base_ranked_cfp_drop, 0)))

    return pd.Series({
        'Natty if Lose to Unranked': natty_unranked,
        'Natty if Lose to Ranked': natty_ranked,
        'CFP if Lose to Unranked': cfp_unranked,
        'CFP if Lose to Ranked': cfp_ranked
    })


def get_team_schedule_summary(scores_df, user):
    user = str(user).strip().title()
    games = scores_df[(scores_df['V_User_Final'] == user) | (scores_df['H_User_Final'] == user)].copy()

    if games.empty:
        return 0, 0, 0.0, 0.0

    wins = len(games[
        ((games['V_User_Final'] == user) & (games['V_Pts'] > games['H_Pts'])) |
        ((games['H_User_Final'] == user) & (games['H_Pts'] > games['V_Pts']))
    ])
    losses = len(games) - wins

    points_for = np.where(games['V_User_Final'] == user, games['V_Pts'], games['H_Pts']).sum()
    points_against = np.where(games['V_User_Final'] == user, games['H_Pts'], games['V_Pts']).sum()
    avg_margin = round((points_for - points_against) / max(1, len(games)), 1)

    return wins, losses, round(points_for / max(1, len(games)), 1), avg_margin


def infer_best_fun_stat(y_data):
    if y_data.empty:
        return "No games found for that season."

    closest = y_data[y_data['Margin'] == y_data['Margin'].min()].iloc[0]
    highest_scoring = y_data[y_data['Total Points'] == y_data['Total Points'].max()].iloc[0]
    blowout = y_data[y_data['Margin'] == y_data['Margin'].max()].iloc[0]

    options = [
        f"Closest game: {closest['Visitor_Final']} vs {closest['Home_Final']} ended with just a {int(closest['Margin'])}-point margin.",
        f"Track meet alert: {highest_scoring['Visitor_Final']} vs {highest_scoring['Home_Final']} combined for {int(highest_scoring['Total Points'])} points.",
        f"Beatdown of the year: {blowout['Winner_Team']} handled business by {int(blowout['Margin'])}."
    ]

    avg_margin = y_data['Margin'].mean()
    if avg_margin <= 7:
        options.append("The whole season played like a knife fight. Average margin was under one score.")
    elif avg_margin >= 20:
        options.append("A lot of Saturdays turned into statements. Average margin cleared 20 points.")

    return options[len(y_data) % len(options)]


def tier_from_dynasty_score(score):
    if score >= 650:
        return "Blue Blood"
    if score >= 450:
        return "Contender"
    if score >= 250:
        return "Builder"
    return "Upstart"



def _recent_recruit_window(row, anchor_year=2041, lookback=4):
    year_cols = sorted([int(c) for c in row.index if str(c).isdigit()])
    vals = []
    for y in year_cols:
        if y <= anchor_year:
            v = clean_rank_value(row.get(str(y)))
            if not pd.isna(v):
                vals.append((y, float(v)))
    if not vals:
        return [], np.nan, 0.0
    vals = vals[-lookback:]
    ranks = [v for _, v in vals]
    weights = np.linspace(1, len(ranks), len(ranks))
    weighted_avg = float(np.average(ranks, weights=weights))
    trend = float(ranks[0] - ranks[-1]) if len(ranks) >= 2 else 0.0
    return vals, weighted_avg, trend


def _recruit_class_tier(weighted_rank, heat_index, bcr):
    if pd.isna(weighted_rank):
        return "No Read"
    if weighted_rank <= 5 or (heat_index >= 88 and bcr >= 55):
        return "Dynasty Class"
    if weighted_rank <= 12 or heat_index >= 80:
        return "Elite Haul"
    if weighted_rank <= 25 or heat_index >= 72:
        return "Strong Class"
    if weighted_rank <= 40 or heat_index >= 62:
        return "Solid Build"
    if weighted_rank <= 65:
        return "Mid Pack"
    return "Needs Bags"


def _recruit_trajectory(row):
    heat = float(row.get('Heat Index', 50))
    pipeline = float(row.get('Pipeline Score', 50))
    speed = float(row.get('Speed Recruiter Index', 50))
    bcr = float(row.get('Blue Chip %', 0))
    if heat >= 84 and pipeline >= 82 and bcr >= 55:
        return "Death Star Loading"
    if heat >= 78 and speed >= 75:
        return "Track Team With Bags"
    if pipeline >= 76:
        return "Roster Machine"
    if heat >= 70 and bcr < 40:
        return "Stars Without Bulk"
    if speed >= 72 and heat < 68:
        return "Speed Lab"
    if heat < 55 and pipeline < 58:
        return "Fraud Watch"
    return "On Schedule"


def _recruit_blurb(row):
    team = row['TEAM']
    tier = row['Class Tier']
    traj = row['Trajectory']
    heat = float(row['Heat Index'])
    bcr = float(row['Blue Chip %'])
    speed = float(row['Speed Recruiter Index'])
    if tier == 'Dynasty Class':
        return f"{team} is recruiting like somebody found the NIL nuke button. This class has full-on dynasty stink on it."
    if traj == 'Track Team With Bags':
        return f"{team} is signing speed freaks and doing it with zero shame. This is less roster building and more a felony footrace."
    if traj == 'Stars Without Bulk':
        return f"{team} keeps landing names, but the blue-chip body count still says somebody forgot the damn trench warfare."
    if traj == 'Fraud Watch':
        return f"{team} is recruiting like the fax machine, the group chat, and the head coach's judgment all failed at once."
    if heat >= 75 and bcr >= 50:
        return f"{team} is stacking a nasty little class. Not all glitz, but enough juice to make the future deeply annoying for everybody else."
    if speed >= 72:
        return f"{team} may not own the whole blue-chip galaxy, but they are absolutely recruiting like speed is a controlled substance."
    return f"{team} is putting together a respectable class. Nothing to start a parade over yet, but definitely not clown shoes either."


def build_recruiting_board(rec_df, model_df, anchor_year=2041):
    rows = []
    rec_local = rec_df.copy()
    rec_local['USER'] = rec_local['USER'].astype(str).str.strip().str.title()
    if 'Teams' in rec_local.columns:
        rec_local['Teams'] = rec_local['Teams'].astype(str).str.strip()

    for _, m in model_df.iterrows():
        user = str(m['USER']).strip().title()
        team = str(m['TEAM']).strip()
        match = rec_local[(rec_local['USER'] == user) & (rec_local['Teams'].astype(str).str.lower() == team.lower())]
        if match.empty:
            match = rec_local[rec_local['Teams'].astype(str).str.lower() == team.lower()]
        if match.empty:
            match = rec_local[rec_local['USER'] == user]
        rec_row = match.iloc[-1] if not match.empty else pd.Series(dtype=object)

        recent_vals, weighted_rank, trend = _recent_recruit_window(rec_row, anchor_year=anchor_year, lookback=4) if not match.empty else ([], np.nan, 0.0)
        recent_display = ' | '.join([f"{y}:{int(v)}" for y, v in recent_vals]) if recent_vals else 'No recent class data'
        heat = round(max(1.0, min(100.0, 101 - weighted_rank)), 1) if not pd.isna(weighted_rank) else 50.0
        blue = round(float(pd.to_numeric(m.get('BCR_Val', 0), errors='coerce') or 0.0), 1)
        pipeline = round(
            heat * 0.34
            + blue * 0.26
            + float(m.get('Team Speed Score', 0)) * 0.16
            + float(m.get('OVERALL', 0)) * 0.12
            + max(trend, 0) * 1.8
            + float(m.get('Generational (96+ speed or 96+ Acceleration)', 0)) * 2.8,
            1
        )
        speed_idx = round(
            heat * 0.22
            + float(m.get('Team Speed Score', 0)) * 0.34
            + float(m.get('Off Speed (90+ speed)', 0)) * 1.0
            + float(m.get('Def Speed (90+ speed)', 0)) * 1.0
            + float(m.get('Quad 90 (90+ SPD, ACC, AGI & COD)', 0)) * 2.0
            + float(m.get('Generational (96+ speed or 96+ Acceleration)', 0)) * 4.0,
            1
        )
        row = {
            'USER': user,
            'TEAM': team,
            'Logo': get_logo_source(team),
            'Recent Cycle': recent_display,
            'Weighted Avg Rank': round(weighted_rank, 1) if not pd.isna(weighted_rank) else np.nan,
            'Trend Score': round(trend, 1),
            'Heat Index': heat,
            'Blue Chip %': blue,
            'Pipeline Score': pipeline,
            'Speed Recruiter Index': speed_idx,
            'Current Recruiting Score': heat,
            'Current Blue Chip Ratio': round(blue / 100.0, 3),
        }
        row['Class Tier'] = _recruit_class_tier(row['Weighted Avg Rank'], heat, blue)
        row['Trajectory'] = _recruit_trajectory(row)
        row['Recruiting Blurb'] = _recruit_blurb(row)
        rows.append(row)

    out = pd.DataFrame(rows).sort_values(['Heat Index', 'Pipeline Score', 'Speed Recruiter Index'], ascending=False).reset_index(drop=True)
    if not out.empty:
        out['Rank'] = np.arange(1, len(out) + 1)
    return out


def render_recruiting_table(df):
    rows_html = []
    for _, row in df.iterrows():
        team = str(row.get('TEAM', ''))
        user = str(row.get('USER', ''))
        primary = get_team_primary_color(team)
        logo_path = get_logo_source(team)
        logo_uri = image_file_to_data_uri(logo_path)
        logo_html = f"<img src='{logo_uri}' style='width:38px;height:38px;object-fit:contain;'/>" if logo_uri else "<div style='font-size:22px;'>🏈</div>"
        cells = [f"""
        <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;white-space:nowrap;">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="font-weight:800;min-width:24px;text-align:center;">#{int(row.get('Rank', 0))}</div>
            <div style="width:40px;text-align:center;">{logo_html}</div>
            <div>
              <div style="font-weight:800;color:{primary};">{html.escape(team)}</div>
              <div style="font-size:12px;color:#cbd5e1;">{html.escape(user)}</div>
            </div>
          </div>
        </td>
        """]
        vals = [
            html.escape(str(row.get('Recent Cycle', '—'))),
            f"{float(row.get('Weighted Avg Rank', 0)):.1f}" if not pd.isna(row.get('Weighted Avg Rank', np.nan)) else '—',
            f"{float(row.get('Heat Index', 0)):.1f}",
            f"{float(row.get('Pipeline Score', 0)):.1f}",
            f"{float(row.get('Speed Recruiter Index', 0)):.1f}",
            f"{float(row.get('Blue Chip %', 0)):.1f}%",
            html.escape(str(row.get('Class Tier', '—'))),
            html.escape(str(row.get('Trajectory', '—'))),
            html.escape(str(row.get('Recruiting Blurb', '—'))),
        ]
        for disp in vals:
            cells.append(f"<td style='padding:10px 12px;border-bottom:1px solid #e5e7eb;text-align:center;white-space:nowrap;'>{disp}</td>")
        rows_html.append(f"<tr style='border-left:6px solid {primary};background:linear-gradient(90deg,{primary}12,transparent 14%);'>{''.join(cells)}</tr>")
    table_html = f"""
    <div style="overflow-x:auto;border:1px solid #e5e7eb;border-radius:14px;">
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead>
          <tr style="background:#f8fafc;color:#111827;">
            <th style="text-align:left;padding:10px 12px;color:#111827;font-weight:800;">Recruiting Board</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">Recent Classes</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">Weighted Avg Rank</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">Heat Index</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">Pipeline Score</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">Speed Recruiter</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">Blue Chip</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">Class Tier</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">Trajectory</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">Notes</th>
          </tr>
        </thead>
        <tbody>{''.join(rows_html)}</tbody>
      </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)


def format_ranked_team_name(team, rank_map):
    team = str(team).strip()
    rank = rank_map.get(team)
    return f"#{int(rank)} {team}" if rank is not None and not pd.isna(rank) else team


def estimate_game_line(team, opp, model_df, rank_map):
    model_local = model_df.copy()
    lookup = model_local.drop_duplicates('TEAM').set_index('TEAM')
    team_pi = float(lookup.loc[team]['Power Index']) if team in lookup.index else 200.0
    opp_pi = float(lookup.loc[opp]['Power Index']) if opp in lookup.index else 200.0
    team_rank = rank_map.get(team)
    opp_rank = rank_map.get(opp)
    team_rank_boost = max(0, 26 - float(team_rank)) * 0.85 if team_rank is not None and not pd.isna(team_rank) else 0.0
    opp_rank_boost = max(0, 26 - float(opp_rank)) * 0.85 if opp_rank is not None and not pd.isna(opp_rank) else 0.0
    diff = (team_pi + team_rank_boost) - (opp_pi + opp_rank_boost)
    line = round(abs(diff) / 6.8, 1)
    if abs(diff) < 2.5:
        return "Pick'em", None
    favored = team if diff > 0 else opp
    return f"{favored} -{line}", favored


def get_team_record_display(team, model_df, rankings_df):
    team = str(team).strip()
    rank_lookup = rankings_df.drop_duplicates('Team').set_index('Team') if rankings_df is not None and not rankings_df.empty else None
    if rank_lookup is not None and team in rank_lookup.index:
        row = rank_lookup.loc[team]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        return str(row.get('Record', '—'))
    model_lookup = model_df.drop_duplicates('TEAM').set_index('TEAM') if model_df is not None and not model_df.empty else None
    if model_lookup is not None and team in model_lookup.index:
        row = model_lookup.loc[team]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        w = pd.to_numeric(row.get('Current Record Wins', np.nan), errors='coerce')
        l = pd.to_numeric(row.get('Current Record Losses', np.nan), errors='coerce')
        if not pd.isna(w) and not pd.isna(l):
            return f"{int(w)}-{int(l)}"
    return '—'


def get_user_series_record(user_a, user_b, scores_df):
    ua = str(user_a).strip().title()
    ub = str(user_b).strip().title()
    if ua == ub or ub == 'Cpu' or ua == 'Cpu':
        return ''
    vs = scores_df[
        ((scores_df['V_User_Final'] == ua) & (scores_df['H_User_Final'] == ub)) |
        ((scores_df['V_User_Final'] == ub) & (scores_df['H_User_Final'] == ua))
    ].copy()
    if vs.empty:
        return f"Series: {ua} and {ub} haven't thrown punches yet."
    a_wins = len(vs[
        ((vs['V_User_Final'] == ua) & (vs['V_Pts'] > vs['H_Pts'])) |
        ((vs['H_User_Final'] == ua) & (vs['H_Pts'] > vs['V_Pts']))
    ])
    b_wins = len(vs) - a_wins
    if a_wins > b_wins:
        return f"Series: {ua} leads {a_wins}-{b_wins}."
    if b_wins > a_wins:
        return f"Series: {ub} leads {b_wins}-{a_wins}."
    return f"Series: tied {a_wins}-{b_wins}."



def get_current_user_games(model_df):
    """Week 12 slate pulled from the uploaded user schedule screenshots.
    The current week is the week after the last final score shown on each user schedule.
    OPP W-L is the opponent record shown on those screenshots.
    """
    weekly_games = [
        {'Week': CURRENT_WEEK_NUMBER, 'Team': 'Florida State', 'User': 'Doug', 'Opponent': 'LSU', 'Opponent User': 'CPU', 'Team Record': '9-1', 'OPP W-L': '4-5', 'Game Type': 'CPU Game'},
        {'Week': CURRENT_WEEK_NUMBER, 'Team': 'Florida', 'User': 'Michael', 'Opponent': 'Oklahoma State', 'Opponent User': 'CPU', 'Team Record': '9-2', 'OPP W-L': '6-4', 'Game Type': 'Completed Game', 'Result': 'W 43-31 vs Oklahoma State'},
        {'Week': CURRENT_WEEK_NUMBER, 'Team': 'Bowling Green', 'User': 'Chris', 'Opponent': 'South Carolina', 'Opponent User': 'CPU', 'Team Record': '9-0', 'OPP W-L': '2-7', 'Game Type': 'CPU Game'},
        {'Week': CURRENT_WEEK_NUMBER, 'Team': 'USF', 'User': 'Anthony', 'Opponent': 'Penn State', 'Opponent User': 'CPU', 'Team Record': '9-0', 'OPP W-L': '9-2', 'Game Type': 'CPU Game'},
        {'Week': CURRENT_WEEK_NUMBER, 'Team': 'Texas Tech', 'User': 'Bubba', 'Opponent': 'BYE', 'Opponent User': '', 'Team Record': '9-1', 'OPP W-L': '', 'Game Type': 'BYE'},
        {'Week': CURRENT_WEEK_NUMBER, 'Team': 'San Jose State', 'User': 'Michael', 'Opponent': 'Ohio State', 'Opponent User': 'CPU', 'Team Record': '9-1', 'OPP W-L': '6-3', 'Game Type': 'CPU Game'},
    ]
    team_to_user = {str(r['TEAM']).strip(): str(r['USER']).strip() for _, r in model_df[['TEAM','USER']].drop_duplicates().iterrows()}
    rows = []
    for g in weekly_games:
        row = dict(g)
        team = row['Team']
        if team in team_to_user:
            row['User'] = team_to_user[team]
        rows.append(row)
    return pd.DataFrame(rows)



def render_current_user_games_cards(games_df, model_df, scores_df):
    if games_df is None or games_df.empty:
        st.caption("No current user games loaded from the schedule screenshots yet.")
        return

    rankings_df = get_cfp_rankings_snapshot()
    rank_map = dict(rankings_df[['Team', 'Rank']].values)
    model_lookup = model_df.drop_duplicates('TEAM').set_index('TEAM') if model_df is not None and not model_df.empty else pd.DataFrame()

    def get_metric(team_name, col, fallback=0.0):
        if isinstance(model_lookup, pd.DataFrame) and not model_lookup.empty and team_name in model_lookup.index:
            try:
                return float(pd.to_numeric(model_lookup.loc[team_name].get(col, fallback), errors='coerce') or fallback)
            except Exception:
                return fallback
        return fallback

    def impact_badge(team_name, opp_name):
        score = get_metric(team_name, 'CFP Odds') + get_metric(team_name, 'Natty Odds')
        if opp_name and opp_name != 'BYE':
            opp_rank = rank_map.get(opp_name)
            if opp_rank is not None and not pd.isna(opp_rank):
                score += max(0, 26 - float(opp_rank)) * 1.35
            score += get_metric(opp_name, 'CFP Odds') * 0.18
        if score >= 75:
            return ('CFP IMPACT: HIGH', '#fecaca', '#7f1d1d')
        if score >= 42:
            return ('CFP IMPACT: MED', '#fde68a', '#78350f')
        return ('CFP IMPACT: LOW', '#d1fae5', '#065f46')

    def rivalry_meter_text(user_a, user_b):
        ua = str(user_a).strip().title()
        ub = str(user_b).strip().title()
        if not ua or not ub or ua.lower() == 'cpu' or ub.lower() == 'cpu' or ua == ub:
            return '', ''
        vs = scores_df[
            ((scores_df['V_User_Final'] == ua) & (scores_df['H_User_Final'] == ub)) |
            ((scores_df['V_User_Final'] == ub) & (scores_df['H_User_Final'] == ua))
        ].copy()
        if vs.empty:
            return 'RIVALRY METER', 'First meeting. Fresh beef.'
        games = len(vs)
        margins = pd.to_numeric(vs['Margin'], errors='coerce').dropna()
        avg_margin = float(margins.mean()) if not margins.empty else 14.0
        if games >= 6 and avg_margin <= 10:
            return 'RIVALRY METER: SPICY', f'{games} prior meetings. This one has real scar tissue.'
        if games >= 3:
            return 'RIVALRY METER: ACTIVE', f'{games} prior meetings. Enough history for both sides to talk shit.'
        return 'RIVALRY METER: WARM', f'{games} prior meetings. Not a blood feud yet, but it is getting there.'

    st.markdown("""
    <style>
    .dynasty-news-v2-card {
        border-radius: 18px;
        padding: 16px 18px;
        margin-bottom: 14px;
        background: linear-gradient(145deg, #111827 0%, #1f2937 100%);
        border: 1px solid #334155;
        box-shadow: 0 8px 20px rgba(0,0,0,0.22);
    }
    .dynasty-news-v2-chip {
        display:inline-block;
        padding:4px 10px;
        border-radius:999px;
        font-size:11px;
        font-weight:900;
        letter-spacing:.04em;
    }
    </style>
    """, unsafe_allow_html=True)

    for _, g in games_df.iterrows():
        team = str(g['Team']).strip()
        opp = str(g['Opponent']).strip()
        team_user = str(g.get('User', '')).strip()
        opp_user = str(g.get('Opponent User', '')).strip() or 'CPU'
        game_type = str(g.get('Game Type', 'Game'))

        team_primary = get_team_primary_color(team)
        team_secondary = get_team_secondary_color(team)
        opp_primary = get_team_primary_color(opp) if opp != 'BYE' else '#64748b'
        opp_secondary = get_team_secondary_color(opp) if opp != 'BYE' else '#e5e7eb'

        team_logo = image_file_to_data_uri(get_logo_source(team))
        opp_logo = image_file_to_data_uri(get_logo_source(opp)) if opp != 'BYE' else ''
        team_logo_html = f"<img src='{team_logo}' style='width:44px;height:44px;object-fit:contain;'/>" if team_logo else "🏈"
        opp_logo_html = f"<img src='{opp_logo}' style='width:44px;height:44px;object-fit:contain;'/>" if opp_logo else ("😴" if opp == 'BYE' else "🏈")

        team_label = format_ranked_team_name(team, rank_map)
        opp_label = format_ranked_team_name(opp, rank_map) if opp != 'BYE' else 'BYE'
        team_record = str(g.get('Team Record', '')).strip() or get_team_record_display(team, model_df, rankings_df)
        opp_record = str(g.get('OPP W-L', '')).strip() if opp != 'BYE' else '—'
        if opp != 'BYE' and not opp_record:
            opp_record = get_team_record_display(opp, model_df, rankings_df)

        favor_text = ''
        result_text = str(g.get('Result', '')).strip()
        if game_type == 'User Game':
            line_text, _favored = estimate_game_line(team, opp, model_df, rank_map)
            favor_text = line_text if line_text == "Pick'em" else f"Favored: {line_text}"

        series_text = ''
        rivalry_head = ''
        rivalry_text = ''
        if game_type == 'User Game':
            series_text = get_user_series_record(team_user, opp_user, scores_df)
            rivalry_head, rivalry_text = rivalry_meter_text(team_user, opp_user)
        elif game_type == 'BYE':
            rivalry_text = f"{team_user or team} gets a bye. Heal up, self-scout, and enjoy a stress-free Saturday for once."
        elif game_type == 'Completed Game':
            rivalry_text = result_text or f'Week {CURRENT_WEEK_NUMBER} final shown on the uploaded schedule screenshot.'
        else:
            rivalry_text = f"{team_user or team} has a CPU game this week. No fake drama here — just take care of business and don't do anything stupid."

        game_chip = 'BYE WEEK' if game_type == 'BYE' else ('FINAL' if game_type == 'Completed Game' else ('USER vs USER' if game_type == 'User Game' else 'USER vs CPU'))
        impact_label, impact_bg, impact_fg = impact_badge(team, opp)

        top_row_right = [
            f"<div class='dynasty-news-v2-chip' style='background:{impact_bg};color:{impact_fg};'>{html.escape(impact_label)}</div>"
        ]
        if favor_text:
            top_row_right.append(f"<div class='dynasty-news-v2-chip' style='background:#dbeafe;color:#1e3a8a;'>{html.escape(favor_text)}</div>")

        result_bar_html = ''
        if game_type == 'Completed Game' and result_text:
            win_loss = 'W' if result_text.strip().upper().startswith('W') else ('L' if result_text.strip().upper().startswith('L') else 'FINAL')
            result_color = '#166534' if win_loss == 'W' else ('#991b1b' if win_loss == 'L' else '#111827')
            result_bg = '#dcfce7' if win_loss == 'W' else ('#fee2e2' if win_loss == 'L' else '#e5e7eb')
            result_bar_html = f"<div style='margin-top:14px;padding:12px 14px;border-radius:14px;background:{result_bg};color:{result_color};font-size:14px;font-weight:900;text-align:center;border:1px solid rgba(255,255,255,.08);'>FINAL — {html.escape(result_text)}</div>"

        left_block = (
            f"<div style='display:flex;align-items:center;gap:12px;min-width:230px;'>"
            f"<div style='width:58px;height:58px;border-radius:14px;background:{team_primary}22;display:flex;align-items:center;justify-content:center;border:2px solid {team_primary};box-shadow:0 0 0 1px rgba(255,255,255,.05) inset;'>{team_logo_html}</div>"
            f"<div>"
            f"<div style='font-size:12px;color:#9ca3af;font-weight:700;'>{html.escape(team_user)}</div>"
            f"<div style='font-size:19px;font-weight:900;color:{team_secondary if team_secondary != '#FFFFFF' else '#f8fafc'};'>{html.escape(team_label)}</div>"
            f"<div style='font-size:12px;color:#cbd5e1;'>Record: {html.escape(team_record)}</div>"
            f"</div>"
            f"</div>"
        )

        if opp == 'BYE':
            right_block = (
                f"<div style='display:flex;align-items:center;gap:12px;min-width:230px;justify-content:flex-end;'>"
                f"<div>"
                f"<div style='font-size:12px;color:#9ca3af;text-align:right;font-weight:700;'>Open date</div>"
                f"<div style='font-size:19px;font-weight:900;color:#f8fafc;text-align:right;'>BYE</div>"
                f"<div style='font-size:12px;color:#cbd5e1;text-align:right;'>Record: —</div>"
                f"</div>"
                f"<div style='width:58px;height:58px;border-radius:14px;background:{opp_primary}22;display:flex;align-items:center;justify-content:center;border:2px solid {opp_primary};'>{opp_logo_html}</div>"
                f"</div>"
            )
        else:
            right_block = (
                f"<div style='display:flex;align-items:center;gap:12px;min-width:230px;justify-content:flex-end;'>"
                f"<div>"
                f"<div style='font-size:12px;color:#9ca3af;text-align:right;font-weight:700;'>{html.escape(opp_user)}</div>"
                f"<div style='font-size:19px;font-weight:900;color:{opp_secondary if opp_secondary != '#FFFFFF' else '#f8fafc'};text-align:right;'>{html.escape(opp_label)}</div>"
                f"<div style='font-size:12px;color:#cbd5e1;text-align:right;'>Record: {html.escape(opp_record)}</div>"
                f"</div>"
                f"<div style='width:58px;height:58px;border-radius:14px;background:{opp_primary}22;display:flex;align-items:center;justify-content:center;border:2px solid {opp_primary};'>{opp_logo_html}</div>"
                f"</div>"
            )

        lower_notes = []
        if series_text:
            lower_notes.append(f"<div style='font-size:12px;color:#e2e8f0;font-weight:800;'>{html.escape(series_text)}</div>")
        if rivalry_head or rivalry_text:
            lower_notes.append(
                f"<div style='margin-top:8px;padding:10px 12px;border-radius:12px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.06);'>"
                f"<div style='font-size:11px;font-weight:900;letter-spacing:.05em;color:#94a3b8;'>{html.escape(rivalry_head or 'WEEKLY READ')}</div>"
                f"<div style='font-size:13px;color:#f8fafc;font-weight:700;margin-top:4px;'>{html.escape(rivalry_text)}</div>"
                f"</div>"
            )

        card_html = (
            f"<div class='dynasty-news-v2-card' style='border-left:6px solid {team_primary};'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px;'>"
            f"<div class='dynasty-news-v2-chip' style='background:rgba(255,255,255,0.08);color:#e5e7eb;'>{html.escape(game_chip)}</div>"
            f"<div style='display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end;'>{''.join(top_row_right)}</div>"
            f"</div>"
            f"<div style='display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;'>"
            f"{left_block}"
            f"<div style='font-size:17px;font-weight:900;color:#94a3b8;letter-spacing:.08em;'>" + ('VS' if opp != 'BYE' else '—') + "</div>"
            f"{right_block}"
            f"</div>"
            f"{result_bar_html}"
            f"{''.join(lower_notes)}"
            f"</div>"
        )
        st.markdown(card_html, unsafe_allow_html=True)


def get_current_recruiting_snapshot():
    rows = [
        {'Rank': 1, 'Team': 'Nebraska', 'Total': 18, '5★': 3, '4★': 15, '3★': 0, 'Points': 239.05},
        {'Rank': 2, 'Team': 'Georgia', 'Total': 16, '5★': 2, '4★': 14, '3★': 0, 'Points': 226.55},
        {'Rank': 3, 'Team': 'USC', 'Total': 13, '5★': 3, '4★': 9, '3★': 1, 'Points': 211.40},
        {'Rank': 4, 'Team': 'Miami', 'Total': 15, '5★': 0, '4★': 11, '3★': 4, 'Points': 203.95},
        {'Rank': 5, 'Team': 'Bowling Green', 'Total': 11, '5★': 4, '4★': 6, '3★': 1, 'Points': 197.90},
        {'Rank': 6, 'Team': 'Texas A&M', 'Total': 15, '5★': 1, '4★': 11, '3★': 3, 'Points': 190.75},
        {'Rank': 7, 'Team': 'Texas', 'Total': 15, '5★': 1, '4★': 9, '3★': 5, 'Points': 190.00},
        {'Rank': 8, 'Team': 'Ohio State', 'Total': 16, '5★': 0, '4★': 11, '3★': 5, 'Points': 184.15},
        {'Rank': 9, 'Team': 'Florida State', 'Total': 13, '5★': 1, '4★': 8, '3★': 4, 'Points': 175.70},
        {'Rank': 10, 'Team': 'Rapid City', 'Total': 14, '5★': 0, '4★': 10, '3★': 4, 'Points': 171.75},
        {'Rank': 11, 'Team': 'Notre Dame', 'Total': 13, '5★': 1, '4★': 7, '3★': 5, 'Points': 168.75},
        {'Rank': 12, 'Team': 'Alabama', 'Total': 16, '5★': 0, '4★': 8, '3★': 8, 'Points': 166.55},
        {'Rank': 13, 'Team': 'Tennessee', 'Total': 15, '5★': 0, '4★': 9, '3★': 6, 'Points': 151.80},
        {'Rank': 14, 'Team': 'San Jose State', 'Total': 9, '5★': 0, '4★': 6, '3★': 3, 'Points': 146.95},
        {'Rank': 15, 'Team': 'USF', 'Total': 11, '5★': 0, '4★': 6, '3★': 5, 'Points': 139.85},
        {'Rank': 16, 'Team': 'Oregon', 'Total': 14, '5★': 0, '4★': 6, '3★': 8, 'Points': 138.75},
        {'Rank': 17, 'Team': 'Clemson', 'Total': 10, '5★': 0, '4★': 7, '3★': 3, 'Points': 137.55},
        {'Rank': 18, 'Team': 'Texas Tech', 'Total': 11, '5★': 0, '4★': 6, '3★': 5, 'Points': 136.80},
        {'Rank': 19, 'Team': 'Georgia Tech', 'Total': 12, '5★': 0, '4★': 7, '3★': 5, 'Points': 134.90},
        {'Rank': 20, 'Team': 'Penn State', 'Total': 12, '5★': 0, '4★': 7, '3★': 5, 'Points': 133.35},
        {'Rank': 21, 'Team': 'LSU', 'Total': 13, '5★': 0, '4★': 6, '3★': 7, 'Points': 132.55},
        {'Rank': 22, 'Team': 'Oklahoma', 'Total': 12, '5★': 0, '4★': 6, '3★': 6, 'Points': 130.80},
        {'Rank': 23, 'Team': 'Michigan', 'Total': 14, '5★': 0, '4★': 6, '3★': 8, 'Points': 129.55},
        {'Rank': 24, 'Team': 'Florida', 'Total': 10, '5★': 0, '4★': 5, '3★': 5, 'Points': 127.10},
        {'Rank': 25, 'Team': 'Hammond', 'Total': 11, '5★': 0, '4★': 5, '3★': 6, 'Points': 125.65},
    ]
    df = pd.DataFrame(rows)
    df['Blue Chip Ratio'] = ((df['5★'] + df['4★']) / df['Total']).round(3)
    df['Logo'] = df['Team'].apply(get_logo_source)
    return df


def get_cfp_rankings_snapshot():
    """
    Always pulls from cfp_rankings_history.csv using the most recent YEAR+WEEK.
    Falls back to hardcoded Week 9 data only if the file is missing or empty.
    Update cfp_rankings_history.csv each week and this auto-updates everywhere:
    Who's In?, Power Rankings, Toughest Matchups, game line estimates, etc.
    """
    try:
        hist = pd.read_csv('cfp_rankings_history.csv')
        if not hist.empty and 'YEAR' in hist.columns and 'WEEK' in hist.columns:
            latest_year = hist['YEAR'].max()
            latest_week = hist.loc[hist['YEAR'] == latest_year, 'WEEK'].max()
            snap = hist[(hist['YEAR'] == latest_year) & (hist['WEEK'] == latest_week)].copy()
            if not snap.empty:
                snap = snap.rename(columns={'RANK': 'Rank', 'TEAM': 'Team', 'RECORD': 'Record'})
                snap['Rank'] = pd.to_numeric(snap['Rank'], errors='coerce')
                snap = snap.dropna(subset=['Rank']).sort_values('Rank').reset_index(drop=True)
                # Parse wins/losses from Record column (e.g. "9-1")
                def parse_wl(rec):
                    try:
                        parts = str(rec).split('-')
                        return int(parts[0]), int(parts[1])
                    except Exception:
                        return 0, 0
                snap['Wins']   = snap['Record'].apply(lambda r: parse_wl(r)[0])
                snap['Losses'] = snap['Record'].apply(lambda r: parse_wl(r)[1])
                snap['Logo']   = snap['Team'].apply(get_logo_source)
                return snap[['Rank', 'Team', 'Wins', 'Losses', 'Record', 'Logo']]
    except Exception:
        pass

    # ── FALLBACK: hardcoded Week 9 snapshot (used only if CSV missing) ────
    data = [
        (1, "Bowling Green", 9, 0),
        (2, "San Jose State", 9, 1),
        (3, "USF", 9, 0),
        (4, "Florida State", 9, 1),
        (5, "Rapid City", 9, 1),
        (6, "Texas", 9, 1),
        (7, "Texas Tech", 9, 1),
        (8, "Georgia", 8, 1),
        (9, "Miami", 8, 1),
        (10, "Alabaster", 7, 2),
        (11, "Nebraska", 7, 2),
        (12, "Oklahoma", 7, 2),
        (13, "Georgia Tech", 8, 1),
        (14, "Hammond", 8, 2),
        (15, "Texas A&M", 7, 2),
        (16, "Penn State", 9, 2),
        (17, "Clemson", 8, 1),
        (18, "NC State", 8, 1),
        (19, "Oregon", 6, 3),
        (20, "San Diego State", 9, 1),
        (21, "Florida", 9, 2),
        (22, "Ohio State", 6, 3),
        (23, "Notre Dame", 7, 3),
        (24, "Panama City", 7, 3),
        (25, "Appalachian State", 8, 1),
    ]
    df = pd.DataFrame(data, columns=['Rank', 'Team', 'Wins', 'Losses'])
    df['Record'] = df['Wins'].astype(str) + '-' + df['Losses'].astype(str)
    df['Logo'] = df['Team'].apply(get_logo_source)
    return df


def _normalize_team_match_key(team):
    return normalize_key(str(team).replace('&', 'and'))


def build_cfp_bubble_board(rankings_df, model_df):
    """
    Late-season CFP bubble model.

    Key design decisions:
    - Rank position is the dominant signal (committee already voted)
    - Remaining schedule pulled live from CPUscores_MASTER.csv for real SOS delta
    - Non-linear rank curves: steep penalty 11-16, moderate 17-25
    - Top 4 bye locks at 96%+, top 12 CFP locks at 95%+
    - Loss penalty is sharp: each loss beyond 1 is a cliff, not a slope
    - Caps removed at the top so true separation shows
    """
    df = rankings_df.copy()
    model_local = model_df.copy()
    model_local['_team_key'] = model_local['TEAM'].apply(_normalize_team_match_key)
    model_lookup = model_local.drop_duplicates('_team_key').set_index('_team_key')

    defaults = {
        'Current CFP Ranking': np.nan,
        'CFP Odds': 42.0,
        'Natty Odds': 3.0,
        'Power Index': 215.0,
        'SOS': 55.0,
        'Resume Score': 58.0,
        'QB Tier': 'Unknown',
        'Program Stock': '➖ Stable',
        'OVERALL': 86.0,
        'Team Speed Score': 50.0,
        'BCR_Val': 35.0,
        'Recruit Score': 50.0,
    }

    enrich_cols = list(defaults.keys())
    for col in enrich_cols:
        vals = []
        for team in df['Team']:
            key = _normalize_team_match_key(team)
            if key in model_lookup.index:
                vals.append(model_lookup.loc[key][col] if col in model_lookup.columns else defaults[col])
            else:
                vals.append(defaults[col])
        df[col] = vals

    df['Games Played'] = df['Wins'] + df['Losses']
    df['Remaining Games'] = (13 - df['Games Played']).clip(lower=0)
    df['Win %'] = (df['Wins'] / (df['Wins'] + df['Losses'])).round(3)

    # ── REMAINING SOS from CPUscores_MASTER ────────────────────────────────
    # Pull live scheduled games and score each team's remaining opponent quality
    try:
        cpu_sched = pd.read_csv('CPUscores_MASTER.csv')
        cpu_sched = cpu_sched[cpu_sched['Status'].str.upper() == 'SCHEDULED'].copy()
        rank_lookup = dict(zip(df['Team'], df['Rank']))

        def remaining_sos_delta(team):
            """
            Returns a modifier ranging roughly -6 to +6 based on remaining opponents.
            Playing a top-5 ranked team: +4 to +6 (win would be huge, loss survivable if already in)
            Playing unranked: +0 (neutral for locks, slight help if bubble)
            """
            games = cpu_sched[
                (cpu_sched['Visitor'] == team) | (cpu_sched['Home'] == team)
            ]
            if games.empty:
                return 0.0
            total_delta = 0.0
            for _, g in games.iterrows():
                opp = g['Visitor'] if g['Home'] == team else g['Home']
                opp_rank = rank_lookup.get(opp, None)
                if opp_rank is not None:
                    # Top 5 opponent = huge deal; ranked but lower = moderate
                    if opp_rank <= 5:
                        total_delta += 5.5
                    elif opp_rank <= 12:
                        total_delta += 3.0
                    elif opp_rank <= 25:
                        total_delta += 1.2
                # Unranked opponent = no bonus (expected win)
            return round(total_delta, 1)

        df['Remaining SOS Delta'] = df['Team'].apply(remaining_sos_delta)
    except Exception:
        df['Remaining SOS Delta'] = 0.0

    # ── RANK SCORE: non-linear, steep around bubble (8-16) ─────────────────
    # Rank 1 = 100, Rank 4 = 91, Rank 8 = 79, Rank 12 = 60, Rank 13 = 45, Rank 16 = 28, Rank 25 = 5
    def rank_score(r):
        r = float(r)
        if r <= 4:
            return 100 - (r - 1) * 3.0          # 100 → 91
        elif r <= 8:
            return 91 - (r - 4) * 3.0           # 91 → 79
        elif r <= 12:
            return 79 - (r - 8) * 4.75          # 79 → 60
        elif r <= 16:
            return 60 - (r - 12) * 8.0          # 60 → 28 (cliff)
        elif r <= 20:
            return 28 - (r - 16) * 4.5          # 28 → 10
        else:
            return max(2, 10 - (r - 20) * 1.0)  # 10 → 5

    df['Rank Score'] = df['Rank'].apply(rank_score)

    # ── LOSS PENALTY: cliff at 2 losses, brutal at 3+ ──────────────────────
    df['Loss Penalty'] = np.select(
        [df['Losses'] == 0, df['Losses'] == 1, df['Losses'] == 2, df['Losses'] == 3],
        [0.0,              0.0,               4.0,               14.0],
        default=28.0
    )

    # ── QB MODIFIER ─────────────────────────────────────────────────────────
    qbm = {'Elite': 6.0, 'Leader': 3.0, 'Average Joe': -1.5, 'Ass': -6.0, 'Unknown': 0.0}
    df['QB Mod'] = df['QB Tier'].map(qbm).fillna(0.0)

    # ── ROSTER QUALITY ───────────────────────────────────────────────────────
    df['Overall CFP Mod'] = np.select(
        [df['OVERALL'] <= 80, df['OVERALL'] <= 82, df['OVERALL'] <= 84],
        [-10.0, -6.0, -3.0],
        default=0.0
    )

    # ── COMBINED RAW SCORE ───────────────────────────────────────────────────
    # Rank Score is dominant (55%), everything else sharpens the edges
    df['CFP Raw'] = (
        df['Rank Score'] * 0.55
        + df['Win %'] * 100 * 0.10
        + df['SOS'] * 0.06
        + df['Resume Score'] * 0.06
        + df['Power Index'].clip(lower=160, upper=360).sub(160).div(2.2) * 0.04
        + df['OVERALL'] * 0.04
        + df['QB Mod']
        + df['Overall CFP Mod']
        + df['Remaining SOS Delta']
        - df['Loss Penalty']
    )

    # ── CFP MAKE % ───────────────────────────────────────────────────────────
    # Sigmoid tuned so rank-1 = ~97%, rank-12 = ~80%, rank-13 = ~45%, rank-25 = ~5%
    # Sigmoid center 42 so rank-12 w/ 1 loss lands ~55%, rank-1 w/ 0 losses ~97%
    df['CFP Make %'] = (1 / (1 + np.exp(-(df['CFP Raw'] - 42) / 5.5)) * 100).round(1)
    df['CFP Make %'] = df['CFP Make %'].clip(lower=0.5, upper=99.0)

    # ── AUTO-BID PATH ────────────────────────────────────────────────────────
    auto_bid_raw = (
        df['Rank Score'] * 0.60
        + df['Win %'] * 100 * 0.18
        + df['SOS'] * 0.06
        + df['QB Mod'] * 0.4
        - df['Loss Penalty'] * 0.6
    )
    df['Auto-Bid %'] = (1 / (1 + np.exp(-(auto_bid_raw - 50) / 6.0)) * 100).round(1)
    df['Auto-Bid %'] = df['Auto-Bid %'].clip(lower=0.5, upper=98.0)

    # ── BYE % (top 4 seeds) ──────────────────────────────────────────────────
    # Bye is purely a top-4 thing. Rank 1-4 = 88-97%, rank 5+ drops sharply.
    bye_raw = (
        df['Rank Score'] * 0.70
        + df['Win %'] * 100 * 0.12
        + df['QB Mod'] * 0.5
        - df['Loss Penalty'] * 0.5
        - df['Rank'] * 1.8   # extra rank pressure for seed specifically
    )
    df['Bye %'] = (1 / (1 + np.exp(-(bye_raw - 48) / 5.5)) * 100).round(1)
    df['Bye %'] = np.where(df['Rank'] > 8,  df['Bye %'] * 0.25, df['Bye %'])
    df['Bye %'] = np.where(df['Rank'] > 12, df['Bye %'] * 0.10, df['Bye %'])
    df['Bye %'] = df['Bye %'].clip(lower=0.1, upper=98.0).round(1)

    # ── BUBBLE TIER ─────────────────────────────────────────────────────────
    def bubble_tier(row):
        pct = row['CFP Make %']
        if pct >= 90: return '🔒 Lock'
        if pct >= 72: return '✅ In Control'
        if pct >= 42: return '⚠️ Bubble'
        if pct >= 18: return '🔥 Need Chaos'
        return '🪦 Practically Dead'

    df['Bubble Tier'] = df.apply(bubble_tier, axis=1)
    df['Committee Score'] = df['Rank Score']   # keep column name for downstream
    df['Projected Seed'] = np.nan
    return df.sort_values(['CFP Make %', 'Bye %', 'Rank'], ascending=[False, False, True]).reset_index(drop=True)


def compute_projected_seed_score(board_df):
    df = board_df.copy()
    df['Seed Score'] = (
        df['Committee Score'] * 0.36
        + (df['Win %'] * 100) * 0.18
        + df['Resume Score'] * 0.16
        + df['SOS'] * 0.12
        + df['Power Index'].clip(lower=160, upper=360).sub(160).div(2.15) * 0.08
        + df['Bye %'] * 0.04
        + df['Auto-Bid %'] * 0.03
        + df['QB Mod'] * 0.55
        + np.where(df['OVERALL'] >= 90, 2.5, 0.0)
        - np.where(df['OVERALL'] <= 84, (85 - df['OVERALL']) * 1.4, 0.0)
    )
    return df






def build_bracket_field_from_screenshot(parsed_teams, cfp_board):
    """
    Converts parsed screenshot teams into a projected_field-style DataFrame
    that render_playoff_bracket can consume directly.
    Merges with cfp_board to pull CFP Make %, Bye %, Auto-Bid %, etc.
    """
    if not parsed_teams:
        return None
    rows = []
    board_lookup = cfp_board.set_index('Team') if not cfp_board.empty else pd.DataFrame()
    for t in parsed_teams:
        seed = t['seed']
        team = t['team']
        record = t.get('record', '')
        wins = losses = 0
        try:
            parts = record.split('-')
            wins, losses = int(parts[0]), int(parts[1])
        except Exception:
            pass

        # Pull enriched data from cfp_board if team matches
        row = {'Team': team, 'Record': record, 'Wins': wins, 'Losses': losses,
               'Projected Seed': seed, 'Rank': seed,
               'CFP Make %': 95.0, 'Bye %': (90.0 if seed <= 4 else 5.0),
               'Auto-Bid %': 80.0, 'Committee Score': max(0, 100 - seed*6),
               'Win %': wins/(wins+losses) if (wins+losses) > 0 else 0.5}

        # Try fuzzy match to cfp_board for richer data
        if not board_lookup.empty:
            for board_team in board_lookup.index:
                if (normalize_key(team) == normalize_key(board_team) or
                    normalize_key(team) in normalize_key(board_team) or
                    normalize_key(board_team) in normalize_key(team)):
                    br = board_lookup.loc[board_team]
                    for col in ['CFP Make %','Bye %','Auto-Bid %','Committee Score',
                                'Rank','QB Tier','SOS','Power Index','OVERALL']:
                        if col in br.index:
                            row[col] = br[col]
                    break
        rows.append(row)

    return pd.DataFrame(rows).sort_values('Projected Seed').reset_index(drop=True)


def render_playoff_bracket(projected_field):
    """Visual SVG bracket for 12-team CFP playoff with connector lines."""
    if projected_field is None or projected_field.empty or len(projected_field) < 12:
        st.info("Need 12 projected teams to render the bracket.")
        return

    pf = projected_field.copy()
    pf['Projected Seed'] = pd.to_numeric(pf['Projected Seed'], errors='coerce')
    pf = pf.dropna(subset=['Projected Seed']).sort_values('Projected Seed').reset_index(drop=True)

    def get_row(seed):
        rows = pf[pf['Projected Seed'] == seed]
        return rows.iloc[0] if not rows.empty else None

    def wp(sa, sb):
        diff = max(-8, min(8, sb - sa))
        return round(max(18, min(82, 50 + diff * 4.5)))

    SW, SH, GAP = 188, 44, 8
    R1X, QFX, SFX, NX = 8, 238, 468, 698
    NW = 220
    W, H = 938, 692

    Q1C, Q2C, Q3C, Q4C = 87, 260, 433, 606
    SF1C = (Q1C + Q2C) // 2
    SF2C = (Q3C + Q4C) // 2
    NC = H // 2

    def ya_yb(c):
        y = c - SH - GAP // 2 - SH // 2
        return y, y + SH + GAP

    def sc(y): return y + SH // 2
    def mc(ya, yb): return (sc(ya) + sc(yb)) // 2

    M1 = (R1X + SW + QFX) // 2
    M2 = (QFX + SW + SFX) // 2
    M3 = (SFX + SW + NX) // 2

    r1g1 = ya_yb(Q1C); r1g4 = ya_yb(Q2C)
    r1g2 = ya_yb(Q3C); r1g3 = ya_yb(Q4C)
    qf1  = ya_yb(Q1C); qf4  = ya_yb(Q2C)
    qf2  = ya_yb(Q3C); qf3  = ya_yb(Q4C)
    sf1  = ya_yb(SF1C); sf2 = ya_yb(SF2C)
    nat  = ya_yb(NC)

    LC = "#2d4060"; GC = "#fbbf24"

    def pth(pts, color=None):
        c = color or LC
        d = "M{},{}".format(pts[0][0], pts[0][1])
        for i in range(1, len(pts)):
            px, py = pts[i-1]; cx, cy = pts[i]
            d += " H{}".format(cx) if py == cy else (" V{}".format(cy) if px == cx else " H{} V{}".format(cx, cy))
        return '<path d="{}" stroke="{}" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'.format(d, c)

    re = R1X + SW; qe = QFX + SW; se = SFX + SW
    P = [
        pth([(re, mc(*r1g1)), (M1, mc(*r1g1)), (M1, sc(qf1[1])), (QFX, sc(qf1[1]))]),
        pth([(re, mc(*r1g4)), (M1, mc(*r1g4)), (M1, sc(qf4[1])), (QFX, sc(qf4[1]))]),
        pth([(re, mc(*r1g2)), (M1, mc(*r1g2)), (M1, sc(qf2[1])), (QFX, sc(qf2[1]))]),
        pth([(re, mc(*r1g3)), (M1, mc(*r1g3)), (M1, sc(qf3[1])), (QFX, sc(qf3[1]))]),
        pth([(qe, mc(*qf1)), (M2, mc(*qf1)), (M2, sc(sf1[0])), (SFX, sc(sf1[0]))]),
        pth([(qe, mc(*qf4)), (M2, mc(*qf4)), (M2, sc(sf1[1])), (SFX, sc(sf1[1]))]),
        pth([(qe, mc(*qf2)), (M2, mc(*qf2)), (M2, sc(sf2[0])), (SFX, sc(sf2[0]))]),
        pth([(qe, mc(*qf3)), (M2, mc(*qf3)), (M2, sc(sf2[1])), (SFX, sc(sf2[1]))]),
        pth([(se, mc(*sf1)), (M3, mc(*sf1)), (M3, sc(nat[0])), (NX, sc(nat[0]))], GC),
        pth([(se, mc(*sf2)), (M3, mc(*sf2)), (M3, sc(nat[1])), (NX, sc(nat[1]))], GC),
    ]
    conn_svg = "\n".join(P)

    def slot_svg(x, y, seed, row, bye=False, proj=False, tbd_lines=None, w=SW):
        if tbd_lines:
            l1, l2 = tbd_lines
            return (
                '<rect x="{}" y="{}" width="{}" height="{}" rx="6" fill="#0d1829" stroke="#1e3a5f" stroke-width="1"/>'.format(x, y, w, SH) +
                '<text x="{}" y="{}" text-anchor="middle" fill="#374151" font-size="10" font-family="monospace">{}</text>'.format(x+w//2, y+17, html.escape(l1)) +
                '<text x="{}" y="{}" text-anchor="middle" fill="#1e3a5f" font-size="10" font-family="monospace">{}</text>'.format(x+w//2, y+32, html.escape(l2))
            )
        if row is None: return ""
        team    = str(row.get("Team", ""))
        record  = str(row.get("Record", ""))
        primary = get_team_primary_color(team)
        logo_uri = image_file_to_data_uri(get_logo_source(team))
        name = (team[:19] + "\u2026") if len(team) > 19 else team
        fill_op = "12" if proj else "1c"
        opacity = "99" if proj else "ff"
        clip_id = "lc{}".format(abs(hash(team + str(y))) % 99999)
        logo_svg = ""; name_x = x + 42
        if logo_uri:
            logo_svg = (
                '<defs><clipPath id="{0}"><rect x="{1}" y="{2}" width="28" height="28" rx="4"/></clipPath></defs>'.format(clip_id, x+35, y+8) +
                '<image href="{}" x="{}" y="{}" width="28" height="28" clip-path="url(#{})" opacity="0.9"/>'.format(logo_uri, x+35, y+8, clip_id)
            )
            name_x = x + 70
        bye_svg = ""
        if bye:
            bye_svg = (
                '<rect x="{}" y="{}" width="36" height="15" rx="7" fill="#14532d"/>'.format(x+w-44, y+14) +
                '<text x="{}" y="{}" text-anchor="middle" fill="#4ade80" font-size="9" font-weight="bold" font-family="monospace">BYE</text>'.format(x+w-26, y+25)
            )
        proj_svg = ""
        if proj:
            proj_svg = (
                '<rect x="{}" y="{}" width="43" height="15" rx="7" fill="#1e3a5f"/>'.format(x+w-50, y+14) +
                '<text x="{}" y="{}" text-anchor="middle" fill="#60a5fa" font-size="8" font-weight="bold" font-family="monospace">PROJ</text>'.format(x+w-28, y+25)
            )
        return (
            '<rect x="{}" y="{}" width="{}" height="{}" rx="6" fill="{}{}" stroke="{}55" stroke-width="1"/>'.format(x, y, w, SH, primary, fill_op, primary) +
            '<rect x="{}" y="{}" width="4" height="{}" rx="3" fill="{}{}"/>'.format(x, y, SH, primary, opacity) +
            '<circle cx="{}" cy="{}" r="13" fill="{}{}"/>'.format(x+20, y+SH//2, primary, opacity) +
            '<text x="{}" y="{}" text-anchor="middle" fill="white" font-size="11" font-weight="bold" font-family="monospace">#{}</text>'.format(x+20, y+SH//2+5, seed) +
            logo_svg +
            '<text x="{}" y="{}" fill="{}" font-size="12" font-weight="bold" font-family="monospace">{}</text>'.format(name_x, y+18, primary, html.escape(name)) +
            '<text x="{}" y="{}" fill="#6b7280" font-size="10" font-family="monospace">{}</text>'.format(name_x, y+34, html.escape(record)) +
            bye_svg + proj_svg
        )

    def wplabel(sa, sb, ya, yb, x, w=SW):
        p = wp(sa, sb); my = mc(ya, yb)
        return (
            '<rect x="{}" y="{}" width="{}" height="18" rx="5" fill="#060e1a"/>'.format(x+22, my-9, w-44) +
            '<text x="{}" y="{}" text-anchor="middle" fill="#475569" font-size="9.5" font-family="monospace">#{}: {}%  ·  #{}: {}%</text>'.format(x+w//2, my+4, sa, p, sb, 100-p)
        )

    def rlbl(x, w, txt, color="#334155"):
        return '<text x="{}" y="18" text-anchor="middle" fill="{}" font-size="9" font-weight="bold" letter-spacing="1.5" font-family="monospace">{}</text>'.format(x+w//2, color, txt)

    hdr = rlbl(R1X,SW,"FIRST ROUND") + rlbl(QFX,SW,"QUARTERFINALS") + rlbl(SFX,SW,"SEMIFINALS") + rlbl(NX,NW,"NATIONAL CHAMPIONSHIP",GC)

    def track(x, w):
        return '<rect x="{}" y="26" width="{}" height="{}" rx="8" fill="#0a1628" stroke="#111f33" stroke-width="1"/>'.format(x, w, H-36)

    tracks = track(R1X,SW) + track(QFX,SW) + track(SFX,SW) + track(NX,NW)

    rows = {s: get_row(s) for s in range(1, 13)}
    wp1=wp(8,9); wp4=wp(5,12); wp2=wp(7,10); wp3=wp(6,11)
    qf1_opp = 8 if wp1>50 else 9
    qf4_opp = 5 if wp4>50 else 12
    qf2_opp = 7 if wp2>50 else 10
    qf3_opp = 6 if wp3>50 else 11

    S = ""
    S += slot_svg(R1X,r1g1[0],8,rows[8])  + slot_svg(R1X,r1g1[1],9,rows[9])
    S += slot_svg(R1X,r1g4[0],5,rows[5])  + slot_svg(R1X,r1g4[1],12,rows[12])
    S += slot_svg(R1X,r1g2[0],7,rows[7])  + slot_svg(R1X,r1g2[1],10,rows[10])
    S += slot_svg(R1X,r1g3[0],6,rows[6])  + slot_svg(R1X,r1g3[1],11,rows[11])
    S += wplabel(8,9,*r1g1,R1X) + wplabel(5,12,*r1g4,R1X)
    S += wplabel(7,10,*r1g2,R1X) + wplabel(6,11,*r1g3,R1X)

    S += slot_svg(QFX,qf1[0],1,rows[1],bye=True)
    S += slot_svg(QFX,qf1[1],qf1_opp,rows[qf1_opp],proj=True)
    S += slot_svg(QFX,qf4[0],4,rows[4],bye=True)
    S += slot_svg(QFX,qf4[1],qf4_opp,rows[qf4_opp],proj=True)
    S += slot_svg(QFX,qf2[0],2,rows[2],bye=True)
    S += slot_svg(QFX,qf2[1],qf2_opp,rows[qf2_opp],proj=True)
    S += slot_svg(QFX,qf3[0],3,rows[3],bye=True)
    S += slot_svg(QFX,qf3[1],qf3_opp,rows[qf3_opp],proj=True)

    S += slot_svg(SFX,sf1[0],"?",None,tbd_lines=("SEMIFINAL 1","Winner: #1 Bracket"))
    S += slot_svg(SFX,sf1[1],"?",None,tbd_lines=("SEMIFINAL 1","Winner: #4 Bracket"))
    S += slot_svg(SFX,sf2[0],"?",None,tbd_lines=("SEMIFINAL 2","Winner: #2 Bracket"))
    S += slot_svg(SFX,sf2[1],"?",None,tbd_lines=("SEMIFINAL 2","Winner: #3 Bracket"))
    S += slot_svg(NX,nat[0],"?",None,tbd_lines=("NATIONAL CHAMPIONSHIP","Winner: Semifinal 1"),w=NW)
    S += slot_svg(NX,nat[1],"?",None,tbd_lines=("NATIONAL CHAMPIONSHIP","Winner: Semifinal 2"),w=NW)

    divider = '<line x1="{}" y1="{}" x2="{}" y2="{}" stroke="#1a2a3a" stroke-width="1" stroke-dasharray="4,8"/>'.format(SFX-10, NC, NX+NW+10, NC)

    svg = (
        "<div style=\"overflow-x:auto;overflow-y:hidden;-webkit-overflow-scrolling:touch;border-radius:12px;background:#060e1a;padding:8px;\">"
        + '<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg" style="display:block;min-width:{W}px;">'.format(W=W, H=H)
        + '<rect width="{}" height="{}" fill="#060e1a"/>'.format(W, H)
        + tracks + hdr + conn_svg + divider + S
        + "</svg></div>"
    )

    st.markdown(svg, unsafe_allow_html=True)
    st.caption("\U0001f7e6 PROJ = projected R1 winner  ·  QF/SF/Natty update once bracket is locked in")



def render_first_four_out(board_df):
    if board_df is None or board_df.empty:
        st.caption("No first four out teams available.")
        return

    def get_logo_path(team):
        path = get_logo_source(team)
        if isinstance(path, str) and path and Path(path).exists():
            return path
        return None

    for _, row in board_df.iterrows():
        team = str(row.get('Team', ''))
        primary = get_team_primary_color(team)
        record = str(row.get('Record', '—'))
        make_pct = format_pct(row.get('CFP Make %', np.nan), 1)
        bye_pct = format_pct(row.get('Bye %', np.nan), 1)
        rank_raw = pd.to_numeric(row.get('Rank', np.nan), errors='coerce')
        rank_disp = f"#{int(rank_raw)}" if pd.notna(rank_raw) else '—'
        logo_path = get_logo_path(team)

        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([5, 1.3, 1.5, 1.2])
            with c1:
                inner = st.columns([0.9, 1.2, 6])
                with inner[0]:
                    st.markdown(f"**{rank_disp}**")
                with inner[1]:
                    if logo_path:
                        st.image(logo_path, width=30)
                    else:
                        st.markdown("🏈")
                with inner[2]:
                    st.markdown(
                        f"<div style='font-size:16px;font-weight:900;color:{primary};'>{html.escape(team)}</div>",
                        unsafe_allow_html=True,
                    )
            c2.markdown(f"**{record}**")
            c3.markdown(f"**{make_pct}**")
            c4.markdown(f"**{bye_pct}**")


def load_video_review_assets():
    base = Path('weekly_out')
    files = {
        'summary': base / 'video_import_summary.txt',
        'standings': base / 'conference_standings_candidates.csv',
        'schedule': base / 'video_schedule_candidates.csv',
        'cfp': base / 'cfp_rankings_candidates.csv',
        'recruiting': base / 'recruiting_candidates.csv',
    }
    out = {}
    out['summary_text'] = files['summary'].read_text(encoding='utf-8', errors='replace') if files['summary'].exists() else ''
    for key in ['standings', 'schedule', 'cfp', 'recruiting']:
        try:
            out[key] = pd.read_csv(files[key]) if files[key].exists() else pd.DataFrame()
        except Exception:
            out[key] = pd.DataFrame()
    return out


def render_video_review_table(df, title, preferred_cols=None):
    st.markdown(f"#### {title}")
    if df is None or df.empty:
        st.caption("No data found yet.")
        return
    view = df.copy()
    if preferred_cols:
        cols = [c for c in preferred_cols if c in view.columns]
        if cols:
            view = view[cols]
    st.dataframe(view, hide_index=True, use_container_width=True)


def build_recruiting_momentum(rec_df, model_df):
    rows = []
    rec_local = rec_df.copy()
    rec_local['USER'] = rec_local['USER'].astype(str).str.strip().str.title()
    if 'Teams' in rec_local.columns:
        rec_local['Teams'] = rec_local['Teams'].astype(str).str.strip()

    for _, m in model_df[['USER', 'TEAM']].drop_duplicates().iterrows():
        user = str(m['USER']).strip().title()
        team = str(m['TEAM']).strip()
        rows_match = rec_local[(rec_local['USER'] == user) & (rec_local['Teams'].astype(str).str.lower() == team.lower())]
        if rows_match.empty:
            rows_match = rec_local[rec_local['USER'] == user]
        if rows_match.empty:
            continue
        row = rows_match.iloc[-1]
        year_cols = sorted([int(c) for c in row.index if str(c).isdigit()])
        points = []
        for y in year_cols:
            val = clean_rank_value(row.get(str(y)))
            if not pd.isna(val):
                points.append((int(y), float(val)))
        if len(points) < 2:
            continue
        recent = points[-5:]
        start_rank = recent[0][1]
        end_rank = recent[-1][1]
        trend = round(start_rank - end_rank, 1)
        rows.append({
            'USER': user,
            'TEAM': team,
            'Years': ' | '.join([f"{y}:{int(v)}" for y, v in recent]),
            'Start Rank': start_rank,
            'Latest Rank': end_rank,
            'Improvement': trend,
            'Momentum': 'Heating Up' if trend > 6 else ('Cooling Off' if trend < -6 else 'Stable'),
            'Logo': get_logo_source(team),
        })
    return pd.DataFrame(rows).sort_values(['Improvement', 'Latest Rank'], ascending=[False, True]).reset_index(drop=True) if rows else pd.DataFrame()


def build_sos_heatmap_df(model_df):
    cols = ['USER', 'TEAM', 'SOS', 'Resume Score', 'Current Record Wins', 'Current Record Losses', 'Combined Opponent Wins', 'Combined Opponent Losses']
    present = [c for c in cols if c in model_df.columns]
    if not present:
        return pd.DataFrame()
    out = model_df[present].copy()
    out['Record'] = out.apply(
        lambda r: f"{int(pd.to_numeric(r.get('Current Record Wins', 0), errors='coerce') or 0)}-"
                  f"{int(pd.to_numeric(r.get('Current Record Losses', 0), errors='coerce') or 0)}",
        axis=1
    )
    out['Opp Record'] = out.apply(
        lambda r: f"{int(pd.to_numeric(r.get('Combined Opponent Wins', 0), errors='coerce') or 0)}-"
                  f"{int(pd.to_numeric(r.get('Combined Opponent Losses', 0), errors='coerce') or 0)}",
        axis=1
    )
    return out.sort_values(['SOS', 'Resume Score'], ascending=False).reset_index(drop=True)


def build_conference_race_board(standings_df):
    if standings_df is None or standings_df.empty:
        return pd.DataFrame()
    board = standings_df.copy()
    label_col = 'screen_label' if 'screen_label' in board.columns else board.columns[0]
    text_col = 'ocr_text' if 'ocr_text' in board.columns else board.columns[-1]
    board[label_col] = board[label_col].astype(str)
    board[text_col] = board[text_col].astype(str)
    grouped = board.groupby(label_col).agg(
        Candidate_Frames=('frame_index', 'count') if 'frame_index' in board.columns else (text_col, 'count'),
        Best_Sharpness=('sharpness', 'max') if 'sharpness' in board.columns else (text_col, 'count'),
        OCR_Sample=(text_col, 'first'),
    ).reset_index()
    grouped = grouped.rename(columns={label_col: 'Conference Screen'})
    return grouped.sort_values(['Candidate_Frames', 'Best_Sharpness'], ascending=[False, False]).reset_index(drop=True)


def render_automation_v2_tab(model_df, rec_df):
    st.header("🎥 Automation V2")
    st.caption("Video-import review, conference race intake, recruiting momentum, and SOS pressure boards in one place.")

    assets = load_video_review_assets()
    momentum_df = build_recruiting_momentum(rec_df, model_df)
    sos_df = build_sos_heatmap_df(model_df)
    conference_board = build_conference_race_board(assets.get('standings'))

    mobile_metrics([
        {"label": "Conference Frames", "value": str(len(assets.get('standings', pd.DataFrame())))},
        {"label": "Schedule Frames",   "value": str(len(assets.get('schedule', pd.DataFrame())))},
        {"label": "CFP Frames",        "value": str(len(assets.get('cfp', pd.DataFrame())))},
        {"label": "Recruiting Frames", "value": str(len(assets.get('recruiting', pd.DataFrame())))},
    ])

    st.subheader("Latest Video Import Summary")
    if assets.get('summary_text'):
        st.code(assets['summary_text'], language='text')
    else:
        st.info("No video_import_summary.txt found yet in weekly_out.")

    st.markdown("---")
    st.subheader("Conference Championship Race Intake")
    if conference_board.empty:
        st.caption("No conference standings candidates found yet.")
    else:
        st.dataframe(conference_board, hide_index=True, use_container_width=True)

    st.markdown("---")
    left, right = st.columns([1.1, 0.9])
    with left:
        st.subheader("Recruiting Momentum")
        if momentum_df.empty:
            st.caption("Not enough recruiting history found yet.")
        else:
            st.dataframe(momentum_df[['TEAM', 'USER', 'Years', 'Latest Rank', 'Improvement', 'Momentum']], hide_index=True, use_container_width=True)
            fig = px.bar(
                momentum_df.head(12),
                x='TEAM',
                y='Improvement',
                color='Momentum',
                hover_data=['USER', 'Years', 'Latest Rank']
            )
            fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("SOS Heatmap")
        if sos_df.empty:
            st.caption("SOS data unavailable.")
        else:
            heat = sos_df[['TEAM', 'SOS', 'Resume Score']].copy()
            heat['TEAM'] = heat['TEAM'].astype(str)
            fig_h = px.imshow(
                heat.set_index('TEAM')[['SOS', 'Resume Score']].round(1),
                aspect='auto',
                color_continuous_scale='RdYlGn'
            )
            fig_h.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig_h, use_container_width=True)

    st.markdown("---")
    st.subheader("Raw Video Review Feeds")
    render_video_review_table(
        assets.get('standings'),
        "Conference Standings Candidates",
        ['screen_label', 'frame_index', 'sharpness', 'ocr_text', 'header_text', 'full_text']
    )
    render_video_review_table(
        assets.get('schedule'),
        "Schedule Candidates",
        ['screen_label', 'frame_index', 'sharpness', 'week_detected', 'records_found', 'scores_found', 'header_text', 'middle_text', 'full_text']
    )
    render_video_review_table(
        assets.get('cfp'),
        "CFP Ranking Candidates",
        ['screen_label', 'frame_index', 'sharpness', 'week_detected', 'header_text', 'middle_text', 'full_text']
    )
    render_video_review_table(
        assets.get('recruiting'),
        "Recruiting Candidates",
        ['screen_label', 'frame_index', 'sharpness', 'week_detected', 'header_text', 'middle_text', 'full_text']
    )


def render_cfp_table(board_df):
    rows_html = []
    for _, row in board_df.iterrows():
        team = str(row.get('Team', ''))
        primary = get_team_primary_color(team)
        logo_uri = image_file_to_data_uri(get_logo_source(team))
        logo_html = f"<img src='{logo_uri}' style='width:36px;height:36px;object-fit:contain;'/>" if logo_uri else "<div style='font-size:22px;'>🏈</div>"
        seed = row.get('Projected Seed', np.nan)
        seed_disp = '—' if pd.isna(seed) else str(int(seed))
        cells = [f"""
        <td style='padding:10px 12px;border-bottom:1px solid #e5e7eb;white-space:nowrap;'>
            <div style='display:flex;align-items:center;gap:10px;'>
                <div style='font-weight:800;min-width:20px;text-align:center;'>#{int(row.get('Rank', 0))}</div>
                <div style='width:38px;text-align:center;'>{logo_html}</div>
                <div style='font-weight:800;color:{primary};'>{html.escape(team)}</div>
            </div>
        </td>
        """]
        vals = [
            row.get('Record', '—'),
            format_pct(row.get('CFP Make %', np.nan), 1),
            format_pct(row.get('Bye %', np.nan), 1),
            format_pct(row.get('Auto-Bid %', np.nan), 1),
            row.get('Bubble Tier', '—'),
            seed_disp,
        ]
        for val in vals:
            cells.append(f"<td style='padding:10px 12px;border-bottom:1px solid #e5e7eb;text-align:center;white-space:nowrap;'>{html.escape(str(val))}</td>")
        rows_html.append(f"<tr style='border-left:6px solid {primary};background:linear-gradient(90deg,{primary}12,transparent 14%);'>{''.join(cells)}</tr>")
    table_html = f"""
    <div style='overflow-x:auto;border:1px solid #e5e7eb;border-radius:14px;'>
      <table style='width:100%;border-collapse:collapse;font-size:13px;'>
        <thead>
          <tr style='background:#f8fafc;color:#111827;'>
            <th style='text-align:left;padding:10px 12px;color:#111827;font-weight:800;'>Team</th>
            <th style='padding:10px 12px;color:#111827;font-weight:800;'>Record</th>
            <th style='padding:10px 12px;color:#111827;font-weight:800;'>Make CFP</th>
            <th style='padding:10px 12px;color:#111827;font-weight:800;'>Bye Odds</th>
            <th style='padding:10px 12px;color:#111827;font-weight:800;'>Auto-Bid Path</th>
            <th style='padding:10px 12px;color:#111827;font-weight:800;'>Tier</th>
            <th style='padding:10px 12px;color:#111827;font-weight:800;'>Projected Seed</th>
          </tr>
        </thead>
        <tbody>{''.join(rows_html)}</tbody>
      </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)


def simulate_cfp_chaos(team_row, scenario, board_df):
    row = team_row.copy()
    rank = int(row['Rank'])
    wins = int(row['Wins'])
    losses = int(row['Losses'])
    sos = float(row.get('SOS', 55.0))
    resume = float(row.get('Resume Score', 58.0))
    cfp_make = float(row.get('CFP Make %', 50.0))
    bye = float(row.get('Bye %', 12.0))

    if scenario == 'Win next game':
        wins += 1
        rank = max(1, rank - (2 if rank > 4 else 1))
        sos += 1.5
        resume += 3.0
        cfp_make = min(99.0, cfp_make + (10 if rank <= 10 else 14))
        bye = min(96.0, bye + (7 if rank <= 8 else 4))
    elif scenario == 'Win over Top-12 team':
        wins += 1
        rank = max(1, rank - (4 if rank > 8 else 2))
        sos += 4.0
        resume += 6.0
        cfp_make = min(99.0, cfp_make + (18 if rank <= 12 else 22))
        bye = min(96.0, bye + (12 if rank <= 8 else 8))
    elif scenario == 'Lose to ranked team':
        losses += 1
        rank = min(25, rank + (3 if rank <= 8 else 2))
        sos += 1.0
        resume -= 3.0
        cfp_make = max(1.0, cfp_make - (11 if losses <= 2 else 16))
        bye = max(0.5, bye - (8 if rank <= 6 else 5))
    elif scenario == 'Lose to unranked team':
        losses += 1
        rank = min(25, rank + (8 if rank <= 10 else 5))
        sos -= 1.5
        resume -= 8.0
        cfp_make = max(1.0, cfp_make - (24 if losses <= 2 else 30))
        bye = max(0.5, bye - (18 if rank <= 8 else 10))

    temp = pd.DataFrame([{
        'Rank': rank, 'Wins': wins, 'Losses': losses, 'Record': f'{wins}-{losses}',
        'Team': row['Team'], 'SOS': sos, 'Resume Score': resume,
        'CFP Make %': cfp_make, 'Bye %': bye
    }])
    return temp.iloc[0]

data = load_data()

if data:
    scores = data['scores']
    stats = data['stats']
    all_users = data['all_users']
    years = data['years']
    meta = data['meta']
    r_2041 = data['r_2041']
    h2h_df = data['h2h_df']
    h2h_heat = data['h2h_heat']
    rivalry_df = data['rivalry_df']
    coty = data['coty']
    heisman = data['heisman']
    heisman_fin = data.get('heisman_fin', None)
    rec = data['rec']
    draft = data['draft']
    champs = data['champs']
    ratings = data['ratings']

    model_2041 = build_2041_model_table(r_2041, stats, rec)
    # Recompute the visible QB tier straight from the latest source file so cache/file drift doesn't screw us.
    if 'QB Tier' in model_2041.columns:
        model_2041 = model_2041.drop(columns=['QB Tier'])
    qb_source = r_2041[['USER', 'TEAM']].copy()
    qb_source['QB Tier'] = r_2041.apply(qb_label, axis=1)
    model_2041 = model_2041.merge(qb_source, on=['USER', 'TEAM'], how='left')
    model_2041['Logo'] = model_2041['TEAM'].apply(get_logo_source)
    user_color_map = build_user_color_map(model_2041)
    team_color_map = build_team_color_map(model_2041)
    # Defensive fill so UI sections never fail if a derived column is absent.
    for col, default in {
        'Program Stock': '➖ Stable',
        'Career Win %': 50.0,
        'Recruit Score': 50.0,
        'Projected Wins': 6.5,
        'CFP Odds': 20,
        'Natty Odds': 5.0,
        'Collapse Risk': 35,
        'Power Index': 200.0
    }.items():
        if col not in model_2041.columns:
            model_2041[col] = default

    scenario_df = model_2041.apply(project_loss_scenarios, axis=1)
    model_2041 = pd.concat([model_2041, scenario_df], axis=1)
    recruiting_board = build_recruiting_board(rec, model_2041)
    current_user_games = get_current_user_games(model_2041)

    # ── Build cfp_board early so Power Rankings can use real CFP Make % ───────
    try:
        _cfp_rankings_early = get_cfp_rankings_snapshot()
        _cfp_board_early = build_cfp_bubble_board(_cfp_rankings_early, model_2041)
        # Merge CFP Make % back into model_2041 for user teams
        if not _cfp_board_early.empty and 'CFP Make %' in _cfp_board_early.columns:
            _cfp_lookup = _cfp_board_early[['Team','CFP Make %']].copy()
            _cfp_lookup = _cfp_lookup.rename(columns={'Team': 'TEAM'})
            model_2041 = model_2041.merge(_cfp_lookup, on='TEAM', how='left')
            # Fill non-matched teams with CFP Odds as fallback
            if 'CFP Make %' not in model_2041.columns:
                model_2041['CFP Make %'] = model_2041['CFP Odds']
            else:
                model_2041['CFP Make %'] = model_2041['CFP Make %'].fillna(model_2041['CFP Odds'])
    except Exception:
        model_2041['CFP Make %'] = model_2041.get('CFP Odds', 42)

    USER_TEAMS = {
        'Mike':  'San Jose State',
        'Devin': 'Bowling Green',
        'Josh':  'USF',
        'Noah':  'Texas Tech',
        'Doug':  'Florida',
        'Nick':  'Florida State',
    }

    RIVALRY_NAMES = {
        frozenset(["Mike",  "Noah"]):  ("⚡ The Overclocked Bowl",      "Two tech schools. One beef. It's the nerd rivalry nobody asked for and everyone should fear."),
        frozenset(["Mike",  "Doug"]):  ("🥖 The Sourdough & Swamp Bowl","West Coast vibes vs Florida Man energy. It shouldn't work but it absolutely goes."),
        frozenset(["Mike",  "Nick"]):  ("🥇 The Gold Rush Classic",     "Gold helmets, West Coast money, Tallahassee attitude. Someone's getting cooked."),
        frozenset(["Mike",  "Devin"]): ("🦅 The Falcon Punch Bowl",     "SJSU vs Bowling Green. Mountain West chaos meets MAC energy. Low-key unhinged."),
        frozenset(["Mike",  "Josh"]):  ("🌊 The Bay vs the Bull",       "California cool meets Tampa heat. Somebody's leaving sunburned."),
        frozenset(["Noah",  "Doug"]):  ("🍖 The Brisket & Gator Tail Showdown","Texas BBQ pit vs Florida swamp cuisine. Bragging rights served with hot sauce."),
        frozenset(["Noah",  "Nick"]):  ("🤠 The Lone Star vs Garnet Grudge","Red Raiders and Seminoles. They meet in the middle of nowhere and throw haymakers."),
        frozenset(["Noah",  "Devin"]): ("🏹 The Wreck the Tech Bowl",   "Noah's Raiders vs Devin's Falcons. Low-key nasty every single time."),
        frozenset(["Noah",  "Josh"]):  ("🍞 The Texas Toast vs Tampa Bowl","Lone Star swagger meets Florida Lightning. The vibe check nobody passes."),
        frozenset(["Doug",  "Nick"]):  ("🍊 The Florida Man Bowl",      "Both of y'all live in Florida. This is the most unhinged in-state rivalry in dynasty history."),
        frozenset(["Doug",  "Devin"]): ("🍩 The Swamp Donuts Classic",  "Florida Gators vs Bowling Green Falcons. Doesn't make geographic sense. Still slaps."),
        frozenset(["Doug",  "Josh"]):  ("⚡ The I-4 Grudge Match",      "Tampa to Gainesville is 2 hours. This rivalry lives rent-free in both their heads."),
        frozenset(["Nick",  "Devin"]): ("🏈 The Seminole & Falcon Faceoff","Tallahassee prestige vs MAC grit. Blue chips vs chaos. Pick your poison."),
        frozenset(["Nick",  "Josh"]):  ("☀️ The Sunshine State Slap Fight","Two Florida programs. One grudge match. The loser has to explain it to their recruits."),
        frozenset(["Devin", "Josh"]):  ("🐦 The Bird Bowl",             "Bowling Green Falcons vs USF Bulls. The most Ohio vs Florida energy imaginable."),
    }

    tabs = st.tabs([
        "🗞️ Dynasty News",
        "📐 SOS & True Path",
        "🏆 Who's In?",
        "📺 Season Recap",
        "🔍 Speed Freaks",
        "🎯 Roster Matchup",
        "📊 Team Overview",
        "🏈 Recruiting Rankings",
        "⚔️ H2H Matrix",
        "🚨 Upset Tracker",
        "🐐 GOAT Rankings",
    ])

    # --- SOS & TRUE PATH ---
    with tabs[1]:
        st.header("📐 SOS & True Path")
        st.caption("Who actually earned their record? Schedule résumé, speed-adjusted difficulty, week-by-week breakdown, and quality wins. Slower teams fight harder for every W.")

        try:
            _cpu_sos = pd.read_csv('CPUscores_MASTER.csv')
            _cpu_sos['YEAR'] = pd.to_numeric(_cpu_sos['YEAR'], errors='coerce')
            _cpu_sos = _cpu_sos[_cpu_sos['YEAR'] == CURRENT_YEAR].copy()
        except Exception:
            _cpu_sos = pd.DataFrame()

        # Normalise user names — Mike Stegeman → Mike
        def _norm_user(u):
            if pd.isna(u): return 'CPU'
            u = str(u).strip()
            if u.lower().startswith('mike'): return 'Mike'
            return u

        if not _cpu_sos.empty:
            _cpu_sos['Vis_User']  = _cpu_sos['Vis_User'].apply(_norm_user)
            _cpu_sos['Home_User'] = _cpu_sos['Home_User'].apply(_norm_user)
            _cpu_sos['Visitor Rank'] = pd.to_numeric(_cpu_sos['Visitor Rank'], errors='coerce')
            _cpu_sos['Home Rank']    = pd.to_numeric(_cpu_sos['Home Rank'],    errors='coerce')
            _cpu_sos['Vis Score']    = pd.to_numeric(_cpu_sos['Vis Score'],    errors='coerce')
            _cpu_sos['Home Score']   = pd.to_numeric(_cpu_sos['Home Score'],   errors='coerce')

        # Speed + QB data from model
        # ── Live speed counts from roster CSV (REDSHIRT-aware) ──────────────
        # cfb26_rosters_full.csv has a REDSHIRT column (1 = sitting out this year).
        # Players with REDSHIRT=1 are excluded from speed counts.
        # Teams without RS screenshots default to 0 (all active) until updated.
        # BG, USF, Texas Tech confirmed: they do not redshirt — all freshmen are active.
        _NO_REDSHIRT_TEAMS = {'Devin', 'Josh', 'Noah'}  # confirmed: never redshirt
        _roster_speed = {}
        try:
            _rfull = pd.read_csv('cfb26_rosters_full.csv')
            _rfull['SPD']      = pd.to_numeric(_rfull['SPD'],      errors='coerce')
            _rfull['ACC']      = pd.to_numeric(_rfull['ACC'],      errors='coerce')
            _rfull['REDSHIRT'] = pd.to_numeric(_rfull.get('REDSHIRT', 0), errors='coerce').fillna(0).astype(int)
            _active = _rfull[_rfull['REDSHIRT'] == 0]
            _team_to_user = {v: k for k, v in USER_TEAMS.items()}
            for _team, _tdf in _active.groupby('Team'):
                _u = _team_to_user.get(_team)
                if not _u:
                    continue
                _roster_speed[_u] = {
                    'team_speed_live': int((_tdf['SPD'] >= 90).sum()),
                    'gen_live':        int(((_tdf['SPD'] >= 96) | (_tdf['ACC'] >= 96)).sum()),
                }
        except Exception:
            pass

        _speed_map = {}
        for _, _sr in model_2041.iterrows():
            _u    = _sr['USER']
            _live = _roster_speed.get(_u, {})
            # Prefer live roster count if available, else fall back to TeamRatingsHistory
            _ts   = _live.get('team_speed_live', float(_sr.get('Team Speed (90+ Speed Guys)', 0) or 0))
            _gen  = _live.get('gen_live',         float(_sr.get('Generational (96+ speed or 96+ Acceleration)', 0) or 0))
            _speed_map[_u] = {
                'team_speed':  float(_ts),
                'off_speed':   float(_sr.get('Off Speed (90+ speed)', 0) or 0),
                'def_speed':   float(_sr.get('Def Speed (90+ speed)', 0) or 0),
                'gen':         float(_gen),
                'overall':     float(_sr.get('OVERALL', 80) or 80),
                'qb_ovr':      float(_sr.get('QB OVR', 80) or 80),
                'qb_tier':     str(_sr.get('QB Tier', 'Average Joe')).strip(),
                'team':        _sr['TEAM'],
                'conf':        _sr.get('CONFERENCE', 'Other'),
                'rs_data_confirmed': (_u in _roster_speed) or (_u in _NO_REDSHIRT_TEAMS),
            }

        _league_avg_speed = sum(v['team_speed'] for v in _speed_map.values()) / max(1, len(_speed_map))

        # Final-season rank lookup — display fallback when at-game rank is NaN
        # e.g. BG was unranked early but ended the season #4 nationally.
        try:
            _cfp_final = pd.read_csv('cfp_rankings_history.csv')
            _cfp_yr    = _cfp_final['YEAR'].max()
            _cfp_wk    = _cfp_final[_cfp_final['YEAR'] == _cfp_yr]['WEEK'].max()
            _cfp_snap  = _cfp_final[
                (_cfp_final['YEAR'] == _cfp_yr) & (_cfp_final['WEEK'] == _cfp_wk)
            ]
            _final_rank_lookup = dict(
                zip(_cfp_snap['TEAM'].str.strip(), _cfp_snap['RANK'].astype(int))
            )
        except Exception:
            _final_rank_lookup = {}

        def _get_user_games(user):
            """Return one row per game for this user.

            opp_rank        – rank at game time (NaN if unranked then)
            opp_final_rank  – rank from end-of-season poll (NaN if never ranked)
            opp_ranked      – True if ranked AT game time
            opp_ranked_final– True if ranked at game time OR ended ranked
            effective_rank  – best available rank: at-game-time first, final fallback
            """
            if _cpu_sos.empty: return pd.DataFrame()
            mask  = (_cpu_sos['Vis_User'] == user) | (_cpu_sos['Home_User'] == user)
            games = _cpu_sos[mask].copy()
            results = []
            for _, g in games.iterrows():
                is_vis    = g['Vis_User'] == user
                my_score  = g['Vis Score']  if is_vis else g['Home Score']
                opp_score = g['Home Score'] if is_vis else g['Vis Score']
                opp_name  = g['Home']       if is_vis else g['Visitor']
                opp_rank  = g['Home Rank']  if is_vis else g['Visitor Rank']
                my_rank   = g['Visitor Rank'] if is_vis else g['Home Rank']
                home_away = 'Away' if is_vis else 'Home'
                week      = str(g['Week'])
                if pd.isna(my_score) or pd.isna(opp_score):
                    result = 'TBD'
                elif my_score > opp_score:
                    result = 'W'
                else:
                    result = 'L'
                margin         = (my_score - opp_score) if result != 'TBD' else None
                opp_ranked     = not pd.isna(opp_rank)
                opp_final_rank = _final_rank_lookup.get(str(opp_name).strip())
                opp_ranked_final = opp_ranked or (opp_final_rank is not None)
                # Best available rank: at-game-time preferred, final fallback
                effective_rank = opp_rank if opp_ranked else (float(opp_final_rank) if opp_final_rank else float('nan'))
                results.append({
                    'week': week, 'opponent': opp_name,
                    'opp_rank': opp_rank,
                    'opp_final_rank': opp_final_rank,
                    'opp_ranked': opp_ranked,
                    'opp_ranked_final': opp_ranked_final,
                    'effective_rank': effective_rank,
                    'my_rank': my_rank, 'result': result,
                    'my_score': my_score, 'opp_score': opp_score,
                    'margin': margin, 'home_away': home_away,
                    'conf_game': int(g.get('Conf Title', 0) or 0) == 1,
                    'bowl': int(g.get('Bowl', 0) or 0) == 1,
                })
            return pd.DataFrame(results)

        def _speed_handicap(user):
            info = _speed_map.get(user, {})
            spd  = info.get('team_speed', _league_avg_speed)
            spd_raw = (_league_avg_speed - spd) * 0.55
            qb_tier = info.get('qb_tier', 'Average Joe')
            qb_ovr  = info.get('qb_ovr', 80)
            qb_base = {'Elite': -4.0, 'Leader': -1.5, 'Average Joe': 1.5, 'Ass': 5.0}.get(qb_tier, 0)
            if qb_tier == 'Elite':
                qb_base += (qb_ovr - 90) * -0.12
            elif qb_tier == 'Ass':
                qb_base += max(0, 80 - qb_ovr) * 0.20
            return round(spd_raw + qb_base, 2)

        def _sos_score(games_df):
            """Compute SOS using final-rank-corrected effective_rank.

            Uses opp_ranked_final so teams like BG (ranked at end, not early)
            are properly credited in ranked wins / avg opp rank.
            Top-10 check uses effective_rank (best available: at-time or final).
            """
            if games_df.empty: return 0, 0, 0, 0
            ranked_wins   = int(((games_df['result']=='W') & games_df['opp_ranked_final']).sum())
            top10_wins    = int(((games_df['result']=='W') & (games_df['effective_rank'] <= 10)).sum())
            ranked_losses = int(((games_df['result']=='L') & games_df['opp_ranked_final']).sum())
            comp_games    = games_df[games_df['opp_ranked_final']]
            avg_opp_rank  = float(comp_games['effective_rank'].mean()) if not comp_games.empty else 99.0
            base_sos = (
                ranked_wins   * 8.5
                + top10_wins  * 4.0
                - ranked_losses * 1.5
                + max(0, (25 - avg_opp_rank)) * 0.8
            )
            return round(base_sos, 1), ranked_wins, top10_wins, round(avg_opp_rank, 1)

        # ── BUILD RÉSUMÉ DATA ─────────────────────────────────────────────────
        resume_rows = []
        for user in USER_TEAMS:
            g = _get_user_games(user)
            spd_info = _speed_map.get(user, {})
            base, rw, t10, avg_opp = _sos_score(g)
            handicap = _speed_handicap(user)
            adj_sos = round(base + handicap, 1)
            wins  = int((g['result'] == 'W').sum()) if not g.empty else 0
            losses = int((g['result'] == 'L').sum()) if not g.empty else 0
            resume_rows.append({
                'User': user, 'Team': USER_TEAMS[user],
                'Record': f"{wins}-{losses}",
                'Ranked Wins': rw, 'Top-10 Wins': t10,
                'Avg Opp Rank': avg_opp if avg_opp < 99 else '—',
                'Base SOS': base,
                'Speed Handicap': f"+{handicap:.1f}" if handicap > 0 else f"{handicap:.1f}",
                '_handicap': handicap,
                'Adj SOS': adj_sos,
                'Team Speed': int(spd_info.get('team_speed', 0)),
                'QB Tier': spd_info.get('qb_tier', '—'),
                'QB OVR': int(spd_info.get('qb_ovr', 0)),
                'Conference': spd_info.get('conf', '—'),
                '_rs_confirmed': spd_info.get('rs_data_confirmed', False),
            })
        resume_df = pd.DataFrame(resume_rows).sort_values('Adj SOS', ascending=False).reset_index(drop=True)

        # Check if preseason rank data exists (WEEK = 0 or 1 from PREVIOUS year)
        # Next season: capture week-1 rankings so we can diff preseason vs final SOS
        _has_preseason = False
        try:
            _cfp_all = pd.read_csv('cfp_rankings_history.csv')
            _years   = sorted(_cfp_all['YEAR'].unique())
            _has_preseason = len(_years) >= 2   # need at least 2 seasons of data
        except Exception:
            pass

        # ── SECTION 1: TOP METRICS ────────────────────────────────────────────
        _top = resume_df.iloc[0]
        _most_rw = resume_df.sort_values('Ranked Wins', ascending=False).iloc[0]
        _hardest = resume_df.sort_values('_handicap', ascending=False).iloc[0]  # highest handicap = slowest
        _fastest = resume_df.sort_values('Team Speed', ascending=False).iloc[0]
        mobile_metrics([
            {"label": "📋 Best Résumé",      "value": _top['User'],        "delta": f"Adj SOS: {_top['Adj SOS']}"},
            {"label": "💪 Most Ranked Wins",  "value": _most_rw['User'],    "delta": f"{_most_rw['Ranked Wins']} ranked W"},
            {"label": "🐢 Hardest Path",      "value": _hardest['User'],    "delta": f"Speed handicap +{_hardest['_handicap']:.1f}"},
            {"label": "⚡ Speed Advantage",   "value": _fastest['User'],    "delta": f"{_fastest['Team Speed']} speed guys"},
        ], cols_desktop=4)

        # ── SECTION 2: RÉSUMÉ LEADERBOARD ────────────────────────────────────
        st.markdown("---")
        st.subheader("📋 Schedule Résumé Board — Final SOS")
        if _has_preseason:
            st.caption("🔵 **Final SOS** · Preseason SOS comparison available — see below. Speed-adjusted SOS = Base SOS + Speed Handicap.")
        else:
            st.caption("📌 **Final SOS** (ranks corrected to end-of-season poll — opponents like BG that earned their ranking late are properly credited). Preseason SOS unlocks next season once week-1 rankings are captured. Speed-adjusted SOS = Base SOS + Speed Handicap.")

        rank_medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣"]
        resume_cards = ""
        for i, row in resume_df.iterrows():
            tc       = get_team_primary_color(row['Team'])
            logo_uri = image_file_to_data_uri(get_logo_source(row['Team']))
            logo_img = f"<img src='{logo_uri}' style='width:34px;height:34px;object-fit:contain;vertical-align:middle;'/>" if logo_uri else "🏈"
            medal    = rank_medals[i] if i < len(rank_medals) else str(i+1)
            hcap     = float(row['_handicap'])
            hcap_color = "#ef4444" if hcap > 4 else ("#f97316" if hcap > 1 else ("#fbbf24" if hcap > 0 else "#22c55e"))
            adj_color  = "#22c55e" if row['Adj SOS'] >= resume_df['Adj SOS'].median() else "#f97316"
            hcap_label = f"+{hcap:.1f}" if hcap > 0 else f"{hcap:.1f}"
            spd = row['Team Speed']
            spd_pct = min(100, int(spd / 15 * 100))
            rs_confirmed = row.get('_rs_confirmed', False)
            rs_badge = "" if rs_confirmed else "<span style='font-size:0.58rem;padding:1px 4px;background:#292524;color:#a8a29e;border-radius:3px;margin-left:4px;'>RS?</span>"
            # QB badge
            _qt   = str(row.get('QB Tier', '—'))
            _qovr = int(row.get('QB OVR', 0))
            _qt_style = {'Elite':('#22c55e','#0d2010'),'Leader':('#60a5fa','#0d1829'),'Average Joe':('#fbbf24','#1c1400'),'Ass':('#ef4444','#200808')}
            _qtc  = _qt_style.get(_qt, ('#6b7280','#1f2937'))
            # Conf badge
            cconf = str(row['Conference'])
            conf_colors = {'SEC':('#fbbf24','#78350f'),'B1G':('#60a5fa','#1e3a5f'),'ACC':('#a78bfa','#3b1d6e'),'Big 12':('#f97316','#431407')}
            cc = conf_colors.get(cconf, ('#6b7280','#1f2937'))
            avg_opp_disp = f"#{int(row['Avg Opp Rank'])}" if row['Avg Opp Rank'] != '—' else '—'
            rw_color = "#22c55e" if row['Ranked Wins'] >= 3 else ("#fbbf24" if row['Ranked Wins'] >= 1 else "#475569")
            t10_color = "#fbbf24" if row['Top-10 Wins'] >= 2 else ("#94a3b8" if row['Top-10 Wins'] >= 1 else "#475569")

            resume_cards += f"""
            <div style='background:#0a1628;border:1px solid #1e293b;border-left:4px solid {tc};
            border-radius:10px;padding:12px 14px;margin-bottom:8px;'>

              <!-- Row 1: rank + logo + name + record + adj SOS -->
              <div style='display:flex;align-items:center;gap:10px;margin-bottom:10px;'>
                <span style='font-size:1.2rem;min-width:28px;'>{medal}</span>
                {logo_img}
                <div style='flex:1;min-width:0;'>
                  <div style='color:{tc};font-weight:900;font-size:0.95rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{html.escape(row['Team'])}</div>
                  <div style='display:flex;align-items:center;gap:6px;margin-top:2px;flex-wrap:wrap;'>
                    <span style='color:#475569;font-size:0.72rem;'>({html.escape(row['User'])})</span>
                    <span style='padding:1px 6px;border-radius:999px;font-size:0.65rem;font-weight:800;background:{cc[1]};color:{cc[0]};border:1px solid {cc[0]}44;'>{html.escape(cconf)}</span>
                  </div>
                </div>
                <div style='text-align:right;flex-shrink:0;'>
                  <div style='color:white;font-weight:800;font-size:0.95rem;'>{row['Record']}</div>
                  <div style='color:{adj_color};font-weight:900;font-size:1.1rem;'>{row['Adj SOS']}</div>
                  <div style='color:#475569;font-size:0.62rem;'>Adj SOS</div>
                </div>
              </div>

              <!-- Row 2: stat pills -->
              <div style='display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;'>
                <div style='background:#111f33;border-radius:6px;padding:5px 9px;text-align:center;'>
                  <div style='color:{rw_color};font-weight:800;font-size:0.9rem;'>{row['Ranked Wins']}</div>
                  <div style='color:#475569;font-size:0.62rem;letter-spacing:.05em;'>RANKED W</div>
                </div>
                <div style='background:#111f33;border-radius:6px;padding:5px 9px;text-align:center;'>
                  <div style='color:{t10_color};font-weight:800;font-size:0.9rem;'>{row['Top-10 Wins']}</div>
                  <div style='color:#475569;font-size:0.62rem;letter-spacing:.05em;'>TOP-10 W</div>
                </div>
                <div style='background:#111f33;border-radius:6px;padding:5px 9px;text-align:center;'>
                  <div style='color:#94a3b8;font-weight:700;font-size:0.9rem;'>{avg_opp_disp}</div>
                  <div style='color:#475569;font-size:0.62rem;letter-spacing:.05em;'>AVG OPP RK</div>
                </div>
                <div style='background:#111f33;border-radius:6px;padding:5px 9px;text-align:center;'>
                  <div style='color:{hcap_color};font-weight:800;font-size:0.9rem;'>{hcap_label}</div>
                  <div style='color:#475569;font-size:0.62rem;letter-spacing:.05em;'>HANDICAP</div>
                </div>
                <div style='background:{_qtc[1]};border-radius:6px;padding:5px 9px;text-align:center;border:1px solid {_qtc[0]}33;'>
                  <div style='color:{_qtc[0]};font-weight:800;font-size:0.82rem;white-space:nowrap;'>{html.escape(_qt)}</div>
                  <div style='color:{_qtc[0]}99;font-size:0.62rem;letter-spacing:.05em;'>{_qovr} OVR QB</div>
                </div>
              </div>

              <!-- Row 3: speed bar -->
              <div style='display:flex;align-items:center;gap:8px;'>
                <span style='color:#475569;font-size:0.68rem;letter-spacing:.05em;white-space:nowrap;'>SPEED</span>
                <div style='flex:1;background:#111f33;border-radius:3px;height:6px;overflow:hidden;'>
                  <div style='background:{tc};width:{spd_pct}%;height:6px;border-radius:3px;'></div>
                </div>
                <span style='color:#94a3b8;font-size:0.72rem;font-weight:700;min-width:24px;text-align:right;'>{spd}{rs_badge}</span>
              </div>

            </div>"""

        st.markdown(resume_cards, unsafe_allow_html=True)

        st.caption("⚠️ Speed Handicap: slower teams (+) face tougher effective difficulty — faster teams can mask roster weaknesses with athleticism. Positive = harder path.")

        # ── SECTION 2b: HARDEST PATH NARRATIVE ───────────────────────────────
        st.markdown("---")
        st.subheader("🪖 Who Had the Hardest Path?")
        st.caption("Ranked by adjusted difficulty — a 9-1 season against ranked opponents with a bad QB and no speed is NOT the same as 9-1 against nobodies.")

        # Sort by _handicap descending = hardest path first
        hardest_df = resume_df.sort_values('_handicap', ascending=False).reset_index(drop=True)
        path_icons = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣"]

        for idx, hr in hardest_df.iterrows():
            huser    = hr['User']
            hteam    = hr['Team']
            hcolor   = get_team_primary_color(hteam)
            logo_uri = image_file_to_data_uri(get_logo_source(hteam))
            logo_img = f"<img src='{logo_uri}' style='width:32px;height:32px;object-fit:contain;vertical-align:middle;margin-right:8px;'/>" if logo_uri else ""
            hcap     = float(hr['_handicap'])
            hspd     = hr['Team Speed']
            hqb      = str(hr.get('QB Tier', '—'))
            hqbovr   = int(hr.get('QB OVR', 0))
            hrw      = hr['Ranked Wins']
            ht10     = hr['Top-10 Wins']
            hrec     = hr['Record']
            hconf    = str(hr.get('Conference', '—'))
            hadjos   = hr['Adj SOS']

            # Build the difficulty narrative sentence
            parts = []
            if hcap >= 5:
                parts.append(f"catastrophic QB situation ({hqb}, {hqbovr} OVR)")
            elif hcap >= 2:
                parts.append(f"below-avg QB ({hqb}, {hqbovr} OVR) dragging them down")
            elif hcap <= -4:
                parts.append(f"elite QB ({hqbovr} OVR) softening the blow")
            else:
                parts.append(f"{hqb} QB ({hqbovr} OVR)")

            if hspd <= 5:
                parts.append(f"almost no team speed ({hspd} guys)")
            elif hspd <= 8:
                parts.append(f"limited speed ({hspd} guys)")
            elif hspd >= 13:
                parts.append(f"elite team speed ({hspd} guys)")
            else:
                parts.append(f"average speed ({hspd} guys)")

            conf_ctx = {'SEC': "in the murder conference (SEC)", 'B1G': "in the other murder conference (B1G)", 'ACC': "in the ACC"}.get(hconf, f"in the {hconf}")
            parts.append(f"competing {conf_ctx}")

            if hrw >= 4:
                parts.append(f"still racked up {hrw} ranked wins")
            elif hrw >= 2:
                parts.append(f"managed {hrw} ranked wins anyway")
            elif hrw == 0:
                parts.append("zero ranked wins on the résumé")
            else:
                parts.append(f"only {hrw} ranked win to show for it")

            # Join narrative
            if len(parts) >= 3:
                narrative = f"{parts[0].capitalize()}, {parts[1]}, {parts[2]} — {parts[3]}."
            else:
                narrative = ". ".join(p.capitalize() for p in parts) + "."

            # Difficulty bar (0–10 scale, handicap capped at ±10)
            bar_pct = min(100, max(0, int((hcap + 6) / 16 * 100)))
            bar_color = "#ef4444" if hcap > 4 else ("#f97316" if hcap > 1 else ("#fbbf24" if hcap > -1 else "#22c55e"))
            hcap_label = f"+{hcap:.1f}" if hcap > 0 else f"{hcap:.1f}"
            rank_icon = path_icons[idx] if idx < len(path_icons) else str(idx+1)

            # Conf badge colors
            _cc = {'SEC':('#fbbf24','#78350f'),'B1G':('#60a5fa','#1e3a5f'),'ACC':('#a78bfa','#3b1d6e')}.get(hconf, ('#6b7280','#1f2937'))
            conf_badge = f"<span style='padding:2px 6px;border-radius:999px;font-size:0.68rem;font-weight:800;background:{_cc[1]};color:{_cc[0]};border:1px solid {_cc[0]}44;'>{html.escape(hconf)}</span>"

            st.markdown(f"""
            <div style='background:#0a1628;border:1px solid #1e293b;border-left:4px solid {hcolor};border-radius:10px;padding:14px 16px;margin-bottom:10px;'>
              <div style='display:flex;align-items:center;gap:10px;margin-bottom:10px;'>
                <span style='font-size:1.4rem;'>{rank_icon}</span>
                {logo_img}
                <div style='flex:1;'>
                  <span style='color:{hcolor};font-weight:900;font-size:1rem;'>{html.escape(hteam)}</span>
                  <span style='color:#475569;font-size:0.8rem;margin-left:8px;'>({html.escape(huser)})</span>
                  <span style='margin-left:8px;'>{conf_badge}</span>
                </div>
                <div style='text-align:right;'>
                  <div style='color:white;font-weight:800;font-size:0.9rem;'>{hrec}</div>
                  <div style='color:#475569;font-size:0.72rem;'>{hrw} ranked W · {ht10} top-10 W</div>
                </div>
              </div>
              <div style='margin-bottom:8px;'>
                <div style='display:flex;justify-content:space-between;margin-bottom:4px;'>
                  <span style='font-size:0.72rem;color:#475569;font-family:monospace;letter-spacing:.05em;'>PATH DIFFICULTY</span>
                  <span style='font-size:0.78rem;color:{bar_color};font-weight:800;font-family:monospace;'>{hcap_label} handicap · Adj SOS {hadjos}</span>
                </div>
                <div style='background:#111f33;border-radius:4px;height:8px;overflow:hidden;'>
                  <div style='background:{bar_color};width:{bar_pct}%;height:8px;border-radius:4px;'></div>
                </div>
              </div>
              <div style='color:#94a3b8;font-size:0.82rem;line-height:1.5;'>{narrative}</div>
            </div>""", unsafe_allow_html=True)

        # ── SECTION 3: WEEK-BY-WEEK TIMELINE ─────────────────────────────────
        st.markdown("---")
        st.subheader("📅 Week-by-Week Schedule")
        sel_user = st.selectbox("Select a user to inspect", list(USER_TEAMS.keys()), key="sos_user_select")

        sel_games = _get_user_games(sel_user)
        sel_team  = USER_TEAMS.get(sel_user, sel_user)
        sel_color = get_team_primary_color(sel_team)
        sel_speed = _speed_map.get(sel_user, {}).get('team_speed', 0)
        sel_handicap = _speed_handicap(sel_user)

        if not sel_games.empty:
            # Speed + QB context banner
            sel_qb_tier = _speed_map.get(sel_user, {}).get('qb_tier', 'Average Joe')
            sel_qb_ovr  = int(_speed_map.get(sel_user, {}).get('qb_ovr', 80))
            spd_tier = "Elite 🔥" if sel_speed >= 13 else ("Above Avg ⚡" if sel_speed >= 10 else ("Below Avg ⚠️" if sel_speed >= 7 else "Slow 🐢"))
            _qb_notes = {
                'Elite':       f"Elite QB ({sel_qb_ovr} OVR) — bails you out when the schedule gets nasty.",
                'Leader':      f"Leader QB ({sel_qb_ovr} OVR) — solid, won't lose you games you should win.",
                'Average Joe': f"Average Joe QB ({sel_qb_ovr} OVR) — adds +1.5 to difficulty. Can't paper over mediocre.",
                'Ass':         f"💀 Ass QB ({sel_qb_ovr} OVR) — adds +5.0 to effective difficulty. This whole season is a knife fight.",
            }
            qb_note = _qb_notes.get(sel_qb_tier, "")
            spd_msg = ("Speed advantage softens tough matchups. " if sel_speed >= 10 else f"Limited speed means no margin for error. ") + qb_note
            st.markdown(
                f"<div style='background:#0d1a2e;border-left:4px solid {sel_color};border-radius:8px;padding:10px 14px;margin-bottom:12px;'>"
                f"<span style='color:{sel_color};font-weight:800;'>{html.escape(sel_team)}</span> "
                f"<span style='color:#94a3b8;font-size:0.82rem;'> · {int(sel_speed)} speed guys — {spd_tier} · {spd_msg}</span>"
                f"</div>", unsafe_allow_html=True
            )

            # Timeline chips
            chips_html = "<div style='display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px;'>"
            week_order = []
            for wk in sel_games['week'].tolist():
                if wk not in week_order: week_order.append(wk)
            # Sort: numeric weeks first, then special
            num_wks  = sorted([w for w in week_order if str(w).isdigit()], key=lambda x: int(x))
            spec_wks = [w for w in week_order if not str(w).isdigit()]
            for wk in num_wks + spec_wks:
                wk_games = sel_games[sel_games['week'] == wk]
                for _, g in wk_games.iterrows():
                    r = g['result']
                    ranked = g['opp_ranked']
                    opp_name_full = str(g['opponent'])
                    # Final-rank fallback: opponent was unranked at game time but
                    # ended the season ranked (e.g. BG was #4 at season end)
                    final_rk = _final_rank_lookup.get(opp_name_full)
                    if ranked:
                        opp_rk_label  = f"#{int(g['opp_rank'])}"
                        opp_rk_suffix = ""
                    elif final_rk:
                        opp_rk_label  = f"▸#{final_rk}"   # ended ranked
                        opp_rk_suffix = " fin"
                    else:
                        opp_rk_label  = ""
                        opp_rk_suffix = ""
                    opp    = opp_name_full[:14]
                    margin = f" {'+' if (g['margin'] or 0)>0 else ''}{int(g['margin'])}" if (g['margin'] is not None and not pd.isna(g['margin'])) else ""
                    if r == 'W' and ranked:
                        bg, txt, border = "#14532d", "#4ade80", "#22c55e"
                        icon = "✅"
                    elif r == 'W' and final_rk:
                        # Win vs team that ended ranked — treat as quality win, slightly dimmer green
                        bg, txt, border = "#0f3320", "#34d399", "#10b981"
                        icon = "✅"
                    elif r == 'W':
                        bg, txt, border = "#1e3a5f", "#93c5fd", "#3b82f6"
                        icon = "✓"
                    elif r == 'L' and ranked:
                        bg, txt, border = "#7f1d1d", "#fca5a5", "#ef4444"
                        icon = "💀"
                    elif r == 'L' and final_rk:
                        bg, txt, border = "#5c1a1a", "#fca5a5", "#dc2626"
                        icon = "💀"
                    elif r == 'L':
                        bg, txt, border = "#3b1f1f", "#f87171", "#dc2626"
                        icon = "✗"
                    else:
                        bg, txt, border = "#1a2535", "#6b7280", "#374151"
                        icon = "⏳"
                    wk_label = f"W{wk}" if str(wk).isdigit() else str(wk)
                    chips_html += (
                        f"<div style='background:{bg};border:1px solid {border};border-radius:8px;"
                        f"padding:7px 10px;min-width:90px;cursor:default;'>"
                        f"<div style='font-size:0.65rem;color:#475569;margin-bottom:2px;'>{wk_label} · {g['home_away']}</div>"
                        f"<div style='font-size:0.78rem;font-weight:800;color:{txt};'>{icon} {opp_rk_label}</div>"
                        f"<div style='font-size:0.7rem;color:{txt}99;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:110px;'>{html.escape(opp)}</div>"
                        f"<div style='font-size:0.7rem;color:{txt}cc;font-weight:700;'>{r}{margin}</div>"
                        f"</div>"
                    )
            chips_html += "</div>"
            st.markdown(chips_html, unsafe_allow_html=True)
            st.caption("🟩 Win vs ranked at game time  ·  🟩 ▸ Win vs team that ended ranked  ·  🟦 Win vs unranked  ·  🟥 Loss vs ranked  ·  ◼ Loss vs unranked  ·  ⏳ Pending")

            # ── SECTION 4: QUALITY WIN / STRENGTH OF LOSS BREAKDOWN ──────────
            st.markdown("---")
            st.subheader("🔬 Quality Win Index")

            wins_df   = sel_games[sel_games['result'] == 'W'].copy()
            losses_df = sel_games[sel_games['result'] == 'L'].copy()
            # Include wins vs teams that ended ranked as quality wins too
            wins_df['_final_rk'] = wins_df['opponent'].apply(lambda o: _final_rank_lookup.get(str(o)))
            losses_df['_final_rk'] = losses_df['opponent'].apply(lambda o: _final_rank_lookup.get(str(o)))
            ranked_wins_df  = wins_df[wins_df['opp_ranked']].sort_values('opp_rank')
            fin_rank_wins_df = wins_df[~wins_df['opp_ranked'] & wins_df['_final_rk'].notna()].sort_values('_final_rk')
            ranked_loss_df  = losses_df[losses_df['opp_ranked']].sort_values('opp_rank')
            unrank_loss_df  = losses_df[~losses_df['opp_ranked']]

            total_quality_wins = len(ranked_wins_df) + len(fin_rank_wins_df)
            qw_col, ql_col = st.columns(2)
            with qw_col:
                st.markdown(f"<div style='font-weight:800;color:#4ade80;margin-bottom:8px;'>✅ Quality Wins ({total_quality_wins})</div>", unsafe_allow_html=True)
                if ranked_wins_df.empty and fin_rank_wins_df.empty:
                    st.caption("No ranked wins yet.")
                else:
                    for _, g in ranked_wins_df.iterrows():
                        margin_str = f"+{int(g['margin'])}" if (g['margin'] and not pd.isna(g['margin'])) else ""
                        st.markdown(
                            f"<div style='padding:5px 8px;margin-bottom:4px;background:#0d2010;border-left:3px solid #22c55e;border-radius:5px;font-size:0.8rem;'>"
                            f"<span style='color:#4ade80;font-weight:800;'>#{int(g['opp_rank'])}</span> "
                            f"<span style='color:#d1d5db;'>{html.escape(str(g['opponent']))}</span> "
                            f"<span style='color:#22c55e;font-weight:700;'>{margin_str}</span>"
                            f"<span style='color:#475569;font-size:0.72rem;margin-left:6px;'>{g['home_away']}</span>"
                            f"</div>", unsafe_allow_html=True
                        )
                    for _, g in fin_rank_wins_df.iterrows():
                        margin_str = f"+{int(g['margin'])}" if (g['margin'] and not pd.isna(g['margin'])) else ""
                        fr = int(g['_final_rk'])
                        st.markdown(
                            f"<div style='padding:5px 8px;margin-bottom:4px;background:#0a1f12;border-left:3px solid #10b981;border-radius:5px;font-size:0.8rem;'>"
                            f"<span style='color:#34d399;font-weight:800;'>▸#{fr} fin</span> "
                            f"<span style='color:#d1d5db;'>{html.escape(str(g['opponent']))}</span> "
                            f"<span style='color:#10b981;font-weight:700;'>{margin_str}</span>"
                            f"<span style='color:#475569;font-size:0.72rem;margin-left:6px;'>{g['home_away']} · unranked at game time</span>"
                            f"</div>", unsafe_allow_html=True
                        )

            with ql_col:
                st.markdown(f"<div style='font-weight:800;color:#f87171;margin-bottom:8px;'>💀 Losses ({len(losses_df)})</div>", unsafe_allow_html=True)
                if losses_df.empty:
                    st.caption("No losses — dynasty.")
                else:
                    for _, g in losses_df.iterrows():
                        margin_str = f"{int(g['margin'])}" if (g['margin'] and not pd.isna(g['margin'])) else ""
                        fin_rk = g.get('_final_rk')
                        fin_rk_valid = (fin_rk is not None) and not (isinstance(fin_rk, float) and pd.isna(fin_rk))
                        if g['opp_ranked']:
                            rk_str   = f"#{int(g['opp_rank'])}"
                            rk_color = "#fca5a5"
                            badge    = ""
                        elif fin_rk_valid:
                            rk_str   = f"▸#{int(fin_rk)} fin"
                            rk_color = "#fca5a5"
                            badge    = ""
                        else:
                            rk_str   = "Unranked"
                            rk_color = "#f97316"
                            badge    = "<span style='margin-left:6px;padding:1px 5px;background:#7c2d12;color:#fed7aa;font-size:0.65rem;border-radius:4px;font-weight:800;'>BAD L</span>"
                        st.markdown(
                            f"<div style='padding:5px 8px;margin-bottom:4px;background:#200d0d;border-left:3px solid #ef4444;border-radius:5px;font-size:0.8rem;'>"
                            f"<span style='color:{rk_color};font-weight:800;'>{rk_str}</span> "
                            f"<span style='color:#d1d5db;'>{html.escape(str(g['opponent']))}</span> "
                            f"<span style='color:#ef4444;font-weight:700;'>{margin_str}</span>"
                            f"{badge}"
                            f"<span style='color:#475569;font-size:0.72rem;margin-left:6px;'>{g['home_away']}</span>"
                            f"</div>", unsafe_allow_html=True
                        )

            # ── SECTION 5: CONFERENCE GAUNTLET ───────────────────────────────
            st.markdown("---")
            st.subheader("🏟️ Conference Gauntlet")

            sel_conf_name = _speed_map.get(sel_user, {}).get('conf', '—')
            sel_team_name = USER_TEAMS.get(sel_user, '')
            conf_str      = CONF_STRENGTH.get(sel_conf_name, 0)
            _conf_groups  = {'SEC': {'Nick','Devin','Doug'}, 'B1G': {'Noah','Josh','Mike'}}
            _conf_rivals_users = _conf_groups.get(sel_conf_name, set()) - {sel_user}

            # ── Pull real full conf record from conf_standings_2041.csv ───────
            _from_standings = False
            conf_w = conf_l = conf_ranked_w = 0
            avg_conf_rank = None
            _uvw_games = pd.DataFrame()
            _conf_st   = pd.DataFrame()
            try:
                _conf_st = pd.read_csv('conf_standings_2041.csv')
                _conf_st['TEAM'] = _conf_st['TEAM'].str.strip()
                _conf_st['USER'] = _conf_st['USER'].fillna('')
                _team_row = _conf_st[_conf_st['TEAM'] == sel_team_name]
                if _team_row.empty:
                    raise ValueError("team not in standings")
                _tr    = _team_row.iloc[0]
                conf_w = int(_tr['CONF_W'])
                conf_l = int(_tr['CONF_L'])
                _conf_peers = _conf_st[
                    (_conf_st['CONFERENCE'] == sel_conf_name) &
                    (_conf_st['TEAM'] != sel_team_name)
                ].copy()
                _conf_peers['RANK'] = pd.to_numeric(_conf_peers['RANK'], errors='coerce')
                conf_opp_ranks_s = _conf_peers['RANK'].dropna()
                avg_conf_rank = round(float(conf_opp_ranks_s.mean()), 1) if not conf_opp_ranks_s.empty else None
                _from_standings = True
            except Exception:
                pass

            # User-vs-user matchups for detailed card display
            if not sel_games.empty:
                _uvw_games = sel_games[
                    sel_games['week'].isin(['Conf Champ']) |
                    sel_games['opponent'].apply(
                        lambda opp: any(USER_TEAMS.get(r,'') == opp for r in _conf_rivals_users)
                    )
                ].copy()
                conf_ranked_w = int(
                    ((_uvw_games['result']=='W') & _uvw_games['opp_ranked_final']).sum()
                ) if not _uvw_games.empty else 0

            cg_metrics = [
                {"label": f"🏟️ {sel_conf_name} Record", "value": f"{conf_w}-{conf_l}", "delta": f"Conf strength: {conf_str}"},
                {"label": "💪 Conf Ranked Wins (u-v-u)", "value": str(conf_ranked_w)},
            ]
            if avg_conf_rank:
                cg_metrics.append({"label": "📊 Avg Ranked Conf Opp", "value": f"#{int(avg_conf_rank)}"})
            mobile_metrics(cg_metrics, cols_desktop=3)

            # Full conf standings (all teams, not just user-vs-user)
            if _from_standings and not _conf_st.empty:
                _conf_peers_all = _conf_st[
                    (_conf_st['CONFERENCE'] == sel_conf_name) &
                    (_conf_st['TEAM'] != sel_team_name)
                ].copy()
                _conf_peers_all['RANK'] = pd.to_numeric(_conf_peers_all['RANK'], errors='coerce')
                _conf_peers_all = _conf_peers_all.sort_values(['CONF_W','W'], ascending=False)
                if not _conf_peers_all.empty:
                    st.markdown("<div style='font-size:0.72rem;color:#64748b;margin:10px 0 5px;letter-spacing:.06em;font-weight:700;'>CONFERENCE STANDINGS (full)</div>", unsafe_allow_html=True)
                    cst_html = "<div style='display:flex;flex-direction:column;gap:3px;'>"
                    for _, cr in _conf_peers_all.iterrows():
                        cr_rk   = int(cr['RANK']) if pd.notna(cr['RANK']) else None
                        cr_user = str(cr['USER']).strip() if str(cr['USER']).strip() not in ('','nan') else None
                        rk_str  = f"#{cr_rk}" if cr_rk else "—"
                        rk_col  = "#fbbf24" if cr_rk else "#374151"
                        user_badge = (
                            f"<span style='font-size:0.62rem;padding:1px 4px;background:#1e3a5f;"
                            f"color:#60a5fa;border-radius:3px;margin-left:5px;'>{html.escape(cr_user)}</span>"
                        ) if cr_user else ""
                        cst_html += (
                            f"<div style='display:flex;align-items:center;gap:8px;padding:5px 10px;"
                            f"background:#0a1628;border-radius:5px;font-size:0.78rem;'>"
                            f"<span style='color:{rk_col};font-weight:800;min-width:28px;'>{rk_str}</span>"
                            f"<span style='color:#d1d5db;flex:1;'>{html.escape(str(cr['TEAM']))}{user_badge}</span>"
                            f"<span style='color:#94a3b8;min-width:36px;text-align:right;'>{int(cr['W'])}-{int(cr['L'])}</span>"
                            f"<span style='color:#475569;font-size:0.7rem;min-width:52px;text-align:right;'>({int(cr['CONF_W'])}-{int(cr['CONF_L'])} conf)</span>"
                            f"</div>"
                        )
                    cst_html += "</div>"
                    st.markdown(cst_html, unsafe_allow_html=True)

            # User-vs-user matchup detail
            if not _uvw_games.empty:
                st.markdown("<div style='font-size:0.72rem;color:#64748b;margin:12px 0 5px;letter-spacing:.06em;font-weight:700;'>USER-VS-USER MATCHUPS</div>", unsafe_allow_html=True)
                conf_html = "<div style='display:flex;flex-direction:column;gap:4px;'>"
                for _, cg in _uvw_games.iterrows():
                    r    = cg['result']
                    rk   = f"#{int(cg['effective_rank'])}" if cg['opp_ranked_final'] else "Unranked"
                    mg   = f" ({'+' if (cg['margin'] or 0)>0 else ''}{int(cg['margin'])})" if (cg['margin'] is not None and not pd.isna(cg['margin'])) else ""
                    wk   = str(cg['week'])
                    opp  = str(cg['opponent'])
                    rc   = "#22c55e" if r=='W' else ("#ef4444" if r=='L' else "#6b7280")
                    icon = "✅" if r=='W' else ("❌" if r=='L' else "⏳")
                    cc_badge = "<span style='font-size:0.62rem;padding:1px 5px;background:#7c2d12;color:#fed7aa;border-radius:3px;margin-left:6px;font-weight:800;'>CONF CHAMP</span>" if wk=='Conf Champ' else ""
                    fin_note = "<span style='font-size:0.62rem;color:#64748b;margin-left:3px;'>▸fin</span>" if (cg['opp_ranked_final'] and not cg['opp_ranked']) else ""
                    conf_html += (
                        f"<div style='display:flex;align-items:center;gap:10px;padding:7px 12px;"
                        f"background:#0d1a2e;border-left:3px solid {rc};border-radius:6px;font-size:0.82rem;'>"
                        f"<span style='color:{rc};font-weight:800;min-width:14px;'>{icon}</span>"
                        f"<span style='color:#94a3b8;min-width:60px;'>{wk}</span>"
                        f"<span style='color:{rc};font-weight:700;'>{rk}{fin_note}</span>"
                        f"<span style='color:#d1d5db;flex:1;'>{html.escape(opp)}</span>"
                        f"<span style='color:{rc};font-weight:700;'>{r}{mg}</span>"
                        f"{cc_badge}"
                        f"</div>"
                    )
                conf_html += "</div>"
                st.markdown(conf_html, unsafe_allow_html=True)

            conf_tier_note = {
                'SEC': "SEC — 16-team murder conference.",
                'B1G': "B1G — co-king of the dynasty. 9-game conf schedule.",
                'ACC': "ACC — top-heavy, real teeth at the top.",
            }.get(sel_conf_name, f"{sel_conf_name}.")
            src_note = "Record from conf_standings_2041.csv." if _from_standings else "⚠️ conf_standings_2041.csv not found — user-vs-user fallback only."
            st.caption(f"📌 {conf_tier_note} {src_note} User-vs-user matchups shown individually.")

        else:
            st.info("No schedule data found for this user. Make sure CPUscores_MASTER.csv is up to date.")

    with tabs[0]:
        import os

        st.header("🗞️ Dynasty News")
        st.caption("Your season command center. Power rankings, toughest tests, award watch, injury report, and the rivalries that keep everyone up at night.")

        # ── DATA LOADS ───────────────────────────────────────────────────────
        try:
            cpu_master = pd.read_csv('CPUscores_MASTER.csv')
        except Exception:
            cpu_master = pd.DataFrame()

        try:
            cfp_hist = pd.read_csv('cfp_rankings_history.csv')
            last_yr  = cfp_hist['YEAR'].max()
            last_wk  = cfp_hist[cfp_hist['YEAR'] == last_yr]['WEEK'].max()
            preseason_rank_map = cfp_hist[
                (cfp_hist['YEAR'] == last_yr) & (cfp_hist['WEEK'] == last_wk)
            ].set_index('TEAM')['RANK'].to_dict()
        except Exception:
            preseason_rank_map = {}

        # ════════════════════════════════════════════════════════════════════
        # SECTION 1 — SEASON POWER RANKINGS
        # ════════════════════════════════════════════════════════════════════
        st.subheader("📡 Preseason Power Rankings")
        st.caption("Preseason projections only — ranked on roster strength, speed, recruiting, QB tier, and coaching pedigree. No in-season results, injuries, or CFP rankings baked in.")

        power_board = model_2041.copy()
        for col in ['Preseason PI', 'Preseason Natty Odds', 'Preseason CFP %', 'Power Index', 'Natty Odds', 'CFP Odds']:
            if col not in power_board.columns:
                power_board[col] = 0
        power_board = power_board.sort_values(['Preseason PI', 'Preseason Natty Odds'], ascending=False).reset_index(drop=True)

        rank_icons = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣"]
        rank_labels = ["KING", "CONTENDER", "FRINGE", "BUBBLE", "LONG SHOT", "REBUILDING"]
        rank_colors = ["#f59e0b", "#9ca3af", "#b45309", "#6b7280", "#374151", "#374151"]

        for idx, row in power_board.iterrows():
            team = str(row.get('TEAM', ''))
            user = str(row.get('USER', ''))
            pi    = row.get('Preseason PI', row.get('Power Index', 0))
            natty = row.get('Preseason Natty Odds', row.get('Natty Odds', 0))
            cfp_pct = row.get('Preseason CFP %', row.get('CFP Odds', 0))
            _conf = str(row.get('CONFERENCE', ''))
            _conf_colors = {'SEC': ('#fbbf24','#78350f'), 'B1G': ('#60a5fa','#1e3a5f'), 'ACC': ('#a78bfa','#3b1d6e'), 'Big 12': ('#f97316','#431407')}
            _cc = _conf_colors.get(_conf, ('#6b7280','#1f2937'))
            conf_badge = f"<span style='display:inline-block;margin-left:8px;padding:1px 7px;border-radius:999px;font-size:0.65rem;font-weight:800;background:{_cc[1]};color:{_cc[0]};border:1px solid {_cc[0]}44;'>{html.escape(_conf) if _conf else ''}</span>" if _conf and _conf != 'Other' else ''
            qb_tier = row.get('QB Tier', '—')
            icon    = rank_icons[idx] if idx < len(rank_icons) else "▪️"
            label   = rank_labels[idx] if idx < len(rank_labels) else ""
            lcolor  = rank_colors[idx] if idx < len(rank_colors) else "#374151"
            tc      = get_team_primary_color(team)
            logo_uri = image_file_to_data_uri(get_logo_source(team))
            logo_html = f"<img src='{logo_uri}' style='width:36px;height:36px;object-fit:contain;vertical-align:middle;margin-right:8px;'/>" if logo_uri else "🏈 "

            qb_chip_color = {"Elite": "#22c55e", "Leader": "#3b82f6", "Average Joe": "#f59e0b", "Ass": "#ef4444"}.get(qb_tier, "#6b7280")

            st.markdown(f"""
            <div style='display:flex;align-items:center;background:linear-gradient(90deg,{tc}18,#1f2937 60%);
            border-left:4px solid {tc};border-radius:10px;padding:10px 14px;margin-bottom:8px;gap:12px;'>
              <div style='font-size:1.6rem;min-width:36px;'>{icon}</div>
              {logo_html}
              <div style='flex:1;'>
                <span style='font-size:1.05rem;font-weight:800;color:{tc};'>{html.escape(team)}</span>
                <span style='color:#9ca3af;font-size:0.82rem;margin-left:8px;'>({html.escape(user)})</span>
                <span style='display:inline-block;margin-left:10px;padding:2px 8px;border-radius:999px;
                font-size:0.7rem;font-weight:900;background:{lcolor};color:white;'>{label}</span>
                {conf_badge}
              </div>
              <div style='text-align:right;min-width:200px;'>
                <span style='font-size:0.8rem;color:#d1d5db;'>Pre-PI: <strong style="color:white;">{round(float(pi),1)}</strong></span>
                <span style='font-size:0.8rem;color:#d1d5db;margin-left:14px;'>🏆 <strong style="color:white;">{round(float(natty),1)}%</strong></span>
                <span style='font-size:0.8rem;color:#d1d5db;margin-left:14px;'>Pre-CFP: <strong style="color:white;">{round(float(cfp_pct),1)}%</strong></span>
                <span style='display:inline-block;margin-left:12px;padding:2px 7px;border-radius:999px;
                font-size:0.72rem;font-weight:700;background:{qb_chip_color}33;color:{qb_chip_color};border:1px solid {qb_chip_color};'>QB: {html.escape(str(qb_tier))}</span>
              </div>
            </div>""", unsafe_allow_html=True)

        # ════════════════════════════════════════════════════════════════════
        # SECTION 2 — DYNASTY HEADLINES
        # All metrics use LIVE model columns (Natty Odds, Power Index,
        # CFP Odds, Collapse Risk) — NOT preseason proxies.
        # Game-result headlines are generated directly from scores.csv.
        # ════════════════════════════════════════════════════════════════════
        st.markdown("---")
        st.subheader("📰 Dynasty Headlines")
        st.caption("Auto-generated from live model data and actual game results. Updates as scores are entered.")

        # ── Hardcoded injury notes (update each bowl week) ────────────────
        BOWL_INJURY_NOTES = {
            'San Jose State': ('QB M.Shorter out 27 weeks — backup goes into Bowl 1', 'critical'),
            'Florida State':  ('WR J.Feesago out 20 weeks — gone for the semis run', 'major'),
            'Bowling Green':  ('DT B.Franco out 24 weeks — pass rush depleted for the whole bowl run', 'major'),
            'Florida':        ('LB R.Casey out 14 weeks — defense shorthanded', 'moderate'),
            'USF':            ('RG T.Christmas out 4 weeks — OL depth tested', 'minor'),
            'Texas Tech':     ('LT K.Cota out 2 weeks — likely back for Bowl 2', 'minor'),
        }
        _inj_colors = {'critical': '#ef4444', 'major': '#f97316', 'moderate': '#eab308', 'minor': '#6b7280'}

        headlines = []

        if not model_2041.empty:

            # ── 1. LIVE TITLE FAVORITE — use Natty Odds, not Preseason ─────
            _natty_col = 'Natty Odds' if 'Natty Odds' in model_2041.columns else 'Preseason Natty Odds'
            _pi_col    = 'Power Index' if 'Power Index' in model_2041.columns else 'Preseason PI'
            _cfp_col   = 'CFP Odds'   if 'CFP Odds'    in model_2041.columns else 'Preseason CFP %'

            title_fav      = model_2041.sort_values(_natty_col, ascending=False).iloc[0]
            pi_leader      = model_2041.sort_values(_pi_col,    ascending=False).iloc[0]
            collapse_row   = model_2041.sort_values('Collapse Risk', ascending=False).iloc[0]

            _tf_user  = str(title_fav['USER'])
            _tf_team  = str(title_fav['TEAM'])
            _tf_natty = round(float(title_fav[_natty_col]), 1)
            _tf_ovr   = int(title_fav.get('OVERALL', 0))
            _tf_cfp   = int(title_fav.get('Current CFP Ranking', 99)) if pd.notna(title_fav.get('Current CFP Ranking')) else None
            _tf_cfp_str = f" (CFP #{_tf_cfp})" if _tf_cfp and _tf_cfp <= 25 else ""
            headlines.append(("🏆", "Title Favorite",
                f"<strong>{_tf_user}</strong> ({html.escape(_tf_team)}{_tf_cfp_str}) leads the model with "
                f"<strong>{_tf_natty}% natty odds</strong> and a {_tf_ovr} OVR roster. "
                f"This number is live — it reflects current record, CFP rank, injuries, and schedule résumé, "
                f"not preseason projections."))

            # ── 2. LIVE POWER INDEX LEADER ────────────────────────────────
            _pi_user  = str(pi_leader['USER'])
            _pi_team  = str(pi_leader['TEAM'])
            _pi_val   = round(float(pi_leader[_pi_col]), 1)
            _pi_ovr   = int(pi_leader.get('OVERALL', 0))
            _pi_rec_w = int(pi_leader.get('Current Record Wins', 0))
            _pi_rec_l = int(pi_leader.get('Current Record Losses', 0))
            headlines.append(("⚡", "Power Index Leader",
                f"<strong>{_pi_user}</strong> ({html.escape(_pi_team)}, "
                f"{_pi_rec_w}&ndash;{_pi_rec_l}) owns the highest live Power Index "
                f"(<strong>{_pi_val}</strong>). The PI blends OVR, speed, recruiting, "
                f"CFP rank, current win%, and schedule strength — no preseason assumptions."))

            # ── 3. CFP #1 CALLOUT ─────────────────────────────────────────
            if 'Current CFP Ranking' in model_2041.columns:
                _cfp_ranked = model_2041[pd.to_numeric(
                    model_2041['Current CFP Ranking'], errors='coerce').notna()].copy()
                _cfp_ranked['_cfp_num'] = pd.to_numeric(
                    _cfp_ranked['Current CFP Ranking'], errors='coerce')
                _cfp_ranked = _cfp_ranked[_cfp_ranked['_cfp_num'] <= 25]
                if not _cfp_ranked.empty:
                    _no1 = _cfp_ranked.sort_values('_cfp_num').iloc[0]
                    _no1_user = str(_no1['USER'])
                    _no1_team = str(_no1['TEAM'])
                    _no1_rank = int(_no1['_cfp_num'])
                    _no1_rec_w = int(_no1.get('Current Record Wins', 0))
                    _no1_rec_l = int(_no1.get('Current Record Losses', 0))
                    _no1_natty = round(float(_no1.get(_natty_col, 0)), 1)
                    # Count how many user teams are ranked
                    _n_ranked = len(_cfp_ranked)
                    _rank_list = ", ".join(
                        f"{str(r['USER'])} (#{int(r['_cfp_num'])})"
                        for _, r in _cfp_ranked.sort_values('_cfp_num').iterrows()
                    )
                    headlines.append(("📡", f"CFP #{_no1_rank}: {_no1_user}",
                        f"<strong>{_no1_user}</strong> ({html.escape(_no1_team)}) is the top-ranked user program "
                        f"at <strong>#{_no1_rank}</strong> with a {_no1_rec_w}&ndash;{_no1_rec_l} record and "
                        f"{_no1_natty}% natty odds. All ranked user programs: {_rank_list}."))

            # ── 4. CURRENT SEASON GAME RESULTS ───────────────────────────
            # Pull games from the current dynasty year and generate narratives
            _curr_yr = CURRENT_YEAR
            _yr_scores = scores[scores[meta['yr']] == _curr_yr].copy() if not scores.empty else pd.DataFrame()

            if not _yr_scores.empty:
                # Build per-user bowl record from current year scores
                _bowl_rec = {}  # user -> [wins, losses]
                _game_narratives = []

                for _, _gs in _yr_scores.iterrows():
                    _vu = str(_gs.get('V_User_Final', _gs.get('Vis_User', ''))).strip()
                    _hu = str(_gs.get('H_User_Final', _gs.get('Home_User', ''))).strip()
                    _vt = str(_gs.get('Visitor_Final', _gs.get('Visitor', ''))).strip()
                    _ht = str(_gs.get('Home_Final', _gs.get('Home', ''))).strip()
                    try:
                        _vp = int(_gs.get('V_Pts', _gs.get('Vis Score', 0)))
                        _hp = int(_gs.get('H_Pts', _gs.get('Home Score', 0)))
                    except (ValueError, TypeError):
                        continue
                    _margin = abs(_vp - _hp)
                    _vis_won = _vp > _hp
                    _wu = _vu if _vis_won else _hu
                    _lu = _hu if _vis_won else _vu
                    _wt = _vt if _vis_won else _ht
                    _lt = _ht if _vis_won else _vt
                    _ws = max(_vp, _hp)
                    _ls = min(_vp, _hp)

                    _bowl_rec.setdefault(_wu, [0, 0])
                    _bowl_rec.setdefault(_lu, [0, 0])
                    _bowl_rec[_wu][0] += 1
                    _bowl_rec[_lu][1] += 1
                    _game_narratives.append({
                        'winner_user': _wu, 'loser_user': _lu,
                        'winner_team': _wt, 'loser_team': _lt,
                        'winner_pts': _ws, 'loser_pts': _ls, 'margin': _margin,
                    })

                # Biggest winner this bowl round
                if _bowl_rec:
                    _best_user = max(_bowl_rec, key=lambda u: (_bowl_rec[u][0], -_bowl_rec[u][1]))
                    _bw, _bl = _bowl_rec[_best_user]
                    _best_team_rows = model_2041[model_2041['USER'] == _best_user]
                    _best_team = str(_best_team_rows.iloc[0]['TEAM']) if not _best_team_rows.empty else _best_user
                    if _bw >= 2:
                        headlines.append(("🔥", f"Bowl Week MVP: {_best_user}",
                            f"<strong>{_best_user}</strong> ({html.escape(_best_team)}) went "
                            f"<strong>{_bw}&ndash;{_bl}</strong> this bowl round. "
                            f"That's the kind of statement run that reshapes the natty picture."))
                    elif _bw == 1 and _bl == 0:
                        headlines.append(("✅", f"Bowl Week Win: {_best_user}",
                            f"<strong>{_best_user}</strong> ({html.escape(_best_team)}) picked up a "
                            f"bowl week W to stay alive."))

                # Biggest blowout
                if _game_narratives:
                    _blowout = max(_game_narratives, key=lambda g: g['margin'])
                    if _blowout['margin'] >= 20:
                        headlines.append(("💥", "Blowout of the Round",
                            f"<strong>{_blowout['winner_user']}</strong> put a beating on "
                            f"<strong>{_blowout['loser_user']}</strong> — "
                            f"{html.escape(_blowout['winner_team'])} "
                            f"{_blowout['winner_pts']}&ndash;{_blowout['loser_pts']} "
                            f"(margin: {_blowout['margin']}). "
                            f"{html.escape(_blowout['loser_team'])} never had an answer."))

                # Closest game / thriller
                _close_games = [g for g in _game_narratives if g['margin'] <= 7]
                if _close_games:
                    _thriller = min(_close_games, key=lambda g: g['margin'])
                    headlines.append(("😰", "Thriller of the Round",
                        f"<strong>{_thriller['winner_user']}</strong> survived a gut-punch — "
                        f"{html.escape(_thriller['winner_team'])} "
                        f"{_thriller['winner_pts']}&ndash;{_thriller['loser_pts']} "
                        f"over {html.escape(_thriller['loser_team'])} "
                        f"(margin: {_thriller['margin']}). "
                        f"<strong>{_thriller['loser_user']}</strong> will feel that one."))

                # Users who went 0-X
                _eliminated = [u for u, (w, l) in _bowl_rec.items() if w == 0 and l > 0]
                if _eliminated:
                    for _eu in _eliminated:
                        _et_rows = model_2041[model_2041['USER'] == _eu]
                        _et = str(_et_rows.iloc[0]['TEAM']) if not _et_rows.empty else _eu
                        headlines.append(("🪦", f"Bracket Chaos: {_eu}",
                            f"<strong>{_eu}</strong> ({html.escape(_et)}) went 0&ndash;1 this round. "
                            f"One more loss ends the season."))

            # ── 5. COLLAPSE WATCH ─────────────────────────────────────────
            _cr_user  = str(collapse_row['USER'])
            _cr_team  = str(collapse_row['TEAM'])
            _cr_risk  = int(collapse_row['Collapse Risk'])
            _cr_ovr   = int(collapse_row.get('OVERALL', 0))
            headlines.append(("💀", "Collapse Watch",
                f"<strong>{_cr_user}</strong> ({html.escape(_cr_team)}, {_cr_ovr} OVR) "
                f"carries the highest volatility marker ({_cr_risk}% collapse risk). "
                f"The model sees real downside if things break wrong — "
                f"BCR, depth, and roster age all flagged."))

            # ── 6. INJURY REPORT ─────────────────────────────────────────
            _critical = [(t, n, s) for t, (n, s) in BOWL_INJURY_NOTES.items()
                         if s in ('critical', 'major')]
            if _critical:
                _it, _in, _is = _critical[0]
                _iu = next((u for u, t in USER_TEAMS.items() if t == _it), _it)
                _ic = _inj_colors[_is]
                headlines.append(("🚑", "Injury Report",
                    f"<strong>{_iu}</strong> takes the biggest health hit: "
                    f"<span style='color:{_ic};'>{_in}.</span> "
                    f"The injury model has already docked their title odds. "
                    f"You can't win it all in street clothes."))

            # ── 7. QB HEADLINES ───────────────────────────────────────────
            qb_elite = model_2041[model_2041['QB Tier'] == 'Elite']
            qb_ass   = model_2041[model_2041['QB Tier'] == 'Ass']
            if not qb_elite.empty:
                # List all elite QBs
                _elite_list = ", ".join(
                    f"<strong>{str(r['USER'])}</strong> ({int(r.get('QB OVR', 0))} OVR)"
                    for _, r in qb_elite.sort_values(_natty_col, ascending=False).iterrows()
                )
                headlines.append(("🧠", "Elite QB Alert",
                    f"Elite QBs still alive: {_elite_list}. "
                    f"Every title in modern dynasty football has had one. "
                    f"When your signal-caller can't be stopped, everything opens up."))
            if not qb_ass.empty:
                _ass_list = ", ".join(
                    f"<strong>{str(r['USER'])}</strong> ({int(r.get('QB OVR', 0))} OVR)"
                    for _, r in qb_ass.iterrows()
                )
                headlines.append(("🚨", "QB Disaster Watch",
                    f"{_ass_list} — rolling out an Ass QB situation in bowl season. "
                    f"A good roster can mask a bad quarterback for about three games. "
                    f"That clock is ticking."))

            # ── 8. RECRUITING KING ────────────────────────────────────────
            if 'Recruit Score' in model_2041.columns:
                _rk = model_2041.sort_values('Recruit Score', ascending=False).iloc[0]
                _rk_user = str(_rk['USER'])
                _rk_team = str(_rk['TEAM'])
                _rk_score = round(float(_rk['Recruit Score']), 1)
                headlines.append(("🎯", "Recruiting King",
                    f"<strong>{_rk_user}</strong> ({html.escape(_rk_team)}) is winning the "
                    f"recruiting war ({_rk_score} recruit score). "
                    f"The roster that wins the natty in {_curr_yr + 2} starts with "
                    f"who you're landing right now."))

            # ── 9. SPEED MERCHANTS ────────────────────────────────────────
            if 'Team Speed (90+ Speed Guys)' in model_2041.columns:
                _sk = model_2041.sort_values('Team Speed (90+ Speed Guys)', ascending=False).iloc[0]
                _sk_user  = str(_sk['USER'])
                _sk_team  = str(_sk['TEAM'])
                _sk_num   = int(_sk.get('Team Speed (90+ Speed Guys)', 0))
                _sk_gen   = int(_sk.get('Generational (96+ speed or 96+ Acceleration)', 0))
                _gen_note = (f" including <strong>{_sk_gen} generational freak"
                             f"{'s' if _sk_gen != 1 else ''}</strong>") if _sk_gen > 0 else ""
                headlines.append(("💨", "Speed Merchants",
                    f"<strong>{_sk_user}</strong> ({html.escape(_sk_team)}) leads with "
                    f"<strong>{_sk_num}</strong> players at 90+ speed{_gen_note}. "
                    f"You can scheme around a lot of things. "
                    f"You can't scheme around not being able to catch the other team's guys."))

        # ── Render all headlines ──────────────────────────────────────────
        for _hl_emoji, _hl_title, _hl_body in headlines:
            st.markdown(
                f"<div style='background:#111827;border:1px solid #374151;"
                f"border-radius:10px;padding:12px 16px;margin-bottom:8px;'>"
                f"<span style='font-size:1.1rem;'>{_hl_emoji}</span>"
                f"<strong style='color:#f3f4f6;margin-left:6px;'>"
                f"{html.escape(_hl_title)}:</strong>"
                f"<span style='color:#d1d5db;font-size:0.9rem;margin-left:4px;'>"
                f"{_hl_body}</span></div>",
                unsafe_allow_html=True
            )

        # ════════════════════════════════════════════════════════════════════
        # SECTION 3 — TOUGHEST MATCHUPS
        # ════════════════════════════════════════════════════════════════════
        st.markdown("---")
        st.subheader("💪 Toughest Matchups of the Season")
        st.caption("Based on preseason rankings + in-season rank at time of game. Results populate as games are played. Scheduled games show as upcoming.")

        if cpu_master.empty:
            st.info("Load CPUscores_MASTER.csv to see toughest matchup cards.")
        else:
            in_season_ranks = get_cfp_rankings_snapshot()
            in_season_map   = dict(in_season_ranks[['Team', 'Rank']].values) if in_season_ranks is not None and not in_season_ranks.empty else {}

            def get_game_difficulty(opp, opp_rank_col_val):
                score = 0
                pre = preseason_rank_map.get(opp)
                ins = in_season_map.get(opp)
                if pre: score += max(0, 26 - float(pre)) * 1.5
                if ins and not pd.isna(ins): score += max(0, 26 - float(ins)) * 1.2
                return score, pre, ins

            matchup_cols = st.columns(3)
            col_idx = 0

            for user, team in USER_TEAMS.items():
                team_mask = (cpu_master['Visitor'] == team) | (cpu_master['Home'] == team)
                team_games = cpu_master[team_mask].copy()
                if team_games.empty:
                    continue

                tc = get_team_primary_color(team)
                logo_uri = image_file_to_data_uri(get_logo_source(team))
                logo_html = f"<img src='{logo_uri}' style='width:28px;height:28px;object-fit:contain;vertical-align:middle;'/>" if logo_uri else "🏈"

                def score_game(row):
                    is_home = row['Home'] == team
                    opp = row['Visitor'] if is_home else row['Home']
                    opp_rank_val = row['Visitor Rank'] if is_home else row['Home Rank']
                    diff, pre, ins = get_game_difficulty(opp, opp_rank_val)
                    my_score  = row['Home Score'] if is_home else row['Vis Score']
                    opp_score = row['Vis Score'] if is_home else row['Home Score']
                    location  = 'vs' if is_home else '@'
                    return pd.Series({
                        'opp': opp, 'location': location, 'difficulty': diff,
                        'pre_rank': pre, 'in_rank': ins,
                        'my_score': my_score, 'opp_score': opp_score,
                        'status': row['Status'], 'week': row['Week']
                    })

                ranked_games = team_games.apply(score_game, axis=1).sort_values('difficulty', ascending=False).head(3)

                cards_html = ""
                for _, g in ranked_games.iterrows():
                    opp_str = str(g['opp'])
                    pre_tag = f"#{int(g['pre_rank'])} preseason" if g['pre_rank'] else "unranked preseason"
                    ins_tag = f" · #{int(g['in_rank'])} in-season" if g['in_rank'] and not pd.isna(g['in_rank']) else ""
                    try:
                        _wk = g['week']
                        week_str = f"Wk {int(_wk)}" if str(_wk).isdigit() else str(_wk)
                    except Exception:
                        week_str = str(g['week'])

                    if str(g['status']).upper() == 'FINAL' and pd.notna(g['my_score']) and pd.notna(g['opp_score']):
                        ms, os_ = int(g['my_score']), int(g['opp_score'])
                        won = ms > os_
                        result_color = "#22c55e" if won else "#ef4444"
                        result_label = f"{'W' if won else 'L'} {ms}–{os_}"
                        status_html = f"<span style='font-weight:900;color:{result_color};'>{result_label}</span>"
                    elif str(g['status']).upper() == 'SCHEDULED':
                        status_html = "<span style='color:#f59e0b;font-weight:700;'>UPCOMING ⏳</span>"
                    else:
                        status_html = f"<span style='color:#9ca3af;'>{html.escape(str(g['status']))}</span>"

                    diff_label = "🔥🔥🔥" if g['difficulty'] >= 50 else ("🔥🔥" if g['difficulty'] >= 30 else "🔥")

                    cards_html += f"""
                    <div style='border-left:3px solid {tc};padding:6px 10px;margin-bottom:6px;background:#0f172a;border-radius:6px;'>
                      <div style='display:flex;justify-content:space-between;align-items:center;'>
                        <span style='font-weight:700;color:#f3f4f6;font-size:0.88rem;'>{diff_label} {html.escape(g['location'])} {html.escape(opp_str)}</span>
                        <span style='font-size:0.75rem;color:#9ca3af;'>{week_str}</span>
                      </div>
                      <div style='font-size:0.75rem;color:#9ca3af;margin-top:2px;'>{pre_tag}{ins_tag}</div>
                      <div style='margin-top:4px;'>{status_html}</div>
                    </div>"""

                with matchup_cols[col_idx % 3]:
                    st.markdown(f"""
                    <div style='background:#1f2937;border:1px solid #374151;border-radius:12px;padding:12px;margin-bottom:12px;'>
                      <div style='display:flex;align-items:center;gap:8px;margin-bottom:8px;'>
                        {logo_html}
                        <span style='color:{tc};font-weight:800;font-size:0.95rem;'>{html.escape(team)}</span>
                        <span style='color:#9ca3af;font-size:0.78rem;'>({html.escape(user)})</span>
                      </div>
                      {cards_html}
                    </div>""", unsafe_allow_html=True)
                col_idx += 1

        # ════════════════════════════════════════════════════════════════════
        # SECTION 4 — AWARD WATCH
        # ════════════════════════════════════════════════════════════════════
        st.markdown("---")
        st.subheader("🏆 Award Watch")

        aw_col1, aw_col2 = st.columns(2)

        with aw_col1:
            st.markdown("#### 🏅 Heisman History")
            if heisman is not None and not heisman.empty:
                user_heisman = heisman[heisman['USER'].isin(USER_TEAMS.keys())].copy()
                by_user = user_heisman.groupby('USER').size().reset_index(name='Heisman Count').sort_values('Heisman Count', ascending=False)
                for _, r in by_user.iterrows():
                    u = r['USER']
                    count = r['Heisman Count']
                    winners = user_heisman[user_heisman['USER'] == u][['YEAR','NAME','POS']].sort_values('YEAR', ascending=False)
                    trophy = "🏆" if count >= 3 else ("🥇" if count >= 2 else "🏅")
                    with st.expander(f"{trophy} **{u}** — {count} Heisman{'s' if count > 1 else ''}"):
                        for _, w in winners.iterrows():
                            yr = int(w['YEAR'])
                            # Check if finalists exist for this year — show runner-up placings
                            fin_note = ""
                            if heisman_fin is not None:
                                fin_rows = heisman_fin[
                                    (heisman_fin['YEAR'] == yr) &
                                    (heisman_fin['USER'].isin(USER_TEAMS.keys())) &
                                    (heisman_fin['FINISH'] > 1)
                                ]
                                if not fin_rows.empty:
                                    runner_ups = ", ".join(
                                        f"{r2['NAME']} (#{int(r2['FINISH'])})"
                                        for _, r2 in fin_rows.iterrows()
                                    )
                                    fin_note = f"<span style='color:#6b7280;font-size:0.72rem;'> · Also: {runner_ups}</span>"
                            st.markdown(
                                f"<div style='padding:4px 0;color:#e5e7eb;font-size:0.85rem;'>"
                                f"<span style='color:#fbbf24;font-weight:700;'>{yr}</span>"
                                f"&nbsp;{w['NAME']} <span style='color:#9ca3af;'>({w['POS']})</span>"
                                f"{fin_note}</div>",
                                unsafe_allow_html=True
                            )

            # Finalist callout — users who finished top-5 but didn't win
            if heisman_fin is not None and not heisman_fin.empty:
                runner_df = heisman_fin[
                    (heisman_fin['USER'].isin(USER_TEAMS.keys())) &
                    (heisman_fin['WINNER'] == 'No')
                ].copy()
                if not runner_df.empty:
                    st.markdown("<div style='margin-top:8px;padding:6px 10px;background:#1f2937;border-left:3px solid #f59e0b;border-radius:6px;'>", unsafe_allow_html=True)
                    st.markdown("<span style='color:#f59e0b;font-size:0.78rem;font-weight:700;'>🥈 FINALIST APPEARANCES (no win)</span>", unsafe_allow_html=True)
                    for _, rf in runner_df.sort_values(['USER','YEAR']).iterrows():
                        st.markdown(
                            f"<div style='font-size:0.78rem;color:#d1d5db;padding:2px 0;'>"
                            f"<span style='color:#9ca3af;'>{int(rf['YEAR'])}</span>"
                            f" &nbsp;<strong>{rf['USER']}</strong> — {rf['NAME']} ({rf['POS']}, {rf['TEAM']}) "
                            f"<span style='color:#6b7280;'>#{int(rf['FINISH'])} overall</span></div>",
                            unsafe_allow_html=True
                        )
                    st.markdown("</div>", unsafe_allow_html=True)
            if heisman is None or heisman.empty:
                st.caption("No Heisman data loaded.")

            # Current candidates from roster
            st.markdown("#### 🌟 2041 Heisman Candidates")
            st.caption("Top skill position players by OVR from current rosters.")
            try:
                roster_for_awards = pd.read_csv('cfb26_rosters_full.csv')
                skill_pos = ['QB','HB','WR','TE']
                candidates = roster_for_awards[roster_for_awards['Pos'].isin(skill_pos)].nlargest(6, 'OVR')[['Team','Name','Pos','Year','OVR','SPD']].reset_index(drop=True)

                rows_html = ""
                for _, c in candidates.iterrows():
                    c_team  = str(c.get('Team', ''))
                    c_name  = str(c.get('Name', ''))
                    c_pos   = str(c.get('Pos', ''))
                    c_yr    = str(c.get('Year', ''))
                    c_ovr   = int(c.get('OVR', 0))
                    c_spd   = int(c.get('SPD', 0))
                    c_color = get_team_primary_color(c_team)
                    c_logo  = image_file_to_data_uri(get_logo_source(c_team))
                    logo_img = f"<img src='{c_logo}' style='width:22px;height:22px;object-fit:contain;vertical-align:middle;margin-right:6px;'/>" if c_logo else "🏈 "
                    ovr_color = "#22c55e" if c_ovr >= 90 else ("#f59e0b" if c_ovr >= 85 else "#d1d5db")
                    rows_html += (
                        f"<div style='display:flex;align-items:center;justify-content:space-between;"
                        f"padding:6px 8px;border-bottom:1px solid #1f2937;'>"
                        f"<div style='display:flex;align-items:center;'>"
                        f"{logo_img}"
                        f"<div>"
                        f"<span style='font-weight:700;color:#f3f4f6;font-size:0.85rem;'>{html.escape(c_name)}</span>"
                        f"<span style='color:#9ca3af;font-size:0.75rem;margin-left:5px;'>{c_pos} · {c_yr}</span><br>"
                        f"<span style='color:{c_color};font-size:0.75rem;'>{html.escape(c_team)}</span>"
                        f"</div></div>"
                        f"<div style='text-align:right;'>"
                        f"<span style='font-weight:900;color:{ovr_color};font-size:0.9rem;'>{c_ovr}</span>"
                        f"<span style='color:#6b7280;font-size:0.72rem;margin-left:4px;'>OVR</span><br>"
                        f"<span style='color:#60a5fa;font-size:0.75rem;'>⚡{c_spd} SPD</span>"
                        f"</div></div>"
                    )
                st.markdown(
                    f"<div style='background:#111827;border:1px solid #374151;border-radius:10px;overflow:hidden;'>"
                    f"{rows_html}</div>",
                    unsafe_allow_html=True
                )
            except Exception:
                st.caption("Load cfb26_rosters_full.csv to see current candidates.")

        with aw_col2:
            st.markdown("#### 🎓 Coach of the Year History")
            if coty is not None and not coty.empty:
                user_coty = coty[coty['User'].isin(USER_TEAMS.keys())].copy()
                by_user_coty = user_coty.groupby('User').size().reset_index(name='COTY Count').sort_values('COTY Count', ascending=False)
                for _, r in by_user_coty.iterrows():
                    u = r['User']
                    count = r['COTY Count']
                    wins = user_coty[user_coty['User'] == u][['Year','Coach','Team']].sort_values('Year', ascending=False)
                    trophy = "🏆" if count >= 3 else ("🥇" if count >= 2 else "🎓")
                    with st.expander(f"{trophy} **{u}** — {count} COTY award{'s' if count > 1 else ''}"):
                        for _, w in wins.iterrows():
                            st.markdown(f"<div style='padding:4px 0;color:#e5e7eb;font-size:0.85rem;'><span style='color:#34d399;font-weight:700;'>{int(w['Year'])}</span> &nbsp;{w['Coach']} <span style='color:#9ca3af;'>({w['Team']})</span></div>", unsafe_allow_html=True)
                if user_coty.empty:
                    st.caption("No user COTY wins yet.")
            else:
                st.caption("No COTY data loaded.")

        # ════════════════════════════════════════════════════════════════════
        # SECTION 5 — INJURY REPORT  (last updated: Bowl Week 1, 2041)
        # To update: drop new screenshots in the ISPN chat
        # ════════════════════════════════════════════════════════════════════
        st.markdown("---")
        st.subheader("🚑 Injury Report")
        st.caption("Last updated: Bowl Week 1, 2041. Drop new screenshots in the ISPN chat to refresh.")

        INJURY_DATA = [
            {
                "user": "Mike", "team": "San Jose State", "seed": 8,
                "injuries": [
                    {"name": "M.Shorter",  "pos": "QB",   "ovr": 85, "injury": "Torn Pectoral",       "weeks": 27, "status": "Injured"},
                    {"name": "D.Caplan",   "pos": "LT",   "ovr": 86, "injury": "Broken Collarbone",    "weeks": 4,  "status": "Injured"},
                ]
            },
            {
                "user": "Noah", "team": "Texas Tech", "seed": 2,
                "injuries": [
                    {"name": "K.Cota",     "pos": "LT",   "ovr": 82, "injury": "Knee Cartilage Tear",  "weeks": 2,  "status": "Injured"},
                ]
            },
            {
                "user": "Josh", "team": "USF", "seed": 11,
                "injuries": [
                    {"name": "T.Christmas","pos": "RG",   "ovr": 76, "injury": "Dislocated Hip",        "weeks": 4,  "status": "Injured"},
                ]
            },
            {
                "user": "Devin", "team": "Bowling Green", "seed": 4,
                "injuries": [
                    {"name": "B.Franco",   "pos": "DT",   "ovr": 84, "injury": "Torn Pectoral",         "weeks": 24, "status": "Injured"},
                ]
            },
            {
                "user": "Doug", "team": "Florida", "seed": 24,
                "injuries": [
                    {"name": "S.Ivie",     "pos": "LEDG", "ovr": 80, "injury": "Dislocated Hip",         "weeks": 1,  "status": "Injured"},
                    {"name": "R.Casey",    "pos": "MIKE", "ovr": 87, "injury": "Fractured Shoulder Blade","weeks": 14, "status": "Injured"},
                ]
            },
            {
                "user": "Nick", "team": "Florida State", "seed": 1,
                "injuries": [
                    {"name": "S.Winterswyk","pos": "QB",  "ovr": 80, "injury": "Dislocated Elbow",       "weeks": 3,  "status": "Injured"},
                    {"name": "J.Fe'esago", "pos": "WR",   "ovr": 90, "injury": "Torn Pectoral",           "weeks": 20, "status": "Injured"},
                ]
            },
        ]

        def injury_severity(weeks):
            if weeks >= 20: return ("🔴", "#ef4444", "Season-Ending")
            if weeks >= 8:  return ("🟠", "#f97316", "Long-Term")
            if weeks >= 3:  return ("🟡", "#eab308", "Mid-Term")
            return ("🟢", "#22c55e", "Short-Term")

        # Sort by total injured weeks descending so hardest-hit teams lead
        INJURY_DATA.sort(key=lambda t: sum(p['weeks'] for p in t['injuries']), reverse=True)

        inj_html = "<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px;'>"
        for team_data in INJURY_DATA:
            team   = team_data['team']
            user   = team_data['user']
            seed   = team_data['seed']
            primary = get_team_primary_color(team)
            logo_uri = image_file_to_data_uri(get_logo_source(team))
            logo_html = f"<img src='{logo_uri}' style='width:28px;height:28px;object-fit:contain;vertical-align:middle;margin-right:6px;'/>" if logo_uri else ""

            rows_html = ""
            for p in team_data['injuries']:
                dot, color, label = injury_severity(p['weeks'])
                rows_html += (
                    f"<div style='display:flex;justify-content:space-between;align-items:center;"
                    f"padding:6px 8px;border-bottom:1px solid #1f2937;'>"
                    f"<div>"
                    f"<span style='font-weight:700;color:#f3f4f6;font-size:0.85rem;'>{html.escape(p['name'])}</span>"
                    f"<span style='color:#9ca3af;font-size:0.75rem;margin-left:6px;'>{p['pos']} · {p['ovr']} OVR</span><br>"
                    f"<span style='color:#d1d5db;font-size:0.78rem;'>{html.escape(p['injury'])}</span>"
                    f"</div>"
                    f"<div style='text-align:right;white-space:nowrap;'>"
                    f"<div style='color:{color};font-size:0.72rem;font-weight:700;'>{dot} {label}</div>"
                    f"<div style='color:#6b7280;font-size:0.7rem;'>{p['weeks']} wks</div>"
                    f"</div>"
                    f"</div>"
                )

            inj_html += (
                f"<div style='background:#111827;border:1px solid #374151;border-radius:12px;overflow:hidden;'>"
                f"<div style='background:{primary}22;border-bottom:2px solid {primary};padding:8px 12px;"
                f"display:flex;align-items:center;'>"
                f"{logo_html}"
                f"<div>"
                f"<div style='font-weight:800;color:#f3f4f6;font-size:0.9rem;'>#{seed} {html.escape(team)}</div>"
                f"<div style='color:#9ca3af;font-size:0.72rem;'>{html.escape(user)} · {len(team_data['injuries'])} player{'s' if len(team_data['injuries'])>1 else ''} out</div>"
                f"</div>"
                f"</div>"
                f"{rows_html}"
                f"</div>"
            )
        inj_html += "</div>"
        st.markdown(inj_html, unsafe_allow_html=True)

        # Teams with no reported injuries
        all_users = set(USER_TEAMS.keys())
        reported  = {t['user'] for t in INJURY_DATA}
        healthy   = all_users - reported
        if healthy:
            h_names = ", ".join(f"**{u}**" for u in sorted(healthy))
            st.caption(f"✅ No injuries reported: {h_names}")

        # ════════════════════════════════════════════════════════════════════
        # SECTION 6 — RIVALRY SPOTLIGHT
        # ════════════════════════════════════════════════════════════════════
        st.markdown("---")
        st.subheader("⚔️ Rivalry Spotlight")
        st.caption("Head-to-head history for every user matchup. The best rivalries have scar tissue.")

        rivalry_stats = []
        user_list = list(USER_TEAMS.keys())
        for i in range(len(user_list)):
            for j in range(i + 1, len(user_list)):
                u1, u2 = user_list[i], user_list[j]
                matchup_games = scores[
                    ((scores['Vis_User'] == u1) & (scores['Home_User'] == u2)) |
                    ((scores['Vis_User'] == u2) & (scores['Home_User'] == u1))
                ].copy()
                if matchup_games.empty:
                    continue

                games_played = len(matchup_games)
                margins = pd.to_numeric(
                    abs(pd.to_numeric(matchup_games['Vis Score'], errors='coerce') -
                        pd.to_numeric(matchup_games['Home Score'], errors='coerce')),
                    errors='coerce'
                ).dropna()
                avg_margin = round(float(margins.mean()), 1) if not margins.empty else 14.0

                u1_wins = int(((matchup_games['Vis_User'] == u1) & (pd.to_numeric(matchup_games['Vis Score'], errors='coerce') > pd.to_numeric(matchup_games['Home Score'], errors='coerce'))).sum() +
                              ((matchup_games['Home_User'] == u1) & (pd.to_numeric(matchup_games['Home Score'], errors='coerce') > pd.to_numeric(matchup_games['Vis Score'], errors='coerce'))).sum())
                u2_wins = games_played - u1_wins

                rivalry_key = frozenset([u1, u2])
                rname, rdesc = RIVALRY_NAMES.get(rivalry_key, (f"{u1} vs {u2}", "Two coaches walk into a stadium..."))

                spice = "🌶️🌶️🌶️" if (games_played >= 5 and avg_margin <= 10) else ("🌶️🌶️" if games_played >= 3 else "🌶️")
                rivalry_stats.append({
                    'key': rivalry_key, 'u1': u1, 'u2': u2, 'name': rname, 'desc': rdesc,
                    'games': games_played, 'avg_margin': avg_margin, 'spice': spice,
                    'u1_wins': u1_wins, 'u2_wins': u2_wins,
                    'score': games_played * 3 + max(0, 20 - avg_margin)
                })

        rivalry_stats.sort(key=lambda x: x['score'], reverse=True)

        if not rivalry_stats:
            st.caption("No user vs user games found yet. Check back after Week 1.")
        else:
            riv_cols = st.columns(2)
            for idx, riv in enumerate(rivalry_stats):
                u1, u2 = riv['u1'], riv['u2']
                t1 = USER_TEAMS.get(u1, u1)
                t2 = USER_TEAMS.get(u2, u2)
                c1 = get_team_primary_color(t1)
                c2 = get_team_primary_color(t2)
                logo1_uri = image_file_to_data_uri(get_logo_source(t1))
                logo2_uri = image_file_to_data_uri(get_logo_source(t2))
                logo1_html = f"<img src='{logo1_uri}' style='width:32px;height:32px;object-fit:contain;'/>" if logo1_uri else "🏈"
                logo2_html = f"<img src='{logo2_uri}' style='width:32px;height:32px;object-fit:contain;'/>" if logo2_uri else "🏈"

                leader = u1 if riv['u1_wins'] > riv['u2_wins'] else (u2 if riv['u2_wins'] > riv['u1_wins'] else None)
                leader_color = c1 if leader == u1 else (c2 if leader == u2 else "#9ca3af")
                series_str = f"{riv['u1_wins']}–{riv['u2_wins']}" if leader else f"{riv['u1_wins']}–{riv['u2_wins']} (EVEN)"
                lead_str = f"{html.escape(leader)} leads" if leader else "DEAD EVEN 🤝"

                with riv_cols[idx % 2]:
                    st.markdown(f"""
                    <div style='background:linear-gradient(135deg,{c1}12,#1f2937 50%,{c2}12);
                    border:1px solid #374151;border-radius:14px;padding:14px 16px;margin-bottom:12px;'>
                      <div style='font-size:1.0rem;font-weight:900;color:#f3f4f6;margin-bottom:2px;'>{riv['spice']} {html.escape(riv['name'])}</div>
                      <div style='font-size:0.78rem;color:#9ca3af;margin-bottom:10px;font-style:italic;'>{html.escape(riv['desc'])}</div>
                      <div style='display:flex;align-items:center;justify-content:space-between;'>
                        <div style='display:flex;align-items:center;gap:6px;'>
                          {logo1_html}
                          <div>
                            <div style='color:{c1};font-weight:700;font-size:0.85rem;'>{html.escape(u1)}</div>
                            <div style='color:#9ca3af;font-size:0.72rem;'>{html.escape(t1)}</div>
                          </div>
                        </div>
                        <div style='text-align:center;padding:0 12px;'>
                          <div style='font-size:1.2rem;font-weight:900;color:#f3f4f6;'>{series_str}</div>
                          <div style='font-size:0.7rem;color:{leader_color};font-weight:700;'>{lead_str}</div>
                          <div style='font-size:0.68rem;color:#6b7280;'>{riv['games']} games · avg margin {riv['avg_margin']} pts</div>
                        </div>
                        <div style='display:flex;align-items:center;gap:6px;'>
                          <div style='text-align:right;'>
                            <div style='color:{c2};font-weight:700;font-size:0.85rem;'>{html.escape(u2)}</div>
                            <div style='color:#9ca3af;font-size:0.72rem;'>{html.escape(t2)}</div>
                          </div>
                          {logo2_html}
                        </div>
                      </div>
                    </div>""", unsafe_allow_html=True)



    # --- WHO'S IN? ---
    with tabs[2]:
        st.header("🏆 Who's In? | CFP Bubble Watch")
        st.caption("Built from your uploaded CFP ranking screenshots, then sharpened with this app's SOS, resume, QB, recruiting, and roster-strength model. Current CFP standards are assumed: five highest-ranked conference champs get in, plus seven at-larges, with the top four seeds earning byes.")

        # ── DATA FRESHNESS BANNER ────────────────────────────────────────────
        try:
            _cfp_hist_check = pd.read_csv('cfp_rankings_history.csv')
            if not _cfp_hist_check.empty:
                _ly = _cfp_hist_check['YEAR'].max()
                _lw = _cfp_hist_check.loc[_cfp_hist_check['YEAR'] == _ly, 'WEEK'].max()
                _snap_size = len(_cfp_hist_check[(_cfp_hist_check['YEAR'] == _ly) & (_cfp_hist_check['WEEK'] == _lw)])
                st.success(f"📡 **Live data** — showing Week {int(_lw)}, {int(_ly)} rankings ({_snap_size} teams). Update `cfp_rankings_history.csv` each week to keep this current.")
            else:
                st.warning("⚠️ `cfp_rankings_history.csv` is empty — showing fallback hardcoded rankings. Add rows to the CSV to go live.")
        except Exception:
            st.warning("⚠️ `cfp_rankings_history.csv` not found — showing fallback hardcoded Week 9 rankings. Push the CSV to your repo to go live.")

        cfp_rankings = get_cfp_rankings_snapshot()
        cfp_board = build_cfp_bubble_board(cfp_rankings, model_2041)

        # Project the field by Make CFP %, then seed the 12-team bracket with a separate seed score.
        projected_field = cfp_board.sort_values(['CFP Make %', 'Bye %', 'Committee Score', 'Rank'], ascending=[False, False, False, True]).head(12).copy()
        projected_field = compute_projected_seed_score(projected_field)
        projected_field = projected_field.sort_values(['Seed Score', 'CFP Make %', 'Bye %', 'Rank'], ascending=[False, False, False, True]).reset_index(drop=True)
        projected_field['Projected Seed'] = range(1, len(projected_field) + 1)

        # Push the corrected projected seeds back onto the full board so the main table matches the bracket table.
        cfp_board = compute_projected_seed_score(cfp_board)
        cfp_board['Projected Seed'] = np.nan
        seed_map = projected_field.set_index('Team')['Projected Seed'].to_dict()
        cfp_board['Projected Seed'] = cfp_board['Team'].map(seed_map)

        first_four_out = cfp_board[~cfp_board['Team'].isin(projected_field['Team'])].sort_values(['CFP Make %', 'Seed Score', 'Rank'], ascending=[False, False, True]).head(4).copy()

        mobile_metrics([
            {"label": "🔒 Projected Locks",  "value": str(int((cfp_board['CFP Make %'] >= 92).sum()))},
            {"label": "📍 Last Team In",      "value": f"#{int(projected_field.iloc[-1]['Rank'])} {projected_field.iloc[-1]['Team']}"},
            {"label": "😬 First Team Out",    "value": f"#{int(first_four_out.iloc[0]['Rank'])} {first_four_out.iloc[0]['Team']}"},
            {"label": "🅱️ Best Bye Shot",     "value": f"{projected_field.sort_values('Bye %', ascending=False).iloc[0]['Team']}", "delta": format_pct(projected_field['Bye %'].max(), 1)},
        ])

        st.subheader('Projected CFP Field')
        render_cfp_table(cfp_board)

        # ── PLAYOFF BRACKET ──────────────────────────────────────────────────
        st.subheader('Playoff Bracket')

        st.info("📸 **To use the official bracket:** enter the seeds below and hit Lock In. It stays saved for the rest of this season — no re-entry needed each visit.")

        with st.expander("✏️ Enter Official CFP Bracket", expanded=False):
            st.caption("Seed #1–4 get first-round byes. Leave teams blank to fall back to projections.")
            MANUAL_SLOTS = [
                (1,"Florida State","12-1"),(2,"Texas Tech","12-1"),
                (3,"Rapid City","12-1"),(4,"Bowling Green","12-1"),
                (5,"Clemson","12-1"),(6,"Texas A&M","10-2"),
                (7,"Alabaster","10-3"),(8,"San Jose State","10-4"),
                (9,"Texas","11-2"),(10,"Georgia Tech","11-2"),
                (11,"USF","10-2"),(12,"San Diego State","12-1"),
            ]
            st.markdown("**Byes (Seeds 1–4)**")
            bye_cols = st.columns(2)
            manual_teams = []
            for idx, (seed, def_team, def_rec) in enumerate(MANUAL_SLOTS[:4]):
                with bye_cols[idx % 2]:
                    st.markdown(f"<div style='color:#4ade80;font-weight:800;font-size:0.8rem;'>#{seed} — BYE</div>", unsafe_allow_html=True)
                    t = st.text_input("Team", value=def_team, key=f"manual_team_{seed}", label_visibility="collapsed")
                    r = st.text_input("Record", value=def_rec, key=f"manual_rec_{seed}", label_visibility="collapsed")
                    if t.strip():
                        manual_teams.append({"seed": seed, "team": t.strip(), "record": r.strip()})

            st.markdown("**First Round (Seeds 5–12)**")
            fr_matchups = [(5,12),(6,11),(7,10),(8,9)]
            slot_map = {s: (t, r) for s, t, r in MANUAL_SLOTS}
            for seed_a, seed_b in fr_matchups:
                mc1, mc2, mc3 = st.columns([5, 1, 5])
                with mc1:
                    def_a_t, def_a_r = slot_map[seed_a]
                    st.markdown(f"<div style='color:#60a5fa;font-weight:700;font-size:0.78rem;'>#{seed_a}</div>", unsafe_allow_html=True)
                    ta = st.text_input("Team", value=def_a_t, key=f"manual_team_{seed_a}", label_visibility="collapsed")
                    ra = st.text_input("Record", value=def_a_r, key=f"manual_rec_{seed_a}", label_visibility="collapsed")
                    if ta.strip(): manual_teams.append({"seed": seed_a, "team": ta.strip(), "record": ra.strip()})
                mc2.markdown("<div style='text-align:center;padding-top:1.4rem;color:#6b7280;font-weight:700;'>vs</div>", unsafe_allow_html=True)
                with mc3:
                    def_b_t, def_b_r = slot_map[seed_b]
                    st.markdown(f"<div style='color:#60a5fa;font-weight:700;font-size:0.78rem;'>#{seed_b}</div>", unsafe_allow_html=True)
                    tb = st.text_input("Team", value=def_b_t, key=f"manual_team_{seed_b}", label_visibility="collapsed")
                    rb = st.text_input("Record", value=def_b_r, key=f"manual_rec_{seed_b}", label_visibility="collapsed")
                    if tb.strip(): manual_teams.append({"seed": seed_b, "team": tb.strip(), "record": rb.strip()})

            use_manual = st.button("📋 Lock In Official Bracket", key="use_manual_bracket", type="primary")

        # ── BRACKET PERSISTENCE (CSV-backed) ────────────────────────────────
        # Reads/writes official_bracket.csv in the repo root.
        # Survives server restarts. Keyed by CURRENT_YEAR — auto-clears next season.
        _BRACKET_CSV = 'official_bracket.csv'

        def load_saved_bracket(year):
            try:
                _b = pd.read_csv(_BRACKET_CSV)
                _b = _b[_b['YEAR'] == year]
                if len(_b) >= 8:
                    return [{'seed': int(r['SEED']), 'team': str(r['TEAM']), 'record': str(r['RECORD'])}
                            for _, r in _b.iterrows()]
            except Exception:
                pass
            return None

        def save_official_bracket(year, teams):
            try:
                # Load existing, drop this year, append new
                try:
                    _existing = pd.read_csv(_BRACKET_CSV)
                    _existing = _existing[_existing['YEAR'] != year]
                except Exception:
                    _existing = pd.DataFrame(columns=['YEAR','SEED','TEAM','RECORD'])
                _new_rows = pd.DataFrame([
                    {'YEAR': year, 'SEED': t['seed'], 'TEAM': t['team'], 'RECORD': t['record']}
                    for t in teams
                ])
                _out = pd.concat([_existing, _new_rows], ignore_index=True).sort_values(['YEAR','SEED'])
                _out.to_csv(_BRACKET_CSV, index=False)
                return True
            except Exception as e:
                st.warning(f"⚠️ Couldn't save bracket to CSV: {e}")
                return False

        if use_manual and len(manual_teams) >= 8:
            if save_official_bracket(CURRENT_YEAR, manual_teams):
                st.session_state[f"official_bracket_{CURRENT_YEAR}"] = manual_teams

        # Try session_state first (fast), fall back to CSV (survives restarts)
        _saved_teams = st.session_state.get(f"official_bracket_{CURRENT_YEAR}")
        if not _saved_teams:
            _saved_teams = load_saved_bracket(CURRENT_YEAR)
            if _saved_teams:
                st.session_state[f"official_bracket_{CURRENT_YEAR}"] = _saved_teams

        bracket_field = None
        if _saved_teams:
            bracket_field = build_bracket_field_from_screenshot(_saved_teams, cfp_board)

        if bracket_field is not None and not bracket_field.empty:
            st.success("📋 Showing **official bracket** — saved to repo. Persists across sessions. Re-enter above to update.")
            render_playoff_bracket(bracket_field)
        else:
            st.caption("📊 Showing **projected bracket** — enter the official field above once the CFP announces.")
            render_playoff_bracket(projected_field)

        st.subheader('First Four Out')
        render_first_four_out(first_four_out)

        st.subheader('CFP Chaos Simulator')
        sim_team = st.selectbox('Pick a team to stress-test', cfp_board.sort_values('Rank')['Team'].tolist(), key='cfp_sim_team')
        sim_scenario = st.selectbox('Scenario', ['Win next game', 'Win over Top-12 team', 'Lose to ranked team', 'Lose to unranked team'], key='cfp_sim_scenario')
        sim_row = cfp_board[cfp_board['Team'] == sim_team].iloc[0]
        sim_result = simulate_cfp_chaos(sim_row, sim_scenario, cfp_board)

        mobile_metrics([
            {"label": "Current CFP %",    "value": format_pct(sim_row['CFP Make %'], 1),
             "delta": f"{sim_result['CFP Make %'] - sim_row['CFP Make %']:+.1f}%"},
            {"label": "Current Bye %",    "value": format_pct(sim_row['Bye %'], 1),
             "delta": f"{sim_result['Bye %'] - sim_row['Bye %']:+.1f}%"},
            {"label": "New Record",       "value": sim_result['Record'], "delta_color": "off"},
            {"label": "Projected Rank",   "value": f"#{int(sim_result['Rank'])}",
             "delta": f"{int(sim_row['Rank']) - int(sim_result['Rank']):+d} spots", "delta_color": "inverse"},
        ])

        if sim_scenario == 'Lose to unranked team':
            st.warning(f"{sim_team} would set fire to a lot of goodwill with an unranked loss. The model treats that as a straight-up committee trust killer.")
        elif sim_scenario == 'Lose to ranked team':
            st.info(f"A ranked loss hurts {sim_team}, but it usually doesn't nuke the whole damn résumé unless the record was already hanging by a thread.")
        elif sim_scenario == 'Win over Top-12 team':
            st.success(f"That's a résumé steroid shot. A top-12 win would give {sim_team} a real committee argument and bye-path juice.")
        else:
            st.success(f"A clean win keeps {sim_team} moving and protects the committee relationship. No chaos, no stupid questions.")
    # --- RECRUITING RANKINGS ---
    with tabs[7]:
        st.header("🏈 Recruiting Rankings")
        st.caption("Current season screenshot board appears first. Heat Index uses the last four class ranks from recruiting.csv, weighted toward the most recent years: lower weighted average rank = hotter score. Pipeline Score blends that heat with blue-chip ratio, current team speed, overall roster quality, improvement, and freak count.")

        current_recruiting = get_current_recruiting_snapshot()
        st.subheader("Current Season National Recruiting Snapshot")
        st.caption("This section is built from the recruiting ranking screenshots currently loaded into the app.")
        render_recruiting_snapshot_table(current_recruiting.head(25))

        if recruiting_board.empty:
            st.info("No recruiting board data could be built from the current recruiting file.")
        else:
            st.subheader("User Dynasty Recruiting Board")
            render_recruiting_table(recruiting_board)

            st.subheader("Full Historical Recruiting Table")
            hist_cols = [c for c in rec.columns if c in ['USER','Teams'] or str(c).isdigit()]
            st.dataframe(rec[hist_cols], hide_index=True, use_container_width=True)

            st.subheader("Recruiting Spotlight")
            spotlight_team = st.selectbox("Choose a class to spotlight", recruiting_board['TEAM'].tolist(), key='recruit_spotlight')
            sp = recruiting_board[recruiting_board['TEAM'] == spotlight_team].iloc[0]
            render_logo(sp['Logo'], width=72)
            st.markdown(f"### {sp['TEAM']} | {sp['USER']}")
            mobile_metrics([
                {"label": "Recent Classes",    "value": str(sp['Recent Cycle'])},
                {"label": "Weighted Avg Rank", "value": str(sp['Weighted Avg Rank']) if not pd.isna(sp['Weighted Avg Rank']) else "—"},
                {"label": "Heat Index",        "value": str(sp['Heat Index'])},
                {"label": "Pipeline Score",    "value": str(sp['Pipeline Score'])},
                {"label": "Speed Recruiter",   "value": str(sp['Speed Recruiter Index'])},
                {"label": "Blue Chip %",       "value": f"{sp['Blue Chip %']}%"},
            ])
            st.markdown(f"**Class Tier:** {sp['Class Tier']}  \n**Trajectory:** {sp['Trajectory']}")
            st.info(sp['Recruiting Blurb'])

    # --- H2H MATRIX ---
    with tabs[8]:
        st.header("⚔️ Head-to-Head Matrix")

        st.subheader("Full H2H Matrix")
        st.dataframe(h2h_df, hide_index=True, use_container_width=True)

        st.subheader("Rivalry Meter")
        if not rivalry_df.empty:
            st.dataframe(
                rivalry_df[['Matchup', 'Games', 'Avg Margin', 'Rivalry Score']].sort_values(['Rivalry Score', 'Games'], ascending=[False, False]),
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("No rivalry data available yet.")

        selected_user = st.selectbox("Select a user for H2H drilldown", all_users, key="h2h_select")
        drill = []
        for opp in all_users:
            if opp == selected_user:
                continue
            matchup = h2h_df[h2h_df['User'] == selected_user][opp].iloc[0]
            diff = h2h_heat.loc[selected_user, opp]
            games = 0
            wins = 0
            losses = 0
            if matchup != "-":
                parts = str(matchup).split('-')
                if len(parts) == 2:
                    wins = int(parts[0])
                    losses = int(parts[1])
                    games = wins + losses
            drill.append({
                'Opponent': opp,
                'Record': matchup,
                'Games': games,
                'Net Edge': diff
            })
        st.dataframe(pd.DataFrame(drill).sort_values(['Games', 'Net Edge'], ascending=[False, False]), hide_index=True, use_container_width=True)

    # --- SEASON RECAP ---
    with tabs[3]:
        st.header("📺 Season Recap")
        sel_year = st.selectbox("Select Season", years, key="season_year")
        y_data = scores[scores[meta['yr']] == sel_year].copy()

        # ── Build user→team map for this season from scores ──────────────────
        _yr_team_map = {}
        for _, _sr in y_data.iterrows():
            _vu = str(_sr.get('V_User_Final', '')).strip()
            _hu = str(_sr.get('H_User_Final', '')).strip()
            if _vu.upper() not in ('CPU', 'NAN', ''):
                _yr_team_map[_vu] = str(_sr.get('Visitor_Final', '')).strip()
            if _hu.upper() not in ('CPU', 'NAN', ''):
                _yr_team_map[_hu] = str(_sr.get('Home_Final', '')).strip()

        def _yr_logo(user):
            team = _yr_team_map.get(str(user), '')
            return image_file_to_data_uri(get_logo_source(team)) if team else None

        def _yr_color(user):
            team = _yr_team_map.get(str(user), '')
            return get_team_primary_color(team) if team else '#64748b'

        def _logo_tag(user, size=36):
            uri = _yr_logo(user)
            team = _yr_team_map.get(str(user), '')
            if uri:
                return f"<img src='{uri}' style='width:{size}px;height:{size}px;object-fit:contain;flex-shrink:0;' title='{html.escape(team)}'/>"
            return f"<span style='font-size:{size*0.6:.0f}px;'>🏈</span>"

        champ_row    = champs[champs['YEAR'] == sel_year]
        heisman_row  = heisman[heisman[meta['h_yr']] == sel_year]
        coty_row     = coty[coty[meta['c_yr']] == sel_year]

        # ── AWARDS BANNER ─────────────────────────────────────────────────────
        award_champ   = "TBD"
        champ_team    = champ_user = ""
        heisman_player = heisman_team = heisman_user = ""
        coty_coach     = coty_team   = coty_user    = ""

        if not champ_row.empty:
            champ_team = champ_row.iloc[0]['Team']
            champ_user = str(champ_row.iloc[0]['user'])
            award_champ = champ_team
        if not heisman_row.empty:
            heisman_player = str(heisman_row.iloc[0][meta['h_player']])
            heisman_team   = str(heisman_row.iloc[0][meta['h_school']])
            heisman_user   = str(heisman_row.iloc[0].get('USER', heisman_row.iloc[0].get('User', '')))
        if not coty_row.empty:
            coty_coach = str(coty_row.iloc[0][meta['c_coach']])
            coty_team  = str(coty_row.iloc[0][meta['c_school']])
            coty_user  = str(coty_row.iloc[0].get('User', coty_row.iloc[0].get('USER', '')))

        def _award_logo_tag(team, size=48):
            uri = image_file_to_data_uri(get_logo_source(team)) if team else None
            if uri:
                return f"<img src='{uri}' style='width:{size}px;height:{size}px;object-fit:contain;flex-shrink:0;'/>"
            return f"<span style='font-size:{int(size*0.55)}px;'>🏈</span>"

        _champ_color = get_team_primary_color(champ_team) if champ_team else '#fbbf24'
        _heis_color  = get_team_primary_color(heisman_team) if heisman_team else '#f59e0b'
        _coty_color  = get_team_primary_color(coty_team) if coty_team else '#34d399'

        def _award_card(accent, logo_tag, badge, line1, line2, line3=''):
            sub = f"<div style='font-size:0.68rem;color:#64748b;margin-top:1px;'>{html.escape(line3)}</div>" if line3 else ''
            return (
                f"<div style='background:linear-gradient(135deg,{accent}22,#0f172a);"
                f"border:1px solid {accent}55;border-radius:12px;padding:14px 16px;"
                f"display:flex;align-items:center;gap:12px;'>"
                f"{logo_tag}"
                f"<div style='min-width:0;'>"
                f"<div style='font-size:0.6rem;color:#94a3b8;letter-spacing:.08em;font-weight:700;margin-bottom:3px;'>{badge}</div>"
                f"<div style='font-weight:900;color:{accent};font-size:0.92rem;line-height:1.25;"
                f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{html.escape(line1)}</div>"
                f"<div style='font-size:0.72rem;color:#94a3b8;margin-top:1px;'>{html.escape(line2)}</div>"
                f"{sub}"
                f"</div></div>"
            )

        awards_html = (
            "<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));"
            "gap:10px;margin-bottom:16px;'>"
            + _award_card(_champ_color, _award_logo_tag(champ_team, 52),
                          "🏆 CHAMPION", award_champ or "TBD", champ_user)
            + _award_card(_heis_color, _award_logo_tag(heisman_team, 52),
                          "🏅 HEISMAN", heisman_player or "TBD",
                          heisman_team, heisman_user)
            + _award_card(_coty_color, _award_logo_tag(coty_team, 52),
                          "👔 COACH OF THE YEAR", coty_coach or "TBD",
                          coty_team, coty_user)
            + "</div>"
        )
        st.markdown(awards_html, unsafe_allow_html=True)

        if not y_data.empty:
            user_games = y_data[
                (y_data['V_User_Final'].astype(str).str.upper() != 'CPU') &
                (y_data['H_User_Final'].astype(str).str.upper() != 'CPU') &
                (y_data['V_User_Final'] != y_data['H_User_Final'])
            ].copy()
            all_user_rows = y_data[
                (y_data['V_User_Final'].astype(str).str.upper() != 'CPU') |
                (y_data['H_User_Final'].astype(str).str.upper() != 'CPU')
            ].copy()

            # ── SEASON IN NUMBERS ─────────────────────────────────────────────
            avg_m       = round(y_data['Margin'].mean(), 1)
            total_games = len(y_data)
            avg_pts     = round(y_data['Total Points'].mean(), 1)
            blowouts    = int((y_data['Margin'] >= 28).sum())
            nail_biters = int((y_data['Margin'] <= 7).sum())
            st.markdown(f"""
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px;margin-bottom:16px;">
              {_mini_stat_chip('Games Logged', str(total_games), '#60a5fa')}
              {_mini_stat_chip('Avg Margin', str(avg_m), '#f59e0b')}
              {_mini_stat_chip('Avg Total Pts', str(avg_pts), '#34d399')}
              {_mini_stat_chip('Blowouts (28+)', str(blowouts), '#f87171')}
              {_mini_stat_chip('Nail-Biters (≤7)', str(nail_biters), '#a78bfa')}
              {_mini_stat_chip('User Battles', str(len(user_games)), '#fb923c')}
            </div>""", unsafe_allow_html=True)

            # ── USER RECORDS THIS SEASON ──────────────────────────────────────
            st.markdown("#### 📋 User Records This Season")
            _user_rec_rows = []
            for _u in sorted(_yr_team_map.keys()):
                _u_games = all_user_rows[
                    (all_user_rows['V_User_Final']==_u) |
                    (all_user_rows['H_User_Final']==_u)
                ]
                _w = int((((_u_games['V_User_Final']==_u) & (_u_games['V_Pts']>_u_games['H_Pts'])) |
                           ((_u_games['H_User_Final']==_u) & (_u_games['H_Pts']>_u_games['V_Pts']))).sum())
                _l = len(_u_games) - _w
                _ppg = round(_u_games.apply(
                    lambda r: r['V_Pts'] if r['V_User_Final']==_u else r['H_Pts'], axis=1).mean(), 1)
                _tc = _yr_color(_u)
                _lt = _logo_tag(_u, 28)
                _team_name = _yr_team_map.get(_u,'?')
                _user_rec_rows.append((_w, _u, _team_name, _tc, _lt, _w, _l, _ppg))

            _user_rec_rows.sort(key=lambda x: -x[0])
            for rank_i, (_, _u, _tname, _tc, _lt, _w, _l, _ppg) in enumerate(_user_rec_rows):
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:10px;"
                    f"background:#0a1628;border-left:4px solid {_tc};"
                    f"border-radius:8px;padding:8px 12px;margin-bottom:5px;'>"
                    f"<span style='color:#475569;font-size:0.72rem;min-width:18px;'>"
                    f"#{rank_i+1}</span>{_lt}"
                    f"<div style='flex:1;min-width:0;'>"
                    f"<div style='font-weight:800;color:{_tc};font-size:0.88rem;"
                    f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>"
                    f"{html.escape(_tname)}</div>"
                    f"<div style='font-size:0.65rem;color:#64748b;'>"
                    f"{html.escape(_u)}</div></div>"
                    f"<div style='text-align:right;'>"
                    f"<div style='font-weight:900;color:#f1f5f9;font-size:0.95rem;'>"
                    f"{_w}&ndash;{_l}</div>"
                    f"<div style='font-size:0.65rem;color:#64748b;'>{_ppg} ppg</div>"
                    f"</div></div>",
                    unsafe_allow_html=True
                )

            # ── GAME OF THE YEAR ──────────────────────────────────────────────
            if not user_games.empty:
                goty = user_games.loc[user_games['Margin'].idxmin()]
                if goty['V_Pts'] > goty['H_Pts']:
                    wu, lu = goty['V_User_Final'], goty['H_User_Final']
                    wt, lt = goty['Visitor_Final'], goty['Home_Final']
                    w_pts, l_pts = int(goty['V_Pts']), int(goty['H_Pts'])
                else:
                    wu, lu = goty['H_User_Final'], goty['V_User_Final']
                    wt, lt = goty['Home_Final'], goty['Visitor_Final']
                    w_pts, l_pts = int(goty['H_Pts']), int(goty['V_Pts'])
                roast_lines = [
                    f"{lu} snatched defeat from the jaws of competence.",
                    f"{lu} turned a pressure moment into performance art.",
                    f"{lu} got all the way to the finish line and face-planted in front of the cameras."
                ]
                roast = roast_lines[int(goty['Margin']) % 3]
                _wc, _lc = _yr_color(wu), _yr_color(lu)
                _wl, _ll = _logo_tag(wu, 40), _logo_tag(lu, 40)
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#0f172a,#1e293b);border:1px solid #fbbf2444;
                            border-radius:14px;padding:16px;margin-bottom:14px;">
                  <div style="font-size:0.62rem;color:#fbbf24;letter-spacing:.1em;font-weight:700;margin-bottom:10px;">🏟️ GAME OF THE YEAR — CLOSEST USER BATTLE</div>
                  <div style="display:flex;align-items:center;justify-content:center;gap:12px;flex-wrap:wrap;">
                    <div style="display:flex;flex-direction:column;align-items:center;gap:4px;min-width:80px;">
                      {_wl}
                      <span style="font-weight:900;color:{_wc};font-size:0.82rem;text-align:center;">{html.escape(wt)}</span>
                      <span style="font-size:0.65rem;color:#64748b;">{html.escape(wu)}</span>
                    </div>
                    <div style="text-align:center;">
                      <div style="font-size:1.6rem;font-weight:900;color:#f1f5f9;">{w_pts} – {l_pts}</div>
                      <div style="font-size:0.68rem;color:#94a3b8;">margin: {int(goty['Margin'])}</div>
                    </div>
                    <div style="display:flex;flex-direction:column;align-items:center;gap:4px;min-width:80px;">
                      {_ll}
                      <span style="font-weight:900;color:{_lc};font-size:0.82rem;text-align:center;">{html.escape(lt)}</span>
                      <span style="font-size:0.65rem;color:#64748b;">{html.escape(lu)}</span>
                    </div>
                  </div>
                  <div style="font-size:0.75rem;color:#94a3b8;margin-top:10px;text-align:center;font-style:italic;">{html.escape(roast)}</div>
                </div>""", unsafe_allow_html=True)

            # ── FUN STAT + NARRATIVE ──────────────────────────────────────────
            st.caption(f"📊 Fun stat: {infer_best_fun_stat(y_data)}")

            # ── HEAD-TO-HEAD USER MATCHUPS ────────────────────────────────────
            if not user_games.empty:
                st.markdown("#### ⚔️ User vs User Results")
                _gtype_map = {}
                for _, _gr in y_data.iterrows():
                    _key = (str(_gr.get('Visitor_Final','')), str(_gr.get('Home_Final','')))
                    _gt = 'Regular Season'
                    if str(_gr.get('Natty Game','no')).upper() == 'YES': _gt = '🏆 National Championship'
                    elif str(_gr.get('CFP','no')).lower() == 'yes':      _gt = '🎯 CFP'
                    elif str(_gr.get('Conf Title','no')).lower() == 'yes': _gt = '🏅 Conf Title'
                    elif str(_gr.get('Bowl','no')).lower() == 'yes':      _gt = '🎳 Bowl'
                    _gtype_map[_key] = _gt

                _games_sorted = user_games.sort_values('Margin')
                for _, _g in _games_sorted.iterrows():
                    _vu2, _hu2 = str(_g['V_User_Final']), str(_g['H_User_Final'])
                    _vt2, _ht2 = str(_g['Visitor_Final']), str(_g['Home_Final'])
                    _vp, _hp   = int(_g['V_Pts']), int(_g['H_Pts'])
                    _v_won     = _vp > _hp
                    _vc = _yr_color(_vu2); _hc = _yr_color(_hu2)
                    _vl = _logo_tag(_vu2, 28); _hl = _logo_tag(_hu2, 28)
                    _vw = "font-weight:900;" if _v_won else "opacity:0.55;"
                    _hw = "font-weight:900;" if not _v_won else "opacity:0.55;"
                    _game_key = (_vt2, _ht2)
                    _gt_label = _gtype_map.get(_game_key, '')
                    _gt_badge = (
                        f"<span style='font-size:0.6rem;padding:2px 6px;"
                        f"background:#1e293b;color:#94a3b8;border-radius:10px;'>"
                        f"{html.escape(_gt_label)}</span>"
                        if _gt_label and _gt_label != 'Regular Season' else ""
                    )
                    _badge_row = (
                        f"<div style='width:100%;display:flex;justify-content:center;"
                        f"margin-top:2px;'>{_gt_badge}</div>"
                        if _gt_badge else ""
                    )
                    st.markdown(
                        f"<div style='display:flex;align-items:center;gap:8px;"
                        f"padding:8px 10px;background:#0a1628;border-radius:8px;"
                        f"border:1px solid #1e293b;flex-wrap:wrap;margin-bottom:5px;'>"
                        f"<div style='display:flex;align-items:center;gap:6px;"
                        f"flex:1;min-width:120px;'>{_vl}"
                        f"<div><div style='color:{_vc};font-size:0.8rem;{_vw}"
                        f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                        f"max-width:110px;'>{html.escape(_vt2)}</div>"
                        f"<div style='font-size:0.62rem;color:#475569;'>"
                        f"{html.escape(_vu2)}</div></div></div>"
                        f"<div style='text-align:center;min-width:70px;'>"
                        f"<div style='font-weight:900;font-size:1rem;color:#f1f5f9;'>"
                        f"{_vp} &ndash; {_hp}</div>"
                        f"<div style='font-size:0.6rem;color:#475569;'>"
                        f"&#177;{int(_g['Margin'])}</div></div>"
                        f"<div style='display:flex;align-items:center;gap:6px;"
                        f"flex:1;justify-content:flex-end;min-width:120px;'>"
                        f"<div style='text-align:right;'>"
                        f"<div style='color:{_hc};font-size:0.8rem;{_hw}"
                        f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                        f"max-width:110px;'>{html.escape(_ht2)}</div>"
                        f"<div style='font-size:0.62rem;color:#475569;'>"
                        f"{html.escape(_hu2)}</div></div>{_hl}</div>"
                        f"{_badge_row}</div>",
                        unsafe_allow_html=True
                    )

        # ── ALL GAMES TABLE (collapsible) ─────────────────────────────────────
        st.markdown("---")
        with st.expander("📋 All Logged Games This Season"):
            st.dataframe(
                y_data[['Visitor_Final', 'V_User_Final', 'V_Pts', 'H_Pts', 'H_User_Final', 'Home_Final', 'Margin', 'Total Points']],
                hide_index=True,
                use_container_width=True
            )

    # --- TEAM OVERVIEW ---
    with tabs[6]:
        st.header("📊 Team Analysis")
        target = st.selectbox("Select Team", model_2041['USER'].tolist(), key="team_analysis_user")
        row = model_2041[model_2041['USER'] == target].iloc[0]

        wins, losses, ppg, avg_margin = get_team_schedule_summary(scores, target)

        mobile_metrics([
            {"label": "🏆 Natty Odds",    "value": f"{row['Natty Odds']}%"},
            {"label": "🎯 CFP Odds",       "value": f"{row['CFP Odds']}%"},
            {"label": "📈 Projected Wins", "value": str(row['Projected Wins'])},
            {"label": "⚡ Power Index",    "value": str(row['Power Index'])},
        ])

        st.markdown("---")

        c1, c2 = st.columns([1.15, 1.85])
        with c1:
            st.subheader("Team Overview")
            logo_path = get_logo_source(row['TEAM'])
            render_logo(logo_path, width=110)
            st.markdown(f"### {row['USER']} | {row['TEAM']}")
            st.write(f"**Program Stock:** {row['Program Stock']}")
            st.write(f"**Current User Record in scores file:** {wins}-{losses}")
            st.write(f"**Average Points Per Game:** {ppg}")
            st.write(f"**Average Margin:** {avg_margin}")
            st.write(f"**Recruit Score:** {row['Recruit Score']}")
            st.write(f"**Current CFP Ranking:** {int(row['Current CFP Ranking']) if pd.notna(row['Current CFP Ranking']) else 'Unranked'}")
            st.write(f"**QB OVR:** {int(row['QB OVR']) if pd.notna(row['QB OVR']) else 'N/A'}")
            st.write(f"**QB Tier:** {row['QB Tier']}")
            st.write(f"**Improvement from prior year:** {row['Improvement']} OVR")
            st.write(f"**SOS:** {row['SOS']} (higher = tougher schedule)")
            st.write(f"**Resume Score:** {row['Resume Score']} (62% current win %, 38% SOS)")
            st.caption("Recent recruiting classes are now baked directly into CFP and natty odds through the Recruit Score, so the class pipeline still matters even without a separate recruiting tab.")
            st.markdown("**Coaching Stops & Rings**")
            render_history_cards(get_program_history_cards(row['USER'], ratings, champs, rec))

        with c2:
            st.subheader("MVP Profile")
            st.write(f"**MVP:** {row['⭐ STAR SKILL GUY (Top OVR)']}")
            st.write(f"**Generational Speed?** {row['Star Skill Guy is Generational Speed?']}")
            st.write(generate_mvp_backstory(row))

            coach_stats_row = stats[stats['User'] == target].iloc[0]
            st.markdown("---")
            st.subheader("Coach Profile")
            st.write(generate_coach_profile(row, coach_stats_row))
            mobile_metrics([
                {"label": "🏅 Career Win %", "value": f"{coach_stats_row['Career Win %']}%"},
                {"label": "🏆 Natties",       "value": str(int(coach_stats_row['Natties']))},
                {"label": "🎯 CFP Wins",      "value": str(int(coach_stats_row['CFP Wins']))},
            ], cols_desktop=3)

        stat_table = pd.DataFrame([
            {'Metric': 'Overall', 'Value': row['OVERALL']},
            {'Metric': 'Offense', 'Value': row['OFFENSE']},
            {'Metric': 'Defense', 'Value': row['DEFENSE']},
            {'Metric': 'Off 90+ Speed Players', 'Value': row['Off Speed (90+ speed)']},
            {'Metric': 'Def 90+ Speed Players', 'Value': row['Def Speed (90+ speed)']},
            {'Metric': 'Total Team Speed', 'Value': row['Team Speed (90+ Speed Guys)']},
            {'Metric': 'Quad 90', 'Value': row['Quad 90 (90+ SPD, ACC, AGI & COD)']},
            {'Metric': 'Generational Talent Count', 'Value': row['Generational (96+ speed or 96+ Acceleration)']},
            {'Metric': 'Where is the Speed?', 'Value': row['Where is the Speed?']},
            {'Metric': 'Speedometer', 'Value': f"{row['Speedometer']} MPH"},
            {'Metric': 'Blue Chip Ratio', 'Value': f"{row['BCR_Val']}%"},
            {'Metric': 'Current Record', 'Value': f"{int(row['Current Record Wins'])}-{int(row['Current Record Losses'])}" if pd.notna(row['Current Record Wins']) and pd.notna(row['Current Record Losses']) else 'N/A'},
            {'Metric': 'Opponent Combined Record', 'Value': f"{int(row['Combined Opponent Wins'])}-{int(row['Combined Opponent Losses'])}" if pd.notna(row['Combined Opponent Wins']) and pd.notna(row['Combined Opponent Losses']) else 'N/A'},
        ])

        st.subheader("Detailed Team Metrics")
        st.dataframe(stat_table, hide_index=True, use_container_width=True)

        detail_chart = pd.DataFrame({
            'Category': ['Overall', 'Offense', 'Defense', 'Off Speed', 'Def Speed', 'Quad 90', 'Generational'],
            'Score': [
                row['OVERALL'],
                row['OFFENSE'],
                row['DEFENSE'],
                row['Off Speed (90+ speed)'],
                row['Def Speed (90+ speed)'],
                row['Quad 90 (90+ SPD, ACC, AGI & COD)'],
                row['Generational (96+ speed or 96+ Acceleration)']
            ]
        })
        st.plotly_chart(px.bar(detail_chart, x='Category', y='Score', text='Score'), use_container_width=True)

    # --- TALENT PROFILE ---
    with tabs[4]:
        st.header("🔍 2041 Speed Freaks")
        st.write("Detailed scouting of high-end athletic ceiling. TEAM SPEED is driven by total 90+ speed depth, but generational freaks act like multipliers that can launch a roster way up the board. On this dashboard, a TEAM SPEED score of 40 equals 65 MPH — anything above that is officially speeding.")

        # ── Compute all speed metrics live from cfb26_rosters_full.csv ────────
        OFF_POS = {'QB','HB','FB','WR','TE','LT','LG','C','RG','RT'}
        DEF_POS = {'LEDG','REDG','DT','MIKE','WILL','SAM','CB','FS','SS'}

        try:
            _sf_roster = pd.read_csv('cfb26_rosters_full.csv')
            _sf_roster['SPD'] = pd.to_numeric(_sf_roster['SPD'], errors='coerce')
            _sf_roster['ACC'] = pd.to_numeric(_sf_roster['ACC'], errors='coerce')
            _sf_roster['REDSHIRT'] = pd.to_numeric(_sf_roster.get('REDSHIRT', 0), errors='coerce').fillna(0).astype(int)
            _sf_active = _sf_roster[_sf_roster['REDSHIRT'] == 0].copy()
            _sf_loaded = True
        except Exception:
            _sf_active = pd.DataFrame()
            _sf_loaded = False

        def _compute_speed_stats(team_df):
            off   = team_df[team_df['Pos'].isin(OFF_POS)]
            defp  = team_df[team_df['Pos'].isin(DEF_POS)]
            total    = int((team_df['SPD'] >= 90).sum())
            off_spd  = int((off['SPD']  >= 90).sum())
            def_spd  = int((defp['SPD'] >= 90).sum())
            quad_90  = int(
                ((team_df['SPD'] >= 90) & (team_df['ACC'] >= 90)
                 & (team_df['AGI'] >= 90) & (team_df['COD'] >= 90)).sum()
            )
            gen      = int(((team_df['SPD'] >= 96) | (team_df['ACC'] >= 96)).sum())
            speed_score = round(
                (total * 2.2 + off_spd * 1.0 + def_spd * 1.0 + quad_90 * 2.5)
                * (1 + gen * 0.16 + quad_90 * 0.07), 1
            )
            speedometer = team_speed_to_mph(speed_score)
            if off_spd > 5 and def_spd > 5:
                where = 'Off & Def'
            elif off_spd > 5:
                where = 'Offense'
            elif def_spd > 5:
                where = 'Defense'
            elif speedometer < 65:
                where = 'Non-Existent'
            else:
                where = 'Balanced'
            return {
                'team_speed':  total,
                'off_speed':   off_spd,
                'def_speed':   def_spd,
                'quad_90':     quad_90,
                'gen':         gen,
                'speed_score': speed_score,
                'speedometer': speedometer,
                'where':       where,
            }

        # Build talent_board: start from model_2041, override with live roster stats
        talent_board = model_2041.copy()

        if _sf_loaded and not _sf_active.empty:
            for _, _mr in talent_board.iterrows():
                _team = _mr['TEAM']
                _tdf  = _sf_active[_sf_active['Team'] == _team]
                if _tdf.empty:
                    continue
                _s = _compute_speed_stats(_tdf)
                idx = talent_board[talent_board['TEAM'] == _team].index
                talent_board.loc[idx, 'Team Speed (90+ Speed Guys)']              = _s['team_speed']
                talent_board.loc[idx, 'Off Speed (90+ speed)']                    = _s['off_speed']
                talent_board.loc[idx, 'Def Speed (90+ speed)']                    = _s['def_speed']
                talent_board.loc[idx, 'Quad 90 (90+ SPD, ACC, AGI & COD)'] = _s['quad_90']
                talent_board.loc[idx, 'Generational (96+ speed or 96+ Acceleration)'] = _s['gen']
                talent_board.loc[idx, 'Team Speed Score']                         = _s['speed_score']
                talent_board.loc[idx, 'Speedometer']                              = _s['speedometer']
                talent_board.loc[idx, 'Where is the Speed?']                      = _s['where']
            _speed_src_note = "📡 Speed metrics computed live from **cfb26_rosters_full.csv** (redshirted players excluded)"
        else:
            _speed_src_note = "⚠️ Roster CSV unavailable — speed metrics from TeamRatingsHistory.csv"

        talent_board = talent_board.sort_values(
            ['Team Speed Score', 'Generational (96+ speed or 96+ Acceleration)', 'Team Speed (90+ Speed Guys)'],
            ascending=False
        ).reset_index(drop=True)
        talent_board['TEAM SPEED Rank'] = np.arange(1, len(talent_board) + 1)

        fastest_team = talent_board.iloc[0]
        st.subheader("⚡ TEAM SPEED Rankings")
        st.caption(_speed_src_note)
        st.success(f"Fastest team alive right now: {fastest_team['TEAM']} ({fastest_team['USER']}) at {fastest_team['Speedometer']} MPH. Defensive coordinators should file a complaint.")
        render_speed_freaks_table(talent_board)

        # ── TEAM EXPANDERS ────────────────────────────────────────────────────
        st.markdown("---")
        for _, r in talent_board.iterrows():
            gens       = int(r['Generational (96+ speed or 96+ Acceleration)'])
            q90_cnt    = int(r['Quad 90 (90+ SPD, ACC, AGI & COD)'])
            team_speed = float(r.get('Team Speed Score', 0))
            tier       = get_speed_tier(team_speed)
            gen_desc   = get_pop_culture_speed_comp(gens)
            if gens == 0:
                bonus_desc = "No multiplier bonus. This is a depth-and-discipline operation."
            elif gens == 1:
                bonus_desc = "One generational freak — the whole scouting report bends around a single superhero."
            else:
                bonus_desc = f"{gens} generational freaks means the speed depth gets turbocharged. This many cheat codes can vault a roster several spots higher than raw depth alone."

            with st.expander(f"#{int(r['TEAM SPEED Rank'])} {r['USER']} | {r['TEAM']} — {tier}"):
                st.write(gen_desc)
                st.write(bonus_desc)
                mobile_metrics([
                    {"label": "🚗 Speedometer",        "value": f"{float(r.get('Speedometer',0)):.1f} MPH"},
                    {"label": "⚡ TEAM SPEED Score",   "value": str(team_speed)},
                    {"label": "💨 90+ Speed Guys",     "value": str(int(r['Team Speed (90+ Speed Guys)']))},
                    {"label": "👽 Gen Freaks",          "value": str(gens)},
                    {"label": "🔷 Quad 90",            "value": str(q90_cnt)},
                    {"label": "⚔️ Off / Def Speed",    "value": f"{int(r['Off Speed (90+ speed)'])} / {int(r['Def Speed (90+ speed)'])}"},
                ], cols_desktop=3)
                st.write(get_speeding_label(team_speed, gens))
                st.write(f"**Where is the Speed?** {r['Where is the Speed?']}  |  **Blue Chip Ratio:** {int(r['BCR_Val'])}%")
                st.progress(min(1.0, team_speed / 100.0))

                # Quad 90 player roster for this team
                if _sf_loaded:
                    _t_active = _sf_active[_sf_active['Team'] == r['TEAM']].copy()
                    _t_active[['SPD','ACC','AGI','COD']] = _t_active[['SPD','ACC','AGI','COD']].apply(pd.to_numeric, errors='coerce')
                    _q90_players = _t_active[
                        (_t_active['SPD']>=90)&(_t_active['ACC']>=90)&
                        (_t_active['AGI']>=90)&(_t_active['COD']>=90)
                    ].sort_values('SPD', ascending=False)
                    _gen_players = _t_active[
                        (_t_active['SPD']>=96)|(_t_active['ACC']>=96)
                    ].sort_values('SPD', ascending=False)
                    if not _q90_players.empty:
                        st.markdown("<div style='font-size:0.72rem;color:#64748b;margin:8px 0 4px;letter-spacing:.06em;font-weight:700;'>🔷 QUAD 90 ATHLETES</div>", unsafe_allow_html=True)
                        _q_html = "<div style='display:flex;flex-wrap:wrap;gap:5px;'>"
                        for _, _p in _q90_players.iterrows():
                            _q_html += (
                                f"<div style='background:#0a1628;border:1px solid #1e3a8a;border-radius:6px;"
                                f"padding:5px 9px;font-size:0.75rem;'>"
                                f"<span style='color:#60a5fa;font-weight:800;'>{html.escape(str(_p['Name']))}</span>"
                                f"<span style='color:#475569;margin:0 4px;'>{html.escape(str(_p['Pos']))}</span>"
                                f"<span style='color:#94a3b8;font-size:0.68rem;'>"
                                f"S{int(_p['SPD'])} A{int(_p['ACC'])} G{int(_p['AGI'])} C{int(_p['COD'])}"
                                f"</span></div>"
                            )
                        _q_html += "</div>"
                        st.markdown(_q_html, unsafe_allow_html=True)
                    if not _gen_players.empty:
                        st.markdown("<div style='font-size:0.72rem;color:#64748b;margin:8px 0 4px;letter-spacing:.06em;font-weight:700;'>👽 GENERATIONAL FREAKS (96+ SPD or ACC)</div>", unsafe_allow_html=True)
                        _g_html = "<div style='display:flex;flex-wrap:wrap;gap:5px;'>"
                        for _, _p in _gen_players.iterrows():
                            _hi = "#f59e0b" if pd.to_numeric(_p['SPD'],errors='coerce') >= 96 else "#a78bfa"
                            _g_html += (
                                f"<div style='background:#0d1a2e;border:1px solid {_hi}44;border-radius:6px;"
                                f"padding:5px 9px;font-size:0.75rem;'>"
                                f"<span style='color:{_hi};font-weight:800;'>{html.escape(str(_p['Name']))}</span>"
                                f"<span style='color:#475569;margin:0 4px;'>{html.escape(str(_p['Pos']))}</span>"
                                f"<span style='color:#94a3b8;font-size:0.68rem;'>"
                                f"S{int(_p['SPD'])} A{int(_p['ACC'])}"
                                f"</span></div>"
                            )
                        _g_html += "</div>"
                        st.markdown(_g_html, unsafe_allow_html=True)

        # ── SECTION 2: LEAGUE-WIDE TOP SPEED ATHLETES ────────────────────────
        st.markdown("---")
        st.subheader("🏃 Fastest Players in the League")
        st.caption("Top 20 by SPD across all active rosters. The guys who make coordinators sweat at 2am.")
        if _sf_loaded and not _sf_active.empty:
            _all_active = _sf_active.copy()
            _all_active[['SPD','ACC','AGI','COD','OVR']] = _all_active[['SPD','ACC','AGI','COD','OVR']].apply(pd.to_numeric, errors='coerce')
            _top_speed = _all_active.nlargest(20, 'SPD').reset_index(drop=True)
            _spd_html = "<div style='display:flex;flex-direction:column;gap:4px;'>"
            for _i, _p in _top_speed.iterrows():
                _tc = get_team_primary_color(_p['Team'])
                _logo_uri = image_file_to_data_uri(get_logo_source(_p['Team']))
                _logo = f"<img src='{_logo_uri}' style='width:22px;height:22px;object-fit:contain;vertical-align:middle;margin-right:6px;'/>" if _logo_uri else ""
                _is_q90 = (pd.notna(_p['SPD']) and _p['SPD']>=90 and pd.notna(_p['ACC']) and _p['ACC']>=90
                           and pd.notna(_p['AGI']) and _p['AGI']>=90 and pd.notna(_p['COD']) and _p['COD']>=90)
                _is_gen = (pd.notna(_p['SPD']) and _p['SPD']>=96) or (pd.notna(_p['ACC']) and _p['ACC']>=96)
                _badges = ""
                if _is_gen:  _badges += "<span style='font-size:0.6rem;padding:1px 4px;background:#78350f;color:#fbbf24;border-radius:3px;margin-left:4px;'>👽GEN</span>"
                if _is_q90:  _badges += "<span style='font-size:0.6rem;padding:1px 4px;background:#1e3a8a;color:#60a5fa;border-radius:3px;margin-left:4px;'>🔷Q90</span>"
                _spd_html += (
                    f"<div style='display:flex;align-items:center;gap:8px;padding:6px 10px;"
                    f"background:#0a1628;border-left:3px solid {_tc};border-radius:5px;font-size:0.8rem;'>"
                    f"<span style='color:#475569;min-width:20px;font-size:0.72rem;'>#{_i+1}</span>"
                    f"{_logo}"
                    f"<span style='color:{_tc};font-weight:800;min-width:80px;'>{html.escape(str(_p['Name']))}</span>"
                    f"<span style='color:#64748b;font-size:0.7rem;min-width:38px;'>{html.escape(str(_p['Pos']))} · {html.escape(str(_p['Year']))}</span>"
                    f"<span style='color:#fbbf24;font-weight:900;min-width:28px;'>S{int(_p['SPD'])}</span>"
                    f"<span style='color:#94a3b8;font-size:0.72rem;'>A{int(_p['ACC'])} G{int(_p['AGI'])} C{int(_p['COD'])}</span>"
                    f"{_badges}"
                    f"<span style='color:#475569;font-size:0.68rem;margin-left:auto;'>{html.escape(str(_p['Team']))}</span>"
                    f"</div>"
                )
            _spd_html += "</div>"
            st.markdown(_spd_html, unsafe_allow_html=True)

        # ── SECTION 3: POSITIONAL SPEED DEPTH ────────────────────────────────
        st.markdown("---")
        st.subheader("📊 Positional Speed Depth")
        st.caption("Where each team's 90+ speed actually lives — WR room, DB room, or the backfield.")
        if _sf_loaded and not _sf_active.empty:
            _POS_GROUPS = {
                'WR Room':   ['WR'],
                'Backfield': ['HB','FB','QB'],
                'DB Room':   ['CB','FS','SS'],
                'Linebackers':['MIKE','WILL','SAM'],
                'D-Line':    ['LEDG','REDG','DT'],
                'O-Line':    ['LT','LG','C','RG','RT'],
                'TE/ST':     ['TE','K','P'],
            }
            _pos_rows = []
            for _team, _tdf in _sf_active.groupby('Team'):
                _u = {v:k for k,v in USER_TEAMS.items()}.get(_team, '')
                if not _u: continue
                _tdf2 = _tdf.copy()
                _tdf2['SPD'] = pd.to_numeric(_tdf2['SPD'], errors='coerce')
                _row = {'User': _u, 'Team': _team}
                for _grp, _pos_list in _POS_GROUPS.items():
                    _grp_df = _tdf2[_tdf2['Pos'].isin(_pos_list)]
                    _row[_grp] = int((_grp_df['SPD'] >= 90).sum())
                _pos_rows.append(_row)
            _pos_df = pd.DataFrame(_pos_rows).set_index('User')

            # Render as a styled HTML grid
            _pos_html = "<div style='overflow-x:auto;'><table style='width:100%;border-collapse:collapse;font-size:0.8rem;'>"
            _pos_html += "<thead><tr style='background:#0a1628;'>"
            _pos_html += "<th style='padding:7px 10px;text-align:left;color:#64748b;'>Team</th>"
            for _grp in _POS_GROUPS:
                _pos_html += f"<th style='padding:7px 8px;text-align:center;color:#64748b;'>{html.escape(_grp)}</th>"
            _pos_html += "</tr></thead><tbody>"
            for _u, _pr in _pos_df.iterrows():
                _tc = get_team_primary_color(_pr['Team'])
                _logo_uri = image_file_to_data_uri(get_logo_source(_pr['Team']))
                _logo = f"<img src='{_logo_uri}' style='width:20px;height:20px;object-fit:contain;vertical-align:middle;margin-right:5px;'/>" if _logo_uri else ""
                _pos_html += f"<tr style='border-bottom:1px solid #1e293b;'>"
                _pos_html += f"<td style='padding:7px 10px;white-space:nowrap;'>{_logo}<span style='color:{_tc};font-weight:800;'>{html.escape(str(_pr['Team']))}</span><span style='color:#475569;font-size:0.7rem;margin-left:5px;'>({html.escape(_u)})</span></td>"
                for _grp in _POS_GROUPS:
                    _val = int(_pr.get(_grp, 0))
                    _col = "#22c55e" if _val >= 3 else ("#fbbf24" if _val >= 1 else "#374151")
                    _pos_html += f"<td style='padding:7px 8px;text-align:center;color:{_col};font-weight:{'800' if _val >= 1 else '400'};'>{_val if _val > 0 else '—'}</td>"
                _pos_html += "</tr>"
            _pos_html += "</tbody></table></div>"
            st.markdown(_pos_html, unsafe_allow_html=True)

        # ── SECTION 4: HEAD-TO-HEAD SPEED MATCHUP ────────────────────────────
        st.markdown("---")
        st.subheader("⚔️ Speed Matchup Comparison")
        st.caption("Pick two teams and see their full speed profiles side by side.")
        _user_list = sorted(USER_TEAMS.keys())
        _hth_col1, _hth_col2 = st.columns(2)
        with _hth_col1:
            _team_a_user = st.selectbox("Team A", _user_list, index=0, key="sf_team_a")
        with _hth_col2:
            _team_b_user = st.selectbox("Team B", _user_list, index=1, key="sf_team_b")

        if _sf_loaded and _team_a_user != _team_b_user:
            _ta_name = USER_TEAMS[_team_a_user]
            _tb_name = USER_TEAMS[_team_b_user]
            _ta_df = _sf_active[_sf_active['Team']==_ta_name].copy()
            _tb_df = _sf_active[_sf_active['Team']==_tb_name].copy()
            for _d in [_ta_df, _tb_df]:
                _d[['SPD','ACC','AGI','COD','OVR']] = _d[['SPD','ACC','AGI','COD','OVR']].apply(pd.to_numeric, errors='coerce')
            _sa = _compute_speed_stats(_ta_df)
            _sb = _compute_speed_stats(_tb_df)
            _tc_a = get_team_primary_color(_ta_name)
            _tc_b = get_team_primary_color(_tb_name)

            _matchup_metrics = [
                ('Speedometer', f"{_sa['speedometer']} MPH", f"{_sb['speedometer']} MPH"),
                ('Speed Score', str(_sa['speed_score']), str(_sb['speed_score'])),
                ('90+ SPD Guys', str(_sa['team_speed']), str(_sb['team_speed'])),
                ('Quad 90', str(_sa['quad_90']), str(_sb['quad_90'])),
                ('Gen Freaks', str(_sa['gen']), str(_sb['gen'])),
                ('Off Speed', str(_sa['off_speed']), str(_sb['off_speed'])),
                ('Def Speed', str(_sa['def_speed']), str(_sb['def_speed'])),
                ('Where', _sa['where'], _sb['where']),
            ]
            _mh = (
                f"<div style='overflow-x:auto;'>"
                f"<table style='width:100%;border-collapse:collapse;font-size:0.82rem;'>"
                f"<thead><tr style='background:#0a1628;'>"
                f"<th style='padding:8px 12px;text-align:center;color:{_tc_a};'>{html.escape(_ta_name)}</th>"
                f"<th style='padding:8px 10px;text-align:center;color:#475569;font-size:0.7rem;'></th>"
                f"<th style='padding:8px 12px;text-align:center;color:{_tc_b};'>{html.escape(_tb_name)}</th>"
                f"</tr></thead><tbody>"
            )
            for _label, _va, _vb in _matchup_metrics:
                # Try to determine winner numerically
                try:
                    _na, _nb = float(str(_va).split()[0]), float(str(_vb).split()[0])
                    _ca = "#22c55e" if _na > _nb else ("#ef4444" if _na < _nb else "#94a3b8")
                    _cb = "#22c55e" if _nb > _na else ("#ef4444" if _nb < _na else "#94a3b8")
                except Exception:
                    _ca = _cb = "#94a3b8"
                _mh += (
                    f"<tr style='border-bottom:1px solid #1e293b;'>"
                    f"<td style='padding:7px 12px;text-align:center;color:{_ca};font-weight:800;'>{html.escape(_va)}</td>"
                    f"<td style='padding:7px 10px;text-align:center;color:#475569;font-size:0.7rem;white-space:nowrap;'>{html.escape(_label)}</td>"
                    f"<td style='padding:7px 12px;text-align:center;color:{_cb};font-weight:800;'>{html.escape(_vb)}</td>"
                    f"</tr>"
                )
            _mh += "</tbody></table></div>"
            st.markdown(_mh, unsafe_allow_html=True)

    # --- UPSET TRACKER ---
    with tabs[9]:
        st.header("🚨 Upset Tracker")

        upset_df = scores.copy()
        rating_map = model_2041.set_index('TEAM')['OVERALL'].to_dict()
        upset_df['Visitor OVR Proxy'] = upset_df['Visitor_Final'].map(rating_map)
        upset_df['Home OVR Proxy'] = upset_df['Home_Final'].map(rating_map)

        upset_df['Expected Winner'] = np.where(
            upset_df['Home OVR Proxy'].fillna(-999) >= upset_df['Visitor OVR Proxy'].fillna(-999),
            upset_df['Home_Final'],
            upset_df['Visitor_Final']
        )
        upset_df['Actual Winner'] = upset_df['Winner_Team']
        upset_df['Underdog Delta'] = np.where(
            upset_df['Actual Winner'] == upset_df['Home_Final'],
            upset_df['Visitor OVR Proxy'].fillna(upset_df['Home OVR Proxy']) - upset_df['Home OVR Proxy'].fillna(upset_df['Visitor OVR Proxy']),
            upset_df['Home OVR Proxy'].fillna(upset_df['Visitor OVR Proxy']) - upset_df['Visitor OVR Proxy'].fillna(upset_df['Home OVR Proxy'])
        )

        upset_df = upset_df[upset_df['Actual Winner'] != upset_df['Expected Winner']].copy()
        upset_df['Upset Score'] = (upset_df['Underdog Delta'].abs().fillna(0) + upset_df['Margin']).round(1)
        upset_df = upset_df.sort_values('Upset Score', ascending=False)

        if upset_df.empty:
            st.info("No upsets were detected with the current proxy model.")
        else:
            st.dataframe(
                upset_df[['YEAR', 'Visitor_Final', 'V_Pts', 'H_Pts', 'Home_Final', 'Actual Winner', 'Expected Winner', 'Upset Score']],
                hide_index=True,
                use_container_width=True
            )

            st.plotly_chart(
                px.bar(
                    upset_df.head(15),
                    x='Actual Winner',
                    y='Upset Score',
                    color='YEAR',
                    hover_data=['Visitor_Final', 'Home_Final', 'Expected Winner']
                ),
                use_container_width=True
            )

    # --- GOAT RANKINGS ---
    with tabs[10]:
        st.header("🐐 Dynasty GOAT Rankings")
        goat = stats.copy().sort_values("GOAT Score", ascending=False).reset_index(drop=True)

        if not goat.empty:
            top = goat.iloc[0]
            mobile_metrics([
                {"label": "👑 GOAT",          "value": str(top['User']),           "delta": f"{top['GOAT Score']} pts"},
                {"label": "🏆 Most Natties",  "value": str(goat.loc[goat['Natties'].idxmax(), 'User']),  "delta": f"{goat['Natties'].max()} titles"},
                {"label": "🎯 Best Win %",    "value": str(goat.loc[goat['Career Win %'].idxmax(), 'User']), "delta": f"{goat['Career Win %'].max()}%"},
                {"label": "🏈 NFL Pipeline",  "value": str(goat.loc[goat['Drafted'].idxmax(), 'User']),   "delta": f"{goat['Drafted'].max()} drafted"},
            ])

        with st.expander("📊 Full GOAT Table", expanded=True):
            st.dataframe(
                goat[['User', 'GOAT Score', 'Career Record', 'Career Win %', 'Natties', 'Natty Apps', 'CFP Wins', 'Conf Titles', '1st Rounders', 'Drafted']],
                hide_index=True,
                use_container_width=True
            )

        st.plotly_chart(
            px.bar(
                goat,
                x="User",
                y="GOAT Score",
                color="User",
                hover_data=['Natties', 'Natty Apps', 'CFP Wins', 'Conf Titles', '1st Rounders', 'Drafted']
            ),
            use_container_width=True
        )



    # --- ROSTER MATCHUP ---
    with tabs[5]:
        render_roster_matchup_tab()

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
