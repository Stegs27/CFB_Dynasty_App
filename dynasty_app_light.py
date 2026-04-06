
import hashlib
import os
from pathlib import Path
import html
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="CFB Dynasty Lite", layout="wide")

# ─────────────────────────────────────────────────────────────────────────────
# YEAR / WEEK CONTROL
# Set to an integer to force a season/week.
# Set to None to auto-detect from the repo files.
# ─────────────────────────────────────────────────────────────────────────────
MANUAL_YEAR = 2043
MANUAL_WEEK = 2

LOGO_DIRS = ["logos", "./logos"]

# ─────────────────────────────────────────────────────────────────────────────
# FILE MAP
# ─────────────────────────────────────────────────────────────────────────────
def build_file_map(year: int, week: int) -> dict[str, str]:
    return {
        "schedule":          f"schedule_{year}.csv",
        "game_summaries":    "game_summaries.csv",
        "bluechip":          f"bluechip_ratio_{year}.csv",
        "cfp_rankings":      "cfp_rankings_history.csv",
        "fpi":               f"fpi_ratings_{year}_wk{week}.csv",
        "ms_plus":           f"ms_plus_{year}_wk{week}.csv",
        "team_conferences":  "team_conferences.csv",
        "team_ratings":      f"team_ratings_{year}.csv",
        "user_teams":        "user_teams.csv",
        "week_game_status":  "week_game_status.csv",
        "week_manual_scores":"week_manual_scores.csv",
        "team_visuals":      "team_visuals.csv",
        "team_aliases":      "team_aliases.csv",
        "cfp_bracket":       "CFPbracketresults.csv",
        "injury_bulletin":   "injury_bulletin.csv",
    }

# ─────────────────────────────────────────────────────────────────────────────
# BASIC HELPERS
# ─────────────────────────────────────────────────────────────────────────────
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

def infer_week_candidates(year: int) -> list[int]:
    candidates = []
    for pattern in [f"fpi_ratings_{year}_wk*.csv", f"ms_plus_{year}_wk*.csv"]:
        for path in Path(".").glob(pattern):
            stem = path.stem
            marker = f"{year}_wk"
            if marker in stem:
                maybe = stem.split(marker, 1)[1]
                if maybe.isdigit():
                    candidates.append(int(maybe))
    return sorted(set(candidates))

def pick_metric_file(prefix: str, year: int, requested_week: int) -> tuple[str, int | None]:
    exact = f"{prefix}_{year}_wk{requested_week}.csv"
    if os.path.exists(exact):
        return exact, requested_week
    candidates = infer_week_candidates(year)
    prior = [w for w in candidates if w <= requested_week]
    if prior:
        use_week = max(prior)
        return f"{prefix}_{year}_wk{use_week}.csv", use_week
    if candidates:
        use_week = max(candidates)
        return f"{prefix}_{year}_wk{use_week}.csv", use_week
    return exact, None

def standardize_schedule_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    rename_map = {
        "YEAR":           "Year",
        "Visitor":        "AwayTeam",
        "Home":           "HomeTeam",
        "Vis Score":      "AwayScore",
        "Home Score":     "HomeScore",
        "Visitor Rank":   "AwayRank",
        "Home Rank":      "HomeRank",
        "Vis_User":       "AwayUser",
        "Home_User":      "HomeUser",
        "Visitor Record": "AwayRecord",
        "Home Record":    "HomeRecord",
        "Status":         "Status",
    }
    for old, new in rename_map.items():
        if old in out.columns and new not in out.columns:
            out = out.rename(columns={old: new})
    return out

def standardize_other_frames(data: dict) -> dict:
    if not data["game_summaries"].empty:
        data["game_summaries"] = data["game_summaries"].rename(columns={
            "YEAR": "Year", "WEEK": "Week",
            "VISITOR": "AwayTeam", "HOME": "HomeTeam",
            "VIS_RANK": "AwayRank", "HOME_RANK": "HomeRank",
            "VIS_FINAL": "AwayScore", "HOME_FINAL": "HomeScore",
            "VIS_USER": "AwayUser", "HOME_USER": "HomeUser",
            "NOTES": "Summary", "HEADLINE": "Headline",
        })
    if not data["cfp_rankings"].empty:
        data["cfp_rankings"] = data["cfp_rankings"].rename(columns={
            "YEAR": "Year", "WEEK": "Week", "TEAM": "Team",
            "RANK": "Rank", "RECORD": "Record",
        })
    if not data["bluechip"].empty:
        data["bluechip"] = data["bluechip"].rename(columns={
            "YEAR": "Year", "TEAM": "Team",
            "BLUE CHIP PERCENTAGE": "BlueChipRatio",
        })
    if not data["team_conferences"].empty:
        data["team_conferences"] = data["team_conferences"].rename(columns={
            "TEAM": "Team", "USER": "User",
            "CONFERENCE": "Conference", "YEAR_JOINED": "YearJoined",
        })
    if not data["team_ratings"].empty:
        data["team_ratings"] = data["team_ratings"].rename(columns={
            "YEAR": "Year", "TEAM": "Team",
            "OVR": "OVR", "OFF": "Off", "DEF": "Def",
        })
    if not data["cfp_bracket"].empty:
        data["cfp_bracket"] = data["cfp_bracket"].rename(columns={
            "YEAR": "Year", "ROUND": "Round", "GAME_ID": "GameID",
            "TEAM1": "Team1", "SEED1": "Seed1",
            "DISPLAY_RANK1": "DisplayRank1", "RECORD1": "Record1",
            "TEAM1_SCORE": "Team1Score", "TEAM2": "Team2", "SEED2": "Seed2",
            "DISPLAY_RANK2": "DisplayRank2", "RECORD2": "Record2",
            "TEAM2_SCORE": "Team2Score", "WINNER": "Winner", "LOSER": "Loser",
            "COMPLETED": "Completed", "SOURCE": "Source", "NOTES": "Notes",
        })
    return data

def build_alias_map(team_aliases_df: pd.DataFrame) -> dict[str, str]:
    alias_map: dict[str, str] = {}
    if team_aliases_df.empty:
        return alias_map
    if "Team" in team_aliases_df.columns and "Alias" in team_aliases_df.columns:
        for _, row in team_aliases_df.iterrows():
            canonical = str(row.get("Team", "")).strip()
            alias = str(row.get("Alias", "")).strip()
            if canonical:
                alias_map[normalize_key(canonical)] = canonical
            if alias:
                alias_map[normalize_key(alias)] = canonical or alias
    else:
        for _, row in team_aliases_df.iterrows():
            vals = [str(v).strip() for v in row.tolist()
                    if str(v).strip() and str(v).lower() != "nan"]
            if not vals:
                continue
            canonical = vals[0]
            alias_map[normalize_key(canonical)] = canonical
            for val in vals[1:]:
                alias_map[normalize_key(val)] = canonical
    return alias_map

def canonical_team_name(name: str, alias_map: dict[str, str]) -> str:
    raw = str(name or "").strip()
    if not raw:
        return ""
    return alias_map.get(normalize_key(raw), raw)

def build_visual_map(team_visuals_df: pd.DataFrame, alias_map: dict[str, str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if team_visuals_df.empty:
        return out
    cols = {c.lower(): c for c in team_visuals_df.columns}
    team_col    = cols.get("team") or cols.get("school") or cols.get("name")
    primary_col = cols.get("primary") or cols.get("primary_color") or cols.get("primarycolor")
    secondary_col = cols.get("secondary") or cols.get("secondary_color") or cols.get("secondarycolor")
    if not team_col:
        return out
    for _, row in team_visuals_df.iterrows():
        team = canonical_team_name(row.get(team_col, ""), alias_map)
        if not team:
            continue
        out[team] = {
            "primary":   str(row.get(primary_col,   "#38bdf8")).strip() if primary_col   else "#38bdf8",
            "secondary": str(row.get(secondary_col, "#f8fafc")).strip() if secondary_col else "#f8fafc",
        }
    return out

def get_team_colors(team: str, visual_map: dict[str, dict]) -> tuple[str, str]:
    visual = visual_map.get(team, {})
    return visual.get("primary", "#38bdf8"), visual.get("secondary", "#f8fafc")

def _logo_candidates(name: str) -> list[str]:
    raw = str(name or "").strip()
    if not raw:
        return []
    parts = raw.replace("&", "and").replace("-", " ").split()
    camel = (parts[0].lower() + "".join(p[:1].upper() + p[1:] for p in parts[1:])
             if parts else "")
    return [normalize_key(raw), normalize_key(camel), raw.replace(" ", ""), raw]

def find_logo_path(team_name: str, alias_map: dict[str, str]) -> str | None:
    team = canonical_team_name(team_name, alias_map)
    candidates: list[str] = []
    for source in [team, team_name]:
        for c in _logo_candidates(source):
            if c and c not in candidates:
                candidates.append(c)
    for folder in LOGO_DIRS:
        for candidate in candidates:
            path = Path(folder) / f"{candidate}.png"
            if path.exists():
                return str(path)
    return None

def merge_manual_scores(schedule_df: pd.DataFrame,
                        manual_scores_df: pd.DataFrame,
                        alias_map: dict[str, str]) -> pd.DataFrame:
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
    key_cols = [c for c in ["Year", "Week", "HomeTeam", "AwayTeam"]
                if c in df.columns and c in ms.columns]
    if not key_cols:
        return df
    merged = df.merge(ms, on=key_cols, how="left", suffixes=("", "_manual"))
    for base, manual in [("HomeScore", "HomeScore_manual"),
                         ("AwayScore",  "AwayScore_manual"),
                         ("Status",     "Status_manual")]:
        if base in merged.columns and manual in merged.columns:
            merged[base] = merged[manual].combine_first(merged[base])
    return merged.drop(columns=[c for c in merged.columns if c.endswith("_manual")],
                       errors="ignore")

def score_columns(df: pd.DataFrame) -> tuple[str | None, str | None]:
    for home_col, away_col in [("HomeScore", "AwayScore"), ("ScoreHome", "ScoreAway")]:
        if home_col in df.columns and away_col in df.columns:
            return home_col, away_col
    return None, None

# ─────────────────────────────────────────────────────────────────────────────
# FIX 1: resolve_current_week — game_status only, NO schedule max-week fallback.
# The old version used schedule.max() which returned 17+ when you're in week 2.
# ─────────────────────────────────────────────────────────────────────────────
def resolve_current_week(game_status_df: pd.DataFrame, fallback_week: int) -> int:
    if not game_status_df.empty:
        for col in ["Week", "week"]:
            if col in game_status_df.columns:
                vals = pd.to_numeric(game_status_df[col], errors="coerce").dropna()
                if not vals.empty:
                    return int(vals.max())
    return fallback_week

# ─────────────────────────────────────────────────────────────────────────────
# FIX 2: Derive user teams from team_conferences.csv (User column non-empty).
# This ensures we get exactly the 6 human coaches, not all 136 teams.
# ─────────────────────────────────────────────────────────────────────────────
def get_user_teams_from_conferences(team_conferences_df: pd.DataFrame,
                                    alias_map: dict[str, str]) -> list[str]:
    if (team_conferences_df.empty
            or "User" not in team_conferences_df.columns
            or "Team" not in team_conferences_df.columns):
        return []
    mask = (
        team_conferences_df["User"].notna()
        & (team_conferences_df["User"].astype(str).str.strip() != "")
        & (team_conferences_df["User"].astype(str).str.lower() != "nan")
    )
    user_rows = team_conferences_df[mask]
    teams = [canonical_team_name(t, alias_map)
             for t in user_rows["Team"].astype(str).tolist()]
    return list(dict.fromkeys(t for t in teams if t))

def get_user_team_list(user_teams_df: pd.DataFrame,
                       alias_map: dict[str, str],
                       schedule_df: pd.DataFrame | None = None,
                       team_conferences_df: pd.DataFrame | None = None) -> list[str]:
    # 1. Try explicit user_teams.csv
    if not user_teams_df.empty:
        cols = {c.lower(): c for c in user_teams_df.columns}
        for name in ["team", "school", "program"]:
            col = cols.get(name)
            if col:
                vals = [canonical_team_name(v, alias_map)
                        for v in user_teams_df[col].dropna().astype(str).tolist()]
                vals = [v for v in vals if v]
                if vals:
                    return list(dict.fromkeys(vals))
        vals = [canonical_team_name(v, alias_map)
                for v in user_teams_df.astype(str).stack().tolist()
                if str(v).strip() and str(v).lower() != "nan"]
        if vals:
            return list(dict.fromkeys(vals))
    # 2. Try team_conferences.csv (most reliable for 6-team user list)
    if team_conferences_df is not None:
        teams = get_user_teams_from_conferences(team_conferences_df, alias_map)
        if teams:
            return teams
    # 3. Last resort — schedule HomeUser/AwayUser (may over-include CPU teams)
    if schedule_df is not None and not schedule_df.empty:
        derived: list[str] = []
        if "HomeUser" in schedule_df.columns and "HomeTeam" in schedule_df.columns:
            derived.extend(
                schedule_df.loc[
                    schedule_df["HomeUser"].notna()
                    & (schedule_df["HomeUser"].astype(str).str.strip() != "")
                    & (schedule_df["HomeUser"].astype(str).str.lower() != "nan"),
                    "HomeTeam",
                ].astype(str).tolist()
            )
        if "AwayUser" in schedule_df.columns and "AwayTeam" in schedule_df.columns:
            derived.extend(
                schedule_df.loc[
                    schedule_df["AwayUser"].notna()
                    & (schedule_df["AwayUser"].astype(str).str.strip() != "")
                    & (schedule_df["AwayUser"].astype(str).str.lower() != "nan"),
                    "AwayTeam",
                ].astype(str).tolist()
            )
        derived = [canonical_team_name(v, alias_map)
                   for v in derived if str(v).strip()]
        return list(dict.fromkeys(derived))
    return []

def load_data() -> dict:
    active_year = MANUAL_YEAR if MANUAL_YEAR is not None else infer_year_from_repo(2043)
    active_week = (MANUAL_WEEK if MANUAL_WEEK is not None
                   else max(infer_week_candidates(active_year) or [1]))

    fpi_path, fpi_week_used = pick_metric_file("fpi_ratings", active_year, active_week)
    ms_path,  ms_week_used  = pick_metric_file("ms_plus",     active_year, active_week)

    file_map = build_file_map(active_year, active_week)
    file_map["fpi"]     = fpi_path
    file_map["ms_plus"] = ms_path

    data = {k: safe_read_csv(v) for k, v in file_map.items()}
    data["schedule"]           = standardize_schedule_columns(data["schedule"])
    data["week_manual_scores"] = standardize_schedule_columns(data["week_manual_scores"])
    data = standardize_other_frames(data)

    alias_map = build_alias_map(data["team_aliases"])
    for frame_name in [
        "schedule", "game_summaries", "bluechip", "cfp_rankings",
        "fpi", "ms_plus", "team_conferences", "team_ratings",
        "user_teams", "week_game_status", "week_manual_scores",
        "cfp_bracket", "injury_bulletin",
    ]:
        df = data[frame_name]
        if df.empty:
            continue
        team_cols = [
            c for c in df.columns
            if "team" in c.lower()
            or c.lower() in {"winner", "loser", "home", "away", "visitor", "school", "program"}
        ]
        for col in team_cols:
            try:
                df[col] = df[col].map(lambda x: canonical_team_name(x, alias_map))
            except Exception:
                pass
        data[frame_name] = df

    data["schedule"] = merge_manual_scores(
        data["schedule"], data["week_manual_scores"], alias_map
    )
    data["alias_map"]   = alias_map
    data["visual_map"]  = build_visual_map(data["team_visuals"], alias_map)
    data["active_year"] = active_year
    data["active_week"] = active_week
    data["file_map"]    = file_map
    data["fpi_week_used"] = fpi_week_used
    data["ms_week_used"]  = ms_week_used
    return data

@st.cache_data(ttl=300)
def get_data() -> dict:
    return load_data()

# ─────────────────────────────────────────────────────────────────────────────
# DOMAIN HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def get_user_labels(schedule_df: pd.DataFrame,
                    user_teams: list[str]) -> dict[str, str]:
    labels: dict[str, str] = {}
    if schedule_df.empty:
        return labels
    if {"HomeUser", "HomeTeam"}.issubset(schedule_df.columns):
        sub = schedule_df.loc[
            schedule_df["HomeTeam"].isin(user_teams)
            & schedule_df["HomeUser"].notna(),
            ["HomeTeam", "HomeUser"],
        ].drop_duplicates()
        labels.update({
            str(r["HomeTeam"]): str(r["HomeUser"])
            for _, r in sub.iterrows()
            if str(r["HomeUser"]).strip()
        })
    if {"AwayUser", "AwayTeam"}.issubset(schedule_df.columns):
        sub = schedule_df.loc[
            schedule_df["AwayTeam"].isin(user_teams)
            & schedule_df["AwayUser"].notna(),
            ["AwayTeam", "AwayUser"],
        ].drop_duplicates()
        labels.update({
            str(r["AwayTeam"]): str(r["AwayUser"])
            for _, r in sub.iterrows()
            if str(r["AwayUser"]).strip()
        })
    return labels

def get_latest_rankings(cfp_rankings_df: pd.DataFrame,
                        active_year: int) -> pd.DataFrame:
    if (cfp_rankings_df.empty
            or "Team" not in cfp_rankings_df.columns
            or "Rank" not in cfp_rankings_df.columns):
        return pd.DataFrame(columns=["Team", "Rank", "Record"])
    df = cfp_rankings_df.copy()
    if "Year" in df.columns:
        df = df[
            pd.to_numeric(df["Year"], errors="coerce")
            .fillna(active_year).astype(int) == active_year
        ]
    if "Week" in df.columns:
        latest_week = pd.to_numeric(df["Week"], errors="coerce").dropna().max()
        if pd.notna(latest_week):
            df = df[pd.to_numeric(df["Week"], errors="coerce") == latest_week]
    out = pd.DataFrame({
        "Team": df["Team"].astype(str).str.strip(),
        "Rank": pd.to_numeric(df["Rank"], errors="coerce"),
        "Record": df["Record"].astype(str) if "Record" in df.columns else "—",
    })
    out = out.dropna(subset=["Team"]).sort_values("Rank", na_position="last")
    return out.drop_duplicates(subset=["Team"], keep="first")

def get_fpi_ms_table(fpi_df: pd.DataFrame,
                     ms_df: pd.DataFrame) -> pd.DataFrame:
    def normalize_metric_df(df: pd.DataFrame,
                            value_name: str,
                            exact_col: str | None = None) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=["Team", value_name])
        cols = {c.lower(): c for c in df.columns}
        team_col = (cols.get("team") or cols.get("school") or cols.get("program"))
        value_col = None
        if exact_col and exact_col in df.columns:
            value_col = exact_col
        if not value_col:
            if value_name == "FPI":
                value_col = cols.get("fpi")
            else:
                value_col = (cols.get("ms+")
                             or cols.get("msplus")
                             or cols.get("ms_plus"))
        if not value_col:
            numeric_candidates = [
                c for c in df.columns
                if pd.api.types.is_numeric_dtype(df[c])
                and c.lower() not in {"year", "week", "rank"}
            ]
            value_col = numeric_candidates[0] if numeric_candidates else None
        if not team_col or not value_col:
            return pd.DataFrame(columns=["Team", value_name])
        return pd.DataFrame({
            "Team":       df[team_col].astype(str).str.strip(),
            value_name:   pd.to_numeric(df[value_col], errors="coerce"),
        })

    fpi = normalize_metric_df(fpi_df, "FPI", "FPI")
    ms  = normalize_metric_df(ms_df,  "MS+", "MSPlus")
    return pd.merge(fpi, ms, on="Team", how="outer")

def build_game_status_lookup(game_status_df: pd.DataFrame,
                             schedule_df: pd.DataFrame) -> dict[tuple[str, str], str]:
    lookup: dict[tuple[str, str], str] = {}
    if not game_status_df.empty:
        cols = {c.lower(): c for c in game_status_df.columns}
        home_col   = cols.get("hometeam") or cols.get("home")
        away_col   = cols.get("awayteam") or cols.get("away") or cols.get("visitor")
        status_col = cols.get("status") or cols.get("game_status")
        if home_col and away_col and status_col:
            for _, row in game_status_df.iterrows():
                h = str(row.get(home_col, "")).strip()
                a = str(row.get(away_col, "")).strip()
                lookup[(h, a)] = str(row.get(status_col, "")).strip()
    if not lookup and not schedule_df.empty and "Status" in schedule_df.columns:
        for _, row in schedule_df.iterrows():
            home = str(row.get("HomeTeam", "")).strip()
            away = str(row.get("AwayTeam", "")).strip()
            if home and away:
                lookup[(home, away)] = str(row.get("Status", "Scheduled")).strip()
    return lookup

def get_status_variant(status: str) -> tuple[str, str]:
    text = str(status or "").upper()
    if "FINAL" in text:
        return "#10b981", "rgba(16,185,129,.18)"
    if "LIVE" in text or "Q" in text:
        return "#38bdf8", "rgba(56,189,248,.18)"
    if "NOT SET" in text or "TBD" in text:
        return "#ef4444", "rgba(239,68,68,.16)"
    return "#f59e0b", "rgba(245,158,11,.16)"

def _is_team_eliminated(team: str, cfp_bracket: pd.DataFrame) -> bool:
    if cfp_bracket.empty or "Loser" not in cfp_bracket.columns:
        return False
    completed_col = cfp_bracket.get("Completed", pd.Series(dtype=str))
    elim = cfp_bracket[
        cfp_bracket["Loser"].astype(str).str.strip() == team
    ]
    if elim.empty:
        return False
    if "Completed" in cfp_bracket.columns:
        elim = elim[pd.to_numeric(elim["Completed"], errors="coerce") == 1]
    return not elim.empty

def build_button_grid_html(user_teams: list[str],
                           user_labels: dict[str, str],
                           data: dict) -> str:
    cards = []
    alias_map  = data["alias_map"]
    visual_map = data["visual_map"]
    for team in user_teams:
        primary, _ = get_team_colors(team, visual_map)
        logo = find_logo_path(team, alias_map)
        user = user_labels.get(team, "")
        if logo:
            logo_html = (
                f"<img src='{logo}' style='width:72px;height:72px;object-fit:contain;"
                f"filter:drop-shadow(0 0 12px {primary});'/>"
            )
        else:
            logo_html = (
                f"<div style='width:72px;height:72px;border-radius:18px;border:2px solid {primary};"
                f"display:flex;align-items:center;justify-content:center;"
                f"color:{primary};font-weight:900;'>🏈</div>"
            )
        cards.append(
            f"<div class='dyn-btn' style='border:3px solid {primary};"
            f"box-shadow:0 0 0 1px rgba(255,255,255,.06) inset,0 0 18px {primary}55;'>"
            f"<div class='dyn-btn-dot' style='background:{primary};box-shadow:0 0 18px {primary};'></div>"
            f"{logo_html}"
            f"<div class='dyn-btn-user' style='color:{primary};'>{html.escape(user)}</div>"
            f"</div>"
        )
    return "<div class='dyn-btn-grid'>" + "".join(cards) + "</div>"

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
def render_old_style_css() -> None:
    st.markdown("""
    <style>
    .stApp{
      background:
        radial-gradient(circle at top left, rgba(30,64,175,.18), transparent 28%),
        radial-gradient(circle at top right, rgba(127,29,29,.16), transparent 24%),
        linear-gradient(180deg,#020817 0%,#061120 35%,#040b18 100%);
      color:#e5e7eb;
    }
    .dyn-btn-wrap{
      background:rgba(9,14,25,.82);
      border:1px solid rgba(255,255,255,.07);
      border-radius:28px;
      padding:24px;
      box-shadow:0 12px 28px rgba(0,0,0,.35), 0 0 0 1px rgba(255,255,255,.03) inset;
      margin-bottom:18px;
    }
    .dyn-btn-grid{
      display:grid;
      grid-template-columns:repeat(3, minmax(0,1fr));
      gap:18px;
    }
    .dyn-btn{
      min-height:220px;
      border-radius:28px;
      display:flex;
      flex-direction:column;
      align-items:center;
      justify-content:center;
      gap:10px;
      background:
        linear-gradient(135deg, rgba(15,23,42,.98), rgba(2,6,23,.98)),
        radial-gradient(circle at top center, rgba(255,255,255,.06), transparent 38%);
      position:relative;
    }
    .dyn-btn-dot{
      width:14px;height:14px;border-radius:999px;position:absolute;top:24px;left:50%;
      transform:translateX(-50%);opacity:.95;
    }
    .dyn-btn-user{
      font-size:2rem;font-weight:900;letter-spacing:.06em;text-transform:uppercase;
      font-family:Impact, Haettenschweiler, 'Arial Narrow Bold', sans-serif;
    }
    .dyn-news-card{
      border-radius:24px;
      background:linear-gradient(180deg, rgba(4,10,24,.96), rgba(3,8,20,.98));
      border:1px solid rgba(255,255,255,.06);
      box-shadow:0 14px 34px rgba(0,0,0,.34),0 0 0 1px rgba(255,255,255,.03) inset;
      overflow:hidden;
      margin:14px 0 26px 0;
      transition:opacity .3s ease,filter .3s ease;
    }
    .dyn-news-top{
      display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;
      padding:14px 18px 0 18px;
    }
    .dyn-chip{
      display:inline-flex;align-items:center;gap:8px;
      padding:8px 14px;border-radius:12px;font-size:1.2rem;font-weight:900;
      letter-spacing:.05em;text-transform:uppercase;
      border:1px solid rgba(255,255,255,.08);
      font-family:Impact, Haettenschweiler, 'Arial Narrow Bold', sans-serif;
    }
    .dyn-mini-chip{
      display:inline-flex;align-items:center;gap:8px;
      padding:7px 12px;border-radius:999px;font-size:.95rem;font-weight:800;
      border:1px solid rgba(255,255,255,.08);color:#e5e7eb;background:rgba(255,255,255,.05);
    }
    .dyn-main{
      display:grid;grid-template-columns: 110px 120px 1fr 280px; gap:18px;
      align-items:center;padding:16px 20px 12px 20px;
    }
    .dyn-rank{
      width:82px;height:82px;border-radius:999px;border:4px solid #fbbf24;
      color:#fbbf24;display:flex;align-items:center;justify-content:center;
      font-size:2.2rem;font-weight:900;
      font-family:Impact, Haettenschweiler, 'Arial Narrow Bold', sans-serif;
      box-shadow:0 0 0 1px rgba(255,255,255,.05) inset;
      margin-left:6px;
    }
    .dyn-logo-box{
      width:110px;height:110px;border-radius:18px;display:flex;align-items:center;
      justify-content:center;background:rgba(255,255,255,.03);
      border:2px solid rgba(255,255,255,.08);
    }
    .dyn-team-line{
      font-size:2.4rem;font-weight:900;line-height:1;
      font-family:Impact, Haettenschweiler, 'Arial Narrow Bold', sans-serif;
      letter-spacing:.02em;
    }
    .dyn-sub{
      color:#94a3b8;font-size:1rem;margin-left:6px;font-family:system-ui,sans-serif;font-weight:500;
    }
    .dyn-record{
      display:inline-flex;padding:8px 14px;border-radius:10px;
      background:rgba(34,197,94,.18);color:#86efac;
      border:1px solid rgba(134,239,172,.22);font-weight:900;font-size:1.35rem;
      margin-top:12px;font-family:Impact, Haettenschweiler, 'Arial Narrow Bold', sans-serif;
    }
    .dyn-divider{
      height:1px;background:linear-gradient(90deg, transparent, rgba(255,255,255,.08), transparent);
      margin:12px 0;
    }
    .dyn-match{
      display:flex;align-items:center;gap:14px;flex-wrap:wrap;
      font-family:Impact, Haettenschweiler, 'Arial Narrow Bold', sans-serif;
      font-size:2rem;line-height:1.1;
    }
    .dyn-opp-rank{ color:#60a5fa; }
    .dyn-right{ text-align:right; }
    .dyn-right-top{ font-size:1.65rem;color:#e5e7eb; }
    .dyn-right-big{
      font-size:2rem;font-weight:900;color:#f8fafc;
      font-family:Impact, Haettenschweiler, 'Arial Narrow Bold', sans-serif;
    }
    .dyn-right-small{ color:#94a3b8;font-size:1.05rem; }
    .dyn-pill{
      display:inline-flex;padding:10px 16px;border-radius:999px;font-weight:900;font-size:1.1rem;
      border:1px solid rgba(132,204,22,.25);background:rgba(101,163,13,.14);color:#84cc16;
      margin-top:16px;font-family:Impact, Haettenschweiler, 'Arial Narrow Bold', sans-serif;
    }
    .dyn-outlook{
      display:inline-flex;align-items:center;gap:10px;padding:16px 24px;border-radius:18px;
      border:1px solid rgba(255,255,255,.10);background:rgba(15,23,42,.72);color:#f8fafc;
      font-size:1.95rem;font-weight:900;letter-spacing:.06em;text-transform:uppercase;
      font-family:Impact, Haettenschweiler, 'Arial Narrow Bold', sans-serif;
      box-shadow:0 10px 20px rgba(0,0,0,.2),0 0 0 1px rgba(255,255,255,.04) inset;
      margin:0 0 20px 0;
    }
    .lite-panel{
      background:linear-gradient(180deg, rgba(6,14,28,.92), rgba(5,10,20,.96));
      border:1px solid rgba(255,255,255,.06);
      border-radius:20px;
      padding:18px 20px;
      margin:10px 0 20px 0;
      box-shadow:0 10px 24px rgba(0,0,0,.25);
    }
    .lite-panel h3{margin-top:0}
    .h2h-wrap table{
      width:100%;border-collapse:separate;border-spacing:8px;
    }
    .h2h-cell{
      background:rgba(15,23,42,.9);border:1px solid rgba(255,255,255,.06);border-radius:14px;
      padding:10px;text-align:center;font-weight:800;color:#e5e7eb;
    }
    @media (max-width: 980px){
      .dyn-btn-grid{grid-template-columns:repeat(2,minmax(0,1fr));}
      .dyn-main{grid-template-columns: 1fr; text-align:left;}
      .dyn-right{text-align:left;}
    }
    </style>
    """, unsafe_allow_html=True)

def render_sidebar(data: dict) -> None:
    st.sidebar.title("Dynasty Lite")
    st.sidebar.caption(f"Year {data['active_year']} • Week {data['active_week']}")
    st.sidebar.caption("Visual port build")
    st.sidebar.caption(
        f"FPI: {Path(data.get('file_map', {}).get('fpi', '—')).name}"
        + (f" (wk {data.get('fpi_week_used')})" if data.get("fpi_week_used") else "")
    )
    st.sidebar.caption(
        f"MS+: {Path(data.get('file_map', {}).get('ms_plus', '—')).name}"
        + (f" (wk {data.get('ms_week_used')})" if data.get("ms_week_used") else "")
    )
    missing = [path for path in data["file_map"].values() if not os.path.exists(path)]
    if missing:
        st.sidebar.warning("Missing files:")
        for path in missing:
            st.sidebar.caption(f"• {path}")

# ─────────────────────────────────────────────────────────────────────────────
# FIX 3: build_old_style_card_html — 4-state muting system ported from big app.
# States: (1) Ready + CFP alive → gold border full opacity
#         (2) Ready + not CFP   → team color border full opacity
#         (3) CFP alive not ready → gold border, grayscale logo, 88% opacity
#         (4) Not ready, not CFP / eliminated → gray border, grayscale, 72% opacity
# ─────────────────────────────────────────────────────────────────────────────
def build_old_style_card_html(team: str, user: str, game_row: pd.Series,
                               rankings: pd.DataFrame, metrics: pd.DataFrame,
                               data: dict, status_override: str | None = None) -> str:
    alias_map  = data["alias_map"]
    visual_map = data["visual_map"]
    primary, _ = get_team_colors(team, visual_map)
    team_logo  = find_logo_path(team, alias_map)

    is_home = str(game_row.get("HomeTeam", "")) == team
    opp = game_row.get("AwayTeam") if is_home else game_row.get("HomeTeam")
    opp = str(opp) if pd.notna(opp) else "BYE"
    opp_primary, _ = get_team_colors(opp, visual_map)
    opp_logo = find_logo_path(opp, alias_map)

    def rank_for(t: str) -> str:
        row = rankings[rankings["Team"] == t]
        if row.empty or pd.isna(row.iloc[0].get("Rank")):
            return "—"
        return f"#{int(row.iloc[0]['Rank'])}"

    def metric_for(t: str, metric: str) -> str:
        row = metrics[metrics["Team"] == t]
        if row.empty or pd.isna(row.iloc[0].get(metric)):
            return "—"
        return f"{float(row.iloc[0][metric]):.1f}"

    team_rank   = rank_for(team)
    opp_rank    = rank_for(opp)
    team_record = str(
        game_row.get("HomeRecord") if is_home else game_row.get("AwayRecord") or "—"
    )
    week    = int(pd.to_numeric(game_row.get("Week", data["active_week"]),
                                errors="coerce") or data["active_week"])
    status  = (status_override if status_override
               else str(game_row.get("Status", "NOT SET") or "NOT SET"))
    status_up = status.upper().strip()

    # ── 4-state muting ──────────────────────────────────────────────────────
    _is_ready_or_final = ("FINAL" in status_up or status.strip() == "Ready"
                          or bool(game_row.get("HomeScore")) or bool(game_row.get("AwayScore")))
    team_in_rankings   = team_rank != "—"
    _is_eliminated     = _is_team_eliminated(team, data.get("cfp_bracket", pd.DataFrame()))
    _cfp_alive         = team_in_rankings and not _is_eliminated

    if _is_ready_or_final:
        if _cfp_alive:
            _card_border    = "#fbbf24"
            _card_opacity   = "1.0"
            _content_filter = ""
            _logo_filter    = ""
        else:
            _card_border    = primary
            _card_opacity   = "1.0"
            _content_filter = ""
            _logo_filter    = ""
    elif _cfp_alive:
        _card_border    = "#fbbf24"
        _card_opacity   = "0.88"
        _content_filter = "filter:grayscale(50%);"
        _logo_filter    = "grayscale(70%) opacity(0.6)"
    elif _is_eliminated:
        _card_border    = "#374151"
        _card_opacity   = "0.62"
        _content_filter = "filter:grayscale(85%);"
        _logo_filter    = "grayscale(100%) opacity(0.35)"
    else:
        _card_border    = "#1e293b"
        _card_opacity   = "0.78"
        _content_filter = "filter:grayscale(35%);"
        _logo_filter    = "grayscale(40%) opacity(0.72)"

    rank_color      = "#fbbf24" if _cfp_alive else ("#60a5fa" if team_in_rankings else "#374151")
    logo_filt_style = f"filter:{_logo_filter};" if _logo_filter else ""
    team_logo_html  = (
        f"<img src='{team_logo}' style='width:84px;height:84px;object-fit:contain;{logo_filt_style}'/>"
        if team_logo else "🏈"
    )
    opp_logo_html = (
        f"<img src='{opp_logo}' style='width:58px;height:58px;object-fit:contain;'/>"
        if opp_logo else "🏈"
    )

    team_fpi = metric_for(team, "FPI")
    team_ms  = metric_for(team, "MS+")
    line_value = "—"
    if team_fpi != "—":
        try:
            opp_fpi_str = metric_for(opp, "FPI")
            if opp_fpi_str != "—":
                line_value = f"{float(team_fpi) - float(opp_fpi_str):+.1f}"
        except Exception:
            pass

    # Simple preseason odds placeholder (real CFP % needs more state)
    if team_rank == "#1":
        natty_odds = "99%"
    elif team_rank in {"#2", "#3"}:
        natty_odds = "88%"
    elif team_in_rankings:
        natty_odds = "72%"
    else:
        natty_odds = "—"

    chip_color, chip_bg = get_status_variant(status)

    return (
        f"<div class='dyn-news-card' style='border:2px solid {_card_border};"
        f"opacity:{_card_opacity};'>"
        # top row
        f"<div class='dyn-news-top'>"
        f"<div class='dyn-chip' style='background:rgba(255,255,255,.07);color:#e5e7eb;'>"
        f"WK {week}</div>"
        f"<div style='display:flex;gap:8px;flex-wrap:wrap;'>"
        f"<div class='dyn-mini-chip'>🛰️ Committee Live <span style='opacity:.75;'>(136-team)</span></div>"
        f"<div class='dyn-mini-chip'>📐 FPI {html.escape(team_fpi)}</div>"
        f"<div class='dyn-mini-chip'>💥 MS+ {html.escape(team_ms)}</div>"
        f"</div></div>"
        # main grid — content filter applied here
        f"<div class='dyn-main' style='{_content_filter}'>"
        f"<div class='dyn-rank' style='border-color:{rank_color};color:{rank_color};'>"
        f"{html.escape(team_rank if team_rank != '—' else '#')}</div>"
        f"<div class='dyn-logo-box' style='border-color:{_card_border};"
        f"box-shadow:0 0 16px {_card_border}44;'>{team_logo_html}</div>"
        f"<div>"
        f"<div class='dyn-team-line' style='color:{primary};'>{html.escape(team)} "
        f"<span class='dyn-sub'>({html.escape(user)})</span></div>"
        f"<div class='dyn-record'>{html.escape(team_record)}</div>"
        f"<div class='dyn-divider'></div>"
        f"<div class='dyn-match'>"
        f"<span style='color:#64748b;'>WK {week}</span>"
        f"<span class='dyn-chip' style='background:{chip_bg};color:{chip_color};"
        f"border-color:{chip_color}55;padding:8px 14px;font-size:1.5rem;'>"
        f"{html.escape(status)}</span>"
        f"<span style='color:#94a3b8;'>vs</span>"
        f"<span class='dyn-opp-rank'>{html.escape(opp_rank)}</span>"
        f"<span style='display:inline-flex;align-items:center;gap:10px;color:{opp_primary};'>"
        f"{opp_logo_html}<span>{html.escape(opp)}</span></span>"
        f"<span style='color:#cbd5e1;'>LINE: "
        f"<span style='color:#86efac;'>{html.escape(team)} {html.escape(line_value)}</span>"
        f"</span></div></div>"
        f"<div class='dyn-right'>"
        f"<div class='dyn-right-top'>Pre-PI: "
        f"<span class='dyn-right-big'>{html.escape(team_fpi)}</span></div>"
        f"<div class='dyn-right-small'>🏆 Natty: "
        f"<span style='color:#60a5fa;font-weight:900;'>{html.escape(natty_odds)}</span></div>"
        f"<div class='dyn-pill'>Speed Freaks: "
        f"{html.escape(team_rank if team_rank != '—' else '#?')}</div>"
        f"</div></div></div>"
    )

# ─────────────────────────────────────────────────────────────────────────────
# FIX 4 & 5: render_user_cards_section
# – Uses active_week directly (not broken resolve_current_week schedule fallback)
# – Proper DataFrame column filtering (not .get() ambiguity)
# – Passes status_override from game_status lookup
# – Uses team_conferences for user team resolution
# ─────────────────────────────────────────────────────────────────────────────
def render_user_cards_section(data: dict) -> None:
    schedule = data["schedule"].copy()
    if schedule.empty:
        st.info("No schedule file found.")
        return

    alias_map  = data["alias_map"]
    rankings   = get_latest_rankings(data["cfp_rankings"], data["active_year"])
    metrics    = get_fpi_ms_table(data["fpi"], data["ms_plus"])
    user_teams = get_user_team_list(
        data["user_teams"], alias_map, schedule,
        team_conferences_df=data.get("team_conferences", pd.DataFrame()),
    )
    if not user_teams:
        st.info("No user teams found. Check user_teams.csv or team_conferences.csv.")
        return
    user_labels = get_user_labels(schedule, user_teams)

    st.markdown(
        "<div class='dyn-btn-wrap'>"
        + build_button_grid_html(user_teams, user_labels, data)
        + "</div>",
        unsafe_allow_html=True,
    )

    # Use active_week directly — not the broken schedule max-week path
    current_week = data["active_week"]
    week_sched   = schedule.copy()
    if "Week" in week_sched.columns:
        week_sched = week_sched[
            pd.to_numeric(week_sched["Week"], errors="coerce") == current_week
        ].copy()

    status_lookup = build_game_status_lookup(data["week_game_status"], week_sched)

    for team in user_teams:
        if "HomeTeam" in week_sched.columns and "AwayTeam" in week_sched.columns:
            team_games = week_sched[
                (week_sched["HomeTeam"] == team) | (week_sched["AwayTeam"] == team)
            ].copy()
        else:
            team_games = pd.DataFrame()

        if team_games.empty:
            st.caption(f"No Week {current_week} game found for {team}.")
            continue

        row     = team_games.iloc[0]
        home    = str(row.get("HomeTeam", ""))
        away    = str(row.get("AwayTeam", ""))
        status  = (status_lookup.get((home, away))
                   or status_lookup.get((away, home))
                   or str(row.get("Status", "NOT SET")))
        user    = user_labels.get(team, "")

        card_html = build_old_style_card_html(
            team, user, row, rankings, metrics, data, status_override=status
        )
        st.markdown(card_html, unsafe_allow_html=True)
        st.markdown(
            f"<div class='dyn-outlook'>🔮 {html.escape(team.upper())}'S "
            f"{data['active_year'] + 1} OUTLOOK →</div>",
            unsafe_allow_html=True,
        )

def render_fpi_ms_section(data: dict) -> None:
    st.markdown("<div class='lite-panel'>", unsafe_allow_html=True)
    st.subheader("FPI + MS+ Ratings")
    merged = get_fpi_ms_table(data["fpi"], data["ms_plus"])
    if merged.empty:
        st.info("FPI/MS+ files were not found or could not be read.")
        st.markdown("</div>", unsafe_allow_html=True)
        return
    rankings = get_latest_rankings(data["cfp_rankings"], data["active_year"])
    if not rankings.empty and "Team" in rankings.columns and "Rank" in rankings.columns:
        merged = merged.merge(rankings[["Team", "Rank"]], on="Team", how="left")
        merged = merged.sort_values(
            ["Rank", "FPI", "MS+"], ascending=[True, False, False], na_position="last"
        )
    c1, c2 = st.columns(2)
    with c1:
        top_fpi = merged.dropna(subset=["FPI"]).head(12)
        if not top_fpi.empty:
            fig = px.bar(top_fpi, x="FPI", y="Team", orientation="h",
                         title="Top FPI", height=480)
            fig.update_layout(
                yaxis={"categoryorder": "total ascending"},
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
            )
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        top_ms = merged.dropna(subset=["MS+"]).head(12)
        if not top_ms.empty:
            fig = px.bar(top_ms, x="MS+", y="Team", orientation="h",
                         title="Top MS+", height=480)
            fig.update_layout(
                yaxis={"categoryorder": "total ascending"},
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="white",
            )
            st.plotly_chart(fig, use_container_width=True)
    display_cols = [c for c in ["Rank", "Team", "FPI", "MS+"] if c in merged.columns]
    st.dataframe(merged[display_cols], hide_index=True, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# FIX 7: resolve_current_week now takes only 2 args
def render_who_would_win(data: dict) -> None:
    st.markdown("<div class='lite-panel'>", unsafe_allow_html=True)
    st.subheader("Who Would Win?")
    metrics = get_fpi_ms_table(data["fpi"], data["ms_plus"])
    df = data["schedule"].copy()
    if df.empty:
        st.info("No current-week matchups available.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    latest_week = resolve_current_week(data["week_game_status"], data["active_week"])
    if "Week" in df.columns:
        df = df[pd.to_numeric(df["Week"], errors="coerce") == latest_week].copy()

    home = metrics.rename(columns={"Team": "HomeTeam", "FPI": "HomeFPI", "MS+": "HomeMS"})
    away = metrics.rename(columns={"Team": "AwayTeam", "FPI": "AwayFPI", "MS+": "AwayMS"})
    df = df.merge(home, on="HomeTeam", how="left").merge(away, on="AwayTeam", how="left")
    df["HomeEdge"] = (
        df[["HomeFPI", "HomeMS"]].mean(axis=1)
        - df[["AwayFPI", "AwayMS"]].mean(axis=1)
    )

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
    show_cols = [c for c in ["Week", "HomeTeam", "AwayTeam",
                              "HomeFPI", "AwayFPI", "HomeMS", "AwayMS", "Prediction"]
                 if c in df.columns]
    st.dataframe(df[show_cols], hide_index=True, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# FIX 6: render_highest_rated_games — TV ratings formula ported from big app.
# Accounts for ranked matchups, drama (margin), scoring, context bonuses,
# upset multiplier, and seeded noise for variety.
# ─────────────────────────────────────────────────────────────────────────────
def render_highest_rated_games(data: dict) -> None:
    st.markdown("<div class='lite-panel'>", unsafe_allow_html=True)
    st.subheader("📺 Highest Rated Games of the Season")
    st.caption(
        "Viewership formula: matchup prestige + drama + scoring + context + "
        "upset bonus. Peak = moment the broadcast peaked."
    )

    schedule = data["schedule"].copy()
    if schedule.empty:
        st.info("No schedule data available.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    try:
        if "Year" in schedule.columns:
            schedule = schedule[
                pd.to_numeric(schedule["Year"], errors="coerce")
                .fillna(data["active_year"]).astype(int) == data["active_year"]
            ]

        home_col, away_col = score_columns(schedule)
        if not home_col or not away_col:
            st.info("No completed games with scores available yet.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        played = schedule.dropna(subset=[home_col, away_col]).copy()
        if "Status" in played.columns:
            played = played[played["Status"].astype(str).str.upper() == "FINAL"]
        if played.empty:
            st.info("No final results yet this season.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        # Week-snapshot rankings for accuracy
        cfp_h = data["cfp_rankings"].copy()
        def _rank_at_week(team: str, week: int) -> float:
            if cfp_h.empty or "Team" not in cfp_h.columns:
                return 99.0
            if "Week" in cfp_h.columns and "Year" in cfp_h.columns:
                snap = cfp_h[
                    (pd.to_numeric(cfp_h["Year"], errors="coerce") == data["active_year"])
                    & (pd.to_numeric(cfp_h["Week"], errors="coerce") <= week)
                ]
                if snap.empty:
                    snap = cfp_h[pd.to_numeric(cfp_h["Year"], errors="coerce") == data["active_year"]]
                if not snap.empty:
                    latest = pd.to_numeric(snap["Week"], errors="coerce").max()
                    snap = snap[pd.to_numeric(snap["Week"], errors="coerce") == latest]
                    row = snap[snap["Team"] == team]
                    if not row.empty:
                        return float(pd.to_numeric(row.iloc[0]["Rank"], errors="coerce") or 99)
            return 99.0

        user_teams_set = set(get_user_team_list(
            data["user_teams"], data["alias_map"], schedule,
            team_conferences_df=data.get("team_conferences", pd.DataFrame()),
        ))

        def _tv_rating(row) -> tuple[float, str, str]:
            hs = float(pd.to_numeric(row.get(home_col), errors="coerce") or 0)
            aw = float(pd.to_numeric(row.get(away_col), errors="coerce") or 0)
            wk = float(pd.to_numeric(row.get("Week", 0), errors="coerce") or 0)
            home_team = str(row.get("HomeTeam", ""))
            away_team = str(row.get("AwayTeam", ""))
            home_user = str(row.get("HomeUser", "") or "").strip()
            away_user = str(row.get("AwayUser", "") or "").strip()

            hr = _rank_at_week(home_team, int(wk))
            vr = _rank_at_week(away_team, int(wk))
            margin      = abs(hs - aw)
            total_pts   = hs + aw
            is_user_game = (home_team in user_teams_set) or (away_team in user_teams_set)
            is_h2h       = (home_team in user_teams_set) and (away_team in user_teams_set)
            is_playoff   = wk >= 16
            is_natty     = wk >= 20

            top_rank   = min(hr, vr)
            both_ranked = hr <= 25 and vr <= 25
            base = 2.0
            if top_rank <= 5:    base += 6.5
            elif top_rank <= 10: base += 4.5
            elif top_rank <= 15: base += 2.8
            elif top_rank <= 25: base += 1.5
            if both_ranked:      base += 2.5

            if margin <= 3:    base += 3.5
            elif margin <= 7:  base += 2.0
            elif margin <= 14: base += 0.8

            if total_pts >= 100: base += 1.5
            elif total_pts >= 80: base += 0.8

            if is_natty:      base += 5.0
            elif is_playoff:  base += 3.2
            if is_h2h:        base += 2.5
            elif is_user_game: base += 1.2

            if wk >= 12:     base += 1.0
            elif wk >= 8:    base += 0.4

            winner_rank = hr if hs > aw else vr
            loser_rank  = vr if hs > aw else hr
            is_upset    = loser_rank <= 10 and winner_rank > loser_rank + 5
            if is_upset: base += 2.0

            seed = f"{data['active_year']}{int(wk)}{home_team}{away_team}".encode()
            noise = (int(hashlib.md5(seed).hexdigest()[:6], 16) % 100) / 100.0 * 0.8 - 0.4
            viewers = round(max(0.5, base + noise), 2)

            if is_natty:       badge = "🏆 NATTY"
            elif is_playoff:   badge = "🏟️ PLAYOFF"
            elif is_h2h:       badge = "⚔️ H2H"
            elif is_upset:     badge = "🚨 UPSET"
            elif both_ranked:  badge = "🔥 RANKED"
            elif margin <= 3:  badge = "💀 THRILLER"
            else:              badge = "📺 MARQUEE"

            if is_natty or is_playoff:     peak = "4th quarter, final drive"
            elif margin <= 3:              peak = "Final possession"
            elif margin <= 7 and wk >= 10: peak = "4th quarter comeback"
            elif is_upset:                 peak = f"Halftime — crowd sensed the upset"
            else:                          peak = f"3rd quarter momentum swing"

            return viewers, badge, peak

        rows = []
        for _, row in played.iterrows():
            viewers, badge, peak = _tv_rating(row)
            rows.append({
                "Week":     row.get("Week", "?"),
                "Home":     str(row.get("HomeTeam", "")),
                "Away":     str(row.get("AwayTeam", "")),
                "Score":    f"{int(float(row.get(home_col,0)))}-{int(float(row.get(away_col,0)))}",
                "Viewers":  viewers,
                "Badge":    badge,
                "Peak":     peak,
            })

        if not rows:
            st.info("No rated games yet.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        games_df = pd.DataFrame(rows).sort_values("Viewers", ascending=False).head(12)
        visual_map = data["visual_map"]
        alias_map  = data["alias_map"]

        for rank_i, (_, g) in enumerate(games_df.iterrows(), 1):
            home_t  = str(g["Home"])
            away_t  = str(g["Away"])
            hp, _   = get_team_colors(home_t, visual_map)
            ap, _   = get_team_colors(away_t, visual_map)
            h_logo  = find_logo_path(home_t, alias_map)
            a_logo  = find_logo_path(away_t, alias_map)
            hl_html = f"<img src='{h_logo}' style='height:28px;object-fit:contain;'/>" if h_logo else ""
            al_html = f"<img src='{a_logo}' style='height:28px;object-fit:contain;'/>" if a_logo else ""
            viewers_m = float(g["Viewers"])
            medal   = "🥇" if rank_i == 1 else ("🥈" if rank_i == 2 else ("🥉" if rank_i == 3 else f"#{rank_i}"))
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:14px;padding:10px 14px;"
                f"border-radius:10px;background:#06090f;border-left:3px solid {hp};"
                f"margin-bottom:6px;flex-wrap:wrap;'>"
                f"<span style='font-size:1.3rem;min-width:28px;'>{medal}</span>"
                f"<span style='font-size:1.1rem;font-weight:900;color:#f87171;min-width:32px;'>"
                f"Wk {int(float(g['Week'])) if str(g['Week']).replace('.','').isdigit() else g['Week']}</span>"
                f"<span style='font-weight:800;padding:2px 8px;border-radius:6px;background:#1e293b;"
                f"color:#f8fafc;font-size:0.85rem;'>{html.escape(str(g['Badge']))}</span>"
                f"<span style='display:flex;align-items:center;gap:6px;color:{hp};font-weight:900;'>"
                f"{hl_html} {html.escape(home_t)}</span>"
                f"<span style='color:#64748b;'>vs</span>"
                f"<span style='display:flex;align-items:center;gap:6px;color:{ap};font-weight:900;'>"
                f"{al_html} {html.escape(away_t)}</span>"
                f"<span style='color:#86efac;font-weight:700;'>{html.escape(str(g['Score']))}</span>"
                f"<span style='margin-left:auto;color:#fbbf24;font-weight:900;font-size:1.1rem;'>"
                f"📺 {viewers_m:.2f}M</span>"
                f"<div style='width:100%;color:#475569;font-size:0.75rem;padding-left:42px;'>"
                f"Peak: {html.escape(str(g['Peak']))}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
    except Exception as e:
        st.caption(f"Highest Rated Games unavailable: {e}")

    st.markdown("</div>", unsafe_allow_html=True)

def render_injury_report(data: dict) -> None:
    st.markdown("<div class='lite-panel'>", unsafe_allow_html=True)
    st.subheader("Injury Report")
    df = data["injury_bulletin"].copy()
    if df.empty:
        st.info("No injury bulletin file found.")
    else:
        st.dataframe(df, hide_index=True, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# NEW: render_spoiling_the_moment — upset / chaos leaderboard
# ─────────────────────────────────────────────────────────────────────────────
def render_spoiling_the_moment(data: dict) -> None:
    st.markdown("<div class='lite-panel'>", unsafe_allow_html=True)
    st.subheader("⚔️ Spoiling the Moment")
    st.caption(
        "Games that flipped the script — ranked killers, blowout shockers, "
        "and chaos merchants sorted by upset impact score."
    )

    schedule = data["schedule"].copy()
    rankings = get_latest_rankings(data["cfp_rankings"], data["active_year"])

    if schedule.empty:
        st.info("No schedule data available.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    try:
        if "Year" in schedule.columns:
            schedule = schedule[
                pd.to_numeric(schedule["Year"], errors="coerce")
                .fillna(data["active_year"]).astype(int) == data["active_year"]
            ]

        home_col, away_col = score_columns(schedule)
        if not home_col or not away_col:
            st.info("No completed games available yet.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        played = schedule.dropna(subset=[home_col, away_col]).copy()
        if "Status" in played.columns:
            played = played[played["Status"].astype(str).str.upper() == "FINAL"]
        if played.empty:
            st.caption("No final results yet this season. The chaos is still loading.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        cfp_map = dict(zip(
            rankings["Team"].astype(str),
            pd.to_numeric(rankings["Rank"], errors="coerce"),
        ))

        rows = []
        for _, row in played.iterrows():
            hs = float(pd.to_numeric(row.get(home_col), errors="coerce") or 0)
            aw = float(pd.to_numeric(row.get(away_col), errors="coerce") or 0)
            if hs == 0 and aw == 0:
                continue
            home_t = str(row.get("HomeTeam", ""))
            away_t = str(row.get("AwayTeam", ""))
            hr = cfp_map.get(home_t, 99)
            vr = cfp_map.get(away_t, 99)
            margin = abs(hs - aw)

            winner      = home_t if hs > aw else away_t
            loser       = away_t if hs > aw else home_t
            winner_rank = (hr if hs > aw else vr) or 99
            loser_rank  = (vr if hs > aw else hr) or 99

            # Chaos score: upset value + drama bonus
            chaos = 0.0
            if loser_rank < winner_rank and loser_rank <= 25:
                chaos = float(winner_rank - loser_rank) + (25 - loser_rank) * 0.5
            elif loser_rank <= 10:
                chaos = float(25 - loser_rank) * 0.8

            if chaos <= 0:
                continue

            if margin <= 3:    chaos += 3.0
            elif margin <= 7:  chaos += 1.5

            wk = row.get("Week", "?")
            score_str = (
                f"{int(hs)}-{int(aw)}" if hs > aw else f"{int(aw)}-{int(hs)}"
            )
            loser_rank_str = f"#{int(loser_rank)}" if loser_rank <= 25 else "unranked"
            rows.append({
                "Week":    wk,
                "Winner":  winner,
                "Loser":   loser,
                "Score":   score_str,
                "Chaos":   chaos,
                "LRank":   loser_rank_str,
                "Margin":  margin,
            })

        if not rows:
            st.caption("No major upsets yet. The chalk is holding. Respect the chalk.")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        upsets = pd.DataFrame(rows).sort_values("Chaos", ascending=False).head(8)
        visual_map = data["visual_map"]
        alias_map  = data["alias_map"]

        for i, (_, g) in enumerate(upsets.iterrows(), 1):
            winner = str(g["Winner"])
            loser  = str(g["Loser"])
            wp, _  = get_team_colors(winner, visual_map)
            lp, _  = get_team_colors(loser,  visual_map)
            wl     = find_logo_path(winner, alias_map)
            ll     = find_logo_path(loser,  alias_map)
            wl_h   = f"<img src='{wl}' style='height:24px;object-fit:contain;'/>" if wl else ""
            ll_h   = f"<img src='{ll}' style='height:24px;object-fit:contain;'/>" if ll else ""
            medal  = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"#{i}"))
            wk_n   = g["Week"]
            margin = float(g["Margin"])
            drama  = " 💀 THRILLER" if margin <= 3 else (" 🔥 CLOSE" if margin <= 7 else "")
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:12px;padding:10px 14px;"
                f"border-radius:10px;background:#06090f;border-left:3px solid {wp};"
                f"margin-bottom:6px;flex-wrap:wrap;'>"
                f"<span style='font-size:1.2rem;min-width:28px;'>{medal}</span>"
                f"<span style='color:#94a3b8;font-size:0.85rem;min-width:40px;'>Wk {wk_n}</span>"
                f"<span style='display:flex;align-items:center;gap:6px;font-weight:900;color:{wp};'>"
                f"{wl_h}{html.escape(winner)}</span>"
                f"<span style='color:#86efac;font-weight:700;'>def.</span>"
                f"<span style='display:flex;align-items:center;gap:6px;color:{lp};'>"
                f"{ll_h}{html.escape(loser)}"
                f"<span style='font-size:0.72rem;color:#64748b;'>({g['LRank']})</span></span>"
                f"<span style='color:#f8fafc;font-weight:700;'>{html.escape(str(g['Score']))}</span>"
                f"<span style='color:#f59e0b;font-size:0.8rem;'>{drama}</span>"
                f"<span style='margin-left:auto;color:#ef4444;font-weight:900;'>⚡ {g['Chaos']:.0f}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
    except Exception as e:
        st.caption(f"Section unavailable: {e}")

    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# NEW: render_flying_under_radar — FPI rank vs CFP rank gap
# ─────────────────────────────────────────────────────────────────────────────
def render_flying_under_radar(data: dict) -> None:
    st.markdown("<div class='lite-panel'>", unsafe_allow_html=True)
    st.subheader("📡 Flying Under the Radar")
    st.caption(
        "Teams whose **FPI rank is significantly better than their CFP rank** — "
        "the computers see something the voters don't. Sorted by biggest gap."
    )

    fpi_table = get_fpi_ms_table(data["fpi"], data["ms_plus"])
    rankings  = get_latest_rankings(data["cfp_rankings"], data["active_year"])

    if fpi_table.empty or rankings.empty:
        st.info("Need both FPI ratings and CFP rankings to surface underrated teams.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    try:
        fpi_sorted = (
            fpi_table.dropna(subset=["FPI"])
            .sort_values("FPI", ascending=False)
            .reset_index(drop=True)
        )
        fpi_sorted["FPI_Rank"] = range(1, len(fpi_sorted) + 1)
        cfp_map = dict(zip(
            rankings["Team"].astype(str),
            pd.to_numeric(rankings["Rank"], errors="coerce"),
        ))
        fpi_sorted["CFP_Rank"] = fpi_sorted["Team"].map(cfp_map)
        ranked = fpi_sorted[fpi_sorted["CFP_Rank"].notna()].copy()
        ranked["Gap"] = ranked["CFP_Rank"] - ranked["FPI_Rank"]
        underrated = ranked[ranked["Gap"] > 3].sort_values("Gap", ascending=False).head(5)

        if underrated.empty:
            st.caption(
                "No major gaps between FPI and CFP right now. "
                "The polls and computers are roughly in agreement."
            )
        else:
            visual_map = data["visual_map"]
            alias_map  = data["alias_map"]
            for _, row in underrated.iterrows():
                t      = str(row["Team"])
                primary, _ = get_team_colors(t, visual_map)
                logo   = find_logo_path(t, alias_map)
                logo_h = (
                    f"<img src='{logo}' style='width:28px;height:28px;"
                    f"object-fit:contain;vertical-align:middle;margin-right:8px;'/>"
                    if logo else ""
                )
                fpi_r  = int(row["FPI_Rank"])
                cfp_r  = int(row["CFP_Rank"])
                gap    = int(row["Gap"])
                fpi_v  = float(row["FPI"])
                st.markdown(
                    f"<div style='background:linear-gradient(90deg,{primary}18 0%,#06090f 35%);"
                    f"border-left:4px solid {primary};border-radius:8px;"
                    f"padding:10px 14px;margin-bottom:6px;'>"
                    f"<div style='display:flex;align-items:center;"
                    f"justify-content:space-between;flex-wrap:wrap;gap:6px;'>"
                    f"<div style='display:flex;align-items:center;gap:6px;'>"
                    f"{logo_h}"
                    f"<span style='font-weight:900;font-size:1rem;color:#f8fafc;'>"
                    f"{html.escape(t)}</span>"
                    f"<span style='font-size:0.68rem;color:#64748b;margin-left:4px;'>"
                    f"FPI {fpi_v:+.1f}</span>"
                    f"</div>"
                    f"<div style='display:flex;align-items:center;gap:14px;'>"
                    f"<div style='text-align:center;'>"
                    f"<div style='font-size:0.55rem;color:#475569;text-transform:uppercase;'>CFP</div>"
                    f"<div style='font-size:1rem;font-weight:900;color:#f87171;'>#{cfp_r}</div></div>"
                    f"<div style='text-align:center;'>"
                    f"<div style='font-size:0.55rem;color:#475569;text-transform:uppercase;'>FPI</div>"
                    f"<div style='font-size:1rem;font-weight:900;color:#4ade80;'>#{fpi_r}</div></div>"
                    f"<div style='text-align:center;'>"
                    f"<div style='font-size:0.55rem;color:#475569;text-transform:uppercase;'>Gap</div>"
                    f"<div style='font-size:1.1rem;font-weight:900;color:#fbbf24;'>+{gap}</div></div>"
                    f"</div></div></div>",
                    unsafe_allow_html=True,
                )
    except Exception as e:
        st.caption(f"Section unavailable: {e}")

    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB RENDERS
# ─────────────────────────────────────────────────────────────────────────────
def render_dynasty_news(data: dict) -> None:
    st.title(f"Dynasty News — {data['active_year']} Week {data['active_week']}")
    render_user_cards_section(data)
    render_fpi_ms_section(data)
    render_who_would_win(data)
    render_highest_rated_games(data)
    render_spoiling_the_moment(data)
    render_flying_under_radar(data)
    render_injury_report(data)

def render_season_recap(data: dict) -> None:
    st.title(f"Season Recap — {data['active_year']}")
    rankings = get_latest_rankings(data["cfp_rankings"], data["active_year"])
    bracket  = data["cfp_bracket"].copy()
    bluechip = data["bluechip"].copy()
    st.markdown("<div class='lite-panel'>", unsafe_allow_html=True)
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
            show = bluechip[[c for c in ["Team", "BlueChipRatio"] if c in bluechip.columns]]
            st.dataframe(
                show if not show.empty else bluechip,
                hide_index=True, use_container_width=True,
            )
    st.subheader("CFP Bracket Results")
    if bracket.empty:
        st.info("No bracket results found.")
    else:
        if "Year" in bracket.columns:
            bracket = bracket[
                pd.to_numeric(bracket["Year"], errors="coerce")
                .fillna(data["active_year"]).astype(int) == data["active_year"]
            ]
        show_cols = [c for c in ["Round", "Team1", "Team1Score", "Team2",
                                  "Team2Score", "Winner", "Loser", "Completed"]
                     if c in bracket.columns]
        st.dataframe(bracket[show_cols], hide_index=True, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

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

    user_teams = get_user_team_list(
        data["user_teams"], data["alias_map"], schedule,
        team_conferences_df=data.get("team_conferences", pd.DataFrame()),
    )
    teams = user_teams if user_teams else sorted(
        set(played["HomeTeam"].dropna().astype(str))
        | set(played["AwayTeam"].dropna().astype(str))
    )

    matrix = pd.DataFrame("", index=teams, columns=teams)
    for _, row in played.iterrows():
        home = str(row["HomeTeam"])
        away = str(row["AwayTeam"])
        if home not in matrix.index or away not in matrix.columns:
            continue
        try:
            hs = int(float(row[home_score_col]))
            aw = int(float(row[away_score_col]))
        except Exception:
            continue
        matrix.loc[home, away] = f"W {hs}-{aw}" if hs > aw else f"L {hs}-{aw}"
        matrix.loc[away, home] = f"W {aw}-{hs}" if aw > hs else f"L {aw}-{hs}"

    header   = "<tr><td></td>" + "".join(
        f"<td class='h2h-cell'><strong>{html.escape(t)}</strong></td>" for t in teams
    ) + "</tr>"
    html_rows = []
    for r in teams:
        row_html = f"<tr><td class='h2h-cell'><strong>{html.escape(r)}</strong></td>"
        for c in teams:
            val = matrix.loc[r, c] if r in matrix.index and c in matrix.columns else ""
            row_html += f"<td class='h2h-cell'>{html.escape(str(val))}</td>"
        row_html += "</tr>"
        html_rows.append(row_html)

    st.markdown(
        "<div class='lite-panel h2h-wrap'><h3>All-Time H2H Grid</h3><table>"
        + header + "".join(html_rows) + "</table></div>",
        unsafe_allow_html=True,
    )

def main():
    data = get_data()
    render_old_style_css()
    render_sidebar(data)
    tab1, tab2, tab3 = st.tabs(["🗞️ Dynasty News", "📺 Season Recap", "⚔️ H2H Matrix"])
    with tab1:
        render_dynasty_news(data)
    with tab2:
        render_season_recap(data)
    with tab3:
        render_h2h_matrix(data)

if __name__ == "__main__":
    main()
