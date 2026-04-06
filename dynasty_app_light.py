
import os
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="CFB Dynasty Lite", layout="wide")

# ------------------------------------------------------------
# YEAR / WEEK CONTROL
# Set to an integer to force a season/week.
# Set to None to auto-detect from the repo files.
# ------------------------------------------------------------
MANUAL_YEAR = 2043
MANUAL_WEEK = 2

LOGO_DIRS = ["logos", "./logos"]

# ------------------------------------------------------------
# BASIC HELPERS
# ------------------------------------------------------------
def normalize_key(value: str) -> str:
    if value is None:
        return ""
    return "".join(ch.lower() for ch in str(value).strip() if ch.isalnum())

def safe_read_csv(path: str) -> pd.DataFrame:
    if not path or not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()

def infer_year_from_repo(default_year: int) -> int:
    candidates = []
    for pattern in ["schedule_*.csv", "team_ratings_*.csv", "bluechip_ratio_*.csv"]:
        for path in Path(".").glob(pattern):
            digits = "".join(ch for ch in path.stem if ch.isdigit())
            if len(digits) >= 4:
                candidates.append(int(digits[-4:]))
    return max(candidates) if candidates else default_year

def infer_week_from_repo(year: int, default_week: int) -> int:
    candidates = []
    for pattern in [f"fpi_ratings_{year}_wk*.csv", f"ms_plus_{year}_wk*.csv"]:
        for path in Path(".").glob(pattern):
            stem = path.stem
            marker = f"{year}_wk"
            if marker in stem:
                maybe = stem.split(marker, 1)[1]
                if maybe.isdigit():
                    candidates.append(int(maybe))
    return max(candidates) if candidates else default_week

def build_base_file_map(year: int) -> dict[str, str]:
    return {
        "schedule": f"schedule_{year}.csv",
        "game_summaries": "game_summaries.csv",
        "bluechip": f"bluechip_ratio_{year}.csv",
        "cfp_rankings": "cfp_rankings_history.csv",
        "team_conferences": "team_conferences.csv",
        "team_ratings": f"team_ratings_{year}.csv",
        "user_teams": "user_teams.csv",
        "week_game_status": "week_game_status.csv",
        "week_manual_scores": "week_manual_scores.csv",
        "team_visuals": "team_visuals.csv",
        "team_aliases": "team_aliases.csv",
        "cfp_bracket": "CFPbracketresults.csv",
        "injury_bulletin": "injury_bulletin.csv",
    }

def resolve_metric_path(prefix: str, year: int, week: int) -> tuple[str, int | None]:
    exact = Path(f"{prefix}_{year}_wk{week}.csv")
    if exact.exists():
        return str(exact), week
    candidates: list[tuple[int, str]] = []
    for path in Path(".").glob(f"{prefix}_{year}_wk*.csv"):
        stem = path.stem
        marker = f"{year}_wk"
        if marker in stem:
            maybe = stem.split(marker, 1)[1]
            if maybe.isdigit():
                candidates.append((int(maybe), str(path)))
    if not candidates:
        return f"{prefix}_{year}_wk{week}.csv", None
    valid_prior = [c for c in candidates if c[0] <= week]
    if valid_prior:
        chosen = max(valid_prior, key=lambda x: x[0])
    else:
        chosen = max(candidates, key=lambda x: x[0])
    return chosen[1], chosen[0]

def standardize_schedule_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    rename_map = {
        "YEAR": "Year",
        "Visitor": "AwayTeam",
        "Home": "HomeTeam",
        "Vis Score": "AwayScore",
        "Home Score": "HomeScore",
        "Visitor Rank": "AwayRank",
        "Home Rank": "HomeRank",
        "Vis_User": "AwayUser",
        "Home_User": "HomeUser",
        "Visitor Record": "AwayRecord",
        "Home Record": "HomeRecord",
    }
    for old, new in rename_map.items():
        if old in out.columns and new not in out.columns:
            out = out.rename(columns={old: new})
    return out

def standardize_other_frames(data: dict) -> dict:
    if not data["game_summaries"].empty:
        data["game_summaries"] = data["game_summaries"].rename(columns={
            "YEAR": "Year", "WEEK": "Week", "VISITOR": "AwayTeam", "HOME": "HomeTeam",
            "VIS_RANK": "AwayRank", "HOME_RANK": "HomeRank", "VIS_FINAL": "AwayScore",
            "HOME_FINAL": "HomeScore", "VIS_USER": "AwayUser", "HOME_USER": "HomeUser",
            "NOTES": "Summary",
        })
    if not data["cfp_rankings"].empty:
        data["cfp_rankings"] = data["cfp_rankings"].rename(columns={
            "YEAR": "Year", "WEEK": "Week", "TEAM": "Team", "RANK": "Rank", "RECORD": "Record"
        })
    if not data["bluechip"].empty:
        data["bluechip"] = data["bluechip"].rename(columns={
            "YEAR": "Year", "TEAM": "Team", "BLUE CHIP PERCENTAGE": "BlueChipRatio"
        })
    if not data["team_conferences"].empty:
        data["team_conferences"] = data["team_conferences"].rename(columns={
            "TEAM": "Team", "USER": "User", "CONFERENCE": "Conference", "YEAR_JOINED": "YearJoined"
        })
    if not data["team_ratings"].empty:
        data["team_ratings"] = data["team_ratings"].rename(columns={
            "YEAR": "Year", "TEAM": "Team", "OVR": "OVR", "OFF": "Off", "DEF": "Def"
        })
    if not data["cfp_bracket"].empty:
        data["cfp_bracket"] = data["cfp_bracket"].rename(columns={
            "YEAR": "Year", "ROUND": "Round", "GAME_ID": "GameID",
            "TEAM1": "Team1", "SEED1": "Seed1", "DISPLAY_RANK1": "DisplayRank1", "RECORD1": "Record1",
            "TEAM1_SCORE": "Team1Score", "TEAM2": "Team2", "SEED2": "Seed2", "DISPLAY_RANK2": "DisplayRank2",
            "RECORD2": "Record2", "TEAM2_SCORE": "Team2Score", "WINNER": "Winner", "LOSER": "Loser",
            "COMPLETED": "Completed", "SOURCE": "Source", "NOTES": "Notes"
        })
    return data

def build_alias_map(team_aliases_df: pd.DataFrame) -> dict[str, str]:
    alias_map = {}
    if team_aliases_df.empty:
        return alias_map
    team_col = "Team" if "Team" in team_aliases_df.columns else team_aliases_df.columns[0]
    alias_col = "Alias" if "Alias" in team_aliases_df.columns else (team_aliases_df.columns[1] if len(team_aliases_df.columns) > 1 else team_col)
    for _, row in team_aliases_df.iterrows():
        canonical = str(row.get(team_col, "")).strip()
        alias = str(row.get(alias_col, "")).strip()
        if canonical:
            alias_map[normalize_key(canonical)] = canonical
        if alias:
            alias_map[normalize_key(alias)] = canonical or alias
    return alias_map

def canonical_team_name(name: str, alias_map: dict[str, str]) -> str:
    raw = str(name or "").strip()
    if not raw:
        return ""
    return alias_map.get(normalize_key(raw), raw)

def build_visual_map(team_visuals_df: pd.DataFrame, alias_map: dict[str, str]) -> dict[str, dict]:
    out = {}
    if team_visuals_df.empty:
        return out
    cols = {c.lower(): c for c in team_visuals_df.columns}
    team_col = cols.get("team") or cols.get("school") or cols.get("name")
    primary_col = cols.get("primary") or cols.get("primary_color") or cols.get("primarycolor")
    secondary_col = cols.get("secondary") or cols.get("secondary_color") or cols.get("secondarycolor")
    if not team_col:
        return out
    for _, row in team_visuals_df.iterrows():
        team = canonical_team_name(row.get(team_col, ""), alias_map)
        if not team:
            continue
        out[team] = {
            "primary": str(row.get(primary_col, "#1f2937")).strip() if primary_col else "#1f2937",
            "secondary": str(row.get(secondary_col, "#94a3b8")).strip() if secondary_col else "#94a3b8",
        }
    return out

def get_team_colors(team: str, visual_map: dict[str, dict]) -> tuple[str, str]:
    visual = visual_map.get(team, {})
    return visual.get("primary", "#1f2937"), visual.get("secondary", "#94a3b8")

def find_logo_path(team_name: str, alias_map: dict[str, str]) -> str | None:
    team = canonical_team_name(team_name, alias_map)
    candidates = []
    raw_variants = [team, team_name]
    for raw in raw_variants:
        raw = str(raw or "").strip()
        if not raw:
            continue
        parts = raw.replace("&", "and").replace("-", " ").split()
        camel = parts[0].lower() + "".join(p[:1].upper() + p[1:] for p in parts[1:]) if parts else ""
        candidates.extend([normalize_key(raw), normalize_key(camel), raw.replace(" ", ""), raw])
    seen = []
    for c in candidates:
        if c and c not in seen:
            seen.append(c)
    for folder in LOGO_DIRS:
        for candidate in seen:
            path = Path(folder) / f"{candidate}.png"
            if path.exists():
                return str(path)
    return None

def merge_manual_scores(schedule_df: pd.DataFrame, manual_scores_df: pd.DataFrame, alias_map: dict[str, str]) -> pd.DataFrame:
    if schedule_df.empty:
        return schedule_df
    df = standardize_schedule_columns(schedule_df.copy())
    for col in ["HomeTeam", "AwayTeam"]:
        if col in df.columns:
            df[col] = df[col].map(lambda x: canonical_team_name(x, alias_map))
    if manual_scores_df.empty:
        return df
    ms = standardize_schedule_columns(manual_scores_df.copy())
    for col in ["HomeTeam", "AwayTeam"]:
        if col in ms.columns:
            ms[col] = ms[col].map(lambda x: canonical_team_name(x, alias_map))
    key_cols = [c for c in ["Year", "Week", "HomeTeam", "AwayTeam"] if c in df.columns and c in ms.columns]
    if not key_cols:
        return df
    merged = df.merge(ms, on=key_cols, how="left", suffixes=("", "_manual"))
    for base, manual in [("HomeScore", "HomeScore_manual"), ("AwayScore", "AwayScore_manual"), ("Status", "Status_manual")]:
        if base in merged.columns and manual in merged.columns:
            merged[base] = merged[manual].combine_first(merged[base])
    return merged.drop(columns=[c for c in merged.columns if c.endswith("_manual")], errors="ignore")

def load_data() -> dict:
    active_year = MANUAL_YEAR if MANUAL_YEAR is not None else infer_year_from_repo(2043)
    active_week = MANUAL_WEEK if MANUAL_WEEK is not None else infer_week_from_repo(active_year, 1)
    file_map = build_base_file_map(active_year)
    fpi_path, fpi_week_used = resolve_metric_path("fpi_ratings", active_year, active_week)
    ms_path, ms_week_used = resolve_metric_path("ms_plus", active_year, active_week)
    file_map["fpi"] = fpi_path
    file_map["ms_plus"] = ms_path

    data = {k: safe_read_csv(v) for k, v in file_map.items()}
    data["schedule"] = standardize_schedule_columns(data["schedule"])
    data["week_manual_scores"] = standardize_schedule_columns(data["week_manual_scores"])
    data = standardize_other_frames(data)

    alias_map = build_alias_map(data["team_aliases"])
    for frame_name in ["schedule", "game_summaries", "bluechip", "cfp_rankings", "fpi", "ms_plus", "team_conferences", "team_ratings", "user_teams", "week_game_status", "week_manual_scores", "cfp_bracket", "injury_bulletin"]:
        df = data[frame_name]
        if df.empty:
            continue
        for col in [c for c in df.columns if "team" in c.lower() or c.lower() in {"winner", "loser", "home", "away", "visitor", "school", "program"}]:
            try:
                df[col] = df[col].map(lambda x: canonical_team_name(x, alias_map))
            except Exception:
                pass
        data[frame_name] = df

    data["schedule"] = merge_manual_scores(data["schedule"], data["week_manual_scores"], alias_map)
    data["alias_map"] = alias_map
    data["visual_map"] = build_visual_map(data["team_visuals"], alias_map)
    data["active_year"] = active_year
    data["active_week"] = active_week
    data["file_map"] = file_map
    data["fpi_week_used"] = fpi_week_used
    data["ms_week_used"] = ms_week_used
    return data

@st.cache_data(ttl=300)
def get_data() -> dict:
    return load_data()

# ------------------------------------------------------------
# DOMAIN HELPERS
# ------------------------------------------------------------
def resolve_current_week(schedule_df: pd.DataFrame, game_status_df: pd.DataFrame, fallback_week: int) -> int:
    if not game_status_df.empty:
        for col in ["Week", "week"]:
            if col in game_status_df.columns:
                vals = pd.to_numeric(game_status_df[col], errors="coerce").dropna()
                if not vals.empty:
                    return int(vals.max())
    if not schedule_df.empty and "Week" in schedule_df.columns:
        vals = pd.to_numeric(schedule_df["Week"], errors="coerce").dropna()
        if not vals.empty:
            return int(vals.max())
    return fallback_week

def get_user_team_list(user_teams_df: pd.DataFrame, alias_map: dict[str, str], schedule_df: pd.DataFrame | None = None) -> list[str]:
    if not user_teams_df.empty:
        cols = {c.lower(): c for c in user_teams_df.columns}
        for name in ["team", "school", "program"]:
            col = cols.get(name)
            if col:
                vals = [canonical_team_name(v, alias_map) for v in user_teams_df[col].dropna().astype(str).tolist()]
                vals = [v for v in vals if v]
                if vals:
                    return list(dict.fromkeys(vals))
        vals = [canonical_team_name(v, alias_map) for v in user_teams_df.astype(str).stack().tolist() if str(v).strip() and str(v).lower() != "nan"]
        if vals:
            return list(dict.fromkeys(vals))
    if schedule_df is not None and not schedule_df.empty:
        derived = []
        if "HomeUser" in schedule_df.columns and "HomeTeam" in schedule_df.columns:
            derived.extend(schedule_df.loc[schedule_df["HomeUser"].notna() & (schedule_df["HomeUser"].astype(str).str.strip() != ""), "HomeTeam"].astype(str).tolist())
        if "AwayUser" in schedule_df.columns and "AwayTeam" in schedule_df.columns:
            derived.extend(schedule_df.loc[schedule_df["AwayUser"].notna() & (schedule_df["AwayUser"].astype(str).str.strip() != ""), "AwayTeam"].astype(str).tolist())
        derived = [canonical_team_name(v, alias_map) for v in derived if str(v).strip()]
        return list(dict.fromkeys(derived))
    return []

def get_latest_rankings(cfp_rankings_df: pd.DataFrame, active_year: int) -> pd.DataFrame:
    if cfp_rankings_df.empty or "Team" not in cfp_rankings_df.columns or "Rank" not in cfp_rankings_df.columns:
        return pd.DataFrame(columns=["Team", "Rank"])
    df = cfp_rankings_df.copy()
    if "Year" in df.columns:
        df = df[pd.to_numeric(df["Year"], errors="coerce").fillna(active_year).astype(int) == active_year]
    if "Week" in df.columns:
        latest_week = pd.to_numeric(df["Week"], errors="coerce").dropna().max()
        if pd.notna(latest_week):
            df = df[pd.to_numeric(df["Week"], errors="coerce") == latest_week]
    out = pd.DataFrame({"Team": df["Team"].astype(str).str.strip(), "Rank": pd.to_numeric(df["Rank"], errors="coerce")})
    out = out.dropna(subset=["Team"]).sort_values("Rank", na_position="last")
    return out.drop_duplicates(subset=["Team"], keep="first")

def get_fpi_ms_table(fpi_df: pd.DataFrame, ms_df: pd.DataFrame) -> pd.DataFrame:
    def normalize_metric_df(df: pd.DataFrame, value_name: str) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=["Team", value_name])
        cols = {c.lower(): c for c in df.columns}
        team_col = cols.get("team") or cols.get("school") or cols.get("program")
        if value_name == "MS+":
            value_col = cols.get("ms+") or cols.get("msplus") or cols.get("ms_plus")
        else:
            value_col = cols.get(value_name.lower())
        if not value_col:
            preferred = [c for c in df.columns if c.lower() in {"rating", "value", "fpi", "ms+", "ms_plus", "msplus"}]
            if preferred:
                value_col = preferred[0]
        if not value_col:
            numeric_candidates = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and c.lower() not in {"year", "week", "rank"}]
            value_col = numeric_candidates[0] if numeric_candidates else None
        if not team_col or not value_col:
            return pd.DataFrame(columns=["Team", value_name])
        return pd.DataFrame({"Team": df[team_col].astype(str).str.strip(), value_name: pd.to_numeric(df[value_col], errors="coerce")})
    merged = pd.merge(normalize_metric_df(fpi_df, "FPI"), normalize_metric_df(ms_df, "MS+"), on="Team", how="outer")
    return merged

def score_columns(df: pd.DataFrame) -> tuple[str | None, str | None]:
    for home_col, away_col in [("HomeScore", "AwayScore"), ("ScoreHome", "ScoreAway")]:
        if home_col in df.columns and away_col in df.columns:
            return home_col, away_col
    return None, None

def build_game_status_lookup(game_status_df: pd.DataFrame, schedule_df: pd.DataFrame) -> dict[tuple[str, str], str]:
    lookup = {}
    if not game_status_df.empty:
        cols = {c.lower(): c for c in game_status_df.columns}
        home_col = cols.get("hometeam") or cols.get("home")
        away_col = cols.get("awayteam") or cols.get("away") or cols.get("visitor")
        status_col = cols.get("status") or cols.get("game_status")
        if home_col and away_col and status_col:
            for _, row in game_status_df.iterrows():
                lookup[(str(row.get(home_col, "")).strip(), str(row.get(away_col, "")).strip())] = str(row.get(status_col, "")).strip()
    if not lookup and not schedule_df.empty and "Status" in schedule_df.columns:
        for _, row in schedule_df.iterrows():
            home = str(row.get("HomeTeam", "")).strip()
            away = str(row.get("AwayTeam", "")).strip()
            if home and away:
                lookup[(home, away)] = str(row.get("Status", "Scheduled")).strip()
    return lookup

def status_chip_html(status: str, count: int) -> str:
    status_u = str(status or "SCHEDULED").upper()
    color_map = {
        "FINAL": ("#22c55e", "rgba(34,197,94,0.16)", "#dcfce7"),
        "LIVE": ("#ef4444", "rgba(239,68,68,0.16)", "#fee2e2"),
        "IN PROGRESS": ("#ef4444", "rgba(239,68,68,0.16)", "#fee2e2"),
        "SCHEDULED": ("#38bdf8", "rgba(56,189,248,0.16)", "#e0f2fe"),
        "BYE": ("#a78bfa", "rgba(167,139,250,0.16)", "#ede9fe"),
    }
    border, bg, fg = color_map.get(status_u, ("#94a3b8", "rgba(148,163,184,0.16)", "#e2e8f0"))
    return f"<span style='display:inline-block;padding:8px 12px;border-radius:999px;border:1px solid {border};background:{bg};color:{fg};font-size:.78rem;font-weight:900;margin:0 8px 10px 0;'>{status_u} • {count}</span>"

# ------------------------------------------------------------
# RENDERERS
# ------------------------------------------------------------
def render_sidebar(data: dict) -> None:
    st.sidebar.title("Dynasty Lite")
    st.sidebar.caption(f"Year {data.get('active_year', MANUAL_YEAR or 2043)} • Week {data.get('active_week', MANUAL_WEEK or 1)}")
    st.sidebar.markdown("### Rollover")
    st.sidebar.caption("Set MANUAL_YEAR / MANUAL_WEEK at the top of the file, or set them to None and let the app auto-detect the newest season/week from the repo.")
    st.sidebar.markdown("### Metrics file in use")

    file_map = data.get('file_map', {}) or {}
    fpi_path = file_map.get('fpi', '')
    ms_path = file_map.get('ms_plus', '')
    fpi_week_used = data.get('fpi_week_used')
    ms_week_used = data.get('ms_week_used')

    fpi_label = Path(fpi_path).name if fpi_path else 'No FPI file found'
    ms_label = Path(ms_path).name if ms_path else 'No MS+ file found'

    st.sidebar.caption(f"FPI: {fpi_label}" + (f" (wk {fpi_week_used})" if fpi_week_used is not None else ""))
    st.sidebar.caption(f"MS+: {ms_label}" + (f" (wk {ms_week_used})" if ms_week_used is not None else ""))

    missing = [path for path in file_map.values() if path and not os.path.exists(path)]
    if missing:
        st.sidebar.warning("Missing files in repo:")
        for path in missing:
            st.sidebar.caption(f"• {path}")

def render_status_signifiers(cards_df: pd.DataFrame) -> None:
    if cards_df.empty or "Status" not in cards_df.columns:
        return
    counts = cards_df["Status"].fillna("SCHEDULED").astype(str).str.upper().value_counts().to_dict()
    preferred_order = ["FINAL", "LIVE", "IN PROGRESS", "SCHEDULED", "BYE"]
    html = "".join(status_chip_html(status, counts[status]) for status in preferred_order if status in counts)
    if html:
        st.markdown(f"<div style='margin:4px 0 14px 0;'>{html}</div>", unsafe_allow_html=True)

def render_team_card(row: pd.Series, rankings: pd.DataFrame, metrics: pd.DataFrame, visual_map: dict[str, dict], alias_map: dict[str, str], status_lookup: dict[tuple[str, str], str]) -> None:
    home = str(row.get("HomeTeam", "")).strip()
    away = str(row.get("AwayTeam", "")).strip()
    week = int(pd.to_numeric(row.get("Week", 0), errors="coerce") or 0)
    home_score_col, away_score_col = score_columns(pd.DataFrame([row]))
    home_score = row.get(home_score_col) if home_score_col else None
    away_score = row.get(away_score_col) if away_score_col else None
    tv = str(row.get("TV_Broadcast", "")).strip() if "TV_Broadcast" in row.index else ""
    kickoff = str(row.get("Kickoff_Time", "")).strip() if "Kickoff_Time" in row.index else ""

    def team_meta(team: str):
        rank_row = rankings[rankings["Team"] == team]
        rank = f"#{int(rank_row.iloc[0]['Rank'])}" if not rank_row.empty and pd.notna(rank_row.iloc[0]["Rank"]) else "Unranked"
        metric_row = metrics[metrics["Team"] == team]
        fpi = "—"
        ms = "—"
        if not metric_row.empty:
            if pd.notna(metric_row.iloc[0].get("FPI")):
                fpi = f"{float(metric_row.iloc[0]['FPI']):.1f}"
            if pd.notna(metric_row.iloc[0].get("MS+")):
                ms = f"{float(metric_row.iloc[0]['MS+']):.1f}"
        logo = find_logo_path(team, alias_map)
        return rank, fpi, ms, logo

    home_rank, home_fpi, home_ms, home_logo = team_meta(home)
    away_rank, away_fpi, away_ms, away_logo = team_meta(away)
    home_primary, home_secondary = get_team_colors(home, visual_map)
    away_primary, away_secondary = get_team_colors(away, visual_map)
    status = status_lookup.get((home, away), str(row.get("Status", "Scheduled")).strip() or "Scheduled")

    st.markdown("""
    <style>
    .dyn-card{border-radius:20px;padding:18px 20px;background:linear-gradient(180deg, rgba(7,12,20,.96), rgba(17,24,39,.98));border:1px solid rgba(255,255,255,.08);margin-bottom:16px;box-shadow:0 10px 24px rgba(0,0,0,.28);}
    .dyn-rank{display:inline-block;padding:4px 10px;border-radius:999px;font-size:.72rem;font-weight:900;color:#fff;letter-spacing:.04em}
    .dyn-center{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;}
    .dyn-vs{font-size:1.7rem;font-weight:900;color:#fff;line-height:1.0}
    .dyn-sub{font-size:.82rem;color:#cbd5e1;font-weight:700;margin-top:6px;text-align:center}
    .dyn-meta{font-size:.76rem;color:#94a3b8;font-weight:800;text-transform:uppercase;letter-spacing:.08em}
    </style>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown("<div class='dyn-card'>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1.5, 0.9, 1.5])
        with c1:
            if home_logo:
                st.image(home_logo, width=72)
            st.markdown(f"### {home}")
            st.markdown(f"<span class='dyn-rank' style='background:{home_primary}; border:1px solid {home_secondary};'>{home_rank}</span>", unsafe_allow_html=True)
            st.caption(f"FPI {home_fpi} • MS+ {home_ms}")
            if home_score is not None and pd.notna(home_score):
                st.metric("Score", int(float(home_score)))
        with c2:
            st.markdown("<div class='dyn-center'>", unsafe_allow_html=True)
            st.markdown(f"<div class='dyn-meta'>Week {week}</div>", unsafe_allow_html=True)
            st.markdown("<div class='dyn-vs'>VS</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='dyn-sub'>{status}</div>", unsafe_allow_html=True)
            if tv:
                st.markdown(f"<div class='dyn-sub'>📺 {tv}</div>", unsafe_allow_html=True)
            if kickoff and kickoff.lower() != 'nan':
                st.markdown(f"<div class='dyn-sub'>🕒 {kickoff}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with c3:
            if away_logo:
                st.image(away_logo, width=72)
            st.markdown(f"### {away}")
            st.markdown(f"<span class='dyn-rank' style='background:{away_primary}; border:1px solid {away_secondary};'>{away_rank}</span>", unsafe_allow_html=True)
            st.caption(f"FPI {away_fpi} • MS+ {away_ms}")
            if away_score is not None and pd.notna(away_score):
                st.metric("Score", int(float(away_score)))
        st.markdown("</div>", unsafe_allow_html=True)

def render_user_cards_section(data: dict) -> None:
    st.subheader("User Dynasty Games")
    alias_map = data["alias_map"]
    rankings = get_latest_rankings(data["cfp_rankings"], data["active_year"])
    metrics = get_fpi_ms_table(data["fpi"], data["ms_plus"])
    user_teams = get_user_team_list(data["user_teams"], alias_map, data["schedule"])
    status_lookup = build_game_status_lookup(data["week_game_status"], data["schedule"])

    cards_df = data["schedule"].copy()
    latest_week = resolve_current_week(cards_df, data["week_game_status"], data["active_week"])
    if "Week" in cards_df.columns:
        cards_df = cards_df[pd.to_numeric(cards_df["Week"], errors="coerce") == latest_week].copy()
    if user_teams:
        cards_df = cards_df[cards_df["HomeTeam"].isin(user_teams) | cards_df["AwayTeam"].isin(user_teams)].copy()

    if cards_df.empty:
        st.info("No user-team games found for the current week.")
        return

    render_status_signifiers(cards_df)
    for _, row in cards_df.iterrows():
        render_team_card(row, rankings, metrics, data["visual_map"], alias_map, status_lookup)

def render_fpi_ms_section(data: dict) -> None:
    st.subheader("FPI + MS+ Ratings")
    merged = get_fpi_ms_table(data["fpi"], data["ms_plus"])
    if merged.empty:
        st.info("FPI/MS+ files were not found or could not be read.")
        return
    rankings = get_latest_rankings(data["cfp_rankings"], data["active_year"])
    merged = merged.merge(rankings, on="Team", how="left")
    merged = merged.sort_values(["Rank", "FPI", "MS+"], ascending=[True, False, False], na_position="last")
    c1, c2 = st.columns(2)
    with c1:
        top_fpi = merged.dropna(subset=["FPI"]).head(12)
        if not top_fpi.empty:
            fig = px.bar(top_fpi, x="FPI", y="Team", orientation="h", title="Top FPI", height=500)
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        top_ms = merged.dropna(subset=["MS+"]).head(12)
        if not top_ms.empty:
            fig = px.bar(top_ms, x="MS+", y="Team", orientation="h", title="Top MS+", height=500)
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)
    st.dataframe(merged[[c for c in ["Rank", "Team", "FPI", "MS+"] if c in merged.columns]], hide_index=True, use_container_width=True)

def render_who_would_win(data: dict) -> None:
    st.subheader("Who Would Win?")
    metrics = get_fpi_ms_table(data["fpi"], data["ms_plus"])
    df = data["schedule"].copy()
    if df.empty:
        st.info("No current-week matchups available.")
        return
    latest_week = resolve_current_week(df, data["week_game_status"], data["active_week"])
    if "Week" in df.columns:
        df = df[pd.to_numeric(df["Week"], errors="coerce") == latest_week].copy()
    if df.empty:
        st.info("No current-week matchups available.")
        return
    home = metrics.rename(columns={"Team": "HomeTeam", "FPI": "HomeFPI", "MS+": "HomeMS"})
    away = metrics.rename(columns={"Team": "AwayTeam", "FPI": "AwayFPI", "MS+": "AwayMS"})
    df = df.merge(home, on="HomeTeam", how="left").merge(away, on="AwayTeam", how="left")
    df["HomeEdge"] = df[["HomeFPI", "HomeMS"]].mean(axis=1) - df[["AwayFPI", "AwayMS"]].mean(axis=1)

    def winner_label(r):
        edge = r.get("HomeEdge")
        if pd.isna(edge):
            return "Too close to call"
        if edge > 1.5:
            return r.get("HomeTeam", "")
        if edge < -1.5:
            return r.get("AwayTeam", "")
        return "Too close to call"
    df["Prediction"] = df.apply(winner_label, axis=1)
    cols = [c for c in ["Week", "HomeTeam", "AwayTeam", "HomeFPI", "AwayFPI", "HomeMS", "AwayMS", "Prediction"] if c in df.columns]
    st.dataframe(df[cols], hide_index=True, use_container_width=True)

def render_highest_rated_games(data: dict) -> None:
    st.subheader("Highest Rated Games of the Season")
    schedule = data["schedule"].copy()
    rankings = get_latest_rankings(data["cfp_rankings"], data["active_year"])
    summaries = data["game_summaries"].copy()
    if schedule.empty:
        st.info("No rated games available yet.")
        return
    if "Year" in schedule.columns:
        schedule = schedule[pd.to_numeric(schedule["Year"], errors="coerce").fillna(data["active_year"]).astype(int) == data["active_year"]]
    home_col, away_col = score_columns(schedule)
    if home_col and away_col:
        schedule = schedule.dropna(subset=[home_col, away_col], how="all")
    home_r = rankings.rename(columns={"Team": "HomeTeam", "Rank": "HomeRank"})
    away_r = rankings.rename(columns={"Team": "AwayTeam", "Rank": "AwayRank"})
    games = schedule.merge(home_r, on="HomeTeam", how="left").merge(away_r, on="AwayTeam", how="left")
    games["RankScore"] = (26 - games["HomeRank"].fillna(26)) + (26 - games["AwayRank"].fillna(26))
    if not summaries.empty:
        keep_cols = [c for c in ["Year", "Week", "HomeTeam", "AwayTeam", "Summary"] if c in summaries.columns]
        join_cols = [c for c in ["Year", "Week", "HomeTeam", "AwayTeam"] if c in keep_cols and c in games.columns]
        if join_cols:
            games = games.merge(summaries[join_cols + ["Summary"]].drop_duplicates(), on=join_cols, how="left")
    games = games.sort_values(["RankScore", "Week"], ascending=[False, False]).head(12)
    display_cols = [c for c in ["Week", "HomeTeam", "AwayTeam", "HomeRank", "AwayRank", "Summary"] if c in games.columns]
    st.dataframe(games[display_cols], hide_index=True, use_container_width=True)

def render_injury_report(data: dict) -> None:
    st.subheader("Injury Report")
    df = data["injury_bulletin"].copy()
    if df.empty:
        st.info("No injury bulletin file found.")
        return
    if "Year" in df.columns:
        df = df[pd.to_numeric(df["Year"], errors="coerce").fillna(data["active_year"]).astype(int) == data["active_year"]]
    if "Week" in df.columns and df["Week"].notna().any():
        df = df[pd.to_numeric(df["Week"], errors="coerce").fillna(data["active_week"]).astype(int) <= data["active_week"]]
    st.dataframe(df, hide_index=True, use_container_width=True)

def render_dynasty_news(data: dict) -> None:
    st.title(f"Dynasty News — {data['active_year']} Week {data['active_week']}")
    render_user_cards_section(data)
    st.divider()
    render_fpi_ms_section(data)
    st.divider()
    render_who_would_win(data)
    st.divider()
    render_highest_rated_games(data)
    st.divider()
    render_injury_report(data)

def render_season_recap(data: dict) -> None:
    st.title(f"Season Recap — {data['active_year']}")
    rankings = get_latest_rankings(data["cfp_rankings"], data["active_year"])
    bracket = data["cfp_bracket"].copy()
    bluechip = data["bluechip"].copy()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Latest CFP Rankings")
        if rankings.empty:
            st.info("No CFP rankings found.")
        else:
            st.dataframe(rankings.head(25), hide_index=True, use_container_width=True)
    with c2:
        st.subheader("Blue-Chip Ratio")
        if bluechip.empty:
            st.info("No blue-chip ratio file found.")
        else:
            if "Year" in bluechip.columns:
                bluechip = bluechip[pd.to_numeric(bluechip["Year"], errors="coerce").fillna(data["active_year"]).astype(int) == data["active_year"]]
            st.dataframe(bluechip[[c for c in ["Team", "BlueChipRatio"] if c in bluechip.columns]], hide_index=True, use_container_width=True)
    st.subheader("CFP Bracket Results")
    if bracket.empty:
        st.info("No bracket results found.")
    else:
        if "Year" in bracket.columns:
            bracket = bracket[pd.to_numeric(bracket["Year"], errors="coerce").fillna(data["active_year"]).astype(int) == data["active_year"]]
        display_cols = [c for c in ["Round", "Team1", "Team1Score", "Team2", "Team2Score", "Winner", "Loser", "Completed"] if c in bracket.columns]
        st.dataframe(bracket[display_cols] if display_cols else bracket, hide_index=True, use_container_width=True)

def render_h2h_matrix(data: dict) -> None:
    st.title("H2H Matrix")
    schedule = data["schedule"].copy()
    if schedule.empty:
        st.info("No schedule file found.")
        return
    home_score_col, away_score_col = score_columns(schedule)
    if not home_score_col or not away_score_col:
        st.info("Schedule file does not contain score columns yet.")
        return
    played = schedule.dropna(subset=[home_score_col, away_score_col]).copy()
    if played.empty:
        st.info("No completed games available for H2H matrix.")
        return
    teams = sorted(set(played["HomeTeam"].dropna().astype(str)) | set(played["AwayTeam"].dropna().astype(str)))
    matrix = pd.DataFrame("", index=teams, columns=teams)
    for _, row in played.iterrows():
        home = str(row["HomeTeam"])
        away = str(row["AwayTeam"])
        hs = int(float(row[home_score_col]))
        aw = int(float(row[away_score_col]))
        matrix.loc[home, away] = f"W {hs}-{aw}" if hs > aw else f"L {hs}-{aw}"
        matrix.loc[away, home] = f"W {aw}-{hs}" if aw > hs else f"L {aw}-{hs}"
    st.dataframe(matrix, use_container_width=True)

def main():
    data = get_data()
    render_sidebar(data)
    tab1, tab2, tab3 = st.tabs(["Dynasty News", "Season Recap", "H2H Matrix"])
    with tab1:
        render_dynasty_news(data)
    with tab2:
        render_season_recap(data)
    with tab3:
        render_h2h_matrix(data)

if __name__ == "__main__":
    main()
