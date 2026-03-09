
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
st.set_page_config(page_title="Island Dynasty HQ", layout="wide", page_icon="🏈")
st.title("🏈 Island Dynasty: The Executive Suite")

CURRENT_WEEK_NUMBER = 12

st.markdown("""
<style>
.block-container {padding-top: 1rem; padding-bottom: 1rem; padding-left: 0.8rem; padding-right: 0.8rem;}
[data-testid="stHorizontalBlock"] {gap: 0.75rem;}
.stTabs [data-baseweb="tab-list"] {gap: 0.25rem; flex-wrap: wrap;}
.stTabs [data-baseweb="tab"] {height: auto; white-space: normal; padding-top: 0.35rem; padding-bottom: 0.35rem;}
@media (max-width: 768px) {
  .block-container {padding-left: 0.5rem; padding-right: 0.5rem;}
  h1 {font-size: 1.5rem !important;}
  h2 {font-size: 1.2rem !important;}
  h3 {font-size: 1.05rem !important;}
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

def render_speed_freaks_table(df):
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
            <div style="font-weight:800;min-width:24px;text-align:center;">#{int(row.get('TEAM SPEED Rank', 0))}</div>
            <div style="width:40px;text-align:center;">{logo_html}</div>
            <div>
              <div style="font-weight:800;color:{primary};">{html.escape(team)}</div>
              <div style="font-size:12px;color:#cbd5e1;">{html.escape(user)}</div>
            </div>
          </div>
        </td>
        """]
        display_vals = [
            f"{float(row.get('Speedometer', 0)):.1f} MPH",
            f"{float(row.get('Team Speed Score', 0)):.1f}",
            html.escape(str(row.get('Where is the Speed?', '—'))),
            str(int(row.get('Team Speed (90+ Speed Guys)', 0))),
            str(int(row.get('Game Breakers (90+ Speed & 90+ Acceleration)', 0))),
            str(int(row.get('Generational (96+ speed or 96+ Acceleration)', 0))),
        ]
        for disp in display_vals:
            cells.append(f"<td style='padding:10px 12px;border-bottom:1px solid #e5e7eb;text-align:center;white-space:nowrap;'>{disp}</td>")
        rows_html.append(f"<tr style='border-left:6px solid {primary};background:linear-gradient(90deg,{primary}12,transparent 14%);'>{''.join(cells)}</tr>")
    table_html = f"""
    <div style="overflow-x:auto;border:1px solid #e5e7eb;border-radius:14px;">
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead>
          <tr style="background:#f8fafc;color:#111827;">
            <th style="text-align:left;padding:10px 12px;color:#111827;font-weight:800;">Fastest Team</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">Speedometer</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">Team Speed Score</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">Where is the Speed?</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">90+ Speed</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">Game Breakers</th>
            <th style="padding:10px 12px;color:#111827;font-weight:800;">Gen Freaks</th>
          </tr>
        </thead>
        <tbody>{''.join(rows_html)}</tbody>
      </table>
    </div>
    """
    st.markdown(table_html, unsafe_allow_html=True)


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
            col_a.markdown(f"<div style='text-align:center;font-size:1.05rem;color:{color_a};'>{'🏆 ' if va > vb else ''}**{va}**</div>", unsafe_allow_html=True)
            col_mid.markdown(f"<div style='text-align:center;color:#6b7280;font-size:0.78rem;font-weight:600;'>{label}</div>", unsafe_allow_html=True)
            col_b.markdown(f"<div style='text-align:center;font-size:1.05rem;color:{color_b};'>**{vb}**{' 🏆' if vb > va else ''}</div>", unsafe_allow_html=True)
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
                    st.dataframe(grp_a[disp_cols].reset_index(drop=True), hide_index=True, use_container_width=True) if not grp_a.empty else st.caption("No players.")
                with pb:
                    st.markdown(f"<div style='display:flex;align-items:center;gap:6px;margin-bottom:4px;'>{sm_logo_b}<span style='color:{color_b};font-weight:800;font-size:0.95rem;'>{team_b}</span></div>", unsafe_allow_html=True)
                    st.dataframe(grp_b[disp_cols].reset_index(drop=True), hide_index=True, use_container_width=True) if not grp_b.empty else st.caption("No players.")

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

        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric(f"{team_a} Redshirts", cb_a["Redshirts"])
        m2.metric(f"{team_a} Avg Elig", cb_a["Avg Elig"])
        m3.metric(f"{team_a} Young", cb_a["Young (3-4yr elig)"])
        m4.metric(f"{team_b} Redshirts", cb_b["Redshirts"])
        m5.metric(f"{team_b} Avg Elig", cb_b["Avg Elig"])
        m6.metric(f"{team_b} Young", cb_b["Young (3-4yr elig)"])

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
            st.dataframe(vets_a.rename(columns={"ExpTag": "Status"}), hide_index=True, use_container_width=True) if not vets_a.empty else st.caption("No seniors.")
        with vc2:
            st.markdown(f"<span style='color:{color_b};font-weight:800;'>{team_b}</span>", unsafe_allow_html=True)
            st.dataframe(vets_b.rename(columns={"ExpTag": "Status"}), hide_index=True, use_container_width=True) if not vets_b.empty else st.caption("No seniors.")

        # Redshirt breakdown
        st.markdown("---")
        st.markdown("#### 🔄 Redshirt Inventory")
        st.caption("Redshirts = players who gained a year in the program without burning eligibility. These players have more development than their class label suggests.")
        rs_a = roster_a[roster_a['IsRS']].sort_values("OVR", ascending=False)[["Name", "Pos", "ExpTag", "OVR", "SPD", "FV"]].reset_index(drop=True)
        rs_b = roster_b[roster_b['IsRS']].sort_values("OVR", ascending=False)[["Name", "Pos", "ExpTag", "OVR", "SPD", "FV"]].reset_index(drop=True)
        rc1, rc2 = st.columns(2)
        with rc1:
            st.markdown(f"<span style='color:{color_a};font-weight:800;'>{team_a} — {len(rs_a)} redshirts</span>", unsafe_allow_html=True)
            st.dataframe(rs_a.rename(columns={"ExpTag": "Status", "FV": "FV Score"}), hide_index=True, use_container_width=True) if not rs_a.empty else st.caption("No redshirts.")
        with rc2:
            st.markdown(f"<span style='color:{color_b};font-weight:800;'>{team_b} — {len(rs_b)} redshirts</span>", unsafe_allow_html=True)
            st.dataframe(rs_b.rename(columns={"ExpTag": "Status", "FV": "FV Score"}), hide_index=True, use_container_width=True) if not rs_b.empty else st.caption("No redshirts.")

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
            st.dataframe(sleepers_a.rename(columns={"ExpTag": "Status", "AthlScore": "Athl", "EligLeft": "Elig"}), hide_index=True, use_container_width=True) if not sleepers_a.empty else st.caption("No high-ceiling sleepers found.")
        with sl2:
            st.markdown(f"<span style='color:{color_b};font-weight:800;'>{team_b} — {len(sleepers_b)} sleepers</span>", unsafe_allow_html=True)
            st.dataframe(sleepers_b.rename(columns={"ExpTag": "Status", "AthlScore": "Athl", "EligLeft": "Elig"}), hide_index=True, use_container_width=True) if not sleepers_b.empty else st.caption("No high-ceiling sleepers found.")

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

        for num_col in [
            'OVERALL', 'OFFENSE', 'DEFENSE', 'Team Speed (90+ Speed Guys)',
            'Def Speed (90+ speed)', 'Off Speed (90+ speed)',
            'Game Breakers (90+ Speed & 90+ Acceleration)',
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


def build_2041_model_table(r_2041, stats_df, rec_df):
    df = r_2041.copy()

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
        u_s = stats_df[stats_df['User'] == row['USER']].iloc[0]

        pedigree_bonus = (
            u_s['Natties'] * 24
            + u_s['Natty Apps'] * 15
            + u_s['CFP Wins'] * 3.2
            + u_s['Conf Titles'] * 1.5
        )
        heartbreak_penalty = max(0, u_s['Natty Apps'] - u_s['Natties']) * 1.0
        cfp_fail_penalty = u_s['CFP Losses'] * 1.1

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
            + row['Game Breakers (90+ Speed & 90+ Acceleration)'] * 1.65
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

    def power_index(row):
        return round(
            row['OVERALL'] * 2.25
            + row['OFFENSE'] * 0.82
            + row['DEFENSE'] * 0.82
            + row['Team Speed (90+ Speed Guys)'] * 2.1
            + row['Game Breakers (90+ Speed & 90+ Acceleration)'] * 1.6
            + row['Generational (96+ speed or 96+ Acceleration)'] * 5.2
            + row['BCR_Val'] * 0.56
            + row['Recruit Score'] * 0.50
            + row['Improvement'] * 4.0
            + row['Career Win %'] * 0.60
            + row['Current Win %'] * 0.50
            + row['SOS'] * 0.38
            + cfp_rank_bonus(row.get('Current CFP Ranking', np.nan)) * 0.86
            + qb_cfp_bonus(row) * 0.95
            + row['Natties'] * 10.5
            + row['Natty Apps'] * 3.4
            + row['CFP Wins'] * 1.2
            - row['CFP Losses'] * 1.2,
            1
        )

    df['Power Index'] = df.apply(power_index, axis=1)
    df['Team Speed Score'] = (
        df['Team Speed (90+ Speed Guys)'] * 2.2
        + df['Off Speed (90+ speed)'] * 1.0
        + df['Def Speed (90+ speed)'] * 1.0
        + df['Game Breakers (90+ Speed & 90+ Acceleration)'] * 1.8
    ) * (1 + df['Generational (96+ speed or 96+ Acceleration)'] * 0.16)
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
        + df['Game Breakers (90+ Speed & 90+ Acceleration)'] * 1.25
        + df['Generational (96+ speed or 96+ Acceleration)'] * 3.1
        + df['Recruit Score'] * 0.46
        + df['Career Win %'] * 0.18
        + df['Current Win %'] * 0.70
        + df['SOS'] * 0.58
        + df['Resume Score'] * 0.42
        + df['Current CFP Ranking'].apply(cfp_rank_bonus) * 1.95
        + df.apply(qb_cfp_bonus, axis=1)
        + df['Natty Apps'] * 1.9
        + df['Natties'] * 2.8
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
            + float(m.get('Game Breakers (90+ Speed & 90+ Acceleration)', 0)) * 2.0
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
    df['Remaining Games'] = (12 - df['Games Played']).clip(lower=0)
    df['Win %'] = (df['Wins'] / (df['Wins'] + df['Losses'])).round(3)
    df['Committee Score'] = ((26 - df['Rank']) / 25) * 100
    df['Top12 Flag'] = (df['Rank'] <= 12).astype(int)
    df['Top8 Flag'] = (df['Rank'] <= 8).astype(int)
    df['Rank Pressure'] = np.where(df['Rank'] <= 12, 0.0, (df['Rank'] - 12) * 2.6)
    df['Loss Penalty'] = np.where(df['Losses'] <= 1, 0, (df['Losses'] - 1) * 12.0)

    qbm = {
        'Elite': 8.0,
        'Leader': 4.0,
        'Average Joe': -2.5,
        'Ass': -8.5,
        'Unknown': 0.0,
    }
    df['QB Mod'] = df['QB Tier'].map(qbm).fillna(0.0)
    df['Overall CFP Mod'] = np.select(
        [df['OVERALL'] <= 80, df['OVERALL'] <= 82, df['OVERALL'] <= 84],
        [-16.0, -11.0, -6.0],
        default=0.0
    )
    df['Lose Out Penalty'] = (
        df['Remaining Games'] * 5.0
        + np.maximum(0, (df['Losses'] + df['Remaining Games']) - 2) * 8.0
        + np.where(df['Rank'] <= 12, df['Remaining Games'] * 2.5, df['Remaining Games'] * 1.2)
    )

    df['CFP Raw'] = (
        df['Committee Score'] * 0.35
        + (df['Win %'] * 100) * 0.17
        + df['SOS'] * 0.12
        + df['Resume Score'] * 0.11
        + df['Recruit Score'] * 0.04
        + df['Team Speed Score'] * 0.03
        + df['BCR_Val'] * 0.02
        + df['Power Index'].clip(lower=160, upper=360).sub(160).div(2.2) * 0.05
        + df['OVERALL'] * 0.07
        + df['Top12 Flag'] * 5.2
        + df['Top8 Flag'] * 2.5
        + df['QB Mod']
        + df['Overall CFP Mod']
        - df['Loss Penalty']
        - df['Rank Pressure']
    )
    df['Lose Out Raw'] = df['CFP Raw'] - df['Lose Out Penalty']
    df['Lose Out CFP %'] = (1 / (1 + np.exp(-(df['Lose Out Raw'] - 43) / 5.8)) * 100).round(1)
    df['Base CFP %'] = (1 / (1 + np.exp(-(df['CFP Raw'] - 46) / 5.8)) * 100).round(1)
    df['CFP Make %'] = (df['Base CFP %'] * 0.76 + df['Lose Out CFP %'] * 0.24).round(1)
    df['CFP Make %'] = df['CFP Make %'].clip(lower=1.0, upper=92.5)

    # Automatic-bid path estimate: best shot for likely conference champs among highly ranked teams.
    auto_bid_raw = (
        df['Committee Score'] * 0.55
        + (df['Win %'] * 100) * 0.20
        + df['SOS'] * 0.08
        + df['Resume Score'] * 0.07
        + df['QB Mod'] * 0.5
        - df['Losses'] * 5.5
    )
    df['Auto-Bid %'] = (1 / (1 + np.exp(-(auto_bid_raw - 48) / 7.0)) * 100).round(1)
    df['Auto-Bid %'] = df['Auto-Bid %'].clip(lower=1.0, upper=97.0)

    bye_raw = (
        df['Committee Score'] * 0.60
        + (df['Win %'] * 100) * 0.15
        + df['Auto-Bid %'] * 0.20
        + df['CFP Make %'] * 0.05
        - df['Rank'] * 1.5
    )
    df['Bye %'] = (1 / (1 + np.exp(-(bye_raw - 55) / 6.5)) * 100).round(1)
    df['Bye %'] = np.where(df['Rank'] > 12, df['Bye %'] * 0.35, df['Bye %'])
    df['Bye %'] = df['Bye %'].clip(lower=0.5, upper=96.0).round(1)

    def bubble_tier(row):
        pct = row['CFP Make %']
        if pct >= 92:
            return '🔒 Lock'
        if pct >= 75:
            return '✅ In Control'
        if pct >= 45:
            return '⚠️ Bubble'
        if pct >= 18:
            return '🔥 Need Chaos'
        return '🪦 Practically Dead'

    df['Bubble Tier'] = df.apply(bubble_tier, axis=1)
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




def render_playoff_bracket(projected_field):
    if projected_field is None or projected_field.empty or len(projected_field) < 12:
        st.info("Need 12 projected teams to render the bracket.")
        return

    pf = projected_field.copy()
    pf['Projected Seed'] = pd.to_numeric(pf['Projected Seed'], errors='coerce')
    pf = pf.dropna(subset=['Projected Seed']).sort_values('Projected Seed').reset_index(drop=True)

    def get_logo_path(team):
        path = get_logo_source(team)
        if isinstance(path, str) and path and Path(path).exists():
            return path
        return None

    def team_card(row, win_prob=None, bye=False):
        team = str(row.get('Team', 'Unknown Team'))
        seed = int(pd.to_numeric(row.get('Projected Seed', 0), errors='coerce') or 0)
        record = str(row.get('Record', '—'))
        primary = get_team_primary_color(team)
        auto_bid = float(pd.to_numeric(row.get('Auto-Bid %', 0), errors='coerce') or 0)
        logo_path = get_logo_path(team)

        with st.container(border=True):
            head_left, head_right = st.columns([4, 1])
            with head_left:
                info_cols = st.columns([0.8, 1.2, 6])
                with info_cols[0]:
                    st.markdown(
                        f"""
                        <div style='display:flex;align-items:center;justify-content:center;width:30px;height:30px;border-radius:999px;background:{primary};color:white;font-weight:900;font-size:12px;'>#{seed}</div>
                        """,
                        unsafe_allow_html=True,
                    )
                with info_cols[1]:
                    if logo_path:
                        st.image(logo_path, width=36)
                    else:
                        st.markdown("### 🏈")
                with info_cols[2]:
                    st.markdown(
                        f"<div style='font-size:18px;font-weight:900;color:{primary};line-height:1.15;'>{html.escape(team)}</div>",
                        unsafe_allow_html=True,
                    )
                    st.caption(f"Record: {record}")
            with head_right:
                if bye:
                    st.markdown(
                        "<div style='margin-top:6px;display:inline-block;padding:4px 8px;border-radius:999px;background:#dcfce7;color:#14532d;font-size:11px;font-weight:800;'>BYE</div>",
                        unsafe_allow_html=True,
                    )
                elif auto_bid >= 55:
                    st.markdown(
                        "<div style='margin-top:6px;display:inline-block;padding:4px 8px;border-radius:999px;background:#fef3c7;color:#92400e;font-size:11px;font-weight:800;'>AUTO-BID TRACK</div>",
                        unsafe_allow_html=True,
                    )
            if win_prob is not None:
                st.progress(float(win_prob) / 100.0)
                st.caption(f"Win probability: {win_prob:.1f}%")

    def matchup(seed_a, seed_b):
        row_a = pf[pf['Projected Seed'] == seed_a].iloc[0]
        row_b = pf[pf['Projected Seed'] == seed_b].iloc[0]
        diff = max(-8, min(8, seed_b - seed_a))
        p_a = max(18.0, min(82.0, 50 + (diff * 4.5)))
        p_b = round(100 - p_a, 1)
        with st.container(border=True):
            st.markdown(f"#### #{seed_a} vs #{seed_b}")
            team_card(row_a, p_a)
            st.markdown("<div style='text-align:center;font-size:12px;font-weight:900;color:#94a3b8;margin:8px 0;'>VS</div>", unsafe_allow_html=True)
            team_card(row_b, p_b)

    semis = [str(pf[pf['Projected Seed'] == s].iloc[0]['Team']) for s in [1, 2, 3, 4]]
    st.caption("Projected semifinalists: " + " • ".join(semis))

    left, right = st.columns([1.0, 1.35])
    with left:
        st.markdown("#### Top 4 Byes")
        for seed in [1, 2, 3, 4]:
            team_card(pf[pf['Projected Seed'] == seed].iloc[0], bye=True)
            st.markdown("")
    with right:
        st.markdown("#### Projected First Round")
        for a, b in [(5, 12), (6, 11), (7, 10), (8, 9)]:
            matchup(a, b)
            st.markdown("")


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

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Conference Frames", len(assets.get('standings', pd.DataFrame())))
    a2.metric("Schedule Frames", len(assets.get('schedule', pd.DataFrame())))
    a3.metric("CFP Frames", len(assets.get('cfp', pd.DataFrame())))
    a4.metric("Recruiting Frames", len(assets.get('recruiting', pd.DataFrame())))

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

    tabs = st.tabs([
        "🗞️ Dynasty News",
        "📰 Dynasty War Room",
        "🏆 Who's In?",
        "📺 Season Recap",
        "🔍 Speed Freaks",
        "📊 Team Overview",
        "🏈 Recruiting Rankings",
        "⚔️ H2H Matrix",
        "🚨 Upset Tracker",
        "🐐 GOAT Rankings",
        "🎯 Roster Matchup",
    ])

    # --- WAR ROOM ---
    with tabs[1]:
        st.header("📰 Dynasty War Room")
        st.caption("Clean board format restored. Team colors and local logos should render here when the files exist in your repo logos folder.")

        title_favorite = model_2041.sort_values('Natty Odds', ascending=False).iloc[0]
        most_dangerous = model_2041.sort_values('Power Index', ascending=False).iloc[0]
        best_recruiter_user = model_2041.sort_values('Recruit Score', ascending=False).iloc[0]
        collapse_team = model_2041.sort_values('Collapse Risk', ascending=False).iloc[0]
        pipeline_king = stats.sort_values('Drafted', ascending=False).iloc[0]

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Title Favorite", f"{title_favorite['USER']} ({title_favorite['Natty Odds']}%)")
        c2.metric("Power Index Leader", f"{most_dangerous['USER']}", f"{most_dangerous['Power Index']}")
        c3.metric("Recruiting King", f"{best_recruiter_user['USER']}", f"{best_recruiter_user['Recruit Score']}")
        c4.metric("Collapse Watch", collapse_team['USER'], f"{collapse_team['Collapse Risk']}%")
        c5.metric("NFL Pipeline", pipeline_king['User'], f"{pipeline_king['Drafted']} drafted")

        st.markdown("#### War Room Board")
        board_defaults = {
            'Logo': '',
            'Current CFP Ranking': np.nan,
            'Power Index': 0.0,
            'Natty Odds': 0.0,
            'CFP Odds': 0,
            'Natty if Lose to Unranked': 0.0,
            'Natty if Lose to Ranked': 0.0,
            'CFP if Lose to Unranked': 0,
            'CFP if Lose to Ranked': 0,
            'Collapse Risk': 0,
            'Program Stock': '➖ Stable'
        }
        model_2041 = ensure_columns(model_2041, board_defaults)
        board_cols = ['TEAM', 'USER', 'Current CFP Ranking', 'SOS', 'QB Tier', 'Power Index', 'Natty Odds', 'CFP Odds',
                      'Natty if Lose to Unranked', 'Natty if Lose to Ranked', 'CFP if Lose to Unranked',
                      'CFP if Lose to Ranked', 'Collapse Risk', 'Program Stock']
        board = model_2041[board_cols].copy().sort_values(['Natty Odds', 'CFP Odds', 'Power Index'], ascending=False)
        board = board.rename(columns={'Current CFP Ranking': 'CFP Rank'})
        render_war_room_table(board)
        with st.expander('Show raw board data'):
            st.dataframe(board, hide_index=True, use_container_width=True)

    with tabs[0]:
        st.header("🗞️ Dynasty News")
        st.markdown(f"<h3 style='text-align:center;margin-bottom:0.75rem;'>Week {CURRENT_WEEK_NUMBER}'s Games</h3>", unsafe_allow_html=True)
        render_current_user_games_cards(current_user_games, model_2041, scores)
        st.markdown("---")
        st.success(f"**{title_favorite['USER']}** has the strongest title case entering 2041 because the model leans hardest on overall roster quality and raw team speed, then lets CFP position and pedigree finish the damn job.")
        st.info(f"**{most_dangerous['USER']}** owns the highest Power Index, which blends team strength, speed, blue-chip makeup, and dynasty history.")
        st.warning(f"**{collapse_team['USER']}** carries the highest volatility marker. The model sees real downside if things break wrong.")

        qb_boost_board = model_2041[model_2041['QB Tier'].isin(['Elite', 'Leader'])].sort_values(['Natty Odds', 'Power Index'], ascending=False)
        if not qb_boost_board.empty:
            qb_star = qb_boost_board.iloc[0]
            if qb_star['QB Tier'] == 'Elite':
                st.write(f"🧠 **QB headline:** {qb_star['USER']} has an **Elite** quarterback, and that spikes the ceiling like hell. The model treats that shit as a real title accelerator, not fluff.")
            else:
                st.write(f"🧠 **QB headline:** {qb_star['USER']} has a **Leader** at quarterback. Not superhero mode, but it's still a damn meaningful bump to CFP and natty odds.")

        doug_source = r_2041[(r_2041['USER'].astype(str).str.strip().str.title() == 'Doug') & (r_2041['TEAM'].astype(str).str.strip().str.lower() == 'florida')]
        doug_model = model_2041[(model_2041['USER'].astype(str).str.strip().str.title() == 'Doug') & (model_2041['TEAM'].astype(str).str.strip().str.lower() == 'florida')]
        doug_qb_tier = None
        doug_qb_flag = False
        if not doug_source.empty:
            doug_src = doug_source.iloc[-1]
            doug_qb_flag = yes_no_flag(doug_src.get('Qb is Ass (under 80)', 'No'))
            doug_qb_tier = qb_label(doug_src)
        if not doug_model.empty:
            doug_qb_tier = str(doug_model.iloc[0].get('QB Tier', doug_qb_tier or 'Unknown'))
            doug_qb_flag = doug_qb_flag or (doug_qb_tier == 'Ass')
        if doug_qb_flag or doug_qb_tier == 'Ass':
            st.error("☠️ **Doug/Florida QB update:** Florida's QB room is ass. The Gators can slap blue-chip makeup on this thing all they want, but that quarterback spot is still one ugly read away from turning the whole damn offense into a fire drill.")
        elif doug_qb_tier:
            st.info(f"Doug/Florida QB currently reads as **{doug_qb_tier}** in the latest file.")

        qb_disaster_board = model_2041[model_2041['QB Tier'] == 'Ass'].sort_values(['Natty Odds', 'Power Index'], ascending=True)
        if not qb_disaster_board.empty:
            qb_disaster = qb_disaster_board.iloc[0]
            st.write(f"💀 **QB disaster watch:** {qb_disaster['USER']} is rolling out an **Ass** QB situation. That's the kind of setup that can take a good roster and make it play like it forgot where the fuck the sticks are.")

        if not rivalry_df.empty:
            top_rivalry = rivalry_df.sort_values('Rivalry Score', ascending=False).iloc[0]
            st.write(f"🔥 **Rivalry of the year:** {top_rivalry['Matchup']} — {int(top_rivalry['Games'])} meetings, rivalry score {top_rivalry['Rivalry Score']}.")

    # --- WHO'S IN? ---
    with tabs[2]:
        st.header("🏆 Who's In? | CFP Bubble Watch")
        st.caption("Built from your uploaded CFP ranking screenshots, then sharpened with this app's SOS, resume, QB, recruiting, and roster-strength model. Current CFP standards are assumed: five highest-ranked conference champs get in, plus seven at-larges, with the top four seeds earning byes.")

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

        m1, m2, m3, m4 = st.columns(4)
        m1.metric('Projected Locks', int((cfp_board['CFP Make %'] >= 92).sum()))
        m2.metric('Last Team In', f"#{int(projected_field.iloc[-1]['Rank'])} {projected_field.iloc[-1]['Team']}")
        m3.metric('First Team Out', f"#{int(first_four_out.iloc[0]['Rank'])} {first_four_out.iloc[0]['Team']}")
        m4.metric('Best Bye Shot', f"{projected_field.sort_values('Bye %', ascending=False).iloc[0]['Team']} ({format_pct(projected_field['Bye %'].max(),1)})")

        st.subheader('Projected CFP Field')
        render_cfp_table(cfp_board)

        st.subheader('Playoff Bracket')
        render_playoff_bracket(projected_field)

        st.subheader('First Four Out')
        render_first_four_out(first_four_out)

        st.subheader('CFP Chaos Simulator')
        sim_team = st.selectbox('Pick a team to stress-test', cfp_board.sort_values('Rank')['Team'].tolist(), key='cfp_sim_team')
        sim_scenario = st.selectbox('Scenario', ['Win next game', 'Win over Top-12 team', 'Lose to ranked team', 'Lose to unranked team'], key='cfp_sim_scenario')
        sim_row = cfp_board[cfp_board['Team'] == sim_team].iloc[0]
        sim_result = simulate_cfp_chaos(sim_row, sim_scenario, cfp_board)

        s1, s2, s3, s4 = st.columns(4)
        s1.metric('Current CFP', format_pct(sim_row['CFP Make %'], 1), delta=f"{sim_result['CFP Make %'] - sim_row['CFP Make %']:+.1f}%")
        s2.metric('Current Bye', format_pct(sim_row['Bye %'], 1), delta=f"{sim_result['Bye %'] - sim_row['Bye %']:+.1f}%")
        s3.metric('New Record', sim_result['Record'])
        s4.metric('Projected Rank', f"#{int(sim_result['Rank'])}", delta=f"{int(sim_row['Rank']) - int(sim_result['Rank']):+d}")

        if sim_scenario == 'Lose to unranked team':
            st.warning(f"{sim_team} would set fire to a lot of goodwill with an unranked loss. The model treats that as a straight-up committee trust killer.")
        elif sim_scenario == 'Lose to ranked team':
            st.info(f"A ranked loss hurts {sim_team}, but it usually doesn't nuke the whole damn résumé unless the record was already hanging by a thread.")
        elif sim_scenario == 'Win over Top-12 team':
            st.success(f"That's a résumé steroid shot. A top-12 win would give {sim_team} a real committee argument and bye-path juice.")
        else:
            st.success(f"A clean win keeps {sim_team} moving and protects the committee relationship. No chaos, no stupid questions.")
    # --- RECRUITING RANKINGS ---
    with tabs[6]:
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
            lc1, lc2 = st.columns([0.35, 0.65])
            with lc1:
                render_logo(sp['Logo'], width=90)
            with lc2:
                st.markdown(f"### {sp['TEAM']} | {sp['USER']}")
                st.write(f"**Recent classes:** {sp['Recent Cycle']}")
                st.write(f"**Weighted avg rank:** {sp['Weighted Avg Rank'] if not pd.isna(sp['Weighted Avg Rank']) else '—'}")
                st.write(f"**Heat Index:** {sp['Heat Index']}")
                st.write(f"**Pipeline Score:** {sp['Pipeline Score']}")
                st.write(f"**Speed Recruiter Index:** {sp['Speed Recruiter Index']}")
                st.write(f"**Blue Chip % proxy:** {sp['Blue Chip %']}%")
                st.write(f"**Class Tier:** {sp['Class Tier']}")
                st.write(f"**Trajectory:** {sp['Trajectory']}")
                st.info(sp['Recruiting Blurb'])

    # --- H2H MATRIX ---
    with tabs[7]:
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
        st.header("📺 AI Dynasty Recap Engine")
        sel_year = st.selectbox("Select Season", years, key="season_year")
        y_data = scores[scores[meta['yr']] == sel_year].copy()

        champ_row = champs[champs['YEAR'] == sel_year]
        heisman_row = heisman[heisman[meta['h_yr']] == sel_year]
        coty_row = coty[coty[meta['c_yr']] == sel_year]

        c1, c2, c3 = st.columns(3)
        with c1:
            if not champ_row.empty:
                champ_team = champ_row.iloc[0]['Team']
                champ_user = champ_row.iloc[0]['user']
                champ_logo = get_logo_source(champ_team)
                lc1, lc2 = st.columns([0.28, 0.72])
                with lc1:
                    render_logo(champ_logo, width=64)
                with lc2:
                    st.success(f"🏆 National Champion: {champ_team} ({champ_user})")
            else:
                st.info("🏆 National Champion: not found")
        with c2:
            if not heisman_row.empty:
                st.success(f"🏅 Heisman: {heisman_row.iloc[0][meta['h_player']]} ({heisman_row.iloc[0][meta['h_school']]})")
            else:
                st.info("🏅 Heisman: not found")
        with c3:
            if not coty_row.empty:
                st.success(f"👔 COTY: {coty_row.iloc[0][meta['c_coach']]} ({coty_row.iloc[0][meta['c_school']]})")
            else:
                st.info("👔 COTY: not found")

        if not y_data.empty:
            user_games = y_data[
                (y_data['V_User_Final'].astype(str).str.upper() != 'CPU') &
                (y_data['H_User_Final'].astype(str).str.upper() != 'CPU') &
                (y_data['V_User_Final'] != y_data['H_User_Final'])
            ].copy()

            avg_m = round(y_data['Margin'].mean(), 1)

            if not user_games.empty:
                goty = user_games.loc[user_games['Margin'].idxmin()]

                if goty['V_Pts'] > goty['H_Pts']:
                    winner_user = goty['V_User_Final']
                    loser_user = goty['H_User_Final']
                    winner_team = goty['Visitor_Final']
                    loser_team = goty['Home_Final']
                else:
                    winner_user = goty['H_User_Final']
                    loser_user = goty['V_User_Final']
                    winner_team = goty['Home_Final']
                    loser_team = goty['Visitor_Final']

                roast_lines = [
                    f"{loser_user} snatched defeat from the jaws of competence.",
                    f"{loser_user} managed to turn a pressure moment into performance art.",
                    f"{loser_user} got all the way to the finish line and face-planted in front of the cameras."
                ]
                roast_line = roast_lines[int(goty['Margin']) % len(roast_lines)]

                st.info(
                    f"🏟️ Game of the Year: {goty['Visitor_Final']} at {goty['Home_Final']} | "
                    f"{winner_user} ({winner_team}) escaped by {int(goty['Margin'])}. "
                    f"{loser_user} ({loser_team}) was one stop away and still found a way to wear it. {roast_line}"
                )
            else:
                st.info("🏟️ Game of the Year: no user-vs-user games found for that season.")

            st.caption(f"Fun stat: {infer_best_fun_stat(y_data)}")
            st.write(
                f"**Narrative:** {sel_year} featured {len(user_games)} user battles. "
                f"The average margin across all logged games was {avg_m}, which points to "
                f"{'a season of wars' if avg_m <= 10 else 'a season with clear pecking-order moments'}."
            )

        st.dataframe(
            y_data[['Visitor_Final', 'V_User_Final', 'V_Pts', 'H_Pts', 'H_User_Final', 'Home_Final', 'Margin', 'Total Points']],
            hide_index=True,
            use_container_width=True
        )

    # --- TEAM OVERVIEW ---
    with tabs[5]:
        st.header("📊 Team Analysis")
        target = st.selectbox("Select Team", model_2041['USER'].tolist(), key="team_analysis_user")
        row = model_2041[model_2041['USER'] == target].iloc[0]

        wins, losses, ppg, avg_margin = get_team_schedule_summary(scores, target)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Natty Odds", f"{row['Natty Odds']}%")
        m2.metric("CFP Odds", f"{row['CFP Odds']}%")
        m3.metric("Projected Wins", row['Projected Wins'])
        m4.metric("Power Index", row['Power Index'])

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
            cpa, cpb, cpc = st.columns(3)
            cpa.metric("Career Win %", f"{coach_stats_row['Career Win %']}%")
            cpb.metric("Natties", int(coach_stats_row['Natties']))
            cpc.metric("CFP Wins", int(coach_stats_row['CFP Wins']))

        stat_table = pd.DataFrame([
            {'Metric': 'Overall', 'Value': row['OVERALL']},
            {'Metric': 'Offense', 'Value': row['OFFENSE']},
            {'Metric': 'Defense', 'Value': row['DEFENSE']},
            {'Metric': 'Off 90+ Speed Players', 'Value': row['Off Speed (90+ speed)']},
            {'Metric': 'Def 90+ Speed Players', 'Value': row['Def Speed (90+ speed)']},
            {'Metric': 'Total Team Speed', 'Value': row['Team Speed (90+ Speed Guys)']},
            {'Metric': 'Game Breakers', 'Value': row['Game Breakers (90+ Speed & 90+ Acceleration)']},
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
            'Category': ['Overall', 'Offense', 'Defense', 'Off Speed', 'Def Speed', 'Game Breakers', 'Generational'],
            'Score': [
                row['OVERALL'],
                row['OFFENSE'],
                row['DEFENSE'],
                row['Off Speed (90+ speed)'],
                row['Def Speed (90+ speed)'],
                row['Game Breakers (90+ Speed & 90+ Acceleration)'],
                row['Generational (96+ speed or 96+ Acceleration)']
            ]
        })
        st.plotly_chart(px.bar(detail_chart, x='Category', y='Score', text='Score'), use_container_width=True)

    # --- TALENT PROFILE ---
    with tabs[4]:
        st.header("🔍 2041 Speed Freaks")
        st.write("Detailed scouting of high-end athletic ceiling. TEAM SPEED is driven by total 90+ speed depth, but generational freaks act like multipliers that can launch a roster way up the board. On this dashboard, a TEAM SPEED score of 40 equals 65 MPH — anything above that is officially speeding.")

        talent_board = model_2041.copy()
        talent_board = talent_board.sort_values(
            ['Team Speed Score', 'Generational (96+ speed or 96+ Acceleration)', 'Team Speed (90+ Speed Guys)'],
            ascending=False
        ).reset_index(drop=True)
        talent_board['TEAM SPEED Rank'] = np.arange(1, len(talent_board) + 1)

        fastest_team = talent_board.iloc[0]
        st.subheader("⚡ TEAM SPEED Rankings")
        st.success(f"Fastest team alive right now: {fastest_team['TEAM']} ({fastest_team['USER']}) at {fastest_team['Speedometer']} MPH. Defensive coordinators should file a complaint.")
        render_speed_freaks_table(talent_board)

        for _, r in talent_board.iterrows():
            gens = int(r['Generational (96+ speed or 96+ Acceleration)'])
            team_speed = float(r.get('Team Speed Score', 0))
            tier = get_speed_tier(team_speed)
            gen_desc = get_pop_culture_speed_comp(gens)

            if gens == 0:
                bonus_desc = "No multiplier bonus here. This is a depth-and-discipline operation."
            elif gens == 1:
                bonus_desc = "One generational freak means the whole scouting report bends around a single superhero."
            else:
                bonus_desc = f"{gens} generational freaks means the speed depth gets turbocharged. This many cheat codes can vault a roster several spots higher than raw depth alone."

            with st.expander(f"#{int(r['TEAM SPEED Rank'])} {r['USER']} | {r['TEAM']} - {tier}"):
                st.write(gen_desc)
                st.write(bonus_desc)
                s1, s2, s3, s4 = st.columns(4)
                s1.metric("Speedometer", f"{float(r.get('Speedometer', r.get('Speed Limit MPH', 0)))} MPH")
                s2.metric("TEAM SPEED Score", f"{team_speed}")
                s3.metric("90+ Speed Players", int(r['Team Speed (90+ Speed Guys)']))
                s4.metric("Generational Freaks", gens)
                st.write(get_speeding_label(team_speed, gens))
                st.write(f"**Game breakers:** {int(r['Game Breakers (90+ Speed & 90+ Acceleration)'])}")
                st.write(f"**Offense 90+ speed:** {int(r['Off Speed (90+ speed)'])} | **Defense 90+ speed:** {int(r['Def Speed (90+ speed)'])}")
                st.write(f"**Where is the Speed?** {r['Where is the Speed?']}")
                st.write(f"**Blue Chip Ratio:** {int(r['BCR_Val'])}%")
                st.progress(min(1.0, team_speed / 100.0))

    # --- UPSET TRACKER ---
    with tabs[8]:
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
    with tabs[9]:
        st.header("🐐 Dynasty GOAT Rankings")
        goat = stats.copy().sort_values("GOAT Score", ascending=False).reset_index(drop=True)

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
    with tabs[10]:
        render_roster_matchup_tab()

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
