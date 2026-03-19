import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import numpy as np
import os
import io
import re
import textwrap
import html
import time
import base64
import hashlib
from pathlib import Path

import os
import random
import html
import pandas as pd
import streamlit as st

# ──────────────────────────────────────────────────────────────────────
# NFL UNIVERSE — HELPERS / CONFIG
# ──────────────────────────────────────────────────────────────────────
def initialize_nfl_universe_settings():
    default_df = pd.DataFrame([{
        "CurrentNFLSeason": 2042,
        "LastCompletedDraftYear": 2041,
        "LastCompletedSuperBowlSeason": 2041,
        "UniverseVersion": 1
    }])

    for col in NFL_UNIVERSE_SETTINGS_COLS:
        if col not in default_df.columns:
            default_df[col] = pd.NA

    default_df = default_df[NFL_UNIVERSE_SETTINGS_COLS].copy()
    default_df.to_csv("nfl_universe_settings.csv", index=False)
    return default_df

def render_centered_logo(src, width=64):
    if not src:
        return

    src = str(src).strip()
    if not src:
        return

    if os.path.exists(src):
        src = file_to_data_uri(src)

    st.markdown(
        f"""
        <div style="display:flex; justify-content:center; margin-bottom:10px;">
            <img src="{src}" style="width:{width}px; height:{width}px; object-fit:contain;" />
        </div>
        """,
        unsafe_allow_html=True
    )

if "draft_audio_enabled" not in st.session_state:
    st.session_state["draft_audio_enabled"] = False

def enable_draft_audio():
    st.session_state["draft_audio_enabled"] = True

def generate_super_bowl_game_statline(row):
    pos = clean_display(row.get("Pos", ""), "")
    bucket = clean_display(row.get("PosBucket", clean_bucket(pos)), "")
    overall = int(safe_num(row.get("OverallEnd", 75), 75))

    if bucket == "QB":
        pass_yds = max(120, int(random.gauss(220 + (overall - 75) * 4.5, 35)))
        pass_tds = max(0, min(5, int(random.gauss(1.6 + max(0, overall - 80) / 12, 0.9))))
        ints = max(0, min(3, int(random.gauss(0.8, 0.8))))
        return f"{pass_yds} pass yds, {pass_tds} pass TD, {ints} INT"

    if bucket == "RB":
        rush_yds = max(25, int(random.gauss(70 + (overall - 75) * 2.2, 22)))
        rush_tds = max(0, min(3, int(random.gauss(0.8, 0.8))))
        return f"{rush_yds} rush yds, {rush_tds} rush TD"

    if bucket == "WR":
        rec_yds = max(20, int(random.gauss(85 + (overall - 75) * 2.5, 28)))
        rec_tds = max(0, min(3, int(random.gauss(0.7, 0.8))))
        return f"{rec_yds} rec yds, {rec_tds} rec TD"

    if bucket == "TE":
        rec_yds = max(15, int(random.gauss(55 + (overall - 75) * 1.8, 20)))
        rec_tds = max(0, min(2, int(random.gauss(0.5, 0.7))))
        return f"{rec_yds} rec yds, {rec_tds} rec TD"

    if bucket in {"EDGE", "IDL", "LB"}:
        tackles = max(2, int(random.gauss(6 + max(0, overall - 75) / 6, 2)))
        sacks = max(0, min(3, int(random.gauss(0.8 + max(0, overall - 85) / 15, 0.8))))
        return f"{tackles} tackles, {sacks} sacks"

    if bucket in {"CB", "S"}:
        tackles = max(2, int(random.gauss(5 + max(0, overall - 75) / 7, 2)))
        ints = max(0, min(2, int(random.gauss(0.35 + max(0, overall - 88) / 25, 0.5))))
        return f"{tackles} tackles, {ints} INT"

    games = 1
    starts = 1 if overall >= 74 else 0
    return f"{games} game, {starts} start"

def build_super_bowl_moment_text(player_name, team, pos_bucket, school="", stat_line="", is_hero=True):
    player_name = clean_display(player_name, "Unknown Player")
    team = clean_display(team, "")
    pos_bucket = clean_display(pos_bucket, "")
    school = clean_display(school, "")
    stat_line = clean_display(stat_line, "")

    school_tag = f" Former {school} star." if school else ""

    hero_templates = {
        "QB": [
            f"The defining moment came when {player_name} led a championship-clinching drive for {team}.{school_tag} He finished with {stat_line}.",
            f"{player_name} delivered the dagger touchdown throw that broke the game open for {team}.{school_tag} He closed the night with {stat_line}.",
            f"The Super Bowl swung when {player_name} calmly converted the biggest late-game series for {team}.{school_tag} He posted {stat_line}.",
            f"{player_name} authored the drive everyone will remember, marching {team} to the decisive score.{school_tag} He finished with {stat_line}."
        ],
        "RB": [
            f"The game turned when {player_name} ripped off the decisive scoring run for {team}.{school_tag} He finished with {stat_line}.",
            f"{player_name} iced the Super Bowl by grinding out the final crushing series for {team}.{school_tag} His line: {stat_line}.",
            f"The title-clinching moment belonged to {player_name}, who punched in the score that changed everything for {team}.{school_tag} He posted {stat_line}.",
            f"{player_name} broke the game open with the kind of late run that ends championships.{school_tag} He finished with {stat_line}."
        ],
        "WR": [
            f"The signature play came when {player_name} made the biggest catch of the night for {team}.{school_tag} He finished with {stat_line}.",
            f"{player_name} delivered the sideline grab that changed the Super Bowl for {team}.{school_tag} He ended with {stat_line}.",
            f"The championship swung on a clutch catch from {player_name} for {team}.{school_tag} He posted {stat_line}.",
            f"{player_name} gave {team} its defining highlight with a huge downfield strike in the biggest moment.{school_tag} He finished with {stat_line}."
        ],
        "TE": [
            f"The signature play came when {player_name} found space in traffic for the biggest catch of the night for {team}.{school_tag} He finished with {stat_line}.",
            f"{player_name} delivered the red-zone play that changed the game for {team}.{school_tag} He ended with {stat_line}.",
            f"The title swung when {team} leaned on {player_name} in the most important moment of the Super Bowl.{school_tag} He posted {stat_line}."
        ],
        "EDGE": [
            f"The turning point came when {player_name} blew up the pocket for {team} and changed the game.{school_tag} He finished with {stat_line}.",
            f"{player_name} delivered the strip-sack moment that sealed the title for {team}.{school_tag} He posted {stat_line}.",
            f"The Super Bowl flipped when {player_name} crashed through for the biggest pressure of the night for {team}.{school_tag} His final line was {stat_line}.",
            f"{team} seized control the moment {player_name} wrecked the decisive passing play.{school_tag} He finished with {stat_line}."
        ],
        "IDL": [
            f"The turning point came when {player_name} collapsed the middle for {team} and wrecked the biggest play of the game.{school_tag} He finished with {stat_line}.",
            f"{player_name} changed the Super Bowl by blowing up the interior on the decisive series for {team}.{school_tag} He posted {stat_line}.",
            f"The title swung when {player_name} disrupted the play that {team} needed most.{school_tag} He ended with {stat_line}."
        ],
        "LB": [
            f"The Super Bowl turned when {player_name} made the stop that every defender dreams about for {team}.{school_tag} He finished with {stat_line}.",
            f"{player_name} delivered the fourth-down stop that changed the game for {team}.{school_tag} He posted {stat_line}.",
            f"The defining defensive play belonged to {player_name}, who shut the door for {team}.{school_tag} He ended with {stat_line}."
        ],
        "CB": [
            f"The defining moment came when {player_name} broke up the biggest pass of the night for {team}.{school_tag} He finished with {stat_line}.",
            f"{player_name} made the game-sealing play in coverage for {team}.{school_tag} He posted {stat_line}.",
            f"The title swung on a back-end defensive gem from {player_name} for {team}.{school_tag} He ended with {stat_line}.",
            f"{player_name} slammed the door on the decisive throw and gave {team} its championship moment.{school_tag} He finished with {stat_line}."
        ],
        "S": [
            f"The defining moment came when {player_name} erased the final threat for {team}.{school_tag} He finished with {stat_line}.",
            f"{player_name} delivered the game-sealing interception for {team}.{school_tag} He posted {stat_line}.",
            f"The Super Bowl turned on a last-line defensive play from {player_name} for {team}.{school_tag} He ended with {stat_line}."
        ],
        "OTHER": [
            f"The defining moment came when {player_name} made the play that swung the game for {team}.{school_tag} He finished with {stat_line}.",
            f"{player_name} delivered the championship moment for {team}.{school_tag} He posted {stat_line}."
        ]
    }

    fail_templates = {
        "QB": [
            f"The turning point was a crushing mistake by {player_name} that swung the Super Bowl away from {team}.{school_tag} He finished with {stat_line}.",
            f"{team} never fully recovered after the late-game error involving {player_name}.{school_tag} He ended the night with {stat_line}.",
            f"The title slipped away when {player_name} forced the biggest throw of the game for {team}.{school_tag} He posted {stat_line}.",
            f"{team} lost control the moment the pressure finally got to {player_name} in the decisive sequence.{school_tag} He finished with {stat_line}."
        ],
        "RB": [
            f"The game tilted when {team} could not lean on {player_name} in the biggest moment.{school_tag} He finished with {stat_line}.",
            f"{team} lost control after a failed late rushing chance centered on {player_name}.{school_tag} He ended with {stat_line}.",
            f"The Super Bowl turned when {player_name} and the run game stalled for {team}.{school_tag} His final line was {stat_line}.",
            f"{team} never recovered after the backfield mistake involving {player_name} in the biggest spot of the game.{school_tag} He finished with {stat_line}."
        ],
        "WR": [
            f"The turning point came on a missed receiving moment involving {player_name} for {team}.{school_tag} He finished with {stat_line}.",
            f"{team} lost its grip on the game after the key pass play involving {player_name} broke down.{school_tag} He posted {stat_line}.",
            f"The Super Bowl turned on a missed opportunity for {player_name} and {team}.{school_tag} He ended with {stat_line}.",
            f"The biggest missed chance of the night landed on {player_name} for {team}.{school_tag} He finished with {stat_line}."
        ],
        "TE": [
            f"The turning point came on a red-zone miss involving {player_name} for {team}.{school_tag} He finished with {stat_line}.",
            f"{team} let the moment slip away when the key play to {player_name} failed to connect.{school_tag} He posted {stat_line}.",
            f"The Super Bowl turned on a missed chance for {player_name} in the biggest moment for {team}.{school_tag} He ended with {stat_line}."
        ],
        "EDGE": [
            f"The title slipped when {team} could not get the pressure it needed, with {player_name} caught in the decisive sequence.{school_tag} He finished with {stat_line}.",
            f"The biggest pass-rush miss of the night hurt {team} at the worst time, and {player_name} was part of it.{school_tag} He posted {stat_line}.",
            f"The turning point came when {team} failed to close the pocket, leaving {player_name} on the wrong side of the moment.{school_tag} He ended with {stat_line}."
        ],
        "IDL": [
            f"The title slipped when {team} failed to control the middle in the decisive moment, with {player_name} involved in the breakdown.{school_tag} He finished with {stat_line}.",
            f"The biggest defensive lapse up front hurt {team} at the wrong time, with {player_name} caught in the sequence.{school_tag} He posted {stat_line}.",
            f"The turning point came when {team} could not hold the interior, and {player_name} was part of the costly moment.{school_tag} He ended with {stat_line}."
        ],
        "LB": [
            f"The turning point came when {team} could not get the stop it needed, with {player_name} caught in the decisive sequence.{school_tag} He finished with {stat_line}.",
            f"The biggest defensive miss of the night hit {team} at the wrong time, with {player_name} on the field for it.{school_tag} He posted {stat_line}.",
            f"The Super Bowl turned when the final stop never came for {team}, and {player_name} was part of the moment.{school_tag} He ended with {stat_line}."
        ],
        "CB": [
            f"The game turned on a coverage lapse involving {player_name} for {team}.{school_tag} He finished with {stat_line}.",
            f"{team} lost the Super Bowl on a back-end breakdown that caught {player_name} in the spotlight.{school_tag} He posted {stat_line}.",
            f"The decisive sequence went against {team}'s secondary, with {player_name} on the wrong side of it.{school_tag} He ended with {stat_line}.",
            f"The title slipped away when the biggest throw of the game got behind {player_name}.{school_tag} He finished with {stat_line}."
        ],
        "S": [
            f"The game turned when the last line of defense broke the wrong way for {team}, with {player_name} caught in the moment.{school_tag} He finished with {stat_line}.",
            f"{team} lost its grip on the Super Bowl after a deep mistake involving {player_name}.{school_tag} He posted {stat_line}.",
            f"The decisive play went against {team}'s safety help, leaving {player_name} in the spotlight.{school_tag} He ended with {stat_line}."
        ],
        "OTHER": [
            f"The turning point was a crushing mistake that swung the game away from {team}, with {player_name} caught in the moment.{school_tag} He finished with {stat_line}.",
            f"{team} never fully recovered after the decisive mistake involving {player_name}.{school_tag} He posted {stat_line}."
        ]
    }

    key = pos_bucket if pos_bucket in hero_templates else "OTHER"
    pool = hero_templates[key] if is_hero else fail_templates[key]
    return random.choice(pool)

import zipfile
from io import BytesIO

NFL_EXPORT_FILES = [
    "nfl_draft_history.csv",
    "nfl_story_events.csv",
    "nfl_super_bowl_history.csv",
    "nfl_player_history.csv",
    "nfl_current_rosters.csv",
    "nfl_awards_history.csv",
    "nfl_playoff_history.csv",
    "nfl_standings_history.csv",
    "nfl_universe_settings.csv",
    "injury_bulletin.csv",
]

def build_nfl_export_zip():
    buffer = BytesIO()
    included_files = []

    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_name in NFL_EXPORT_FILES:
            if os.path.exists(file_name):
                zf.write(file_name, arcname=file_name)
                included_files.append(file_name)

    buffer.seek(0)
    return buffer.getvalue(), included_files

def score_super_bowl_moment_candidate(row):
    pos_bucket = clean_display(row.get("PosBucket", clean_bucket(row.get("Pos", ""))), "")
    role = clean_display(row.get("Role", ""), "")
    starts = safe_num(row.get("Starts", 0), 0)
    overall_end = safe_num(row.get("OverallEnd", 0), 0)
    career_value = safe_num(row.get("CareerValue", 0), 0)
    mvp_votes = safe_num(row.get("MVPVotes", 0), 0)

    score = 0.0
    score += career_value * 1.0
    score += overall_end * 0.35
    score += starts * 2.0
    score += mvp_votes * 2.5

    if role in {"Starter", "Day 1 Starter"}:
        score += 20
    elif role in {"QB Battle", "Starter Battle"}:
        score += 10
    elif role in {"WR3", "CB3", "RB2", "TE2", "Primary Rotation", "Pass Rush Rotation", "DL Rotation", "LB Rotation", "DB Rotation", "Committee Back"}:
        score += 4
    elif "Backup" in role or role in {"QB2", "Developmental QB", "Depth", "Depth Piece", "Rotation WR", "Depth Back", "Depth TE", "Depth OL", "Depth EDGE", "Depth IDL", "Depth LB", "Depth CB", "Depth Safety"}:
        score -= 8

    # Big suppression for backup QBs unless they truly played
    if pos_bucket == "QB":
        if starts >= 14:
            score += 22
        elif starts >= 10:
            score += 12
        elif starts >= 6:
            score += 3
        else:
            score -= 55

        if role not in {"Starter", "QB Battle"} and starts < 8:
            score -= 60

    # Skill guys and defenders still need real usage
    elif pos_bucket in {"RB", "WR", "TE"}:
        if starts >= 10:
            score += 10
        elif starts >= 6:
            score += 4
        elif starts <= 2:
            score -= 15

    elif pos_bucket in {"EDGE", "IDL", "LB", "CB", "S"}:
        if starts >= 10:
            score += 8
        elif starts >= 6:
            score += 3
        elif starts <= 2:
            score -= 10

    return round(score, 2)

def generate_super_bowl_signature_moment(champion, runner_up, score, season_player_df, nfl_draft_hist_df=None):
    champion = str(champion)
    runner_up = str(runner_up)
    score = str(score)

    if season_player_df is None or season_player_df.empty:
        return f"{champion} made the final drive stand up in a gritty {score} Super Bowl win.", ""

    game_pool = season_player_df[
        season_player_df["NFLTeam"].astype(str).isin([champion, runner_up])
    ].copy()

    if game_pool.empty:
        return f"{champion} made the final drive stand up in a gritty {score} Super Bowl win.", ""

    draft_lookup = {}
    if nfl_draft_hist_df is not None and not nfl_draft_hist_df.empty:
        for _, dr in nfl_draft_hist_df.iterrows():
            draft_lookup[str(dr.get("PlayerID", ""))] = {
                "CollegeTeam": clean_display(dr.get("CollegeTeam", ""), ""),
                "CollegeUser": clean_display(dr.get("CollegeUser", ""), "")
            }

    game_pool["CareerValue"] = pd.to_numeric(game_pool.get("CareerValue", 0), errors="coerce").fillna(0)
    game_pool["OverallEnd"] = pd.to_numeric(game_pool.get("OverallEnd", 0), errors="coerce").fillna(0)
    game_pool["Starts"] = pd.to_numeric(game_pool.get("Starts", 0), errors="coerce").fillna(0)
    game_pool["MVPVotes"] = pd.to_numeric(game_pool.get("MVPVotes", 0), errors="coerce").fillna(0)
    game_pool["SBMomentScore"] = game_pool.apply(score_super_bowl_moment_candidate, axis=1)

    def is_user_alum(row):
        meta = draft_lookup.get(str(row.get("PlayerID", "")), {})
        return clean_display(meta.get("CollegeUser", ""), "") != ""

    user_pool = game_pool[game_pool.apply(is_user_alum, axis=1)].copy()

    def player_meta(row):
        meta = draft_lookup.get(str(row.get("PlayerID", "")), {})
        return {
            "player": clean_display(row.get("Player", ""), "Unknown Player"),
            "team": clean_display(row.get("NFLTeam", ""), ""),
            "pos": clean_display(row.get("Pos", ""), ""),
            "stat": generate_super_bowl_game_statline(row),
            "school": clean_display(meta.get("CollegeTeam", ""), ""),
            "user": clean_display(meta.get("CollegeUser", ""), "")
        }

    def make_hero_line(row):
        m = player_meta(row)
        return build_super_bowl_moment_text(
            player_name=m["player"],
            team=m["team"],
            pos_bucket=clean_display(row.get("PosBucket", clean_bucket(row.get("Pos", ""))), ""),
            school=m["school"],
            stat_line=m["stat"],
            is_hero=True
        )

    def make_failure_line(row):
        m = player_meta(row)
        return build_super_bowl_moment_text(
            player_name=m["player"],
            team=m["team"],
            pos_bucket=clean_display(row.get("PosBucket", clean_bucket(row.get("Pos", ""))), ""),
            school=m["school"],
            stat_line=m["stat"],
            is_hero=False
        )

    used_player = ""

    user_champs = user_pool[user_pool["NFLTeam"].astype(str) == champion].copy()
    champ_pool = game_pool[game_pool["NFLTeam"].astype(str) == champion].copy()
    runner_pool = game_pool[game_pool["NFLTeam"].astype(str) == runner_up].copy()

    # Prefer user alumni heroes, but only if they actually profile like major contributors
    if not user_champs.empty and random.random() < 0.60:
        hero_pool = user_champs.sort_values(["SBMomentScore", "CareerValue", "OverallEnd"], ascending=[False, False, False]).head(3).copy()
        if not hero_pool.empty:
            hero = hero_pool.sample(1).iloc[0]
            used_player = clean_display(hero.get("Player", ""), "")
            return make_hero_line(hero), used_player

    # Occasionally use a painful runner-up failure, but not from random low-usage backups
    if not runner_pool.empty and random.random() < 0.20:
        fail_pool = runner_pool.sort_values(["SBMomentScore", "CareerValue", "OverallEnd"], ascending=[True, True, True]).head(3).copy()

        # Remove truly irrelevant low-usage guys if possible
        meaningful_fail_pool = fail_pool[fail_pool["SBMomentScore"] > -20].copy()
        if not meaningful_fail_pool.empty:
            fail_pool = meaningful_fail_pool

        if not fail_pool.empty:
            fail = fail_pool.sample(1).iloc[0]
            used_player = clean_display(fail.get("Player", ""), "")
            return make_failure_line(fail), used_player

    # Most of the time use one of the champion's strongest real contributors
    if not champ_pool.empty:
        hero_pool = champ_pool.sort_values(["SBMomentScore", "CareerValue", "OverallEnd"], ascending=[False, False, False]).head(5).copy()

        # Prefer meaningful contributors if possible
        meaningful_hero_pool = hero_pool[hero_pool["SBMomentScore"] > 15].copy()
        if not meaningful_hero_pool.empty:
            hero_pool = meaningful_hero_pool

        hero = hero_pool.sample(1).iloc[0]
        used_player = clean_display(hero.get("Player", ""), "")
        return make_hero_line(hero), used_player

    if not runner_pool.empty:
        fail_pool = runner_pool.sort_values(["SBMomentScore", "CareerValue", "OverallEnd"], ascending=[True, True, True]).head(4).copy()
        fail = fail_pool.sample(1).iloc[0]
        used_player = clean_display(fail.get("Player", ""), "")
        return make_failure_line(fail), used_player

    return f"{champion} made the final drive stand up in a gritty {score} Super Bowl win.", used_player

def generate_super_bowl_user_alumni_note(champion, runner_up, season_player_df, nfl_draft_hist_df=None, already_used_player=""):
    if season_player_df is None or season_player_df.empty or nfl_draft_hist_df is None or nfl_draft_hist_df.empty:
        return ""

    game_pool = season_player_df[
        season_player_df["NFLTeam"].astype(str).isin([str(champion), str(runner_up)])
    ].copy()

    if game_pool.empty:
        return ""

    draft_lookup = {}
    for _, dr in nfl_draft_hist_df.iterrows():
        draft_lookup[str(dr.get("PlayerID", ""))] = {
            "CollegeTeam": clean_display(dr.get("CollegeTeam", ""), ""),
            "CollegeUser": clean_display(dr.get("CollegeUser", ""), "")
        }

    game_pool["CareerValue"] = pd.to_numeric(game_pool.get("CareerValue", 0), errors="coerce").fillna(0)
    game_pool["OverallEnd"] = pd.to_numeric(game_pool.get("OverallEnd", 0), errors="coerce").fillna(0)

    user_rows = []
    for _, r in game_pool.iterrows():
        meta = draft_lookup.get(str(r.get("PlayerID", "")), {})
        if clean_display(meta.get("CollegeUser", ""), ""):
            player_name = clean_display(r.get("Player", ""), "")
            if player_name and player_name != already_used_player:
                user_rows.append((r, meta))

    if not user_rows:
        return ""

    user_rows = sorted(
        user_rows,
        key=lambda x: (
            safe_num(x[0].get("CareerValue", 0), 0),
            safe_num(x[0].get("OverallEnd", 0), 0)
        ),
        reverse=True
    )

    r, meta = user_rows[0]
    player = clean_display(r.get("Player", ""), "")
    team = clean_display(r.get("NFLTeam", ""), "")
    stat = generate_super_bowl_game_statline(r)
    school = clean_display(meta.get("CollegeTeam", ""), "")
    user = clean_display(meta.get("CollegeUser", ""), "")

    pos_bucket = clean_display(r.get("PosBucket", clean_bucket(r.get("Pos", ""))), "")

    if pos_bucket == "QB":
        options = [
            f"User alumni note: {player} ({school}, {user}) also had a major hand in the game for {team}, finishing with {stat}.",
            f"User alumni note: {player} ({school}, {user}) also helped drive the offense for {team} with {stat}.",
        ]
    elif pos_bucket in {"RB", "WR", "TE"}:
        options = [
            f"User alumni note: {player} ({school}, {user}) also produced in the Super Bowl for {team} with {stat}.",
            f"User alumni note: {player} ({school}, {user}) also contributed key offense for {team}, posting {stat}.",
        ]
    elif pos_bucket in {"EDGE", "IDL", "LB", "CB", "S"}:
        options = [
            f"User alumni note: {player} ({school}, {user}) also showed up defensively for {team}, posting {stat}.",
            f"User alumni note: {player} ({school}, {user}) also made his presence felt on defense for {team} with {stat}.",
        ]
    else:
        options = [
            f"User alumni note: {player} ({school}, {user}) also contributed for {team} with {stat}.",
            f"User alumni note: {player} ({school}, {user}) also played a part in the Super Bowl for {team}, finishing with {stat}.",
        ]

    return random.choice(options)

def play_user_pick_chime(audio_path="espn_chime.mp3"):
    try:
        if not st.session_state.get("draft_audio_enabled", False):
            return

        if not os.path.exists(audio_path):
            return

        audio_uri = file_to_data_uri(audio_path)
        if not audio_uri:
            return

        components.html(
            f"""
            <audio id="userPickChime" preload="auto">
                <source src="{audio_uri}" type="audio/mpeg">
            </audio>
            <script>
                const audio = document.getElementById("userPickChime");
                if (audio) {{
                    audio.currentTime = 0;
                    audio.play().catch(err => console.log("Audio play blocked:", err));
                }}
            </script>
            """,
            height=0,
        )
    except Exception:
        pass


ROUND_START = {1: 1, 2: 33, 3: 65, 4: 97, 5: 129, 6: 161, 7: 193}
ROUND_END   = {1: 32, 2: 64, 3: 96, 4: 128, 5: 160, 6: 192, 7: 224}

POS_BUCKET_MAP = {
    "QB": "QB",
    "HB": "RB",
    "RB": "RB",
    "FB": "RB",
    "WR": "WR",
    "TE": "TE",
    "LT": "OL",
    "LG": "OL",
    "C": "OL",
    "RG": "OL",
    "RT": "OL",
    "LEDG": "EDGE",
    "REDG": "EDGE",
    "EDGE": "EDGE",
    "LE": "EDGE",
    "RE": "EDGE",
    "DT": "IDL",
    "IDL": "IDL",
    "MIKE": "LB",
    "WILL": "LB",
    "SAM": "LB",
    "MLB": "LB",
    "LOLB": "LB",
    "ROLB": "LB",
    "LB": "LB",
    "CB": "CB",
    "FS": "S",
    "SS": "S",
    "S": "S",
}

POS_PREMIUM = {
    "QB": 10,
    "EDGE": 9,
    "WR": 8,
    "CB": 8,
    "OL": 7,
    "IDL": 6,
    "LB": 5,
    "S": 5,
    "RB": 4,
    "TE": 4,
}

NFL_UNIVERSE_SETTINGS_COLS = [
    "CurrentNFLSeason", "LastCompletedDraftYear", "LastCompletedSuperBowlSeason", "UniverseVersion"
]

CFB_USER_DRAFT_RESULTS_COLS = [
    "DraftYear", "Player", "CollegeTeam", "CollegeUser", "Pos", "Class", "OVR", "DraftRound"
]

NFL_DRAFT_HISTORY_COLS = [
    "DraftYear", "PlayerID", "Player", "CollegeTeam", "CollegeUser",
    "Pos", "PosBucket", "Class", "CollegeOVR", "OVR", "DraftRoundCanon",
    "GeneratedNFLTeam", "GeneratedRoundPick", "GeneratedOverallPick",
    "OriginalPick", "WasTrade", "TradeNote",
    "GenerationMethod", "DraftValueScore", "NeedScore", "CareerTier",
    "RookieRole", "PeakOVR", "StoryTag",
    "ProOutcome", "DevelopmentCurve",
    "DraftSource", "TrackStoryline",
    "IsCanonRound", "IsCanonTeam", "IsCanonPick"
]

NFL_CURRENT_ROSTER_COLS = [
    "Season", "Team", "PlayerID", "Name", "Pos", "PosBucket",
    "OVR", "Age", "Status", "Source", "CollegeTeam", "CollegeUser"
]

NFL_PLAYER_HISTORY_COLS = [
    "Season", "PlayerID", "Player", "NFLTeam", "Pos", "PosBucket", "Age", "Role",
    "OverallStart", "OverallEnd", "PeakOVR", "ProOutcome", "DevelopmentCurve",
    "Games", "Starts", "StatLine", "ProBowl", "AllPro", "MVPVotes",
    "SuperBowlWin", "SuperBowlAppear", "CareerValue", "Status"
]

NFL_SUPER_BOWL_HISTORY_COLS = [
    "Season", "Champion", "RunnerUp", "Score", "MVP", "MVPTeam", "Headline",
    "GameMoment", "UserAlumniNote"
]

NFL_STORY_EVENTS_COLS = [
    "Season", "Week", "PlayerID", "Player", "NFLTeam", "EventType", "Headline",
    "Description", "ImpactScore"
]

NFL_PLAYOFF_HISTORY_COLS = [
    "Season", "Round", "Winner", "Loser", "Score"
]

NFL_STANDINGS_HISTORY_COLS = [
    "Season", "Team", "Conference", "Wins", "Losses", "WinPct",
    "Seed", "TeamPower", "OffenseScore", "DefenseScore", "QBScore", "DepthScore", "StarPower"
]

NFL_AWARDS_HISTORY_COLS = [
    "Season", "Award", "PlayerID", "Player", "NFLTeam", "Pos", "Result", "Notes"
]
def ensure_csv_exists(path, columns, default_rows=None):
    if not os.path.exists(path):
        df = pd.DataFrame(default_rows or [], columns=columns)
        df.to_csv(path, index=False)


def normalize_key(s):
    import re
    return re.sub(r"[^a-z0-9]+", "", str(s).lower().strip())


def clean_bucket(pos):
    pos = str(pos).strip().upper()
    return POS_BUCKET_MAP.get(pos, pos)


def build_player_id(draft_year, college_team, player_name, pos):
    return f"{draft_year}_{normalize_key(college_team)}_{normalize_key(player_name)}_{normalize_key(pos)}"


def safe_num(value, default=0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _normalize_logo_key(s):
    import re
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())


def _build_logo_index(search_dir="."):
    idx = {}
    try:
        for fname in os.listdir(search_dir):
            if not fname.lower().endswith(".png"):
                continue
            stem = os.path.splitext(fname)[0]
            idx[_normalize_logo_key(stem)] = os.path.join(search_dir, fname)
    except Exception:
        pass
    return idx


def get_school_logo_path(team_name):
    name = str(team_name).strip()
    if not name:
        return None

    manual_map = {
        "Florida State": "floridaState.png",
        "Florida": "florida.png",
        "Bowling Green": "bowlingGreen.png",
        "USF": "southFlorida.png",
        "Texas Tech": "texasTech.png",
        "San Jose State": "sanJoseState.png",
        "Ohio State": "ohioState.png",
        "Boise State": "boiseState.png",
        "NC State": "ncState.png",
        "Ole Miss": "oleMiss.png",
        "Notre Dame": "notreDame.png",
        "Oklahoma State": "OklahomaState.png",
        "Air Force": "airForce.png",
        "UTSA": "texasSanAntonio.png",
        "Louisiana": "louisianaLafayette.png",
        "UL Monroe": "louisianaMonroe.png",
        "ULM": "louisianaMonroe.png",
        "Miami (OH)": "miamiOH.png",
        "Miami OH": "miamiOH.png",
        "Death Valley": "Death Valley.png",
        "Gate City": "GateCity.png",
        "Hammond": "Hammond.png",
        "Panama City": "Panama City.png",
        "Rapid City": "RapidCity.png",
        "Alabaster": "Alabaster.png",
    }

    for search_dir in [".", "logos"]:
        if name in manual_map:
            candidate = os.path.join(search_dir, manual_map[name])
            if os.path.exists(candidate):
                return candidate

    root_index = _build_logo_index(".")
    logos_index = _build_logo_index("logos")
    logo_index = {**logos_index, **root_index}

    alias_keys = {
        "usf": "southFlorida",
        "utsa": "texasSanAntonio",
        "ulm": "louisianaMonroe",
        "ulmonroe": "louisianaMonroe",
        "louisiana": "louisianaLafayette",
        "miamioh": "miamiOH",
        "ncstate": "ncState",
        "olemiss": "oleMiss",
        "notredame": "notreDame",
        "oklahomastate": "OklahomaState",
        "airforce": "airForce",
        "appstate": "appalachianState",
    }

    norm_name = _normalize_logo_key(name)

    if norm_name in alias_keys:
        alias_norm = _normalize_logo_key(alias_keys[norm_name])
        if alias_norm in logo_index:
            return logo_index[alias_norm]

    if norm_name in logo_index:
        return logo_index[norm_name]

    parts = name.replace("&", "and").split()
    if parts:
        camel_name = parts[0].lower() + "".join(p[:1].upper() + p[1:] for p in parts[1:])
        camel_norm = _normalize_logo_key(camel_name)
        if camel_norm in logo_index:
            return logo_index[camel_norm]

    return None


def get_school_logo_html(team_name, width=52, margin="0"):
    if 'image_file_to_data_uri' in globals():
        local_path = get_school_logo_path(team_name)
        if local_path:
            uri = image_file_to_data_uri(local_path)
            if uri:
                return f'<img src="{uri}" width="{width}" style="margin:{margin}; filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.45));">'

    return f"""
        <div style="
            width:{width}px; height:{width}px; border-radius:50%;
            background:rgba(255,255,255,0.08); color:#FFF;
            display:flex; align-items:center; justify-content:center;
            font-weight:800; font-size:0.75rem; margin:{margin};
            border:1px solid rgba(255,255,255,0.15);
            text-align:center; padding:4px;
        ">CFB</div>
    """


def get_school_logo_src(team_name):
    if 'image_file_to_data_uri' in globals():
        local_path = get_school_logo_path(team_name)
        if local_path:
            uri = image_file_to_data_uri(local_path)
            if uri:
                return uri
    return None

def advance_nfl_universe_one_year(speed_mode="Broadcast", rerun_latest_draft=False):
    try:
        universe = load_nfl_universe_data()

        cfb_draft = universe.get("cfb_draft", pd.DataFrame())
        cfb_roster = universe.get("cfb_roster", pd.DataFrame())
        nfl_roster = universe.get("nfl_roster", pd.DataFrame())
        nfl_draft_hist = universe.get("nfl_draft_hist", pd.DataFrame())
        nfl_player_hist = universe.get("nfl_player_hist", pd.DataFrame())
        nfl_super_bowl = universe.get("nfl_super_bowl", pd.DataFrame())
        nfl_story = universe.get("nfl_story", pd.DataFrame())
        nfl_current_rosters = universe.get("nfl_current_rosters", pd.DataFrame())
        nfl_awards_hist = universe.get("nfl_awards_hist", pd.DataFrame())
        nfl_playoff_hist = universe.get("nfl_playoff_hist", pd.DataFrame())

        status_lines = []

        # Step 1: lock / rerun newest draft class
        updated_draft_hist, processed_year, draft_msg = refresh_nfl_draft_history(
            live_mode=False,
            speed_mode=speed_mode,
            force_latest=rerun_latest_draft
        )
        if draft_msg:
            status_lines.append(draft_msg)

        # reload after draft refresh
        universe = load_nfl_universe_data()
        nfl_draft_hist = universe.get("nfl_draft_hist", pd.DataFrame())
        nfl_current_rosters = universe.get("nfl_current_rosters", pd.DataFrame())
        nfl_player_hist = universe.get("nfl_player_hist", pd.DataFrame())

        # Step 2: refresh current rosters before season
        try:
            refreshed_rosters = build_nfl_current_rosters(
                season_year=get_current_nfl_season(),
                nfl_roster_df=universe.get("nfl_roster", pd.DataFrame()),
                nfl_draft_hist_df=nfl_draft_hist,
                nfl_player_hist_df=nfl_player_hist,
                existing_current_rosters_df=nfl_current_rosters
            )

            if refreshed_rosters is not None and not refreshed_rosters.empty:
                for col in NFL_CURRENT_ROSTER_COLS:
                    if col not in refreshed_rosters.columns:
                        refreshed_rosters[col] = pd.NA
                refreshed_rosters = refreshed_rosters[NFL_CURRENT_ROSTER_COLS].copy()
                refreshed_rosters.to_csv("nfl_current_rosters.csv", index=False)
                status_lines.append(f"Current NFL rosters refreshed for {get_current_nfl_season()}.")
        except Exception as e:
            status_lines.append(f"Roster refresh warning: {type(e).__name__}: {e}")

        # Step 3: simulate season
        sim_result, sim_msg = simulate_nfl_season()
        if sim_msg:
            status_lines.append(sim_msg)

        if sim_result is None:
            return None, " | ".join(status_lines)

        # Step 4: refresh next-season current rosters after offseason maintenance
        try:
            universe = load_nfl_universe_data()
            refreshed_postseason_rosters = build_nfl_current_rosters(
                season_year=get_current_nfl_season(),
                nfl_roster_df=universe.get("nfl_roster", pd.DataFrame()),
                nfl_draft_hist_df=universe.get("nfl_draft_hist", pd.DataFrame()),
                nfl_player_hist_df=universe.get("nfl_player_hist", pd.DataFrame()),
                existing_current_rosters_df=universe.get("nfl_current_rosters", pd.DataFrame())
            )

            if refreshed_postseason_rosters is not None and not refreshed_postseason_rosters.empty:
                for col in NFL_CURRENT_ROSTER_COLS:
                    if col not in refreshed_postseason_rosters.columns:
                        refreshed_postseason_rosters[col] = pd.NA
                refreshed_postseason_rosters = refreshed_postseason_rosters[NFL_CURRENT_ROSTER_COLS].copy()
                refreshed_postseason_rosters.to_csv("nfl_current_rosters.csv", index=False)
                status_lines.append(f"Postseason/offseason rosters refreshed for {get_current_nfl_season()}.")
        except Exception as e:
            status_lines.append(f"Postseason roster refresh warning: {type(e).__name__}: {e}")

        return sim_result, " | ".join(status_lines)

    except Exception as e:
        return None, f"NFL year advance error: {type(e).__name__}: {e}"

def get_nfl_logo_slug(team_name):
    name = str(team_name).strip().lower()

    slug_map = {
        "arizona cardinals": "cardinals", "cardinals": "cardinals",
        "atlanta falcons": "falcons", "falcons": "falcons",
        "baltimore ravens": "ravens", "ravens": "ravens",
        "buffalo bills": "bills", "bills": "bills",
        "carolina panthers": "panthers", "panthers": "panthers",
        "chicago bears": "bears", "bears": "bears",
        "cincinnati bengals": "bengals", "bengals": "bengals",
        "cleveland browns": "browns", "browns": "browns",
        "dallas cowboys": "cowboys", "cowboys": "cowboys",
        "denver broncos": "broncos", "broncos": "broncos",
        "detroit lions": "lions", "lions": "lions",
        "green bay packers": "packers", "packers": "packers",
        "houston texans": "texans", "texans": "texans",
        "indianapolis colts": "colts", "colts": "colts",
        "jacksonville jaguars": "jaguars", "jaguars": "jaguars",
        "kansas city chiefs": "chiefs", "chiefs": "chiefs",
        "las vegas raiders": "raiders", "raiders": "raiders",
        "los angeles chargers": "chargers", "chargers": "chargers",
        "los angeles rams": "rams", "rams": "rams",
        "miami dolphins": "dolphins", "dolphins": "dolphins",
        "minnesota vikings": "vikings", "vikings": "vikings",
        "new england patriots": "patriots", "patriots": "patriots",
        "new orleans saints": "saints", "saints": "saints",
        "new york giants": "giants", "giants": "giants",
        "new york jets": "jets", "jets": "jets",
        "philadelphia eagles": "eagles", "eagles": "eagles",
        "pittsburgh steelers": "steelers", "steelers": "steelers",
        "san francisco 49ers": "49ers", "49ers": "49ers",
        "seattle seahawks": "seahawks", "seahawks": "seahawks",
        "tampa bay buccaneers": "buccaneers", "buccaneers": "buccaneers",
        "tennessee titans": "titans", "titans": "titans",
        "washington commanders": "commanders", "commanders": "commanders", "washington redskins": "redskins", "redskins": "redskins",
    }

    return slug_map.get(name)


def get_nfl_logo_path(team_name):
    slug = get_nfl_logo_slug(team_name)
    if not slug:
        return None

    candidates = [
        f"{slug}.png",
        os.path.join(".", f"{slug}.png"),
    ]

    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def get_nfl_logo_html(team_name, width=52, margin="0"):
    if 'image_file_to_data_uri' in globals():
        local_path = get_nfl_logo_path(team_name)
        if local_path:
            uri = image_file_to_data_uri(local_path)
            if uri:
                return f'<img src="{uri}" width="{width}" style="margin:{margin}; filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.45));">'

    return f"""
        <div style="
            width:{width}px; height:{width}px; border-radius:50%;
            background:rgba(255,255,255,0.08); color:#FFF;
            display:flex; align-items:center; justify-content:center;
            font-weight:800; font-size:0.8rem; margin:{margin};
            border:1px solid rgba(255,255,255,0.15);
        ">NFL</div>
    """


def get_nfl_logo_src(team_name):
    team = str(team_name).strip().lower()

    team_aliases = {
        "cardinals": "cardinals",
        "falcons": "falcons",
        "ravens": "ravens",
        "bills": "bills",
        "panthers": "panthers",
        "bears": "bears",
        "bengals": "bengals",
        "browns": "browns",
        "cowboys": "cowboys",
        "broncos": "broncos",
        "lions": "lions",
        "packers": "packers",
        "texans": "texans",
        "colts": "colts",
        "jaguars": "jaguars",
        "chiefs": "chiefs",
        "raiders": "raiders",
        "chargers": "chargers",
        "rams": "rams",
        "dolphins": "dolphins",
        "vikings": "vikings",
        "patriots": "patriots",
        "saints": "saints",
        "giants": "giants",
        "jets": "jets",
        "eagles": "eagles",
        "steelers": "steelers",
        "49ers": "49ers",
        "seahawks": "seahawks",
        "buccaneers": "buccaneers",
        "bucs": "buccaneers",
        "titans": "titans",
        "commanders": "commanders",
        "washington commanders": "commanders",
        "washington": "commanders"
    }

    slug = team_aliases.get(team, team)

    local_candidates = [
        f"{slug}.png",
        f"_{slug}.png",
        f"nfl_{slug}.png",
        os.path.join("logos", f"{slug}.png"),
        os.path.join("assets", "logos", f"{slug}.png"),
    ]

    for path in local_candidates:
        if os.path.exists(path):
            return image_file_to_data_uri(path)

    return None


def calc_athletic_bonus(row, bucket):
    spd = safe_num(row.get("SPD", 0))
    acc = safe_num(row.get("ACC", 0))
    agi = safe_num(row.get("AGI", 0))
    cod = safe_num(row.get("COD", 0))
    awr = safe_num(row.get("AWR", 0))
    strength = safe_num(row.get("STR", 0))

    if bucket in {"WR", "CB", "RB", "S"}:
        return (spd + acc + agi + cod) / 20.0
    if bucket == "QB":
        return (awr + acc + agi) / 15.0
    if bucket in {"OL", "IDL", "EDGE", "LB"}:
        return (strength + acc + awr) / 15.0
    if bucket == "TE":
        return (spd + strength + acc) / 18.0
    return (spd + acc + awr) / 18.0


def calc_draft_value(row):
    bucket = clean_bucket(row.get("PosBucket", row.get("Pos", "")))
    ovr = safe_num(row.get("OVR", 0))
    awr = safe_num(row.get("AWR", 0))
    player_class = str(row.get("Class", "")).strip()

    class_bonus = {
        "JR": 2.5,
        "JR (RS)": 1.5,
        "SR": 1.0,
        "SR (RS)": 0.5,
    }.get(player_class, 0.0)

    athletic_bonus = calc_athletic_bonus(row, bucket)
    pos_bonus = POS_PREMIUM.get(bucket, 3)
    variance = random.uniform(-2.5, 2.5)

    return round((ovr * 0.70) + (awr * 0.08) + athletic_bonus + pos_bonus + class_bonus + variance, 2)


def build_nfl_team_needs(nfl_roster_df):
    if nfl_roster_df is None or nfl_roster_df.empty:
        return pd.DataFrame(columns=[
            "NFLTeam", "PosBucket", "NeedScore", "StarterOVR", "StarterAge", "DepthCount"
        ])

    df = nfl_roster_df.copy()

    if "Team" not in df.columns:
        df["Team"] = ""
    if "Pos" not in df.columns:
        df["Pos"] = ""
    if "OVR" not in df.columns:
        df["OVR"] = 70
    if "Age" not in df.columns:
        df["Age"] = 25

    df["Team"] = df["Team"].fillna("").astype(str).str.strip()
    df["Pos"] = df["Pos"].fillna("").astype(str).str.strip()
    df["OVR"] = pd.to_numeric(df["OVR"], errors="coerce").fillna(70)
    df["Age"] = pd.to_numeric(df["Age"], errors="coerce").fillna(25)
    df["PosBucket"] = df["Pos"].map(clean_bucket)

    room_targets = {
        "QB": 3,
        "RB": 4,
        "WR": 6,
        "TE": 3,
        "OL": 9,
        "EDGE": 4,
        "IDL": 4,
        "LB": 5,
        "CB": 5,
        "S": 4
    }

    starter_counts = {
        "QB": 1,
        "RB": 1,
        "WR": 3,
        "TE": 1,
        "OL": 5,
        "EDGE": 2,
        "IDL": 2,
        "LB": 3,
        "CB": 2,
        "S": 2
    }

    premium_weight = {
        "QB": 1.55,
        "OL": 1.20,
        "EDGE": 1.18,
        "CB": 1.12,
        "WR": 1.10,
        "LT": 1.15,
        "S": 1.00,
        "RB": 0.95,
        "TE": 0.95,
        "IDL": 1.00,
        "LB": 0.98
    }

    rows = []

    for team in sorted(df["Team"].dropna().astype(str).unique().tolist()):
        team_df = df[df["Team"].astype(str) == str(team)].copy()

        for bucket, room_target in room_targets.items():
            room = team_df[team_df["PosBucket"].astype(str) == str(bucket)].copy()
            room = room.sort_values(["OVR", "Age"], ascending=[False, True]).reset_index(drop=True)

            starter_n = starter_counts.get(bucket, 1)

            starter_ovr = safe_num(room["OVR"].iloc[0], 68) if not room.empty else 68
            starter_age = safe_num(room["Age"].iloc[0], 25) if not room.empty else 25
            depth_count = int(len(room))

            top_starters = room.head(starter_n).copy()
            top_depth = room.head(min(room_target, len(room))).copy()

            starter_avg = safe_num(top_starters["OVR"].mean(), starter_ovr if not room.empty else 68)
            depth_avg = safe_num(top_depth["OVR"].mean(), starter_avg if not top_starters.empty else 68)

            need = 0.0

            if bucket == "QB":
                if starter_ovr <= 72:
                    need += 42
                elif starter_ovr <= 76:
                    need += 30
                elif starter_ovr <= 80:
                    need += 18
                elif starter_ovr <= 84:
                    need += 8

                if starter_ovr >= 95 and starter_age <= 31:
                    need -= 50
                elif starter_ovr >= 90 and starter_age <= 32:
                    need -= 40
                elif starter_ovr >= 85 and starter_age <= 30:
                    need -= 28
                elif starter_ovr >= 82 and starter_age <= 28:
                    need -= 18

            else:
                if starter_avg <= 70:
                    need += 26
                elif starter_avg <= 74:
                    need += 18
                elif starter_avg <= 78:
                    need += 10
                elif starter_avg <= 82:
                    need += 4

                if starter_age >= 32:
                    need += 5
                elif starter_age >= 30:
                    need += 2

                if starter_avg >= 90:
                    need -= 18
                elif starter_avg >= 86:
                    need -= 10

            missing_depth = max(0, room_target - depth_count)
            need += missing_depth * 4.5

            if depth_count > 0:
                if depth_avg <= 68:
                    need += 6
                elif depth_avg <= 72:
                    need += 3
                elif depth_avg >= 84:
                    need -= 4

            if depth_count >= room_target:
                if starter_avg >= 84 and depth_avg >= 78:
                    need -= 8
                if starter_avg >= 88 and depth_avg >= 80:
                    need -= 6

            need *= premium_weight.get(bucket, 1.0)
            need = round(max(0, min(99, need)), 2)

            rows.append({
                "NFLTeam": team,
                "PosBucket": bucket,
                "NeedScore": need,
                "StarterOVR": round(float(starter_ovr), 2),
                "StarterAge": round(float(starter_age), 2),
                "DepthCount": depth_count
            })

    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(columns=[
            "NFLTeam", "PosBucket", "NeedScore", "StarterOVR", "StarterAge", "DepthCount"
        ])

    out = out.sort_values(["NFLTeam", "NeedScore"], ascending=[True, False]).reset_index(drop=True)
    return out

def assign_career_tier(round_num):
    r = random.random()
    tables = {
        1: [("Superstar", 0.18), ("Star", 0.28), ("Solid Starter", 0.27), ("Starter", 0.17), ("Rotation", 0.07), ("Bust", 0.03)],
        2: [("Superstar", 0.08), ("Star", 0.20), ("Solid Starter", 0.30), ("Starter", 0.22), ("Rotation", 0.13), ("Bust", 0.07)],
        3: [("Superstar", 0.05), ("Star", 0.14), ("Solid Starter", 0.24), ("Starter", 0.26), ("Rotation", 0.20), ("Bust", 0.11)],
        4: [("Star", 0.03), ("Solid Starter", 0.12), ("Starter", 0.28), ("Rotation", 0.32), ("Fringe", 0.18), ("Bust", 0.07)],
        5: [("Star", 0.02), ("Solid Starter", 0.08), ("Starter", 0.20), ("Rotation", 0.35), ("Fringe", 0.25), ("Bust", 0.10)],
        6: [("Star", 0.01), ("Solid Starter", 0.05), ("Starter", 0.14), ("Rotation", 0.32), ("Fringe", 0.33), ("Bust", 0.15)],
        7: [("Star", 0.01), ("Solid Starter", 0.04), ("Starter", 0.10), ("Rotation", 0.25), ("Fringe", 0.38), ("Bust", 0.22)],
    }
    table = tables.get(int(round_num), tables[7])
    total = 0.0
    for label, p in table:
        total += p
        if r <= total:
            return label
    return table[-1][0]


def assign_rookie_role(round_num, need_score, pos_bucket):
    round_num = int(round_num)
    need_score = safe_num(need_score, 0)

    if pos_bucket == "QB":
        if round_num == 1 and need_score >= 80:
            return "QB Battle"
        if round_num <= 2:
            return "QB2"
        return "Developmental QB"

    if pos_bucket == "RB":
        if round_num <= 2 and need_score >= 70:
            return "Committee Back"
        if round_num <= 4:
            return "RB2"
        return "Depth Back"

    if pos_bucket == "WR":
        if round_num == 1 and need_score >= 80:
            return "Day 1 Starter"
        if round_num <= 2:
            return "WR3"
        return "Rotation WR"

    if pos_bucket == "TE":
        if round_num <= 3:
            return "TE2"
        return "Depth TE"

    if pos_bucket == "OL":
        if round_num <= 2 and need_score >= 75:
            return "Starter Battle"
        if round_num <= 4:
            return "Swing OL"
        return "Depth OL"

    if pos_bucket == "EDGE":
        if round_num <= 2:
            return "Pass Rush Rotation"
        return "Depth EDGE"

    if pos_bucket == "IDL":
        if round_num <= 3:
            return "DL Rotation"
        return "Depth IDL"

    if pos_bucket == "LB":
        if round_num <= 3:
            return "LB Rotation"
        return "Depth LB"

    if pos_bucket == "CB":
        if round_num <= 2:
            return "CB3"
        return "Depth CB"

    if pos_bucket == "S":
        if round_num <= 3:
            return "DB Rotation"
        return "Depth Safety"

    if round_num == 1 and need_score >= 80:
        return "Day 1 Starter"
    if round_num <= 2 and need_score >= 70:
        return "Primary Rotation"
    if round_num <= 4:
        return "Depth Piece"
    return "Roster Battle"


def estimate_peak_ovr(base_ovr, career_tier):
    base_ovr = int(round(safe_num(base_ovr, 70)))
    bumps = {
        "Superstar": random.randint(6, 10),
        "Star": random.randint(4, 7),
        "Solid Starter": random.randint(2, 5),
        "Starter": random.randint(1, 3),
        "Rotation": random.randint(0, 2),
        "Fringe": random.randint(-1, 1),
        "Bust": random.randint(-3, 0),
    }
    return max(60, min(99, base_ovr + bumps.get(career_tier, 0)))


def generate_story_tag(pos_bucket, career_tier, round_num):
    if career_tier == "Superstar":
        return "Face of the franchise"
    if career_tier == "Star" and int(round_num) >= 3:
        return "Mid-round steal"
    if career_tier == "Bust" and int(round_num) == 1:
        return "First-round pressure"
    if pos_bucket in {"WR", "CB"}:
        return "Speed mismatch"
    if pos_bucket == "EDGE":
        return "Pass-rush juice"
    if pos_bucket == "QB":
        return "Franchise swing"
    if pos_bucket == "RB":
        return "Explosive weapon"
    if pos_bucket == "OL":
        return "Trench anchor"
    return "Developmental upside"


@st.cache_data(ttl=300)
def load_nfl_universe_data():
    ensure_csv_exists("cfb_user_draft_results.csv", CFB_USER_DRAFT_RESULTS_COLS)
    ensure_csv_exists("nfl_draft_history.csv", NFL_DRAFT_HISTORY_COLS)
    ensure_csv_exists("nfl_player_history.csv", NFL_PLAYER_HISTORY_COLS)
    ensure_csv_exists("nfl_super_bowl_history.csv", NFL_SUPER_BOWL_HISTORY_COLS)
    ensure_csv_exists("nfl_story_events.csv", NFL_STORY_EVENTS_COLS)
    ensure_csv_exists("nfl_standings_history.csv", NFL_STANDINGS_HISTORY_COLS)
    ensure_csv_exists("nfl_awards_history.csv", NFL_AWARDS_HISTORY_COLS)
    ensure_csv_exists("nfl_playoff_history.csv", NFL_PLAYOFF_HISTORY_COLS)
    ensure_csv_exists("nfl_current_rosters.csv", NFL_CURRENT_ROSTER_COLS)
    ensure_csv_exists("nfl_universe_settings.csv", NFL_UNIVERSE_SETTINGS_COLS, [{
        "CurrentNFLSeason": 2042,
        "LastCompletedDraftYear": 2041,
        "LastCompletedSuperBowlSeason": 2041,
        "UniverseVersion": 1
    }])

    nfl_roster = pd.read_csv("NFLroster26_MASTER.csv") if os.path.exists("NFLroster26_MASTER.csv") else pd.DataFrame()
    cfb_roster = pd.read_csv("cfb26_rosters_full.csv") if os.path.exists("cfb26_rosters_full.csv") else pd.DataFrame()
    cfb_draft = pd.read_csv("cfb_user_draft_results.csv")

    nfl_draft_hist = pd.read_csv("nfl_draft_history.csv")
    for col in NFL_DRAFT_HISTORY_COLS:
        if col not in nfl_draft_hist.columns:
            nfl_draft_hist[col] = pd.NA
    nfl_draft_hist = nfl_draft_hist.reindex(columns=NFL_DRAFT_HISTORY_COLS)
    
    nfl_current_rosters = pd.read_csv("nfl_current_rosters.csv")
    for col in NFL_CURRENT_ROSTER_COLS:
        if col not in nfl_current_rosters.columns:
            nfl_current_rosters[col] = pd.NA
    nfl_current_rosters = nfl_current_rosters.reindex(columns=NFL_CURRENT_ROSTER_COLS)

    nfl_player_hist = pd.read_csv("nfl_player_history.csv")
    nfl_super_bowl = pd.read_csv("nfl_super_bowl_history.csv")
    nfl_story = pd.read_csv("nfl_story_events.csv")
    nfl_settings = pd.read_csv("nfl_universe_settings.csv")

    nfl_standings_hist = pd.read_csv("nfl_standings_history.csv")
    for col in NFL_STANDINGS_HISTORY_COLS:
        if col not in nfl_standings_hist.columns:
            nfl_standings_hist[col] = pd.NA
    nfl_standings_hist = nfl_standings_hist.reindex(columns=NFL_STANDINGS_HISTORY_COLS)

    nfl_awards_hist = pd.read_csv("nfl_awards_history.csv")
    for col in NFL_AWARDS_HISTORY_COLS:
        if col not in nfl_awards_hist.columns:
            nfl_awards_hist[col] = pd.NA
    nfl_awards_hist = nfl_awards_hist.reindex(columns=NFL_AWARDS_HISTORY_COLS)

    nfl_playoff_hist = pd.read_csv("nfl_playoff_history.csv")
    for col in NFL_PLAYOFF_HISTORY_COLS:
        if col not in nfl_playoff_hist.columns:
            nfl_playoff_hist[col] = pd.NA
    nfl_playoff_hist = nfl_playoff_hist.reindex(columns=NFL_PLAYOFF_HISTORY_COLS)

    return {
        "nfl_roster": nfl_roster,
        "cfb_roster": cfb_roster,
        "cfb_draft": cfb_draft,
        "nfl_draft_hist": nfl_draft_hist,
        "nfl_player_hist": nfl_player_hist,
        "nfl_super_bowl": nfl_super_bowl,
        "nfl_story": nfl_story,
        "nfl_settings": nfl_settings,
        "nfl_standings_hist": nfl_standings_hist,
        "nfl_awards_hist": nfl_awards_hist,
        "nfl_playoff_hist": nfl_playoff_hist,
        "nfl_current_rosters": nfl_current_rosters,
    }

def calc_nfl_rookie_entry_ovr(cfb_ovr, draft_round, pos_bucket=""):
    cfb_ovr = safe_num(cfb_ovr, 80)
    draft_round = int(safe_num(draft_round, 7))
    pos_bucket = str(pos_bucket).strip().upper()

    # Lower overall entry curve: most rookies should not arrive as stars
    if cfb_ovr >= 99:
        rookie_ovr = random.randint(82, 84)
        if random.random() < 0.12:
            rookie_ovr = random.randint(85, 86)
    elif cfb_ovr >= 97:
        rookie_ovr = random.randint(81, 84)
        if random.random() < 0.08:
            rookie_ovr = 85
    elif cfb_ovr >= 95:
        rookie_ovr = random.randint(80, 83)
    elif cfb_ovr >= 93:
        rookie_ovr = random.randint(79, 82)
    elif cfb_ovr >= 90:
        rookie_ovr = random.randint(77, 81)
    elif cfb_ovr >= 87:
        rookie_ovr = random.randint(75, 79)
    elif cfb_ovr >= 84:
        rookie_ovr = random.randint(73, 77)
    elif cfb_ovr >= 80:
        rookie_ovr = random.randint(70, 75)
    else:
        rookie_ovr = random.randint(66, 72)

    # Draft capital matters, but less than before
    round_bonus_map = {
        1: 1.5,
        2: 0.5,
        3: 0.0,
        4: -1.0,
        5: -2.0,
        6: -3.0,
        7: -4.0
    }
    rookie_ovr += round_bonus_map.get(draft_round, -4.0)

    # Position nuance
    if pos_bucket == "QB":
        rookie_ovr -= 1.0
    elif pos_bucket in {"RB", "WR", "CB", "S"}:
        rookie_ovr += 0.5
    elif pos_bucket in {"OL", "IDL", "LB"}:
        rookie_ovr -= 0.5

    rookie_ovr = int(round(rookie_ovr))

    # Hard cap with very rare elite exceptions
    if rookie_ovr > 84:
        if random.random() < 0.08:
            rookie_ovr = min(86, rookie_ovr)
        else:
            rookie_ovr = 84

    rookie_ovr = max(64, min(86, rookie_ovr))
    return rookie_ovr
# ──────────────────────────────────────────────────────────────────────
# NFL UNIVERSE — DRAFT ENRICHMENT
# ──────────────────────────────────────────────────────────────────────
def assign_pro_outcome(cfb_ovr, draft_round, pos_bucket="", awr=75, spd=75, age=22):
    cfb_ovr = safe_num(cfb_ovr, 80)
    draft_round = int(safe_num(draft_round, 7))
    awr = safe_num(awr, 75)
    spd = safe_num(spd, 75)
    age = safe_num(age, 22)
    pos_bucket = str(pos_bucket).strip().upper()

    score = 0.0
    score += (cfb_ovr - 80) * 1.2
    score += max(0, 8 - draft_round) * 1.8
    score += (awr - 75) * 0.45
    score += (spd - 75) * 0.20

    volatility = 0.0
    if pos_bucket == "QB":
        volatility = random.uniform(-10, 8)
    elif pos_bucket in {"WR", "CB", "EDGE"}:
        volatility = random.uniform(-8, 7)
    elif pos_bucket in {"RB", "S", "LB"}:
        volatility = random.uniform(-6, 5)
    else:
        volatility = random.uniform(-5, 4)

    if age <= 21:
        volatility += random.uniform(-3, 3)
    elif age >= 24:
        volatility += random.uniform(-1, 1)

    score += volatility

    bust_roll = random.random()

    if draft_round == 1:
        if cfb_ovr >= 95:
            if bust_roll < 0.05:
                return "Bust", "Flat"
            elif bust_roll < 0.16:
                return "Developmental", "Slow Burn"
        elif cfb_ovr >= 90:
            if bust_roll < 0.08:
                return "Bust", "Flat"
            elif bust_roll < 0.24:
                return "Developmental", "Slow Burn"
        else:
            if bust_roll < 0.12:
                return "Bust", "Flat"
            elif bust_roll < 0.30:
                return "Developmental", "Slow Burn"

    elif draft_round in {2, 3}:
        if bust_roll < 0.14:
            return "Bust", "Flat"
        elif bust_roll < 0.34:
            return "Developmental", "Slow Burn"

    else:
        if bust_roll < 0.22:
            return "Bust", "Flat"
        elif bust_roll < 0.48:
            return "Developmental", "Slow Burn"

    if score >= 34:
        return "Superstar", "Fast Rise"
    elif score >= 26:
        return "Star", "Fast Rise"
    elif score >= 18:
        return "Impact Starter", "Steady Rise"
    elif score >= 10:
        return "Steady Starter", "Normal"
    elif score >= 4:
        return "Developmental", "Slow Burn"
    else:
        return "Bust", "Flat"


def estimate_peak_ovr_from_outcome(rookie_ovr, pro_outcome):
    rookie_ovr = int(safe_num(rookie_ovr, 75))
    outcome = str(pro_outcome).strip()

    if outcome == "Superstar":
        peak = rookie_ovr + random.randint(8, 13)
    elif outcome == "Star":
        peak = rookie_ovr + random.randint(6, 10)
    elif outcome == "Impact Starter":
        peak = rookie_ovr + random.randint(4, 7)
    elif outcome == "Steady Starter":
        peak = rookie_ovr + random.randint(2, 5)
    elif outcome == "Developmental":
        peak = rookie_ovr + random.randint(0, 3)
    else:  # Bust
        peak = rookie_ovr + random.randint(-6, 0)

    return max(62, min(99, peak))

def enrich_user_draft_results(cfb_draft_df, cfb_roster_df, nfl_roster_df):
    if cfb_draft_df is None or cfb_draft_df.empty:
        return pd.DataFrame(columns=NFL_DRAFT_HISTORY_COLS)

    work = cfb_draft_df.copy()

    for col in ["Player", "CollegeTeam", "CollegeUser", "Pos", "Class"]:
        if col in work.columns:
            work[col] = work[col].astype(str).str.strip()

    if "DraftYear" in work.columns:
        work["DraftYear"] = pd.to_numeric(work["DraftYear"], errors="coerce").fillna(0).astype(int)
    if "DraftRound" in work.columns:
        work["DraftRound"] = pd.to_numeric(work["DraftRound"], errors="coerce").fillna(0).astype(int)
    if "OVR" in work.columns:
        work["OVR"] = pd.to_numeric(work["OVR"], errors="coerce").fillna(0)

    roster_lookup = pd.DataFrame()
    if cfb_roster_df is not None and not cfb_roster_df.empty:
        roster_lookup = cfb_roster_df.copy()
        roster_lookup["Name_key"] = roster_lookup["Name"].astype(str).map(normalize_key)
        roster_lookup["Team_key"] = roster_lookup["Team"].astype(str).map(normalize_key)

    enriched_rows = []
    team_needs = build_nfl_team_needs(nfl_roster_df)
    nfl_teams = sorted(team_needs["NFLTeam"].dropna().astype(str).unique().tolist())

    if not nfl_teams:
        return pd.DataFrame(columns=NFL_DRAFT_HISTORY_COLS)

    for draft_year in sorted(work["DraftYear"].dropna().unique()):
        class_df = work[work["DraftYear"] == draft_year].copy()

        for rnd in sorted(class_df["DraftRound"].dropna().unique()):
            rnd = int(rnd)
            if rnd not in ROUND_START:
                continue

            pool = class_df[class_df["DraftRound"] == rnd].copy()
            if pool.empty:
                continue

            used_teams = set()
            row_objs = []

            for _, row in pool.iterrows():
                player_key = normalize_key(row.get("Player", ""))
                team_key = normalize_key(row.get("CollegeTeam", ""))

                roster_match = pd.DataFrame()
                if not roster_lookup.empty:
                    roster_match = roster_lookup[
                        (roster_lookup["Name_key"] == player_key) &
                        (roster_lookup["Team_key"] == team_key)
                    ].head(1)

                merged = row.to_dict()

                if not roster_match.empty:
                    for extra_col in ["OVR", "Year", "SPD", "ACC", "AGI", "COD", "STR", "AWR"]:
                        if extra_col in roster_match.columns:
                            val = roster_match.iloc[0][extra_col]
                            if extra_col == "Year":
                                if not merged.get("Class") or str(merged.get("Class")).strip() in {"", "nan", "None"}:
                                    merged["Class"] = val
                            elif extra_col not in merged or merged.get(extra_col) in [0, "", None] or pd.isna(merged.get(extra_col)):
                                merged[extra_col] = val

                if not merged.get("Class") or str(merged.get("Class")).strip() in {"", "nan", "None"}:
                    merged["Class"] = "SR"

                if safe_num(merged.get("OVR", 0), 0) == 0:
                    merged["OVR"] = 80

                merged["PosBucket"] = clean_bucket(merged.get("Pos", ""))
                draft_value = calc_draft_value(merged)

                row_objs.append({
                    "base": merged,
                    "draft_value": draft_value
                })

            row_objs = sorted(row_objs, key=lambda x: x["draft_value"], reverse=True)

            pick_slots = list(range(ROUND_START[rnd], min(ROUND_END[rnd], ROUND_START[rnd] + len(row_objs) - 1) + 1))
            if len(pick_slots) < len(row_objs):
                pick_slots = list(range(ROUND_START[rnd], ROUND_END[rnd] + 1))

            for idx, obj in enumerate(row_objs):
                merged = obj["base"]
                bucket = merged["PosBucket"]
                draft_value = obj["draft_value"]

                need_pool = team_needs[team_needs["PosBucket"] == bucket].copy()
                if need_pool.empty:
                    need_pool = team_needs.copy()

                need_pool["FitScore"] = need_pool["NeedScore"].astype(float) * 0.75 + draft_value * 0.15
                need_pool["FitScore"] = need_pool["FitScore"] + need_pool.apply(lambda _: random.uniform(0, 10), axis=1)

                fresh_need = need_pool[~need_pool["NFLTeam"].isin(used_teams)].copy()
                selection_pool = fresh_need if not fresh_need.empty else need_pool
                selection_pool = selection_pool.sort_values(["FitScore", "NeedScore"], ascending=False)

                chosen = selection_pool.iloc[0]
                chosen_team = str(chosen["NFLTeam"])
                need_score = round(float(chosen["NeedScore"]), 2)
                used_teams.add(chosen_team)

                overall_pick = pick_slots[idx] if idx < len(pick_slots) else ROUND_END[rnd]
                round_pick = overall_pick - ROUND_START[rnd] + 1

                career_tier = assign_career_tier(rnd)
                rookie_role = assign_rookie_role(rnd, need_score, bucket)
                rookie_entry_ovr = calc_nfl_rookie_entry_ovr(
                    cfb_ovr=safe_num(merged.get("OVR", 80), 80),
                    draft_round=rnd,
                    pos_bucket=bucket
                )
                pro_outcome, development_curve = assign_pro_outcome(
                    cfb_ovr=safe_num(merged.get("OVR", 80), 80),
                    draft_round=rnd,
                    pos_bucket=bucket,
                    awr=safe_num(merged.get("AWR", 75), 75),
                    spd=safe_num(merged.get("SPD", 75), 75),
                    age=safe_num(merged.get("Age", 22), 22)
                )
                peak_ovr = estimate_peak_ovr_from_outcome(
                    rookie_ovr=rookie_entry_ovr,
                    pro_outcome=pro_outcome
                )
                story_tag = generate_story_tag(bucket, career_tier, rnd)

                enriched_rows.append({
                    "DraftYear": int(draft_year),
                    "PlayerID": build_player_id(draft_year, merged.get("CollegeTeam", ""), merged.get("Player", ""), merged.get("Pos", "")),
                    "Player": merged.get("Player", ""),
                    "CollegeTeam": merged.get("CollegeTeam", ""),
                    "CollegeUser": merged.get("CollegeUser", ""),
                    "Pos": merged.get("Pos", ""),
                    "PosBucket": bucket,
                    "Class": merged.get("Class", ""),
                    "CollegeOVR": int(round(safe_num(merged.get("OVR", 80), 80))),
                    "OVR": rookie_entry_ovr,
                    "DraftRoundCanon": rnd,
                    "GeneratedNFLTeam": chosen_team,
                    "GeneratedRoundPick": int(round_pick),
                    "GeneratedOverallPick": int(overall_pick),
                    "OriginalPick": pd.NA,
                    "WasTrade": "No",
                    "TradeNote": "",
                    "GenerationMethod": "round_locked_team_generated",
                    "DraftValueScore": round(float(draft_value), 2),
                    "NeedScore": need_score,
                    "CareerTier": career_tier,
                    "RookieRole": rookie_role,
                    "PeakOVR": peak_ovr,
                    "StoryTag": story_tag,
                    "ProOutcome": pro_outcome,
                    "DevelopmentCurve": development_curve,
                    "DraftSource": row.get("DraftSource", "user_results"),
                    "TrackStoryline": row.get("TrackStoryline", "Yes"),
                    "IsCanonRound": "Yes",
                    "IsCanonTeam": "No",
                    "IsCanonPick": "No",
                })

    out = pd.DataFrame(enriched_rows)
    for col in NFL_DRAFT_HISTORY_COLS:
        if col not in out.columns:
            out[col] = pd.NA
    return out[NFL_DRAFT_HISTORY_COLS].copy()


def get_newest_unprocessed_draft_class(cfb_draft_df, nfl_draft_hist_df):
    if cfb_draft_df is None or cfb_draft_df.empty:
        return pd.DataFrame(), None, "No rows found in cfb_user_draft_results.csv."

    work = cfb_draft_df.copy()
    work["DraftYear"] = pd.to_numeric(work["DraftYear"], errors="coerce")
    work = work.dropna(subset=["DraftYear"]).copy()

    if work.empty:
        return pd.DataFrame(), None, "No valid DraftYear values found in cfb_user_draft_results.csv."

    work["DraftYear"] = work["DraftYear"].astype(int)
    newest_year = int(work["DraftYear"].max())

    existing_years = set()
    if nfl_draft_hist_df is not None and not nfl_draft_hist_df.empty and "DraftYear" in nfl_draft_hist_df.columns:
        existing_years = set(
            pd.to_numeric(nfl_draft_hist_df["DraftYear"], errors="coerce")
            .dropna()
            .astype(int)
            .tolist()
        )

    if newest_year in existing_years:
        return pd.DataFrame(), newest_year, f"Draft class {newest_year} is already locked in."

    newest_df = work[work["DraftYear"] == newest_year].copy()
    if newest_df.empty:
        return pd.DataFrame(), newest_year, f"No draft rows found for newest year {newest_year}."

    return newest_df, newest_year, None


def is_user_team(team_name):
    if 'USER_TEAMS' in globals():
        return str(team_name).strip() in set(USER_TEAMS.values())
    return False


def is_senior_label(year_val):
    y = str(year_val).strip().upper()
    return y in {"SR", "SR (RS)", "RS SR"}


def build_round1_pick_order(nfl_roster_df):
    if nfl_roster_df is None or nfl_roster_df.empty or "Team" not in nfl_roster_df.columns:
        return [
            "Bears", "Jets", "Giants", "Patriots", "Cardinals", "Commanders", "Titans", "Falcons",
            "Seahawks", "Raiders", "Saints", "Broncos", "Vikings", "Colts", "Steelers", "Bengals",
            "Browns", "Rams", "Dolphins", "Buccaneers", "Packers", "Texans", "Jaguars", "Chargers",
            "Cowboys", "Eagles", "Bills", "Lions", "49ers", "Chiefs", "Ravens", "Panthers"
        ]

    teams = sorted(nfl_roster_df["Team"].dropna().astype(str).unique().tolist())

    preferred_order = [
        "Bears", "Jets", "Giants", "Patriots", "Cardinals", "Commanders", "Redskins", "Titans",
        "Falcons", "Seahawks", "Raiders", "Saints", "Broncos", "Vikings", "Colts", "Steelers",
        "Bengals", "Browns", "Rams", "Dolphins", "Buccaneers", "Packers", "Texans", "Jaguars",
        "Chargers", "Cowboys", "Eagles", "Bills", "Lions", "49ers", "Chiefs", "Ravens", "Panthers"
    ]

    norm_map = {str(t).strip().lower(): t for t in teams}
    ordered = []

    for team in preferred_order:
        key = team.strip().lower()
        if key in norm_map and norm_map[key] not in ordered:
            ordered.append(norm_map[key])

    for team in teams:
        if team not in ordered:
            ordered.append(team)

    return ordered[:32]

def maybe_apply_round1_trade(current_pick, current_team, available_order, remaining_players, team_needs):
    if not available_order or len(available_order) < 2:
        return current_team, current_pick, "No", ""

    trade_chance = 0.22
    if random.random() > trade_chance:
        return current_team, current_pick, "No", ""

    if remaining_players is None or remaining_players.empty:
        return current_team, current_pick, "No", ""

    top_player = remaining_players.iloc[0]
    player_bucket = clean_bucket(top_player.get("PosBucket", top_player.get("Pos", "")))

    need_pool = team_needs[team_needs["PosBucket"] == player_bucket].copy()
    if need_pool.empty:
        return current_team, current_pick, "No", ""

    candidates = []
    for idx, team in enumerate(available_order):
        if str(team) == str(current_team):
            continue

        row = need_pool[need_pool["NFLTeam"].astype(str) == str(team)]
        if row.empty:
            continue

        need_score = safe_num(row.iloc[0].get("NeedScore", 0), 0)
        pick_num = current_pick + idx
        candidates.append((team, pick_num, need_score))

    if not candidates:
        return current_team, current_pick, "No", ""

    candidates = sorted(candidates, key=lambda x: (x[2], -x[1]), reverse=True)
    chosen_team, chosen_pick, _ = candidates[0]

    if chosen_pick == current_pick:
        return current_team, current_pick, "No", ""

    source_pick = int(chosen_pick)
    target_pick = int(current_pick)
    move_word = "up" if target_pick < source_pick else "down"
    trade_note = f"{chosen_team} traded {move_word} from #{source_pick} to #{target_pick}"

    return chosen_team, source_pick, "Yes", trade_note

def clean_display(val, fallback=""):
    if pd.isna(val):
        return fallback
    text = str(val).strip()
    if text.lower() in {"nan", "none", "<na>"}:
        return fallback
    return text

def draft_source_label(val):
    text = clean_display(val).lower()
    if text == "user_results":
        return "Tracked"
    if text == "cpu_pool":
        return "CPU Pool"
    return ""

def file_to_data_uri(path_str):
    try:
        if path_str and os.path.exists(path_str):
            ext = Path(path_str).suffix.lower().replace(".", "")
            mime_map = {
                "mp3": "audio/mpeg",
                "wav": "audio/wav",
                "ogg": "audio/ogg",
                "png": "image/png",
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "webp": "image/webp",
            }
            mime = mime_map.get(ext, "application/octet-stream")
            with open(path_str, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("ascii")
            return f"data:{mime};base64,{encoded}"
    except Exception:
        return ""
    return ""

def live_reveal_nfl_draft(generated_df, speed_mode="Broadcast"):
    if generated_df is None or generated_df.empty:
        st.info("No generated draft rows to reveal.")
        return generated_df

    df = generated_df.copy().sort_values(
        ["DraftYear", "GeneratedOverallPick", "Player"],
        ascending=[True, True, True]
    ).reset_index(drop=True)

    speed_map = {
        "Turbo": {"r1": 1.6, "mid": 0.35, "late": 0.15, "suspense": 0.50, "transition": 1.0},
        "Fast": {"r1": 3.5, "mid": 0.75, "late": 0.30, "suspense": 1.10, "transition": 1.8},
        "Broadcast": {"r1": 7.0, "mid": 3.0, "late": 1.5, "suspense": 2.00, "transition": 3.0},
    }
    speeds = speed_map.get(speed_mode, speed_map["Broadcast"])

    progress = st.progress(0, text="Initializing NFL Draft Universe...")
    header_ph = st.empty()
    trade_ph = st.empty()
    card_ph = st.empty()
    board_ph = st.empty()
    stats_ph = st.empty()

    revealed_rows = []
    total = len(df)
    day2_banner_shown = False

    for idx, (_, row) in enumerate(df.iterrows(), start=1):
        round_num = int(safe_num(row.get("DraftRoundCanon", 1), 1))
        overall_pick = int(safe_num(row.get("GeneratedOverallPick", idx), idx))
        nfl_team = clean_display(row.get("GeneratedNFLTeam", "Unknown Team"), "Unknown Team")
        school = clean_display(row.get("CollegeTeam", "Unknown School"), "Unknown School")
        player = clean_display(row.get("Player", "Unknown Player"), "Unknown Player")
        college_user = clean_display(row.get("CollegeUser", ""), "")
        pos = clean_display(row.get("Pos", ""), "")
        pos_bucket = clean_display(row.get("PosBucket", ""), "")
        rookie_role = clean_display(row.get("RookieRole", ""), "")
        career_tier = clean_display(row.get("CareerTier", ""), "")
        story_tag = clean_display(row.get("StoryTag", ""), "")
        college_ovr = int(safe_num(row.get("CollegeOVR", row.get("OVR", 0)), 0))
        ovr = int(safe_num(row.get("OVR", 0), 0))
        draft_source = clean_display(row.get("DraftSource", "cpu_pool"), "cpu_pool").lower()
        source_label = draft_source_label(draft_source)
        is_user_pick = draft_source == "user_results"
        was_trade = clean_display(row.get("WasTrade", "No"), "No").lower() == "yes"
        trade_note = clean_display(row.get("TradeNote", ""), "")

        progress.progress(idx / total, text=f"Revealing pick {overall_pick} of {total}")

        if is_user_pick:
            play_user_pick_chime()

        if round_num == 1:
            if is_user_pick:
                header_ph.markdown(
                    f"""
                    <div style="background:linear-gradient(135deg, rgba(245,158,11,0.20), rgba(255,255,255,0.03)); border:1px solid rgba(255,255,255,0.10); border-left:8px solid #22c55e; border-radius:14px; padding:14px 18px; margin-bottom:12px; box-shadow:0 6px 14px rgba(0,0,0,0.35);">
                        <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:14px;">
                            <div>
                                <div style="font-size:0.78rem; color:#86efac; text-transform:uppercase; letter-spacing:1.1px; font-weight:800;">NFL Draft • Round 1</div>
                                <div style="font-size:1.65rem; font-weight:900; color:#ffffff; margin-top:8px; line-height:1.15;">Pick #{overall_pick} is in</div>
                            </div>
                            <div style="display:flex; flex-direction:column; align-items:flex-end; gap:8px; margin-top:2px;">
                                <span style="display:inline-block;font-size:0.78rem;color:#dcfce7;font-weight:900;padding:6px 10px;border-radius:999px;background:rgba(34,197,94,0.18);border:1px solid rgba(34,197,94,0.35);white-space:nowrap;">USER PICK</span>
                                <span style="display:inline-block;font-size:0.82rem;color:#fef3c7;font-weight:800;padding:6px 10px;border-radius:999px;background:rgba(245,158,11,0.14);border:1px solid rgba(245,158,11,0.24);white-space:nowrap;">On the Clock</span>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                header_ph.markdown(
                    f"""
                    <div style="background:linear-gradient(135deg, rgba(245,158,11,0.20), rgba(255,255,255,0.03)); border:1px solid rgba(255,255,255,0.10); border-left:8px solid #f59e0b; border-radius:14px; padding:14px 18px; margin-bottom:12px; box-shadow:0 6px 14px rgba(0,0,0,0.35);">
                        <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:14px;">
                            <div>
                                <div style="font-size:0.78rem; color:#fcd34d; text-transform:uppercase; letter-spacing:1.1px; font-weight:800;">NFL Draft • Round 1</div>
                                <div style="font-size:1.65rem; font-weight:900; color:#ffffff; margin-top:8px; line-height:1.15;">Pick #{overall_pick} is in</div>
                            </div>
                            <div style="margin-top:2px;">
                                <span style="display:inline-block;font-size:0.82rem;color:#fef3c7;font-weight:800;padding:6px 10px;border-radius:999px;background:rgba(245,158,11,0.14);border:1px solid rgba(245,158,11,0.24);white-space:nowrap;">On the Clock</span>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            if was_trade and trade_note:
                trade_ph.markdown(textwrap.dedent(f"""
                    <div style="background:linear-gradient(90deg, rgba(34,197,94,0.18), rgba(255,255,255,0.03)); border:1px solid rgba(34,197,94,0.28); border-left:8px solid #22c55e; border-radius:14px; padding:12px 16px; margin-bottom:14px; box-shadow:0 6px 14px rgba(0,0,0,0.30);">
                        <div style="display:flex; align-items:center; justify-content:space-between; gap:16px;">
                            <div style="display:flex; align-items:center; gap:12px;">
                                <div style="width:36px; height:36px; border-radius:999px; background:rgba(34,197,94,0.18); display:flex; align-items:center; justify-content:center; font-size:1.05rem; border:1px solid rgba(34,197,94,0.30);">🔁</div>
                                <div>
                                    <div style="font-size:0.76rem; color:#86efac; text-transform:uppercase; letter-spacing:1.2px; font-weight:800;">Trade Alert</div>
                                    <div style="font-size:1.02rem; color:#f8fafc; font-weight:800; margin-top:2px;">{html.escape(trade_note)}</div>
                                </div>
                            </div>
                            <div style="font-size:0.78rem; color:#d1fae5; font-weight:700; padding:5px 9px; border-radius:999px; background:rgba(34,197,94,0.14); border:1px solid rgba(34,197,94,0.25); white-space:nowrap;">Round 1 Move</div>
                        </div>
                    </div>
                """), unsafe_allow_html=True)
            else:
                trade_ph.empty()

            time.sleep(speeds["suspense"])

            with card_ph.container():
                school_logo_src = get_school_logo_src(school)
                nfl_logo_src = get_nfl_logo_src(nfl_team)

                top_left, top_mid, top_right = st.columns([1, 2, 1])

                with top_left:
                    if school_logo_src:
                        school_logo_uri = file_to_data_uri(school_logo_src) if os.path.exists(str(school_logo_src)) else str(school_logo_src)
                        st.markdown(
                            f"""
                            <div style="width:100%; display:flex; justify-content:center; margin-bottom:10px;">
                                <img src="{school_logo_uri}" style="width:64px; height:64px; object-fit:contain;" />
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                with top_mid:
                    st.caption("SELECTED")
                    st.markdown(f"## {player}")
                    st.write(f"{pos} / {pos_bucket} • {college_ovr} CFB OVR • {ovr} NFL Rookie OVR")

                    role_line = f"{rookie_role} • {career_tier} ceiling".strip(" •")
                    if role_line:
                        st.write(role_line)

                    if story_tag:
                        st.caption(story_tag)

                with top_right:
                    if nfl_logo_src:
                        nfl_logo_uri = file_to_data_uri(nfl_logo_src) if os.path.exists(str(nfl_logo_src)) else str(nfl_logo_src)
                        st.markdown(
                            f"""
                            <div style="width:100%; display:flex; justify-content:center; margin-bottom:10px;">
                                <img src="{nfl_logo_uri}" style="width:64px; height:64px; object-fit:contain;" />
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                info_left, info_right = st.columns(2)

                with info_left:
                    st.caption("FROM")
                    st.markdown(f"**{school}**")
                    if college_user:
                        st.write(college_user)
                    if source_label:
                        st.caption(source_label)

                with info_right:
                    st.caption("TO")
                    st.markdown(f"**{nfl_team}**")
                    st.write(f"Round 1 • Pick {overall_pick}")

        else:
            if not day2_banner_shown:
                trade_ph.empty()
                card_ph.markdown(textwrap.dedent("""
                    <div style="background:linear-gradient(180deg, rgba(2,6,23,0.92), rgba(15,23,42,0.90)); border:1px solid rgba(255,255,255,0.08); border-top:4px solid #94a3b8; border-radius:18px; padding:28px 22px; margin-bottom:14px; box-shadow:0 10px 24px rgba(0,0,0,0.45); text-align:center;">
                        <div style="font-size:0.8rem; color:#94a3b8; text-transform:uppercase; letter-spacing:2px; font-weight:800; margin-bottom:8px;">End of Round 1</div>
                        <div style="font-size:2rem; font-weight:900; color:#ffffff; line-height:1.1; margin-bottom:8px;">Day 2 Begins</div>
                        <div style="font-size:1rem; color:#cbd5e1; line-height:1.5;">The first-round fireworks are over. The board now shifts to a faster view for Rounds 2–7.</div>
                    </div>
                """), unsafe_allow_html=True)

                time.sleep(speeds["transition"])

                header_ph.markdown(textwrap.dedent("""
                    <div style="background:linear-gradient(135deg, rgba(255,255,255,0.07), rgba(255,255,255,0.02)); border:1px solid rgba(255,255,255,0.10); border-left:6px solid #64748b; border-radius:12px; padding:12px 16px; margin-bottom:12px; box-shadow:0 6px 14px rgba(0,0,0,0.35);">
                        <div style="font-size:0.82rem; color:#d1d5db; text-transform:uppercase; letter-spacing:1px;">Day 2</div>
                        <div style="font-size:1.2rem; font-weight:800; color:#fff; margin-top:3px;">Rounds 2+ moving to board view</div>
                    </div>
                """), unsafe_allow_html=True)

                day2_banner_shown = True

            trade_ph.empty()
            card_ph.empty()

        revealed_rows.append({
            "Pick": overall_pick,
            "Rnd": round_num,
            "Player": player,
            "School": school,
            "User": college_user,
            "Pos": pos,
            "Bucket": pos_bucket,
            "NFL Team": nfl_team,
            "Source": source_label,
            "Trade": trade_note if was_trade else ""
        })

        board_df = pd.DataFrame(revealed_rows)
        if not board_df.empty:
            board_df.insert(3, "School Logo", board_df["School"].map(get_school_logo_src))
            board_df.insert(8, "NFL Logo", board_df["NFL Team"].map(get_nfl_logo_src))

        board_ph.dataframe(
            board_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "School Logo": st.column_config.ImageColumn(""),
                "NFL Logo": st.column_config.ImageColumn(""),
            }
        )

        first_rounders = sum(1 for r in revealed_rows if r["Rnd"] == 1)
        tracked_rows = [r for r in revealed_rows if r["Source"] == "Tracked" and clean_display(r["User"])]
        top_user = "—"
        if tracked_rows:
            tracked_df = pd.DataFrame(tracked_rows)
            if not tracked_df.empty:
                top_user = tracked_df["User"].value_counts().idxmax()

        stats_ph.markdown(textwrap.dedent(f"""
            <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:10px; margin:10px 0 16px 0;">
                <div class="isp-stat-box">
                    <div class="isp-muted">Picks Revealed</div>
                    <div style="font-size:1.6rem; font-weight:800; color:#fff;">{len(revealed_rows)}</div>
                </div>
                <div class="isp-stat-box">
                    <div class="isp-muted">Round 1 Picks</div>
                    <div style="font-size:1.6rem; font-weight:800; color:#fff;">{first_rounders}</div>
                </div>
                <div class="isp-stat-box">
                    <div class="isp-muted">Tracked Picks</div>
                    <div style="font-size:1.6rem; font-weight:800; color:#fff;">{sum(1 for r in revealed_rows if r['Source'] == 'Tracked')}</div>
                </div>
                <div class="isp-stat-box">
                    <div class="isp-muted">Top Pipeline</div>
                    <div style="font-size:1.25rem; font-weight:800; color:#fff;">{html.escape(str(top_user))}</div>
                </div>
            </div>
        """), unsafe_allow_html=True)

        if round_num == 1:
            time.sleep(speeds["r1"])
        elif round_num <= 3:
            time.sleep(speeds["mid"])
        else:
            time.sleep(speeds["late"])

    progress.progress(1.0, text="Draft reveal complete.")
    return df

def normalize_nfl_team_key(team_name):
    slug = get_nfl_logo_slug(team_name)
    if slug:
        return slug
    return str(team_name).strip().lower()

def get_team_qb_block_level(team_name, nfl_roster_df, nfl_draft_hist_df=None, current_draft_year=None):
    team_name = str(team_name).strip()

    qb_room = pd.DataFrame()
    if nfl_roster_df is not None and not nfl_roster_df.empty:
        qb_room = nfl_roster_df[
            (nfl_roster_df["Team"].astype(str).str.strip() == team_name) &
            (nfl_roster_df["Pos"].astype(str).map(clean_bucket) == "QB")
        ].copy()

    if not qb_room.empty:
        qb_room["OVR"] = pd.to_numeric(qb_room["OVR"], errors="coerce").fillna(0)
        qb_room["Age"] = pd.to_numeric(qb_room.get("Age", 25), errors="coerce").fillna(25)

        best_qb_ovr = safe_num(qb_room["OVR"].max(), 0)
        youngest_top_qb_age = safe_num(
            qb_room.sort_values(["OVR", "Age"], ascending=[False, True]).iloc[0]["Age"],
            35
        )

        # Hard franchise QB block
        if best_qb_ovr >= 95 and youngest_top_qb_age <= 35:
            return "hard"
        if best_qb_ovr >= 90 and youngest_top_qb_age <= 32:
            return "hard"
        if best_qb_ovr >= 85 and youngest_top_qb_age <= 30:
            return "hard"
        if best_qb_ovr >= 82 and youngest_top_qb_age <= 28:
            return "medium"

    # Recent draft investment check
    if nfl_draft_hist_df is not None and not nfl_draft_hist_df.empty and current_draft_year is not None:
        hist = nfl_draft_hist_df.copy()
        hist["DraftYear"] = pd.to_numeric(hist["DraftYear"], errors="coerce")
        recent_qbs = hist[
            (hist["GeneratedNFLTeam"].astype(str).str.strip() == team_name) &
            (hist["PosBucket"].astype(str).str.strip() == "QB") &
            (hist["DraftYear"].fillna(-1).astype(int) >= int(current_draft_year) - 2)
        ].copy()

        if not recent_qbs.empty:
            best_recent_round = pd.to_numeric(recent_qbs["DraftRoundCanon"], errors="coerce").fillna(7).min()
            if best_recent_round <= 2:
                return "hard"
            return "medium"

    return "none"

def refresh_nfl_draft_history(live_mode=False, speed_mode="Broadcast", force_latest=False):
    universe = load_nfl_universe_data()
    cfb_draft = universe["cfb_draft"]
    cfb_roster = universe["cfb_roster"]
    base_nfl_roster = universe["nfl_roster"]
    nfl_roster = (
        universe["nfl_current_rosters"].copy()
        if "nfl_current_rosters" in universe
        and universe["nfl_current_rosters"] is not None
        and not universe["nfl_current_rosters"].empty
        else base_nfl_roster.copy()
    )
    existing_hist = universe["nfl_draft_hist"]

    if cfb_draft is None or cfb_draft.empty:
        return existing_hist, None, "No rows found in cfb_user_draft_results.csv."

    work = cfb_draft.copy()
    work["DraftYear"] = pd.to_numeric(work["DraftYear"], errors="coerce")
    work = work.dropna(subset=["DraftYear"]).copy()

    if work.empty:
        return existing_hist, None, "No valid DraftYear values found."

    work["DraftYear"] = work["DraftYear"].astype(int)
    newest_year = int(work["DraftYear"].max())

    if not force_latest:
        existing_years = set()
        if existing_hist is not None and not existing_hist.empty and "DraftYear" in existing_hist.columns:
            existing_years = set(
                pd.to_numeric(existing_hist["DraftYear"], errors="coerce")
                .dropna()
                .astype(int)
                .tolist()
            )
        if newest_year in existing_years:
            return existing_hist, newest_year, f"Draft class {newest_year} is already locked in."

    user_class = work[work["DraftYear"] == newest_year].copy()
    user_class["DraftSource"] = "user_results"
    user_class["TrackStoryline"] = "Yes"

    for col in ["Player", "CollegeTeam", "Pos", "Class"]:
        if col in user_class.columns:
            user_class[col] = user_class[col].fillna("").astype(str).str.strip()

    user_class["CollegeUser"] = (
        user_class.get("CollegeUser", "")
        .fillna("")
        .astype(str)
        .replace("nan", "")
        .str.strip()
    )

    user_class["DraftRound"] = pd.to_numeric(
        user_class.get("DraftRound"), errors="coerce"
    ).fillna(7).astype(int)

    user_class["OVR"] = pd.to_numeric(
        user_class.get("OVR"), errors="coerce"
    ).fillna(0)

    try:
        cpu_pool = pd.read_csv("cpu_draft_pool.csv")
    except Exception:
        cpu_pool = pd.DataFrame()

    if not cpu_pool.empty:
        cpu_pool["DraftYear"] = pd.to_numeric(cpu_pool.get("DraftYear"), errors="coerce")
        cpu_pool = cpu_pool[
            cpu_pool["DraftYear"].fillna(-1).astype(int) == int(newest_year)
        ].copy()

        for col in ["Player", "CollegeTeam", "Pos", "Class"]:
            if col in cpu_pool.columns:
                cpu_pool[col] = cpu_pool[col].fillna("").astype(str).str.strip()

        cpu_pool["CollegeUser"] = ""

        cpu_pool["DraftRound"] = pd.to_numeric(
            cpu_pool.get("DraftRound"), errors="coerce"
        ).fillna(7).astype(int)

        cpu_pool["OVR"] = pd.to_numeric(
            cpu_pool.get("OVR"), errors="coerce"
        ).fillna(0)

        cpu_pool["DraftSource"] = "cpu_pool"
        cpu_pool["TrackStoryline"] = "No"
    else:
        cpu_pool = pd.DataFrame(columns=list(user_class.columns) + ["DraftSource", "TrackStoryline"])

    combined_new_class = pd.concat(
        [user_class, cpu_pool],
        ignore_index=True,
        sort=False
    )

    if combined_new_class.empty:
        return existing_hist, newest_year, f"No draft rows found for class {newest_year}."

    combined_new_class["__player_key"] = combined_new_class.apply(
        lambda r: build_player_id(
            int(safe_num(r.get("DraftYear", newest_year), newest_year)),
            r.get("CollegeTeam", ""),
            r.get("Player", ""),
            r.get("Pos", "")
        ),
        axis=1
    )

    source_priority = {
        "user_results": 0,
        "cpu_pool": 1,
    }
    combined_new_class["__source_rank"] = (
        combined_new_class["DraftSource"].astype(str).map(source_priority).fillna(9)
    )

    combined_new_class = combined_new_class.sort_values(
        ["__player_key", "__source_rank", "DraftRound", "OVR"],
        ascending=[True, True, True, False]
    ).drop_duplicates(subset=["__player_key"], keep="first").copy()

    combined_new_class = combined_new_class.drop(
        columns=["__player_key", "__source_rank"], errors="ignore"
    )

    generated_new = enrich_user_draft_results(combined_new_class, cfb_roster, nfl_roster)

    if generated_new.empty:
        return existing_hist, newest_year, f"Could not generate draft history for class {newest_year}."

    # Build a stable source lookup from the pre-enrichment combined class
    source_meta = combined_new_class.copy()

    source_meta["__source_key"] = source_meta.apply(
        lambda r: "||".join([
            str(int(safe_num(r.get("DraftYear", newest_year), newest_year))),
            normalize_key(clean_display(r.get("CollegeTeam", ""), "")),
            normalize_key(clean_display(r.get("Player", ""), "")),
            normalize_key(clean_display(r.get("Pos", ""), ""))
        ]),
        axis=1
    )

    source_meta = source_meta.sort_values(
        ["DraftSource", "DraftRound", "OVR"],
        ascending=[True, True, False]
    ).drop_duplicates(subset=["__source_key"], keep="first").copy()

    source_lookup = dict(zip(source_meta["__source_key"], source_meta["DraftSource"]))
    storyline_lookup = dict(zip(source_meta["__source_key"], source_meta["TrackStoryline"]))

    generated_new["__source_key"] = generated_new.apply(
        lambda r: "||".join([
            str(int(safe_num(r.get("DraftYear", newest_year), newest_year))),
            normalize_key(clean_display(r.get("CollegeTeam", ""), "")),
            normalize_key(clean_display(r.get("Player", ""), "")),
            normalize_key(clean_display(r.get("Pos", ""), ""))
        ]),
        axis=1
    )

    generated_new["DraftSource"] = generated_new["__source_key"].map(source_lookup)
    generated_new["TrackStoryline"] = generated_new["__source_key"].map(storyline_lookup)

    generated_new["TrackStoryline"] = generated_new["TrackStoryline"].fillna("No")
    generated_new["DraftSource"] = generated_new["DraftSource"].fillna(
        generated_new["TrackStoryline"].astype(str).str.upper().map({
            "YES": "user_results",
            "NO": "cpu_pool"
        })
    ).fillna("cpu_pool")

    generated_new = generated_new.drop(columns=["__source_key"], errors="ignore")

    generated_new["OriginalPick"] = pd.NA
    generated_new["WasTrade"] = "No"
    generated_new["TradeNote"] = ""

    round1_order = build_round1_pick_order(nfl_roster)
    team_needs = build_nfl_team_needs(nfl_roster)

    if team_needs is None or team_needs.empty:
        return existing_hist, newest_year, "Draft rerun stopped: build_nfl_team_needs returned no usable rows."

    r1 = generated_new[generated_new["DraftRoundCanon"] == 1].copy()
    later = generated_new[generated_new["DraftRoundCanon"] != 1].copy()

    assigned_round_rows = []

    # --- ROUND 1 ---
    if not r1.empty:
        r1 = r1.sort_values(["OVR", "DraftValueScore"], ascending=[False, False]).reset_index(drop=True)

        available_order = round1_order.copy()
        used_player_ids = set()

        max_r1 = min(32, len(r1))
        round1_pool = r1.head(max_r1).copy()

        for pick_num in range(1, max_r1 + 1):
            current_team = available_order[0] if available_order else f"Team {pick_num}"
            remaining_players = round1_pool[~round1_pool["PlayerID"].isin(used_player_ids)].copy()

            if remaining_players.empty:
                break

            trade_team, original_pick, was_trade, trade_note = maybe_apply_round1_trade(
                current_pick=pick_num,
                current_team=current_team,
                available_order=available_order,
                remaining_players=remaining_players,
                team_needs=team_needs
            )

            drafting_team = trade_team
            drafting_team_key = normalize_nfl_team_key(drafting_team)

            candidate_rows = []
            for _, cand in remaining_players.iterrows():
                bucket = clean_bucket(cand.get("PosBucket", cand.get("Pos", "")))

                need_row = team_needs[
                    (team_needs["NFLTeam"].astype(str).map(normalize_nfl_team_key) == drafting_team_key) &
                    (team_needs["PosBucket"].astype(str).str.strip() == str(bucket).strip())
                ]

                need_score = safe_num(
                    need_row.iloc[0]["NeedScore"] if not need_row.empty else 0,
                    0
                )

                disqualify_qb = False

                if bucket == "QB":
                    qb_block_level = get_team_qb_block_level(
                        team_name=drafting_team,
                        nfl_roster_df=nfl_roster,
                        nfl_draft_hist_df=existing_hist,
                        current_draft_year=newest_year
                    )

                    if qb_block_level == "hard":
                        disqualify_qb = True
                    elif qb_block_level == "medium":
                        if int(safe_num(cand.get("DraftRoundCanon", 7), 7)) <= 1:
                            disqualify_qb = True

                if disqualify_qb:
                    fit_score = -999999
                else:
                    fit_score = (
                        safe_num(cand.get("DraftValueScore", 0), 0) * 0.72 +
                        safe_num(cand.get("OVR", 0), 0) * 0.18 +
                        need_score * 0.10
                    )

                cand_copy = cand.copy()
                cand_copy["__fit_score"] = fit_score
                candidate_rows.append(cand_copy)

            candidate_df = pd.DataFrame(candidate_rows)
            if candidate_df.empty:
                continue

            candidate_df = candidate_df.sort_values(
                ["__fit_score", "OVR", "DraftValueScore"],
                ascending=[False, False, False]
            )

            row = candidate_df.iloc[0].copy()
            row["GeneratedNFLTeam"] = drafting_team
            row["GeneratedOverallPick"] = pick_num
            row["GeneratedRoundPick"] = pick_num
            row["OriginalPick"] = original_pick if was_trade == "Yes" else pick_num
            row["WasTrade"] = was_trade
            row["TradeNote"] = trade_note

            assigned_round_rows.append(row)
            used_player_ids.add(row["PlayerID"])

            if drafting_team in available_order:
                available_order.remove(drafting_team)

    # --- LATER ROUNDS ---
    later_assigned = []
    if not later.empty:
        later = later.sort_values(
            ["DraftRoundCanon", "OVR", "DraftValueScore"],
            ascending=[True, False, False]
        ).reset_index(drop=True)

        used_player_ids = set(
            [r["PlayerID"] for r in assigned_round_rows if "PlayerID" in r]
        )

        for rnd in sorted(later["DraftRoundCanon"].dropna().unique().tolist()):
            rnd = int(rnd)

            rnd_df_all = later[
                (pd.to_numeric(later["DraftRoundCanon"], errors="coerce").fillna(0).astype(int) == rnd) &
                (~later["PlayerID"].isin(used_player_ids))
            ].copy()

            if rnd_df_all.empty:
                continue

            pick_start = ROUND_START.get(rnd, 0)
            pick_end = ROUND_END.get(rnd, 0)
            round_capacity = max(0, pick_end - pick_start + 1)

            # Guarantee tracked/user players are included in the round pool,
            # but do not auto-force them to the first picks.
            user_round_df = rnd_df_all[
                rnd_df_all["DraftSource"].astype(str).str.strip().str.lower() == "user_results"
            ].copy()

            cpu_round_df = rnd_df_all[
                rnd_df_all["DraftSource"].astype(str).str.strip().str.lower() != "user_results"
            ].copy()

            cpu_round_df = cpu_round_df.sort_values(
                ["OVR", "DraftValueScore", "Player"],
                ascending=[False, False, True]
            ).reset_index(drop=True)

            cpu_needed = max(0, round_capacity - len(user_round_df))
            round_pool = pd.concat(
                [user_round_df, cpu_round_df.head(cpu_needed)],
                ignore_index=True,
                sort=False
            ).drop_duplicates(subset=["PlayerID"], keep="first").copy()

            if round_pool.empty:
                continue

            nfl_team_list = sorted(nfl_roster["Team"].dropna().astype(str).unique().tolist())
            if not nfl_team_list:
                nfl_team_list = round1_order.copy()

            available_order = nfl_team_list.copy()
            round_pick = 1

            for overall_pick in range(
                pick_start,
                min(pick_end, pick_start + len(round_pool) - 1) + 1
            ):
                remaining_players = round_pool[~round_pool["PlayerID"].isin(used_player_ids)].copy()
                if remaining_players.empty:
                    break

                drafting_team = (
                    available_order[0]
                    if available_order
                    else nfl_team_list[(round_pick - 1) % len(nfl_team_list)]
                )

                candidate_rows = []
                for _, cand in remaining_players.iterrows():
                    bucket = clean_bucket(cand.get("PosBucket", cand.get("Pos", "")))
                    drafting_team_key = normalize_nfl_team_key(drafting_team)

                    need_row = team_needs[
                        (team_needs["NFLTeam"].astype(str).map(normalize_nfl_team_key) == drafting_team_key) &
                        (team_needs["PosBucket"].astype(str).str.strip() == str(bucket).strip())
                    ]

                    need_score = safe_num(
                        need_row.iloc[0]["NeedScore"] if not need_row.empty else 0,
                        0
                    )

                    qb_penalty = 0

                    if bucket == "QB":
                        qb_block_level = get_team_qb_block_level(
                            team_name=drafting_team,
                            nfl_roster_df=nfl_roster,
                            nfl_draft_hist_df=existing_hist,
                            current_draft_year=newest_year
                        )

                        if qb_block_level == "hard":
                            qb_penalty = 999
                        elif qb_block_level == "medium":
                            qb_penalty = 25

                    fit_score = (
                        safe_num(cand.get("DraftValueScore", 0), 0) * 0.68 +
                        safe_num(cand.get("OVR", 0), 0) * 0.17 +
                        need_score * 0.15 -
                        qb_penalty
                    )

                    cand_copy = cand.copy()
                    cand_copy["__fit_score"] = fit_score
                    candidate_rows.append(cand_copy)

                candidate_df = pd.DataFrame(candidate_rows)
                if candidate_df.empty:
                    continue

                candidate_df = candidate_df.sort_values(
                    ["__fit_score", "OVR", "DraftValueScore"],
                    ascending=[False, False, False]
                )

                row = candidate_df.iloc[0].copy()
                row["GeneratedNFLTeam"] = drafting_team
                row["GeneratedOverallPick"] = overall_pick
                row["GeneratedRoundPick"] = round_pick
                row["OriginalPick"] = overall_pick
                row["WasTrade"] = "No"
                row["TradeNote"] = ""

                later_assigned.append(row)
                used_player_ids.add(row["PlayerID"])

                if drafting_team in available_order:
                    available_order.remove(drafting_team)

                round_pick += 1
                if not available_order:
                    available_order = nfl_team_list.copy()

    generated_new = pd.DataFrame(assigned_round_rows + later_assigned)

    generated_new = generated_new.sort_values(
        ["DraftYear", "GeneratedOverallPick", "Player"],
        ascending=[True, True, True]
    ).reset_index(drop=True)

    if live_mode:
        generated_new = live_reveal_nfl_draft(generated_new, speed_mode=speed_mode)

    if existing_hist is None or existing_hist.empty:
        combined = generated_new.copy()
    else:
        existing_clean = existing_hist.copy()
        if "DraftYear" in existing_clean.columns:
            existing_clean["DraftYear"] = pd.to_numeric(existing_clean["DraftYear"], errors="coerce")
            existing_clean = existing_clean[
                existing_clean["DraftYear"].fillna(-1).astype(int) != int(newest_year)
            ].copy()

        combined = pd.concat([existing_clean, generated_new], ignore_index=True)

    combined = combined.sort_values(
        ["DraftYear", "GeneratedOverallPick", "Player"],
        ascending=[True, True, True]
    ).reset_index(drop=True)

    for col in NFL_DRAFT_HISTORY_COLS:
        if col not in combined.columns:
            combined[col] = pd.NA
    combined = combined[NFL_DRAFT_HISTORY_COLS].copy()
    combined.to_csv("nfl_draft_history.csv", index=False)

    if force_latest:
        return combined, newest_year, f"Draft class {newest_year} rerun for testing."

    return combined, newest_year, f"Draft class {newest_year} has been officially added to NFL history."


def seed_story_events_from_draft_class(draft_class_df, existing_story_df=None):
    if draft_class_df is None or draft_class_df.empty:
        return existing_story_df if existing_story_df is not None else pd.DataFrame(columns=NFL_STORY_EVENTS_COLS)

    src = draft_class_df.copy()

    if "TrackStoryline" not in src.columns:
        src["TrackStoryline"] = "Yes"

    src = src[src["TrackStoryline"].astype(str).str.upper() == "YES"].copy()

    if src.empty:
        return existing_story_df if existing_story_df is not None else pd.DataFrame(columns=NFL_STORY_EVENTS_COLS)

    src["DraftYear"] = pd.to_numeric(src["DraftYear"], errors="coerce")
    src = src.dropna(subset=["DraftYear"]).copy()

    if src.empty:
        return existing_story_df if existing_story_df is not None else pd.DataFrame(columns=NFL_STORY_EVENTS_COLS)

    src["DraftYear"] = src["DraftYear"].astype(int)
    draft_year = int(src["DraftYear"].max())

    if existing_story_df is None:
        if os.path.exists("nfl_story_events.csv"):
            existing_story_df = pd.read_csv("nfl_story_events.csv")
        else:
            existing_story_df = pd.DataFrame(columns=NFL_STORY_EVENTS_COLS)

    existing_story_df = existing_story_df.copy() if existing_story_df is not None else pd.DataFrame(columns=NFL_STORY_EVENTS_COLS)

    if not existing_story_df.empty and "Season" in existing_story_df.columns:
        existing_story_df["Season"] = pd.to_numeric(existing_story_df["Season"], errors="coerce")
        existing_story_df = existing_story_df[
            ~(
                existing_story_df["Season"].fillna(-1).astype(int).eq(draft_year) &
                existing_story_df["EventType"].astype(str).eq("DraftNight")
            )
        ].copy()

    rows = []
    src = src.sort_values(["GeneratedOverallPick", "Player"], ascending=[True, True])

    for _, r in src.iterrows():
        player = str(r.get("Player", "Unknown Player"))
        nfl_team = str(r.get("GeneratedNFLTeam", "Unknown Team"))
        college_team = str(r.get("CollegeTeam", "Unknown School"))
        round_num = int(safe_num(r.get("DraftRoundCanon", 0), 0))
        pick_num = int(safe_num(r.get("GeneratedOverallPick", 999), 999))
        pos = str(r.get("Pos", ""))
        pos_bucket = str(r.get("PosBucket", ""))
        story_tag = str(r.get("StoryTag", ""))

        rows.append({
            "Season": draft_year,
            "Week": 0,
            "PlayerID": r.get("PlayerID", ""),
            "Player": player,
            "NFLTeam": nfl_team,
            "EventType": "DraftNight",
            "Headline": f"{player} lands with the {nfl_team}",
            "Description": f"{college_team} {pos} ({pos_bucket}) was selected in Round {round_num} at pick {pick_num}. {story_tag}",
            "ImpactScore": int(max(50, 100 - pick_num))
        })

    new_story_df = pd.DataFrame(rows, columns=NFL_STORY_EVENTS_COLS)

    if existing_story_df.empty:
        combined = new_story_df.copy()
    else:
        combined = pd.concat([existing_story_df, new_story_df], ignore_index=True)

    combined = combined.sort_values(["Season", "Week", "ImpactScore"], ascending=[False, True, False]).reset_index(drop=True)
    combined.to_csv("nfl_story_events.csv", index=False)
    return combined

import plotly.graph_objects as go

def render_team_athletic_profile_plotly(team_metric_map):
    """
    team_metric_map example:
    {
        "Florida State": {
            "Players 90+ Speed": 12,
            "Roster Avg Speed": 84.6,
            "Roster Avg Overall": 86.2,
            "Best Player Overall": 97,
            "Players 90+ Overall": 8,
            "Roster Avg Awareness": 81.4,
            "Roster Avg Agility": 83.7,
        },
        "Texas Tech": {
            ...
        }
    }
    """

    if not team_metric_map:
        st.caption("No athletic profile data available.")
        return

    metric_order = [
        "Players 90+ Speed",
        "Roster Avg Speed",
        "Roster Avg Overall",
        "Best Player Overall",
        "Players 90+ Overall",
        "Roster Avg Awareness",
        "Roster Avg Agility",
    ]

    first_team = list(team_metric_map.keys())[0]
    categories = [m for m in metric_order if m in team_metric_map[first_team]]

    if not categories:
        st.caption("No athletic profile metrics available.")
        return

    all_vals = []
    for _, metrics in team_metric_map.items():
        for cat in categories:
            try:
                all_vals.append(float(metrics.get(cat, 0)))
            except Exception:
                pass

    if not all_vals:
        st.caption("No athletic profile values available.")
        return

    min_val = min(all_vals)
    max_val = max(all_vals)

    axis_floor = max(0, int(min_val) - 3)
    axis_ceiling = min(100, int(max_val) + 3) if max_val <= 100 else int(max_val) + 2

    fig = go.Figure()

    for team, metrics in team_metric_map.items():
        team_color = TEAM_VISUALS.get(team, {}).get("primary", "#38bdf8")
        vals = [float(metrics.get(cat, 0)) for cat in categories]

        fig.add_trace(go.Bar(
            y=categories,
            x=vals,
            name=team,
            orientation="h",
            marker=dict(color=team_color),
            text=[f"{v:.1f}" if isinstance(v, float) and not v.is_integer() else f"{int(v)}" for v in vals],
            textposition="outside",
            hovertemplate=f"<b>{team}</b><br>%{{y}}: %{{x}}<extra></extra>"
        ))

    fig.update_layout(
        barmode="group",
        height=520,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        margin=dict(l=20, r=40, t=20, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        ),
        xaxis=dict(
            title="Value",
            range=[axis_floor, axis_ceiling],
            gridcolor="rgba(255,255,255,0.10)",
            zeroline=False
        ),
        yaxis=dict(
            title="",
            autorange="reversed"
        )
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def get_latest_saved_draft_year():
    if not os.path.exists("nfl_draft_history.csv"):
        return None

    try:
        hist = pd.read_csv("nfl_draft_history.csv")
    except Exception:
        return None

    if hist.empty or "DraftYear" not in hist.columns:
        return None

    years = pd.to_numeric(hist["DraftYear"], errors="coerce").dropna()
    if years.empty:
        return None

    return int(years.astype(int).max())


def replay_saved_nfl_draft(draft_year, speed_mode="Broadcast"):
    if not os.path.exists("nfl_draft_history.csv"):
        st.warning("No saved NFL draft history found yet.")
        return

    try:
        hist = pd.read_csv("nfl_draft_history.csv")
    except Exception:
        st.warning("Could not read nfl_draft_history.csv.")
        return

    if hist.empty:
        st.warning("NFL draft history is empty.")
        return

    hist["DraftYear"] = pd.to_numeric(hist["DraftYear"], errors="coerce")
    replay_df = hist[hist["DraftYear"].fillna(-1).astype(int) == int(draft_year)].copy()

    if replay_df.empty:
        st.warning(f"No saved draft results found for {draft_year}.")
        return

    live_reveal_nfl_draft(replay_df, speed_mode=speed_mode)
    
import math

def get_current_nfl_season():
    if not os.path.exists("nfl_universe_settings.csv"):
        initialize_nfl_universe_settings()
        return 2042

    try:
        s = pd.read_csv("nfl_universe_settings.csv")
        if s.empty or "CurrentNFLSeason" not in s.columns:
            initialize_nfl_universe_settings()
            return 2042
        val = pd.to_numeric(s["CurrentNFLSeason"], errors="coerce").dropna()
        return int(val.iloc[0]) if not val.empty else 2042
    except Exception:
        initialize_nfl_universe_settings()
        return 2042


def save_nfl_universe_settings(current_season=None, last_draft_year=None, last_super_bowl_season=None):
    if not os.path.exists("nfl_universe_settings.csv"):
        s = initialize_nfl_universe_settings()
    else:
        try:
            s = pd.read_csv("nfl_universe_settings.csv")
        except Exception:
            s = initialize_nfl_universe_settings()

    if s.empty:
        s = initialize_nfl_universe_settings()

    for col in NFL_UNIVERSE_SETTINGS_COLS:
        if col not in s.columns:
            s[col] = pd.NA

    if current_season is not None:
        s.loc[0, "CurrentNFLSeason"] = int(current_season)
    if last_draft_year is not None:
        s.loc[0, "LastCompletedDraftYear"] = int(last_draft_year)
    if last_super_bowl_season is not None:
        s.loc[0, "LastCompletedSuperBowlSeason"] = int(last_super_bowl_season)

    if pd.isna(s.loc[0, "UniverseVersion"]):
        s.loc[0, "UniverseVersion"] = 1

    s = s[NFL_UNIVERSE_SETTINGS_COLS].copy()
    s.to_csv("nfl_universe_settings.csv", index=False)


def get_latest_completed_draft_year():
    if not os.path.exists("nfl_draft_history.csv"):
        return None
    try:
        df = pd.read_csv("nfl_draft_history.csv")
    except Exception:
        return None
    if df.empty or "DraftYear" not in df.columns:
        return None
    years = pd.to_numeric(df["DraftYear"], errors="coerce").dropna()
    return int(years.max()) if not years.empty else None

def get_nfl_conference(team_name):
    name = str(team_name).strip().lower()

    if not name:
        return ""

    afc_full = {
        "buffalo bills", "miami dolphins", "new england patriots", "new york jets",
        "baltimore ravens", "cincinnati bengals", "cleveland browns", "pittsburgh steelers",
        "houston texans", "indianapolis colts", "jacksonville jaguars", "tennessee titans",
        "denver broncos", "kansas city chiefs", "las vegas raiders", "los angeles chargers"
    }

    nfc_full = {
        "dallas cowboys", "new york giants", "philadelphia eagles", "washington commanders",
        "chicago bears", "detroit lions", "green bay packers", "minnesota vikings",
        "atlanta falcons", "carolina panthers", "new orleans saints", "tampa bay buccaneers",
        "arizona cardinals", "los angeles rams", "san francisco 49ers", "seattle seahawks"
    }

    afc_short = {
        "bills", "dolphins", "patriots", "jets",
        "ravens", "bengals", "browns", "steelers",
        "texans", "colts", "jaguars", "titans",
        "broncos", "chiefs", "raiders", "chargers"
    }

    nfc_short = {
        "cowboys", "giants", "eagles", "commanders",
        "bears", "lions", "packers", "vikings",
        "falcons", "panthers", "saints", "buccaneers", "bucs",
        "cardinals", "rams", "49ers", "seahawks"
    }

    if name in afc_full or name in afc_short:
        return "AFC"
    if name in nfc_full or name in nfc_short:
        return "NFC"

    # fallback contains match for names like "Chicago Bears Team"
    for token in afc_short:
        if token in name:
            return "AFC"
    for token in nfc_short:
        if token in name:
            return "NFC"

    return ""

def build_nfl_team_strengths(nfl_roster_df):
    if nfl_roster_df is None or nfl_roster_df.empty:
        return pd.DataFrame(columns=[
            "Team", "Conference", "OffenseScore", "DefenseScore",
            "QBScore", "StarPower", "DepthScore", "TeamPower"
        ])

    df = nfl_roster_df.copy()

    for col in ["Team", "Pos", "Name"]:
        if col not in df.columns:
            df[col] = ""

    for col in ["OVR", "SPD", "ACC", "AWR", "Age"]:
        if col not in df.columns:
            df[col] = 0

    df["OVR"] = pd.to_numeric(df["OVR"], errors="coerce").fillna(0)
    df["SPD"] = pd.to_numeric(df["SPD"], errors="coerce").fillna(0)
    df["ACC"] = pd.to_numeric(df["ACC"], errors="coerce").fillna(0)
    df["AWR"] = pd.to_numeric(df["AWR"], errors="coerce").fillna(0)
    df["Age"] = pd.to_numeric(df["Age"], errors="coerce").fillna(25)
    df["PosBucket"] = df["Pos"].map(clean_bucket)

    rows = []

    for team in sorted(df["Team"].dropna().astype(str).unique().tolist()):
        team_df = df[df["Team"].astype(str) == str(team)].copy()

        qb_df = team_df[team_df["PosBucket"] == "QB"].sort_values("OVR", ascending=False)
        qb1 = safe_num(qb_df["OVR"].iloc[0], 70) if not qb_df.empty else 70
        qb_score = round(qb1, 2)

        off_buckets = ["QB", "RB", "WR", "TE", "OL"]
        def_buckets = ["EDGE", "IDL", "LB", "CB", "S"]

        offense_df = team_df[team_df["PosBucket"].isin(off_buckets)].copy()
        defense_df = team_df[team_df["PosBucket"].isin(def_buckets)].copy()

        offense_score = round(
            safe_num(offense_df["OVR"].nlargest(10).mean(), 72) * 0.78 +
            safe_num(offense_df["SPD"].nlargest(8).mean(), 72) * 0.10 +
            qb1 * 0.12,
            2
        )

        defense_score = round(
            safe_num(defense_df["OVR"].nlargest(11).mean(), 72) * 0.84 +
            safe_num(defense_df["AWR"].nlargest(8).mean(), 72) * 0.16,
            2
        )

        star_power = int((team_df["OVR"] >= 90).sum())
        depth_score = round(safe_num(team_df["OVR"].nlargest(20).mean(), 72), 2)

        team_power = round(
            offense_score * 0.42 +
            defense_score * 0.40 +
            qb1 * 0.10 +
            depth_score * 0.05 +
            star_power * 0.35,
            2
        )

        rows.append({
            "Team": team,
            "Conference": get_nfl_conference(team),
            "OffenseScore": offense_score,
            "DefenseScore": defense_score,
            "QBScore": qb_score,
            "StarPower": star_power,
            "DepthScore": depth_score,
            "TeamPower": team_power
        })

    return pd.DataFrame(rows)


def simulate_nfl_regular_season(team_strength_df, season_year, games_per_team=17):
    if team_strength_df is None or team_strength_df.empty:
        return pd.DataFrame(columns=[
            "Season", "Team", "Conference", "Wins", "Losses", "WinPct",
            "TeamPower", "OffenseScore", "DefenseScore", "QBScore", "DepthScore", "StarPower", "Seed"
        ])

    teams = team_strength_df["Team"].dropna().astype(str).tolist()
    power_map = dict(zip(team_strength_df["Team"], team_strength_df["TeamPower"]))

    rows = []
    for team in teams:
        opps = [t for t in teams if t != team]
        wins = 0
        losses = 0

        sampled_opps = random.choices(opps, k=games_per_team)
        for opp in sampled_opps:
            team_power = safe_num(power_map.get(team, 75), 75)
            opp_power = safe_num(power_map.get(opp, 75), 75)

            diff = team_power - opp_power
            win_prob = 1 / (1 + math.exp(-(diff / 5.5)))
            win_prob = max(0.12, min(0.88, win_prob + random.uniform(-0.05, 0.05)))

            if random.random() < win_prob:
                wins += 1
            else:
                losses += 1

        row = team_strength_df[team_strength_df["Team"] == team].iloc[0].to_dict()
        row["Season"] = int(season_year)
        row["Wins"] = int(wins)
        row["Losses"] = int(losses)
        row["WinPct"] = round(wins / max(1, wins + losses), 3)
        row["Seed"] = pd.NA
        rows.append(row)

    out = pd.DataFrame(rows)

    if "Conference" not in out.columns:
        out["Conference"] = out["Team"].map(get_nfl_conference)

    out["Conference"] = out["Conference"].astype(str).str.upper().str.strip()

    seeded_frames = []
    for conf in ["AFC", "NFC"]:
        conf_df = out[out["Conference"] == conf].copy()
        if conf_df.empty:
            continue

        conf_df = conf_df.sort_values(
            ["Wins", "TeamPower", "QBScore", "Team"],
            ascending=[False, False, False, True]
        ).reset_index(drop=True)

        conf_df["Seed"] = range(1, len(conf_df) + 1)
        seeded_frames.append(conf_df)

    if seeded_frames:
        out = pd.concat(seeded_frames, ignore_index=True)
    else:
        out = out.sort_values(
            ["Wins", "TeamPower", "QBScore", "Team"],
            ascending=[False, False, False, True]
        ).reset_index(drop=True)
        out["Seed"] = range(1, len(out) + 1)

    wanted_cols = [
        "Season", "Team", "Conference", "Wins", "Losses", "WinPct",
        "TeamPower", "OffenseScore", "DefenseScore", "QBScore", "DepthScore", "StarPower", "Seed"
    ]
    for col in wanted_cols:
        if col not in out.columns:
            out[col] = pd.NA

    out = out[wanted_cols].copy()
    return out


def simulate_playoff_game(team_a, team_b, power_map):
    power_a = safe_num(power_map.get(team_a, 75), 75)
    power_b = safe_num(power_map.get(team_b, 75), 75)

    diff = power_a - power_b
    win_prob_a = 1 / (1 + math.exp(-(diff / 4.8)))
    win_prob_a = max(0.10, min(0.90, win_prob_a + random.uniform(-0.03, 0.03)))

    winner = team_a if random.random() < win_prob_a else team_b
    loser = team_b if winner == team_a else team_a

    base_w = random.randint(20, 34)
    base_l = random.randint(13, 30)
    if base_l >= base_w:
        base_l = max(10, base_w - random.randint(1, 9))

    score = f"{winner} {base_w}, {loser} {base_l}"
    return winner, loser, score


def simulate_nfl_playoffs(standings_df, season_year):
    if standings_df is None or standings_df.empty:
        return None, None, None, pd.DataFrame(columns=NFL_PLAYOFF_HISTORY_COLS)

    work = standings_df.copy()
    if "Conference" not in work.columns:
        return None, None, None, pd.DataFrame(columns=NFL_PLAYOFF_HISTORY_COLS)

    work["Wins"] = pd.to_numeric(work["Wins"], errors="coerce").fillna(0)
    work["TeamPower"] = pd.to_numeric(work["TeamPower"], errors="coerce").fillna(0)

    playoff_rows = []

    def simulate_game(team_a_row, team_b_row, round_name):
        team_a = str(team_a_row["Team"])
        team_b = str(team_b_row["Team"])

        power_a = safe_num(team_a_row.get("TeamPower", 75), 75)
        power_b = safe_num(team_b_row.get("TeamPower", 75), 75)

        score_a = int(round(random.gauss(21 + (power_a - 75) * 0.35, 6)))
        score_b = int(round(random.gauss(21 + (power_b - 75) * 0.35, 6)))

        score_a = max(10, score_a)
        score_b = max(10, score_b)

        if score_a == score_b:
            if power_a >= power_b:
                score_a += 3
            else:
                score_b += 3

        if score_a > score_b:
            winner, loser = team_a, team_b
            winner_row = team_a_row
        else:
            winner, loser = team_b, team_a
            winner_row = team_b_row

        playoff_rows.append({
            "Season": int(season_year),
            "Round": round_name,
            "Winner": winner,
            "Loser": loser,
            "Score": f"{max(score_a, score_b)}-{min(score_a, score_b)}"
        })

        return winner_row

    def run_conference_bracket(conf_df):
        conf_df = conf_df.sort_values(
            ["Wins", "TeamPower", "Team"],
            ascending=[False, False, True]
        ).head(7).copy().reset_index(drop=True)

        if len(conf_df) < 7:
            return None

        conf_df["Seed"] = range(1, len(conf_df) + 1)
        seed_map = {int(r["Seed"]): r for _, r in conf_df.iterrows()}

        wc1_winner = simulate_game(seed_map[2], seed_map[7], "Wild Card")
        wc2_winner = simulate_game(seed_map[3], seed_map[6], "Wild Card")
        wc3_winner = simulate_game(seed_map[4], seed_map[5], "Wild Card")

        winners = [wc1_winner, wc2_winner, wc3_winner]
        winners = sorted(winners, key=lambda r: int(r["Seed"]))

        div1_winner = simulate_game(seed_map[1], winners[-1], "Divisional")
        div2_winner = simulate_game(winners[0], winners[1], "Divisional")

        conf_winner = simulate_game(div1_winner, div2_winner, "Conference Championship")
        return conf_winner

    work["Conference"] = work["Conference"].astype(str).str.upper().str.strip()

    afc_df = work[work["Conference"] == "AFC"].copy()
    nfc_df = work[work["Conference"] == "NFC"].copy()

    if afc_df.empty or nfc_df.empty:
        print("PLAYOFF CONF ERROR:", work[["Team", "Conference"]].to_dict("records"))
        return None, None, None, pd.DataFrame(columns=NFL_PLAYOFF_HISTORY_COLS)

    if afc_df.empty or nfc_df.empty:
        return None, None, None, pd.DataFrame(columns=NFL_PLAYOFF_HISTORY_COLS)

    afc_champ = run_conference_bracket(afc_df)
    nfc_champ = run_conference_bracket(nfc_df)

    if afc_champ is None or nfc_champ is None:
        return None, None, None, pd.DataFrame(columns=NFL_PLAYOFF_HISTORY_COLS)

    super_bowl_winner = simulate_game(afc_champ, nfc_champ, "Super Bowl")
    champion = str(super_bowl_winner["Team"])

    if champion == str(afc_champ["Team"]):
        runner_up = str(nfc_champ["Team"])
    else:
        runner_up = str(afc_champ["Team"])

    playoff_df = pd.DataFrame(playoff_rows, columns=NFL_PLAYOFF_HISTORY_COLS)
    sb_row = playoff_df[playoff_df["Round"] == "Super Bowl"].tail(1)
    score = sb_row.iloc[0]["Score"] if not sb_row.empty else ""

    return champion, runner_up, score, playoff_df


def choose_super_bowl_mvp(champion, player_season_rows):
    if player_season_rows is None or player_season_rows.empty:
        return "Team MVP", champion

    team_df = player_season_rows[player_season_rows["NFLTeam"].astype(str) == str(champion)].copy()
    if team_df.empty:
        return "Team MVP", champion

    team_df["CareerValue"] = pd.to_numeric(team_df["CareerValue"], errors="coerce").fillna(0)
    team_df = team_df.sort_values(["CareerValue", "OverallEnd"], ascending=[False, False])

    top = team_df.iloc[0]
    return str(top.get("Player", "Team MVP")), champion

def calc_nfl_progression_delta(age, years_pro, rookie_role, career_tier, pro_outcome, development_curve):
    age = int(safe_num(age, 23))
    years_pro = int(safe_num(years_pro, 1))
    rookie_role = str(rookie_role).strip()
    career_tier = str(career_tier).strip()
    pro_outcome = str(pro_outcome).strip()
    development_curve = str(development_curve).strip()

    delta = 0.0

    # Age curve
    if age <= 22:
        delta += random.uniform(1.5, 4.0)
    elif age <= 24:
        delta += random.uniform(1.0, 3.0)
    elif age <= 27:
        delta += random.uniform(0.0, 1.5)
    elif age <= 29:
        delta += random.uniform(-0.5, 0.8)
    elif age <= 31:
        delta += random.uniform(-1.5, 0.2)
    else:
        delta += random.uniform(-3.0, -0.5)

    # Development path
    if development_curve == "Fast Rise":
        if years_pro <= 3:
            delta += random.uniform(1.0, 2.5)
    elif development_curve == "Steady Rise":
        if years_pro <= 4:
            delta += random.uniform(0.5, 1.5)
    elif development_curve == "Slow Burn":
        if years_pro <= 2:
            delta += random.uniform(-1.0, 0.5)
        elif years_pro <= 5:
            delta += random.uniform(0.5, 2.0)
    elif development_curve == "Flat":
        delta += random.uniform(-1.0, 0.5)

    # Outcome influence
    if pro_outcome == "Superstar":
        delta += random.uniform(0.8, 2.0)
    elif pro_outcome == "Star":
        delta += random.uniform(0.4, 1.4)
    elif pro_outcome == "Impact Starter":
        delta += random.uniform(0.1, 1.0)
    elif pro_outcome == "Steady Starter":
        delta += random.uniform(-0.2, 0.8)
    elif pro_outcome == "Developmental":
        delta += random.uniform(-0.5, 1.0)
    elif pro_outcome == "Bust":
        delta += random.uniform(-2.2, -0.2)

    # Role / tier nudges
    if rookie_role in {"Day 1 Starter", "Featured Rookie"}:
        delta += random.uniform(0.2, 1.0)
    elif rookie_role in {"Depth Piece", "Bench Development"}:
        delta += random.uniform(-0.4, 0.3)

    if career_tier == "Superstar":
        delta += random.uniform(0.4, 1.0)
    elif career_tier == "Star":
        delta += random.uniform(0.2, 0.8)
    elif career_tier == "Depth":
        delta += random.uniform(-0.5, 0.2)

    return round(delta, 2)

def should_retire_nfl_player(age, overall_end, pro_outcome, pos_bucket):
    age = int(safe_num(age, 30))
    overall_end = int(safe_num(overall_end, 75))
    pro_outcome = str(pro_outcome).strip()
    pos_bucket = str(pos_bucket).strip().upper()

    if age >= 38:
        return True

    if age >= 36:
        if pos_bucket == "QB" and pro_outcome in {"Superstar", "Star"} and overall_end >= 84:
            return random.random() < 0.35
        return random.random() < 0.75

    if age >= 34:
        if pos_bucket == "QB" and pro_outcome in {"Superstar", "Star"} and overall_end >= 86:
            return random.random() < 0.18
        if overall_end < 80:
            return random.random() < 0.50
        return random.random() < 0.28

    if age >= 32:
        if overall_end < 74 and pro_outcome in {"Bust", "Developmental"}:
            return random.random() < 0.30
        if pos_bucket in {"RB", "LB", "EDGE", "IDL"} and overall_end < 78:
            return random.random() < 0.18

    return False


def determine_nfl_player_status(age, years_pro, overall_end, pro_outcome, pos_bucket):
    age = int(safe_num(age, 30))
    years_pro = int(safe_num(years_pro, 1))
    overall_end = int(safe_num(overall_end, 75))
    pro_outcome = str(pro_outcome).strip()
    pos_bucket = str(pos_bucket).strip().upper()

    # Out of league / washout logic
    if pro_outcome == "Bust" and years_pro >= 4 and overall_end <= 71 and random.random() < 0.45:
        return "Out of League"

    if pro_outcome in {"Bust", "Developmental"} and years_pro >= 6 and overall_end <= 69 and random.random() < 0.55:
        return "Out of League"

    if should_retire_nfl_player(age, overall_end, pro_outcome, pos_bucket):
        return "Retired"

    if age >= 33 and pro_outcome not in {"Superstar", "Star"} and random.random() < 0.30:
        return "Declining"

    if pro_outcome == "Bust" and years_pro >= 3 and overall_end < 74 and random.random() < 0.35:
        return "Fringe"

    return "Active"

def simulate_nfl_player_season(season_year, nfl_draft_hist_df=None, nfl_roster_df=None, existing_player_hist_df=None):
    if nfl_draft_hist_df is None:
        nfl_draft_hist_df = pd.read_csv("nfl_draft_history.csv") if os.path.exists("nfl_draft_history.csv") else pd.DataFrame()

    if nfl_roster_df is None:
        nfl_roster_df = pd.read_csv("NFLroster26_MASTER.csv") if os.path.exists("NFLroster26_MASTER.csv") else pd.DataFrame()

    if existing_player_hist_df is None:
        existing_player_hist_df = pd.read_csv("nfl_player_history.csv") if os.path.exists("nfl_player_history.csv") else pd.DataFrame(columns=NFL_PLAYER_HISTORY_COLS)

    if nfl_draft_hist_df is None or nfl_draft_hist_df.empty:
        return existing_player_hist_df if existing_player_hist_df is not None else pd.DataFrame(columns=NFL_PLAYER_HISTORY_COLS)

    draft_df = nfl_draft_hist_df.copy()
    draft_df["DraftYear"] = pd.to_numeric(draft_df["DraftYear"], errors="coerce")
    draft_df = draft_df.dropna(subset=["DraftYear"]).copy()
    if draft_df.empty:
        return existing_player_hist_df

    draft_df["DraftYear"] = draft_df["DraftYear"].astype(int)
    eligible_players = draft_df[draft_df["DraftYear"] <= int(season_year)].copy()
    if eligible_players.empty:
        return existing_player_hist_df

    latest_status_map = {}
    if existing_player_hist_df is not None and not existing_player_hist_df.empty:
        hist_tmp = existing_player_hist_df.copy()
        if "Season" in hist_tmp.columns:
            hist_tmp["Season"] = pd.to_numeric(hist_tmp["Season"], errors="coerce")
            hist_tmp = hist_tmp.sort_values(["PlayerID", "Season"])
            latest_hist = hist_tmp.dropna(subset=["PlayerID"]).drop_duplicates(subset=["PlayerID"], keep="last")
            latest_status_map = dict(
                zip(
                    latest_hist["PlayerID"].astype(str),
                    latest_hist["Status"].astype(str)
                )
            )

    rows = []
    for _, r in eligible_players.iterrows():
        draft_year = int(safe_num(r.get("DraftYear", season_year), season_year))
        years_pro = max(1, int(season_year) - draft_year + 1)

        player = str(r.get("Player", "Unknown Player"))
        player_id = str(r.get("PlayerID", ""))
        prior_status = str(latest_status_map.get(player_id, "")).strip()

        if prior_status in {"Retired", "Out of League"}:
            continue

        nfl_team = str(r.get("GeneratedNFLTeam", "Unknown Team"))
        pos = str(r.get("Pos", ""))
        bucket = str(r.get("PosBucket", clean_bucket(pos)))
        rookie_role = str(r.get("RookieRole", "Depth Piece"))
        career_tier = str(r.get("CareerTier", "Starter"))
        pro_outcome = str(r.get("ProOutcome", "Steady Starter")).strip()
        development_curve = str(r.get("DevelopmentCurve", "Normal")).strip()

        rookie_entry_ovr = int(safe_num(r.get("OVR", 75), 75))
        peak_ovr = int(safe_num(r.get("PeakOVR", rookie_entry_ovr + 3), rookie_entry_ovr + 3))
        round_num = int(safe_num(r.get("DraftRoundCanon", 7), 7))

        age = 21 + years_pro

        overall_start = rookie_entry_ovr
        if years_pro > 1:
            prior_rows = existing_player_hist_df[
                existing_player_hist_df["PlayerID"].astype(str) == str(player_id)
            ].copy() if existing_player_hist_df is not None and not existing_player_hist_df.empty else pd.DataFrame()

            if not prior_rows.empty and "Season" in prior_rows.columns:
                prior_rows["Season"] = pd.to_numeric(prior_rows["Season"], errors="coerce")
                prior_rows = prior_rows[
                    prior_rows["Season"].fillna(-1).astype(int) < int(season_year)
                ].sort_values("Season")

                if not prior_rows.empty:
                    overall_start = int(safe_num(prior_rows.iloc[-1].get("OverallEnd", rookie_entry_ovr), rookie_entry_ovr))

        progression_delta = calc_nfl_progression_delta(
            age=age,
            years_pro=years_pro,
            rookie_role=rookie_role,
            career_tier=career_tier,
            pro_outcome=pro_outcome,
            development_curve=development_curve
        )

        overall_end = int(round(overall_start + progression_delta))
        overall_end = max(62, min(peak_ovr, overall_end))

        if years_pro == 1:
            role = rookie_role
        else:
            if pro_outcome in {"Superstar", "Star", "Impact Starter"}:
                role = "Starter"
            elif pro_outcome in {"Steady Starter", "Developmental"}:
                role = "Rotation"
            else:
                role = "Depth"

        games = random.randint(11, 17)
        starts = 0
        if role in {"Starter", "QB Battle"}:
            starts = random.randint(8, 17)
        elif role in {"WR3", "CB3", "RB2", "TE2", "Starter Battle", "Primary Rotation", "Pass Rush Rotation", "DL Rotation", "LB Rotation", "DB Rotation", "Committee Back", "Rotation"}:
            starts = random.randint(1, 9)
        else:
            starts = random.randint(0, 4)

        stat_line = ""
        if bucket == "QB":
            pass_yds = int(300 + overall_end * 32 + starts * 55 + random.randint(-250, 350))
            pass_tds = max(1, int(pass_yds / 180) + random.randint(-2, 4))
            stat_line = f"{pass_yds} pass yds, {pass_tds} pass TD"
        elif bucket == "RB":
            rush_yds = int(120 + overall_end * 9 + games * 14 + random.randint(-120, 180))
            rush_tds = max(0, int(rush_yds / 140) + random.randint(-1, 3))
            stat_line = f"{rush_yds} rush yds, {rush_tds} rush TD"
        elif bucket == "WR":
            rec_yds = int(150 + overall_end * 11 + games * 18 + random.randint(-150, 220))
            rec_tds = max(0, int(rec_yds / 170) + random.randint(-1, 3))
            stat_line = f"{rec_yds} rec yds, {rec_tds} rec TD"
        elif bucket == "TE":
            rec_yds = int(100 + overall_end * 8 + games * 10 + random.randint(-90, 150))
            rec_tds = max(0, int(rec_yds / 190) + random.randint(-1, 2))
            stat_line = f"{rec_yds} rec yds, {rec_tds} rec TD"
        elif bucket in {"EDGE", "IDL", "LB"}:
            sacks = max(0, int((overall_end - 70) / 4) + random.randint(-2, 3))
            tackles = int(22 + games * 2.4 + starts * 1.1 + random.randint(-10, 18))
            stat_line = f"{tackles} tackles, {sacks} sacks"
        elif bucket in {"CB", "S"}:
            ints = max(0, int((overall_end - 72) / 7) + random.randint(-1, 3))
            tackles = int(18 + games * 2.1 + starts * 1.0 + random.randint(-8, 15))
            stat_line = f"{tackles} tackles, {ints} INT"
        else:
            stat_line = f"{games} games, {starts} starts"

        pro_bowl = "Yes" if overall_end >= 90 and pro_outcome in {"Superstar", "Star", "Impact Starter"} and random.random() < 0.55 else "No"
        all_pro = "Yes" if overall_end >= 93 and pro_outcome in {"Superstar", "Star"} and random.random() < 0.28 else "No"
        mvp_votes = int(random.randint(1, 10)) if bucket == "QB" and overall_end >= 92 and pro_outcome in {"Superstar", "Star"} and random.random() < 0.22 else 0

        career_value = round(
            overall_end * 0.45 +
            starts * 1.25 +
            years_pro * 1.75 +
            (8 if pro_bowl == "Yes" else 0) +
            (10 if all_pro == "Yes" else 0) +
            (mvp_votes * 1.5),
            1
        )

        status = determine_nfl_player_status(
            age=age,
            years_pro=years_pro,
            overall_end=overall_end,
            pro_outcome=pro_outcome,
            pos_bucket=bucket
        )

        rows.append({
            "Season": int(season_year),
            "PlayerID": player_id,
            "Player": player,
            "NFLTeam": nfl_team,
            "Pos": pos,
            "PosBucket": bucket,
            "Age": int(age),
            "Role": role,
            "OverallStart": int(overall_start),
            "OverallEnd": int(overall_end),
            "PeakOVR": int(peak_ovr),
            "ProOutcome": pro_outcome,
            "DevelopmentCurve": development_curve,
            "Games": int(games),
            "Starts": int(starts),
            "StatLine": stat_line,
            "ProBowl": pro_bowl,
            "AllPro": all_pro,
            "MVPVotes": int(mvp_votes),
            "SuperBowlWin": "No",
            "SuperBowlAppear": "No",
            "CareerValue": career_value,
            "Status": status
        })

    new_df = pd.DataFrame(rows, columns=NFL_PLAYER_HISTORY_COLS)

    existing_clean = existing_player_hist_df.copy() if existing_player_hist_df is not None else pd.DataFrame(columns=NFL_PLAYER_HISTORY_COLS)
    if not existing_clean.empty and "Season" in existing_clean.columns:
        existing_clean["Season"] = pd.to_numeric(existing_clean["Season"], errors="coerce")
        existing_clean = existing_clean[existing_clean["Season"].fillna(-1).astype(int) != int(season_year)].copy()

    combined = pd.concat([existing_clean, new_df], ignore_index=True)
    for col in NFL_PLAYER_HISTORY_COLS:
        if col not in combined.columns:
            combined[col] = pd.NA
    combined = combined[NFL_PLAYER_HISTORY_COLS].copy()
    combined.to_csv("nfl_player_history.csv", index=False)
    return combined

NFL_POSITION_ROOM_TARGETS = {
    "QB": 3,
    "RB": 4,
    "WR": 6,
    "TE": 3,
    "OL": 9,
    "EDGE": 4,
    "IDL": 4,
    "LB": 5,
    "CB": 5,
    "S": 4
}


def get_free_agent_fill_ovr(team_strength, pos_bucket):
    team_strength = safe_num(team_strength, 78)
    pos_bucket = str(pos_bucket).strip().upper()

    base = 68
    if team_strength >= 90:
        base = 74
    elif team_strength >= 85:
        base = 72
    elif team_strength >= 80:
        base = 70
    elif team_strength >= 75:
        base = 68
    else:
        base = 66

    pos_bonus = {
        "QB": 2,
        "OL": 1,
        "EDGE": 1,
        "CB": 1
    }.get(pos_bucket, 0)

    return int(max(60, min(79, round(base + pos_bonus + random.uniform(-2, 2)))))

def calc_udfa_entry_ovr(cfb_ovr, pos_bucket=""):
    cfb_ovr = safe_num(cfb_ovr, 78)
    pos_bucket = str(pos_bucket).strip().upper()

    if cfb_ovr >= 92:
        nfl_ovr = random.randint(72, 76)
    elif cfb_ovr >= 88:
        nfl_ovr = random.randint(69, 74)
    elif cfb_ovr >= 84:
        nfl_ovr = random.randint(66, 72)
    elif cfb_ovr >= 80:
        nfl_ovr = random.randint(64, 69)
    else:
        nfl_ovr = random.randint(60, 66)

    if pos_bucket == "QB":
        nfl_ovr -= 1
    elif pos_bucket in {"RB", "WR", "CB", "S"}:
        nfl_ovr += 1

    return int(max(58, min(76, nfl_ovr)))
    
def assign_udfa_hidden_traits(cfb_ovr, pos_bucket="", awr=75, spd=75, age=22):
    cfb_ovr = safe_num(cfb_ovr, 78)
    awr = safe_num(awr, 75)
    spd = safe_num(spd, 75)
    age = safe_num(age, 22)
    pos_bucket = str(pos_bucket).strip().upper()

    score = 0.0
    score += (cfb_ovr - 78) * 1.0
    score += (awr - 75) * 0.45
    score += (spd - 75) * 0.20

    if pos_bucket == "QB":
        score += random.uniform(-8, 6)
    elif pos_bucket in {"WR", "CB", "EDGE"}:
        score += random.uniform(-7, 6)
    else:
        score += random.uniform(-6, 5)

    if age <= 21:
        score += random.uniform(-2, 3)
    elif age >= 24:
        score += random.uniform(-1, 1)

    if score >= 24:
        return "Star", "Fast Rise"
    elif score >= 17:
        return "Impact Starter", "Steady Rise"
    elif score >= 10:
        return "Steady Starter", "Normal"
    elif score >= 4:
        return "Developmental", "Slow Burn"
    else:
        return "Bust", "Flat"

def build_udfa_pool_for_season(season_year, cfb_roster_df, nfl_draft_hist_df):
    season_year = int(season_year)

    drafted_ids = set()
    if nfl_draft_hist_df is not None and not nfl_draft_hist_df.empty and "PlayerID" in nfl_draft_hist_df.columns:
        drafted_ids = set(
            nfl_draft_hist_df["PlayerID"].dropna().astype(str).tolist()
        )

    udfa_frames = []

    # ------------------------------------------------------------
    # SOURCE 1: cpu_draft_pool.csv players from previous class who were not drafted
    # ------------------------------------------------------------
    try:
        cpu_pool = pd.read_csv("cpu_draft_pool.csv")
    except Exception:
        cpu_pool = pd.DataFrame()

    if not cpu_pool.empty:
        cpu_pool["DraftYear"] = pd.to_numeric(cpu_pool.get("DraftYear"), errors="coerce")
        cpu_pool = cpu_pool[
            cpu_pool["DraftYear"].fillna(-1).astype(int) == int(season_year - 1)
        ].copy()

        for col in ["Player", "CollegeTeam", "CollegeUser", "Pos", "Class"]:
            if col not in cpu_pool.columns:
                cpu_pool[col] = ""
            cpu_pool[col] = cpu_pool[col].fillna("").astype(str).str.strip()

        for col in ["OVR", "AWR", "SPD", "Age"]:
            if col not in cpu_pool.columns:
                cpu_pool[col] = 0
            cpu_pool[col] = pd.to_numeric(cpu_pool[col], errors="coerce").fillna(0)

        cpu_pool["PosBucket"] = cpu_pool["Pos"].map(clean_bucket)
        cpu_pool["PlayerID"] = cpu_pool.apply(
            lambda r: build_player_id(
                int(safe_num(r.get("DraftYear", season_year - 1), season_year - 1)),
                r.get("CollegeTeam", ""),
                r.get("Player", ""),
                r.get("Pos", "")
            ),
            axis=1
        )

        cpu_udfa = cpu_pool[~cpu_pool["PlayerID"].astype(str).isin(drafted_ids)].copy()
        if not cpu_udfa.empty:
            cpu_udfa["CollegeUser"] = (
                cpu_udfa.get("CollegeUser", "")
                .fillna("")
                .astype(str)
                .replace(["nan", "None", "none", "<NA>"], "")
                .str.strip()
            )
            cpu_udfa["NFLUdfaOVR"] = cpu_udfa.apply(
                lambda r: calc_udfa_entry_ovr(
                    cfb_ovr=safe_num(r.get("OVR", 75), 75),
                    pos_bucket=r.get("PosBucket", "")
                ),
                axis=1
            )

            cpu_traits = cpu_udfa.apply(
                lambda r: assign_udfa_hidden_traits(
                    cfb_ovr=safe_num(r.get("OVR", 75), 75),
                    pos_bucket=r.get("PosBucket", ""),
                    awr=safe_num(r.get("AWR", 75), 75),
                    spd=safe_num(r.get("SPD", 75), 75),
                    age=safe_num(r.get("Age", 22), 22)
                ),
                axis=1
            )

            cpu_udfa["ProOutcome"] = cpu_traits.map(lambda x: x[0] if isinstance(x, tuple) else "Developmental")
            cpu_udfa["DevelopmentCurve"] = cpu_traits.map(lambda x: x[1] if isinstance(x, tuple) else "Slow Burn")
            cpu_udfa["PeakOVR"] = cpu_udfa.apply(
                lambda r: estimate_peak_ovr_from_outcome(
                    rookie_ovr=safe_num(r.get("NFLUdfaOVR", 66), 66),
                    pro_outcome=r.get("ProOutcome", "Developmental")
                ),
                axis=1
            )

            udfa_frames.append(cpu_udfa)

    # ------------------------------------------------------------
    # SOURCE 2: cfb26_rosters_full.csv seniors / RS seniors not drafted
    # ------------------------------------------------------------
    if cfb_roster_df is not None and not cfb_roster_df.empty:
        roster = cfb_roster_df.copy()

        if "Name" not in roster.columns:
            roster["Name"] = ""
        if "Team" not in roster.columns:
            roster["Team"] = ""
        if "Pos" not in roster.columns:
            roster["Pos"] = ""
        if "Year" not in roster.columns:
            roster["Year"] = ""
        if "OVR" not in roster.columns:
            roster["OVR"] = 0
        if "AWR" not in roster.columns:
            roster["AWR"] = 75
        if "SPD" not in roster.columns:
            roster["SPD"] = 75
        if "Age" not in roster.columns:
            roster["Age"] = 22
        if "User" not in roster.columns:
            roster["User"] = ""

        for col in ["Name", "Team", "Pos", "Year", "User"]:
            roster[col] = roster[col].fillna("").astype(str).str.strip()

        for col in ["OVR", "AWR", "SPD", "Age"]:
            roster[col] = pd.to_numeric(roster[col], errors="coerce").fillna(0)

        roster = roster[
            roster["Year"].astype(str).isin({"SR", "RS SR"})
        ].copy()

        roster = roster[
            (roster["Name"].astype(str).str.strip() != "") &
            (roster["Team"].astype(str).str.strip() != "") &
            (roster["Pos"].astype(str).str.strip() != "")
        ].copy()

        if not roster.empty:
            roster["Player"] = roster["Name"]
            roster["CollegeTeam"] = roster["Team"]
            roster["CollegeUser"] = (
                roster.get("User", "")
                .fillna("")
                .astype(str)
                .replace(["nan", "None", "none", "<NA>"], "")
                .str.strip()
            )
            roster["PosBucket"] = roster["Pos"].map(clean_bucket)
            roster["DraftYear"] = int(season_year - 1)
            roster["Class"] = roster["Year"]

            roster["PlayerID"] = roster.apply(
                lambda r: build_player_id(
                    int(season_year - 1),
                    r.get("CollegeTeam", ""),
                    r.get("Player", ""),
                    r.get("Pos", "")
                ),
                axis=1
            )

            roster_udfa = roster[~roster["PlayerID"].astype(str).isin(drafted_ids)].copy()
            if not roster_udfa.empty:
                roster_udfa["NFLUdfaOVR"] = roster_udfa.apply(
                    lambda r: calc_udfa_entry_ovr(
                        cfb_ovr=safe_num(r.get("OVR", 75), 75),
                        pos_bucket=r.get("PosBucket", "")
                    ),
                    axis=1
                )

                roster_traits = roster_udfa.apply(
                    lambda r: assign_udfa_hidden_traits(
                        cfb_ovr=safe_num(r.get("OVR", 75), 75),
                        pos_bucket=r.get("PosBucket", ""),
                        awr=safe_num(r.get("AWR", 75), 75),
                        spd=safe_num(r.get("SPD", 75), 75),
                        age=safe_num(r.get("Age", 22), 22)
                    ),
                    axis=1
                )

                roster_udfa["ProOutcome"] = roster_traits.map(lambda x: x[0] if isinstance(x, tuple) else "Developmental")
                roster_udfa["DevelopmentCurve"] = roster_traits.map(lambda x: x[1] if isinstance(x, tuple) else "Slow Burn")
                roster_udfa["PeakOVR"] = roster_udfa.apply(
                    lambda r: estimate_peak_ovr_from_outcome(
                        rookie_ovr=safe_num(r.get("NFLUdfaOVR", 66), 66),
                        pro_outcome=r.get("ProOutcome", "Developmental")
                    ),
                    axis=1
                )

                udfa_frames.append(roster_udfa)

    if not udfa_frames:
        return pd.DataFrame()

    udfa_df = pd.concat(udfa_frames, ignore_index=True, sort=False)

    # De-dupe by PlayerID, keeping stronger NFL UDFA entry value
    udfa_df = udfa_df.sort_values(
        ["PlayerID", "NFLUdfaOVR", "OVR", "Player"],
        ascending=[True, False, False, True]
    ).drop_duplicates(subset=["PlayerID"], keep="first").copy()

    udfa_df = udfa_df.sort_values(
        ["NFLUdfaOVR", "OVR", "Player"],
        ascending=[False, False, True]
    ).reset_index(drop=True)

    return udfa_df

NFL_FA_FIRST_NAMES = [
    "Marcus", "Darius", "Trevor", "Jalen", "Malik", "Andre", "Tyler", "Jordan",
    "Chris", "Brandon", "Devin", "Xavier", "Tyrone", "Noah", "Javon", "Kendall",
    "Isaiah", "Cameron", "Micah", "Elijah", "Rashad", "Trey", "Avery", "Donovan"
]

NFL_FA_LAST_NAMES = [
    "Hawkins", "Morrison", "Daniels", "Bennett", "Carter", "Wallace", "Holmes", "Bryant",
    "Foster", "Shelton", "Greene", "Patterson", "Mason", "Reed", "Porter", "Banks",
    "Vaughn", "Collins", "Hayes", "Murray", "Sutton", "Webb", "Barber", "Gibson"
]

def generate_nfl_free_agent_name(used_names=None):
    used_names = used_names or set()

    for _ in range(100):
        full_name = f"{random.choice(NFL_FA_FIRST_NAMES)} {random.choice(NFL_FA_LAST_NAMES)}"
        if full_name.strip().lower() not in used_names:
            return full_name

    return f"Free Agent {random.randint(100, 999)}"

def run_nfl_offseason_roster_maintenance(season_year, current_roster_df, cfb_roster_df=None, nfl_draft_hist_df=None):
    season_year = int(season_year)

    if current_roster_df is None or current_roster_df.empty:
        return pd.DataFrame(columns=NFL_CURRENT_ROSTER_COLS)

    work = current_roster_df.copy()
    for col in NFL_CURRENT_ROSTER_COLS:
        if col not in work.columns:
            work[col] = pd.NA

    work["OVR"] = pd.to_numeric(work["OVR"], errors="coerce").fillna(70)
    work["Age"] = pd.to_numeric(work["Age"], errors="coerce").fillna(25)
    work["Status"] = work["Status"].fillna("Active").astype(str)

    # Keep only roster-eligible players
    work = work[~work["Status"].isin(["Retired", "Out of League"])].copy()

    fill_rows = []

    team_strength_map = {}
    if not work.empty:
        tmp_strength = build_nfl_team_strengths(work)
        if not tmp_strength.empty:
            team_strength_map = dict(
                zip(
                    tmp_strength["Team"].astype(str),
                    pd.to_numeric(tmp_strength["TeamPower"], errors="coerce").fillna(78)
                )
            )

    udfa_pool = build_udfa_pool_for_season(
        season_year=season_year,
        cfb_roster_df=cfb_roster_df,
        nfl_draft_hist_df=nfl_draft_hist_df
    )

    udfa_used_ids = set()

    for team in sorted(work["Team"].dropna().astype(str).unique().tolist()):
        team_df = work[work["Team"].astype(str) == str(team)].copy()

        for pos_bucket, target_count in NFL_POSITION_ROOM_TARGETS.items():
            room = team_df[team_df["PosBucket"].astype(str) == str(pos_bucket)].copy()
            needed = max(0, int(target_count) - len(room))

            if needed <= 0:
                continue

            team_strength = safe_num(team_strength_map.get(team, 78), 78)

            # 1) Fill from UDFAs first
            if udfa_pool is not None and not udfa_pool.empty:
                udfa_room = udfa_pool[
                    (udfa_pool["PosBucket"].astype(str) == str(pos_bucket)) &
                    (~udfa_pool["PlayerID"].astype(str).isin(udfa_used_ids))
                ].copy()

                udfa_room = udfa_room.sort_values(
                    ["NFLUdfaOVR", "OVR", "Player"],
                    ascending=[False, False, True]
                )

                for _, ur in udfa_room.head(needed).iterrows():
                    fill_rows.append({
                        "Season": season_year,
                        "Team": team,
                        "PlayerID": ur.get("PlayerID", ""),
                        "Name": ur.get("Player", ""),
                        "Pos": ur.get("Pos", ""),
                        "PosBucket": ur.get("PosBucket", pos_bucket),
                        "OVR": int(safe_num(ur.get("NFLUdfaOVR", 66), 66)),
                        "Age": random.randint(22, 24),
                        "Status": "Active",
                        "Source": "udfa_fill",
                        "CollegeTeam": ur.get("CollegeTeam", ""),
                        "CollegeUser": ur.get("CollegeUser", "")
                    })
                    udfa_used_ids.add(str(ur.get("PlayerID", "")))

                udfa_taken = min(len(udfa_room), needed)
                needed = max(0, needed - udfa_taken)

            # 2) Remaining holes get veteran filler
            for idx in range(1, needed + 1):
                fill_ovr = get_free_agent_fill_ovr(team_strength, pos_bucket)
                fill_age = random.randint(24, 31)

                used_names = set(
                    work.get("Name", pd.Series(dtype=str)).dropna().astype(str).str.strip().str.lower().tolist()
                )
                fa_name = generate_nfl_free_agent_name(used_names)

                fill_rows.append({
                    "Season": season_year,
                    "Team": team,
                    "PlayerID": f"FA_{season_year}_{normalize_key(team)}_{pos_bucket}_{idx}_{random.randint(1000,9999)}",
                    "Name": fa_name,
                    "Pos": pos_bucket,
                    "PosBucket": pos_bucket,
                    "OVR": fill_ovr,
                    "Age": fill_age,
                    "Status": "Active",
                    "Source": "free_agent_fill",
                    "CollegeTeam": "",
                    "CollegeUser": ""
                })

    if fill_rows:
        fill_df = pd.DataFrame(fill_rows, columns=NFL_CURRENT_ROSTER_COLS)
        work = pd.concat([work, fill_df], ignore_index=True)

    for col in NFL_CURRENT_ROSTER_COLS:
        if col not in work.columns:
            work[col] = pd.NA

    work = work[NFL_CURRENT_ROSTER_COLS].copy()
    work.to_csv("nfl_current_rosters.csv", index=False)
    return work

def build_nfl_current_roster_for_season(season_year, nfl_roster_df, nfl_draft_hist_df, nfl_player_hist_df, existing_current_rosters_df=None):
    season_year = int(season_year)

    if existing_current_rosters_df is None:
        existing_current_rosters_df = (
            pd.read_csv("nfl_current_rosters.csv")
            if os.path.exists("nfl_current_rosters.csv")
            else pd.DataFrame(columns=NFL_CURRENT_ROSTER_COLS)
        )

    existing_current = existing_current_rosters_df.copy()

    if not existing_current.empty and "Season" in existing_current.columns:
        existing_current["Season"] = pd.to_numeric(existing_current["Season"], errors="coerce")
        existing_current = existing_current[
            existing_current["Season"].fillna(-1).astype(int) != int(season_year)
        ].copy()

    base_roster = nfl_roster_df.copy() if nfl_roster_df is not None else pd.DataFrame()
    if base_roster.empty:
        return pd.DataFrame(columns=NFL_CURRENT_ROSTER_COLS)

    for col in ["Team", "Name", "Pos"]:
        if col not in base_roster.columns:
            base_roster[col] = ""
    for col in ["OVR", "Age"]:
        if col not in base_roster.columns:
            base_roster[col] = 0

    base_roster["OVR"] = pd.to_numeric(base_roster["OVR"], errors="coerce").fillna(70)
    base_roster["Age"] = pd.to_numeric(base_roster["Age"], errors="coerce").fillna(25)
    base_roster["PosBucket"] = base_roster["Pos"].map(clean_bucket)

    current_rows = []
    for _, r in base_roster.iterrows():
        base_name = ""
        for candidate_col in ["Name", "Player", "FullName", "PlayerName", "PLAYER", "NAME"]:
            if candidate_col in r and pd.notna(r.get(candidate_col)) and str(r.get(candidate_col)).strip():
                base_name = str(r.get(candidate_col)).strip()
                break

        if not base_name:
            first_name = ""
            last_name = ""

            for first_col in ["FirstName", "First", "FIRSTNAME", "FIRST"]:
                if first_col in r and pd.notna(r.get(first_col)) and str(r.get(first_col)).strip():
                    first_name = str(r.get(first_col)).strip()
                    break

            for last_col in ["LastName", "Last", "LASTNAME", "LAST"]:
                if last_col in r and pd.notna(r.get(last_col)) and str(r.get(last_col)).strip():
                    last_name = str(r.get(last_col)).strip()
                    break

            base_name = f"{first_name} {last_name}".strip()

        if not base_name:
            base_name = f"{str(r.get('Pos', '')).strip()} Player"

        current_rows.append({
            "Season": season_year,
            "Team": r.get("Team", ""),
            "PlayerID": "",
            "Name": base_name,
            "Pos": r.get("Pos", ""),
            "PosBucket": r.get("PosBucket", ""),
            "OVR": int(round(safe_num(r.get("OVR", 70), 70))),
            "Age": int(round(safe_num(r.get("Age", 25), 25))),
            "Status": "Active",
            "Source": "base_nfl_roster",
            "CollegeTeam": "",
            "CollegeUser": ""
        })

    current_df = pd.DataFrame(current_rows, columns=NFL_CURRENT_ROSTER_COLS)

    hist = nfl_player_hist_df.copy() if nfl_player_hist_df is not None else pd.DataFrame()
    if not hist.empty:
        hist["Season"] = pd.to_numeric(hist["Season"], errors="coerce")
        hist = hist[hist["Season"].fillna(-1).astype(int) <= season_year].copy()
        hist = hist.sort_values(["PlayerID", "Season"]).drop_duplicates(subset=["PlayerID"], keep="last")

    draft = nfl_draft_hist_df.copy() if nfl_draft_hist_df is not None else pd.DataFrame()
    if not draft.empty:
        draft["DraftYear"] = pd.to_numeric(draft["DraftYear"], errors="coerce")
        draft = draft[draft["DraftYear"].fillna(9999).astype(int) <= season_year].copy()

    if not draft.empty and not hist.empty:
        draft_lookup = {
            str(r.get("PlayerID", "")): r
            for _, r in draft.iterrows()
        }

        dynasty_rows = []
        for _, pr in hist.iterrows():
            player_id = str(pr.get("PlayerID", "")).strip()
            if not player_id:
                continue

            # Never treat inherited/base NFL players as dynasty additions
            if player_id.startswith("BASE::"):
                continue

            status = str(pr.get("Status", "Active")).strip()
            if status in {"Retired", "Out of League"}:
                continue

            dr = draft_lookup.get(player_id, {})
            dynasty_rows.append({
                "Season": season_year,
                "Team": pr.get("NFLTeam", dr.get("GeneratedNFLTeam", "")),
                "PlayerID": player_id,
                "Name": pr.get("Player", dr.get("Player", "")),
                "Pos": pr.get("Pos", dr.get("Pos", "")),
                "PosBucket": pr.get("PosBucket", dr.get("PosBucket", clean_bucket(pr.get("Pos", dr.get("Pos", ""))))),
                "OVR": int(round(safe_num(pr.get("OverallEnd", dr.get("OVR", 72)), 72))),
                "Age": int(round(safe_num(pr.get("Age", 24), 24))),
                "Status": status if status else "Active",
                "Source": "dynasty_player",
                "CollegeTeam": dr.get("CollegeTeam", ""),
                "CollegeUser": dr.get("CollegeUser", "")
            })

        dynasty_df = pd.DataFrame(dynasty_rows, columns=NFL_CURRENT_ROSTER_COLS)

        if not dynasty_df.empty:
            dynasty_keys = set(
                dynasty_df.apply(
                    lambda r: f"{str(r.get('Team','')).strip().lower()}||{str(r.get('Name','')).strip().lower()}",
                    axis=1
                ).tolist()
            )

            current_df["__key"] = current_df.apply(
                lambda r: f"{str(r.get('Team','')).strip().lower()}||{str(r.get('Name','')).strip().lower()}",
                axis=1
            )
            current_df = current_df[~current_df["__key"].isin(dynasty_keys)].copy()
            current_df = current_df.drop(columns="__key", errors="ignore")

            current_df = pd.concat([current_df, dynasty_df], ignore_index=True)

    for col in NFL_CURRENT_ROSTER_COLS:
        if col not in current_df.columns:
            current_df[col] = pd.NA

    current_df = current_df[NFL_CURRENT_ROSTER_COLS].copy()

    if existing_current is not None and not existing_current.empty:
        for col in NFL_CURRENT_ROSTER_COLS:
            if col not in existing_current.columns:
                existing_current[col] = pd.NA
        existing_current = existing_current[NFL_CURRENT_ROSTER_COLS].copy()
        current_df = pd.concat([existing_current, current_df], ignore_index=True)
    print(current_df[current_df["PlayerID"].astype(str).str.startswith("BASE::", na=False)]["Source"].value_counts(dropna=False))
    current_df.to_csv("nfl_current_rosters.csv", index=False)

    season_df = current_df[
        pd.to_numeric(current_df["Season"], errors="coerce").fillna(-1).astype(int) == int(season_year)
    ].copy()

    return season_df

def simulate_nfl_season(season_year=None):
    universe = load_nfl_universe_data()
    nfl_roster = universe["nfl_roster"]
    cfb_roster = universe["cfb_roster"]
    nfl_draft_hist = universe["nfl_draft_hist"]
    nfl_player_hist = universe["nfl_player_hist"]
    nfl_super_bowl = universe["nfl_super_bowl"]
    nfl_story = universe["nfl_story"]

    if season_year is None:
        season_year = get_current_nfl_season()

    season_year = int(season_year)

    nfl_current_roster = build_nfl_current_roster_for_season(
        season_year=season_year,
        nfl_roster_df=nfl_roster,
        nfl_draft_hist_df=nfl_draft_hist,
        nfl_player_hist_df=nfl_player_hist,
        existing_current_rosters_df=universe["nfl_current_rosters"] if "nfl_current_rosters" in universe else None
    )

    team_strength_df = build_nfl_team_strengths(nfl_current_roster)
    if team_strength_df.empty:
        return None, "NFL roster data is missing, so the season could not be simulated."

    standings_df = simulate_nfl_regular_season(team_strength_df, season_year=season_year, games_per_team=17)
    
    print("STANDINGS TEAM / CONF:")
    print(
        standings_df[["Team", "Conference", "Seed"]]
        .sort_values(["Conference", "Seed"])
        .to_dict("records")
    )

    existing_standings = pd.read_csv("nfl_standings_history.csv") if os.path.exists("nfl_standings_history.csv") else pd.DataFrame(columns=NFL_STANDINGS_HISTORY_COLS)

    if not existing_standings.empty and "Season" in existing_standings.columns:
        existing_standings["Season"] = pd.to_numeric(existing_standings["Season"], errors="coerce")
        existing_standings = existing_standings[
            existing_standings["Season"].fillna(-1).astype(int) != int(season_year)
        ].copy()

    standings_to_save = standings_df.copy()
    for col in NFL_STANDINGS_HISTORY_COLS:
        if col not in standings_to_save.columns:
            standings_to_save[col] = pd.NA
    standings_to_save = standings_to_save[NFL_STANDINGS_HISTORY_COLS].copy()

    standings_combined = pd.concat([existing_standings, standings_to_save], ignore_index=True)
    standings_combined.to_csv("nfl_standings_history.csv", index=False)

    player_hist_combined = simulate_nfl_player_season(
        season_year=season_year,
        nfl_draft_hist_df=nfl_draft_hist,
        nfl_roster_df=nfl_roster,
        existing_player_hist_df=nfl_player_hist
    )

    base_roster_player_rows = simulate_base_nfl_roster_season_rows(
        season_year=season_year,
        nfl_current_rosters_df=nfl_current_roster if "nfl_current_roster" in locals() else universe.get("nfl_current_rosters", pd.DataFrame()),
        existing_player_hist_df=player_hist_combined
    )

    if base_roster_player_rows is not None and not base_roster_player_rows.empty:
        existing_nonseason = player_hist_combined.copy()
        if "Season" in existing_nonseason.columns:
            existing_nonseason["Season"] = pd.to_numeric(existing_nonseason["Season"], errors="coerce")
            existing_nonseason = existing_nonseason[
                existing_nonseason["Season"].fillna(-1).astype(int) != int(season_year)
            ].copy()

        season_dynasty_rows = player_hist_combined[
            pd.to_numeric(player_hist_combined["Season"], errors="coerce").fillna(-1).astype(int) == int(season_year)
        ].copy()

        season_combined_rows = pd.concat([season_dynasty_rows, base_roster_player_rows], ignore_index=True)

        if "PlayerID" in season_combined_rows.columns:
            season_combined_rows = season_combined_rows.drop_duplicates(subset=["PlayerID"], keep="first").copy()

        player_hist_combined = pd.concat([existing_nonseason, season_combined_rows], ignore_index=True)

        for col in NFL_PLAYER_HISTORY_COLS:
            if col not in player_hist_combined.columns:
                player_hist_combined[col] = pd.NA

        player_hist_combined = player_hist_combined[NFL_PLAYER_HISTORY_COLS].copy()
        player_hist_combined.to_csv("nfl_player_history.csv", index=False)

    champion, runner_up, score, playoff_log = simulate_nfl_playoffs(standings_df, season_year)
    if champion is None:
        return None, "Could not determine playoff results."
    existing_playoff = universe["nfl_playoff_hist"].copy() if universe["nfl_playoff_hist"] is not None else pd.DataFrame(columns=NFL_PLAYOFF_HISTORY_COLS)

    if not existing_playoff.empty and "Season" in existing_playoff.columns:
        existing_playoff["Season"] = pd.to_numeric(existing_playoff["Season"], errors="coerce")
        existing_playoff = existing_playoff[
            existing_playoff["Season"].fillna(-1).astype(int) != int(season_year)
        ].copy()

    playoff_log_clean = playoff_log.copy() if playoff_log is not None else pd.DataFrame(columns=NFL_PLAYOFF_HISTORY_COLS)
    for col in NFL_PLAYOFF_HISTORY_COLS:
        if col not in playoff_log_clean.columns:
            playoff_log_clean[col] = pd.NA
    playoff_log_clean = playoff_log_clean[NFL_PLAYOFF_HISTORY_COLS].copy()

    playoff_combined = pd.concat([existing_playoff, playoff_log_clean], ignore_index=True)
    playoff_combined.to_csv("nfl_playoff_history.csv", index=False)

    season_player_df = player_hist_combined[
        pd.to_numeric(player_hist_combined["Season"], errors="coerce").fillna(-1).astype(int) == int(season_year)
    ].copy()

    awards_hist = simulate_nfl_awards(
        season_year=season_year,
        season_player_df=season_player_df,
        existing_awards_df=universe["nfl_awards_hist"]
    )


    season_story_rows = []

    season_player_df = player_hist_combined[
        pd.to_numeric(player_hist_combined["Season"], errors="coerce").fillna(-1).astype(int) == int(season_year)
    ].copy()
    if not season_player_df.empty:
        breakout_df = season_player_df.sort_values(["CareerValue", "OverallEnd"], ascending=[False, False]).head(3)
        for _, r in breakout_df.iterrows():
            season_story_rows.append({
                "Season": int(season_year),
                "Week": 21,
                "PlayerID": r.get("PlayerID", ""),
                "Player": r.get("Player", ""),
                "NFLTeam": r.get("NFLTeam", ""),
                "EventType": "SeasonOutcome",
                "Headline": f"{r.get('Player', '')} makes noise in year {max(1, season_year - int(get_latest_completed_draft_year() or season_year) + 1)}",
                "Description": f"{r.get('NFLTeam', '')} {r.get('Pos', '')} posted {r.get('StatLine', '')}. Role: {r.get('Role', '')}.",
                "ImpactScore": int(min(99, max(55, safe_num(r.get('CareerValue', 60), 60))))
            })

        retired_df = season_player_df[season_player_df["Status"].astype(str) == "Retired"].copy().head(6)
        for _, r in retired_df.iterrows():
            season_story_rows.append({
                "Season": int(season_year),
                "Week": 24,
                "PlayerID": r.get("PlayerID", ""),
                "Player": r.get("Player", ""),
                "NFLTeam": r.get("NFLTeam", ""),
                "EventType": "Retirement",
                "Headline": f"{r.get('Player', '')} calls it a career",
                "Description": f"{r.get('NFLTeam', '')} {r.get('Pos', '')} retires after the {season_year} season.",
                "ImpactScore": 80
            })

        out_df = season_player_df[season_player_df["Status"].astype(str) == "Out of League"].copy().head(6)
        for _, r in out_df.iterrows():
            season_story_rows.append({
                "Season": int(season_year),
                "Week": 24,
                "PlayerID": r.get("PlayerID", ""),
                "Player": r.get("Player", ""),
                "NFLTeam": r.get("NFLTeam", ""),
                "EventType": "RosterTurnover",
                "Headline": f"{r.get('Player', '')} falls out of the league",
                "Description": f"{r.get('NFLTeam', '')} {r.get('Pos', '')} is no longer holding a roster spot heading into next season.",
                "ImpactScore": 66
            })

    sb_season_pool = player_hist_combined[
        pd.to_numeric(player_hist_combined["Season"], errors="coerce").fillna(-1).astype(int) == int(season_year)
    ].copy()

    mvp_name, mvp_team = choose_super_bowl_mvp(champion, sb_season_pool.copy())

    sb_headline = f"{champion} defeat {runner_up} to win the Super Bowl"

    sb_signature_moment, sb_used_player = generate_super_bowl_signature_moment(
        champion=champion,
        runner_up=runner_up,
        score=score,
        season_player_df=sb_season_pool,
        nfl_draft_hist_df=nfl_draft_hist
    )

    sb_user_note = generate_super_bowl_user_alumni_note(
        champion=champion,
        runner_up=runner_up,
        season_player_df=sb_season_pool,
        nfl_draft_hist_df=nfl_draft_hist,
        already_used_player=sb_used_player
    )

    new_sb_row = pd.DataFrame([{
        "Season": int(season_year),
        "Champion": champion,
        "RunnerUp": runner_up,
        "Score": score,
        "MVP": mvp_name,
        "MVPTeam": mvp_team,
        "Headline": sb_headline,
        "GameMoment": sb_signature_moment,
        "UserAlumniNote": sb_user_note
    }])

    existing_sb = nfl_super_bowl.copy() if nfl_super_bowl is not None else pd.DataFrame(columns=NFL_SUPER_BOWL_HISTORY_COLS)
    if not existing_sb.empty and "Season" in existing_sb.columns:
        existing_sb["Season"] = pd.to_numeric(existing_sb["Season"], errors="coerce")
        existing_sb = existing_sb[
            existing_sb["Season"].fillna(-1).astype(int) != int(season_year)
        ].copy()

    sb_combined = pd.concat([existing_sb, new_sb_row], ignore_index=True)
    for col in NFL_SUPER_BOWL_HISTORY_COLS:
        if col not in sb_combined.columns:
            sb_combined[col] = pd.NA
    sb_combined = sb_combined[NFL_SUPER_BOWL_HISTORY_COLS].copy()
    sb_combined.to_csv("nfl_super_bowl_history.csv", index=False)

    season_awards = awards_hist[
        pd.to_numeric(awards_hist["Season"], errors="coerce").fillna(-1).astype(int) == int(season_year)
    ].copy()

    if not season_awards.empty:
        for _, r in season_awards.iterrows():
            if str(r.get("Result", "")) != "Winner":
                continue
            season_story_rows.append({
                "Season": int(season_year),
                "Week": 23,
                "PlayerID": r.get("PlayerID", ""),
                "Player": r.get("Player", ""),
                "NFLTeam": r.get("NFLTeam", ""),
                "EventType": "Award",
                "Headline": f"{r.get('Player', '')} wins {r.get('Award', '')}",
                "Description": f"{r.get('NFLTeam', '')} {r.get('Pos', '')} earned {r.get('Award', '')}. {r.get('Notes', '')}",
                "ImpactScore": 92
            })

    season_story_rows.append({
        "Season": int(season_year),
        "Week": 22,
        "PlayerID": "",
        "Player": mvp_name,
        "NFLTeam": champion,
        "EventType": "SuperBowl",
        "Headline": sb_headline,
        "Description": f"{champion} beat {runner_up}. Super Bowl MVP: {mvp_name}. Final score: {score}.",
        "ImpactScore": 99
    })

    existing_story = nfl_story.copy() if nfl_story is not None else pd.DataFrame(columns=NFL_STORY_EVENTS_COLS)
    if not existing_story.empty and "Season" in existing_story.columns:
        existing_story["Season"] = pd.to_numeric(existing_story["Season"], errors="coerce")
        existing_story = existing_story[
            ~(
                existing_story["Season"].fillna(-1).astype(int).eq(int(season_year)) &
                existing_story["EventType"].astype(str).isin(["SeasonOutcome", "SuperBowl"])
            )
        ].copy()

    story_combined = pd.concat([existing_story, pd.DataFrame(season_story_rows)], ignore_index=True)
    for col in NFL_STORY_EVENTS_COLS:
        if col not in story_combined.columns:
            story_combined[col] = pd.NA
    story_combined = story_combined[NFL_STORY_EVENTS_COLS].copy()
    story_combined.to_csv("nfl_story_events.csv", index=False)

    next_season_roster = build_nfl_current_roster_for_season(
        season_year=season_year + 1,
        nfl_roster_df=nfl_roster,
        nfl_draft_hist_df=nfl_draft_hist,
        nfl_player_hist_df=player_hist_combined,
        existing_current_rosters_df=universe["nfl_current_rosters"] if "nfl_current_rosters" in universe else None
    )

    next_season_roster = run_nfl_offseason_roster_maintenance(
        season_year=season_year + 1,
        current_roster_df=next_season_roster,
        cfb_roster_df=cfb_roster,
        nfl_draft_hist_df=nfl_draft_hist
    )

    save_nfl_universe_settings(
        current_season=season_year + 1,
        last_draft_year=get_latest_completed_draft_year(),
        last_super_bowl_season=season_year
    )

    return {
        "season_year": season_year,
        "standings": standings_df,
        "standings_history": standings_combined,
        "champion": champion,
        "runner_up": runner_up,
        "score": score,
        "super_bowl_history": sb_combined,
        "player_history": player_hist_combined,
        "story_events": story_combined,
        "awards_history": awards_hist,
        "playoff_log": playoff_log,
        "playoff_history": playoff_combined
    }, f"NFL season {season_year} simulated. Champion: {champion}."

def simulate_base_nfl_roster_season_rows(season_year, nfl_current_rosters_df, existing_player_hist_df=None):
    if nfl_current_rosters_df is None or nfl_current_rosters_df.empty:
        return pd.DataFrame(columns=NFL_PLAYER_HISTORY_COLS)

    work = nfl_current_rosters_df.copy()
    if "Season" in work.columns:
        work["Season"] = pd.to_numeric(work["Season"], errors="coerce")
        work = work[work["Season"].fillna(-1).astype(int) == int(season_year)].copy()

    if work.empty:
        return pd.DataFrame(columns=NFL_PLAYER_HISTORY_COLS)

    if "Source" in work.columns:
        work = work[
            work["Source"].astype(str).isin(["base_nfl_roster", "free_agent_fill"])
        ].copy()

    if work.empty:
        return pd.DataFrame(columns=NFL_PLAYER_HISTORY_COLS)

    existing_player_hist_df = existing_player_hist_df.copy() if existing_player_hist_df is not None else pd.DataFrame()

    rows = []
    for _, r in work.iterrows():
        player = str(r.get("Name", r.get("Player", "Unknown Player"))).strip()
        nfl_team = str(r.get("Team", "")).strip()
        pos = str(r.get("Pos", "")).strip()
        bucket = str(r.get("PosBucket", clean_bucket(pos))).strip()

        player_id = str(r.get("PlayerID", "")).strip()
        if not player_id:
            player_id = f"BASE::{normalize_key(nfl_team)}::{normalize_key(player)}::{normalize_key(pos)}"

        current_age = int(safe_num(r.get("Age", 26), 26))
        roster_ovr = int(safe_num(r.get("OVR", 72), 72))

        prior_rows = pd.DataFrame()
        if existing_player_hist_df is not None and not existing_player_hist_df.empty and "PlayerID" in existing_player_hist_df.columns:
            prior_rows = existing_player_hist_df[
                existing_player_hist_df["PlayerID"].astype(str) == player_id
            ].copy()

            if not prior_rows.empty and "Season" in prior_rows.columns:
                prior_rows["Season"] = pd.to_numeric(prior_rows["Season"], errors="coerce")
                prior_rows = prior_rows[
                    prior_rows["Season"].fillna(-1).astype(int) < int(season_year)
                ].sort_values("Season")

        if not prior_rows.empty:
            overall_start = int(safe_num(prior_rows.iloc[-1].get("OverallEnd", roster_ovr), roster_ovr))
            age = int(safe_num(prior_rows.iloc[-1].get("Age", current_age - 1), current_age - 1)) + 1
        else:
            overall_start = roster_ovr
            age = current_age

        # Simple veteran age curve
        if age <= 24:
            delta = random.uniform(0.0, 2.0)
        elif age <= 28:
            delta = random.uniform(-0.5, 1.2)
        elif age <= 31:
            delta = random.uniform(-1.2, 0.5)
        elif age <= 34:
            delta = random.uniform(-2.0, 0.2)
        else:
            delta = random.uniform(-3.0, -0.4)

        overall_end = int(max(60, min(99, round(overall_start + delta))))
        peak_ovr = max(overall_start, overall_end)

        if bucket == "QB":
            role = "Starter" if overall_end >= 74 else "Backup"
            starts = random.randint(10, 17) if role == "Starter" else random.randint(0, 4)
            games = max(starts, random.randint(11, 17))
            pass_yds = int(250 + overall_end * 30 + starts * 50 + random.randint(-250, 300))
            pass_tds = max(1, int(pass_yds / 185) + random.randint(-2, 4))
            stat_line = f"{pass_yds} pass yds, {pass_tds} pass TD"
            mvp_votes = random.randint(1, 10) if overall_end >= 90 and starts >= 12 and random.random() < 0.18 else 0
        elif bucket == "RB":
            role = "Starter" if overall_end >= 76 else "Rotation"
            starts = random.randint(6, 16) if role == "Starter" else random.randint(0, 6)
            games = random.randint(11, 17)
            rush_yds = int(100 + overall_end * 9 + games * 12 + random.randint(-120, 180))
            rush_tds = max(0, int(rush_yds / 145) + random.randint(-1, 3))
            stat_line = f"{rush_yds} rush yds, {rush_tds} rush TD"
            mvp_votes = 0
        elif bucket in {"WR", "TE"}:
            role = "Starter" if overall_end >= 76 else "Rotation"
            starts = random.randint(5, 16) if role == "Starter" else random.randint(0, 6)
            games = random.randint(11, 17)
            rec_yds = int(120 + overall_end * 10 + games * 14 + random.randint(-130, 210))
            rec_tds = max(0, int(rec_yds / 175) + random.randint(-1, 3))
            stat_line = f"{rec_yds} rec yds, {rec_tds} rec TD"
            mvp_votes = 0
        elif bucket in {"EDGE", "IDL", "LB"}:
            role = "Starter" if overall_end >= 75 else "Rotation"
            starts = random.randint(5, 17) if role == "Starter" else random.randint(0, 5)
            games = random.randint(11, 17)
            sacks = max(0, int((overall_end - 70) / 4) + random.randint(-2, 3))
            tackles = int(18 + games * 2.2 + starts * 1.1 + random.randint(-8, 14))
            stat_line = f"{tackles} tackles, {sacks} sacks"
            mvp_votes = 0
        elif bucket in {"CB", "S"}:
            role = "Starter" if overall_end >= 75 else "Rotation"
            starts = random.randint(5, 17) if role == "Starter" else random.randint(0, 5)
            games = random.randint(11, 17)
            ints = max(0, int((overall_end - 72) / 7) + random.randint(-1, 3))
            tackles = int(18 + games * 2.0 + starts * 1.0 + random.randint(-8, 14))
            stat_line = f"{tackles} tackles, {ints} INT"
            mvp_votes = 0
        else:
            role = "Depth"
            starts = random.randint(0, 4)
            games = random.randint(8, 17)
            stat_line = f"{games} games, {starts} starts"
            mvp_votes = 0

        pro_bowl = "Yes" if overall_end >= 89 and random.random() < 0.35 else "No"
        all_pro = "Yes" if overall_end >= 92 and random.random() < 0.16 else "No"

        career_value = round(
            overall_end * 0.42 +
            starts * 1.20 +
            (8 if pro_bowl == "Yes" else 0) +
            (10 if all_pro == "Yes" else 0) +
            (mvp_votes * 1.5),
            1
        )

        status = "Active"
        if should_retire_nfl_player(age, overall_end, "Base NFL Veteran", bucket):
            status = "Retired"
        elif age >= 34 and overall_end <= 68 and random.random() < 0.35:
            status = "Out of League"
        elif age >= 32 and random.random() < 0.20:
            status = "Declining"

        rows.append({
            "Season": int(season_year),
            "PlayerID": player_id,
            "Player": player,
            "NFLTeam": nfl_team,
            "Pos": pos,
            "PosBucket": bucket,
            "Age": age,
            "Role": role,
            "OverallStart": overall_start,
            "OverallEnd": overall_end,
            "PeakOVR": peak_ovr,
            "ProOutcome": "Base NFL Veteran",
            "DevelopmentCurve": "Normal",
            "Games": games,
            "Starts": starts,
            "StatLine": stat_line,
            "ProBowl": pro_bowl,
            "AllPro": all_pro,
            "MVPVotes": int(mvp_votes),
            "SuperBowlWin": "No",
            "SuperBowlAppear": "No",
            "CareerValue": career_value,
            "Status": status
        })

    out = pd.DataFrame(rows)
    for col in NFL_PLAYER_HISTORY_COLS:
        if col not in out.columns:
            out[col] = pd.NA
    return out[NFL_PLAYER_HISTORY_COLS].copy()
            
def simulate_nfl_awards(season_year, season_player_df, existing_awards_df=None):
    if existing_awards_df is None:
        existing_awards_df = pd.read_csv("nfl_awards_history.csv") if os.path.exists("nfl_awards_history.csv") else pd.DataFrame(columns=NFL_AWARDS_HISTORY_COLS)

    existing_awards_df = existing_awards_df.copy()
    if not existing_awards_df.empty and "Season" in existing_awards_df.columns:
        existing_awards_df["Season"] = pd.to_numeric(existing_awards_df["Season"], errors="coerce")
        existing_awards_df = existing_awards_df[
            existing_awards_df["Season"].fillna(-1).astype(int) != int(season_year)
        ].copy()

    if season_player_df is None or season_player_df.empty:
        combined = existing_awards_df.copy()
        combined.to_csv("nfl_awards_history.csv", index=False)
        return combined

    work = season_player_df.copy()
    work["CareerValue"] = pd.to_numeric(work["CareerValue"], errors="coerce").fillna(0)
    work["OverallEnd"] = pd.to_numeric(work["OverallEnd"], errors="coerce").fillna(0)
    work["MVPVotes"] = pd.to_numeric(work["MVPVotes"], errors="coerce").fillna(0)

    rows = []

    # MVP
    work["MVPScore"] = work["MVPVotes"] * 3.5 + work["CareerValue"] * 0.9 + work["OverallEnd"] * 0.6

    # Strong QB bias for MVP, like real NFL voting
    work["MVPScore"] = work["MVPScore"] + work["PosBucket"].astype(str).map(
        lambda p: 22 if p == "QB" else (6 if p in {"RB", "WR", "TE"} else 0)
    )

    # Extra bump for elite QB seasons
    qb_mask = work["PosBucket"].astype(str) == "QB"
    work.loc[qb_mask, "MVPScore"] = work.loc[qb_mask, "MVPScore"] + (
        pd.to_numeric(work.loc[qb_mask, "OverallEnd"], errors="coerce").fillna(0) * 0.35
    )

    mvp_df = work.sort_values(["MVPScore", "MVPVotes", "CareerValue", "OverallEnd"], ascending=[False, False, False, False])

    if not mvp_df.empty:
        r = mvp_df.iloc[0]
        rows.append({
            "Season": int(season_year),
            "Award": "NFL MVP",
            "PlayerID": r.get("PlayerID", ""),
            "Player": r.get("Player", ""),
            "NFLTeam": r.get("NFLTeam", ""),
            "Pos": r.get("Pos", ""),
            "Result": "Winner",
            "Notes": r.get("StatLine", "")
        })

    # Offensive Player of the Year / Defensive Player of the Year
    offense_buckets = {"QB", "RB", "WR", "TE", "OL"}
    defense_buckets = {"EDGE", "IDL", "LB", "CB", "S"}

    opoy_pool = work[work["PosBucket"].astype(str).isin(offense_buckets)].copy()
    dpoy_pool = work[work["PosBucket"].astype(str).isin(defense_buckets)].copy()

    if not opoy_pool.empty:
        opoy_pool["OPOYScore"] = (
            pd.to_numeric(opoy_pool["CareerValue"], errors="coerce").fillna(0) * 1.0 +
            pd.to_numeric(opoy_pool["OverallEnd"], errors="coerce").fillna(0) * 0.7
        )

        # Slight nudge away from MVP being the only QB award,
        # but QBs can still win OPOY with huge seasons.
        opoy_pool["OPOYScore"] = opoy_pool["OPOYScore"] + opoy_pool["PosBucket"].astype(str).map(
            lambda p: 2 if p in {"RB", "WR", "TE"} else 0
        )

        opoy_df = opoy_pool.sort_values(
            ["OPOYScore", "CareerValue", "OverallEnd"],
            ascending=[False, False, False]
        )

        if not opoy_df.empty:
            r = opoy_df.iloc[0]
            rows.append({
                "Season": int(season_year),
                "Award": "Offensive Player of the Year",
                "PlayerID": r.get("PlayerID", ""),
                "Player": r.get("Player", ""),
                "NFLTeam": r.get("NFLTeam", ""),
                "Pos": r.get("Pos", ""),
                "Result": "Winner",
                "Notes": r.get("StatLine", "")
            })

    if not dpoy_pool.empty:
        dpoy_pool["DPOYScore"] = (
            pd.to_numeric(dpoy_pool["CareerValue"], errors="coerce").fillna(0) * 1.0 +
            pd.to_numeric(dpoy_pool["OverallEnd"], errors="coerce").fillna(0) * 0.8
        )

        # Slight edge-rusher / linebacker weighting
        dpoy_pool["DPOYScore"] = dpoy_pool["DPOYScore"] + dpoy_pool["PosBucket"].astype(str).map(
            lambda p: 2 if p in {"EDGE", "LB"} else 0
        )

        dpoy_df = dpoy_pool.sort_values(
            ["DPOYScore", "CareerValue", "OverallEnd"],
            ascending=[False, False, False]
        )

        if not dpoy_df.empty:
            r = dpoy_df.iloc[0]
            rows.append({
                "Season": int(season_year),
                "Award": "Defensive Player of the Year",
                "PlayerID": r.get("PlayerID", ""),
                "Player": r.get("Player", ""),
                "NFLTeam": r.get("NFLTeam", ""),
                "Pos": r.get("Pos", ""),
                "Result": "Winner",
                "Notes": r.get("StatLine", "")
            })

    # Rookie awards
    rookies = work[work["Age"].fillna(99).astype(int) <= 22].copy()
    if not rookies.empty:
        off_rookie = rookies[rookies["PosBucket"].astype(str).isin(["QB", "RB", "WR", "TE", "OL"])].sort_values(
            ["CareerValue", "OverallEnd"], ascending=[False, False]
        )
        def_rookie = rookies[rookies["PosBucket"].astype(str).isin(["EDGE", "IDL", "LB", "CB", "S"])].sort_values(
            ["CareerValue", "OverallEnd"], ascending=[False, False]
        )

        if not off_rookie.empty:
            r = off_rookie.iloc[0]
            rows.append({
                "Season": int(season_year),
                "Award": "Offensive Rookie of the Year",
                "PlayerID": r.get("PlayerID", ""),
                "Player": r.get("Player", ""),
                "NFLTeam": r.get("NFLTeam", ""),
                "Pos": r.get("Pos", ""),
                "Result": "Winner",
                "Notes": r.get("StatLine", "")
            })

        if not def_rookie.empty:
            r = def_rookie.iloc[0]
            rows.append({
                "Season": int(season_year),
                "Award": "Defensive Rookie of the Year",
                "PlayerID": r.get("PlayerID", ""),
                "Player": r.get("Player", ""),
                "NFLTeam": r.get("NFLTeam", ""),
                "Pos": r.get("Pos", ""),
                "Result": "Winner",
                "Notes": r.get("StatLine", "")
            })

    # All-Pro
    allpro_df = work.sort_values(["OverallEnd", "CareerValue"], ascending=[False, False]).head(6)
    for _, r in allpro_df.iterrows():
        rows.append({
            "Season": int(season_year),
            "Award": "All-Pro",
            "PlayerID": r.get("PlayerID", ""),
            "Player": r.get("Player", ""),
            "NFLTeam": r.get("NFLTeam", ""),
            "Pos": r.get("Pos", ""),
            "Result": "First Team",
            "Notes": r.get("StatLine", "")
        })

    # Pro Bowl
    probowl_df = work.sort_values(["CareerValue", "OverallEnd"], ascending=[False, False]).head(12)
    for _, r in probowl_df.iterrows():
        rows.append({
            "Season": int(season_year),
            "Award": "Pro Bowl",
            "PlayerID": r.get("PlayerID", ""),
            "Player": r.get("Player", ""),
            "NFLTeam": r.get("NFLTeam", ""),
            "Pos": r.get("Pos", ""),
            "Result": "Selected",
            "Notes": r.get("StatLine", "")
        })

    new_df = pd.DataFrame(rows, columns=NFL_AWARDS_HISTORY_COLS)
    combined = pd.concat([existing_awards_df, new_df], ignore_index=True)

    for col in NFL_AWARDS_HISTORY_COLS:
        if col not in combined.columns:
            combined[col] = pd.NA

    combined = combined[NFL_AWARDS_HISTORY_COLS].copy()
    combined.to_csv("nfl_awards_history.csv", index=False)
    return combined            

# 🚨 STREAMLIT RULE: You can only have ONE set_page_config, and it MUST be first! 🚨
st.set_page_config(
    page_title="ISPN College Football Gameday",
    page_icon="https://media.licdn.com/dms/image/sync/v2/D5627AQF8Fr9Tf4XYPQ/articleshare-shrink_800/articleshare-shrink_800/0/1719872318020?e=2147483647&v=beta&t=U2U9JE3vLoVeupd5tqDMceMxmhMeu0G47py4I5IUZ8o",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_dynasty_state(path='dynasty_state.csv'):
    defaults = {
        'CurrentWeek': 16,
        'CurrentYear': 2041,
        'IsBowlWeek': True,
        'BowlRound': 1,
    }
    try:
        state_df = pd.read_csv(path)
        if state_df.empty:
            return defaults
        row = state_df.iloc[0].to_dict()

        def _to_int(value, fallback):
            try:
                if pd.isna(value):
                    return fallback
                return int(float(value))
            except Exception:
                return fallback

        def _to_bool(value, fallback):
            if pd.isna(value):
                return fallback
            sval = str(value).strip().lower()
            if sval in ('1', 'true', 'yes', 'y', 'on'):
                return True
            if sval in ('0', 'false', 'no', 'n', 'off'):
                return False
            return fallback

        return {
            'CurrentWeek': _to_int(row.get('CurrentWeek', defaults['CurrentWeek']), defaults['CurrentWeek']),
            'CurrentYear': _to_int(row.get('CurrentYear', defaults['CurrentYear']), defaults['CurrentYear']),
            'IsBowlWeek': _to_bool(row.get('IsBowlWeek', defaults['IsBowlWeek']), defaults['IsBowlWeek']),
            'BowlRound': _to_int(row.get('BowlRound', defaults['BowlRound']), defaults['BowlRound']),
        }
    except Exception:
        return defaults


_DYNASTY_STATE = load_dynasty_state()
CURRENT_WEEK_NUMBER = _DYNASTY_STATE['CurrentWeek']
CURRENT_YEAR        = _DYNASTY_STATE['CurrentYear']
IS_BOWL_WEEK        = _DYNASTY_STATE['IsBowlWeek']
BOWL_ROUND          = _DYNASTY_STATE['BowlRound']

st.markdown("""
    <style>
    /* 1. HIDE DEFAULT STREAMLIT ELEMENTS */
    .stDeployButton {display:none;}
    [data-testid="stDecoration"] {display:none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background: transparent;}

    /* 2. THE MAIN CONTAINER - RAISED UP & RESPONSIVE */
    .main .block-container {
        max-width: 1200px;
        padding-top: 0rem;   /* Raised page up */
        padding-right: 1rem;
        padding-left: 1rem;
        padding-bottom: 2rem;
    }

    /* 3. CENTER ALL HEADERS & SUBTEXT */
    h1, h2, h3 {
        text-align: center !important;
        width: 100%;
        margin-top: 0rem !important;
    }

    /* Targets st.caption */
    .stCaption {
        text-align: center !important;
        display: block;
        width: 100%;
    }

    /* Targets markdown paragraphs following headers */
    h1 + p, h2 + p, h3 + p, .stMarkdown p {
        text-align: center !important;
    }

    /* 4. SWIPEABLE TABS FOR MOBILE/TABLETS */
    div[data-testid="stTabList"] {
        display: flex;
        overflow-x: auto;         /* Allows horizontal swipe */
        white-space: nowrap;      /* Keeps tabs on one line */
        scrollbar-width: none;    /* Hides scrollbar (Firefox) */
        -ms-overflow-style: none; /* Hides scrollbar (Edge) */
        gap: 8px;
        padding-bottom: 5px;
    }

    div[data-testid="stTabList"]::-webkit-scrollbar {
        display: none;            /* Hides scrollbar (Chrome/Safari) */
    }

    /* Makes tab buttons easier to tap on touchscreens */
    button[data-testid="stBaseButton-tertiary"] {
        flex: 0 0 auto;
        padding: 10px 15px;
    }

    /* 5. MOBILE OPTIMIZATION */
    @media (max-width: 768px) {
        .main .block-container {
            padding-top: 0rem;
            padding-right: 0.5rem;
            padding-left: 0.5rem;
        }
        h1 { font-size: 1.8rem !important; }
        h2 { font-size: 1.5rem !important; }
    }

    /* ── ISPN UTILITY CLASSES ────────────────────────────────────────────
       Global reusable classes replacing repeated inline styles.
       Used across recruiting tables, CFP boards, SOS, H2H, Classics.
    ─────────────────────────────────────────────────────────────────── */

    /* Table containers */
    .isp-table-wrap {
        overflow-x: auto;
        border: 1px solid #334155;
        border-radius: 14px;
        background: #0f172a;
    }
    .isp-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }

    /* Header rows */
    .isp-tr-header {
        background: #111827;
        color: #f8fafc;
    }

    /* Table headers — dark bg (white text) */
    .isp-th {
        padding: 10px 12px;
        color: #f8fafc;
        font-weight: 800;
    }
    .isp-th-left {
        text-align: left;
    }

    /* Table headers — light bg (dark text) */
    .isp-th-light {
        padding: 10px 12px;
        color: #111827;
        font-weight: 800;
    }

    /* Table cell — pinned/nowrap */
    .isp-td-pin {
        padding: 10px 12px;
        border-bottom: 1px solid #334155;
        white-space: nowrap;
    }

    /* Narrow number column */
    .isp-td-num {
        width: 38px;
        text-align: center;
    }

    /* Stat box card */
    .isp-stat-box {
        background: rgba(255,255,255,0.05);
        padding: 12px;
        border-radius: 10px;
        text-align: center;
    }

    /* Muted small caption text */
    .isp-muted {
        font-size: 0.8rem;
        color: #9ca3af;
    }

    /* Centered block with bottom margin */
    .isp-tc {
        text-align: center;
        margin-bottom: 10px;
    }

    /* Flex row with gap */
    .isp-flex-row {
        display: flex;
        align-items: center;
        gap: 10px;
    }

    /* Logo sizes */
    .isp-logo-55 { width: 55px; height: 55px; object-fit: contain; }
    .isp-logo-60 { width: 60px; height: 60px; object-fit: contain; }
    .isp-logo-65 { width: 65px; height: 65px; object-fit: contain; }
    </style>
    """, unsafe_allow_html=True)

def load_team_visuals(csv_path="team_visuals.csv"):
    try:
        _tv = pd.read_csv(csv_path)
        if _tv.empty or 'Team' not in _tv.columns:
            return {}
        visuals = {}
        for _, _r in _tv.iterrows():
            _team = str(_r.get('Team', '')).strip()
            if not _team:
                continue
            visuals[_team] = {
                'slug': str(_r.get('Slug', '')).strip(),
                'primary': str(_r.get('Primary', '')).strip() or '#38bdf8',
                'secondary': str(_r.get('Secondary', '')).strip() or '#94a3b8',
            }
        return visuals
    except Exception:
        return {}

TEAM_VISUALS = load_team_visuals()

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

def get_team_logo_url(team):
    slug = get_team_slug(team)
    return f"https://a.espncdn.com/i/teamlogos/ncaa/500/{slug}.png" if slug else ""

def get_local_logo_path(team):
    aliases = get_team_aliases(clean_team_name_for_lookup(team))
    exact_keys = [normalize_key(a) for a in aliases]

    for key in exact_keys:
        if key in LOGO_FILE_INDEX:
            return str(LOGO_FILE_INDEX[key])

    return ""

def get_logo_source(team):
    local = get_local_logo_path(team)
    if local:
        return local
    return ""

def clean_team_name_for_lookup(team):
    team = str(team).strip()
    if not team or team.lower() == "nan":
        return ""

    # remove seed/rank prefixes like "#2 " or "2 "
    team = re.sub(r'^\#?\d+\s+', '', team).strip()

    # remove trailing playoff asterisk(s)
    team = re.sub(r'\*+$', '', team).strip()

    return team

def get_redshirt_logo_path():
    candidates = [
        "REDSHIRT.png",
        "logos/REDSHIRT.png",
        "/mount/src/cfb_dynasty_app/REDSHIRT.png",
        "/mount/src/cfb_dynasty_app/logos/REDSHIRT.png",
    ]
    for path in candidates:
        try:
            if os.path.exists(path):
                return path
        except Exception:
            pass
    return ""

def get_redshirt_logo_html(width=18, margin="0 4px -3px 4px"):
    try:
        path = get_redshirt_logo_path()
        if path:
            uri = image_file_to_data_uri(path)
            if uri:
                return f'<img src="{uri}" width="{width}" style="margin:{margin}; vertical-align:middle;">'
    except Exception:
        pass
    return "🔴"

def get_redshirt_logo_src():
    try:
        path = get_redshirt_logo_path()
        if path:
            return image_file_to_data_uri(path)
    except Exception:
        pass
    return None

def get_team_primary_color(team):
    team = clean_team_name_for_lookup(team)

    if team in TEAM_VISUALS:
        return TEAM_VISUALS[team].get("primary", "#1f77b4")

    nteam = normalize_key(team)

    for name, meta in TEAM_VISUALS.items():
        if normalize_key(name) == nteam:
            return meta.get("primary", "#1f77b4")

    for name, meta in TEAM_VISUALS.items():
        aliases = TEAM_ALIASES.get(name, [])
        for alias in [name] + aliases:
            if normalize_key(alias) == nteam:
                return meta.get("primary", "#1f77b4")

    return "#1f77b4"


def get_team_secondary_color(team):
    team = clean_team_name_for_lookup(team)

    if team in TEAM_VISUALS:
        return TEAM_VISUALS[team].get("secondary", "#ffffff")

    nteam = normalize_key(team)

    for name, meta in TEAM_VISUALS.items():
        if normalize_key(name) == nteam:
            return meta.get("secondary", "#ffffff")

    for name, meta in TEAM_VISUALS.items():
        aliases = TEAM_ALIASES.get(name, [])
        for alias in [name] + aliases:
            if normalize_key(alias) == nteam:
                return meta.get("secondary", "#ffffff")

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
          <div class="isp-flex-row">
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
      <table class="isp-table">
        <thead>
          <tr style="background:#f8fafc;color:#111827;">
            <th class="isp-th-light isp-th-left">Team</th>
            <th class="isp-th-light">CFP Rank</th>
            <th class="isp-th-light">SOS</th>
            <th class="isp-th-light">QB Tier</th>
            <th class="isp-th-light">Power Index</th>
            <th class="isp-th-light">Natty Odds</th>
            <th class="isp-th-light">CFP Odds</th>
            <th class="isp-th-light">Natty if Lose to Unranked</th>
            <th class="isp-th-light">Natty if Lose to Ranked</th>
            <th class="isp-th-light">CFP if Lose to Unranked</th>
            <th class="isp-th-light">CFP if Lose to Ranked</th>
            <th class="isp-th-light">Collapse Risk</th>
            <th class="isp-th-light">Program Stock</th>
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
    # ── SAFE LOOKUP: Find 'user', 'User', or 'USER' dynamically ──
    user_col = next((c for c in champs_local.columns if str(c).strip().lower() == 'user'), None)
    if user_col:
        champs_local['user'] = champs_local[user_col].astype(str).str.strip().str.title()
    else:
        champs_local['user'] = "" 

    champs_local['Team'] = champs_local['Team'].astype(str).str.strip().map(normalize_history_team_name)
    # ── SAFE LOOKUP: Find 'YEAR' dynamically to avoid hidden character crashes ──
    year_col = next((c for c in champs_local.columns if str(c).replace('\ufeff', '').strip().upper() == 'YEAR'), None)
    if year_col:
        champs_local['YEAR'] = pd.to_numeric(champs_local[year_col], errors='coerce')
    else:
        champs_local['YEAR'] = 0  # Fallback so the math doesn't crash


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
        monsters   = int(row.get('Monsters', 0))
        quick_hogs = int(row.get('Quick Hogs', 0))
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
            + chip('CHEAT', str(quad_90), '#60a5fa')
            + chip('MON', str(monsters), '#f97316')
            + chip('HOG', str(quick_hogs), '#22c55e')
            + chip('GEN', str(gen), '#fbbf24')
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
    # Recalculate directly from final Team Speed Score.
    # A final speed score of 130 maps to 200 MPH.
    mph = (team_speed_score / 130.0) * 200.0
    return round(max(0.0, mph), 1)


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
            rs_tag = "🔴" if row['IsRS'] else ""
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

        st.markdown("---")
        st.subheader("📊 Athletic Comparison Chart")

        team_metric_map = {
            team_a: {
                "Players 90+ Speed": summ_a["90+ SPD Count"],
                "Roster Avg Speed": summ_a["Avg SPD"],
                "Roster Avg Overall": summ_a["Avg OVR"],
                "Best Player Overall": summ_a["Top OVR"],
                "Players 90+ Overall": summ_a["90+ OVR Count"],
                "Roster Avg Awareness": summ_a["Avg AWR"],
                "Roster Avg Agility": summ_a["Avg AGI"],
            },
            team_b: {
                "Players 90+ Speed": summ_b["90+ SPD Count"],
                "Roster Avg Speed": summ_b["Avg SPD"],
                "Roster Avg Overall": summ_b["Avg OVR"],
                "Best Player Overall": summ_b["Top OVR"],
                "Players 90+ Overall": summ_b["90+ OVR Count"],
                "Roster Avg Awareness": summ_b["Avg AWR"],
                "Roster Avg Agility": summ_b["Avg AGI"],
            }
        }

        render_team_athletic_profile_plotly(team_metric_map)

        

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
        st.caption("Score drop when each group's best player is removed. 🟢 Solid depth  🟡 Some risk 🔴 One injury from disaster.")

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
        st.markdown(
            f"<div style='color:#9ca3af; font-size:0.875rem; margin-top:-6px; margin-bottom:8px;'>"
            f"Class distribution with redshirt-aware eligibility. "
            f"{get_redshirt_logo_html(width=16, margin='0 4px -3px 4px')} = currently redshirting."
            f"</div>",
            unsafe_allow_html=True
        )

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
        st.markdown(
            f"#### {get_redshirt_logo_html(width=18, margin='0 6px -3px 0')} Redshirt Inventory",
            unsafe_allow_html=True
        )
        st.caption("Redshirts = players who gained a year in the program without burning eligibility. These players have more development than their class label suggests.")
        rs_a = roster_a[roster_a['IsRS']].sort_values("OVR", ascending=False)[["Name", "Pos", "ExpTag", "OVR", "SPD", "FV"]].reset_index(drop=True)
        rs_b = roster_b[roster_b['IsRS']].sort_values("OVR", ascending=False)[["Name", "Pos", "ExpTag", "OVR", "SPD", "FV"]].reset_index(drop=True)
        rc1, rc2 = st.columns(2)
        with rc1:
            st.markdown(
                f"<span style='color:{color_a};font-weight:800;'>{team_a} — "
                f"{get_redshirt_logo_html(width=16, margin='0 4px -3px 4px')} {len(rs_a)} redshirts</span>",
                unsafe_allow_html=True
            )
            if not rs_a.empty:
                st.dataframe(rs_a.rename(columns={"ExpTag": "Status", "FV": "FV Score"}), hide_index=True, use_container_width=True)
            else:
                st.caption("No redshirts.")
        with rc2:
            st.markdown(
                f"<span style='color:{color_b};font-weight:800;'>{team_b} — "
                f"{get_redshirt_logo_html(width=16, margin='0 4px -3px 4px')} {len(rs_b)} redshirts</span>",
                unsafe_allow_html=True
            )
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


# ── AUTO-SYNC: Derive CFP/natty stats and write back to CSVs ─────────────────
def sync_derived_stats():
    """
    Auto-derives and writes back the following fields:
      UserDraftPicks.csv  → CFP Wins, CFP Losses, National Titles, National Title Appearances
      coach_records.csv   → CareerWins, CareerLosses, CareerWinPct, PlayoffWins,
                            PlayoffLosses, PlayoffWinPct, NationalTitles, ConferenceTitles

    Fields intentionally left manual:
      Career Wins/Losses, Conference Titles, Guys Sent to NFL, 1st Rounders
    """
    import os as _os
    import pandas as _pd

    msgs = []

    # ── 1. Load source files ─────────────────────────────────────────────────
    try:
        cfp = _pd.read_csv("CFPbracketresults.csv")
        scores_raw = _pd.read_csv("CPUscores_MASTER.csv")
        champs_raw = _pd.read_csv("champs.csv")
    except Exception as e:
        return False, [f"❌ Could not load source CSVs: {e}"]

    # ── 2. Build user → team lookup across all years ─────────────────────────
    scores_raw["YEAR"] = _pd.to_numeric(scores_raw["YEAR"], errors="coerce")
    user_teams_all = {}   # user -> set of all teams they've ever controlled
    for _, row in scores_raw.iterrows():
        for u_col, t_col in [("Vis_User", "Visitor"), ("Home_User", "Home")]:
            u = str(row.get(u_col, "")).strip().title()
            t = str(row.get(t_col, "")).strip()
            if u and u.upper() != "CPU" and u.lower() not in ("nan", ""):
                user_teams_all.setdefault(u, set()).add(t.lower())

    # ── 3. Derive CFP stats from CFPbracketresults.csv ───────────────────────
    cfp_done = cfp[cfp["COMPLETED"] == 1].copy()
    ncg = cfp_done[cfp_done["ROUND"].str.upper() == "NCG"]

    def _cfp_stats(user):
        teams = user_teams_all.get(user, set())
        wins = losses = natty_titles = natty_apps = 0
        for _, row in cfp_done.iterrows():
            w = str(row["WINNER"]).strip().lower()
            l = str(row["LOSER"]).strip().lower()
            if w in teams:
                wins += 1
            if l in teams:
                losses += 1
        for _, row in ncg.iterrows():
            t1 = str(row["TEAM1"]).strip().lower()
            t2 = str(row["TEAM2"]).strip().lower()
            w  = str(row["WINNER"]).strip().lower()
            if t1 in teams or t2 in teams:
                natty_apps += 1
                if w in teams:
                    natty_titles += 1
        return wins, losses, natty_titles, natty_apps

    # Also derive natty titles from champs.csv (more reliable source)
    champs_raw["user"] = champs_raw["user"].astype(str).str.strip().str.title()
    champs_user_counts = (
        champs_raw[champs_raw["user"].str.upper() != "CPU"]["user"]
        .value_counts()
        .to_dict()
    )

    # ── 4. Update UserDraftPicks.csv ─────────────────────────────────────────
    udp_path = "UserDraftPicks.csv"
    try:
        udp = _pd.read_csv(udp_path)
    except Exception as e:
        return False, [f"❌ Could not read UserDraftPicks.csv: {e}"]

    udp["USER"] = udp["USER"].astype(str).str.strip().str.title()

    changed_udp = 0
    for i, row in udp.iterrows():
        u = row["USER"]
        cfp_w, cfp_l, _, natty_apps = _cfp_stats(u)
        natty_titles = champs_user_counts.get(u, 0)

        updates = {
            "CFP Wins":                    cfp_w,
            "CFP Losses":                  cfp_l,
            "National Titles":             natty_titles,
            "National Title Appearances":  natty_apps,
        }
        for col, val in updates.items():
            if col in udp.columns and int(udp.at[i, col]) != int(val):
                udp.at[i, col] = int(val)
                changed_udp += 1

    try:
        udp.to_csv(udp_path, index=False)
        msgs.append(f"✅ UserDraftPicks.csv — {changed_udp} field(s) updated")
    except Exception as e:
        msgs.append(f"❌ Could not write UserDraftPicks.csv: {e}")

    # ── 5. Update coach_records.csv ──────────────────────────────────────────
    cr_path = "coach_records.csv"
    if not _os.path.exists(cr_path):
        msgs.append("⚠️ coach_records.csv not found — skipping coach sync")
    else:
        try:
            cr = _pd.read_csv(cr_path)
        except Exception as e:
            msgs.append(f"❌ Could not read coach_records.csv: {e}")
            cr = None

        if cr is not None:
            cr["User"] = cr["User"].astype(str).str.strip().str.title()
            changed_cr = 0

            # Re-read freshly written UDPs
            udp_fresh = _pd.read_csv(udp_path)
            udp_fresh["USER"] = udp_fresh["USER"].astype(str).str.strip().str.title()

            for i, row in cr.iterrows():
                u = str(row["User"]).strip().title()
                udp_row = udp_fresh[udp_fresh["USER"] == u]
                if udp_row.empty:
                    continue
                ur = udp_row.iloc[0]

                cw  = int(safe_num(ur.get("Career Wins",  0), 0))
                cl  = int(safe_num(ur.get("Career Losses", 0), 0))
                pw  = int(safe_num(ur.get("CFP Wins",   0), 0))
                pl  = int(safe_num(ur.get("CFP Losses", 0), 0))
                nt  = int(safe_num(ur.get("National Titles", 0), 0))
                ct  = int(safe_num(ur.get("Conference Titles", 0), 0))
                cwp = round(cw / max(1, cw + cl), 3)
                pwp = round(pw / max(1, pw + pl), 3)

                sync_map = {
                    "CareerWins":       cw,
                    "CareerLosses":     cl,
                    "CareerWinPct":     cwp,
                    "PlayoffWins":      pw,
                    "PlayoffLosses":    pl,
                    "PlayoffWinPct":    pwp,
                    "NationalTitles":   nt,
                    "ConferenceTitles": ct,
                }
                for col, val in sync_map.items():
                    if col in cr.columns:
                        old = cr.at[i, col]
                        try:
                            if round(float(old), 3) != round(float(val), 3):
                                cr.at[i, col] = val
                                changed_cr += 1
                        except Exception:
                            cr.at[i, col] = val
                            changed_cr += 1

            try:
                cr.to_csv(cr_path, index=False)
                msgs.append(f"✅ coach_records.csv — {changed_cr} field(s) updated")
            except Exception as e:
                msgs.append(f"❌ Could not write coach_records.csv: {e}")

    return True, msgs


@st.cache_data(ttl=300)
def load_data(current_year=CURRENT_YEAR):
    try:
        # LOAD ALL CORE FILES
        scores = pd.read_csv('CPUscores_MASTER.csv')
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
        r_2041 = ratings[ratings['YEAR'] == current_year].copy()
        r_2040 = ratings[ratings['YEAR'] == current_year - 1].copy()
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
            'OVERALL', 'OFFENSE', 'DEFENSE', 'QB OVR'
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


def get_recent_recruiting_score(rec_df, user, team=None, current_year=None, lookback=3):
    if current_year is None:
        current_year = CURRENT_YEAR
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
        <td class="isp-td-pin">
          <div class="isp-flex-row">
            <div style="font-weight:800;min-width:24px;text-align:center;color:#e5e7eb;">#{int(row.get('Projected Seed Display', 0))}</div>
            <div class="isp-td-num">{logo_html}</div>
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
    <div class="isp-table-wrap">
      <table class="isp-table">
        <thead>
          <tr class="isp-tr-header">
            <th class="isp-th isp-th-left">Top 25 Snapshot</th>
            <th class="isp-th">Total</th>
            <th class="isp-th">5★</th>
            <th class="isp-th">4★</th>
            <th class="isp-th">3★</th>
            <th class="isp-th">Points</th>
            <th class="isp-th">Blue Chip Ratio</th>
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

    # Zero-fill speed cols — no longer in TeamRatingsHistory.csv.
    # Live roster enrichment overwrites these after this function returns.
    # They must exist here so scoring formulas don't KeyError.
    for _spd_col in [
        'Team Speed (90+ Speed Guys)',
        'Quad 90 (90+ SPD, ACC, AGI & COD)',
        'Generational (96+ speed or 96+ Acceleration)',
        'Off Speed (90+ speed)',
        'Def Speed (90+ speed)',
        'Monsters',
        'Quick Hogs',
        'Cheat Codes',
        'Current CFP Ranking',
        'Current Record Wins',
        'Current Record Losses',
        'Combined Opponent Wins',
        'Combined Opponent Losses',
    ]:
        if _spd_col not in df.columns:
            df[_spd_col] = 0
        df[_spd_col] = pd.to_numeric(df[_spd_col], errors='coerce').fillna(0)

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


def _recent_recruit_window(row, anchor_year=None, lookback=4):
    if anchor_year is None:
        anchor_year = CURRENT_YEAR
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


def build_recruiting_board(rec_df, model_df, anchor_year=None):
    if anchor_year is None:
        anchor_year = CURRENT_YEAR
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
          <div class="isp-flex-row">
            <div style="font-weight:800;min-width:24px;text-align:center;">#{int(row.get('Projected Seed Display', 0))}</div>
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
      <table class="isp-table">
        <thead>
          <tr style="background:#f8fafc;color:#111827;">
            <th class="isp-th-light isp-th-left">Recruiting Board</th>
            <th class="isp-th-light">Recent Classes</th>
            <th class="isp-th-light">Weighted Avg Rank</th>
            <th class="isp-th-light">Heat Index</th>
            <th class="isp-th-light">Pipeline Score</th>
            <th class="isp-th-light">Speed Recruiter</th>
            <th class="isp-th-light">Blue Chip</th>
            <th class="isp-th-light">Class Tier</th>
            <th class="isp-th-light">Trajectory</th>
            <th class="isp-th-light">Notes</th>
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


def _load_recruiting_csv(filename=None):
    """
    Load recruiting history. Always tries recruiting_class_history_all.csv first
    (single source of truth). Falls back to the supplied filename only if the
    primary file is missing or empty.
    """
    _std_cols = ['Year','ClassType','Rank','Team','User','TotalCommits','FiveStar','FourStar',
                 'ThreeStar','TwoStar','OneStar','Points']

    def _read_and_clean(path):
        df = pd.read_csv(path)
        df.columns = [c.strip() for c in df.columns]
        for c in ['Rank','TotalCommits','FiveStar','FourStar','ThreeStar','TwoStar','OneStar','Year']:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int)
        if 'Points' in df.columns:
            df['Points'] = pd.to_numeric(df['Points'], errors='coerce').fillna(0.0)
        if 'ClassType' not in df.columns:
            df['ClassType'] = 'OVERALL'
        return df

    # Always try the primary file first
    try:
        df = _read_and_clean('recruiting_class_history_all.csv')
        if not df.empty:
            return df
    except Exception:
        pass

    # Fall back to the supplied filename if provided
    if filename and filename != 'recruiting_class_history_all.csv':
        try:
            df = _read_and_clean(filename)
            if not df.empty:
                return df
        except Exception:
            pass

    return pd.DataFrame(columns=_std_cols)


def _recruiting_snapshot(class_type, year=None, fallback_file=None):
    """
    Shared helper: reads recruiting_class_history_all.csv, filters by ClassType,
    computes BlueChipRatio and Logo, and returns sorted by Rank.
    Falls back to fallback_file if the primary has no matching rows.
    """
    _user_team_map = {
        'Devin': ['Bowling Green','Hammond'],
        'Mike':  ['San Jose State','Rapid City','Wyoming','Maryland'],
        'Josh':  ['USF','Georgia','Panama City'],
        'Noah':  ['Texas Tech','Alabaster'],
        'Doug':  ['Florida','Death Valley','UTSA'],
        'Nick':  ['Florida State','Nebraska','Gate City'],
    }

    df = _load_recruiting_csv(fallback_file)

    if df.empty:
        return pd.DataFrame()

    # Filter to the requested class type
    if 'ClassType' in df.columns and class_type:
        df = df[df['ClassType'].str.upper() == class_type.upper()].copy()

    if df.empty:
        return pd.DataFrame()

    # Year filter
    if 'Year' in df.columns:
        yr = int(year) if year else int(df['Year'].max())
        df = df[df['Year'] == yr].copy()

    if df.empty:
        return pd.DataFrame()

    # Fill User from team map if missing
    if 'User' not in df.columns:
        df['User'] = ''
    if df['User'].isna().all() or (df['User'].astype(str).str.strip() == '').all():
        df['User'] = ''
        for usr, teams in _user_team_map.items():
            df.loc[df['Team'].isin(teams), 'User'] = usr

    # Numeric hygiene
    for col in ['FiveStar','FourStar','TotalCommits']:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    if 'Rank' not in df.columns:
        df['Rank'] = np.nan
    df['Rank'] = pd.to_numeric(df['Rank'], errors='coerce')

    df['BlueChipRatio'] = (
        (df['FiveStar'] + df['FourStar']) / df['TotalCommits'].replace(0, np.nan)
    ).fillna(0).round(3)

    if 'Team' not in df.columns:
        df['Team'] = ''
    df['Logo'] = df['Team'].apply(get_logo_source)

    return df.sort_values('Rank', na_position='last').reset_index(drop=True)


def get_hs_recruiting_snapshot(year=None):
    """HS recruiting class — reads from recruiting_class_history_all.csv (ClassType=HS)."""
    return _recruiting_snapshot('HS', year=year, fallback_file='recruiting_high_school_history.csv')


def get_portal_recruiting_snapshot(year=None):
    """Transfer portal class — reads from recruiting_class_history_all.csv (ClassType=TRANSFER)."""
    return _recruiting_snapshot('TRANSFER', year=year, fallback_file='recruiting_transfer_portal_history.csv')


def get_overall_recruiting_snapshot(year=None):
    """Overall recruiting class — reads from recruiting_class_history_all.csv (ClassType=OVERALL)."""
    return _recruiting_snapshot('OVERALL', year=year, fallback_file='recruiting_overall_history.csv')


def get_current_recruiting_snapshot():
    """Legacy shim used elsewhere in the app — returns top-25 HS snapshot."""
    df = get_hs_recruiting_snapshot()
    df = df.rename(columns={
        'TotalCommits': 'Total', 'FiveStar': '5★', 'FourStar': '4★',
        'ThreeStar': '3★', 'TwoStar': '2★', 'OneStar': '1★',
        'BlueChipRatio': 'Blue Chip Ratio',
    })
    return df.head(25)


def build_ispn_classics(scores_df, ratings_df):
    """
    Returns a DataFrame of the most iconic games in dynasty history.
    Blends closeness (low margin) + stakes (game type) + upset factor (OVR delta).
    Each row includes all context needed to render a broadcast-style card.
    """
    if scores_df is None or scores_df.empty:
        return pd.DataFrame()

    # Build team OVR lookup: (team, year) -> OVR
    _ovr = {}
    if ratings_df is not None and not ratings_df.empty:
        for _, _r in ratings_df.iterrows():
            try:
                _ovr[(str(_r['TEAM']).strip(), int(_r['YEAR']))] = float(_r.get('OVERALL', 75))
            except Exception:
                pass

    def _get_ovr(team, year):
        t = str(team).strip()
        v = _ovr.get((t, year))
        if v is None:
            v = _ovr.get((t, year - 1))
        return float(v) if v is not None else 75.0

    rows = []
    for _, g in scores_df.iterrows():
        try:
            yr   = int(g.get('YEAR', 0))
            vis  = str(g.get('Visitor_Final', g.get('Visitor', ''))).strip()
            hom  = str(g.get('Home_Final',    g.get('Home', ''))).strip()
            vpts = int(g.get('V_Pts', g.get('Vis Score', 0)))
            hpts = int(g.get('H_Pts', g.get('Home Score', 0)))
            vu   = str(g.get('V_User_Final', g.get('Vis_User', ''))).strip()
            hu   = str(g.get('H_User_Final', g.get('Home_User', ''))).strip()
            margin = abs(vpts - hpts)
            vis_won = vpts > hpts
            winner      = vis if vis_won else hom
            loser       = hom if vis_won else vis
            winner_user = vu  if vis_won else hu
            loser_user  = hu  if vis_won else vu
            winner_pts  = vpts if vis_won else hpts
            loser_pts   = hpts if vis_won else vpts

            # Game type
            def _flag_yes(v):
                _s = str(v).strip().lower()
                return _s in {'yes', 'true', '1', 'y'}

            _nat = g.get('Natty Game', 'NO')
            _cfp = g.get('CFP', 'No')
            _cft = g.get('Conf Title', 'No')
            _bwl = g.get('Bowl', 'No')

            if _flag_yes(_nat):
                gtype = 'National Championship'
                gtype_weight = 20
            elif _flag_yes(_cfp):
                gtype = 'CFP Playoff'
                gtype_weight = 12
            elif _flag_yes(_cft):
                gtype = 'Conf Title'
                gtype_weight = 8
            elif _flag_yes(_bwl):
                gtype = 'Bowl Game'
                gtype_weight = 4
            else:
                gtype = 'Regular Season'
                gtype_weight = 0

            # OVR delta — positive means underdog won
            w_ovr = _get_ovr(winner, yr)
            l_ovr = _get_ovr(loser, yr)
            ovr_diff = round(l_ovr - w_ovr, 1)   # positive = underdog won
            is_upset = ovr_diff >= 3.0

            # Classic score: closeness is the main driver, stakes + upset are bonuses
            closeness = max(0, 35 - margin)       # max 35 for OT thriller
            classic_score = closeness + gtype_weight + max(0, ovr_diff * 0.6)
            classic_score = round(classic_score, 1)

            rows.append({
                'Year': yr, 'Visitor': vis, 'VisPts': vpts,
                'HomePts': hpts, 'Home': hom,
                'VisUser': vu, 'HomeUser': hu,
                'Margin': margin, 'Winner': winner, 'Loser': loser,
                'WinnerUser': winner_user, 'LoserUser': loser_user,
                'WinnerPts': winner_pts, 'LoserPts': loser_pts,
                'WinnerOVR': w_ovr, 'LoserOVR': l_ovr,
                'OVR_Diff': ovr_diff, 'IsUpset': is_upset,
                'GameType': gtype, 'ClassicScore': classic_score,
            })
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).sort_values('ClassicScore', ascending=False).reset_index(drop=True)
    return df


def get_cfp_rankings_snapshot():
    """
    Always pulls from cfp_rankings_history.csv using the most recent YEAR+WEEK.
    CSV-first behavior: if the file is missing or empty, return an empty DataFrame.
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

                def parse_wl(rec):
                    try:
                        parts = str(rec).split('-')
                        return int(parts[0]), int(parts[1])
                    except Exception:
                        return 0, 0

                snap['Wins'] = snap['Record'].apply(lambda r: parse_wl(r)[0])
                snap['Losses'] = snap['Record'].apply(lambda r: parse_wl(r)[1])
                snap['Logo'] = snap['Team'].apply(get_logo_source)
                return snap[['Rank', 'Team', 'Wins', 'Losses', 'Record', 'Logo']]
    except Exception:
        pass

    return pd.DataFrame(columns=['Rank', 'Team', 'Wins', 'Losses', 'Record', 'Logo'])

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


def resolve_playoff_bracket_results(bracket_field, year):
    """Resolve actual CFP bracket winners from CPUscores_MASTER.csv for a locked bracket.
    Matches completed games by the official 12-team field and advances winners round by round.
    Returns a dict of actual game winners/participants that render_playoff_bracket can display.
    """
    result = {
        'r1_winners': {}, 'qf_winners': {}, 'sf_winners': {},
        'qf_slots': {}, 'sf_slots': {}, 'nat_slots': {},
        'r1_games': {}, 'qf_games': {}, 'sf_games': {}, 'nat_game': None
    }
    try:
        if bracket_field is None or bracket_field.empty:
            return result

        games = pd.DataFrame()
        week_col = None

        # Preferred source: explicit CFP bracket results CSV
        try:
            cfp_res = pd.read_csv('CFPbracketresults.csv')
            if not cfp_res.empty:
                year_col = smart_col(cfp_res, ['YEAR', 'Year'])
                team1_col = smart_col(cfp_res, ['TEAM1', 'Team1', 'Away', 'Visitor'])
                team2_col = smart_col(cfp_res, ['TEAM2', 'Team2', 'Home'])
                score1_col = smart_col(cfp_res, ['TEAM1_SCORE', 'Team1 Score', 'Away Score', 'Vis Score'])
                score2_col = smart_col(cfp_res, ['TEAM2_SCORE', 'Team2 Score', 'Home Score'])
                week_col = smart_col(cfp_res, ['ROUND', 'Week', 'WEEK', 'GAME_ID'])
                completed_col = smart_col(cfp_res, ['COMPLETED', 'Completed'])
                if all([year_col, team1_col, team2_col, score1_col, score2_col]):
                    games = cfp_res.copy()
                    games[year_col] = pd.to_numeric(games[year_col], errors='coerce')
                    games = games[games[year_col] == int(year)].copy()
                    if completed_col and completed_col in games.columns:
                        games = games[pd.to_numeric(games[completed_col], errors='coerce').fillna(0).astype(int) == 1].copy()
                    games['_away_team'] = games[team1_col].astype(str).str.strip()
                    games['_home_team'] = games[team2_col].astype(str).str.strip()
                    games['_away_norm'] = games['_away_team'].apply(normalize_key)
                    games['_home_norm'] = games['_home_team'].apply(normalize_key)
                    games['_away_score'] = pd.to_numeric(games[score1_col], errors='coerce')
                    games['_home_score'] = pd.to_numeric(games[score2_col], errors='coerce')
                    games = games.dropna(subset=['_away_score', '_home_score']).copy()
        except Exception:
            games = pd.DataFrame()

        # Fallback source: CPUscores_MASTER.csv
        if games.empty:
            try:
                cpu = pd.read_csv('CPUscores_MASTER.csv')
                if cpu.empty:
                    return result
                year_col = smart_col(cpu, ['YEAR', 'Year'])
                away_team_col = smart_col(cpu, ['Visitor', 'Away', 'Away Team', 'VISITOR', 'AWAY'])
                home_team_col = smart_col(cpu, ['Home', 'Home Team', 'HOME'])
                away_score_col = smart_col(cpu, ['Vis Score', 'Visitor Score', 'Away Score', 'Vis_Score', 'Away_Score', 'Visitor_Score'])
                home_score_col = smart_col(cpu, ['Home Score', 'Home_Score', 'HomeScore'])
                week_col = smart_col(cpu, ['WEEK', 'Week'])
                if not all([year_col, away_team_col, home_team_col, away_score_col, home_score_col]):
                    return result
                games = cpu.copy()
                games[year_col] = pd.to_numeric(games[year_col], errors='coerce')
                games = games[games[year_col] == int(year)].copy()
                if games.empty:
                    return result
                games['_away_team'] = games[away_team_col].astype(str).str.strip()
                games['_home_team'] = games[home_team_col].astype(str).str.strip()
                games['_away_norm'] = games['_away_team'].apply(normalize_key)
                games['_home_norm'] = games['_home_team'].apply(normalize_key)
                games['_away_score'] = pd.to_numeric(games[away_score_col], errors='coerce')
                games['_home_score'] = pd.to_numeric(games[home_score_col], errors='coerce')
                games = games.dropna(subset=['_away_score', '_home_score']).copy()
            except Exception:
                return result

        if games.empty:
            return result

        if week_col and week_col in games.columns:
            def _week_ord(v):
                s = str(v).strip().lower()
                import re as _re
                m = _re.search(r'(\d+)', s)
                if 'national' in s or 'champ' in s or 'natty' in s or 'ncg' in s:
                    return 240
                if 'semi' in s or s == 'sf' or 'bowl week 2' in s or 'bowlweek2' in s:
                    return 230
                if 'quarter' in s or s == 'qf':
                    return 220
                if 'first round' in s or 'round 1' in s or s == 'r1':
                    return 210
                if 'playoff' in s or 'bowl week 1' in s or 'bowlweek1' in s:
                    return 205
                if 'conf' in s and 'champ' in s:
                    return 199
                return int(m.group(1)) if m else -1
            games['_week_ord'] = games[week_col].apply(_week_ord)
            games = games.sort_values(['_week_ord']).reset_index(drop=True)
        else:
            games = games.reset_index(drop=True)

        pf = bracket_field.copy()
        pf['Projected Seed'] = pd.to_numeric(pf['Projected Seed'], errors='coerce')
        pf = pf.dropna(subset=['Projected Seed']).sort_values('Projected Seed').reset_index(drop=True)
        pf['_norm'] = pf['Team'].astype(str).apply(normalize_key)
        row_by_seed = {int(r['Projected Seed']): r for _, r in pf.iterrows()}
        row_by_norm = {str(r['_norm']): r for _, r in pf.iterrows()}
        field_norms = set(row_by_norm.keys())
        games = games[games['_away_norm'].isin(field_norms) & games['_home_norm'].isin(field_norms)].copy()
        if games.empty:
            return result

        def _winner_row(g):
            if float(g['_home_score']) == float(g['_away_score']):
                return None
            win_norm = g['_home_norm'] if float(g['_home_score']) > float(g['_away_score']) else g['_away_norm']
            return row_by_norm.get(win_norm)

        def _find_game(norm_a, norm_b):
            if not norm_a or not norm_b:
                return None
            mask = ((games['_away_norm'] == norm_a) & (games['_home_norm'] == norm_b)) | ((games['_away_norm'] == norm_b) & (games['_home_norm'] == norm_a))
            hits = games[mask]
            if hits.empty:
                return None
            return hits.iloc[-1]

        def _seed_norm(seed):
            r = row_by_seed.get(seed)
            return str(r['_norm']) if r is not None else None

        # First round
        r1_map = {1: (8, 9), 4: (5, 12), 2: (7, 10), 3: (6, 11)}
        for bracket_seed, (sa, sb) in r1_map.items():
            g = _find_game(_seed_norm(sa), _seed_norm(sb))
            if g is not None:
                wr = _winner_row(g)
                if wr is not None:
                    result['r1_winners'][bracket_seed] = wr
                    result['qf_slots'][bracket_seed] = wr
                    result['r1_games'][bracket_seed] = g

        # Quarterfinals
        for bracket_seed, bye_seed in [(1, 1), (4, 4), (2, 2), (3, 3)]:
            opp = result['qf_slots'].get(bracket_seed)
            if opp is None:
                continue
            g = _find_game(_seed_norm(bye_seed), str(opp['_norm']))
            if g is not None:
                wr = _winner_row(g)
                if wr is not None:
                    result['qf_winners'][bracket_seed] = wr
                    result['qf_games'][bracket_seed] = g

        # Semifinals participants / winners
        sf_pairs = {
            1: (result['qf_winners'].get(1), result['qf_winners'].get(4)),
            2: (result['qf_winners'].get(2), result['qf_winners'].get(3)),
        }
        for sf_idx, pair in sf_pairs.items():
            a, b = pair
            if a is None or b is None:
                continue
            result['sf_slots'][sf_idx] = pair
            g = _find_game(str(a['_norm']), str(b['_norm']))
            if g is not None:
                wr = _winner_row(g)
                if wr is not None:
                    result['sf_winners'][sf_idx] = wr
                    result['sf_games'][sf_idx] = g

        # National title participants / winner
        nat_a = result['sf_winners'].get(1)
        nat_b = result['sf_winners'].get(2)
        if nat_a is not None and nat_b is not None:
            result['nat_slots'] = {1: nat_a, 2: nat_b}
            g = _find_game(str(nat_a['_norm']), str(nat_b['_norm']))
            if g is not None:
                wr = _winner_row(g)
                if wr is not None:
                    result['nat_winner'] = wr
                    result['nat_game'] = g
        return result
    except Exception:
        return result


def render_playoff_bracket(projected_field, actual_results=None):
    """Visual SVG bracket for 12-team CFP playoff with connector lines."""
    if projected_field is None or projected_field.empty or len(projected_field) < 12:
        st.info("Need 12 projected teams to render the bracket.")
        return

    actual_results = actual_results or {}
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

    def slot_svg(x, y, seed, row, bye=False, proj=False, actual=False, tbd_lines=None, w=SW, winner=False, score_text=None):
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
        name = (team[:19] + "…") if len(team) > 19 else team
        fill_op = "22" if winner else ("18" if actual else ("12" if proj else "1c"))
        opacity = "dd" if winner else ("bb" if actual else ("99" if proj else "ff"))
        stroke_color = "#fbbf24" if winner else (primary + "55")
        stroke_width = "2" if winner else "1"
        clip_id = "lc{}".format(abs(hash(team + str(y))) % 99999)
        logo_svg = ""; name_x = x + 42
        if logo_uri:
            logo_svg = (
                '<defs><clipPath id="{0}"><rect x="{1}" y="{2}" width="28" height="28" rx="4"/></clipPath></defs>'.format(clip_id, x+35, y+8) +
                '<image href="{}" x="{}" y="{}" width="28" height="28" clip-path="url(#{} )" opacity="0.9"/>'.format(logo_uri, x+35, y+8, clip_id).replace('#{} )'.format(clip_id), '#{})'.format(clip_id))
            )
            name_x = x + 70
        badge_x = x + w - 50
        badge_svg = ""
        if bye:
            badge_svg = (
                '<rect x="{}" y="{}" width="36" height="15" rx="7" fill="#14532d"/>'.format(x+w-44, y+14) +
                '<text x="{}" y="{}" text-anchor="middle" fill="#4ade80" font-size="9" font-weight="bold" font-family="monospace">BYE</text>'.format(x+w-26, y+25)
            )
        elif proj:
            badge_svg = (
                '<rect x="{}" y="{}" width="43" height="15" rx="7" fill="#1e3a5f"/>'.format(badge_x, y+14) +
                '<text x="{}" y="{}" text-anchor="middle" fill="#60a5fa" font-size="8" font-weight="bold" font-family="monospace">PROJ</text>'.format(badge_x+22, y+25)
            )
        elif actual:
            label = "WON" if winner else "FINAL"
            fill = "#14532d" if winner else "#1f2937"
            txt = "#86efac" if winner else "#cbd5e1"
            badge_svg = (
                '<rect x="{}" y="{}" width="43" height="15" rx="7" fill="{}"/>'.format(badge_x, y+14, fill) +
                '<text x="{}" y="{}" text-anchor="middle" fill="{}" font-size="8" font-weight="bold" font-family="monospace">{}</text>'.format(badge_x+22, y+25, txt, label)
            )
        score_svg = ""
        if score_text:
            score_w = 34 if len(str(score_text)) <= 2 else 42
            score_x = x + w - score_w - 10
            score_svg = (
                '<rect x="{}" y="{}" width="{}" height="16" rx="7" fill="#0b1220" stroke="{}" stroke-width="1"/>'.format(score_x, y+25, score_w, '#fbbf24' if winner else '#334155') +
                '<text x="{}" y="{}" text-anchor="middle" fill="{}" font-size="9" font-weight="bold" font-family="monospace">{}</text>'.format(score_x + score_w/2, y+36, '#f8fafc' if winner else '#cbd5e1', html.escape(str(score_text)))
            )
        return (
            '<rect x="{}" y="{}" width="{}" height="{}" rx="6" fill="{}{}" stroke="{}" stroke-width="{}"/>'.format(x, y, w, SH, primary, fill_op, stroke_color, stroke_width) +
            '<rect x="{}" y="{}" width="4" height="{}" rx="3" fill="{}{}"/>'.format(x, y, SH, primary, opacity) +
            '<circle cx="{}" cy="{}" r="13" fill="{}{}"/>'.format(x+20, y+SH//2, primary, opacity) +
            '<text x="{}" y="{}" text-anchor="middle" fill="white" font-size="11" font-weight="bold" font-family="monospace">#{}</text>'.format(x+20, y+SH//2+5, seed) +
            logo_svg +
            '<text x="{}" y="{}" fill="{}" font-size="12" font-weight="bold" font-family="monospace">{}</text>'.format(name_x, y+18, '#fde68a' if winner else primary, html.escape(name)) +
            '<text x="{}" y="{}" fill="#6b7280" font-size="10" font-family="monospace">{}</text>'.format(name_x, y+34, html.escape(record)) +
            badge_svg + score_svg
        )

    def game_team_score(game_row, team_row):
        if game_row is None or team_row is None:
            return None
        try:
            team_norm = normalize_key(str(team_row.get('Team', '')))
            away_norm = str(game_row.get('_away_norm', ''))
            home_norm = str(game_row.get('_home_norm', ''))
            if team_norm == away_norm:
                return int(game_row.get('_away_score'))
            if team_norm == home_norm:
                return int(game_row.get('_home_score'))
        except Exception:
            return None
        return None

    def game_winner_norm(game_row):
        if game_row is None:
            return None
        try:
            away_score = float(game_row.get('_away_score'))
            home_score = float(game_row.get('_home_score'))
            if away_score == home_score:
                return None
            return str(game_row.get('_away_norm')) if away_score > home_score else str(game_row.get('_home_norm'))
        except Exception:
            return None

    def row_is_winner(game_row, team_row):
        if game_row is None or team_row is None:
            return False
        return normalize_key(str(team_row.get('Team', ''))) == game_winner_norm(game_row)

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
    r1_games = actual_results.get('r1_games', {})
    qf_games = actual_results.get('qf_games', {})
    sf_games = actual_results.get('sf_games', {})
    nat_game = actual_results.get('nat_game')
    wp1=wp(8,9); wp4=wp(5,12); wp2=wp(7,10); wp3=wp(6,11)
    qf1_opp = actual_results.get('qf_slots', {}).get(1, rows[8] if wp1>50 else rows[9])
    qf4_opp = actual_results.get('qf_slots', {}).get(4, rows[5] if wp4>50 else rows[12])
    qf2_opp = actual_results.get('qf_slots', {}).get(2, rows[7] if wp2>50 else rows[10])
    qf3_opp = actual_results.get('qf_slots', {}).get(3, rows[6] if wp3>50 else rows[11])

    S = ""
    r1g = r1_games.get(1)
    S += slot_svg(R1X,r1g1[0],8,rows[8], actual=r1g is not None, winner=row_is_winner(r1g, rows[8]), score_text=game_team_score(r1g, rows[8]))
    S += slot_svg(R1X,r1g1[1],9,rows[9], actual=r1g is not None, winner=row_is_winner(r1g, rows[9]), score_text=game_team_score(r1g, rows[9]))
    r1g = r1_games.get(4)
    S += slot_svg(R1X,r1g4[0],5,rows[5], actual=r1g is not None, winner=row_is_winner(r1g, rows[5]), score_text=game_team_score(r1g, rows[5]))
    S += slot_svg(R1X,r1g4[1],12,rows[12], actual=r1g is not None, winner=row_is_winner(r1g, rows[12]), score_text=game_team_score(r1g, rows[12]))
    r1g = r1_games.get(2)
    S += slot_svg(R1X,r1g2[0],7,rows[7], actual=r1g is not None, winner=row_is_winner(r1g, rows[7]), score_text=game_team_score(r1g, rows[7]))
    S += slot_svg(R1X,r1g2[1],10,rows[10], actual=r1g is not None, winner=row_is_winner(r1g, rows[10]), score_text=game_team_score(r1g, rows[10]))
    r1g = r1_games.get(3)
    S += slot_svg(R1X,r1g3[0],6,rows[6], actual=r1g is not None, winner=row_is_winner(r1g, rows[6]), score_text=game_team_score(r1g, rows[6]))
    S += slot_svg(R1X,r1g3[1],11,rows[11], actual=r1g is not None, winner=row_is_winner(r1g, rows[11]), score_text=game_team_score(r1g, rows[11]))
    if actual_results.get('r1_winners'):
        pass
    else:
        S += wplabel(8,9,*r1g1,R1X) + wplabel(5,12,*r1g4,R1X)
        S += wplabel(7,10,*r1g2,R1X) + wplabel(6,11,*r1g3,R1X)

    qfg = qf_games.get(1)
    S += slot_svg(QFX,qf1[0],1,rows[1],bye=True, actual=qfg is not None, winner=row_is_winner(qfg, rows[1]), score_text=game_team_score(qfg, rows[1]))
    S += slot_svg(QFX,qf1[1],str(qf1_opp.get('Projected Seed', '?')) if qf1_opp is not None else '?', qf1_opp, actual=qfg is not None or (1 in actual_results.get('r1_winners', {})), proj=qfg is None and not (1 in actual_results.get('r1_winners', {})), winner=row_is_winner(qfg, qf1_opp), score_text=game_team_score(qfg, qf1_opp))
    qfg = qf_games.get(4)
    S += slot_svg(QFX,qf4[0],4,rows[4],bye=True, actual=qfg is not None, winner=row_is_winner(qfg, rows[4]), score_text=game_team_score(qfg, rows[4]))
    S += slot_svg(QFX,qf4[1],str(qf4_opp.get('Projected Seed', '?')) if qf4_opp is not None else '?', qf4_opp, actual=qfg is not None or (4 in actual_results.get('r1_winners', {})), proj=qfg is None and not (4 in actual_results.get('r1_winners', {})), winner=row_is_winner(qfg, qf4_opp), score_text=game_team_score(qfg, qf4_opp))
    qfg = qf_games.get(2)
    S += slot_svg(QFX,qf2[0],2,rows[2],bye=True, actual=qfg is not None, winner=row_is_winner(qfg, rows[2]), score_text=game_team_score(qfg, rows[2]))
    S += slot_svg(QFX,qf2[1],str(qf2_opp.get('Projected Seed', '?')) if qf2_opp is not None else '?', qf2_opp, actual=qfg is not None or (2 in actual_results.get('r1_winners', {})), proj=qfg is None and not (2 in actual_results.get('r1_winners', {})), winner=row_is_winner(qfg, qf2_opp), score_text=game_team_score(qfg, qf2_opp))
    qfg = qf_games.get(3)
    S += slot_svg(QFX,qf3[0],3,rows[3],bye=True, actual=qfg is not None, winner=row_is_winner(qfg, rows[3]), score_text=game_team_score(qfg, rows[3]))
    S += slot_svg(QFX,qf3[1],str(qf3_opp.get('Projected Seed', '?')) if qf3_opp is not None else '?', qf3_opp, actual=qfg is not None or (3 in actual_results.get('r1_winners', {})), proj=qfg is None and not (3 in actual_results.get('r1_winners', {})), winner=row_is_winner(qfg, qf3_opp), score_text=game_team_score(qfg, qf3_opp))

    sf1_top = actual_results.get('qf_winners', {}).get(1)
    sf1_bot = actual_results.get('qf_winners', {}).get(4)
    sf2_top = actual_results.get('qf_winners', {}).get(2)
    sf2_bot = actual_results.get('qf_winners', {}).get(3)
    nat_top = actual_results.get('sf_winners', {}).get(1)
    nat_bot = actual_results.get('sf_winners', {}).get(2)
    nat_winner = actual_results.get('nat_winner')

    sfg = sf_games.get(1)
    if sf1_top is not None:
        S += slot_svg(SFX,sf1[0],str(sf1_top.get('Projected Seed', '?')),sf1_top,actual=True,winner=row_is_winner(sfg, sf1_top),score_text=game_team_score(sfg, sf1_top))
    else:
        S += slot_svg(SFX,sf1[0],"?",None,tbd_lines=("SEMIFINAL 1","Winner: #1 Bracket"))
    if sf1_bot is not None:
        S += slot_svg(SFX,sf1[1],str(sf1_bot.get('Projected Seed', '?')),sf1_bot,actual=True,winner=row_is_winner(sfg, sf1_bot),score_text=game_team_score(sfg, sf1_bot))
    else:
        S += slot_svg(SFX,sf1[1],"?",None,tbd_lines=("SEMIFINAL 1","Winner: #4 Bracket"))

    sfg = sf_games.get(2)
    if sf2_top is not None:
        S += slot_svg(SFX,sf2[0],str(sf2_top.get('Projected Seed', '?')),sf2_top,actual=True,winner=row_is_winner(sfg, sf2_top),score_text=game_team_score(sfg, sf2_top))
    else:
        S += slot_svg(SFX,sf2[0],"?",None,tbd_lines=("SEMIFINAL 2","Winner: #2 Bracket"))
    if sf2_bot is not None:
        S += slot_svg(SFX,sf2[1],str(sf2_bot.get('Projected Seed', '?')),sf2_bot,actual=True,winner=row_is_winner(sfg, sf2_bot),score_text=game_team_score(sfg, sf2_bot))
    else:
        S += slot_svg(SFX,sf2[1],"?",None,tbd_lines=("SEMIFINAL 2","Winner: #3 Bracket"))

    if nat_top is not None:
        S += slot_svg(NX, nat[0], str(nat_top.get('Projected Seed', '?')), nat_top, actual=True, w=NW, winner=row_is_winner(nat_game, nat_top), score_text=game_team_score(nat_game, nat_top))
    else:
        S += slot_svg(NX, nat[0], "?", None, tbd_lines=("NATIONAL CHAMPIONSHIP", "Winner: Semifinal 1"), w=NW)

    if nat_bot is not None:
        S += slot_svg(NX, nat[1], str(nat_bot.get('Projected Seed', '?')), nat_bot, actual=True, w=NW, winner=row_is_winner(nat_game, nat_bot), score_text=game_team_score(nat_game, nat_bot))
    else:
        S += slot_svg(NX, nat[1], "?", None, tbd_lines=("NATIONAL CHAMPIONSHIP", "Winner: Semifinal 2"), w=NW)

    if nat_winner is not None:
        first_nat = nat[0] if nat and len(nat) > 0 else 94
        champ_y = max(38, first_nat - 56)
        S += slot_svg(NX, champ_y, str(nat_winner.get('Projected Seed', '?')), nat_winner, actual=True, winner=True, score_text=game_team_score(nat_game, nat_winner), w=NW)

    divider = '<line x1="{}" y1="{}" x2="{}" y2="{}" stroke="#1a2a3a" stroke-width="1" stroke-dasharray="4,8"/>'.format(
        SFX - 10, NC, NX + NW + 10, NC
    )

    svg = (
        '<div style="overflow-x:auto;overflow-y:hidden;-webkit-overflow-scrolling:touch;border-radius:12px;background:#060e1a;padding:8px;">'
        + '<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg" style="display:block;min-width:{W}px;">'.format(W=W, H=H)
        + '<rect width="{}" height="{}" fill="#060e1a"/>'.format(W, H)
        + tracks + hdr + conn_svg + divider + S
        + "</svg></div>"
    )

    st.markdown(svg, unsafe_allow_html=True)

    nat_actual = actual_results.get('nat_winner', None)
    r1_actual = actual_results.get('r1_winners', None)
    qf_actual = actual_results.get('qf_winners', None)
    sf_actual = actual_results.get('sf_winners', None)

    def has_actual_data(x):
        if x is None:
            return False
        if isinstance(x, pd.DataFrame):
            return not x.empty
        if isinstance(x, pd.Series):
            return not x.empty
        if isinstance(x, (list, tuple, set, dict)):
            return len(x) > 0
        return True

    if has_actual_data(nat_actual):
        st.caption("🟩 FINAL = actual playoff advancement from CPUscores_MASTER.csv · bracket locked to official seeds")
    elif has_actual_data(r1_actual) or has_actual_data(qf_actual) or has_actual_data(sf_actual):
        st.caption("🟩 FINAL = actual playoff advancement from CPUscores_MASTER.csv · remaining open rounds stay projected/placeholders")
    else:
        st.caption("🟦 PROJ = projected R1 winner · lock the bracket and post playoff scores to CPUscores_MASTER.csv to auto-advance rounds")


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
                <div style='font-weight:800;min-width:20px;text-align:center;'>#{int(row.get('Projected Seed Display', 0))}</div>
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

data = load_data(current_year=CURRENT_YEAR)

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

    # ── Enrich model_2041 with QB profile CSV data ─────────────────────────────
    try:
        _qb_enrich = pd.read_csv('QBprofileData.csv')
        _qb_enrich['User'] = _qb_enrich['User'].astype(str).str.strip().str.title()
        _qb_enrich['Team'] = _qb_enrich['Team'].astype(str).str.strip()

        # Filter to current season — prevents duplicates when multiple years exist
        if 'Year' in _qb_enrich.columns:
            _qb_enrich['Year'] = pd.to_numeric(_qb_enrich['Year'], errors='coerce')
            _years_available = _qb_enrich['Year'].dropna().unique()
            _target_year = CURRENT_YEAR if CURRENT_YEAR in _years_available else (
                int(_years_available.max()) if len(_years_available) > 0 else CURRENT_YEAR
            )
            _qb_enrich = _qb_enrich[_qb_enrich['Year'] == _target_year].copy()

        _qb_cols = ['User', 'Player', 'Archetype', 'OVR', 'Class', 'StarRating',
                    'Height', 'Weight', 'Hometown', 'Pipeline', 'Mentals', 'Physicals']
        _qb_enrich = _qb_enrich[[c for c in _qb_cols if c in _qb_enrich.columns]].copy()
        _qb_enrich = _qb_enrich.rename(columns={
            'Player': 'QB_Player', 'Archetype': 'QB_Archetype',
            'OVR': 'QB_OVR_CSV', 'Class': 'QB_Class', 'StarRating': 'QB_Stars',
            'Height': 'QB_Height', 'Weight': 'QB_Weight', 'Hometown': 'QB_Hometown',
            'Pipeline': 'QB_Pipeline', 'Mentals': 'QB_Mentals', 'Physicals': 'QB_Physicals',
        })
        model_2041 = model_2041.merge(_qb_enrich.rename(columns={'User': 'USER'}),
                                      on='USER', how='left')
    except Exception:
        pass

    try:
        _qb_rank_enrich = pd.read_csv('QB_power_rankingsData.csv')
        _qb_rank_enrich['User'] = _qb_rank_enrich['User'].astype(str).str.strip().str.title()
        _qb_rank_enrich = _qb_rank_enrich[['User', 'Rank']].rename(
            columns={'User': 'USER', 'Rank': 'QB_Dynasty_Rank'})
        model_2041 = model_2041.merge(_qb_rank_enrich, on='USER', how='left')
    except Exception:
        pass

    # ── Enrich model_2041 with live roster speed counts ───────────────────────
    # Replaces TeamRatingsHistory speed cols — single source of truth is the roster CSV.
    try:
        _roster_raw = pd.read_csv('cfb26_rosters_full.csv')
        # Filter to current season if Season column exists
        if 'Season' in _roster_raw.columns:
            _roster_raw['Season'] = pd.to_numeric(_roster_raw['Season'], errors='coerce')
            _seasons_avail = _roster_raw['Season'].dropna().unique()
            _roster_season = CURRENT_YEAR if CURRENT_YEAR in _seasons_avail else int(_seasons_avail.max())
            _roster_raw = _roster_raw[_roster_raw['Season'] == _roster_season].copy()

        for _c in ['SPD','ACC','AGI','COD','STR']:
            _roster_raw[_c] = pd.to_numeric(_roster_raw.get(_c), errors='coerce').fillna(0)
        _roster_raw['REDSHIRT'] = pd.to_numeric(_roster_raw.get('REDSHIRT', 0), errors='coerce').fillna(0).astype(int)
        _roster_raw['PosNorm'] = _roster_raw.get('Pos', pd.Series(dtype=str)).astype(str).str.upper().str.strip()
        _active_r = _roster_raw.copy()  # REDSHIRT filter removed — tracked per team separately

        _front7  = {'DT','LEDG','REDG','SAM','MIKE','WILL'}
        _ol_pos  = {'LT','LG','C','RG','RT'}
        _off_pos = {'QB','HB','RB','FB','WR','TE','LT','LG','C','RG','RT'}
        _def_pos = {'DT','LEDG','REDG','SAM','MIKE','WILL','CB','FS','SS','S'}

        _spd_rows = []
        for _t, _tdf in _active_r.groupby('Team'):
            _spd_rows.append({
                'TEAM': str(_t).strip(),
                'Team Speed (90+ Speed Guys)':
                    int((_tdf['SPD'] >= 90).sum()),
                'Quad 90 (90+ SPD, ACC, AGI & COD)':
                    int(((_tdf['SPD'] >= 90) & (_tdf['ACC'] >= 90) & (_tdf['AGI'] >= 90) & (_tdf['COD'] >= 90)).sum()),
                'Generational (96+ speed or 96+ Acceleration)':
                    int(((_tdf['SPD'] >= 96) | (_tdf['ACC'] >= 96)).sum()),
                'Off Speed (90+ speed)':
                    int(((_tdf['SPD'] >= 90) & (_tdf['PosNorm'].isin(_off_pos))).sum()),
                'Def Speed (90+ speed)':
                    int(((_tdf['SPD'] >= 90) & (_tdf['PosNorm'].isin(_def_pos))).sum()),
                'Monsters':
                    int((_tdf['PosNorm'].isin(_front7) & (
                        ((_tdf['ACC'] >= 90) & (_tdf['SPD'] >= 84)) |
                        ((_tdf['SPD'] >= 90) & (_tdf['ACC'] >= 84))
                    )).sum()),
                'Quick Hogs':
                    int((_tdf['PosNorm'].isin(_ol_pos) & (_tdf['AGI'] >= 85) & (_tdf['STR'] >= 90)).sum()),
            })

        _spd_df = pd.DataFrame(_spd_rows)
        if not _spd_df.empty:
            _drop_spd = [c for c in [
                'Team Speed (90+ Speed Guys)', 'Quad 90 (90+ SPD, ACC, AGI & COD)',
                'Generational (96+ speed or 96+ Acceleration)',
                'Off Speed (90+ speed)', 'Def Speed (90+ speed)',
                'Monsters', 'Quick Hogs',
            ] if c in model_2041.columns]
            model_2041 = model_2041.drop(columns=_drop_spd, errors='ignore').merge(
                _spd_df, on='TEAM', how='left'
            )
            for _sc in ['Team Speed (90+ Speed Guys)', 'Quad 90 (90+ SPD, ACC, AGI & COD)',
                        'Generational (96+ speed or 96+ Acceleration)',
                        'Off Speed (90+ speed)', 'Def Speed (90+ speed)',
                        'Monsters', 'Quick Hogs']:
                model_2041[_sc] = pd.to_numeric(model_2041[_sc], errors='coerce').fillna(0)

            # Alias: Quad 90 guys are also called Cheat Codes
            model_2041['Cheat Codes'] = model_2041['Quad 90 (90+ SPD, ACC, AGI & COD)']
    except Exception:
        pass

    # ── Enrich model_2041 with derived season stats ───────────────────────────
    # Replaces TeamRatingsHistory: Current Record, Combined Opponent W/L, CFP Ranking
    try:
        _sc = scores[scores['YEAR'] == CURRENT_YEAR].copy() if 'YEAR' in scores.columns else pd.DataFrame()
        _sc['V_Pts'] = pd.to_numeric(_sc.get('V_Pts', _sc.get('Vis Score', 0)), errors='coerce')
        _sc['H_Pts'] = pd.to_numeric(_sc.get('H_Pts', _sc.get('Home Score', 0)), errors='coerce')
        _sc = _sc.dropna(subset=['V_Pts','H_Pts'])

        # Build full team record lookup for the season (all teams including CPU)
        _all_team_records = {}
        for _team in pd.concat([_sc['Home'], _sc['Visitor']]).dropna().unique():
            _t = str(_team).strip()
            _hg = _sc[_sc['Home'] == _t]
            _vg = _sc[_sc['Visitor'] == _t]
            _tw = len(_hg[_hg['H_Pts'] > _hg['V_Pts']]) + len(_vg[_vg['V_Pts'] > _vg['H_Pts']])
            _tl = len(_hg) + len(_vg) - _tw
            _all_team_records[_t] = (_tw, _tl)

        _season_stat_rows = []
        for _, _mrow in model_2041.iterrows():
            _t = str(_mrow.get('TEAM', '')).strip()
            _hg = _sc[_sc['Home'] == _t]
            _vg = _sc[_sc['Visitor'] == _t]
            _w = len(_hg[_hg['H_Pts'] > _hg['V_Pts']]) + len(_vg[_vg['V_Pts'] > _vg['H_Pts']])
            _l = len(_hg) + len(_vg) - _w

            # Opponents this team has faced
            _opps = list(_sc[_sc['Home'] == _t]['Visitor'].astype(str).str.strip())
            _opps += list(_sc[_sc['Visitor'] == _t]['Home'].astype(str).str.strip())
            _opp_w = sum(_all_team_records.get(_o, (0, 0))[0] for _o in _opps)
            _opp_l = sum(_all_team_records.get(_o, (0, 0))[1] for _o in _opps)

            _season_stat_rows.append({
                'TEAM': _t,
                'Current Record Wins':       _w,
                'Current Record Losses':     _l,
                'Combined Opponent Wins':    _opp_w,
                'Combined Opponent Losses':  _opp_l,
            })

        _season_stat_df = pd.DataFrame(_season_stat_rows)
        if not _season_stat_df.empty:
            _drop_ss = [c for c in ['Current Record Wins','Current Record Losses',
                                    'Combined Opponent Wins','Combined Opponent Losses']
                        if c in model_2041.columns]
            model_2041 = model_2041.drop(columns=_drop_ss, errors='ignore').merge(
                _season_stat_df, on='TEAM', how='left'
            )
    except Exception:
        pass

    # ── Enrich model_2041 with latest CFP ranking ─────────────────────────────
    try:
        _cfp_rh = pd.read_csv('cfp_rankings_history.csv')
        _cfp_rh['YEAR'] = pd.to_numeric(_cfp_rh['YEAR'], errors='coerce')
        _cfp_rh['WEEK'] = pd.to_numeric(_cfp_rh['WEEK'], errors='coerce')
        _cfp_cy = _cfp_rh[_cfp_rh['YEAR'] == CURRENT_YEAR]
        if not _cfp_cy.empty:
            _latest_wk = _cfp_cy['WEEK'].max()
            _cfp_snap = _cfp_cy[_cfp_cy['WEEK'] == _latest_wk][['TEAM','RANK']].copy()
            _cfp_snap.columns = ['TEAM','Current CFP Ranking']
            _cfp_snap['Current CFP Ranking'] = pd.to_numeric(_cfp_snap['Current CFP Ranking'], errors='coerce')
            _cfp_snap['TEAM'] = _cfp_snap['TEAM'].astype(str).str.strip()
            if 'Current CFP Ranking' in model_2041.columns:
                model_2041 = model_2041.drop(columns=['Current CFP Ranking'])
            model_2041 = model_2041.merge(_cfp_snap, on='TEAM', how='left')
    except Exception:
        pass

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

    # ── USER_TEAMS: auto-derived from team_conferences.csv ───────────────
    # Falls back to hardcoded dict only if CSV is missing or empty.
    try:
        _tc_df = pd.read_csv('team_conferences.csv')
        _tc_df['USER'] = _tc_df['USER'].astype(str).str.strip().str.title()
        _tc_df['TEAM'] = _tc_df['TEAM'].astype(str).str.strip()
        # Keep most recent entry per user (highest YEAR_JOINED)
        if 'YEAR_JOINED' in _tc_df.columns:
            _tc_df['YEAR_JOINED'] = pd.to_numeric(_tc_df['YEAR_JOINED'], errors='coerce')
            _tc_df = _tc_df.sort_values('YEAR_JOINED', ascending=False)
        USER_TEAMS = dict(zip(
            _tc_df.drop_duplicates('USER', keep='first')['USER'],
            _tc_df.drop_duplicates('USER', keep='first')['TEAM']
        ))
        if not USER_TEAMS:
            raise ValueError("Empty team_conferences.csv")
    except Exception:
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
# ════════════════════════════════════════════════════════════════════
# DYNAMIC GLOBAL HEADER (Fixed Syntax & Eastern Time)
# ════════════════════════════════════════════════════════════════════
import pytz
from datetime import datetime

# 1. ROBUST TIMEZONE LOGIC (Miramar, FL is US/Eastern)
try:
    eastern = pytz.timezone('US/Eastern')
    now_et = datetime.now(eastern)
    time_display = now_et.strftime("%-I:%M %p")
except Exception:
    time_display = "Live"

def get_header_logo(team_name):
    try:
        path = get_logo_source(team_name)
        uri = image_file_to_data_uri(path)
        if uri: return uri
        slug = TEAM_VISUALS.get(team_name, {}).get('slug', normalize_key(team_name))
        return f"https://raw.githubusercontent.com/j99p/ispn_2041/main/logos/{slug}.png"
    except Exception:
        return "https://raw.githubusercontent.com/j99p/ispn_2041/main/logos/ncaa.png"

# ════════════════════════════════════════════════════════════════════
# MULTI-HEADLINE BUILDER — pulls from all live CSVs
# Each headline: {badge, text, blurb, logo_html, priority}
# Higher priority = shown first / drives the hero card.
# ════════════════════════════════════════════════════════════════════

_all_headlines = []

# ── RANK LOOKUP (built first — used everywhere below) ─────────────────
_rank_lookup = {}   # team_name_lower -> int rank
_cfp_week_label = 0
try:
    _rl_df = pd.read_csv('cfp_rankings_history.csv')
    _rl_df['YEAR'] = pd.to_numeric(_rl_df['YEAR'], errors='coerce')
    _rl_df['WEEK'] = pd.to_numeric(_rl_df['WEEK'], errors='coerce')
    _rl_df['RANK'] = pd.to_numeric(_rl_df['RANK'], errors='coerce')
    _rl_cy = _rl_df[_rl_df['YEAR'] == CURRENT_YEAR]
    if not _rl_cy.empty:
        _cfp_week_label = int(_rl_cy['WEEK'].max())
        _rl_snap = _rl_cy[_rl_cy['WEEK'] == _cfp_week_label]
        for _, _rr in _rl_snap.iterrows():
            _rank_lookup[str(_rr['TEAM']).strip().lower()] = int(_rr['RANK'])
except Exception:
    pass

def _rk(team_name):
    """Return '#N ' prefix if ranked, else ''."""
    r = _rank_lookup.get(str(team_name).strip().lower())
    return f'#{r} ' if r else ''

def _rk_inline(team_name):
    """Return ' [#N]' suffix for ticker text if ranked, else ''."""
    r = _rank_lookup.get(str(team_name).strip().lower())
    return f' [#{r}]' if r else ''

# ── 1. PLAYOFF RESULTS (highest priority) ─────────────────────────────
try:
    if os.path.exists('CFPbracketresults.csv'):
        _b_df = pd.read_csv('CFPbracketresults.csv')
        if not _b_df.empty:
            _round_map = {'R1': 1, 'QF': 2, 'SF': 3, 'NCG': 4}
            _b_df['_rsort'] = _b_df['ROUND'].map(_round_map).fillna(0)

            _cy_games = _b_df[
                (_b_df['YEAR'] == CURRENT_YEAR) & (_b_df['COMPLETED'] == 1)
            ].copy()

            if not _cy_games.empty:
                _latest_round_sort = _cy_games['_rsort'].max()
                _cy_games = _cy_games[
                    _cy_games['_rsort'] == _latest_round_sort
                ].copy().sort_values(['GAME_ID'], ascending=True)

            for _, _gm in _cy_games.iterrows():
                t1 = str(_gm.get('TEAM1', '')).strip()
                t2 = str(_gm.get('TEAM2', '')).strip()
                s1 = pd.to_numeric(_gm.get('TEAM1_SCORE', 0), errors='coerce')
                s2 = pd.to_numeric(_gm.get('TEAM2_SCORE', 0), errors='coerce')
                raw_w = str(_gm.get('WINNER', '')).strip()
                if raw_w.lower() == t1.lower():
                    _w, _l, ws, ls = t1, t2, int(s1), int(s2)
                elif raw_w.lower() == t2.lower():
                    _w, _l, ws, ls = t2, t1, int(s2), int(s1)
                else:
                    if s1 >= s2: _w, _l, ws, ls = t1, t2, int(s1), int(s2)
                    else: _w, _l, ws, ls = t2, t1, int(s2), int(s1)
                _rd = str(_gm.get('ROUND', 'Playoffs'))
                _note = str(_gm.get('NOTES', '')).strip()
                diff = ws - ls
                if _note and _note.lower() != 'nan':
                    _blurb = _note
                elif diff >= 24: _blurb = f"{_w} delivers a statement win in the {_rd}."
                elif diff <= 3:  _blurb = f"An absolute classic. {_w} survives a {_rd} thriller."
                elif diff <= 7:  _blurb = f"{_w} holds on in a hard-fought {_rd} battle."
                else:            _blurb = f"{_w} takes care of business and advances."
                _wl = get_header_logo(_w)
                _ll = get_header_logo(_l)
                _lh = (f'<div style="display:flex;justify-content:center;align-items:center;'
                       f'gap:20px;margin-bottom:10px;">'
                       f'<img src="{_wl}" class="isp-logo-55">'
                       f'<span style="color:#94a3b8;font-weight:900;font-size:1.4rem;">VS</span>'
                       f'<img src="{_ll}" class="isp-logo-55"></div>')
                _pri = _round_map.get(_rd, 1) * 100
                # Ticker text: include ranks next to team names
                _ticker_txt = f"{_rk(_w)}{_w} {ws} \u2013 {ls} {_rk(_l)}{_l}"
                _all_headlines.append({
                    'badge': 'FINAL SCORE', 'priority': _pri,
                    'text': _ticker_txt,
                    'blurb': _blurb, 'logo_html': _lh,
                })
except Exception:
    pass

# ── 2. CFP RANKINGS SNAPSHOT (one headline, skip during active playoffs) ──
# IS_BOWL_WEEK=True means playoff is live — rankings are frozen, skip it.
if not IS_BOWL_WEEK:
    try:
        if _rank_lookup and _cfp_week_label:
            _top10_teams = sorted(_rank_lookup.items(), key=lambda x: x[1])[:10]
            _top10_str = '  ·  '.join(
                f"#{r} {t.title()}" for t, r in _top10_teams
            )
            # Find the #1 team for hero logo
            _cfp_no1_name = next((t for t, r in _top10_teams if r == 1), None)
            if _cfp_no1_name:
                _cfp_no1_proper = _cfp_no1_name.title()
                # Try to get proper-cased name from original data
                try:
                    _rl_snap2 = pd.read_csv('cfp_rankings_history.csv')
                    _rl_snap2['YEAR'] = pd.to_numeric(_rl_snap2['YEAR'], errors='coerce')
                    _rl_snap2['WEEK'] = pd.to_numeric(_rl_snap2['WEEK'], errors='coerce')
                    _rl_snap2['RANK'] = pd.to_numeric(_rl_snap2['RANK'], errors='coerce')
                    _no1_row = _rl_snap2[
                        (_rl_snap2['YEAR'] == CURRENT_YEAR) &
                        (_rl_snap2['WEEK'] == _cfp_week_label) &
                        (_rl_snap2['RANK'] == 1)
                    ]
                    if not _no1_row.empty:
                        _cfp_no1_proper = str(_no1_row.iloc[0]['TEAM']).strip()
                        _no1_rec = str(_no1_row.iloc[0].get('RECORD', '')).strip()
                        _rec_str = f" ({_no1_rec})" if _no1_rec and _no1_rec.lower() != 'nan' else ''
                except Exception:
                    _no1_rec = ''
                    _rec_str = ''
                _cfp_logo = get_header_logo(_cfp_no1_proper)
                _cfp_lh = f'<div class="isp-tc"><img src="{_cfp_logo}" class="isp-logo-60"></div>'
                _all_headlines.append({
                    'badge': 'CFP TOP 10',
                    'priority': 85,
                    'text': f"Week {_cfp_week_label} CFP Rankings: {_top10_str}",
                    'blurb': f"{_cfp_no1_proper}{_rec_str} is #1. The committee has spoken.",
                    'logo_html': _cfp_lh,
                })
    except Exception:
        pass

# ── 3. HEISMAN WATCH / LEADER THIS SEASON ─────────────────────────────
# If no winner yet this year, show the leader with season stats.
# If won already, show the winner.
_heisman_won_this_year = False
try:
    _hh_check = pd.read_csv('Heisman_History.csv')
    _hh_check['YEAR'] = pd.to_numeric(_hh_check['YEAR'], errors='coerce')

    if CURRENT_YEAR in _hh_check['YEAR'].values:
        _heisman_won_this_year = True

        _hw_rows = _hh_check[_hh_check['YEAR'] == CURRENT_YEAR].copy()
        _hw_row = _hw_rows.tail(1).iloc[0]

        _hwn = str(_hw_row.get('NAME', '')).strip()
        _hwt = str(_hw_row.get('TEAM', '')).strip()
        _hwu = str(_hw_row.get('USER', '')).strip()
        _hwp = str(_hw_row.get('POS', _hw_row.get('Position', ''))).strip()

        if _hwn and _hwn.lower() != 'nan':
            _hl = get_header_logo(_hwt)
            _lh = f'<div class="isp-tc"><img src="{_hl}" class="isp-logo-65"></div>'

            _text = f"{_hwn}"
            if _hwt and _hwp and _hwp.lower() != 'nan':
                _text += f" ({_hwt}, {_hwp}) wins the {CURRENT_YEAR} Heisman Trophy"
            elif _hwt:
                _text += f" ({_hwt}) wins the {CURRENT_YEAR} Heisman Trophy"
            else:
                _text += f" wins the {CURRENT_YEAR} Heisman Trophy"

            _blurb = f"{_hwt} ({_hwu}) takes home the hardware. The dynasty grows."
            if not _hwu or _hwu.lower() == 'nan':
                _blurb = f"{_hwt} takes home the hardware. The dynasty grows."

            if not any(
                str(h.get('badge', '')).strip() == 'HEISMAN WINNER'
                for h in _all_headlines
            ):
                _all_headlines.append({
                    'badge': 'HEISMAN WINNER',
                    'priority': 69,
                    'text': _text,
                    'blurb': _blurb,
                    'logo_html': _lh,
                })
except Exception:
    pass

if not _heisman_won_this_year and not any(
    str(h.get('badge', '')).strip() == 'HEISMAN WINNER'
    for h in _all_headlines
):
    # Show leader + their season stats from model_2041
    try:
        if not model_2041.empty and 'Heisman Player' in model_2041.columns:
            _hz = model_2041[model_2041['Heisman Player'].notna()].copy()
            for _, _hrow in _hz.iterrows():
                _hp = str(_hrow.get('Heisman Player', '')).strip()
                _hs = str(_hrow.get('Heisman Stats', '')).strip()
                _ht = str(_hrow.get('TEAM', '')).strip()
                if _hp and _hp.lower() not in ['tbd', 'nan']:
                    _hl = get_header_logo(_ht)
                    _lh = f'<div class="isp-tc"><img src="{_hl}" class="isp-logo-65"></div>'

                    _recent_game_str = ''
                    try:
                        _cpu_s = pd.read_csv('CPUscores_MASTER.csv')
                        _cpu_s['YEAR'] = pd.to_numeric(_cpu_s['YEAR'], errors='coerce')
                        _cpu_s['Week'] = pd.to_numeric(_cpu_s['Week'], errors='coerce')
                        _cpu_s['Vis Score'] = pd.to_numeric(_cpu_s['Vis Score'], errors='coerce')
                        _cpu_s['Home Score'] = pd.to_numeric(_cpu_s['Home Score'], errors='coerce')
                        _ht_lower = _ht.strip().lower()
                        _cpu_cy = _cpu_s[_cpu_s['YEAR'] == CURRENT_YEAR].copy()

                        _ht_games = _cpu_cy[
                            (_cpu_cy['Visitor'].str.strip().str.lower() == _ht_lower) |
                            (_cpu_cy['Home'].str.strip().str.lower() == _ht_lower)
                        ].dropna(subset=['Vis Score', 'Home Score'])

                        if not _ht_games.empty:
                            _last_wk = _ht_games['Week'].max()
                            _lg = _ht_games[_ht_games['Week'] == _last_wk].iloc[0]
                            _is_vis = str(_lg['Visitor']).strip().lower() == _ht_lower
                            _tm_s = int(_lg['Vis Score']) if _is_vis else int(_lg['Home Score'])
                            _op_s = int(_lg['Home Score']) if _is_vis else int(_lg['Vis Score'])
                            _opp = str(_lg['Home'] if _is_vis else _lg['Visitor']).strip()
                            _res = 'W' if _tm_s > _op_s else 'L'
                            _recent_game_str = f" | Wk {int(_last_wk)}: {_res} {_tm_s}-{_op_s} vs {_opp}"
                    except Exception:
                        pass

                    _stats_display = _hs if _hs and _hs.lower() != 'nan' else 'Season leader'
                    _all_headlines.append({
                        'badge': 'HEISMAN WATCH',
                        'priority': 70,
                        'text': f"{_hp} ({_ht}) — {_stats_display}{_recent_game_str}",
                        'blurb': "The race for the bronze statue is heating up. No winner yet.",
                        'logo_html': _lh,
                    })
                    break
    except Exception:
        pass

# ── 4. THIS WEEK'S GAMES (most recent week in CPUscores_MASTER) ────────
try:
    _wk_df = pd.read_csv('CPUscores_MASTER.csv')
    _wk_df['YEAR'] = pd.to_numeric(_wk_df['YEAR'], errors='coerce')
    _wk_df['Week'] = pd.to_numeric(_wk_df['Week'], errors='coerce')
    _wk_df['Vis Score'] = pd.to_numeric(_wk_df['Vis Score'], errors='coerce')
    _wk_df['Home Score'] = pd.to_numeric(_wk_df['Home Score'], errors='coerce')
    _wk_cy = _wk_df[_wk_df['YEAR'] == CURRENT_YEAR].copy()
    _wk_done = _wk_cy.dropna(subset=['Vis Score', 'Home Score'])
    if not _wk_done.empty:
        _latest_wk = int(_wk_done['Week'].max())
        _this_wk_games = _wk_done[_wk_done['Week'] == _latest_wk].copy()
        _this_wk_games['Margin'] = (_this_wk_games['Vis Score'] - _this_wk_games['Home Score']).abs()

        _known_users_set = set(USER_TEAMS.keys())
        def _is_user_team(u): return str(u).strip().split()[0].title() in _known_users_set

        for _, _g in _this_wk_games.iterrows():
            _vis = str(_g['Visitor']).strip()
            _hm  = str(_g['Home']).strip()
            _vs  = int(_g['Vis Score'])
            _hs2 = int(_g['Home Score'])
            _vis_u = str(_g.get('Vis_User', '')).strip()
            _hm_u  = str(_g.get('Home_User', '')).strip()
            # Only show user-involved games
            if not (_is_user_team(_vis_u) or _is_user_team(_hm_u)):
                continue
            _winner = _vis if _vs > _hs2 else _hm
            _loser  = _hm  if _vs > _hs2 else _vis
            _wscore = _vs  if _vs > _hs2 else _hs2
            _lscore = _hs2 if _vs > _hs2 else _vs
            _diff   = abs(_vs - _hs2)
            # Ranks in ticker text
            _w_rk = _rk_inline(_winner)
            _l_rk = _rk_inline(_loser)
            if _diff <= 3:
                _bdg = 'THRILLER'
                _pri = 75
                _blurb = f"A {_diff}-point nailbiter in Week {_latest_wk}. {_winner} escapes with the W."
            elif _diff >= 21:
                _bdg = 'BLOWOUT'
                _pri = 65
                _blurb = f"{_winner} sends a message in Week {_latest_wk}. Not even close."
            else:
                _bdg = f'WK {_latest_wk} RESULT'
                _pri = 60
                _blurb = f"{_winner} takes care of business in Week {_latest_wk}."
            # Show user vs user games at higher priority
            if _is_user_team(_vis_u) and _is_user_team(_hm_u):
                _pri += 10
                _bdg = 'H2H RESULT' if _diff > 3 else 'H2H THRILLER'
            _wl = get_header_logo(_winner)
            _ll = get_header_logo(_loser)
            _lh = (f'<div style="display:flex;justify-content:center;align-items:center;'
                   f'gap:20px;margin-bottom:10px;">'
                   f'<img src="{_wl}" style="width:50px;height:50px;object-fit:contain;">'
                   f'<span style="color:#94a3b8;font-weight:900;font-size:1.3rem;">VS</span>'
                   f'<img src="{_ll}" style="width:50px;height:50px;object-fit:contain;"></div>')
            _all_headlines.append({
                'badge': _bdg, 'priority': _pri,
                'text': f"{_winner}{_w_rk} {_wscore} \u2013 {_lscore} {_loser}{_l_rk}",
                'blurb': _blurb, 'logo_html': _lh,
            })
except Exception:
    pass

# ── 5. DEFENDING CHAMP ────────────────────────────────────────────────
try:
    _dc = pd.read_csv('champs.csv')
    _dc['YEAR'] = pd.to_numeric(_dc.get('YEAR'), errors='coerce')

    _dc = _dc.dropna(subset=['YEAR']).copy()
    _dc['YEAR'] = _dc['YEAR'].astype(int)

    _dc = _dc[
        _dc['Team'].notna() &
        (_dc['Team'].astype(str).str.strip() != '') &
        (_dc['Team'].astype(str).str.lower().str.strip() != 'nan')
    ].copy()

    if not _dc.empty:
        _dc_last = _dc.sort_values('YEAR', ascending=False).head(1)

        _dc_year = int(_dc_last.iloc[0]['YEAR'])
        _dc_team = str(_dc_last.iloc[0].get('Team', '')).strip()
        _dc_user = str(_dc_last.iloc[0].get('user', '')).strip()

        if _dc_team and _dc_team.lower() != 'nan':
            _dcl = get_header_logo(_dc_team)
            _lh = f'<div class="isp-tc"><img src="{_dcl}" class="isp-logo-65"></div>'
            _dc_rk = _rk_inline(_dc_team)

            _next_season = _dc_year + 1

            _dc_blurb = (
                f"{_dc_user}'s {_dc_team} won the {_dc_year} national title. Can anyone knock them off the throne?"
                if _dc_user and _dc_user.lower() != 'nan'
                else f"{_dc_team} won the {_dc_year} national title. Can anyone knock them off the throne?"
            )

            _all_headlines.append({
                'badge': 'DEFENDING CHAMPS',
                'priority': 50,
                'text': f"{_dc_team}{_dc_rk} enters {_next_season} with a target on their back",
                'blurb': _dc_blurb,
                'logo_html': _lh,
            })
except Exception:
    pass

# ── 6. USER RECRUITING CLASSES (OVERALL) ────────────────────────────
try:
    _rh_all = _load_recruiting_csv()
    _rh = _rh_all[_rh_all['ClassType'].str.upper() == 'OVERALL'].copy() if 'ClassType' in _rh_all.columns else _rh_all.copy()

    _rh['Year'] = pd.to_numeric(_rh['Year'], errors='coerce')
    _rh['Rank'] = pd.to_numeric(_rh['Rank'], errors='coerce')
    _rh['Points'] = pd.to_numeric(_rh['Points'], errors='coerce')
    _rh['TotalCommits'] = pd.to_numeric(_rh['TotalCommits'], errors='coerce')
    _rh['FiveStar'] = pd.to_numeric(_rh['FiveStar'], errors='coerce').fillna(0)
    _rh['FourStar'] = pd.to_numeric(_rh['FourStar'], errors='coerce').fillna(0)
    _rh['ThreeStar'] = pd.to_numeric(_rh['ThreeStar'], errors='coerce').fillna(0)
    _rh['Team'] = _rh['Team'].fillna('').astype(str).str.strip()
    _rh['User'] = _rh['User'].fillna('').astype(str).str.strip()

    if 'USER_TEAMS' in globals():
        _user_team_list = [str(t).strip() for t in USER_TEAMS.values()]
    else:
        _user_team_list = ["Florida State", "Florida", "Bowling Green", "USF", "Texas Tech", "San Jose State"]

    _rh_cy = _rh[
        (_rh['Year'] == CURRENT_YEAR) &
        (_rh['Team'].isin(_user_team_list))
    ].copy()

    if _rh_cy.empty:
        _rh_cy = _rh[
            (_rh['Year'] == CURRENT_YEAR - 1) &
            (_rh['Team'].isin(_user_team_list))
        ].copy()

    if not _rh_cy.empty:
        _headline_year = int(pd.to_numeric(_rh_cy['Year'], errors='coerce').dropna().iloc[0])
        _rh_cy = _rh_cy.sort_values(['Rank', 'Points'], ascending=[True, False]).reset_index(drop=True)

        for _, _rrow in _rh_cy.iterrows():
            _rt = str(_rrow.get('Team', '')).strip()
            _ru = str(_rrow.get('User', '')).strip()
            _rpts = float(_rrow.get('Points', 0)) if not pd.isna(_rrow.get('Points', pd.NA)) else 0.0
            _r5 = int(_rrow.get('FiveStar', 0) or 0)
            _r4 = int(_rrow.get('FourStar', 0) or 0)
            _r3 = int(_rrow.get('ThreeStar', 0) or 0)
            _rtc = int(_rrow.get('TotalCommits', 0) or 0)
            _rec_rank_num = int(_rrow.get('Rank', 999)) if not pd.isna(_rrow.get('Rank', pd.NA)) else 999

            if not _rt or _rt.lower() == 'nan':
                continue

            _rl = get_header_logo(_rt)
            _lh = f'<div class="isp-tc"><img src="{_rl}" class="isp-logo-60"></div>'

            _star_parts = []
            if _r5 > 0:
                _star_parts.append(f"{_r5}⭐⭐⭐⭐⭐")
            if _r4 > 0:
                _star_parts.append(f"{_r4}⭐⭐⭐⭐")
            if _r3 > 0 and not _star_parts:
                _star_parts.append(f"{_r3}⭐⭐⭐")
            _star_str = " · ".join(_star_parts) if _star_parts else "Class loaded"

            _owner_prefix = f"{_ru}'s " if _ru and _ru.lower() != 'nan' else ""

            _all_headlines.append({
                'badge': f'USER CLASS #{_rec_rank_num}',
                'priority': 44,
                'text': f"{_rt} — #{_rec_rank_num} overall · {_star_str} · {round(_rpts, 1)} pts · {_rtc} commits",
                'blurb': f"{_owner_prefix}{_headline_year} overall recruiting class for {_rt} finished #{_rec_rank_num} nationally.",
                'logo_html': _lh,
            })
except Exception as e:
    st.error(f"Recruiting ticker error: {e}")

# ── 7. INJURY BULLETIN (from CSV) ─────────────────────────────────────
try:
    _inj_df = pd.read_csv('injury_bulletin.csv')
    if not _inj_df.empty:
        _inj_df['Year'] = pd.to_numeric(_inj_df.get('Year'), errors='coerce')
        _inj_df['WeeksOut'] = pd.to_numeric(_inj_df.get('WeeksOut'), errors='coerce')
        _inj_df['OVR'] = pd.to_numeric(_inj_df.get('OVR'), errors='coerce')

        _inj_df = _inj_df[
            (_inj_df['Year'].fillna(-1).astype(int) == CURRENT_YEAR) &
            (_inj_df['WeeksOut'].fillna(0).astype(int) > 4)
        ].copy()

        _inj_df = _inj_df.sort_values(['WeeksOut', 'OVR'], ascending=[False, False])

        for _, _inj in _inj_df.iterrows():
            _it = str(_inj.get('Team', '')).strip()
            _iu = str(_inj.get('User', '')).strip()
            _iw = int(pd.to_numeric(_inj.get('WeeksOut'), errors='coerce') or 0)
            _ip = str(_inj.get('Pos', '')).strip()
            _iname = str(_inj.get('Player', '')).strip()
            _ii = str(_inj.get('Injury', '')).strip()
            _iovr = int(pd.to_numeric(_inj.get('OVR'), errors='coerce') or 0)

            _il = get_header_logo(_it)
            _ilh = f'<div class="isp-tc"><img src="{_il}" class="isp-logo-60"></div>'

            _sev = "SEASON-ENDING" if _iw >= 20 else "LONG-TERM INJ"

            _role_map = {
                "QB": "starting QB",
                "HB": "starting RB",
                "RB": "starting RB",
                "FB": "starting RB",
                "WR": "top WR",
                "TE": "starting TE",
                "LT": "starting LT",
                "LG": "starting guard",
                "C": "starting center",
                "RG": "starting guard",
                "RT": "starting RT",
                "LEDG": "top pass rusher",
                "REDG": "top pass rusher",
                "EDGE": "top pass rusher",
                "LE": "top pass rusher",
                "RE": "top pass rusher",
                "DT": "starting DT",
                "IDL": "starting DT",
                "MIKE": "starting linebacker",
                "WILL": "starting linebacker",
                "SAM": "starting linebacker",
                "MLB": "starting linebacker",
                "LOLB": "starting linebacker",
                "ROLB": "starting linebacker",
                "LB": "starting linebacker",
                "CB": "starting corner",
                "FS": "starting safety",
                "SS": "starting safety",
                "S": "starting safety",
            }

            _role_text = _role_map.get(_ip, f"key {_ip}")

            if _iw >= 20:
                _headline_options = [
                    f"{_iu}'s season takes a hit — loses {_role_text} to {_ii}",
                    f"{_iu} loses {_role_text} for the season — {_ii}",
                    f"Disaster for {_iu} — {_role_text} done for the year with {_ii}",
                ]
                _blurb = (
                    f"{_iu}'s {_it} will be without {_iname} ({_ip}, {_iovr} OVR) for the rest of the year "
                    f"after a {_ii.lower()}."
                )
            else:
                _headline_options = [
                    f"{_iu} loses {_role_text} long term — {_ii}",
                    f"{_iu}'s depth chart takes a hit — {_role_text} out with {_ii}",
                    f"Big injury blow for {_iu} — {_role_text} sidelined by {_ii}",
                ]
                _blurb = (
                    f"{_iu}'s {_it} is without {_iname} ({_ip}, {_iovr} OVR) for about {_iw} weeks "
                    f"with a {_ii.lower()}."
                )

            _headline_text = random.choice(_headline_options)

            _all_headlines.append({
                'badge': _sev,
                'priority': 90,
                'text': _headline_text,
                'blurb': _blurb,
                'logo_html': _ilh,
            })
except Exception:
    pass

# ── 8. NFL UNIVERSE HONORS / SUPER BOWL ──────────────────────────────
try:
    # Super Bowl result
    if os.path.exists('nfl_super_bowl_history.csv'):
        _sb_df = pd.read_csv('nfl_super_bowl_history.csv')
        if not _sb_df.empty:
            _sb_df['Season'] = pd.to_numeric(_sb_df.get('Season'), errors='coerce')
            _sb_df = _sb_df.dropna(subset=['Season']).sort_values('Season', ascending=False)

            if not _sb_df.empty:
                _sb = _sb_df.iloc[0]
                _sb_season = int(_sb.get('Season', 0))
                _sb_champ = str(_sb.get('Champion', '')).strip()
                _sb_runner = str(_sb.get('RunnerUp', '')).strip()
                _sb_score = str(_sb.get('Score', '')).strip()
                _sb_mvp = str(_sb.get('MVP', '')).strip()

                if _sb_champ and _sb_runner:
                    _wl = get_header_logo(_sb_champ)
                    _ll = get_header_logo(_sb_runner)
                    _lh = (
                        f'<div style="display:flex;justify-content:center;align-items:center;'
                        f'gap:20px;margin-bottom:10px;">'
                        f'<img src="{_wl}" class="isp-logo-55">'
                        f'<span style="color:#94a3b8;font-weight:900;font-size:1.4rem;">VS</span>'
                        f'<img src="{_ll}" class="isp-logo-55"></div>'
                    )

                    _sb_blurb = f"{_sb_champ} won the Super Bowl"
                    if _sb_score:
                        _sb_blurb += f" by a score of {_sb_score}"
                    if _sb_mvp and _sb_mvp.lower() != 'nan':
                        _sb_blurb += f". {_sb_mvp} took home Super Bowl MVP."
                    else:
                        _sb_blurb += "."

                    _all_headlines.append({
                        'badge': 'NFL SUPER BOWL',
                        'priority': 98,
                        'text': f"Super Bowl {_sb_season}: {_sb_champ} {_sb_score} {_sb_runner}".strip(),
                        'blurb': _sb_blurb,
                        'logo_html': _lh,
                    })

    # NFL awards
    if os.path.exists('nfl_awards_history.csv'):
        _aw_df = pd.read_csv('nfl_awards_history.csv')
        if not _aw_df.empty:
            _aw_df['Season'] = pd.to_numeric(_aw_df.get('Season'), errors='coerce')
            _aw_df = _aw_df.dropna(subset=['Season']).copy()

            if not _aw_df.empty:
                _latest_aw_season = int(_aw_df['Season'].astype(int).max())
                _aw_df = _aw_df[
                    (_aw_df['Season'].astype(int) == _latest_aw_season) &
                    (_aw_df['Result'].astype(str).str.strip() == 'Winner')
                ].copy()

                _award_order = [
                    ('NFL MVP', 'NFL MVP', 97),
                    ('Offensive Player of the Year', 'OPOY', 96),
                    ('Defensive Player of the Year', 'DPOY', 96),
                    ('Offensive Rookie of the Year', 'OROY', 95),
                    ('Defensive Rookie of the Year', 'DROY', 95),
                ]

                for _award_name, _award_short, _pri in _award_order:
                    _row_df = _aw_df[_aw_df['Award'].astype(str).str.strip() == _award_name].copy()
                    if _row_df.empty:
                        continue

                    _rw = _row_df.iloc[0]
                    _player = str(_rw.get('Player', '')).strip()
                    _team = str(_rw.get('NFLTeam', '')).strip()
                    _pos = str(_rw.get('Pos', '')).strip()

                    if not _player or _player.lower() == 'nan':
                        continue

                    _logo = get_nfl_logo_src(_team) if _team else None
                    _lh = (
                        f'<div class="isp-tc"><img src="{_logo}" class="isp-logo-60"></div>'
                        if _logo else ''
                    )

                    _text = f"{_latest_aw_season} {_award_short}: {_player}"
                    if _team and _pos:
                        _text += f" ({_team}, {_pos})"
                    elif _team:
                        _text += f" ({_team})"

                    _blurb = f"{_player} wins {_award_name}"
                    if _team:
                        _blurb += f" for {_team}"
                    if _pos:
                        _blurb += f" at {_pos}"
                    _blurb += "."

                    _all_headlines.append({
                        'badge': _award_short,
                        'priority': _pri,
                        'text': _text,
                        'blurb': _blurb,
                        'logo_html': _lh,
                    })
except Exception:
    pass

# ── FALLBACK ──────────────────────────────────────────────────────────
if not _all_headlines:
    _all_headlines.append({
        'badge': 'TOP STORY', 'priority': 0,
        'text': "Your home for league rankings, playoff races, and Heisman watch.",
        'blurb': f"ISPN Dynasty Coverage — Season {CURRENT_YEAR}",
        'logo_html': '',
    })

# Sort highest priority first
_all_headlines.sort(key=lambda h: h['priority'], reverse=True)
_top = _all_headlines[0]

top_headline = _top['text']
game_blurb   = _top['blurb']
badge_text   = _top['badge']
logo_html    = _top['logo_html']
is_gold      = True

# Build team-colored headline HTML
# Scan top_headline for team names and color each one with its brand color.
# No redundant CFP rank badge — the badge_text already says CFP TOP 10 / FINAL SCORE etc.
def _colorize_headline(text):
    """Replace known team names in headline text with team-color-styled spans."""
    import re as _re

    escaped = html.escape(str(text)).upper()

    team_names = sorted(TEAM_VISUALS.keys(), key=len, reverse=True)
    pattern = _re.compile(
        r'(?<![A-Z0-9])(' + '|'.join(_re.escape(t.upper()) for t in team_names) + r')(?![A-Z0-9])'
    )

    def _safe_color(team_name):
        color = TEAM_VISUALS.get(team_name, {}).get('primary', '#fbbf24')
        try:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            if lum < 60:
                color = f'#{min(255, r+80):02x}{min(255, g+80):02x}{min(255, b+80):02x}'
        except Exception:
            pass
        return color

    color_map = {t.upper(): _safe_color(t) for t in team_names}

    def repl(match):
        team_upper = match.group(1)
        color = color_map.get(team_upper, '#fbbf24')
        return f'<span style="color:{color};font-weight:900;">{team_upper}</span>'

    return pattern.sub(repl, escaped)

_hero_headline_html = _colorize_headline(top_headline)

# ── TICKER ITEM BUILDER ───────────────────────────────────────────────
def _badge_color(badge):
    if badge == 'FINAL SCORE':
        return ('#dc2626', 'white')
    if badge in ('H2H RESULT', 'H2H THRILLER', 'THRILLER', 'BLOWOUT') or badge.startswith('WK '):
        return ('#f59e0b', '#451a03')
    if 'CFP' in badge:
        return ('#059669', 'white')
    if 'RECRUIT' in badge:
        return ('#7c3aed', 'white')
    if 'INJ' in badge or 'SEASON-ENDING' in badge:
        return ('#dc2626', 'white')
    if 'HEISMAN' in badge:
        return ('#f59e0b', '#451a03')
    if 'DEFEND' in badge:
        return ('#1d4ed8', 'white')
    return ('#3b82f6', 'white')

_ticker_items = ''
for h in _all_headlines:
    _bg, _fg = _badge_color(h['badge'])
    _ticker_items += (
        f"<div class='slide'>"
        f"<span class='badge' style='background:{_bg};color:{_fg};'>{h['badge']}</span>"
        f"<span class='hl'>{html.escape(h['text'])}</span>"
        f"</div>"
    )

# ── HERO SECTION ─────────────────────────────────────────────────────
st.markdown(f"""
<style>
@keyframes subtle-pulse {{
  0%  {{ opacity:0.8; transform:scale(1);    }}
  50% {{ opacity:1;   transform:scale(1.03); }}
  100%{{ opacity:0.8; transform:scale(1);    }}
}}
@keyframes live-blink {{
  0%,100% {{ opacity:1;   }}
  50%     {{ opacity:0.4; }}
}}
.top-story-badge {{
  display:inline-block; background:#f59e0b; color:#451a03;
  padding:2px 8px; border-radius:4px; font-size:0.65rem; font-weight:900;
  margin-bottom:6px; animation:subtle-pulse 3s infinite ease-in-out; letter-spacing:1px;
}}
.live-indicator {{ animation:live-blink 2s infinite ease-in-out; color:#38bdf8; font-weight:900; }}
</style>
<div style="margin-top:-75px;margin-bottom:0;text-align:center;">
  <h2 style="margin-bottom:10px;font-weight:800;letter-spacing:-0.5px;">📰 Dynasty News</h2>
  {logo_html}
  <div class="top-story-badge">{badge_text}</div>
  <div style="font-size:1.15rem;font-weight:800;letter-spacing:0.5px;margin-bottom:4px;line-height:1.4;">{_hero_headline_html}</div>
  <div style="color:#94a3b8;font-size:0.85rem;font-style:italic;max-width:500px;margin:0 auto;">"{html.escape(game_blurb)}"</div>
  <div style="color:#38bdf8;font-size:0.65rem;margin-top:8px;letter-spacing:1px;font-weight:800;">
    <span class="live-indicator">●</span> LIVE UPDATE: {time_display} ET
  </div>
</div>
""", unsafe_allow_html=True)

# ── SCROLLING TICKER (sticky, page-level) ────────────────────────────
_ticker_char_count = sum(len(h['badge']) + len(h['text']) + 4 for h in _all_headlines)
_ticker_duration = max(15, int(_ticker_char_count * 0.20))

st.markdown(f"""
<style>
  .sticky-news-ticker {{
    position: fixed;
    top: 3.75rem;
    z-index: 9999;
    background: #0d1b2e;
    border-top: 2px solid #dc2626;
    border-bottom: 1px solid #1e293b;
    padding: 9px 0;
    overflow: hidden;
  }}

  .sticky-news-ticker::before,
  .sticky-news-ticker::after {{
    content: '';
    position: absolute;
    top: 0;
    bottom: 0;
    width: 80px;
    z-index: 2;
    pointer-events: none;
  }}

  .sticky-news-ticker::before {{
    left: 0;
    background: linear-gradient(to right, #0d1b2e 40%, transparent);
  }}

  .sticky-news-ticker::after {{
    right: 0;
    background: linear-gradient(to left, #0d1b2e 40%, transparent);
  }}

  .sticky-news-ticker .ticker-track {{
    display: inline-flex;
    white-space: nowrap;
    animation: scroll-left {_ticker_duration}s linear infinite;
  }}

  @keyframes scroll-left {{
    0%   {{ transform: translateX(0); }}
    100% {{ transform: translateX(-50%); }}
  }}

  .sticky-news-ticker .slide {{
    display: inline-flex;
    align-items: center;
    padding: 0 36px;
    font-size: 15px;
    font-weight: 600;
    color: #cbd5e1;
    white-space: nowrap;
    letter-spacing: 0.01em;
  }}

  .sticky-news-ticker .slide + .slide::before {{
    content: '●';
    color: #f59e0b;
    font-size: 6px;
    margin-right: 36px;
    opacity: 0.6;
    vertical-align: middle;
  }}

  .sticky-news-ticker .badge {{
    display: inline-block;
    padding: 3px 9px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 900;
    letter-spacing: .1em;
    margin-right: 10px;
    vertical-align: middle;
    line-height: 1.8;
    text-transform: uppercase;
    flex-shrink: 0;
  }}

  .sticky-news-ticker .hl {{
    font-weight: 700;
    color: #f8fafc;
    font-size: 15px;
    letter-spacing: 0.01em;
  }}
</style>

<div class="sticky-news-ticker">
  <div class="ticker-track">{_ticker_items}{_ticker_items}</div>
</div>
""", unsafe_allow_html=True)


# ── TABS START ───────────────────────────────────────────────────────
tabs = st.tabs([
    "🗞️ Dynasty News",          # tabs[0]
    "🏈 NFL Universe",          # tabs[1]
    "📐 SOS & True Path",       # tabs[2]
    "🏆 Who's In?",             # tabs[3]
    "🥇 Recruiting Rankings",   # tabs[4]
     "🚪 Roster Attrition",      # tabs[5]
    "📺 Season Recap",          # tabs[6]
    "🔍 Speed Freaks",          # tabs[7]
    "🎯 Roster Matchup",        # tabs[8]
    "🏛️ Coach Legacy",         # tabs[9]
    "⚔️ H2H Matrix",            # tabs[10]
    "🎬 ISPN Classics",         # tabs[11]
    "🐐 GOAT Rankings",         # tabs[12]
])

    # ── SOS & TRUE PATH ──────────────────────────────────────────────────
with tabs[2]:
        st.header("📐 SOS & True Path")
        st.caption("Who actually earned their record? Schedule résumé, speed-adjusted difficulty, and quality wins.")

        # 1. LOAD MASTER DATA
        try:
            _cpu_sos = pd.read_csv('CPUscores_MASTER.csv')
            _cpu_sos['YEAR'] = pd.to_numeric(_cpu_sos['YEAR'], errors='coerce')
            _cpu_sos = _cpu_sos[_cpu_sos['YEAR'] == CURRENT_YEAR].copy()
        except Exception:
            _cpu_sos = pd.DataFrame()

        # 2. INITIALIZE USER NORMALIZATION
        _known_users = {'mike':'Mike','devin':'Devin','josh':'Josh','noah':'Noah','doug':'Doug','nick':'Nick'}
        def _norm_user(u):
            if pd.isna(u): return 'CPU'
            u = str(u).strip()
            first = u.split()[0].lower() if u else ''
            return _known_users.get(first, u)

        if not _cpu_sos.empty:
            _cpu_sos['Vis_User']  = _cpu_sos['Vis_User'].apply(_norm_user)
            _cpu_sos['Home_User'] = _cpu_sos['Home_User'].apply(_norm_user)
            for _c in ['Visitor Rank', 'Home Rank', 'Vis Score', 'Home Score']:
                _cpu_sos[_c] = pd.to_numeric(_cpu_sos.get(_c, 0), errors='coerce')

        # 3. SPEED DATA — sourced from model_2041 (pre-computed from roster CSV)

        # 4. OFFICIAL RANK LOOKUP (LATEST CFP)
        try:
            _cfp_master = pd.read_csv('cfp_rankings_history.csv')
            _latest_wk = _cfp_master['WEEK'].max()
            _latest_snap = _cfp_master[_cfp_master['WEEK'] == _latest_wk]
            _final_rank_lookup = dict(zip(_latest_snap['TEAM'].str.strip(), _latest_snap['RANK'].astype(int)))
        except Exception:
            _final_rank_lookup = {}

        # 5. BUILD SPEED MAP
        _speed_map = {}
        for _, _sr in model_2041.iterrows():
            _u = _sr.get('USER', 'CPU')
            _team_name = str(_sr.get('TEAM', '')).strip()
            _ts = float(_sr.get('Team Speed (90+ Speed Guys)', 0) or 0)

            _speed_map[_u] = {
                'team_speed': _ts,
                'qb_tier': str(_sr.get('QB Tier', 'Average Joe')).strip(),
                'qb_ovr': float(_sr.get('QB OVR', 80) or 80),
                'team': _team_name,
                'conf': _sr.get('CONFERENCE', 'Other'),
                'rs_data_confirmed': _ts > 0,
            }

        _league_avg_speed = sum(v['team_speed'] for v in _speed_map.values()) / max(1, len(_speed_map))

        # 6. LOGIC FUNCTIONS
        def _get_user_games(user):
            if _cpu_sos.empty: return pd.DataFrame()
            mask = (_cpu_sos['Vis_User'] == user) | (_cpu_sos['Home_User'] == user)
            games = _cpu_sos[mask].copy()
            results = []
            for _, g in games.iterrows():
                is_vis = g['Vis_User'] == user
                my_s, opp_s = (g['Vis Score'], g['Home Score']) if is_vis else (g['Home Score'], g['Vis Score'])
                opp_n, opp_r = (g['Home'], g['Home Rank']) if is_vis else (g['Visitor'], g['Visitor Rank'])

                # Check for CFP rank if at-game-time rank is missing
                opp_final_r = _final_rank_lookup.get(str(opp_n).strip())
                eff_rank = opp_r if not pd.isna(opp_r) else (float(opp_final_r) if opp_final_r else float('nan'))

                res = 'TBD'
                if not pd.isna(my_s) and not pd.isna(opp_s):
                    res = 'W' if my_s > opp_s else 'L'

                results.append({
                    'week': str(g['Week']), 'opponent': opp_n, 'result': res,
                    'effective_rank': eff_rank, 'opp_ranked_final': not pd.isna(eff_rank),
                    'opp_ranked': not pd.isna(opp_r),
                    'opp_rank': opp_r,
                    'home_away': 'Away' if is_vis else 'Home',
                    'margin': (my_s - opp_s) if res != 'TBD' else None
                })
            return pd.DataFrame(results)

        def _speed_handicap(user):
            info = _speed_map.get(user, {})
            spd = info.get('team_speed', _league_avg_speed)
            spd_raw = (_league_avg_speed - spd) * 0.55
            qb_tier = info.get('qb_tier', 'Average Joe')
            qb_base = {'Elite': -4.0, 'Leader': -1.5, 'Average Joe': 1.5, 'Ass': 5.0}.get(qb_tier, 0)
            return round(spd_raw + qb_base, 2)

        def _sos_score(games_df):
            if games_df.empty: return 0, 0, 0, 0
            rw = int(((games_df['result']=='W') & games_df['opp_ranked_final']).sum())
            t10 = int(((games_df['result']=='W') & (games_df['effective_rank'] <= 10)).sum())
            rl = int(((games_df['result']=='L') & games_df['opp_ranked_final']).sum())
            comp = games_df[games_df['opp_ranked_final']]
            avg_r = float(comp['effective_rank'].mean()) if not comp.empty else 99.0
            base = (rw * 8.5) + (t10 * 4.0) - (rl * 1.5) + (max(0, (25 - avg_r)) * 0.8)
            return round(base, 1), rw, t10, round(avg_r, 1)

        # 7. BUILD RÉSUMÉ DATA
        resume_rows = []
        for user in USER_TEAMS:
            g = _get_user_games(user)
            base, rw, t10, avg_opp = _sos_score(g)
            hcap = _speed_handicap(user)
            resume_rows.append({
                'User': user, 'Team': USER_TEAMS[user],
                'Record': f"{int((g['result']=='W').sum() if not g.empty else 0)}-{int((g['result']=='L').sum() if not g.empty else 0)}",
                'Ranked Wins': rw, 'Top-10 Wins': t10, 'Avg Opp Rank': avg_opp if avg_opp < 99 else '—',
                'Base SOS': base, '_handicap': hcap, 'Adj SOS': round(base + hcap, 1),
                'Team Speed': int(_speed_map.get(user, {}).get('team_speed', 0)),
                'QB Tier': _speed_map.get(user, {}).get('qb_tier', '—'),
                'QB OVR': int(_speed_map.get(user, {}).get('qb_ovr', 0)),
                'Conference': _speed_map.get(user, {}).get('conf', '—')
            })
        resume_df = pd.DataFrame(resume_rows).sort_values('Adj SOS', ascending=False).reset_index(drop=True)

        # 8. TOP METRICS RENDER
        _top = resume_df.iloc[0]
        _most_rw = resume_df.sort_values('Ranked Wins', ascending=False).iloc[0]
        _hardest = resume_df.sort_values('_handicap', ascending=False).iloc[0]
        _fastest = resume_df.sort_values('Team Speed', ascending=False).iloc[0]

        mobile_metrics([
            {"label": "📋 Best Résumé",      "value": _top['User'],        "delta": f"Adj SOS: {_top['Adj SOS']}"},
            {"label": "💪 Most Ranked Wins",  "value": _most_rw['User'],    "delta": f"{_most_rw['Ranked Wins']} ranked W"},
            {"label": "🐢 Hardest Path",      "value": _hardest['User'],    "delta": f"Handicap +{_hardest['_handicap']:.1f}"},
            {"label": "⚡ Speed Advantage",   "value": _fastest['User'],    "delta": f"{_fastest['Team Speed']} speed guys"},
        ], cols_desktop=4)

        # 9. RENDER LEADERBOARD CARDS
        st.markdown("---")
        st.subheader("📋 Schedule Résumé Board — Final SOS")
        st.caption("📌 **Final SOS** uses latest CFP ranks. Adjusted SOS = Base SOS + Speed Handicap.")

        rank_medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣"]

        # Pre-compute speed bar scale across all users
        _max_spd = max(float(r['Team Speed']) for _, r in resume_df.iterrows()) or 1
        _max_base_sos = max(float(r['Base SOS']) for _, r in resume_df.iterrows()) or 1

        resume_cards = ""
        for i, row in resume_df.iterrows():
            tc = get_team_primary_color(row['Team'])
            logo_uri = image_file_to_data_uri(get_logo_source(row['Team']))
            logo_img = f"<img src='{logo_uri}' style='width:34px;height:34px;object-fit:contain;vertical-align:middle;'/>" if logo_uri else "🏈"
            medal = rank_medals[i] if i < len(rank_medals) else str(i+1)

            hcap = float(row['_handicap'])
            hcap_color = "#ef4444" if hcap > 4 else ("#f97316" if hcap > 1 else ("#fbbf24" if hcap > 0 else "#22c55e"))
            adj_color = "#22c55e" if row['Adj SOS'] >= resume_df['Adj SOS'].median() else "#f97316"

            # QB Badge Color
            _qt = str(row.get('QB Tier', '—'))
            _qtc = {'Elite':('#22c55e','#0d2010'),'Leader':('#60a5fa','#0d1829'),'Average Joe':('#fbbf24','#1c1400'),'Ass':('#ef4444','#200808')}.get(_qt, ('#6b7280','#1f2937'))

            # ── SPEED vs SCHEDULE BAR ─────────────────────────────────────────
            _spd_count  = float(row['Team Speed'])
            _base_sos   = float(row['Base SOS'])
            _mph        = team_speed_to_mph(_spd_count)

            # Speed bar fill: how fast is this team relative to the league max
            _spd_bar_pct = min(100, round(_spd_count / _max_spd * 100))

            # SOS difficulty tick: where does their schedule sit (0–100)
            _sos_tick_pct = min(100, round(_base_sos / _max_base_sos * 100))

            # Bar color: fast team on hard schedule = green; slow team on hard schedule = brutal red
            if hcap <= -3:
                _spd_bar_color = "#22c55e"   # speed advantage — green
                _spd_label = f"⚡ {int(_spd_count)} speed guys · {_mph:.0f} MPH — SPEED ADVANTAGE"
            elif hcap <= 0:
                _spd_bar_color = "#4ade80"   # slight edge
                _spd_label = f"⚡ {int(_spd_count)} speed guys · {_mph:.0f} MPH — holding their own"
            elif hcap <= 2:
                _spd_bar_color = "#fbbf24"   # warning
                _spd_label = f"🐢 {int(_spd_count)} speed guys · {_mph:.0f} MPH — speed deficit vs schedule"
            elif hcap <= 4:
                _spd_bar_color = "#f97316"   # orange alert
                _spd_label = f"🐢 {int(_spd_count)} speed guys · {_mph:.0f} MPH — real speed problem"
            else:
                _spd_bar_color = "#ef4444"   # red — cooked
                _spd_label = f"💀 {int(_spd_count)} speed guys · {_mph:.0f} MPH — SPEED CRISIS vs this schedule"

            resume_cards += f"""
            <div style='background:#0a1628;border:1px solid #1e293b;border-left:4px solid {tc};border-radius:10px;padding:12px 14px;margin-bottom:8px;'>
              <div style='display:flex;align-items:center;gap:10px;margin-bottom:10px;'>
                <span style='font-size:1.2rem;min-width:28px;'>{medal}</span>
                {logo_img}
                <div style='flex:1;min-width:0;'>
                  <div style='color:{tc};font-weight:900;font-size:0.95rem;'>{html.escape(row['Team'])}</div>
                  <div style='color:#475569;font-size:0.72rem;'>({html.escape(row['User'])})</div>
                </div>
                <div style='text-align:right;flex-shrink:0;'>
                  <div style='color:white;font-weight:800;font-size:0.95rem;'>{row['Record']}</div>
                  <div style='color:{adj_color};font-weight:900;font-size:1.1rem;'>{row['Adj SOS']}</div>
                  <div style='color:#475569;font-size:0.62rem;'>Adj SOS</div>
                </div>
              </div>
              <div style='display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;'>
                <div style='background:#111f33;border-radius:6px;padding:5px 9px;text-align:center;'>
                  <div style='color:#22c55e;font-weight:800;font-size:0.9rem;'>{row['Ranked Wins']}</div>
                  <div style='color:#475569;font-size:0.62rem;'>RANKED W</div>
                </div>
                <div style='background:#111f33;border-radius:6px;padding:5px 9px;text-align:center;'>
                  <div style='color:#94a3b8;font-weight:700;font-size:0.9rem;'>{row['Avg Opp Rank']}</div>
                  <div style='color:#475569;font-size:0.62rem;'>AVG OPP RK</div>
                </div>
                <div style='background:#111f33;border-radius:6px;padding:5px 9px;text-align:center;'>
                  <div style='color:{hcap_color};font-weight:800;font-size:0.9rem;'>{"+" if hcap > 0 else ""}{hcap:.1f}</div>
                  <div style='color:#475569;font-size:0.62rem;'>HANDICAP</div>
                </div>
                <div style='background:{_qtc[1]};border-radius:6px;padding:5px 9px;text-align:center;border:1px solid {_qtc[0]}33;'>
                  <div style='color:{_qtc[0]};font-weight:800;font-size:0.82rem;'>{_qt}</div>
                  <div style='color:{_qtc[0]}99;font-size:0.62rem;'>{row['QB OVR']} OVR</div>
                </div>
              </div>
              <!-- SPEED vs SCHEDULE BAR -->
              <div style='margin-top:2px;'>
                <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;'>
                  <span style='font-size:0.65rem;color:#475569;font-family:monospace;letter-spacing:.04em;'>SPEED vs SCHEDULE</span>
                  <span style='font-size:0.68rem;color:{_spd_bar_color};font-weight:700;'>{_spd_label}</span>
                </div>
                <!-- track -->
                <div style='position:relative;background:#111f33;border-radius:4px;height:8px;overflow:visible;'>
                  <!-- speed fill -->
                  <div style='background:{_spd_bar_color};width:{_spd_bar_pct}%;height:8px;border-radius:4px;opacity:0.85;'></div>
                  <!-- SOS difficulty tick mark -->
                  <div style='position:absolute;top:-3px;left:{_sos_tick_pct}%;width:2px;height:14px;background:#f59e0b;border-radius:1px;' title='Schedule difficulty'></div>
                </div>
                <div style='display:flex;justify-content:space-between;margin-top:3px;'>
                  <span style='font-size:0.58rem;color:#334155;'>slow</span>
                  <span style='font-size:0.58rem;color:#f59e0b;'>▲ SOS difficulty</span>
                  <span style='font-size:0.58rem;color:#334155;'>fast</span>
                </div>
              </div>
            </div>"""

        st.markdown(resume_cards, unsafe_allow_html=True)


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
        st.caption("Preseason projections only — ranked on roster strength, speed, recruiting, QB tier, and coaching pedigree.")

        # 1. Initialize Defaults and Load Data
        power_board = model_2041.copy()
        for col in ['Preseason PI', 'Preseason Natty Odds', 'Preseason CFP %', 'Power Index', 'Natty Odds', 'CFP Odds']:
            if col not in power_board.columns:
                power_board[col] = 0

        power_board = power_board.sort_values(['Preseason PI', 'Preseason Natty Odds'], ascending=False).reset_index(drop=True)

        # --- NEW: Official Rank Lookup ---
        try:
            _cfp_hist = pd.read_csv('cfp_rankings_history.csv')
            _latest_wk = _cfp_hist['WEEK'].max()
            _latest_snap = _cfp_hist[_cfp_hist['WEEK'] == _latest_wk]
            # Map Team Name -> Rank
            official_rank_map = dict(zip(_latest_snap['TEAM'].str.strip(), _latest_snap['RANK'].astype(int)))
        except:
            official_rank_map = {}

        # 2. Initialize Bracket Variables (Prevents NameError)
        official_cfp_teams = []
        eliminated_teams = []
        defending_champ = ""
        csv_error = False

        # 3. Load Bracket Logic
        try:
            if os.path.exists('CFPbracketresults.csv'):
                _b_df = pd.read_csv('CFPbracketresults.csv')

                # Find Defending Champ
                _prev_year = CURRENT_YEAR - 1
                _last_year_bracket = _b_df[_b_df['YEAR'] == _prev_year]
                if not _last_year_bracket.empty and 'WINNER' in _last_year_bracket.columns:
                    _dc_raw = _last_year_bracket[_last_year_bracket['WINNER'].notna()]['WINNER'].iloc[-1]
                    defending_champ = str(_dc_raw).strip().lower()

                # Get Current Year Status
                _cy_bracket = _b_df[_b_df['YEAR'] == CURRENT_YEAR]
                if not _cy_bracket.empty:
                    t1 = _cy_bracket['TEAM1'].dropna().unique().tolist()
                    t2 = _cy_bracket['TEAM2'].dropna().unique().tolist()
                    official_cfp_teams = [str(t).strip().lower() for t in (t1 + t2)]

                    if 'LOSER' in _cy_bracket.columns:
                        eliminated_teams = [str(t).strip().lower() for t in _cy_bracket['LOSER'].dropna().unique().tolist()]
            else:
                csv_error = "Bracket CSV file missing."
        except Exception as e:
            csv_error = str(e)

        # Admin Warning (Only shows if there's an issue with the file)
        if csv_error:
            st.error(f"⚠️ **Bracket Data Error:** {csv_error}. Card status logic may be disabled.")

        # 4. Define UI Constants
        rank_icons = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣"]
        rank_labels = ["KING", "CONTENDER", "FRINGE", "BUBBLE", "LONG SHOT", "REBUILDING"]
        rank_colors = ["#f59e0b", "#9ca3af", "#b45309", "#6b7280", "#374151", "#374151"]

        # 5. Render the Cards
        for idx, row in power_board.iterrows():
            team = str(row.get('TEAM', ''))
            user = str(row.get('USER', ''))
            pi    = row.get('Preseason PI', row.get('Power Index', 0))
            natty = row.get('Preseason Natty Odds', row.get('Natty Odds', 0))
            cfp_pct = row.get('Preseason CFP %', row.get('CFP Odds', 0))
            live_natty = float(row.get('Natty Odds', 0))
            live_cfp = float(row.get('CFP Odds', 0))

            # --- THE FIX: Official Rank & Gold Glow Logic ---
            _team_name = team.strip()
            curr_rank = official_rank_map.get(_team_name, "UR")

            if curr_rank != "UR" and int(curr_rank) <= 4:
                # Top 4 Playoff Bound - Gold Glow
                rank_label = f"#{curr_rank}"
                badge_style = "color:#fbbf24; background:#fbbf2415; border:1px solid #fbbf2488; box-shadow: 0 0 12px #fbbf2444;"
            elif curr_rank != "UR":
                # Top 25 - Blue Badge
                rank_label = f"#{curr_rank}"
                badge_style = "color:#60a5fa; background:#60a5fa15; border:1px solid #60a5fa44;"
            else:
                # Unranked - Subdued Gray
                rank_label = "UNRANKED"
                badge_style = "color:#94a3b8; background:#94a3b810; border:1px solid #94a3b833;"

            rank_badge = f"<span style='{badge_style} font-size:0.75rem; font-weight:800; margin-left:6px; padding:2px 8px; border-radius:4px; text-transform:uppercase;'>RANK {rank_label}</span>"


            _team_clean = team.strip().lower()
            is_official = _team_clean in official_cfp_teams
            is_eliminated = _team_clean in eliminated_teams
            is_defending_champ = (_team_clean == defending_champ)

            official_badge, defending_badge, card_glow, bw_style = "", "", "", ""
            card_opacity = "1.0"

            if is_defending_champ:
                defending_badge = f"<span style='display:inline-block;margin-left:8px;padding:2px 8px;border-radius:999px;font-size:0.7rem;font-weight:900;background:#fbbf24;color:#78350f;border:1px solid #78350f;'>🛡️ DEFENDING CHAMP</span>"
                card_opacity = "0.9"

            if len(official_cfp_teams) > 0:
                if is_official:
                    if is_eliminated:
                        official_badge = f"<span style='display:inline-block;margin-left:10px;padding:2px 8px;border-radius:999px;font-size:0.7rem;font-weight:900;background:#4b5563;color:white;border:1px solid #4b5563;'>❌ ELIMINATED</span>"
                        card_glow, bw_style = "border: 1px solid #4b5563;", "filter: grayscale(100%);"
                        card_opacity = "0.8" if is_defending_champ else "0.7"
                        live_natty, live_cfp = 0.0, 100.0
                    else:
                        card_glow = "box-shadow: 0px 0px 15px rgba(5, 150, 105, 0.4); border: 1px solid #059669;"
                        official_badge = f"<span style='display:inline-block;margin-left:10px;padding:2px 8px;border-radius:999px;font-size:0.7rem;font-weight:900;background:#059669;color:white;border:1px solid #059669;'>🔒 OFFICIAL FIELD</span>"
                        live_cfp, card_opacity = 100.0, "1.0"
                else:
                    official_badge = f"<span style='display:inline-block;margin-left:10px;padding:2px 8px;border-radius:999px;font-size:0.7rem;font-weight:900;background:#dc2626;color:white;border:1px solid #dc2626;'>❌ OUT</span>"
                    bw_style = "filter: grayscale(100%);"
                    card_opacity = "0.8" if is_defending_champ else "0.6"
                    live_natty, live_cfp = 0.0, 0.0

            label = rank_labels[idx] if idx < len(rank_labels) else "UNRANKED"
            lcolor = rank_colors[idx] if idx < len(rank_colors) else "#374151"
            if label.upper() == "KING": label = "TITLE FAVORITE"

            tc = get_team_primary_color(team)
            logo_uri = image_file_to_data_uri(get_logo_source(team))
            logo_html = f"<img src='{logo_uri}' style='width:38px;height:38px;object-fit:contain;vertical-align:middle;margin-right:8px;{bw_style}'/>" if logo_uri else "🏈 "

            qb_tier = row.get('QB Tier', '—')
            qb_chip_color = {"Elite": "#22c55e", "Leader": "#3b82f6", "Average Joe": "#f59e0b", "Ass": "#ef4444"}.get(qb_tier, "#6b7280")
            icon = rank_icons[idx] if idx < len(rank_icons) else "▪️"

            # Render HTML Card
            card_html = (
                f"<div style='display:flex; align-items:center; background:linear-gradient(90deg,{tc}18,#1f2937 60%); "
                f"border-left:5px solid {tc}; {card_glow} opacity:{card_opacity}; border-radius:10px; padding:10px 14px; margin-bottom:4px; gap:12px; flex-wrap:wrap;'>"
                f"<div style='font-size:1.6rem; min-width:36px; {bw_style}'>{icon}</div>"
                f"{logo_html}"
                f"<div style='flex:1; min-width:200px; {bw_style}'>"
                f"<span style='font-size:1.05rem; font-weight:800; color:{tc if not bw_style else '#9ca3af'};'>{html.escape(team)}</span> "
                f"<span style='color:#9ca3af; font-size:0.82rem;'>({html.escape(user)})</span> {rank_badge}"
                f"<div style='margin-top:4px;'>"
                f"<span style='display:inline-block; padding:2px 8px; border-radius:999px; font-size:0.7rem; font-weight:900; background:{lcolor if not bw_style else '#4b5563'}; color:white;'>{label}</span>"
                f" {official_badge} {defending_badge}</div></div>"
                f"<div style='text-align:right; {bw_style}'>"
                f"<span style='font-size:0.8rem; color:#d1d5db;'>Pre-PI: <strong style='color:white;'>{round(float(pi),1)}</strong></span><br>"
                f"<span style='font-size:0.8rem; color:#d1d5db;'>🏆 Pre: <strong style='color:white;'>{round(float(natty),1)}%</strong> | Live: <strong style='color:#22c55e;'>{round(float(live_natty),1)}%</strong></span><br>"
                f"<span style='font-size:0.8rem; color:#d1d5db;'>CFP Pre: <strong style='color:white;'>{round(float(cfp_pct),1)}%</strong> | Live: <strong style='color:#3b82f6;'>{round(float(live_cfp),1)}%</strong></span>"
                f"<div style='margin-top:4px;'><span style='display:inline-block;padding:2px 7px;border-radius:999px;font-size:0.72rem;font-weight:700;background:{qb_chip_color}33;color:{qb_chip_color};border:1px solid {qb_chip_color};'>QB: {html.escape(str(qb_tier))}</span></div>"
                f"</div></div>"
            )
            st.markdown(card_html, unsafe_allow_html=True)

            # ── TEAM OVERVIEW JUMP BUTTON ─────────────────────────────────────
            if st.button(
                f"🏛️ View {team} Coach Legacy →",
                key=f"_goto_overview_{team}_{idx}",
                use_container_width=False,
            ):
                st.session_state["team_analysis_user"] = user
                st.session_state["_jump_to_team_analysis"] = True
                st.rerun()

            st.markdown("<div style='margin-bottom:6px;'></div>", unsafe_allow_html=True)

        # ════════════════════════════════════════════════════════════════════
        # SECTION 2 — DYNASTY HEADLINES
        # All metrics use LIVE model columns (Natty Odds, Power Index,
        # CFP Odds, Collapse Risk) — NOT preseason proxies.
        # Game-result headlines are generated directly from CPUscores_MASTER.csv.
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
            # ── LIVE OVERRIDES FOR HEADLINES ──────────────────────────
            try:
                _live_cfp_df = get_cfp_rankings_snapshot()
                _live_cfp_map = _live_cfp_df.set_index('Team')
                def _get_live_record(t_name, fw, fl):
                    if t_name in _live_cfp_map.index:
                        return int(_live_cfp_map.loc[t_name, 'Wins']), int(_live_cfp_map.loc[t_name, 'Losses'])
                    return fw, fl
                def _get_live_rank(t_name, f_rank):
                    if t_name in _live_cfp_map.index:
                        return int(_live_cfp_map.loc[t_name, 'Rank'])
                    return f_rank
            except Exception:
                def _get_live_record(t_name, fw, fl): return fw, fl
                def _get_live_rank(t_name, f_rank): return f_rank
            # ──────────────────────────────────────────────────────────────────

            # ── 1. LIVE TITLE FAVORITE — use Natty Odds, not Preseason ─────
            _natty_col = 'Natty Odds' if 'Natty Odds' in model_2041.columns else 'Preseason Natty Odds'
            _pi_col = 'Power Index' if 'Power Index' in model_2041.columns else 'Preseason PI'
            _cfp_col = 'CFP Odds' if 'CFP Odds' in model_2041.columns else 'Preseason CFP %'

            title_fav = model_2041.sort_values(_natty_col, ascending=False).iloc[0]
            pi_leader = model_2041.sort_values(_pi_col, ascending=False).iloc[0]
            collapse_row = model_2041.sort_values('Collapse Risk', ascending=False).iloc[0]

            _tf_user = str(title_fav['USER'])
            _tf_team = str(title_fav['TEAM'])
            _tf_natty = round(float(title_fav[_natty_col]), 1)
            _tf_ovr = int(title_fav.get('OVERALL', 0))

            # Use live rank instead of static CSV rank
            _tf_cfp_raw = title_fav.get('Current CFP Ranking', 99)
            _tf_cfp = _get_live_rank(_tf_team, int(_tf_cfp_raw) if pd.notna(_tf_cfp_raw) else 99)
            _tf_cfp_str = f" (CFP #{_tf_cfp})" if _tf_cfp and _tf_cfp <= 25 else ""

            headlines.append(("🏆", "National Title Favorite",
                              f"<strong>{_tf_user}</strong> ({html.escape(_tf_team)}) leads the model with "
                              f"a <strong>{_tf_natty}%</strong> chance to win it all. "
                              f"At {_tf_ovr} OVR{_tf_cfp_str}, this roster has the juice to "
                              f"survive the 12-team gauntlet."))
            # ── [ADDED] CHOKE JOB OVERRIDE ──────────────────────────────
            try:
                _choke_res = pd.read_csv('CFPbracketresults.csv')
                _comp_col_c = next((c for c in _choke_res.columns if c.strip().upper() == 'COMPLETED'), None)
                if _comp_col_c:
                    _choke_res = _choke_res[pd.to_numeric(_choke_res[_comp_col_c], errors='coerce').fillna(0).astype(int) == 1]

                _t1_col_c = next((c for c in _choke_res.columns if c.strip().upper() in ['TEAM1', 'AWAY', 'VISITOR']), 'TEAM1')
                _t2_col_c = next((c for c in _choke_res.columns if c.strip().upper() in ['TEAM2', 'HOME']), 'TEAM2')
                _s1_col_c = next((c for c in _choke_res.columns if c.strip().upper() in ['TEAM1_SCORE', 'AWAY SCORE', 'VIS SCORE']), 'TEAM1_SCORE')
                _s2_col_c = next((c for c in _choke_res.columns if c.strip().upper() in ['TEAM2_SCORE', 'HOME SCORE']), 'TEAM2_SCORE')
                _rnd_col_c = next((c for c in _choke_res.columns if c.strip().upper() in ['ROUND', 'WEEK']), 'ROUND')

                # Read from bottom to top so we catch their MOST RECENT loss, not an older one!
                for _, _cg in _choke_res.iloc[::-1].iterrows():
                    _c_t1 = str(_cg[_t1_col_c]).strip()
                    _c_t2 = str(_cg[_t2_col_c]).strip()
                    _c_s1 = int(float(_cg[_s1_col_c]))
                    _c_s2 = int(float(_cg[_s2_col_c]))

                    _choked = False
                    _choke_opp = ""
                    _choke_score_str = ""
                    _choke_rnd = str(_cg.get(_rnd_col_c, 'the playoffs')).strip()

                    if _c_t1 == _tf_team and _c_s1 < _c_s2:
                        _choked = True
                        _choke_opp = _c_t2
                        _choke_score_str = f"{_c_s2}-{_c_s1}"
                    elif _c_t2 == _tf_team and _c_s2 < _c_s1:
                        _choked = True
                        _choke_opp = _c_t1
                        _choke_score_str = f"{_c_s1}-{_c_s2}"

                    if _choked:
                        # Intercept and overwrite the Title Favorite headline
                        headlines[-1] = ("🤡", "Generational Choke Job",
                                         f"<strong>{_tf_user}</strong> ({html.escape(_tf_team)}) was the model's National Title Favorite with "
                                         f"<strong>{_tf_natty}% odds</strong>, but they just absolutely choked it away. "
                                         f"They got sent packing by {html.escape(_choke_opp)} {_choke_score_str} in {_choke_rnd}. "
                                         f"Hang the banner for winning the simulation, because they aren't winning it on the field.")
                        break
            except Exception:
                pass
            # ────────────────────────────────────────────────────────────

            # ── 2. POWER INDEX LEADER ─────────────────────────────────────
            _pi_user = str(pi_leader['USER'])
            _pi_team = str(pi_leader['TEAM'])
            _pi_val = round(float(pi_leader[_pi_col]), 1)
            _pi_ovr = int(pi_leader.get('OVERALL', 0))

            # Use live record instead of static CSV record
            _pi_rec_w, _pi_rec_l = _get_live_record(_pi_team, int(pi_leader.get('Current Record Wins', 0)), int(pi_leader.get('Current Record Losses', 0)))
            _pi_rec_str = f" ({_pi_rec_w}-{_pi_rec_l})" if _pi_rec_w or _pi_rec_l else ""

            if _pi_user != _tf_user:
                headlines.append(("💪", "Power Index Alpha",
                                  f"While {_tf_user} has the highest title odds, <strong>{_pi_user}</strong> "
                                  f"({html.escape(_pi_team)}) sits at #1 in the Power Index ({_pi_val}){_pi_rec_str}. "
                                  f"This is the most dangerous team on a neutral field right now."))

            # ── 3. CFP #1 CALLOUT ─────────────────────────────────────────
            _cfp_ranked = model_2041.copy()
            _cfp_ranked['_cfp_num'] = _cfp_ranked['TEAM'].apply(lambda t: _get_live_rank(t, 99))
            _cfp_ranked = _cfp_ranked[_cfp_ranked['_cfp_num'] <= 25]

            if not _cfp_ranked.empty:
                _no1 = _cfp_ranked.sort_values('_cfp_num').iloc[0]
                _no1_user = str(_no1['USER'])
                _no1_team = str(_no1['TEAM'])
                _no1_rank = int(_no1['_cfp_num'])
                _no1_rec_w, _no1_rec_l = _get_live_record(_no1_team, int(_no1.get('Current Record Wins', 0)), int(_no1.get('Current Record Losses', 0)))
                _no1_natty = round(float(_no1.get(_natty_col, 0)), 1)

                if _no1_rank == 1 and _no1_user not in [_tf_user, _pi_user]:
                    headlines.append(("🥇", "Committee's Darling",
                                      f"<strong>{_no1_user}</strong> ({html.escape(_no1_team)}) is sitting pretty "
                                      f"at CFP #1 ({_no1_rec_w}-{_no1_rec_l}), despite only having {_no1_natty}% title odds. "
                                      f"The resume is doing the heavy lifting."))

                          # ── 4. BOWL SEASON STATUS ─────────────────────────────────────
            try:
                _cfp_res = pd.read_csv('CFPbracketresults.csv')

                _comp_col = next((c for c in _cfp_res.columns if c.strip().upper() == 'COMPLETED'), None)
                if _comp_col:
                    _cfp_res = _cfp_res[pd.to_numeric(_cfp_res[_comp_col], errors='coerce').fillna(0).astype(int) == 1]

                _t1_col = next((c for c in _cfp_res.columns if c.strip().upper() in ['TEAM1', 'AWAY', 'VISITOR']), 'TEAM1')
                _t2_col = next((c for c in _cfp_res.columns if c.strip().upper() in ['TEAM2', 'HOME']), 'TEAM2')
                _s1_col = next((c for c in _cfp_res.columns if c.strip().upper() in ['TEAM1_SCORE', 'AWAY SCORE', 'VIS SCORE']), 'TEAM1_SCORE')
                _s2_col = next((c for c in _cfp_res.columns if c.strip().upper() in ['TEAM2_SCORE', 'HOME SCORE']), 'TEAM2_SCORE')
                _rnd_col = next((c for c in _cfp_res.columns if c.strip().upper() in ['ROUND', 'WEEK']), 'ROUND')

                _user_teams_list = model_2041['TEAM'].unique()
                _headline_text = None

                # Read from bottom to top to guarantee we grab the MOST RECENT valid game
                for _, _cg in _cfp_res.iloc[::-1].iterrows():
                    _c_t1 = str(_cg[_t1_col]).strip()
                    _c_t2 = str(_cg[_t2_col]).strip()

                    if _c_t1 in _user_teams_list or _c_t2 in _user_teams_list:
                        _c_s1 = int(float(_cg[_s1_col]))
                        _c_s2 = int(float(_cg[_s2_col]))

                        # Skip if it's a 0-0 tie (an unplayed game mistakenly flagged as completed)
                        if _c_s1 == 0 and _c_s2 == 0:
                            continue

                        _round = str(_cg.get(_rnd_col, 'the playoffs')).strip()

                        _winner = _c_t1 if _c_s1 > _c_s2 else _c_t2
                        _loser = _c_t2 if _c_s1 > _c_s2 else _c_t1
                        _win_score = _c_s1 if _c_s1 > _c_s2 else _c_s2
                        _lose_score = _c_s2 if _c_s1 > _c_s2 else _c_s1

                        _w_user_df = model_2041[model_2041['TEAM'] == _winner]
                        _w_user = str(_w_user_df.iloc[0]['USER']) if not _w_user_df.empty else 'CPU'

                        _l_user_df = model_2041[model_2041['TEAM'] == _loser]
                        _l_user = str(_l_user_df.iloc[0]['USER']) if not _l_user_df.empty else 'CPU'

                        _winner_str = f"<strong>{_w_user}</strong> ({html.escape(_winner)})" if _w_user != 'CPU' else html.escape(_winner)
                        _loser_str = f"<strong>{_l_user}</strong> ({html.escape(_loser)})" if _l_user != 'CPU' else html.escape(_loser)

                        _round_lower = _round.lower()
                        if any(k in _round_lower for k in ['national title', 'championship', 'title game', 'final']):
                            _headline_text = f"The season is complete. {_winner_str} just beat " \
                                             f"{_loser_str} {_win_score}-{_lose_score} " \
                                             f"in {_round} to win the national title."
                        else:
                            _headline_text = f"The bracket is active. {_winner_str} just took down " \
                                             f"{_loser_str} {_win_score}-{_lose_score} " \
                                             f"in {_round}. Surviving and advancing is all that matters now."
                        break # We found the newest actual game, break the loop

                if _headline_text:
                    headlines.append(("🏟️", "Playoff Picture", _headline_text))
                else:
                    raise Exception("No user games completed in bracket")

            except Exception:
                # Fallback: Bracket hasn't started yet, show top seeds dictating pace
                _bt = model_2041.copy()
                _bt['_cfp_num'] = _bt['TEAM'].apply(lambda t: _get_live_rank(t, 99))
                _bowl_teams = _bt[_bt['_cfp_num'].fillna(99) <= 25].sort_values('_cfp_num')

                if not _bowl_teams.empty:
                    _status_notes = []
                    for _, _btr in _bowl_teams.head(4).iterrows():  # Top 4 ranked users
                        _bu = str(_btr['USER'])
                        _br = int(_btr['_cfp_num'])
                        _bw, _bl = _get_live_record(str(_btr['TEAM']), int(_btr.get('Current Record Wins', 0)), int(_btr.get('Current Record Losses', 0)))
                        _status_notes.append(f"#{_br} {_bu} ({_bw}-{_bl})")

                    if _status_notes:
                        headlines.append(("🏟️", "Playoff Picture",
                                          f"The top of the bracket is locked in. "
                                          f"{', '.join(_status_notes)} are currently dictating the pace of the postseason."))

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
        try:
            # LIVE RECRUITING OVERRIDE
            _live_rec_df = get_overall_recruiting_snapshot()
            if not _live_rec_df.empty:
                _live_rec_king = _live_rec_df.sort_values('Rank').iloc[0]
                _rk_team = str(_live_rec_king['Team'])
                _rk_user = str(_live_rec_king.get('User', ''))
                # Find user from model_2041 if missing
                if not _rk_user or _rk_user.lower() in ('nan', ''):
                    _u_match = model_2041[model_2041['TEAM'] == _rk_team]
                    _rk_user = str(_u_match.iloc[0]['USER']) if not _u_match.empty else 'CPU'

                _rk_pts = round(float(_live_rec_king.get('Points', 0)), 2)
                headlines.append(("🎯", "Recruiting King",
                                  f"<strong>{_rk_user}</strong> ({html.escape(_rk_team)}) is winning the "
                                  f"recruiting war with the #1 overall class ({_rk_pts} pts). "
                                  f"The roster that wins the natty in {CURRENT_YEAR + 2} starts with "
                                  f"who you're landing right now."))
            else:
                raise Exception("Fallback to static")
        except Exception:
            if 'Recruit Score' in model_2041.columns:
                _rk = model_2041.sort_values('Recruit Score', ascending=False).iloc[0]
                _rk_user = str(_rk['USER'])
                _rk_team = str(_rk['TEAM'])
                _rk_score = round(float(_rk['Recruit Score']), 1)
                headlines.append(("🎯", "Recruiting King",
                                  f"<strong>{_rk_user}</strong> ({html.escape(_rk_team)}) is winning the "
                                  f"recruiting war ({_rk_score} recruit score). "
                                  f"The roster that wins the natty in {CURRENT_YEAR + 2} starts with "
                                  f"who you're landing right now."))

            # ── 9. SPEED MERCHANTS ────────────────────────────────────────
        try:
            # LIVE SPEED OVERRIDE
            _sf_roster = pd.read_csv('cfb26_rosters_full.csv')
            if 'Season' in _sf_roster.columns:
                _sf_roster['Season'] = pd.to_numeric(_sf_roster['Season'], errors='coerce')
                _avail = _sf_roster['Season'].dropna().unique()
                _tgt = CURRENT_YEAR if CURRENT_YEAR in _avail else (int(max(_avail)) if len(_avail) else CURRENT_YEAR)
                _sf_roster = _sf_roster[_sf_roster['Season'] == _tgt].copy()
            _sf_roster['SPD'] = pd.to_numeric(_sf_roster['SPD'], errors='coerce')
            _sf_roster['ACC'] = pd.to_numeric(_sf_roster['ACC'], errors='coerce')

            # [ADDED] Load AGI and COD for the 4-Quad metric
            _sf_roster['AGI'] = pd.to_numeric(_sf_roster.get('AGI', pd.Series(dtype=float)), errors='coerce')
            _sf_roster['COD'] = pd.to_numeric(_sf_roster.get('COD', pd.Series(dtype=float)), errors='coerce')

            _sf_active = _sf_roster.copy()  # REDSHIRT filter removed

            _team_speeds = []
            for _t in model_2041['TEAM'].unique():
                _tdf = _sf_active[_sf_active['Team'] == _t]
                _s90 = int((_tdf['SPD'] >= 90).sum())
                _gen = int(((_tdf['SPD'] >= 96) | (_tdf['ACC'] >= 96)).sum())

                # [ADDED] Calculate 4-Quad (90+ SPD, ACC, AGI, COD)
                _quad = int(((_tdf['SPD'] >= 90) & (_tdf['ACC'] >= 90) & (_tdf['AGI'] >= 90) & (_tdf['COD'] >= 90)).sum())

                _team_speeds.append({'TEAM': _t, 'S90': _s90, 'GEN': _gen, 'QUAD': _quad})

            _live_speed_df = pd.DataFrame(_team_speeds).sort_values(['S90', 'GEN'], ascending=False)
            _sk = _live_speed_df.iloc[0]
            _sk_team = str(_sk['TEAM'])
            _sk_user = str(model_2041[model_2041['TEAM'] == _sk_team]['USER'].iloc[0])
            _sk_num = int(_sk['S90'])
            _sk_gen = int(_sk['GEN'])
            _sk_quad = int(_sk['QUAD'])  # [ADDED] Extract Quad count

            _gen_note = (f" including <strong>{_sk_gen} generational freak"
                         f"{'s' if _sk_gen != 1 else ''}</strong>") if _sk_gen > 0 else ""

            # [ADDED] Format the 4-Quad note string
            _quad_note = (f" and <strong>{_sk_quad} 4-Quad athlete"
                          f"{'s' if _sk_quad != 1 else ''}</strong>") if _sk_quad > 0 else ""

            # [ADDED] Inject {_quad_note} into the headline string
            headlines.append(("💨", "Speed Merchants",
                              f"<strong>{_sk_user}</strong> ({html.escape(_sk_team)}) leads with "
                              f"<strong>{_sk_num}</strong> active players at 90+ speed{_gen_note}{_quad_note}. "
                              f"You can scheme around a lot of things. "
                              f"You can't scheme around not being able to catch the other team's guys."))
        except Exception:
            if 'Team Speed (90+ Speed Guys)' in model_2041.columns:
                _sk = model_2041.sort_values('Team Speed (90+ Speed Guys)', ascending=False).iloc[0]
                _sk_user = str(_sk['USER'])
                _sk_team = str(_sk['TEAM'])
                _sk_num = int(_sk.get('Team Speed (90+ Speed Guys)', 0))
                _sk_gen = int(_sk.get('Generational (96+ speed or 96+ Acceleration)', 0))

                # [ADDED] Fallback logic for static data
                _sk_quad = int(_sk.get('Quad 90 (90+ SPD, ACC, AGI & COD)', 0))

                _gen_note = (f" including <strong>{_sk_gen} generational freak"
                             f"{'s' if _sk_gen != 1 else ''}</strong>") if _sk_gen > 0 else ""

                # [ADDED] Fallback note string
                _quad_note = (f" and <strong>{_sk_quad} 4-Quad athlete"
                              f"{'s' if _sk_quad != 1 else ''}</strong>") if _sk_quad > 0 else ""

                # [ADDED] Inject {_quad_note} into the fallback headline string
                headlines.append(("💨", "Speed Merchants",
                                  f"<strong>{_sk_user}</strong> ({html.escape(_sk_team)}) leads with "
                                  f"<strong>{_sk_num}</strong> players at 90+ speed{_gen_note}{_quad_note}. "
                                  f"You can scheme around a lot of things. "
                                  f"You can't scheme around not being able to catch the other team's guys."))

                         # ── [ADDED] HTML CARD RENDERER WITH HOVER GLOW & USER FALLBACK ────
        st.markdown("<br>", unsafe_allow_html=True)

        # Inject the CSS animation block for the cards
        st.markdown("""
        <style>
        .headline-card {
            display: flex;
            align-items: center;
            background-color: rgba(30, 30, 30, 0.6);
            border-left: 5px solid #ff4b4b;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            transition: all 0.3s ease;
        }
        .headline-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 15px rgba(255, 75, 75, 0.25);
            background-color: rgba(40, 40, 40, 0.8);
        }
        </style>
        """, unsafe_allow_html=True)

        for _hl_emoji, _hl_title, _hl_body in headlines:
            _team_name = ""
            _body_lower = _hl_body.lower()

            # 1. Try to find the team name from your active user dataframe
            for _t in model_2041['TEAM'].unique():
                _t_clean = str(_t).strip().lower()
                if f"({_t_clean})" in _body_lower or f"({html.escape(str(_t)).strip().lower()})" in _body_lower:
                    _team_name = _t
                    break

            # 2. User Fallback: If no team was found, look for the user's name
            if not _team_name:
                for _, _row in model_2041.iterrows():
                    _u = str(_row['USER']).strip()
                    if _u and _u.lower() not in ['nan', 'cpu', 'none', '']:
                        if f"<strong>{_u.lower()}</strong>" in _body_lower or f" {_u.lower()} " in _body_lower or _body_lower.startswith(f"{_u.lower()}"):
                            _team_name = str(_row['TEAM'])
                            break

            # 3. [ADDED] Global Fallback: If it's a CPU team like Nebraska, extract it directly from the text format!
            if not _team_name:
                import re
                _cpu_match = re.search(r'</strong> \((.*?)\)', _hl_body)
                if _cpu_match:
                    # Clean up any HTML escaping just in case (e.g., Texas A&amp;M)
                    _team_name = html.unescape(_cpu_match.group(1).strip())

            # Fetch the logo using the app's native asset pipeline
            _logo_uri = image_file_to_data_uri(get_logo_source(_team_name)) if _team_name else ""
            _img_html = f"<img src='{_logo_uri}' width='55' style='margin-right: 15px; border-radius: 5px; object-fit: contain;'>" if _logo_uri else ""

            # Use no indentation inside the HTML string to prevent Markdown code blocks
            _card_html = f"""<div class="headline-card">
{_img_html}
<div>
<h4 style="margin: 0; padding-bottom: 5px; font-size: 1.1rem; color: #ffffff;">
{_hl_emoji} {_hl_title}
</h4>
<p style="margin: 0; font-size: 0.9rem; color: #cccccc; line-height: 1.4;">
{_hl_body}
</p>
</div>
</div>"""
            st.markdown(_card_html, unsafe_allow_html=True)

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

                    diff_label = "Tier 3" if g['difficulty'] >= 50 else ("Tier 2" if g['difficulty'] >= 30 else "Tier 1")

                    cards_html += f"""
                    <div style='border-left:3px solid {tc};padding:6px 10px;margin-bottom:6px;background:#0f172a;border-radius:6px;'>
                      <div style='display:flex;justify-content:space-between;align-items:center;'>
                        <span style='font-weight:700;color:#f3f4f6;font-size:0.88rem;'>{diff_label} · {html.escape(g['location'])} {html.escape(opp_str)}</span>
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

        # ── Commissioner Tools ────────────────────────────────────────────────
        st.markdown("---")
        with st.expander("⚙️ Commissioner Tools", expanded=False):
            st.caption("Admin controls for advancing the season and syncing stats.")

            col_sync, col_ref = st.columns(2)

            with col_sync:
                if st.button("📊 Sync Stats", use_container_width=True,
                             key="comm_sync_stats",
                             help="Auto-derives CFP wins/losses, natty counts from CSVs"):
                    with st.spinner("Syncing…"):
                        _ok, _msgs = sync_derived_stats()
                    for _m in _msgs:
                        if _m.startswith("✅"):
                            st.success(_m)
                        elif _m.startswith("⚠️"):
                            st.warning(_m)
                        else:
                            st.error(_m)
                    if _ok:
                        st.cache_data.clear()

            with col_ref:
                if st.button("🔄 Refresh Data", use_container_width=True,
                             key="comm_refresh_data",
                             help="Clears cache and reloads all CSVs"):
                    st.cache_data.clear()
                    st.rerun()




    # --- WHO'S IN? ---
with tabs[3]:
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
                st.warning("⚠️ `cfp_rankings_history.csv` is empty — upload rows to the CSV to populate this board.")
        except Exception:
            st.warning("⚠️ `cfp_rankings_history.csv` not found — push the CSV to your repo to populate this board.")

        cfp_rankings = get_cfp_rankings_snapshot()
        cfp_board = build_cfp_bubble_board(cfp_rankings, model_2041)

               # ── 12-TEAM PLAYOFF LOGIC (5+7 MODEL) ───────────────────────────────
        # 1. Load the standings to map teams to their conferences
        try:
            conf_df = pd.read_csv(f'conf_standings_{int(CURRENT_YEAR)}.csv')
            conf_map = dict(zip(conf_df['TEAM'], conf_df['CONFERENCE']))
        except Exception:
            conf_map = {}
            
        cfp_board['Conference'] = cfp_board['Team'].map(conf_map)
        
        # 2. Sort the entire board strictly by Rank
        board_by_rank = cfp_board.sort_values('Rank', ascending=True).copy()
        
        # 3. Identify highest-ranked team in each conference as the projected champion
        conf_teams = board_by_rank.dropna(subset=['Conference'])
        if not conf_teams.empty:
            champs = conf_teams.drop_duplicates(subset=['Conference'], keep='first')
            
            # 4. The 5 highest-ranked champions are our Automatic Qualifiers (AQs)
            aq_champs = champs.head(5)
            
            # 5. Top 4 highest-ranked champs get the Byes (Seeds 1-4)
            top_4_byes = aq_champs.head(4).copy()
            
            # 6. The 5th AQ Champ goes into the At-Large pool to be seeded 5-12
            fifth_champ = aq_champs.tail(1).copy()
            
            # 7. Identify the At-Large pool (everyone else not in the top 5 champs)
            aq_names = aq_champs['Team'].tolist()
            remaining_pool = board_by_rank[~board_by_rank['Team'].isin(aq_names)]
            
            # 8. Take the 7 highest-ranked teams from the remaining pool
            at_large_bids = remaining_pool.head(7).copy()
            
            # 9. Combine the 5th Champ and the 7 At-Larges, and sort them purely by Rank for seeds 5-12
            seeds_5_to_12 = pd.concat([fifth_champ, at_large_bids]).sort_values('Rank', ascending=True)
            
            # 10. Build the final 12-team field!
            projected_field = pd.concat([top_4_byes, seeds_5_to_12]).reset_index(drop=True)
            projected_field['Projected Seed'] = range(1, 13)
        else:
            # Fallback if no conference data is found
            projected_field = board_by_rank.head(12).copy()
            projected_field['Projected Seed'] = range(1, 13)

        # Calculate seed scores (for internal model consistency)
        projected_field = compute_projected_seed_score(projected_field)

        # Push the corrected projected seeds back onto the full board
        cfp_board = compute_projected_seed_score(cfp_board)
        cfp_board['Projected Seed'] = np.nan
        seed_map = projected_field.set_index('Team')['Projected Seed'].to_dict()
        cfp_board['Projected Seed'] = cfp_board['Team'].map(seed_map)

        # First Four Out logic
        first_four_out = cfp_board[~cfp_board['Team'].isin(projected_field['Team'])].sort_values('Rank', ascending=True).head(4).copy()


        mobile_metrics([
            {"label": "🔒 Projected Locks",  "value": str(int((cfp_board['CFP Make %'] >= 92).sum()))},
            {"label": "📍 Last Team In",      "value": f"#{int(projected_field.iloc[-1]['Rank'])} {projected_field.iloc[-1]['Team']}"},
            {"label": "😬 First Team Out",    "value": f"#{int(first_four_out.iloc[0]['Rank'])} {first_four_out.iloc[0]['Team']}"},
            {"label": "🅱️ Best Bye Shot",     "value": f"{projected_field.sort_values('Bye %', ascending=False).iloc[0]['Team']}", "delta": format_pct(projected_field['Bye %'].max(), 1)},
        ])

        st.subheader('Projected CFP Field')
        projected_field_display = projected_field.copy()
        projected_field_display['Projected Seed Display'] = pd.to_numeric(
            projected_field_display['Projected Seed'] if 'Projected Seed' in projected_field_display.columns else 0,
            errors='coerce'
        ).fillna(999).astype(int)
        projected_field_display['Committee Rank Display'] = pd.to_numeric(
            projected_field_display['Rank'] if 'Rank' in projected_field_display.columns else 0,
            errors='coerce'
        ).fillna(999).astype(int)
        projected_field_display['Make CFP'] = projected_field_display['CFP Make %'] if 'CFP Make %' in projected_field_display.columns else 0
        projected_field_display['Bye Odds'] = projected_field_display['Bye %'] if 'Bye %' in projected_field_display.columns else 0
        projected_field_display['Auto-Bid Path'] = projected_field_display['Auto-Bid Path %'] if 'Auto-Bid Path %' in projected_field_display.columns else 0
        projected_field_display['Seed Score'] = projected_field_display['Score'] if 'Score' in projected_field_display.columns else 0
        if 'Bubble Tier' not in projected_field_display.columns:
            projected_field_display['Bubble Tier'] = ''
        if 'Record' not in projected_field_display.columns:
            projected_field_display['Record'] = ''
        projected_field_rows = []
        for _, row in projected_field_display.sort_values('Projected Seed Display', ascending=True).head(12).iterrows():
            team = str(row.get('Team', ''))
            primary = get_team_primary_color(team)
            logo_uri = image_file_to_data_uri(get_logo_source(team))
            logo_html = f"<img src='{logo_uri}' style='width:34px;height:34px;object-fit:contain;'/>" if logo_uri else "<div style='font-size:20px;'>🏈</div>"
            cells = [f"""
            <td class="isp-td-pin">
              <div class="isp-flex-row">
                <div style="font-weight:800;min-width:24px;text-align:center;color:#e5e7eb;">#{int(row.get('Projected Seed Display', 0))}</div>
                <div class="isp-td-num">{logo_html}</div>
                <div style="font-weight:800;color:{primary};">{html.escape(team)}</div>
              </div>
            </td>
            """]
            vals = [
                str(int(row.get('Committee Rank Display', 0))),
                html.escape(str(row.get('Record', ''))),
                format_pct(row.get('Make CFP', 0), 1),
                format_pct(row.get('Bye Odds', 0), 1),
                format_pct(row.get('Auto-Bid Path', 0), 1),
                html.escape(str(row.get('Bubble Tier', ''))),
                f"{float(pd.to_numeric(row.get('Seed Score', 0), errors='coerce') or 0):.2f}",
            ]
            for disp in vals:
                cells.append(f"<td style='padding:10px 12px;border-bottom:1px solid #334155;text-align:center;white-space:nowrap;color:#e5e7eb;'>{disp}</td>")
            projected_field_rows.append(f"<tr style='border-left:6px solid {primary};background:linear-gradient(90deg,{primary}22,rgba(15,23,42,.95) 14%);'>{''.join(cells)}</tr>")
        projected_field_html = f"""
        <div class="isp-table-wrap">
          <table class="isp-table">
            <thead>
              <tr class="isp-tr-header">
                <th class="isp-th isp-th-left">Projected Field</th>
                <th class="isp-th">Committee Rank</th>
                <th class="isp-th">Record</th>
                <th class="isp-th">Make CFP</th>
                <th class="isp-th">Bye Odds</th>
                <th class="isp-th">Auto-Bid Path</th>
                <th class="isp-th">Bubble Tier</th>
                <th class="isp-th">Seed Score</th>
              </tr>
            </thead>
            <tbody>{''.join(projected_field_rows)}</tbody>
          </table>
        </div>
        """
        st.markdown(projected_field_html, unsafe_allow_html=True)

        st.subheader('First Four Out')
        render_first_four_out(first_four_out)

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
            actual_bracket = resolve_playoff_bracket_results(bracket_field, CURRENT_YEAR)
            st.success("📋 Showing **official bracket** — saved to repo. Persists across sessions. Re-enter above to update.")
            render_playoff_bracket(bracket_field, actual_results=actual_bracket)
        else:
            st.caption("📊 Showing **projected bracket** — enter the official field above once the CFP announces.")
            render_playoff_bracket(projected_field)

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
with tabs[4]:
    # ── Year selector ─────────────────────────────────────────────────────
    try:
        _rec_all_years = _load_recruiting_csv()
        _rec_years_avail = sorted(
            _rec_all_years['Year'].dropna().unique().astype(int).tolist(), reverse=True
        ) if not _rec_all_years.empty and 'Year' in _rec_all_years.columns else [CURRENT_YEAR]
    except Exception:
        _rec_years_avail = [CURRENT_YEAR]

    if CURRENT_YEAR not in _rec_years_avail:
        _rec_years_avail = [CURRENT_YEAR] + _rec_years_avail

    _rec_year_col, _rec_spacer = st.columns([1, 3])
    with _rec_year_col:
        recruit_year = st.selectbox(
            "Season", _rec_years_avail,
            index=0,
            key="recruit_year_select",
            label_visibility="collapsed"
        )

    st.header(f"🏈 {recruit_year} Recruiting Final Rankings")
    st.caption("Final class rankings — high school, portal, and overall. Uses the uploaded recruiting history CSVs automatically.")

    # ── Load recruiting snapshots from history CSVs ──────────────────────
    _hs_df = get_hs_recruiting_snapshot(recruit_year)
    _portal_df = get_portal_recruiting_snapshot(recruit_year)
    _overall_df = get_overall_recruiting_snapshot(recruit_year)

    def _empty_recruit_df():
        return pd.DataFrame(columns=[
            'Rank', 'Team', 'User', 'TotalCommits', 'FiveStar', 'FourStar',
            'ThreeStar', 'TwoStar', 'OneStar', 'Points', 'BlueChipRatio', 'Logo'
        ])

    def _prep_recruit_df(df):
        if df is None or df.empty:
            return _empty_recruit_df()

        df = df.copy()
        defaults = {
            'Rank': 0,
            'Team': '',
            'User': '',
            'TotalCommits': 0,
            'FiveStar': 0,
            'FourStar': 0,
            'ThreeStar': 0,
            'TwoStar': 0,
            'OneStar': 0,
            'Points': 0.0,
        }
        for col, default in defaults.items():
            if col not in df.columns:
                df[col] = default

        df['Rank'] = pd.to_numeric(df['Rank'], errors='coerce').fillna(0).astype(int)
        for col in ['TotalCommits', 'FiveStar', 'FourStar', 'ThreeStar', 'TwoStar', 'OneStar']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        df['Points'] = pd.to_numeric(df['Points'], errors='coerce').fillna(0.0)
        df['Team'] = df['Team'].astype(str).str.strip()
        df['User'] = df['User'].fillna('').astype(str).str.strip()

        if 'BlueChipRatio' not in df.columns:
            df['BlueChipRatio'] = ((df['FiveStar'] + df['FourStar']) / df['TotalCommits'].replace(0, 1)).round(3)
        else:
            df['BlueChipRatio'] = pd.to_numeric(df['BlueChipRatio'], errors='coerce').fillna(0.0)

        if 'Logo' not in df.columns:
            df['Logo'] = df['Team'].apply(get_logo_source)

        return df.sort_values(['Rank', 'Points'], ascending=[True, False]).reset_index(drop=True)

    _hs_df = _prep_recruit_df(_hs_df)
    _portal_df = _prep_recruit_df(_portal_df)
    _overall_df = _prep_recruit_df(_overall_df)

    if _hs_df.empty and _portal_df.empty and _overall_df.empty:
        st.warning(f"No recruiting data found for {recruit_year}.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("HS Teams Ranked", len(_hs_df))
        with c2:
            st.metric("Portal Teams Ranked", len(_portal_df))
        with c3:
            st.metric("Overall Teams Ranked", len(_overall_df))
        with c4:
            st.metric("Year", recruit_year)

    st.markdown("---")

    # ── USER TEAMS SPOTLIGHT ──────────────────────────────────────────────
    st.subheader(f"👑 User Coaches — {recruit_year} Class Snapshot")
    _user_teams_map = {
        str(r['USER']).strip(): str(r['TEAM']).strip()
        for _, r in model_2041.iterrows()
    }
    _team_to_user = {team: user for user, team in _user_teams_map.items()}

    for _df in (_hs_df, _portal_df, _overall_df):
        if not _df.empty:
            _df['User'] = _df['Team'].astype(str).str.strip().map(_team_to_user).fillna('')

    _hs_lookup = {str(r['Team']).strip(): r for _, r in _hs_df.iterrows()}
    _portal_lookup = {str(r['Team']).strip(): r for _, r in _portal_df.iterrows()}
    _overall_lookup = {str(r['Team']).strip(): r for _, r in _overall_df.iterrows()}

    def _row_has_recruit_data(_row):
        if _row is None:
            return False
        try:
            _pts = pd.to_numeric(_row.get('Points', np.nan), errors='coerce')
        except Exception:
            _pts = np.nan
        try:
            _commits = pd.to_numeric(_row.get('TotalCommits', np.nan), errors='coerce')
        except Exception:
            _commits = np.nan
        return (pd.notna(_pts) and float(_pts) > 0) or (pd.notna(_commits) and float(_commits) > 0)

    _user_rows = []
    for _usr, _tm in sorted(_user_teams_map.items()):
        _hs_row = _hs_lookup.get(_tm)
        _portal_row = _portal_lookup.get(_tm)
        _overall_row = _overall_lookup.get(_tm)
        _effective_overall_row = _overall_row if _row_has_recruit_data(_overall_row) else _hs_row
        _user_rows.append({
            'Coach': _usr,
            'Team': _tm,
            'HS Rank': int(_hs_row['Rank']) if _hs_row is not None and pd.notna(_hs_row['Rank']) else None,
            'HS Points': round(float(_hs_row['Points']), 2) if _hs_row is not None and pd.notna(_hs_row['Points']) else 0.0,
            'Portal Rank': int(_portal_row['Rank']) if _portal_row is not None and pd.notna(_portal_row['Rank']) else None,
            'Portal Points': round(float(_portal_row['Points']), 2) if _portal_row is not None and pd.notna(_portal_row['Points']) else 0.0,
            'Overall Rank': int(_effective_overall_row['Rank']) if _effective_overall_row is not None and pd.notna(_effective_overall_row['Rank']) else None,
            'Overall Points': round(float(_effective_overall_row['Points']), 2) if _effective_overall_row is not None and pd.notna(_effective_overall_row['Points']) else 0.0,
            'Total Commits': int(_effective_overall_row['TotalCommits']) if _effective_overall_row is not None and pd.notna(_effective_overall_row['TotalCommits']) else 0,
            '5★': int(_effective_overall_row['FiveStar']) if _effective_overall_row is not None and pd.notna(_effective_overall_row['FiveStar']) else 0,
            '4★': int(_effective_overall_row['FourStar']) if _effective_overall_row is not None and pd.notna(_effective_overall_row['FourStar']) else 0,
            '3★': int(_effective_overall_row['ThreeStar']) if _effective_overall_row is not None and pd.notna(_effective_overall_row['ThreeStar']) else 0,
            'Blue Chip %': round(float(_effective_overall_row['BlueChipRatio']) * 100, 1) if _effective_overall_row is not None and pd.notna(_effective_overall_row.get('BlueChipRatio', np.nan)) else 0.0,
        })

    if _user_rows:
        _user_df = pd.DataFrame(_user_rows).sort_values(['Overall Rank', 'HS Rank'], ascending=[True, True], na_position='last')

        def _fmt_rank(val):
            try:
                if pd.isna(val):
                    return '—'
                return f"#{int(val)}"
            except Exception:
                return '—'

        def _fmt_points(val):
            try:
                return f"{float(val):.2f}"
            except Exception:
                return '0.00'

        _cards_html = ["""<style>
.recruit-user-grid {
    display:grid;
    grid-template-columns:repeat(auto-fit,minmax(260px,1fr));
    gap:12px;
    margin:8px 0 4px 0;
}
.recruit-user-card {
    border-radius:16px;
    padding:14px;
    background:linear-gradient(145deg,#0f172a 0%,#1e293b 100%);
    border:1px solid rgba(148,163,184,.22);
    box-shadow:0 8px 22px rgba(0,0,0,.18);
    min-width:0;
}
.recruit-user-top {
    display:flex;
    align-items:center;
    gap:12px;
    margin-bottom:12px;
}
.recruit-user-logo-wrap {
    width:58px;
    height:58px;
    border-radius:14px;
    display:flex;
    align-items:center;
    justify-content:center;
    flex-shrink:0;
    background:rgba(255,255,255,.04);
    border:1px solid rgba(255,255,255,.08);
}
.recruit-user-logo-wrap img {
    width:44px;
    height:44px;
    object-fit:contain;
}
.recruit-user-coach {
    font-size:.75rem;
    font-weight:800;
    color:#94a3b8;
    letter-spacing:.04em;
    text-transform:uppercase;
}
.recruit-user-team {
    font-size:1.05rem;
    font-weight:900;
    line-height:1.1;
}
.recruit-user-rankline {
    font-size:.78rem;
    color:#cbd5e1;
    margin-top:3px;
}
.recruit-user-metrics {
    display:grid;
    grid-template-columns:repeat(3,minmax(0,1fr));
    gap:8px;
    margin-bottom:10px;
}
.recruit-user-metric {
    background:rgba(15,23,42,.85);
    border:1px solid rgba(51,65,85,.9);
    border-radius:10px;
    padding:8px 8px 7px 8px;
    text-align:center;
    min-width:0;
}
.recruit-user-metric-value {
    font-size:1rem;
    font-weight:900;
    color:#f8fafc;
    line-height:1.1;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
}
.recruit-user-metric-label {
    font-size:.63rem;
    color:#94a3b8;
    font-weight:700;
    letter-spacing:.04em;
    text-transform:uppercase;
    margin-top:3px;
}
.recruit-user-bottom {
    display:grid;
    grid-template-columns:repeat(4,minmax(0,1fr));
    gap:8px;
    margin-bottom:10px;
}
.recruit-user-chip {
    background:rgba(255,255,255,.04);
    border:1px solid rgba(148,163,184,.18);
    border-radius:999px;
    padding:5px 8px;
    text-align:center;
    font-size:.73rem;
    color:#e2e8f0;
    font-weight:800;
    white-space:nowrap;
    overflow:hidden;
    text-overflow:ellipsis;
}
.recruit-user-footer {
    font-size:.76rem;
    color:#cbd5e1;
    display:flex;
    justify-content:space-between;
    gap:8px;
    flex-wrap:wrap;
}
@media (max-width: 640px) {
    .recruit-user-grid { grid-template-columns:1fr; gap:10px; }
    .recruit-user-card { padding:12px; }
    .recruit-user-metrics { grid-template-columns:repeat(3,minmax(0,1fr)); gap:6px; }
    .recruit-user-bottom { grid-template-columns:repeat(4,minmax(0,1fr)); gap:6px; }
    .recruit-user-metric-value { font-size:.92rem; }
    .recruit-user-chip { font-size:.68rem; padding:5px 6px; }
}
</style>
<div class='recruit-user-grid'>"""]

        for _, _r in _user_df.iterrows():
            _team = str(_r['Team']).strip()
            _coach = str(_r['Coach']).strip()
            _primary = get_team_primary_color(_team)
            _secondary = get_team_secondary_color(_team)
            _logo_uri = image_file_to_data_uri(get_logo_source(_team))
            _logo_html = f"<img src='{_logo_uri}' alt='{html.escape(_team)} logo'/>" if _logo_uri else "<span style='font-size:28px;'>🏈</span>"
            _card_html = (
                f"<div class='recruit-user-card' style='border-left:5px solid {_primary};'>"
                f"<div class='recruit-user-top'>"
                f"<div class='recruit-user-logo-wrap' style='box-shadow:inset 0 0 0 1px {_primary}33;'>{_logo_html}</div>"
                f"<div style='min-width:0;'>"
                f"<div class='recruit-user-coach'>{html.escape(_coach)}</div>"
                f"<div class='recruit-user-team' style='color:{_primary};'>{html.escape(_team)}</div>"
                f"<div class='recruit-user-rankline'>Overall {_fmt_rank(_r['Overall Rank'])} · HS {_fmt_rank(_r['HS Rank'])} · Portal {_fmt_rank(_r['Portal Rank'])}</div>"
                f"</div>"
                f"</div>"
                f"<div class='recruit-user-metrics'>"
                f"<div class='recruit-user-metric'><div class='recruit-user-metric-value'>{_fmt_points(_r['Overall Points'])}</div><div class='recruit-user-metric-label'>Overall Pts</div></div>"
                f"<div class='recruit-user-metric'><div class='recruit-user-metric-value'>{int(_r['Total Commits'])}</div><div class='recruit-user-metric-label'>Commits</div></div>"
                f"<div class='recruit-user-metric'><div class='recruit-user-metric-value'>{float(_r['Blue Chip %']):.1f}%</div><div class='recruit-user-metric-label'>Blue Chip</div></div>"
                f"</div>"
                f"<div class='recruit-user-bottom'>"
                f"<div class='recruit-user-chip'>5★ {int(_r['5★'])}</div>"
                f"<div class='recruit-user-chip'>4★ {int(_r['4★'])}</div>"
                f"<div class='recruit-user-chip'>3★ {int(_r['3★'])}</div>"
                f"<div class='recruit-user-chip'>HS {_fmt_points(_r['HS Points'])}</div>"
                f"</div>"
                f"<div class='recruit-user-footer'>"
                f"<span>Portal Pts: <strong style='color:{_secondary if _secondary != '#FFFFFF' else '#f8fafc'};'>{_fmt_points(_r['Portal Points'])}</strong></span>"
                f"<span>Class Year: <strong>{recruit_year}</strong></span>"
                f"</div>"
                f"</div>"
            )
            _cards_html.append(_card_html)

        _cards_html.append("</div>")
        st.markdown(''.join(_cards_html), unsafe_allow_html=True)
    else:
        st.caption("No user teams found in model_2041.")

    st.markdown("---")

    # ── CLASS RANKS HIGHER ───────────────────────────────────────────────
    recruit_tabs = st.tabs(["🏫 High School", "🔁 Transfer Portal", "📊 Overall"])

    with recruit_tabs[0]:
        st.subheader(f"{recruit_year} High School Recruiting Rankings")
        if _hs_df.empty:
            st.info("No high school recruiting data available.")
        else:
            hs_display = _hs_df.rename(columns={
                'TotalCommits': 'Total',
                'FiveStar': '5★',
                'FourStar': '4★',
                'ThreeStar': '3★',
                'TwoStar': '2★',
                'OneStar': '1★',
                'BlueChipRatio': 'Blue Chip Ratio',
            })
            render_recruiting_snapshot_table(hs_display[['Rank', 'Team', 'Total', '5★', '4★', '3★', 'Points', 'Blue Chip Ratio']])
            with st.expander("Show full HS table"):
                st.dataframe(hs_display, hide_index=True, use_container_width=True)

    with recruit_tabs[1]:
        st.subheader(f"{recruit_year} Transfer Portal Rankings")
        if _portal_df.empty:
            st.info("No transfer portal recruiting data available for this year.")
        else:
            portal_display = _portal_df.rename(columns={
                'TotalCommits': 'Total',
                'FiveStar': '5★',
                'FourStar': '4★',
                'ThreeStar': '3★',
                'TwoStar': '2★',
                'OneStar': '1★',
                'BlueChipRatio': 'Blue Chip Ratio',
            })
            render_recruiting_snapshot_table(portal_display[['Rank', 'Team', 'Total', '5★', '4★', '3★', 'Points', 'Blue Chip Ratio']])
            with st.expander("Show full portal table"):
                st.dataframe(portal_display, hide_index=True, use_container_width=True)

    with recruit_tabs[2]:
        st.subheader(f"{recruit_year} Overall Recruiting Rankings")
        if _overall_df.empty:
            st.info("No overall recruiting data available.")
        else:
            overall_display = _overall_df.rename(columns={
                'TotalCommits': 'Total',
                'FiveStar': '5★',
                'FourStar': '4★',
                'ThreeStar': '3★',
                'TwoStar': '2★',
                'OneStar': '1★',
                'BlueChipRatio': 'Blue Chip Ratio',
            })
            render_recruiting_snapshot_table(overall_display[['Rank', 'Team', 'Total', '5★', '4★', '3★', 'Points', 'Blue Chip Ratio']])
            with st.expander("Show full overall table"):
                st.dataframe(overall_display, hide_index=True, use_container_width=True)

    st.markdown("---")

    # ── COACH HISTORY AT BOTTOM ─────────────────────────────────────────
    st.subheader("🕰️ Coach Recruiting History")
    st.caption("Pick a current user coach to see every school they have coached and the class ranks they posted there over time. Lower rank = better class.")

    _history_year_cols = [c for c in rec.columns if str(c).isdigit()] if rec is not None and not rec.empty else []
    if _history_year_cols:
        _history_year_cols = sorted(_history_year_cols, key=lambda x: int(str(x)))
        _rec_hist = rec.copy()
        _rec_hist['USER'] = _rec_hist['USER'].astype(str).str.strip().str.title()
        _rec_hist['Teams'] = _rec_hist['Teams'].astype(str).str.strip().map(normalize_history_team_name)

        _history_users = sorted(_user_teams_map.keys())
        _hist_user = st.selectbox(
            "Choose a coach",
            _history_users,
            key="coach_recruiting_history_user"
        )

        _coach_rows = _rec_hist[_rec_hist['USER'] == _hist_user].copy()
        if _coach_rows.empty:
            st.caption("No recruiting history found for that coach in recruiting.csv.")
        else:
            _school_cards = []
            for _, _hr in _coach_rows.iterrows():
                _hist_team = str(_hr.get('Teams', '')).strip()
                if not _hist_team or _hist_team.lower() == 'nan':
                    continue

                _year_vals = []
                for _yc in _history_year_cols:
                    _v = _hr.get(_yc)
                    if pd.notna(_v) and str(_v).strip() not in ('', 'nan', '-', '--'):
                        try:
                            _rank_val = int(float(_v))
                            _year_vals.append({'Year': int(_yc), 'Class Rank': _rank_val})
                        except Exception:
                            pass

                if not _year_vals:
                    continue

                _hist_df = pd.DataFrame(_year_vals).sort_values('Year', ascending=False).reset_index(drop=True)
                _best_rank = int(_hist_df['Class Rank'].min())
                _latest_rank = int(_hist_df.iloc[0]['Class Rank'])
                _years_span = sorted(_hist_df['Year'].astype(int).tolist())

                if len(_years_span) == 1:
                    _years_label = str(_years_span[0])
                else:
                    _years_label = f"{_years_span[0]}–{_years_span[-1]}"

                _school_cards.append({
                    'team': _hist_team,
                    'df': _hist_df,
                    'best_rank': _best_rank,
                    'latest_rank': _latest_rank,
                    'years_label': _years_label,
                    'classes': len(_hist_df),
                })

            if not _school_cards:
                st.caption("No historical class ranks found for that coach.")
            else:
                _school_cards = sorted(_school_cards, key=lambda x: x['df']['Year'].min())

                st.markdown(f"#### {_hist_user}'s class-by-class results")

                for _card in _school_cards:
                    st.markdown(
                        f"**{_card['team']}** — Best: #{_card['best_rank']} · "
                        f"Latest: #{_card['latest_rank']} · Years: {_card['years_label']} · "
                        f"Classes: {_card['classes']}"
                    )
                    st.dataframe(_card['df'], hide_index=True, use_container_width=True)
    else:
        st.caption("No recruiting history columns were found in recruiting.csv.")

    # --- H2H MATRIX ---
with tabs[10]:
        st.header("⚔️ Head-to-Head Matrix")
        st.caption("All-time user vs. user records. Net Edge = wins minus losses. Rivalry Score weights game count and balance.")

        # ── FULL GRID — one card per matchup cell ─────────────────────────────────
        st.subheader("📊 All-Time H2H Grid")

        # Build sorted user list with current team info for logo + color
        _h2h_user_info = {}
        for _, _mr in model_2041.iterrows():
            _h2h_user_info[str(_mr['USER'])] = {
                'team': str(_mr['TEAM']),
                'color': get_team_primary_color(str(_mr['TEAM'])),
                'logo_uri': image_file_to_data_uri(get_logo_source(str(_mr['TEAM']))),
            }

        _h2h_users = sorted(all_users)

        # Header row — opponent logos
        _header_cells = "<td style='padding:6px;'></td>"
        for _opp in _h2h_users:
            _opp_info = _h2h_user_info.get(_opp, {})
            _opp_tc   = _opp_info.get('color', '#6b7280')
            _opp_lu   = _opp_info.get('logo_uri', '')
            _logo_tag  = (f"<img src='{_opp_lu}' style='width:28px;height:28px;"
                          f"object-fit:contain;'/>" if _opp_lu else "🏈")
            _header_cells += (
                f"<td style='text-align:center;padding:6px;'>"
                f"<div style='display:flex;flex-direction:column;align-items:center;gap:2px;'>"
                f"{_logo_tag}"
                f"<span style='font-size:0.6rem;color:{_opp_tc};font-weight:700;white-space:nowrap;'>"
                f"{html.escape(_opp)}</span></div></td>"
            )

        # Data rows
        _data_rows = ""
        for _usr in _h2h_users:
            _usr_info = _h2h_user_info.get(_usr, {})
            _usr_tc   = _usr_info.get('color', '#6b7280')
            _usr_lu   = _usr_info.get('logo_uri', '')
            _usr_logo = (f"<img src='{_usr_lu}' style='width:28px;height:28px;"
                         f"object-fit:contain;'/>" if _usr_lu else "🏈")

            _row_cells = (
                f"<td style='padding:6px 8px;white-space:nowrap;border-right:1px solid #1e293b;'>"
                f"<div style='display:flex;align-items:center;gap:6px;'>"
                f"{_usr_logo}"
                f"<span style='font-size:0.72rem;font-weight:700;color:{_usr_tc};'>"
                f"{html.escape(_usr)}</span></div></td>"
            )

            _usr_h2h_row = h2h_df[h2h_df['User'] == _usr]

            for _opp in _h2h_users:
                if _usr == _opp:
                    _row_cells += (
                        "<td style='text-align:center;padding:6px;"
                        "background:#1e293b;'>"
                        "<span style='color:#374151;font-size:1rem;'>&#8212;</span></td>"
                    )
                    continue
                try:
                    _rec = _usr_h2h_row[_opp].iloc[0] if not _usr_h2h_row.empty else "0-0"
                    _net = int(h2h_heat.loc[_usr, _opp])
                    _parts = str(_rec).split('-')
                    _w = int(_parts[0]) if len(_parts) == 2 else 0
                    _l = int(_parts[1]) if len(_parts) == 2 else 0
                except Exception:
                    _rec, _w, _l, _net = "0-0", 0, 0, 0
                _cell_bg = ("#0d2b0d" if _net > 0 else
                            "#2b0d0d" if _net < 0 else "#111827")
                _rec_color = ("#22c55e" if _net > 0 else
                              "#f87171" if _net < 0 else "#94a3b8")
                _net_str = (f"+{_net}" if _net > 0 else
                            str(_net) if _net < 0 else "Even")
                _row_cells += (
                    f"<td style='text-align:center;padding:6px 8px;"
                    f"background:{_cell_bg};'>"
                    f"<div style='font-weight:900;font-size:0.82rem;color:{_rec_color};'>"
                    f"{html.escape(str(_rec))}</div>"
                    f"<div style='font-size:0.58rem;color:#475569;'>{_net_str}</div>"
                    f"</td>"
                )
            _data_rows += f"<tr style='border-bottom:1px solid #0f172a;'>{_row_cells}</tr>"

        st.markdown(
            f"<div style='overflow-x:auto;border:1px solid #1e293b;"
            f"border-radius:12px;background:#0f172a;'>"
            f"<table style='width:100%;border-collapse:collapse;font-size:13px;'>"
            f"<thead><tr style='background:#111827;'>{_header_cells}</tr></thead>"
            f"<tbody>{_data_rows}</tbody></table></div>",
            unsafe_allow_html=True
        )

        # ── RIVALRY METER ───────────────────────────────────────────────────────────
        st.markdown("---")
        st.subheader("🔥 Rivalry Meter")
        if not rivalry_df.empty:
            _sorted_riv = rivalry_df.sort_values(
                ['Rivalry Score', 'Games'], ascending=[False, False])
            for _, _rv in _sorted_riv.iterrows():
                _matchup_parts = str(_rv['Matchup']).split(' vs ')
                _ua = _matchup_parts[0].strip() if len(_matchup_parts) == 2 else str(_rv['Matchup'])
                _ub = _matchup_parts[1].strip() if len(_matchup_parts) == 2 else ''
                _ia = _h2h_user_info.get(_ua, {})
                _ib = _h2h_user_info.get(_ub, {})
                _ca = _ia.get('color', '#6b7280')
                _cb = _ib.get('color', '#6b7280')
                _la = _ia.get('logo_uri', '')
                _lb = _ib.get('logo_uri', '')
                _logo_a = (f"<img src='{_la}' style='width:32px;height:32px;"
                           f"object-fit:contain;'/>" if _la else "🏈")
                _logo_b = (f"<img src='{_lb}' style='width:32px;height:32px;"
                           f"object-fit:contain;'/>" if _lb else "🏈")
                _wa = int(_rv.get(_ua, 0)) if _ua in _rv else 0
                _wb = int(_rv.get(_ub, 0)) if _ub in _rv else 0
                _riv_score = float(_rv.get('Rivalry Score', 0))
                _avg_margin = float(_rv.get('Avg Margin', 0))
                _games = int(_rv.get('Games', 0))
                _heat = ("🔥🔥🔥" if _riv_score >= 25 else
                         "🔥🔥" if _riv_score >= 15 else "🔥")
                _bar_pct_a = int((_wa / max(_games, 1)) * 100)
                st.markdown(
                    f"<div style='background:#111827;border:1px solid #1e293b;"
                    f"border-radius:12px;padding:14px 16px;margin-bottom:8px;'>"
                    f"<div style='display:flex;align-items:center;gap:10px;flex-wrap:wrap;"
                    f"margin-bottom:10px;'>"
                    f"<div style='display:flex;align-items:center;gap:8px;flex:1;min-width:100px;'>"
                    f"{_logo_a}"
                    f"<span style='font-weight:900;color:{_ca};font-size:0.9rem;'>"
                    f"{html.escape(_ua)}</span></div>"
                    f"<div style='text-align:center;min-width:60px;'>"
                    f"<div style='font-size:0.65rem;color:#475569;'>{_games} games</div>"
                    f"<div style='font-size:1.1rem;font-weight:900;color:#f1f5f9;'>"
                    f"{_wa} &ndash; {_wb}</div>"
                    f"<div style='font-size:0.65rem;color:#64748b;'>"
                    f"avg &#177;{_avg_margin:.1f}</div></div>"
                    f"<div style='display:flex;align-items:center;gap:8px;flex:1;"
                    f"justify-content:flex-end;min-width:100px;'>"
                    f"<span style='font-weight:900;color:{_cb};font-size:0.9rem;'>"
                    f"{html.escape(_ub)}</span>"
                    f"{_logo_b}</div></div>"
                    f"<div style='display:flex;align-items:center;gap:8px;'>"
                    f"<div style='flex:1;background:#0f172a;border-radius:999px;height:6px;overflow:hidden;'>"
                    f"<div style='width:{_bar_pct_a}%;height:100%;background:{_ca};"
                    f"border-radius:999px;'></div></div>"
                    f"<span style='font-size:0.72rem;color:#fbbf24;font-weight:700;white-space:nowrap;'>"
                    f"{_heat} {_riv_score:.0f} pts</span></div></div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("No rivalry data available yet.")

        # ── 1-on-1 DRILLDOWN ────────────────────────────────────────────────────────
        st.markdown("---")
        st.subheader("🔍 1-on-1 Drilldown")
        _drill_user = st.selectbox(
            "Select a coach", _h2h_users, key="h2h_select")
        _drill_info = _h2h_user_info.get(_drill_user, {})
        _drill_tc   = _drill_info.get('color', '#6b7280')
        _drill_lu   = _drill_info.get('logo_uri', '')
        _drill_logo = (f"<img src='{_drill_lu}' style='width:36px;height:36px;"
                       f"object-fit:contain;'/>" if _drill_lu else "🏈")

        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;"
            f"padding:10px 14px;background:linear-gradient(90deg,{_drill_tc}1a,#0f172a);"
            f"border:1px solid {_drill_tc}44;border-left:4px solid {_drill_tc};"
            f"border-radius:10px;margin-bottom:12px;'>"
            f"{_drill_logo}"
            f"<span style='font-weight:900;font-size:1rem;color:{_drill_tc};'>"
            f"{html.escape(_drill_user)}</span>"
            f"<span style='font-size:0.75rem;color:#64748b;margin-left:4px;'>"
            f"&mdash; {html.escape(_drill_info.get('team', ''))}</span>"
            f"</div>",
            unsafe_allow_html=True
        )

        _drill_row = h2h_df[h2h_df['User'] == _drill_user]
        for _opp in sorted(all_users):
            if _opp == _drill_user:
                continue
            _opp_info2 = _h2h_user_info.get(_opp, {})
            _opp_tc2   = _opp_info2.get('color', '#6b7280')
            _opp_lu2   = _opp_info2.get('logo_uri', '')
            _opp_logo2 = (f"<img src='{_opp_lu2}' style='width:28px;height:28px;"
                          f"object-fit:contain;'/>" if _opp_lu2 else "🏈")
            try:
                _rec2  = _drill_row[_opp].iloc[0] if not _drill_row.empty else "0-0"
                _net2  = int(h2h_heat.loc[_drill_user, _opp])
                _parts2 = str(_rec2).split('-')
                _w2 = int(_parts2[0]) if len(_parts2) == 2 else 0
                _l2 = int(_parts2[1]) if len(_parts2) == 2 else 0
            except Exception:
                _rec2, _w2, _l2, _net2 = "0-0", 0, 0, 0
            _net_c2 = ("#22c55e" if _net2 > 0 else
                       "#f87171" if _net2 < 0 else "#94a3b8")
            _net_s2 = f"+{_net2}" if _net2 > 0 else str(_net2)
            _edge_label = ("LEADS" if _net2 > 0 else
                           "TRAILS" if _net2 < 0 else "EVEN")
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:10px;"
                f"padding:10px 14px;background:#111827;border:1px solid #1e293b;"
                f"border-radius:10px;margin-bottom:6px;flex-wrap:wrap;'>"
                f"<div style='display:flex;align-items:center;gap:6px;flex:1;"
                f"min-width:100px;'>{_opp_logo2}"
                f"<span style='font-weight:700;color:{_opp_tc2};'>"
                f"{html.escape(_opp)}</span></div>"
                f"<div style='font-weight:900;font-size:1.1rem;color:#f1f5f9;'>"
                f"{_w2} &ndash; {_l2}</div>"
                f"<div style='text-align:right;min-width:80px;'>"
                f"<span style='font-weight:800;color:{_net_c2};font-size:0.8rem;'>"
                f"{_net_s2} &nbsp;"
                f"<span style='font-size:0.65rem;'>{_edge_label}</span></span>"
                f"</div></div>",
                unsafe_allow_html=True
            )

# --- SEASON RECAP ---
with tabs[6]:
    st.header("📺 Season Recap")
    sel_year = int(st.selectbox("Select Season", years, key="season_year"))
    y_data = scores[scores[meta['yr']].astype(int) == sel_year].copy()

    # 1. DATA LOADING & STAT ENGINE
    try:
        ovr_col = next((c for c in model_2041.columns if 'OVR' in str(c).upper() or 'OVERALL' in str(c).upper()), None)
        team_col = next((c for c in model_2041.columns if 'TEAM' in str(c).upper()), 'TEAM')
        _ratings = dict(zip(model_2041[team_col].str.strip(), pd.to_numeric(model_2041[ovr_col], errors='coerce').fillna(0))) if ovr_col else {}
        
        heisman_all = pd.read_csv('Heisman_Finalists.csv')
        heisman_all = heisman_all[heisman_all['YEAR'].astype(int) == sel_year].copy()
    except:
        _ratings = {}; heisman_all = pd.DataFrame()

    def format_heisman_stats(row):
        """Builds a position-specific stat line from CSV columns."""
        pos = str(row.get('POS', '')).upper()
        parts = []
        
        def _fmt(val, label):
            if pd.notnull(val) and val != 0:
                # Format as int if possible
                return f"{int(val)} {label}"
            return None

        if pos == 'QB':
            parts += [f"{_fmt(row.get('PASS_YDS'), 'Yds')}", f"{_fmt(row.get('PASS_TD'), 'TD')}", f"{_fmt(row.get('PASS_INT'), 'Int')}"]
            r_yds = _fmt(row.get('RUSH_YDS'), 'Rush Yds')
            if r_yds: parts.append(r_yds)
        elif pos in ['HB', 'RB']:
            parts += [f"{_fmt(row.get('RUSH_YDS'), 'Yds')}", f"{_fmt(row.get('RUSH_TD'), 'TD')}", f"{_fmt(row.get('REC_YDS'), 'Rec Yds')}"]
        elif pos in ['WR', 'TE']:
            parts += [f"{_fmt(row.get('CATCHES'), 'Rec')}", f"{_fmt(row.get('REC_YDS'), 'Yds')}", f"{_fmt(row.get('REC_TD'), 'TD')}"]
        
        # Filter out Nones and join
        valid_parts = [p for p in parts if p and 'None' not in p]
        return " | ".join(valid_parts) if valid_parts else "Stats Pending"

    # 2. HELPER FUNCTIONS
    def _award_logo_tag(team, size=48):
        uri = image_file_to_data_uri(get_logo_source(team)) if team else None
        return f"<img src='{uri}' style='width:{size}px;height:{size}px;object-fit:contain;'/>" if uri else "🏈"

    def _award_card(accent, logo_tag, badge, line1, line2, line3='', stats=''):
        stat_div = f"<div style='margin-top:8px; padding-top:6px; border-top:1px solid {accent}33; font-size:0.7rem; color:#f1f5f9; font-family:monospace; font-weight:600;'>{html.escape(stats)}</div>" if stats else ""
        return (
            f"<div style='background:linear-gradient(135deg,{accent}22,#0f172a); border:1px solid {accent}55; border-radius:12px; padding:14px 16px; display:flex; align-items:center; gap:12px;'>"
            f"{logo_tag}<div style='min-width:0;'><div style='font-size:0.6rem; color:#94a3b8; letter-spacing:.08em; font-weight:700; margin-bottom:3px;'>{badge}</div>"
            f"<div style='font-weight:900; color:{accent}; font-size:0.92rem; line-height:1.25; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{html.escape(line1)}</div>"
            f"<div style='font-size:0.72rem; color:#94a3b8; margin-top:1px;'>{html.escape(line2)}</div>{line3 if line3 else ''}{stat_div}</div></div>"
        )

    # 3. AWARDS LOGIC
    award_champ = "TBD"; champ_team = ""; path_to_title = []
    try:
        _b_results = pd.read_csv('CFPbracketresults.csv')
        _ncg = _b_results[(_b_results['YEAR'].astype(int) == sel_year) & (_b_results['ROUND'].str.strip() == 'NCG') & (_b_results['COMPLETED'] == 1)]
        if not _ncg.empty:
            award_champ = str(_ncg.iloc[0]['WINNER']).strip()
            champ_team = award_champ
            _my_wins = _b_results[(_b_results['YEAR'].astype(int) == sel_year) & (_b_results['WINNER'].str.strip() == champ_team) & (_b_results['COMPLETED'] == 1)]
            _rd_order = {'R1': 1, 'QF': 2, 'SF': 3, 'NCG': 4}
            _my_wins = _my_wins.copy(); _my_wins['_rd_sort'] = _my_wins['ROUND'].str.strip().map(_rd_order); _my_wins = _my_wins.sort_values('_rd_sort')
            for _, _wg in _my_wins.iterrows():
                _is_t1 = str(_wg['TEAM1']).strip() == champ_team
                _opp = str(_wg['TEAM2']).strip() if _is_t1 else str(_wg['TEAM1']).strip()
                _my_s, _opp_s = (int(_wg['TEAM1_SCORE']), int(_wg['TEAM2_SCORE'])) if _is_t1 else (int(_wg['TEAM2_SCORE']), int(_wg['TEAM1_SCORE']))
                path_to_title.append(f"{str(_wg['ROUND']).strip()}: def. {_opp} ({_my_s}-{_opp_s})")
    except: pass

    # Heisman Banner
    if not heisman_all.empty:
        _winner_row = heisman_all[heisman_all['FINISH'].astype(int) == 1].iloc[0]
        he_p = f"{str(_winner_row['NAME'])} ({str(_winner_row.get('POS', '—'))})"
        he_t, he_u = str(_winner_row['TEAM']), str(_winner_row.get('USER', ''))
        he_stats = format_heisman_stats(_winner_row)
    else: he_p, he_t, he_u, he_stats = "TBD", "", "", ""

    coty_row = coty[coty[meta['c_yr']].astype(int) == sel_year]
    co_c = str(coty_row.iloc[0][meta['c_coach']]) if not coty_row.empty else "TBD"
    co_t = str(coty_row.iloc[0][meta['c_school']]) if not coty_row.empty else ""

    # 4. RENDER BANNER
    _c_col, _h_col, _ct_col = [get_team_primary_color(t) if t else '#fbbf24' for t in [champ_team, he_t, co_t]]
    path_html = "".join([f"<div style='font-size:0.62rem; color:#94a3b8; line-height:1.2; margin-top:1px;'>• {p}</div>" for p in path_to_title])
    if path_html: path_html = f"<div style='margin-top:8px; border-top:1px solid {_c_col}33; padding-top:6px;'>{path_html}</div>"

    awards_html = (
        "<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:10px; margin-bottom:16px;'>"
        + _award_card(_c_col, _award_logo_tag(champ_team, 52), "🏆 NATIONAL CHAMPION", award_champ, "", line3=path_html)
        + _award_card(_h_col, _award_logo_tag(he_t, 52), "🏅 HEISMAN WINNER", he_p, f"{he_t} ({he_u})", stats=he_stats)
        + _award_card(_ct_col, _award_logo_tag(co_t, 52), "🎓 COACH OF THE YEAR", co_c, f"{co_t}")
        + "</div>"
    )
    st.markdown(awards_html, unsafe_allow_html=True)

    # 5. USER BATTLES (Upset Detection)
    if not y_data.empty:
        user_games = y_data[(y_data['V_User_Final'].astype(str).str.upper() != 'CPU') & (y_data['H_User_Final'].astype(str).str.upper() != 'CPU') & (y_data['V_User_Final'] != y_data['H_User_Final'])].copy()
        if not user_games.empty:
            st.markdown(f"#### ⚔️ User Battles of {sel_year}")
            for _, _g in user_games.iterrows():
                vt, ht = str(_g['Visitor_Final']).strip(), str(_g['Home_Final']).strip()
                v_ovr, h_ovr = _ratings.get(vt, 0), _ratings.get(ht, 0)
                is_upset = (int(_g['V_Pts']) > int(_g['H_Pts']) and v_ovr < h_ovr - 2) or (int(_g['H_Pts']) > int(_g['V_Pts']) and h_ovr < v_ovr - 2)
                badge = f"<span style='background:#ef4444;color:white;font-size:0.6rem;padding:2px 6px;border-radius:4px;margin-left:8px;font-weight:900;'>🔥 UPSET (+{abs(v_ovr-h_ovr)})</span>" if is_upset else ""
                st.markdown(f"<div style='display:flex;align-items:center;gap:8px;padding:8px 10px;background:#0a1628;border-radius:8px;border:1px solid #1e293b;margin-bottom:5px;'>"
                            f"<div style='display:flex;align-items:center;gap:6px;flex:1;'>{_award_logo_tag(vt, 28)}<div><div style='color:{get_team_primary_color(vt)};font-size:0.8rem;font-weight:800;'>{html.escape(vt)}</div><div style='font-size:0.62rem;color:#475569;'>{int(v_ovr)} OVR</div></div></div>"
                            f"<div style='text-align:center;min-width:110px;'><div style='font-weight:900;font-size:1.1rem;color:#f1f5f9;'>{int(_g['V_Pts'])} &ndash; {int(_g['H_Pts'])}</div>{badge}</div>"
                            f"<div style='display:flex;align-items:center;gap:6px;flex:1;justify-content:flex-end;'><div style='text-align:right;'><div style='color:{get_team_primary_color(ht)};font-size:0.8rem;font-weight:800;'>{html.escape(ht)}</div><div style='font-size:0.62rem;color:#475569;'>{int(h_ovr)} OVR</div></div>{_award_logo_tag(ht, 28)}</div></div>", unsafe_allow_html=True)

    # 6. HEISMAN LEADERBOARD (Vertical Stack with Custom Stats)
    if not heisman_all.empty:
        st.markdown("#### 🏆 Heisman Voting Results")
        leaderboard = heisman_all.sort_values('FINISH')
        
        for idx, _f in leaderboard.head(5).reset_index(drop=True).iterrows():
            _ft = str(_f['TEAM']).strip()
            _f_color = get_team_primary_color(_ft)
            _finish = int(_f['FINISH'])
            _stats = format_heisman_stats(_f)
            
            _bg = "#1e293b" if _finish == 1 else "#0f172a"
            _bw = "6px" if _finish == 1 else "4px"
            stat_html = f"<div style='margin-top:8px; padding-top:6px; border-top:1px solid {_f_color}33; font-size:0.75rem; color:#cbd5e1; font-family:monospace; font-weight:600;'>📊 {_stats}</div>" if _stats else ""

            st.markdown(f"""
            <div style='background:{_bg}; border:1px solid #1e293b; border-left:{_bw} solid {_f_color}; border-radius:10px; padding:14px 18px; display:flex; align-items:center; gap:12px; margin-bottom:8px;'>
              <div style='flex-shrink:0; background:#0a1628; padding:4px; border-radius:6px;'>{_award_logo_tag(_ft, size=34)}</div>
              <div style='flex:1; min-width:0;'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                  <div style='font-weight:900; font-size:1.05rem; color:white;'>{html.escape(str(_f['NAME']))} {"👑" if _finish == 1 else ""}</div>
                  <div style='font-weight:800; color:{_f_color if _finish == 1 else "#94a3b8"}; font-size:0.95rem;'>#{_finish}</div>
                </div>
                <div style='font-size:0.75rem; color:#94a3b8; margin-top:2px;'>{html.escape(_ft)} • {str(_f.get('POS','—'))} • {str(_f.get('USER','CPU'))}</div>
                {stat_html}
              </div>
            </div>""", unsafe_allow_html=True)

# --- 2041 ALL-AMERICANS ---
    st.markdown("---")
    st.subheader("🏅 2041 All-Americans")

    try:
        aa_df = pd.read_csv("all_americans.csv")
    except Exception:
        aa_df = pd.DataFrame(columns=["Year", "TeamType", "Pos", "Player", "School", "Class"])

    for col in ["Year", "TeamType", "Pos", "Player", "School", "Class"]:
        if col not in aa_df.columns:
            aa_df[col] = pd.NA

    aa_df["Year"] = pd.to_numeric(aa_df["Year"], errors="coerce")
    aa_df["TeamType"] = (
        aa_df["TeamType"]
        .astype(str)
        .str.strip()
        .replace({
            "First Team": "1st Team",
            "Second Team": "2nd Team",
            "Freshman Team": "Freshman"
        })
    )
    aa_df["Pos"] = aa_df["Pos"].astype(str).str.strip()
    aa_df["Player"] = aa_df["Player"].astype(str).str.strip()
    aa_df["School"] = aa_df["School"].astype(str).str.strip()
    aa_df["Class"] = aa_df["Class"].astype(str).str.strip()

    user_team_map = USER_TEAMS if 'USER_TEAMS' in globals() else {}
    team_to_user = {str(team).strip(): str(user).strip() for user, team in user_team_map.items()}
    user_team_set = set(team_to_user.keys())

    def get_school_logo_src(team_name):
        try:
            logo_path = get_logo_source(team_name)
            if logo_path:
                uri = image_file_to_data_uri(logo_path)
                if uri:
                    return uri
        except Exception:
            pass
        return None

    def prep_aa_table(df_in):
        if df_in.empty:
            return df_in

        out = df_in.copy()
        out.insert(0, "Logo", out["School"].map(get_school_logo_src))
        out["User"] = out["School"].map(lambda x: team_to_user.get(str(x).strip(), ""))
        return out

    recap_year = sel_year
    aa_year_df = aa_df[aa_df["Year"] == recap_year].copy()

    if aa_year_df.empty:
        st.caption("No All-Americans logged for this season yet.")
    else:
        aa_tabs = st.tabs(["🥇 1st Team", "🥈 2nd Team", "🌟 Freshman"])

        with aa_tabs[0]:
            first_df = prep_aa_table(aa_year_df[aa_year_df["TeamType"] == "1st Team"].copy())
            if first_df.empty:
                st.caption("No 1st Team rows found.")
            else:
                st.dataframe(
                    first_df[["Logo", "Pos", "Player", "School", "Class", "User"]],
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Logo": st.column_config.ImageColumn(""),
                        "Pos": st.column_config.TextColumn("Pos", width="small"),
                        "Player": st.column_config.TextColumn("Player", width="medium"),
                        "School": st.column_config.TextColumn("School", width="medium"),
                        "Class": st.column_config.TextColumn("Class", width="small"),
                        "User": st.column_config.TextColumn("User", width="small"),
                    }
                )

        with aa_tabs[1]:
            second_df = prep_aa_table(aa_year_df[aa_year_df["TeamType"] == "2nd Team"].copy())
            if second_df.empty:
                st.caption("No 2nd Team rows found.")
            else:
                st.dataframe(
                    second_df[["Logo", "Pos", "Player", "School", "Class", "User"]],
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Logo": st.column_config.ImageColumn(""),
                        "Pos": st.column_config.TextColumn("Pos", width="small"),
                        "Player": st.column_config.TextColumn("Player", width="medium"),
                        "School": st.column_config.TextColumn("School", width="medium"),
                        "Class": st.column_config.TextColumn("Class", width="small"),
                        "User": st.column_config.TextColumn("User", width="small"),
                    }
                )

        with aa_tabs[2]:
            fresh_df = prep_aa_table(aa_year_df[aa_year_df["TeamType"] == "Freshman"].copy())
            if fresh_df.empty:
                st.caption("No Freshman rows found.")
            else:
                st.dataframe(
                    fresh_df[["Logo", "Pos", "Player", "School", "Class", "User"]],
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Logo": st.column_config.ImageColumn(""),
                        "Pos": st.column_config.TextColumn("Pos", width="small"),
                        "Player": st.column_config.TextColumn("Player", width="medium"),
                        "School": st.column_config.TextColumn("School", width="medium"),
                        "Class": st.column_config.TextColumn("Class", width="small"),
                        "User": st.column_config.TextColumn("User", width="small"),
                    }
                )

    # --- TEAM OVERVIEW ---


# --- SPEED FREAKS ---
with tabs[7]:
    st.header("🔍 Speed Freaks")
    st.caption("Team speed, cheat-code athletes, and where the juice actually lives on the roster.")

    _sf_df = model_2041.copy() if 'model_2041' in globals() else pd.DataFrame()

    if _sf_df is None or _sf_df.empty:
        st.info("No Speed Freaks data available.")
    else:
        _sf_df = _sf_df.copy()

        _required_defaults = {
            'USER': '',
            'TEAM': '',
            'Team Speed Score': 0,
            'Speedometer': 0,
            'TEAM SPEED Rank': 0,
            'Team Speed (90+ Speed Guys)': 0,
            'Quad 90 (90+ SPD, ACC, AGI & COD)': 0,
            'Generational (96+ speed or 96+ Acceleration)': 0,
            'Off Speed (90+ speed)': 0,
            'Def Speed (90+ speed)': 0,
            'Monsters': 0,
            'Quick Hogs': 0,
            'Where is the Speed?': 'Balanced',
        }
        for _col, _default in _required_defaults.items():
            if _col not in _sf_df.columns:
                _sf_df[_col] = _default

        for _num_col in [
            'Team Speed Score', 'Speedometer', 'TEAM SPEED Rank',
            'Team Speed (90+ Speed Guys)', 'Quad 90 (90+ SPD, ACC, AGI & COD)',
            'Generational (96+ speed or 96+ Acceleration)',
            'Off Speed (90+ speed)', 'Def Speed (90+ speed)', 'Monsters', 'Quick Hogs'
        ]:
            _sf_df[_num_col] = pd.to_numeric(_sf_df[_num_col], errors='coerce').fillna(0)

        try:
            _sf_roster = pd.read_csv('cfb26_rosters_full.csv')
            if 'Season' in _sf_roster.columns:
                _sf_roster['Season'] = pd.to_numeric(_sf_roster['Season'], errors='coerce')
                _avail = _sf_roster['Season'].dropna().unique()
                _tgt = CURRENT_YEAR if CURRENT_YEAR in _avail else (int(max(_avail)) if len(_avail) else CURRENT_YEAR)
                _sf_roster = _sf_roster[_sf_roster['Season'] == _tgt].copy()
            _sf_roster['SPD'] = pd.to_numeric(_sf_roster.get('SPD'), errors='coerce')
            _sf_roster['ACC'] = pd.to_numeric(_sf_roster.get('ACC'), errors='coerce')
            _sf_roster['AGI'] = pd.to_numeric(_sf_roster.get('AGI'), errors='coerce')
            _sf_roster['COD'] = pd.to_numeric(_sf_roster.get('COD'), errors='coerce')
            _sf_roster['STR'] = pd.to_numeric(_sf_roster.get('STR'), errors='coerce')
            _sf_roster['REDSHIRT'] = pd.to_numeric(_sf_roster.get('REDSHIRT', 0), errors='coerce').fillna(0).astype(int)
            _sf_roster['PosNorm'] = _sf_roster.get('Pos', '').astype(str).str.upper().str.strip()
            _sf_active = _sf_roster.copy()  # REDSHIRT filter removed

            _front7 = {'DT', 'LEDG', 'REDG', 'SAM', 'MIKE', 'WILL'}
            _ol = {'LT', 'LG', 'C', 'RG', 'RT'}

            _live_rows = []
            for _t in _sf_df['TEAM'].dropna().astype(str).unique():
                _tdf = _sf_active[_sf_active['Team'].astype(str) == _t].copy()

                _s90 = int((_tdf['SPD'] >= 90).sum())
                _gen = int(((_tdf['SPD'] >= 96) | (_tdf['ACC'] >= 96)).sum())
                _quad = int(((_tdf['SPD'] >= 90) & (_tdf['ACC'] >= 90) & (_tdf['AGI'] >= 90) & (_tdf['COD'] >= 90)).sum())
                _mon = int(((_tdf['PosNorm'].isin(_front7)) & (((_tdf['ACC'] >= 90) & (_tdf['SPD'] >= 84)) | ((_tdf['SPD'] >= 90) & (_tdf['ACC'] >= 84)))).sum())
                _qh = int(((_tdf['PosNorm'].isin(_ol)) & (_tdf['AGI'] >= 85) & (_tdf['STR'] >= 90)).sum())
                _off = int(((_tdf['SPD'] >= 90) & (_tdf['PosNorm'].isin({'QB', 'HB', 'RB', 'WR', 'TE', 'LT', 'LG', 'C', 'RG', 'RT'}))).sum())
                _def = int(((_tdf['SPD'] >= 90) & (_tdf['PosNorm'].isin({'DT', 'LEDG', 'REDG', 'SAM', 'MIKE', 'WILL', 'CB', 'FS', 'SS', 'S'}))).sum())

                _live_rows.append({
                    'TEAM': _t,
                    'Team Speed (90+ Speed Guys)': _s90,
                    'Quad 90 (90+ SPD, ACC, AGI & COD)': _quad,
                    'Cheat Codes': _quad,
                    'Generational (96+ speed or 96+ Acceleration)': _gen,
                    'Monsters': _mon,
                    'Quick Hogs': _qh,
                    'Off Speed (90+ speed)': _off,
                    'Def Speed (90+ speed)': _def,
                })

            _live_speed_df = pd.DataFrame(_live_rows)
            if not _live_speed_df.empty:
                _sf_df = _sf_df.drop(columns=[
                    'Team Speed (90+ Speed Guys)', 'Quad 90 (90+ SPD, ACC, AGI & COD)',
                    'Generational (96+ speed or 96+ Acceleration)', 'Monsters', 'Quick Hogs',
                    'Off Speed (90+ speed)', 'Def Speed (90+ speed)'
                ], errors='ignore').merge(_live_speed_df, on='TEAM', how='left')

                for _num_col in [
                    'Team Speed (90+ Speed Guys)', 'Quad 90 (90+ SPD, ACC, AGI & COD)',
                    'Generational (96+ speed or 96+ Acceleration)', 'Monsters', 'Quick Hogs',
                    'Off Speed (90+ speed)', 'Def Speed (90+ speed)'
                ]:
                    _sf_df[_num_col] = pd.to_numeric(_sf_df[_num_col], errors='coerce').fillna(0)

                _sf_df['Team Speed Score'] = (
                    _sf_df['Team Speed (90+ Speed Guys)'] * 2.2
                    + _sf_df['Off Speed (90+ speed)'] * 1.0
                    + _sf_df['Def Speed (90+ speed)'] * 1.0
                    + _sf_df['Quad 90 (90+ SPD, ACC, AGI & COD)'] * 2.5
                    + _sf_df['Monsters'] * 1.4
                    + _sf_df['Quick Hogs'] * 1.2
                ) * (
                    1
                    + _sf_df['Generational (96+ speed or 96+ Acceleration)'] * 0.16
                    + _sf_df['Quad 90 (90+ SPD, ACC, AGI & COD)'] * 0.07
                )
                _sf_df['Team Speed Score'] = _sf_df['Team Speed Score'].round(1)

        except Exception:
            pass

        if 'team_speed_to_mph' in globals():
            _sf_df['Speedometer'] = _sf_df['Team Speed Score'].apply(team_speed_to_mph)

        def _where_is_the_speed(row):
            _off_fast = pd.to_numeric(row.get('Off Speed (90+ speed)', 0), errors='coerce')
            _def_fast = pd.to_numeric(row.get('Def Speed (90+ speed)', 0), errors='coerce')
            _mph = pd.to_numeric(row.get('Speedometer', np.nan), errors='coerce')
            if _off_fast <= 5 and _def_fast <= 5 and (not pd.isna(_mph)) and _mph < 65:
                return 'Non-Existent'
            if _off_fast > 5 and _def_fast > 5:
                return 'Off & Def'
            if _off_fast > 5:
                return 'Offense'
            if _def_fast > 5:
                return 'Defense'
            return 'Balanced'

        _sf_df['Where is the Speed?'] = _sf_df.apply(_where_is_the_speed, axis=1)

        _sf_df = _sf_df.sort_values(
            ['Team Speed Score', 'Quad 90 (90+ SPD, ACC, AGI & COD)', 'Monsters', 'TEAM'],
            ascending=[False, False, False, True]
        ).reset_index(drop=True)
        _sf_df['TEAM SPEED Rank'] = range(1, len(_sf_df) + 1)

        _leader = _sf_df.iloc[0]
        _most_gen = _sf_df.sort_values(
            ['Generational (96+ speed or 96+ Acceleration)', 'Team Speed Score'],
            ascending=[False, False]
        ).iloc[0]
        _most_quad = _sf_df.sort_values(
            ['Quad 90 (90+ SPD, ACC, AGI & COD)', 'Team Speed Score'],
            ascending=[False, False]
        ).iloc[0]
        _most_mon = _sf_df.sort_values(
            ['Monsters', 'Team Speed Score'],
            ascending=[False, False]
        ).iloc[0]

        mobile_metrics([
            {"label": "⚡ Speed King", "value": str(_leader.get('USER', '—')), "delta": f"{float(_leader.get('Speedometer', 0)):.1f} MPH"},
            {"label": "🎮 Cheat Codes", "value": str(_most_quad.get('USER', '—')), "delta": f"{int(_most_quad.get('Quad 90 (90+ SPD, ACC, AGI & COD)', 0))} cheat codes"},
            {"label": "👹 Monsters", "value": str(_most_mon.get('USER', '—')), "delta": f"{int(_most_mon.get('Monsters', 0))} monsters"},
            {"label": "🧬 Most Freaks", "value": str(_most_gen.get('USER', '—')), "delta": f"{int(_most_gen.get('Generational (96+ speed or 96+ Acceleration)', 0))} generational"},
        ], cols_desktop=4)

        st.markdown(
            """
            <div style="background:rgba(15,23,42,0.70); border:1px solid rgba(148,163,184,0.18); border-radius:12px; padding:12px 14px; margin-top:10px; margin-bottom:14px;">
              <div style="font-weight:800; color:#f8fafc; margin-bottom:8px;">Speed Freaks Key</div>
              <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:8px; font-size:0.9rem; color:#cbd5e1;">
                <div><strong>Cheat Code</strong>: 90+ SPD, 90+ ACC, 90+ AGI, and 90+ COD.</div>
                <div><strong>Monster</strong>: DT / EDGE / LB with 90+ ACC and 84+ SPD, or 90+ SPD and 84+ ACC.</div>
                <div><strong>Quick Hog</strong>: OL with 85+ AGI and 90+ STR.</div>
                <div><strong>Generational Freak</strong>: any player with 96+ SPD or 96+ ACC.</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("---")
        render_speed_freaks_table(_sf_df)

        st.markdown("---")
        _scatter_df = _sf_df.copy()
        _natty_col = 'Natty Odds' if 'Natty Odds' in _scatter_df.columns else ('Preseason Natty Odds' if 'Preseason Natty Odds' in _scatter_df.columns else None)
        _scatter_needed = ['USER', 'TEAM', 'Speedometer']
        if _natty_col and all(c in _scatter_df.columns for c in _scatter_needed):
            _keep_cols = _scatter_needed + [_natty_col] + [c for c in [
                'Quad 90 (90+ SPD, ACC, AGI & COD)',
                'Monsters',
                'Quick Hogs',
                'Generational (96+ speed or 96+ Acceleration)'
            ] if c in _scatter_df.columns]
            _scatter_df = _scatter_df[_keep_cols].copy()

            _scatter_df['Speedometer'] = pd.to_numeric(_scatter_df['Speedometer'], errors='coerce')
            _scatter_df[_natty_col] = pd.to_numeric(_scatter_df[_natty_col], errors='coerce')
            _scatter_df = _scatter_df.dropna(subset=['Speedometer', _natty_col]).copy()

            if not _scatter_df.empty:
                _scatter_df['TeamLabel'] = _scatter_df['USER'].astype(str) + " • " + _scatter_df['TEAM'].astype(str)
                _scatter_df['LogoSrc'] = None

                def _sf_logo_src(_team):
                    try:
                        if 'get_school_logo_src' in globals():
                            _src = get_school_logo_src(_team)
                            if _src:
                                return _src
                        if 'get_logo_source' in globals() and 'image_file_to_data_uri' in globals():
                            _path = get_logo_source(_team)
                            if _path:
                                try:
                                    return image_file_to_data_uri(_path)
                                except Exception:
                                    return _path
                    except Exception:
                        return None
                    return None

                _scatter_df['LogoSrc'] = _scatter_df['TEAM'].apply(_sf_logo_src)

                _x_min = max(0, float(_scatter_df['Speedometer'].min()) - 12)
                _x_max = float(_scatter_df['Speedometer'].max()) + 12
                _y_min = max(0, float(_scatter_df[_natty_col].min()) - 2)
                _y_max = float(_scatter_df[_natty_col].max()) + 3

                _speed_style_fig = go.Figure()

                _speed_style_fig.add_trace(
                    go.Scatter(
                        x=_scatter_df['Speedometer'],
                        y=_scatter_df[_natty_col],
                        mode='markers',
                        marker=dict(size=1, color='rgba(0,0,0,0)'),
                        hovertemplate=(
                            "<b>%{customdata[0]}</b><br>"
                            "MPH: %{x:.1f}<br>"
                            "National Title Odds: %{y:.1f}%<br>"
                            "Cheat Codes: %{customdata[1]}<br>"
                            "Monsters: %{customdata[2]}<br>"
                            "Quick Hogs: %{customdata[3]}<br>"
                            "Generational Freaks: %{customdata[4]}<extra></extra>"
                        ),
                        customdata=_scatter_df[[
                            'TeamLabel',
                            'Quad 90 (90+ SPD, ACC, AGI & COD)',
                            'Monsters',
                            'Quick Hogs',
                            'Generational (96+ speed or 96+ Acceleration)'
                        ]].fillna(0).values
                    )
                )

                for _, _r in _scatter_df.iterrows():
                    _logo = _r.get('LogoSrc')
                    if isinstance(_logo, str) and _logo.strip():
                        _speed_style_fig.add_layout_image(
                            dict(
                                source=_logo,
                                x=float(_r['Speedometer']),
                                y=float(_r[_natty_col]),
                                xref='x',
                                yref='y',
                                sizex=max(6.0, (_x_max - _x_min) * 0.05),
                                sizey=max(1.6, (_y_max - _y_min) * 0.09),
                                xanchor='center',
                                yanchor='middle',
                                layer='above'
                            )
                        )
                    else:
                        _speed_style_fig.add_trace(
                            go.Scatter(
                                x=[float(_r['Speedometer'])],
                                y=[float(_r[_natty_col])],
                                mode='text',
                                text=[str(_r['TEAM'])],
                                textfont=dict(size=11, color='rgba(60,60,60,0.95)'),
                                hoverinfo='skip',
                                showlegend=False
                            )
                        )

                _speed_style_fig.update_layout(
                    height=700,
                    paper_bgcolor='#efefef',
                    plot_bgcolor='#efefef',
                    margin=dict(l=40, r=30, t=120, b=80),
                    showlegend=False,
                    font=dict(color='#111111', family='Arial, sans-serif'),
                    title=dict(
                        text="<b>More Juice, More Title Hope</b><br><span style='font-size:18px;'>Speed Freaks data plotted as MPH versus National Title odds.</span>",
                        x=0.5,
                        xanchor='center',
                        y=0.96,
                        yanchor='top',
                        font=dict(size=28, color='#111111')
                    ),
                    xaxis=dict(
                        title='MPH',
                        range=[_x_min, _x_max],
                        showgrid=False,
                        zeroline=False,
                        tickfont=dict(size=13, color='#111111'),
                        title_font=dict(size=18, color='#111111')
                    ),
                    yaxis=dict(
                        title='National Title Odds',
                        ticksuffix='%',
                        range=[_y_min, _y_max],
                        showgrid=False,
                        zeroline=False,
                        tickfont=dict(size=13, color='#111111'),
                        title_font=dict(size=18, color='#111111')
                    ),
                    annotations=[
                        dict(
                            xref='paper', yref='paper', x=0.01, y=0.86,
                            text="Logos show each user team's spot on the board.",
                            showarrow=False, font=dict(size=13, color='#333333'), align='left'
                        ),
                        dict(
                            xref='paper', yref='paper', x=0.01, y=-0.12,
                            text="Chart: ChatGPT • Source: Speed Freaks roster metrics + live natty odds",
                            showarrow=False, font=dict(size=12, color='#444444'), align='left'
                        )
                    ]
                )

                st.plotly_chart(_speed_style_fig, use_container_width=True, config={'displayModeBar': False})

        st.markdown("---")
        _show_cols = [
            c for c in [
                'TEAM SPEED Rank', 'USER', 'TEAM', 'Speedometer', 'Team Speed Score',
                'Team Speed (90+ Speed Guys)', 'Quad 90 (90+ SPD, ACC, AGI & COD)',
                'Monsters', 'Quick Hogs', 'Generational (96+ speed or 96+ Acceleration)',
                'Off Speed (90+ speed)', 'Def Speed (90+ speed)', 'Where is the Speed?'
            ] if c in _sf_df.columns
        ]

        _table_df = _sf_df[_show_cols].copy()
        if 'Speedometer' in _table_df.columns:
            _table_df['Speedometer'] = _table_df['Speedometer'].map(lambda v: f"{float(v):.1f} MPH" if pd.notna(v) else '—')
        if 'Team Speed Score' in _table_df.columns:
            _table_df['Team Speed Score'] = _table_df['Team Speed Score'].map(lambda v: f"{float(v):.1f}" if pd.notna(v) else '—')

        rename_map = {
            'TEAM SPEED Rank': 'Rank',
            'USER': 'Coach',
            'TEAM': 'Team',
            'Speedometer': 'Speedometer',
            'Team Speed Score': 'Speed Score',
            'Team Speed (90+ Speed Guys)': '90+ Speed',
            'Quad 90 (90+ SPD, ACC, AGI & COD)': 'Cheat Codes',
            'Monsters': 'Monsters',
            'Quick Hogs': 'Quick Hogs',
            'Generational (96+ speed or 96+ Acceleration)': 'Generational Freaks',
            'Off Speed (90+ speed)': 'Off Speed',
            'Def Speed (90+ speed)': 'Def Speed',
            'Where is the Speed?': 'Speed Location',
        }
        _table_df = _table_df.rename(columns=rename_map)
        st.dataframe(_table_df, hide_index=True, use_container_width=True)


with tabs[9]:
        st.header("🏛️ Coach Legacy")
        st.caption("Career arc by coach across all schools. Powered by CPUscores_MASTER.csv, CFPbracketresults.csv, champs.csv, COTY.csv, recruiting_class_history_all.csv, and preseason_expectations_history.csv.")

        if st.session_state.pop("_jump_to_team_analysis", False):
            components.html("""
            <script>
            setTimeout(function() {
                try {
                    var tabs = window.parent.document.querySelectorAll('[data-baseweb="tab"]');
                    if (tabs && tabs[9]) { tabs[9].click(); }
                } catch(e) {}
            }, 150);
            </script>
            """, height=0)

        def _smart(df, cols):
            return smart_col(df, cols) if 'smart_col' in globals() else next((c for c in cols if c in df.columns), None)

        def _safe_num(s):
            return pd.to_numeric(s, errors='coerce')

        def _load_first(paths):
            for p in paths:
                try:
                    _df = pd.read_csv(p)
                    if not _df.empty:
                        return _df
                except Exception:
                    continue
            return pd.DataFrame()

        # ── Source files ──────────────────────────────────────────────────────
        legacy_scores = scores.copy() if 'scores' in globals() and isinstance(scores, pd.DataFrame) else pd.DataFrame()
        legacy_scores.columns = [str(c).strip() for c in legacy_scores.columns]

        legacy_champs = champs.copy() if 'champs' in globals() and isinstance(champs, pd.DataFrame) else pd.DataFrame()
        legacy_champs.columns = [str(c).strip() for c in legacy_champs.columns]

        legacy_coty = coty.copy() if 'coty' in globals() and isinstance(coty, pd.DataFrame) else pd.DataFrame()
        legacy_coty.columns = [str(c).strip() for c in legacy_coty.columns]

        legacy_ratings = ratings.copy() if 'ratings' in globals() and isinstance(ratings, pd.DataFrame) else pd.DataFrame()
        legacy_ratings.columns = [str(c).strip() for c in legacy_ratings.columns]

        preseason_exp = _load_first([
            'preseason_expectations_history.csv',
            'preseason_expectations_history_userteams_fixed.csv',
            'preseason_expectations_history_monsters_updated.csv',
            'preseason_expectations_history_final.csv',
            'preseason_expectations_history_filled_v2.csv',
            'preseason_expectations_history_filled.csv',
        ])
        preseason_exp.columns = [str(c).strip() for c in preseason_exp.columns]

        coach_records = _load_first([
            'coach_records.csv',
            'coach_records_base_userteams_corrected.csv',
            'coach_records_base_userteams_full.csv',
            'coach_records_base_userteams_corrected.xlsx',
            'coach_records_base_userteams_full.xlsx',
        ])
        coach_records.columns = [str(c).strip() for c in coach_records.columns]

        recruit_hist = _load_recruiting_csv()
        recruit_hist.columns = [str(c).strip() for c in recruit_hist.columns]

        cfp_hist = _load_first(['cfp_rankings_history.csv'])
        cfp_hist.columns = [str(c).strip() for c in cfp_hist.columns]

        cfp_results = _load_first(['CFPbracketresults.csv'])
        cfp_results.columns = [str(c).strip() for c in cfp_results.columns]

        # ── Standardize key sources ───────────────────────────────────────────
        if not legacy_ratings.empty:
            if 'USER' in legacy_ratings.columns:
                legacy_ratings['USER'] = safe_title_series(legacy_ratings['USER'])
            if 'TEAM' in legacy_ratings.columns:
                legacy_ratings['TEAM'] = legacy_ratings['TEAM'].astype(str).str.strip()
            _ry = _smart(legacy_ratings, ['YEAR', 'Year'])
            if _ry:
                legacy_ratings[_ry] = _safe_num(legacy_ratings[_ry]).astype('Int64')

        if not preseason_exp.empty:
            _py = _smart(preseason_exp, ['Year', 'YEAR'])
            _pu = _smart(preseason_exp, ['User', 'USER'])
            _pt = _smart(preseason_exp, ['Team', 'TEAM'])
            if _py: preseason_exp[_py] = _safe_num(preseason_exp[_py]).astype('Int64')
            if _pu: preseason_exp[_pu] = safe_title_series(preseason_exp[_pu])
            if _pt: preseason_exp[_pt] = preseason_exp[_pt].astype(str).str.strip()

        if not coach_records.empty:
            _cru = _smart(coach_records, ['User', 'USER'])
            _crt = _smart(coach_records, ['Team', 'TEAM'])
            if _cru: coach_records[_cru] = safe_title_series(coach_records[_cru])
            if _crt: coach_records[_crt] = coach_records[_crt].astype(str).str.strip()

        if not recruit_hist.empty:
            _rhy = _smart(recruit_hist, ['Year', 'YEAR'])
            _rht = _smart(recruit_hist, ['Team', 'TEAM'])
            _rhu = _smart(recruit_hist, ['User', 'USER'])
            _rhr = _smart(recruit_hist, ['Rank', 'RANK'])
            if _rhy: recruit_hist[_rhy] = _safe_num(recruit_hist[_rhy]).astype('Int64')
            if _rht: recruit_hist[_rht] = recruit_hist[_rht].astype(str).str.strip()
            if _rhu: recruit_hist[_rhu] = safe_title_series(recruit_hist[_rhu])
            if _rhr: recruit_hist[_rhr] = _safe_num(recruit_hist[_rhr])

        if not cfp_hist.empty:
            _cy = _smart(cfp_hist, ['YEAR', 'Year'])
            _cw = _smart(cfp_hist, ['WEEK', 'Week'])
            _ct = _smart(cfp_hist, ['TEAM', 'Team'])
            _cr = _smart(cfp_hist, ['RANK', 'Rank'])
            if _cy: cfp_hist[_cy] = _safe_num(cfp_hist[_cy]).astype('Int64')
            if _cw: cfp_hist[_cw] = _safe_num(cfp_hist[_cw])
            if _ct: cfp_hist[_ct] = cfp_hist[_ct].astype(str).str.strip()
            if _cr: cfp_hist[_cr] = _safe_num(cfp_hist[_cr])

        if not cfp_results.empty:
            _bcy = _smart(cfp_results, ['YEAR', 'Year'])
            _bround = _smart(cfp_results, ['ROUND', 'Round'])
            _bteam1 = _smart(cfp_results, ['TEAM1', 'Team1'])
            _bteam2 = _smart(cfp_results, ['TEAM2', 'Team2'])
            _bwin = _smart(cfp_results, ['WINNER', 'Winner'])
            _blose = _smart(cfp_results, ['LOSER', 'Loser'])
            if _bcy: cfp_results[_bcy] = _safe_num(cfp_results[_bcy]).astype('Int64')
            for _bc in [_bround, _bteam1, _bteam2, _bwin, _blose]:
                if _bc and _bc in cfp_results.columns:
                    cfp_results[_bc] = cfp_results[_bc].astype(str).str.strip()

        _score_year_col = _smart(legacy_scores, ['YEAR', 'Year'])
        if _score_year_col:
            legacy_scores[_score_year_col] = _safe_num(legacy_scores[_score_year_col]).astype('Int64')
        for _uc in ['V_User_Final', 'H_User_Final']:
            if _uc in legacy_scores.columns:
                legacy_scores[_uc] = safe_title_series(legacy_scores[_uc])
        for _tc in ['Visitor_Final', 'Home_Final']:
            if _tc in legacy_scores.columns:
                legacy_scores[_tc] = legacy_scores[_tc].astype(str).str.strip()

        _champ_year_col = _smart(legacy_champs, ['Year', 'YEAR'])
        _champ_user_col = _smart(legacy_champs, ['user', 'User'])
        _champ_team_col = _smart(legacy_champs, ['Team', 'TEAM'])
        if _champ_year_col: legacy_champs[_champ_year_col] = _safe_num(legacy_champs[_champ_year_col]).astype('Int64')
        if _champ_user_col: legacy_champs[_champ_user_col] = safe_title_series(legacy_champs[_champ_user_col])
        if _champ_team_col: legacy_champs[_champ_team_col] = legacy_champs[_champ_team_col].astype(str).str.strip()

        _coty_year_col = _smart(legacy_coty, ['Year', 'YEAR'])
        _coty_user_col = _smart(legacy_coty, ['User', 'USER'])
        _coty_team_col = _smart(legacy_coty, ['Team', 'TEAM', 'School'])
        if _coty_year_col: legacy_coty[_coty_year_col] = _safe_num(legacy_coty[_coty_year_col]).astype('Int64')
        if _coty_user_col: legacy_coty[_coty_user_col] = safe_title_series(legacy_coty[_coty_user_col])
        if _coty_team_col: legacy_coty[_coty_team_col] = legacy_coty[_coty_team_col].astype(str).str.strip()

        # ── Coach options from ratings first, then scores fallback ────────────
        coach_options = []
        if not legacy_ratings.empty and 'USER' in legacy_ratings.columns:
            coach_options.extend([u for u in legacy_ratings['USER'].dropna().astype(str).unique() if u and u.lower() != 'nan'])
        if not legacy_scores.empty:
            for _c in ['V_User_Final', 'H_User_Final']:
                if _c in legacy_scores.columns:
                    coach_options.extend([u for u in legacy_scores[_c].dropna().astype(str).unique() if u and u.upper() != 'CPU' and u.lower() != 'nan'])
        coach_options = sorted(pd.unique(pd.Series(coach_options)).tolist())

        if not coach_options:
            st.warning("Coach Legacy needs TeamRatingsHistory.csv and CPUscores_MASTER.csv.")
            st.stop()

        left_sel, right_sel = st.columns([1.2, 1.0])
        with left_sel:
            target = st.selectbox("Select Coach", coach_options, key="coach_legacy_user")
        with right_sel:
            view_mode = st.radio("View", ["Career View", "Single Season View"], horizontal=True, key="coach_legacy_view")

        _coach_ratings = legacy_ratings[legacy_ratings['USER'] == target].copy() if 'USER' in legacy_ratings.columns else pd.DataFrame()
        _coach_ratings = _coach_ratings.sort_values(_smart(_coach_ratings, ['YEAR', 'Year']) or 'YEAR') if not _coach_ratings.empty else _coach_ratings

        _coach_record_row = pd.Series(dtype=object)
        if not coach_records.empty:
            _cru = _smart(coach_records, ['User', 'USER'])
            _crt = _smart(coach_records, ['Team', 'TEAM'])
            _cr = coach_records.copy()
            if _cru:
                _cr = _cr[_cr[_cru] == target]
            if _cr.empty and _crt and not _coach_ratings.empty and 'TEAM' in _coach_ratings.columns:
                _current_team_guess = str(_coach_ratings.sort_values(_smart(_coach_ratings, ['YEAR', 'Year']) or 'YEAR').iloc[-1].get('TEAM', '')).strip()
                if _current_team_guess:
                    _cr = coach_records[coach_records[_crt] == _current_team_guess].copy()
            if not _cr.empty:
                _coach_record_row = _cr.iloc[0]

        # Build year -> team map from historical game results first, then supplement with ratings
        _year_team = {}
        if not legacy_scores.empty and _score_year_col is not None:
            _score_slice = legacy_scores[legacy_scores[_score_year_col].notna()].copy()
            _mask = pd.Series(False, index=_score_slice.index)
            if 'V_User_Final' in _score_slice.columns:
                _mask = _mask | (_score_slice['V_User_Final'] == target)
            if 'H_User_Final' in _score_slice.columns:
                _mask = _mask | (_score_slice['H_User_Final'] == target)
            _score_slice = _score_slice[_mask].copy()
            if not _score_slice.empty:
                _teams = []
                for _, _r in _score_slice.iterrows():
                    try:
                        _yr = int(_r.get(_score_year_col))
                    except Exception:
                        continue
                    if str(_r.get('H_User_Final', '')) == target:
                        _tm = str(_r.get('Home_Final', '')).strip()
                    elif str(_r.get('V_User_Final', '')) == target:
                        _tm = str(_r.get('Visitor_Final', '')).strip()
                    else:
                        _tm = ''
                    if _tm and _tm.lower() != 'nan':
                        _teams.append((_yr, _tm))
                if _teams:
                    _yt = pd.DataFrame(_teams, columns=['Year', 'Team'])
                    for _yr, _grp in _yt.groupby('Year'):
                        try:
                            _year_team[int(_yr)] = str(_grp['Team'].mode().iloc[0]).strip()
                        except Exception:
                            pass

        # supplement missing years from TeamRatingsHistory
        _rating_year_col = _smart(_coach_ratings, ['YEAR', 'Year'])
        if not _coach_ratings.empty and _rating_year_col and 'TEAM' in _coach_ratings.columns:
            for _yr, _grp in _coach_ratings.groupby(_rating_year_col):
                try:
                    _year_team.setdefault(int(_yr), str(_grp['TEAM'].mode().iloc[0]).strip())
                except Exception:
                    pass

        # fall back to current visible team if needed
        if not _year_team and 'model_2041' in globals() and isinstance(model_2041, pd.DataFrame):
            _m = model_2041[model_2041['USER'] == target]
            if not _m.empty:
                _year_team[int(CURRENT_YEAR)] = str(_m.iloc[0].get('TEAM', '')).strip()

        _coach_years = sorted(_year_team.keys())
        if not _coach_years:
            st.warning("No career years were found for this coach in TeamRatingsHistory.csv.")
            st.stop()

        # helper: season games for coach/year
        def _coach_games_for_year(_coach, _yr):
            if legacy_scores.empty or _score_year_col is None:
                return pd.DataFrame()
            _s = legacy_scores[legacy_scores[_score_year_col] == int(_yr)].copy()
            _mask = False
            if 'V_User_Final' in _s.columns:
                _mask = _mask | (_s['V_User_Final'] == _coach)
            if 'H_User_Final' in _s.columns:
                _mask = _mask | (_s['H_User_Final'] == _coach)
            _g = _s[_mask].copy()
            return _g

        def _rank_lookup(_team, _yr):
            if cfp_hist.empty:
                return np.nan
            _cy = _smart(cfp_hist, ['YEAR', 'Year']); _cw = _smart(cfp_hist, ['WEEK', 'Week'])
            _ct = _smart(cfp_hist, ['TEAM', 'Team']); _cr = _smart(cfp_hist, ['RANK', 'Rank'])
            if None in [_cy, _ct, _cr]:
                return np.nan
            _slice = cfp_hist[cfp_hist[_cy] == int(_yr)].copy()
            if _slice.empty:
                return np.nan
            if _cw and _cw in _slice.columns:
                _wk = _slice[_cw].dropna().max()
                if pd.notna(_wk):
                    _slice = _slice[_slice[_cw] == _wk].copy()
            _row = _slice[_slice[_ct] == str(_team).strip()]
            if _row.empty:
                return np.nan
            return _safe_num(_row.iloc[0][_cr])

        def _cfp_result_for_team_year(_team, _yr):
            _team = str(_team).strip()
            if not _team or cfp_results.empty:
                return ""
            _bcy = _smart(cfp_results, ['YEAR', 'Year'])
            _bround = _smart(cfp_results, ['ROUND', 'Round'])
            _bteam1 = _smart(cfp_results, ['TEAM1', 'Team1'])
            _bteam2 = _smart(cfp_results, ['TEAM2', 'Team2'])
            _bwin = _smart(cfp_results, ['WINNER', 'Winner'])
            _blose = _smart(cfp_results, ['LOSER', 'Loser'])
            if None in [_bcy, _bround, _bteam1, _bteam2, _bwin, _blose]:
                return ""
            _yr_df = cfp_results[cfp_results[_bcy] == int(_yr)].copy()
            if _yr_df.empty:
                return ""
            _team_games = _yr_df[
                (_yr_df[_bteam1] == _team) | (_yr_df[_bteam2] == _team) | (_yr_df[_bwin] == _team) | (_yr_df[_blose] == _team)
            ].copy()
            if _team_games.empty:
                return ""
            _rounds = _team_games[_bround].astype(str).str.upper()
            _won_title = ((_team_games[_bround].astype(str).str.upper().isin(['NCG', 'FINAL', 'CHAMPIONSHIP'])) & (_team_games[_bwin] == _team)).any()
            if _won_title:
                return "National Champion"
            _lost_title = ((_team_games[_bround].astype(str).str.upper().isin(['NCG', 'FINAL', 'CHAMPIONSHIP'])) & (_team_games[_blose] == _team)).any()
            if _lost_title:
                return "Title Game"
            _lost_sf = ((_team_games[_bround].astype(str).str.upper().isin(['SF', 'SEMIFINAL', 'SEMIFINALS'])) & (_team_games[_blose] == _team)).any()
            if _lost_sf:
                return "Semifinal"
            _lost_qf = ((_team_games[_bround].astype(str).str.upper().isin(['QF', 'QUARTERFINAL', 'QUARTERFINALS'])) & (_team_games[_blose] == _team)).any()
            if _lost_qf:
                return "Quarterfinal"
            _lost_r1 = ((_team_games[_bround].astype(str).str.upper().isin(['R1', 'ROUND 1', 'FIRST ROUND'])) & (_team_games[_blose] == _team)).any()
            if _lost_r1:
                return "Round 1"
            return "CFP"

        def _won_title_for_team_year(_coach, _team, _yr):
            _team = str(_team).strip()
            _by_bracket = False
            if _team and not cfp_results.empty:
                _cfp_res_label = _cfp_result_for_team_year(_team, _yr)
                _by_bracket = (_cfp_res_label == 'National Champion')
            _by_champs = False
            if not legacy_champs.empty and _champ_year_col and _champ_user_col:
                _champ_slice = legacy_champs[(legacy_champs[_champ_year_col] == int(_yr)) & (legacy_champs[_champ_user_col] == _coach)].copy()
                if _champ_team_col and _champ_team_col in _champ_slice.columns and _team:
                    _champ_slice = _champ_slice[_champ_slice[_champ_team_col].astype(str).str.strip() == _team]
                _by_champs = not _champ_slice.empty
            return bool(_by_bracket or _by_champs)

        def _schedule_df(_coach, _yr):
            _g = _coach_games_for_year(_coach, _yr).copy()
            if _g.empty:
                return pd.DataFrame()
            _rows = []
            for _, _r in _g.iterrows():
                _is_home = str(_r.get('H_User_Final', '')) == _coach
                _team = str(_r.get('Home_Final' if _is_home else 'Visitor_Final', '')).strip()
                _opp = str(_r.get('Visitor_Final' if _is_home else 'Home_Final', '')).strip()
                _team_pts = _safe_num(pd.Series([_r.get('H_Pts' if _is_home else 'V_Pts', np.nan)])).iloc[0]
                _opp_pts = _safe_num(pd.Series([_r.get('V_Pts' if _is_home else 'H_Pts', np.nan)])).iloc[0]
                _res = 'W' if pd.notna(_team_pts) and pd.notna(_opp_pts) and _team_pts > _opp_pts else 'L'
                _wk_col = _smart(_g, ['Week', 'WEEK'])
                _week = _r.get(_wk_col, '') if _wk_col else ''
                _opp_rank = _rank_lookup(_opp, _yr)
                _rows.append({
                    'Week': _week,
                    'Team': _team,
                    'Opponent': _opp,
                    'Opponent Rank': (int(_opp_rank) if pd.notna(_opp_rank) else ''),
                    'Result': _res,
                    'Score': f"{int(_team_pts)}-{int(_opp_pts)}" if pd.notna(_team_pts) and pd.notna(_opp_pts) else '—',
                    'Margin': (float(_team_pts) - float(_opp_pts)) if pd.notna(_team_pts) and pd.notna(_opp_pts) else np.nan,
                })
            _df = pd.DataFrame(_rows)
            if 'Week' in _df.columns:
                try:
                    _df['Week_Sort'] = _safe_num(_df['Week'])
                except Exception:
                    _df['Week_Sort'] = np.nan
                _df = _df.sort_values(['Week_Sort', 'Opponent'], na_position='last').drop(columns=['Week_Sort'])
            return _df

        def _season_metrics(_coach, _yr):
            _games = _schedule_df(_coach, _yr)
            _team = _year_team.get(int(_yr), '')
            _wins = int((_games['Result'] == 'W').sum()) if not _games.empty else 0
            _losses = int((_games['Result'] == 'L').sum()) if not _games.empty else 0
            _ppg = np.nan
            _avg_margin = np.nan
            if not _games.empty:
                _pts_for = []
                for _s in _games['Score']:
                    try:
                        _a, _b = str(_s).split('-')
                        _pts_for.append(float(_a))
                    except Exception:
                        pass
                if _pts_for:
                    _ppg = round(float(np.mean(_pts_for)), 1)
                if 'Margin' in _games.columns and _games['Margin'].notna().any():
                    _avg_margin = round(float(_games['Margin'].mean()), 1)

            _rank_vals = _safe_num(_games['Opponent Rank']) if ('Opponent Rank' in _games.columns) else pd.Series(dtype=float)
            _ranked_mask = _rank_vals.notna() if not _rank_vals.empty else pd.Series(dtype=bool)
            _rw = int(((_games['Result'] == 'W') & _ranked_mask).sum()) if not _games.empty and not _rank_vals.empty else 0
            _t10 = int(((_games['Result'] == 'W') & (_rank_vals <= 10)).sum()) if not _games.empty and not _rank_vals.empty else 0
            _rl = int(((_games['Result'] == 'L') & _ranked_mask).sum()) if not _games.empty and not _rank_vals.empty else 0
            _comp = _rank_vals[_ranked_mask] if not _rank_vals.empty else pd.Series(dtype=float)
            _avg_r = float(_comp.mean()) if not _comp.empty else 99.0
            _base_sos = round((_rw * 8.5) + (_t10 * 4.0) - (_rl * 1.5) + (max(0, (25 - _avg_r)) * 0.8), 1)

            def _season_strength_context():
                _spd = np.nan
                _qb_tier = 'Average Joe'
                _qb_ovr = 80.0

                # TeamRatingsHistory / ratings first
                if not legacy_ratings.empty:
                    _ry = _smart(legacy_ratings, ['YEAR', 'Year'])
                    _rt = _smart(legacy_ratings, ['TEAM', 'Team'])
                    _ru = _smart(legacy_ratings, ['USER', 'User'])
                    _slice = legacy_ratings.copy()
                    if _ry:
                        _slice = _slice[_slice[_ry] == int(_yr)]
                    if _rt and _team:
                        _tm = _slice[_slice[_rt].astype(str).str.strip() == str(_team).strip()]
                        if not _tm.empty:
                            _slice = _tm
                    if _slice.empty and _ru:
                        _slice = legacy_ratings[(legacy_ratings[_ry] == int(_yr)) & (legacy_ratings[_ru] == _coach)] if _ry else legacy_ratings[legacy_ratings[_ru] == _coach]
                    if not _slice.empty:
                        _r0 = _slice.iloc[0]
                        _spd_col = _smart(legacy_ratings, ['Team Speed (90+ Speed Guys)', 'TeamSpeed'])
                        _qbt_col = _smart(legacy_ratings, ['QB Tier'])
                        _qbo_col = _smart(legacy_ratings, ['QB OVR', 'QBOvr'])
                        if _spd_col:
                            _spd = _safe_num(pd.Series([_r0.get(_spd_col, np.nan)])).iloc[0]
                        if _qbt_col:
                            _qb_tier = clean_display(_r0.get(_qbt_col, 'Average Joe'), 'Average Joe')
                        if _qbo_col:
                            _qb_ovr = _safe_num(pd.Series([_r0.get(_qbo_col, 80)])).iloc[0]

                # preseason expectations fallback for speed only
                if pd.isna(_spd) and not preseason_exp.empty:
                    _py = _smart(preseason_exp, ['Year', 'YEAR']); _pu = _smart(preseason_exp, ['User', 'USER']); _pt = _smart(preseason_exp, ['Team', 'TEAM'])
                    _spd_col = _smart(preseason_exp, ['TeamSpeed', 'Team Speed'])
                    if _py and _spd_col:
                        _pr = preseason_exp[(preseason_exp[_py] == int(_yr))].copy()
                        if _pu:
                            _pr = _pr[_pr[_pu] == _coach]
                        if _pt and _team and not _pr.empty:
                            _tm = _pr[_pr[_pt].astype(str).str.strip() == str(_team).strip()]
                            if not _tm.empty:
                                _pr = _tm
                        if not _pr.empty:
                            _spd = _safe_num(pd.Series([_pr.iloc[0].get(_spd_col, np.nan)])).iloc[0]

                return _spd, _qb_tier, _qb_ovr

            _team_speed, _qb_tier, _qb_ovr = _season_strength_context()

            _league_avg_speed = 8.0
            if not legacy_ratings.empty:
                _spd_hist_col = _smart(legacy_ratings, ['Team Speed (90+ Speed Guys)', 'TeamSpeed'])
                if _spd_hist_col:
                    _spd_vals = _safe_num(legacy_ratings[_spd_hist_col])
                    if _spd_vals.notna().any():
                        _league_avg_speed = float(_spd_vals.dropna().mean())
            elif 'model_2041' in globals() and isinstance(model_2041, pd.DataFrame):
                _spd_hist_col = _smart(model_2041, ['Team Speed (90+ Speed Guys)', 'TeamSpeed'])
                if _spd_hist_col:
                    _spd_vals = _safe_num(model_2041[_spd_hist_col])
                    if _spd_vals.notna().any():
                        _league_avg_speed = float(_spd_vals.dropna().mean())

            if pd.isna(_team_speed):
                _team_speed = _league_avg_speed

            _spd_raw = (_league_avg_speed - float(_team_speed)) * 0.55
            _qb_base = {'Elite': -4.0, 'Leader': -1.5, 'Average Joe': 1.5, 'Ass': 5.0}.get(str(_qb_tier).strip(), 0)
            _handicap = round(_spd_raw + _qb_base, 2)
            _sos = round(_base_sos + _handicap, 1)

            _top5 = int(((_games['Result'] == 'W') & (_rank_vals <= 5)).sum()) if not _games.empty and not _rank_vals.empty else 0
            _path = round((_rw * 7) + (_t10 * 6) + (_top5 * 5) + (_wins * 1.5) + max(0, _handicap * 8), 1)

            if _path >= 90:
                _tier = "Historic"
            elif _path >= 65:
                _tier = "Brutal"
            elif _path >= 40:
                _tier = "Tough"
            else:
                _tier = "Manageable"

            _cfp_result = _cfp_result_for_team_year(_team, _yr)
            _national_title = _won_title_for_team_year(_coach, _team, _yr)
            _final_rank = _rank_lookup(_team, _yr)
            if _national_title:
                _final_rank = 1

            _proj = _natty = _cfp = np.nan
            if not preseason_exp.empty:
                _py = _smart(preseason_exp, ['Year', 'YEAR']); _pu = _smart(preseason_exp, ['User', 'USER']); _pt = _smart(preseason_exp, ['Team', 'TEAM'])
                _pr = preseason_exp.copy()
                if _py and _pu and _pt:
                    _pr = _pr[(_pr[_py] == int(_yr)) & (_pr[_pu] == _coach) & (_pr[_pt] == str(_team).strip())]
                    if _pr.empty:
                        _pr = preseason_exp[(preseason_exp[_py] == int(_yr)) & (preseason_exp[_pu] == _coach)]
                    if _pr.empty:
                        _pr = preseason_exp[(preseason_exp[_py] == int(_yr)) & (preseason_exp[_pt] == str(_team).strip())]
                    if not _pr.empty:
                        _r0 = _pr.iloc[0]
                        _proj = _safe_num(pd.Series([_r0.get(_smart(preseason_exp, ['ProjectedWins']), np.nan)])).iloc[0] if _smart(preseason_exp, ['ProjectedWins']) else np.nan
                        _cfp = _safe_num(pd.Series([_r0.get(_smart(preseason_exp, ['CFPOdds', 'CFP Odds']), np.nan)])).iloc[0] if _smart(preseason_exp, ['CFPOdds', 'CFP Odds']) else np.nan
                        _natty = _safe_num(pd.Series([_r0.get(_smart(preseason_exp, ['NattyOdds', 'Natty Odds']), np.nan)])).iloc[0] if _smart(preseason_exp, ['NattyOdds', 'Natty Odds']) else np.nan

            _rec_over = _rec_hs = _rec_tp = np.nan
            if not recruit_hist.empty:
                _ry = _smart(recruit_hist, ['Year', 'YEAR']); _rt = _smart(recruit_hist, ['Team', 'TEAM']); _rr = _smart(recruit_hist, ['Rank', 'RANK']); _rc = _smart(recruit_hist, ['ClassType'])
                _rh = recruit_hist.copy()
                if _ry and _rt and _rr:
                    _rh = _rh[(_rh[_ry] == int(_yr)) & (_rh[_rt] == str(_team).strip())]
                    if not _rh.empty:
                        if _rc and _rc in _rh.columns:
                            def _rank_for(_lab):
                                _m = _rh[_rh[_rc].astype(str).str.upper() == _lab]
                                if _m.empty: return np.nan
                                return _safe_num(pd.Series([_m.iloc[0][_rr]])).iloc[0]
                            _rec_over = _rank_for('OVERALL')
                            _rec_hs = _rank_for('HS')
                            _rec_tp = _rank_for('TRANSFER')
                        elif not _rh.empty:
                            _rec_over = _safe_num(pd.Series([_rh.iloc[0][_rr]])).iloc[0]

            _coty_flag = False
            if not legacy_coty.empty and _coty_year_col and _coty_user_col:
                _coty_flag = not legacy_coty[(legacy_coty[_coty_year_col] == int(_yr)) & (legacy_coty[_coty_user_col] == _coach)].empty

            return {
                'Year': int(_yr),
                'School': _team,
                'Record': f"{_wins}-{_losses}",
                'Wins': _wins,
                'Losses': _losses,
                'SOS': _sos,
                'Hardest Path': _path,
                'Path Tier': _tier,
                'Final Rank': (int(_final_rank) if pd.notna(_final_rank) else np.nan),
                'CFP Result': _cfp_result,
                'National Title': ("Yes" if _national_title else ""),
                'Recruiting Overall': _rec_over,
                'Recruiting HS': _rec_hs,
                'Recruiting Transfer': _rec_tp,
                'Preseason Natty Odds': _natty,
                'Preseason CFP Odds': _cfp,
                'Projected Wins': _proj,
                'Actual Wins': _wins,
                'PPG': _ppg,
                'Avg Margin': _avg_margin,
                'Coach of the Year': "Yes" if _coty_flag else "",
            }

        _legacy_rows = [_season_metrics(target, _yr) for _yr in _coach_years]
        legacy_df = pd.DataFrame(_legacy_rows).sort_values('Year')

        def _sos_tier(x):
            try:
                x = float(x)
            except Exception:
                return "—"
            if x < 4:
                return "Soft"
            if x < 6:
                return "Manageable"
            if x < 8:
                return "Solid"
            if x < 10:
                return "Tough"
            return "Brutal"

        def _path_tier_from_score(x):
            try:
                x = float(x)
            except Exception:
                return "—"
            if x < 25:
                return "Manageable"
            if x < 50:
                return "Tough"
            if x < 75:
                return "Brutal"
            return "Historic"

        def _metric_descriptor(label, value):
            try:
                if pd.isna(value):
                    return "—"
                v = float(value)
            except Exception:
                return "—"
            if label == 'Generational Freaks':
                if v <= 0: return 'None'
                if v <= 1: return 'Rare'
                if v <= 3: return 'Loaded'
                return 'Absurd'
            if label == 'Cheat Codes':
                if v <= 0: return 'None'
                if v <= 2: return 'A Few'
                if v <= 4: return 'Dangerous'
                return 'Broken'
            if label == 'Monsters':
                if v <= 0: return 'None'
                if v <= 2: return 'Nasty'
                if v <= 4: return 'Problem'
                return 'Terror Front'
            if label == 'Quick Hogs':
                if v <= 0: return 'None'
                if v <= 2: return 'Agile Front'
                if v <= 4: return 'Road Graders'
                return 'Wall of Beef'
            return '—'

        def _pretty_legacy_table(df):
            if df.empty:
                return df
            _df = df.copy()

            _num_cols = [c for c in [
                'Preseason Natty Odds','Preseason CFP Odds','SOS','Hardest Path',
                'Final Rank','Recruiting Overall','Recruiting HS','Recruiting Transfer',
                'Projected Wins','Actual Wins'
            ] if c in _df.columns]

            for _c in _num_cols:
                _df[_c] = pd.to_numeric(_df[_c], errors='coerce')

            if 'Preseason Natty Odds' in _df.columns:
                _df['Preseason Natty Odds'] = _df['Preseason Natty Odds'].map(lambda v: f"{v:.1f}%" if pd.notna(v) else '—')
            if 'Preseason CFP Odds' in _df.columns:
                _df['Preseason CFP Odds'] = _df['Preseason CFP Odds'].map(lambda v: f"{v:.1f}%" if pd.notna(v) else '—')
            if 'SOS' in _df.columns:
                _df['SOS'] = _df['SOS'].map(lambda v: f"{v:.1f}" if pd.notna(v) else '—')
            if 'Hardest Path' in _df.columns:
                _df['Hardest Path'] = _df['Hardest Path'].map(lambda v: f"{v:.1f}" if pd.notna(v) else '—')
            if 'Projected Wins' in _df.columns:
                _df['Projected Wins'] = _df['Projected Wins'].map(lambda v: f"{v:.1f}" if pd.notna(v) else '—')
            if 'Actual Wins' in _df.columns:
                _df['Actual Wins'] = _df['Actual Wins'].map(lambda v: f"{v:.0f}" if pd.notna(v) else '—')

            for _rank_col in ['Final Rank','Recruiting Overall','Recruiting HS','Recruiting Transfer']:
                if _rank_col in _df.columns:
                    _df[_rank_col] = _df[_rank_col].map(lambda v: int(v) if pd.notna(v) else '—')

            for _flag_col in ['National Title', 'Coach of the Year']:
                if _flag_col in _df.columns:
                    _df[_flag_col] = _df[_flag_col].fillna('No').astype(str).str.strip()

            return _df.fillna('—')

        def _render_coach_legacy_snapshot_table(df):
            if df.empty:
                st.caption("No coach legacy rows available.")
                return

            _df = _pretty_legacy_table(df).copy()
            _rows_html = []

            for _, _row in _df.sort_values('Year', ascending=False).iterrows():
                _team = str(_row.get('School', '')).strip()
                _primary = get_team_primary_color(_team) if 'get_team_primary_color' in globals() else '#38bdf8'
                _logo_uri = None
                try:
                    _logo_path = get_logo_source(_team) if 'get_logo_source' in globals() else None
                    _logo_uri = image_file_to_data_uri(_logo_path) if _logo_path and 'image_file_to_data_uri' in globals() else None
                except Exception:
                    _logo_uri = None

                _logo_html = f"<img src='{_logo_uri}' style='width:34px;height:34px;object-fit:contain;'/>" if _logo_uri else "<div style='font-size:20px;'>🏫</div>"

                _year_disp = html.escape(str(_row.get('Year', '—')))
                _team_disp = html.escape(_team)
                _record_disp = html.escape(str(_row.get('Record', '—')))
                _cfp_disp = html.escape(str(_row.get('CFP Result', '—')))
                _natty_disp = html.escape(str(_row.get('National Title', '—')))
                _natty_color = '#fbbf24' if str(_row.get('National Title', 'No')).strip().lower() == 'yes' else '#e5e7eb'
                _coty_disp = html.escape(str(_row.get('Coach of the Year', '—')))
                _coty_color = '#60a5fa' if str(_row.get('Coach of the Year', 'No')).strip().lower() == 'yes' else '#e5e7eb'

                _cells = [f'''
                <td class="isp-td-pin">
                  <div class="isp-flex-row">
                    <div style="font-weight:800;min-width:34px;text-align:center;color:#e5e7eb;">{_year_disp}</div>
                    <div class="isp-td-num">{_logo_html}</div>
                    <div style="font-weight:800;color:{_primary};">{_team_disp}</div>
                  </div>
                </td>
                ''']

                _vals = [
                    _record_disp,
                    _cfp_disp,
                    f"<span style='color:{_natty_color};font-weight:800;'>{_natty_disp}</span>",
                    html.escape(str(_row.get('Preseason Natty Odds', '—'))),
                    html.escape(str(_row.get('Preseason CFP Odds', '—'))),
                    html.escape(str(_row.get('SOS', '—'))),
                    html.escape(str(_row.get('SOS Tier', '—'))),
                    html.escape(str(_row.get('Hardest Path', '—'))),
                    html.escape(str(_row.get('Path Tier', '—'))),
                    html.escape(str(_row.get('Final Rank', '—'))),
                    html.escape(str(_row.get('Recruiting Overall', '—'))),
                    html.escape(str(_row.get('Recruiting HS', '—'))),
                    html.escape(str(_row.get('Recruiting Transfer', '—'))),
                    html.escape(str(_row.get('Projected Wins', '—'))),
                    html.escape(str(_row.get('Actual Wins', '—'))),
                    f"<span style='color:{_coty_color};font-weight:800;'>{_coty_disp}</span>",
                ]

                for _disp in _vals:
                    _cells.append(f"<td style='padding:10px 12px;border-bottom:1px solid #334155;text-align:center;white-space:nowrap;color:#e5e7eb;'>{_disp}</td>")

                _rows_html.append(f"<tr style='border-left:6px solid {_primary};background:linear-gradient(90deg,{_primary}22,rgba(15,23,42,.95) 14%);'>{''.join(_cells)}</tr>")

            _table_html = f'''
            <div class="isp-table-wrap">
              <table class="isp-table">
                <thead>
                  <tr class="isp-tr-header">
                    <th class="isp-th isp-th-left">Year-by-Year Legacy</th>
                    <th class="isp-th">Record</th>
                    <th class="isp-th">CFP Result</th>
                    <th class="isp-th">Natty</th>
                    <th class="isp-th">Natty Odds</th>
                    <th class="isp-th">CFP Odds</th>
                    <th class="isp-th">SOS</th>
                    <th class="isp-th">SOS Tier</th>
                    <th class="isp-th">Hardest Path</th>
                    <th class="isp-th">Path Tier</th>
                    <th class="isp-th">Final Rank</th>
                    <th class="isp-th">Rec Ovr</th>
                    <th class="isp-th">HS</th>
                    <th class="isp-th">Portal</th>
                    <th class="isp-th">Proj Wins</th>
                    <th class="isp-th">Actual Wins</th>
                    <th class="isp-th">COTY</th>
                  </tr>
                </thead>
                <tbody>{''.join(_rows_html)}</tbody>
              </table>
            </div>
            '''
            st.markdown(_table_html, unsafe_allow_html=True)

        if not legacy_df.empty:
            legacy_df['SOS Tier'] = legacy_df['SOS'].apply(_sos_tier) if 'SOS' in legacy_df.columns else "—"
            if 'Path Tier' not in legacy_df.columns and 'Hardest Path' in legacy_df.columns:
                legacy_df['Path Tier'] = legacy_df['Hardest Path'].apply(_path_tier_from_score)

        # ── Career cards ───────────────────────────────────────────────────────
        _schools = [str(t).strip() for t in pd.Series(list(_year_team.values())).dropna().unique() if str(t).strip()]
        _career_w = int(legacy_df['Wins'].sum()) if not legacy_df.empty else 0
        _career_l = int(legacy_df['Losses'].sum()) if not legacy_df.empty else 0
        _natties = int((legacy_df['National Title'].astype(str) == 'Yes').sum()) if (not legacy_df.empty and 'National Title' in legacy_df.columns) else 0
        if _natties == 0 and not legacy_champs.empty and _champ_user_col:
            _natties = int((legacy_champs[_champ_user_col] == target).sum())

        if not _coach_record_row.empty:
            _cr_record = str(_coach_record_row.get(_smart(coach_records, ['CareerRecord']), '')).strip()
            _cr_record = _cr_record.replace('="', '').replace('"', '')
            if '-' in _cr_record:
                try:
                    _cw_txt, _cl_txt = _cr_record.split('-', 1)
                    _career_w = int(str(_cw_txt).strip())
                    _career_l = int(str(_cl_txt).strip())
                except Exception:
                    pass

        _avg_sos = round(float(legacy_df['SOS'].dropna().mean()), 1) if not legacy_df.empty and legacy_df['SOS'].dropna().any() else np.nan
        _avg_path = round(float(legacy_df['Hardest Path'].dropna().mean()), 1) if not legacy_df.empty and legacy_df['Hardest Path'].dropna().any() else np.nan
        _avg_vs_proj = round(float((legacy_df['Actual Wins'].fillna(0) - legacy_df['Projected Wins'].fillna(0)).mean()), 1) if not legacy_df.empty and 'Projected Wins' in legacy_df.columns else np.nan

        mobile_metrics([
            {"label": "🏫 Schools", "value": str(len(_schools))},
            {"label": "📘 Career Record", "value": f"{_career_w}-{_career_l}"},
            {"label": "🏆 Natties", "value": str(_natties)},
            {"label": "📐 AVG SOS", "value": f"{_avg_sos:.1f} • {_sos_tier(_avg_sos)}" if pd.notna(_avg_sos) else "—"},
            {"label": "🪓 AVG PATH", "value": f"{_avg_path:.1f} • {_path_tier_from_score(_avg_path)}" if pd.notna(_avg_path) else "—"},
            {"label": "📈 VS PROJ WINS", "value": f"{_avg_vs_proj:+.1f}" if pd.notna(_avg_vs_proj) else "—"},
        ])

        if not _coach_record_row.empty:
            st.markdown("### Coach Resume")
            _resume_rows = []
            for _label, _cand in [
                ('Prestige', ['Prestige']),
                ('Level', ['Level']),
                ('Archetype', ['Archetype']),
                ('Off Scheme', ['OffScheme']),
                ('Def Scheme', ['DefScheme']),
                ('Alma Mater', ['AlmaMater']),
                ('Playoff Record', ['PlayoffRecord']),
                ('Conference Titles', ['ConferenceTitles']),
                ('First Rounders', ['FirstRounders']),
                ('Draft Picks', ['DraftPicks']),
                ('Top 5 Recruiting Classes', ['Top5RecruitingClasses']),
                ('Bowl Record', ['BowlRecord']),
                ('Record vs Rivals', ['RecordVsRivals']),
                ('Record vs Top 25', ['RecordVsTop25']),
            ]:
                _col = _smart(coach_records, _cand)
                if _col:
                    _val = _coach_record_row.get(_col, '')
                    if pd.notna(_val) and str(_val).strip():
                        _resume_rows.append({'Metric': _label, 'Value': str(_val).replace('="', '').replace('"','')})
            if _resume_rows:
                st.dataframe(pd.DataFrame(_resume_rows), use_container_width=True, hide_index=True)

        st.markdown("### Coaching Stops")
        _stop_cols = st.columns(max(1, min(4, len(_schools))))
        for i, _school in enumerate(_schools):
            _school_years = sorted([y for y, t in _year_team.items() if str(t).strip() == _school])
            _school_titles = 0
            if not legacy_df.empty and 'School' in legacy_df.columns and 'National Title' in legacy_df.columns:
                _school_titles = int(((legacy_df['School'].astype(str).str.strip() == _school) & (legacy_df['National Title'].astype(str) == 'Yes')).sum())
            with _stop_cols[i % len(_stop_cols)]:
                _uri = image_file_to_data_uri(get_logo_source(_school)) if 'image_file_to_data_uri' in globals() else None
                if _uri:
                    st.markdown(f"<div style='text-align:center;'><img src='{_uri}' style='height:72px;object-fit:contain;'/></div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div style='text-align:center;font-size:2rem;'>🏫</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align:center;font-size:1.2rem;font-weight:800;margin-top:4px;'>{html.escape(_school)}</div>", unsafe_allow_html=True)
                _yr_text = f"{min(_school_years)}-{max(_school_years)}" if len(_school_years) > 1 else str(_school_years[0])
                st.markdown(f"<div style='text-align:center;color:#9ca3af;margin-top:2px;'>{_yr_text}</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align:center;color:#cbd5e1;margin-top:10px;'>Titles: {_school_titles}</div>", unsafe_allow_html=True)

        st.markdown("### 🗓️ Year-by-Year Legacy")
        _display_df = legacy_df.copy()
        for _col in ['Preseason Natty Odds', 'Preseason CFP Odds', 'SOS', 'Hardest Path', 'Final Rank', 'Recruiting Overall', 'Recruiting HS', 'Recruiting Transfer', 'Projected Wins']:
            if _col in _display_df.columns:
                _display_df[_col] = _display_df[_col].where(_display_df[_col].notna(), None)
        _legacy_table_show = _display_df[['Year','School','Record','CFP Result','National Title','Preseason Natty Odds','Preseason CFP Odds','SOS','SOS Tier','Hardest Path','Path Tier','Final Rank','Recruiting Overall','Recruiting HS','Recruiting Transfer','Projected Wins','Actual Wins','Coach of the Year']].copy()
        _render_coach_legacy_snapshot_table(_legacy_table_show)

        # Selected season controls
        _default_year = int(legacy_df['Year'].max()) if not legacy_df.empty else int(CURRENT_YEAR)
        if view_mode == "Single Season View":
            selected_year = st.selectbox("Season Detail", list(legacy_df['Year'].astype(int).tolist()), index=max(0, len(legacy_df)-1), key="coach_legacy_year")
        else:
            selected_year = st.selectbox("Season Detail", list(legacy_df['Year'].astype(int).tolist()), index=max(0, len(legacy_df)-1), key="coach_legacy_year_cv")

        _season_row = legacy_df[legacy_df['Year'] == int(selected_year)].iloc[0]
        _season_team = str(_season_row['School'])
        st.markdown(f"## 🧭 Selected Season: {int(selected_year)} {_season_team}")

        mobile_metrics([
            {"label": "📘 Record", "value": str(_season_row['Record'])},
            {"label": "📐 SOS", "value": f"{float(_season_row['SOS']):.1f} • {_sos_tier(_season_row['SOS'])}" if pd.notna(_season_row['SOS']) else "—"},
            {"label": "🪓 Hardest Path", "value": f"{float(_season_row['Hardest Path']):.1f} • {_path_tier_from_score(_season_row['Hardest Path'])}" if pd.notna(_season_row['Hardest Path']) else "—"},
            {"label": "🏈 CFP Result", "value": str(_season_row['CFP Result']) if str(_season_row.get('CFP Result', '')).strip() else "—"},
            {"label": "🏆 Natty Odds", "value": f"{float(_season_row['Preseason Natty Odds']):.1f}%" if pd.notna(_season_row['Preseason Natty Odds']) else "—"},
            {"label": "🎯 CFP Odds", "value": f"{float(_season_row['Preseason CFP Odds']):.1f}%" if pd.notna(_season_row['Preseason CFP Odds']) else "—"},
            {"label": "📈 Proj Wins", "value": f"{float(_season_row['Projected Wins']):.1f}" if pd.notna(_season_row['Projected Wins']) else "—"},
            {"label": "✅ Actual Wins", "value": str(int(_season_row['Actual Wins'])) if pd.notna(_season_row['Actual Wins']) else "—"},
        ])

        # Selected season identity + recruiting
        _season_rating = pd.DataFrame()
        if not _coach_ratings.empty and _rating_year_col and 'TEAM' in _coach_ratings.columns:
            _season_rating = _coach_ratings[(_coach_ratings[_rating_year_col] == int(selected_year)) & (_coach_ratings['TEAM'] == _season_team)].copy()
            if _season_rating.empty:
                _season_rating = _coach_ratings[_coach_ratings[_rating_year_col] == int(selected_year)].copy()

        _season_exp = pd.DataFrame()
        if not preseason_exp.empty:
            _py = _smart(preseason_exp, ['Year', 'YEAR']); _pu = _smart(preseason_exp, ['User', 'USER']); _pt = _smart(preseason_exp, ['Team', 'TEAM'])
            _season_exp = preseason_exp[(preseason_exp[_py] == int(selected_year)) & (preseason_exp[_pu] == target) & (preseason_exp[_pt] == _season_team)].copy() if None not in [_py, _pu, _pt] else pd.DataFrame()

        _left, _right = st.columns(2)

        with _left:
            st.markdown("### Team Identity")
            _identity_rows = []
            if not _season_rating.empty:
                _sr = _season_rating.iloc[0]
                for _label, _cand in [
                    ('Overall', ['OVERALL', 'Overall']),
                    ('Offense', ['OFFENSE', 'Offense']),
                    ('Defense', ['DEFENSE', 'Defense']),
                    ('Team Speed', ['Team Speed (90+ Speed Guys)', 'TeamSpeed']),
                    ('Blue Chip Ratio', ['Blue Chip Ratio (4 & 5 star recruit ratio on roster)', 'BlueChipRatio']),
                    ('Generational Freaks', ['Generational (96+ speed or 96+ Acceleration)', 'GenerationalFreaks']),
                ]:
                    _col = _smart(_season_rating, _cand)
                    if _col:
                        _val = _sr.get(_col, '—')
                        _identity_rows.append({'Metric': _label, 'Value': _val, 'Descriptor': _metric_descriptor(_label, _val)})
            if not _season_exp.empty:
                _se = _season_exp.iloc[0]
                for _label, _cand in [
                    ('Cheat Codes', ['CheatCodes']),
                    ('Monsters', ['Monsters']),
                    ('Quick Hogs', ['QuickHogs']),
                ]:
                    _col = _smart(_season_exp, _cand)
                    if _col:
                        _val = _se.get(_col, '—')
                        _identity_rows.append({'Metric': _label, 'Value': _val, 'Descriptor': _metric_descriptor(_label, _val)})
            _identity_df = pd.DataFrame(_identity_rows)
            if not _identity_df.empty:
                st.dataframe(_identity_df, use_container_width=True, hide_index=True)
            else:
                st.info("No team identity data found for this season.")

        with _right:
            st.markdown("### Recruiting by Year")
            _recruit_rows = [
                {'Metric': 'Overall Rank', 'Value': (int(_season_row['Recruiting Overall']) if pd.notna(_season_row['Recruiting Overall']) else '—')},
                {'Metric': 'HS Rank', 'Value': (int(_season_row['Recruiting HS']) if pd.notna(_season_row['Recruiting HS']) else '—')},
                {'Metric': 'Transfer Rank', 'Value': (int(_season_row['Recruiting Transfer']) if pd.notna(_season_row['Recruiting Transfer']) else '—')},
                {'Metric': 'PPG', 'Value': (_season_row['PPG'] if pd.notna(_season_row['PPG']) else '—')},
                {'Metric': 'Avg Margin', 'Value': (_season_row['Avg Margin'] if pd.notna(_season_row['Avg Margin']) else '—')},
            ]
            _recruit_df = pd.DataFrame(_recruit_rows)
            st.dataframe(_recruit_df, use_container_width=True, hide_index=True)

        def _render_coach_schedule_snapshot_table(df):
            if df.empty:
                st.info("No schedule data found for this season.")
                return

            _df = df.copy()
            _keep = [c for c in ['Week','Team','Opponent','Opponent Rank','Result','Score','Margin'] if c in _df.columns]
            _df = _df[_keep].copy()

            if 'Opponent Rank' in _df.columns:
                _df['Opponent Rank'] = pd.to_numeric(_df['Opponent Rank'], errors='coerce')
            if 'Margin' in _df.columns:
                _df['Margin'] = pd.to_numeric(_df['Margin'], errors='coerce')

            def _logo_uri(_team_name):
                try:
                    _p = get_logo_source(_team_name) if 'get_logo_source' in globals() else None
                    return image_file_to_data_uri(_p) if _p and 'image_file_to_data_uri' in globals() else None
                except Exception:
                    return None

            _df.insert(1, 'Team Logo', _df['Team'].map(_logo_uri) if 'Team' in _df.columns else None)
            _df.insert(3, 'Opponent Logo', _df['Opponent'].map(_logo_uri) if 'Opponent' in _df.columns else None)

            if 'Opponent Rank' in _df.columns:
                _df['Opponent Rank'] = _df['Opponent Rank'].apply(lambda x: f"#{int(x)}" if pd.notna(x) else '—')
            if 'Result' in _df.columns:
                _df['Result'] = _df['Result'].astype(str).str.strip().str.upper().map({'W':'✅ W','L':'❌ L'}).fillna(_df['Result'])
            if 'Margin' in _df.columns:
                _df['Margin'] = _df['Margin'].apply(lambda x: f"{float(x):.1f}" if pd.notna(x) else '—')

            st.dataframe(
                _df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'Team Logo': st.column_config.ImageColumn('', width='small'),
                    'Opponent Logo': st.column_config.ImageColumn('', width='small'),
                    'Week': st.column_config.TextColumn('Week', width='small'),
                    'Team': st.column_config.TextColumn('Team', width='medium'),
                    'Opponent': st.column_config.TextColumn('Opponent', width='medium'),
                    'Opponent Rank': st.column_config.TextColumn('Opp Rank', width='small'),
                    'Result': st.column_config.TextColumn('Result', width='small'),
                    'Score': st.column_config.TextColumn('Score', width='small'),
                    'Margin': st.column_config.TextColumn('Margin', width='small'),
                }
            )

        st.markdown("### Schedule & Results")
        _sched = _schedule_df(target, int(selected_year))
        _render_coach_schedule_snapshot_table(_sched)
with tabs[11]:
        st.header("🎬 ISPN Classics")
        st.caption(
            "The most iconic games in dynasty history — ranked by closeness, "
            "stakes, and upset factor. Margin drives the score; natties, CFP games, "
            "and big upsets push it higher."
        )

        _classics_df = build_ispn_classics(scores, ratings)

        if _classics_df.empty:
            st.info("No game data available yet.")
        else:
            # ── Sub-tabs: ALL / UPSETS / CLOSEST ─────────────────────────────────
            _ctab_all, _ctab_upsets, _ctab_close = st.tabs(
                ["🏆 Top Classics", "🚨 Biggest Upsets", "😰 Closest Games"])

            def _render_classic_card(row, rank_num):
                """Render a single broadcast-style game card."""
                _wc  = get_team_primary_color(str(row['Winner']))
                _lc  = get_team_primary_color(str(row['Loser']))
                _wlu = image_file_to_data_uri(get_logo_source(str(row['Winner'])))
                _llu = image_file_to_data_uri(get_logo_source(str(row['Loser'])))
                _w_img = (f"<img src='{_wlu}' style='width:40px;height:40px;"
                          f"object-fit:contain;'/>" if _wlu else "🏈")
                _l_img = (f"<img src='{_llu}' style='width:40px;height:40px;"
                          f"object-fit:contain;'/>" if _llu else "🏈")

                _gt = str(row['GameType'])
                _gt_bg = ("#7c3aed" if 'Championship' in _gt else
                          "#0369a1" if 'CFP' in _gt else
                          "#166534" if 'Conf' in _gt else
                          "#92400e" if 'Bowl' in _gt else "#1e293b")
                _gt_color = ("#e9d5ff" if 'Championship' in _gt else
                             "#bfdbfe" if 'CFP' in _gt else
                             "#bbf7d0" if 'Conf' in _gt else
                             "#fde68a" if 'Bowl' in _gt else "#94a3b8")

                _upset_badge = ""
                if row['IsUpset']:
                    _diff = float(row['OVR_Diff'])
                    _upset_badge = (
                        f"<span style='padding:2px 8px;background:#7f1d1d;"
                        f"color:#fca5a5;font-size:0.62rem;font-weight:800;"
                        f"border-radius:999px;white-space:nowrap;'>"
                        f"&#9888; UPSET +{_diff:.1f} OVR</span>"
                    )

                _margin = int(row['Margin'])
                _close_label = ("2OT THRILLER" if _margin <= 1 else
                                "OT WAR" if _margin <= 3 else
                                "NAIL-BITER" if _margin <= 7 else
                                "CLOSE CALL" if _margin <= 14 else "")
                _close_badge = ""
                if _close_label:
                    _close_badge = (
                        f"<span style='padding:2px 8px;background:#1c1917;"
                        f"color:#fbbf24;font-size:0.62rem;font-weight:800;"
                        f"border-radius:999px;white-space:nowrap;border:1px solid #78350f;'>"
                        f"&#128293; {_close_label}</span>"
                    )

                _rank_str = f"#{rank_num}"
                _score_str = f"{int(row['WinnerPts'])} &ndash; {int(row['LoserPts'])}"
                _classic_score = float(row['ClassicScore'])

                st.markdown(
                    f"<div style='background:linear-gradient(135deg,#0f172a,#111827);"
                    f"border:1px solid #1e293b;border-radius:14px;"
                    f"padding:14px 16px;margin-bottom:10px;'>"
                    f"<div style='display:flex;align-items:center;gap:8px;"
                    f"flex-wrap:wrap;margin-bottom:10px;'>"
                    f"<span style='font-size:0.75rem;font-weight:900;color:#475569;"
                    f"min-width:26px;'>{_rank_str}</span>"
                    f"<span style='padding:2px 8px;background:{_gt_bg};"
                    f"color:{_gt_color};font-size:0.62rem;font-weight:700;"
                    f"border-radius:999px;white-space:nowrap;'>{html.escape(_gt)}</span>"
                    f"<span style='font-size:0.62rem;color:#475569;'>"
                    f"{int(row['Year'])}</span>"
                    f"{_upset_badge}{_close_badge}"
                    f"<span style='margin-left:auto;font-size:0.65rem;color:#374151;"
                    f"font-weight:700;'>&#9733; {_classic_score:.0f} pts</span>"
                    f"</div>"
                    f"<div style='display:flex;align-items:center;"
                    f"gap:10px;flex-wrap:wrap;'>"
                    f"<div style='display:flex;align-items:center;gap:8px;"
                    f"flex:1;min-width:110px;'>"
                    f"{_w_img}"
                    f"<div>"
                    f"<div style='font-weight:900;color:{_wc};font-size:0.9rem;"
                    f"line-height:1.1;'>{html.escape(str(row['Winner']))}</div>"
                    f"<div style='font-size:0.65rem;color:#64748b;'>"
                    f"{html.escape(str(row['WinnerUser']))}</div>"
                    f"</div></div>"
                    f"<div style='text-align:center;min-width:70px;'>"
                    f"<div style='font-size:1.4rem;font-weight:900;color:#f1f5f9;"
                    f"letter-spacing:-0.5px;'>{_score_str}</div>"
                    f"<div style='font-size:0.6rem;color:#475569;'>"
                    f"&#177;{_margin}</div>"
                    f"</div>"
                    f"<div style='display:flex;align-items:center;gap:8px;"
                    f"flex:1;justify-content:flex-end;min-width:110px;'>"
                    f"<div style='text-align:right;'>"
                    f"<div style='font-weight:700;color:{_lc};font-size:0.9rem;"
                    f"opacity:0.65;line-height:1.1;'>"
                    f"{html.escape(str(row['Loser']))}</div>"
                    f"<div style='font-size:0.65rem;color:#64748b;'>"
                    f"{html.escape(str(row['LoserUser']))}</div>"
                    f"</div>"
                    f"{_l_img}"
                    f"</div></div></div>",
                    unsafe_allow_html=True
                )

            with _ctab_all:
                st.caption("Ranked by Classic Score = closeness + stakes + upset factor.")
                _top25 = _classics_df.head(25)
                for _ci, (_idx, _crow) in enumerate(_top25.iterrows(), 1):
                    _render_classic_card(_crow, _ci)

            with _ctab_upsets:
                st.caption("Games where the lower-rated team pulled off the W. Ranked by OVR gap.")
                _upsets = _classics_df[_classics_df['IsUpset']].sort_values(
                    'OVR_Diff', ascending=False).head(20)
                if _upsets.empty:
                    st.info("No upset data detected with current ratings proxy.")
                else:
                    for _ci, (_idx, _crow) in enumerate(_upsets.iterrows(), 1):
                        _render_classic_card(_crow, _ci)

            with _ctab_close:
                st.caption("The absolute gut-punchers — decided by a single score or less.")
                _close = _classics_df.sort_values('Margin').head(20)
                for _ci, (_idx, _crow) in enumerate(_close.iterrows(), 1):
                    _render_classic_card(_crow, _ci)

# --- GOAT RANKINGS (Tab 12) ---
with tabs[12]:
    st.header("🐐 The GOAT Council")
    st.caption("Legacy is built on titles, trophies, pipelines, and sustained dominance.")

    def _safe_int(v, default=0):
        try:
            if pd.isna(v):
                return default
            return int(float(v))
        except Exception:
            return default

    def _parse_record_parts(val):
        s = str(val).strip()
        s = s.replace('="', '').replace('"', '').replace('=', '')
        if '-' in s:
            try:
                a, b = s.split('-', 1)
                return _safe_int(a, 0), _safe_int(b, 0)
            except Exception:
                return 0, 0
        return 0, 0

    def _load_goat_base_users():
        users = []
        try:
            if 'model_2041' in globals() and isinstance(model_2041, pd.DataFrame) and 'USER' in model_2041.columns:
                users = [str(u).strip() for u in model_2041['USER'].dropna().astype(str).tolist() if str(u).strip().upper() not in ('CPU', 'NAN', '')]
        except Exception:
            users = []
        return sorted(list(dict.fromkeys(users)))

    all_users = _load_goat_base_users()
    goat_stats = {
        u: {
            'rings': 0, 'rings_base': 0, 'rings_champs': 0, 'heismans': 0, 'cotys': 0,
            'conf_titles': 0, 'draft_picks': 0, 'first_rounders': 0, 'top5_classes': 0,
            'career_wins': 0, 'career_losses': 0, 'playoff_wins': 0, 'playoff_losses': 0,
            'current_team': '', 'visible_coach_name': '', 'prestige': '', 'level': pd.NA
        }
        for u in all_users
    }

    # coach_records.csv enrichment
    coach_records = pd.DataFrame()
    try:
        if os.path.exists('coach_records.csv'):
            coach_records = pd.read_csv('coach_records.csv')
            for _, row in coach_records.iterrows():
                u_name = str(row.get('User', '')).strip()
                if not u_name:
                    continue
                if u_name not in goat_stats:
                    goat_stats[u_name] = {
                        'rings': 0, 'heismans': 0, 'cotys': 0,
                        'conf_titles': 0, 'draft_picks': 0, 'first_rounders': 0, 'top5_classes': 0,
                        'career_wins': 0, 'career_losses': 0, 'playoff_wins': 0, 'playoff_losses': 0,
                        'current_team': '', 'visible_coach_name': '', 'prestige': '', 'level': pd.NA
                    }

                goat_stats[u_name]['current_team'] = clean_display(row.get('Team', ''), goat_stats[u_name]['current_team'])
                goat_stats[u_name]['visible_coach_name'] = clean_display(row.get('VisibleCoachName', ''), goat_stats[u_name]['visible_coach_name'])
                goat_stats[u_name]['prestige'] = clean_display(row.get('Prestige', ''), goat_stats[u_name]['prestige'])
                goat_stats[u_name]['level'] = row.get('Level', goat_stats[u_name]['level'])

                _cw, _cl = _parse_record_parts(row.get('CareerRecord', '0-0'))
                _pw, _pl = _parse_record_parts(row.get('PlayoffRecord', '0-0'))
                goat_stats[u_name]['career_wins'] = max(goat_stats[u_name]['career_wins'], _cw)
                goat_stats[u_name]['career_losses'] = max(goat_stats[u_name]['career_losses'], _cl)
                goat_stats[u_name]['playoff_wins'] = max(goat_stats[u_name]['playoff_wins'], _pw)
                goat_stats[u_name]['playoff_losses'] = max(goat_stats[u_name]['playoff_losses'], _pl)
                goat_stats[u_name]['rings_base'] = max(goat_stats[u_name].get('rings_base', 0), _safe_int(row.get('NationalTitles', 0), 0))
                goat_stats[u_name]['conf_titles'] = max(goat_stats[u_name]['conf_titles'], _safe_int(row.get('ConferenceTitles', 0), 0))
                goat_stats[u_name]['first_rounders'] = max(goat_stats[u_name]['first_rounders'], _safe_int(row.get('FirstRounders', 0), 0))
                goat_stats[u_name]['draft_picks'] = max(goat_stats[u_name]['draft_picks'], _safe_int(row.get('DraftPicks', 0), 0))
                goat_stats[u_name]['top5_classes'] = max(goat_stats[u_name]['top5_classes'], _safe_int(row.get('Top5RecruitingClasses', 0), 0))
    except Exception:
        coach_records = pd.DataFrame()

    # champs.csv
    try:
        if os.path.exists('champs.csv'):
            _champs_df = pd.read_csv('champs.csv')
            _u_col = next((c for c in _champs_df.columns if str(c).upper() in ['USER', 'COACH', 'WINNER_USER']), None)
            if _u_col:
                for _, row in _champs_df.iterrows():
                    u_name = str(row.get(_u_col, '')).strip()
                    if not u_name:
                        continue
                    if u_name not in goat_stats:
                        goat_stats[u_name] = {
                            'rings': 0, 'rings_base': 0, 'rings_champs': 0, 'heismans': 0, 'cotys': 0,
                            'conf_titles': 0, 'draft_picks': 0, 'first_rounders': 0, 'top5_classes': 0,
                            'career_wins': 0, 'career_losses': 0, 'playoff_wins': 0, 'playoff_losses': 0,
                            'current_team': '', 'visible_coach_name': '', 'prestige': '', 'level': pd.NA
                        }
                    goat_stats[u_name]['rings'] += 1
    except Exception:
        pass

    # Heismans
    try:
        if os.path.exists('Heisman_Finalists.csv'):
            _h_df = pd.read_csv('Heisman_Finalists.csv')
            if 'FINISH' in _h_df.columns:
                _h_df['FINISH'] = pd.to_numeric(_h_df['FINISH'], errors='coerce')
                _h_winners = _h_df[_h_df['FINISH'] == 1].copy()
                for _, row in _h_winners.iterrows():
                    u_name = str(row.get('USER', '')).strip()
                    if not u_name:
                        continue
                    if u_name not in goat_stats:
                        goat_stats[u_name] = {
                            'rings': 0, 'rings_base': 0, 'rings_champs': 0, 'heismans': 0, 'cotys': 0,
                            'conf_titles': 0, 'draft_picks': 0, 'first_rounders': 0, 'top5_classes': 0,
                            'career_wins': 0, 'career_losses': 0, 'playoff_wins': 0, 'playoff_losses': 0,
                            'current_team': '', 'visible_coach_name': '', 'prestige': '', 'level': pd.NA
                        }
                    goat_stats[u_name]['heismans'] += 1
    except Exception:
        pass

    # COTY
    try:
        if 'coty' in locals() and isinstance(coty, pd.DataFrame) and not coty.empty:
            for _, row in coty.iterrows():
                u_name = str(row.get('User', row.get('USER', ''))).strip()
                if not u_name:
                    continue
                if u_name not in goat_stats:
                    goat_stats[u_name] = {
                        'rings': 0, 'heismans': 0, 'cotys': 0,
                        'conf_titles': 0, 'draft_picks': 0, 'first_rounders': 0, 'top5_classes': 0,
                        'career_wins': 0, 'career_losses': 0, 'playoff_wins': 0, 'playoff_losses': 0,
                        'current_team': '', 'visible_coach_name': '', 'prestige': '', 'level': pd.NA
                    }
                goat_stats[u_name]['cotys'] += 1
    except Exception:
        pass

    def _legacy_tier(score):
        if score >= 220:
            return "Immortal"
        if score >= 140:
            return "Dynasty Titan"
        if score >= 85:
            return "Legend"
        if score >= 45:
            return "Builder"
        return "Contender"

    for _u in list(goat_stats.keys()):
        goat_stats[_u]['rings'] = max(
            _safe_int(goat_stats[_u].get('rings_base', 0), 0),
            _safe_int(goat_stats[_u].get('rings_champs', 0), 0)
        )

    goat_rows = []
    for u, stats in goat_stats.items():
        rings = _safe_int(stats.get('rings', 0), 0)
        heismans = _safe_int(stats.get('heismans', 0), 0)
        cotys = _safe_int(stats.get('cotys', 0), 0)
        conf_titles = _safe_int(stats.get('conf_titles', 0), 0)
        draft_picks = _safe_int(stats.get('draft_picks', 0), 0)
        first_rounders = _safe_int(stats.get('first_rounders', 0), 0)
        top5_classes = _safe_int(stats.get('top5_classes', 0), 0)
        cw = _safe_int(stats.get('career_wins', 0), 0)
        cl = _safe_int(stats.get('career_losses', 0), 0)
        pw = _safe_int(stats.get('playoff_wins', 0), 0)
        pl = _safe_int(stats.get('playoff_losses', 0), 0)

        score = (
            rings * 15 +
            heismans * 5 +
            cotys * 3 +
            conf_titles * 2 +
            first_rounders * 1 +
            min(15, int(draft_picks / 5)) +
            top5_classes * 1 +
            min(20, int(cw / 20)) +
            min(12, int(pw / 4))
        )

        win_pct = round((cw / max(1, cw + cl)), 3) if (cw + cl) > 0 else np.nan
        playoff_pct = round((pw / max(1, pw + pl)), 3) if (pw + pl) > 0 else np.nan
        career_record = f"{cw}-{cl}" if (cw + cl) > 0 else "—"
        playoff_record = f"{pw}-{pl}" if (pw + pl) > 0 else "—"

        goat_rows.append({
            'Coach': u,
            'DisplayName': stats.get('visible_coach_name') or u,
            'Team': stats.get('current_team', ''),
            'Prestige': clean_display(stats.get('prestige', ''), '—'),
            'Level': _safe_int(stats.get('level', 0), 0) if pd.notna(stats.get('level', pd.NA)) else '—',
            'Career Record': career_record,
            'Career Win %': win_pct,
            'Playoff Record': playoff_record,
            'Playoff Win %': playoff_pct,
            'Titles': rings,
            'Heismans': heismans,
            'COTYs': cotys,
            'Conf Titles': conf_titles,
            '1st Rd': first_rounders,
            'Draft Picks': draft_picks,
            'Top 5 Classes': top5_classes,
            'Legacy Score': score,
            'Tier': _legacy_tier(score),
        })

    legacy_df = pd.DataFrame(goat_rows)
    if legacy_df.empty:
        st.info("Win some hardware to enter the GOAT Council.")
    else:
        legacy_df = legacy_df.sort_values(
            ['Legacy Score', 'Titles', 'Heismans', 'COTYs', 'Draft Picks'],
            ascending=[False, False, False, False, False]
        ).reset_index(drop=True)

        top3 = legacy_df.head(3).copy()
        p_cols = st.columns(3)
        medals = ['🥇', '🥈', '🥉']
        for i, (_, row) in enumerate(top3.iterrows()):
            with p_cols[i]:
                _team = clean_display(row.get('Team', ''), '')
                _logo = get_school_logo_src(_team) if _team else None
                if _logo:
                    st.markdown(
                        f"<div style='display:flex;justify-content:center;margin-bottom:8px;'><img src='{_logo}' style='width:56px;height:56px;object-fit:contain;'></div>",
                        unsafe_allow_html=True
                    )
                st.metric(
                    label=f"{medals[i]} {row['Coach']}",
                    value=f"{int(row['Legacy Score'])} pts",
                    delta=f"{row['Tier']} • {row['Titles']} titles"
                )

        st.markdown("---")

        def _render_goat_snapshot_table(df):
            if df.empty:
                st.caption("No GOAT rows available.")
                return

            _rows_html = []
            for idx, _row in df.iterrows():
                _team = str(_row.get('Team', '')).strip()
                _primary = get_team_primary_color(_team) if 'get_team_primary_color' in globals() else '#38bdf8'
                _logo_uri = None
                try:
                    _logo_path = get_logo_source(_team) if 'get_logo_source' in globals() else None
                    _logo_uri = image_file_to_data_uri(_logo_path) if _logo_path and 'image_file_to_data_uri' in globals() else None
                except Exception:
                    _logo_uri = get_school_logo_src(_team) if _team else None

                _logo_html = f"<img src='{_logo_uri}' style='width:34px;height:34px;object-fit:contain;'/>" if _logo_uri else "<div style='font-size:20px;'>🏫</div>"
                _rank = idx + 1
                _medal = "🥇" if _rank == 1 else ("🥈" if _rank == 2 else ("🥉" if _rank == 3 else f"#{_rank}"))
                _coach = html.escape(str(_row.get('Coach', '—')))
                _team_disp = html.escape(_team or '—')
                _tier = html.escape(str(_row.get('Tier', '—')))
                _prestige = html.escape(str(_row.get('Prestige', '—')))
                _record = html.escape(str(_row.get('Career Record', '—')))
                _playoff_record = html.escape(str(_row.get('Playoff Record', '—')))
                _legacy_score = int(_safe_int(_row.get('Legacy Score', 0), 0))

                _cells = [f'''
                <td class="isp-td-pin">
                  <div class="isp-flex-row">
                    <div style="font-weight:900;min-width:38px;text-align:center;color:#e5e7eb;">{_medal}</div>
                    <div class="isp-td-num">{_logo_html}</div>
                    <div>
                      <div style="font-weight:900;color:{_primary};">{_coach}</div>
                      <div style="font-size:11px;color:#94a3b8;">{_team_disp}</div>
                    </div>
                  </div>
                </td>
                ''']

                _vals = [
                    f"<span style='font-weight:900;color:#f8fafc;'>{_legacy_score}</span>",
                    html.escape(str(_row.get('Titles', 0))),
                    html.escape(str(_row.get('Heismans', 0))),
                    html.escape(str(_row.get('COTYs', 0))),
                    html.escape(str(_row.get('Conf Titles', 0))),
                    html.escape(str(_row.get('1st Rd', 0))),
                    html.escape(str(_row.get('Draft Picks', 0))),
                    html.escape(str(_row.get('Top 5 Classes', 0))),
                    _record,
                    _playoff_record,
                    html.escape(f"{float(_row['Career Win %']):.3f}" if pd.notna(_row.get('Career Win %', np.nan)) else '—'),
                    html.escape(f"{float(_row['Playoff Win %']):.3f}" if pd.notna(_row.get('Playoff Win %', np.nan)) else '—'),
                    _prestige,
                    html.escape(str(_row.get('Level', '—'))),
                    f"<span style='font-weight:800;color:#fbbf24;'>{_tier}</span>",
                ]
                for _disp in _vals:
                    _cells.append(f"<td style='padding:10px 12px;border-bottom:1px solid #334155;text-align:center;white-space:nowrap;color:#e5e7eb;'>{_disp}</td>")

                _rows_html.append(f"<tr style='border-left:6px solid {_primary};background:linear-gradient(90deg,{_primary}22,rgba(15,23,42,.95) 14%);'>{''.join(_cells)}</tr>")

            _table_html = f'''
            <div class="isp-table-wrap">
              <table class="isp-table">
                <thead>
                  <tr class="isp-tr-header">
                    <th class="isp-th isp-th-left">GOAT Rankings</th>
                    <th class="isp-th">Legacy</th>
                    <th class="isp-th">Titles</th>
                    <th class="isp-th">Heismans</th>
                    <th class="isp-th">COTYs</th>
                    <th class="isp-th">Conf</th>
                    <th class="isp-th">1st Rd</th>
                    <th class="isp-th">Drafted</th>
                    <th class="isp-th">Top 5</th>
                    <th class="isp-th">Career</th>
                    <th class="isp-th">Playoff</th>
                    <th class="isp-th">Win %</th>
                    <th class="isp-th">PO Win %</th>
                    <th class="isp-th">Prestige</th>
                    <th class="isp-th">Level</th>
                    <th class="isp-th">Tier</th>
                  </tr>
                </thead>
                <tbody>{''.join(_rows_html)}</tbody>
              </table>
            </div>
            '''
            st.markdown(_table_html, unsafe_allow_html=True)

        _render_goat_snapshot_table(legacy_df)

        st.markdown("---")
        st.caption("Legacy score weighting: National Title (15), Heisman (5), COTY (3), Conference Title (2), plus pipeline and résumé bonuses.")
# ──────────────────────────────────────────────────────────────────────
# NFL UNIVERSE
# ──────────────────────────────────────────────────────────────────────
with tabs[1]:
    nfl_universe_logo_path = "_NFL_logo.png"
    if os.path.exists(nfl_universe_logo_path):
        logo_uri = file_to_data_uri(nfl_universe_logo_path)
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; justify-content:center; gap:14px; margin-bottom:8px;">
                <img src="{logo_uri}" style="height:54px; object-fit:contain;" />
                <h2 style="margin:0; padding:0;">NFL Universe</h2>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.header("NFL Universe")

    st.caption("Track where dynasty alumni land, how their NFL careers evolve, and who owns the fictional pro landscape.")

    if "nfl_universe_loaded" not in st.session_state:
        st.session_state["nfl_universe_loaded"] = False

    if not st.session_state["nfl_universe_loaded"]:
        st.markdown("<div style='text-align:center; padding: 40px 0 20px 0;'>", unsafe_allow_html=True)
        if st.button("🏈 Load NFL Universe", use_container_width=False, key="nfl_universe_load_btn"):
            st.session_state["nfl_universe_loaded"] = True
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        # Don't st.stop() — that kills all other tabs too. Just skip the rest of this tab.
        universe = None
        nfl_roster = pd.DataFrame()
        cfb_draft = pd.DataFrame()
    if universe is not None:
        nfl_draft_hist = universe["nfl_draft_hist"]
        nfl_current_rosters = universe["nfl_current_rosters"]

        for col in NFL_DRAFT_HISTORY_COLS:
            if col not in nfl_draft_hist.columns:
                nfl_draft_hist[col] = pd.NA
        nfl_draft_hist = nfl_draft_hist.reindex(columns=NFL_DRAFT_HISTORY_COLS)

        nfl_player_hist = universe["nfl_player_hist"]
        nfl_super_bowl = universe["nfl_super_bowl"]
        nfl_story = universe["nfl_story"]
        nfl_settings = universe["nfl_settings"]
        nfl_standings_hist = universe["nfl_standings_hist"]
        nfl_awards_hist = universe["nfl_awards_hist"]
        nfl_playoff_hist = universe["nfl_playoff_hist"]

        if "nfl_commissioner_unlocked" not in st.session_state:
            st.session_state["nfl_commissioner_unlocked"] = False

        is_commissioner = st.session_state["nfl_commissioner_unlocked"]

        latest_input_draft_year = (
            int(pd.to_numeric(cfb_draft["DraftYear"], errors="coerce").max())
            if not cfb_draft.empty and "DraftYear" in cfb_draft.columns and pd.to_numeric(cfb_draft["DraftYear"], errors="coerce").notna().any()
            else None
        )

        latest_saved_draft_year = get_latest_saved_draft_year()

        st.markdown("---")
        st.caption(f"Working directory: {os.getcwd()}")



        nfl_tabs = st.tabs([
            "📦 Draft Central",
            "🏁 Season Recap",
            "🏅 Awards",
            "🧾 Offseason Recap",
            "📚 NFL Player Database",
            "👤 Alumni Tracker",
            "🏆 Super Bowl History",
            "📰 Storylines",
            "🏟️ NFL Teams",
        ])

    # ── Draft Central ──────────────────────────────────────────────────
        with nfl_tabs[0]:
            st.subheader("📦 Draft Central")

            replay_l, replay_c, replay_r = st.columns([1, 1.45, 1])
            with replay_c:
                if st.button("▶️ Replay Saved Draft With Audio", use_container_width=True, key="replay_saved_draft_with_audio_draft_central"):
                    enable_draft_audio()
                    if latest_saved_draft_year is None:
                        st.warning("No saved draft exists yet.")
                    else:
                        replay_saved_nfl_draft(latest_saved_draft_year, speed_mode="Broadcast")

            st.markdown(
                "<div style='text-align:center;color:#9ca3af;font-size:0.9rem;'>This button enables audio and starts the replay in one click.</div>",
                unsafe_allow_html=True
            )

            if nfl_draft_hist.empty:
                st.info("No NFL draft universe data yet. Fill cfb_user_draft_results.csv, then click Regenerate.")
            else:
                years = sorted(nfl_draft_hist["DraftYear"].dropna().unique().tolist())

                # ── Year selector state ───────────────────────────────────────
                if "draft_central_year" not in st.session_state or st.session_state["draft_central_year"] not in years:
                    st.session_state["draft_central_year"] = years[-1]
                sel_year = st.session_state["draft_central_year"]

                yr_df = nfl_draft_hist[nfl_draft_hist["DraftYear"] == sel_year].copy()
                yr_df = yr_df.sort_values(["DraftRoundCanon", "GeneratedOverallPick"])

                tracked_yr_df = yr_df[
                    yr_df["DraftSource"].astype(str).str.strip().str.lower().eq("user_results")
                ].copy()

                # ── Compute metrics ───────────────────────────────────────────
                _total_drafted = len(yr_df)
                _first_rounders = int((yr_df["DraftRoundCanon"] == 1).sum())
                _top_user = yr_df["CollegeUser"].value_counts().idxmax() if not yr_df["CollegeUser"].dropna().empty else "—"
                if not tracked_yr_df.empty:
                    _best_pick_val = pd.to_numeric(tracked_yr_df["GeneratedOverallPick"], errors="coerce").min()
                elif not yr_df.empty:
                    _best_pick_val = pd.to_numeric(yr_df["GeneratedOverallPick"], errors="coerce").min()
                else:
                    _best_pick_val = None
                _best_pick = f"#{int(_best_pick_val)}" if _best_pick_val and not pd.isna(_best_pick_val) else "—"
                _top_bucket = yr_df["PosBucket"].value_counts().idxmax() if not yr_df["PosBucket"].dropna().empty else "—"

                # ── Top pick data ─────────────────────────────────────────────
                if not tracked_yr_df.empty:
                    top_pick = tracked_yr_df.sort_values("GeneratedOverallPick", ascending=True).iloc[0]
                elif not yr_df.empty:
                    top_pick = yr_df.sort_values("GeneratedOverallPick", ascending=True).iloc[0]
                else:
                    top_pick = None

                if top_pick is not None:
                    _school      = str(top_pick.get("CollegeTeam", ""))
                    _nfl_team    = str(top_pick.get("GeneratedNFLTeam", ""))
                    _player      = str(top_pick.get("Player", ""))
                    _user_name   = clean_display(top_pick.get("CollegeUser", ""), "")
                    _pos         = str(top_pick.get("Pos", ""))
                    _pos_bucket  = str(top_pick.get("PosBucket", ""))
                    _rookie_role = str(top_pick.get("RookieRole", ""))
                    _career_tier = str(top_pick.get("CareerTier", ""))
                    _story_tag   = html.escape(str(top_pick.get("StoryTag", "")))
                    _pick_no     = int(safe_num(top_pick.get("GeneratedOverallPick", 0), 0))
                    _rnd         = int(safe_num(top_pick.get("DraftRoundCanon", 0), 0))
                    _college_ovr = int(safe_num(top_pick.get("CollegeOVR", 0), 0))
                    _nfl_ovr     = int(safe_num(top_pick.get("OVR", 0), 0))
                    _draft_src   = str(top_pick.get("DraftSource", "user_results")).strip().lower()

                    # School logo
                    _school_logo_src = get_school_logo_src(_school) or ""
                    if _school_logo_src:
                        _school_logo_html = f'<img src="{_school_logo_src}" style="width:44px;height:44px;object-fit:contain;border-radius:6px;">'
                    else:
                        _school_logo_html = '<div style="width:44px;height:44px;border-radius:6px;background:var(--secondary-background-color);border:1px solid rgba(255,255,255,0.1);display:flex;align-items:center;justify-content:center;font-size:20px;">🎓</div>'

                    # NFL logo
                    _nfl_logo_src = get_nfl_logo_src(_nfl_team) or ""
                    if _nfl_logo_src:
                        _nfl_logo_html = f'<img src="{_nfl_logo_src}" style="width:44px;height:44px;object-fit:contain;border-radius:6px;">'
                    else:
                        _nfl_logo_html = '<div style="width:44px;height:44px;border-radius:6px;background:var(--secondary-background-color);border:1px solid rgba(255,255,255,0.1);display:flex;align-items:center;justify-content:center;font-size:20px;">🏈</div>'

                    # User brand color chip
                    _primary_color = get_team_primary_color(_school) if _school else ""
                    if _draft_src == "background_r1":
                        _user_chip = "<span style='display:inline-block;background:rgba(148,163,184,0.18);color:#94a3b8;border:1px solid rgba(148,163,184,0.30);font-size:11px;font-weight:500;padding:3px 9px;border-radius:20px;'>League Prospect</span>"
                    elif _user_name and _primary_color:
                        import re as _re
                        _hex = _primary_color.lstrip("#")
                        try:
                            _r, _g, _b = int(_hex[0:2],16), int(_hex[2:4],16), int(_hex[4:6],16)
                            _user_chip = f"<span style='display:inline-block;background:rgba({_r},{_g},{_b},0.18);color:{_primary_color};border:1px solid rgba({_r},{_g},{_b},0.40);font-size:11px;font-weight:500;padding:3px 9px;border-radius:20px;'>{html.escape(_user_name)}</span>"
                        except Exception:
                            _user_chip = f"<span style='display:inline-block;background:rgba(34,197,94,0.15);color:#4ade80;border:1px solid rgba(34,197,94,0.35);font-size:11px;font-weight:500;padding:3px 9px;border-radius:20px;'>{html.escape(_user_name)}</span>"
                    elif _user_name:
                        _user_chip = f"<span style='display:inline-block;background:rgba(34,197,94,0.15);color:#4ade80;border:1px solid rgba(34,197,94,0.35);font-size:11px;font-weight:500;padding:3px 9px;border-radius:20px;'>{html.escape(_user_name)}</span>"
                    else:
                        _user_chip = "<span style='display:inline-block;background:rgba(59,130,246,0.15);color:#60a5fa;border:1px solid rgba(59,130,246,0.35);font-size:11px;font-weight:500;padding:3px 9px;border-radius:20px;'>CPU</span>"

                    # Career tier chip color
                    _tier_colors = {
                        "superstar": ("rgba(250,204,21,0.18)", "#fbbf24", "rgba(250,204,21,0.40)"),
                        "star":      ("rgba(74,222,128,0.15)", "#4ade80", "rgba(74,222,128,0.35)"),
                        "starter":   ("rgba(96,165,250,0.15)", "#60a5fa", "rgba(96,165,250,0.35)"),
                        "backup":    ("rgba(148,163,184,0.15)", "#94a3b8", "rgba(148,163,184,0.30)"),
                    }
                    _tc = _tier_colors.get(_career_tier.lower(), _tier_colors["backup"])
                    _tier_chip = f"<span style='display:inline-block;background:{_tc[0]};color:{_tc[1]};border:1px solid {_tc[2]};font-size:11px;font-weight:500;padding:3px 9px;border-radius:20px;'>{html.escape(_career_tier)}</span>"
                    _role_chip  = f"<span style='display:inline-block;background:rgba(96,165,250,0.15);color:#60a5fa;border:1px solid rgba(96,165,250,0.35);font-size:11px;font-weight:500;padding:3px 9px;border-radius:20px;'>{html.escape(_rookie_role)}</span>"

                    # Year selector pills for card header
                    _year_pills = ""
                    for _yr in years:
                        _active_style = "background:#f1f5f9;color:#0f172a;border-color:transparent;" if int(_yr) == int(sel_year) else ""
                        _year_pills += (
                            f'<button onclick="window.parent.postMessage({{type:\'streamlit:setComponentValue\',value:{int(_yr)}}},\'*\')" '
                            f'style="font-size:12px;font-weight:500;padding:4px 10px;border-radius:6px;cursor:pointer;'
                            f'border:1px solid rgba(148,163,184,0.35);color:#94a3b8;background:transparent;{_active_style}">'
                            f'{int(_yr)}</button>'
                        )

                    # ── Render spotlight card ─────────────────────────────────
                    components.html(f"""
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
      .dc-metrics {{ display: grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap: 8px; margin-bottom: 16px; }}
      .dc-metric {{ background: rgba(255,255,255,0.05); border-radius: 8px; padding: 10px 12px; text-align: center; border: 1px solid rgba(255,255,255,0.08); }}
      .dc-metric-num {{ font-size: 20px; font-weight: 500; color: #f1f5f9; line-height: 1.2; }}
      .dc-metric-lbl {{ font-size: 10px; color: #64748b; margin-top: 3px; text-transform: uppercase; letter-spacing: .05em; }}
      .dc-card {{ border: 1px solid rgba(255,255,255,0.10); border-radius: 12px; overflow: hidden; }}
      .dc-header {{ background: rgba(255,255,255,0.04); padding: 10px 16px; border-bottom: 1px solid rgba(255,255,255,0.08); display: flex; align-items: center; justify-content: space-between; gap: 12px; }}
      .dc-header-label {{ font-size: 11px; font-weight: 500; color: #64748b; text-transform: uppercase; letter-spacing: .06em; white-space: nowrap; }}
      .dc-year-tabs {{ display: flex; gap: 4px; }}
      .dc-body {{ display: grid; grid-template-columns: 1fr auto 1fr; }}
      .dc-panel {{ padding: 18px 20px; }}
      .dc-panel-mid {{ border-left: 1px solid rgba(255,255,255,0.08); border-right: 1px solid rgba(255,255,255,0.08); display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 20px 24px; text-align: center; min-width: 190px; }}
      .dc-panel-label {{ font-size: 10px; font-weight: 500; color: #64748b; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 8px; }}
      .dc-logo-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }}
      .dc-team-name {{ font-size: 16px; font-weight: 500; color: #f1f5f9; }}
      .dc-team-sub  {{ font-size: 12px; color: #64748b; margin-top: 2px; }}
      .dc-chips {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 10px; }}
      .dc-chip-gray {{ display:inline-block;background:rgba(148,163,184,0.12);color:#94a3b8;border:1px solid rgba(148,163,184,0.25);font-size:11px;font-weight:500;padding:3px 9px;border-radius:20px; }}
      .dc-pick-label {{ font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: .06em; }}
      .dc-pick-num   {{ font-size: 52px; font-weight: 500; color: #f1f5f9; line-height: 1; margin: 2px 0 6px; }}
      .dc-player-name {{ font-size: 18px; font-weight: 500; color: #f1f5f9; }}
      .dc-player-sub  {{ font-size: 12px; color: #64748b; margin-top: 4px; }}
      .dc-story {{ font-size: 12px; color: #64748b; margin-top: 10px; font-style: italic; border-left: 2px solid rgba(255,255,255,0.12); padding-left: 8px; line-height: 1.5; }}
      .dc-nfl-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 10px; justify-content: flex-end; }}
      .dc-nfl-name {{ font-size: 16px; font-weight: 500; color: #f1f5f9; text-align: right; }}
      .dc-nfl-sub  {{ font-size: 12px; color: #64748b; margin-top: 2px; text-align: right; }}
    </style>

    <div style="padding:4px 0 0;">

      <div class="dc-metrics">
        <div class="dc-metric"><div class="dc-metric-num">{_total_drafted}</div><div class="dc-metric-lbl">Players Drafted</div></div>
        <div class="dc-metric"><div class="dc-metric-num">{_first_rounders}</div><div class="dc-metric-lbl">1st Rounders</div></div>
        <div class="dc-metric"><div class="dc-metric-num">{html.escape(str(_top_user))}</div><div class="dc-metric-lbl">Top Pipeline</div></div>
        <div class="dc-metric"><div class="dc-metric-num">{_best_pick}</div><div class="dc-metric-lbl">Earliest Pick</div></div>
        <div class="dc-metric"><div class="dc-metric-num">{html.escape(str(_top_bucket))}</div><div class="dc-metric-lbl">Top Position</div></div>
      </div>

      <div class="dc-card">
        <div class="dc-header">
          <span class="dc-header-label">Top User Pick</span>
          <div class="dc-year-tabs">{_year_pills}</div>
        </div>
        <div class="dc-body">

          <div class="dc-panel">
            <div class="dc-panel-label">School</div>
            <div class="dc-logo-row">
              {_school_logo_html}
              <div>
                <div class="dc-team-name">{html.escape(_school)}</div>
                <div class="dc-team-sub">{html.escape(_pos)} / {html.escape(_pos_bucket)}</div>
              </div>
            </div>
            <div class="dc-chips">
              {_user_chip}
              <span class="dc-chip-gray">{_college_ovr} CFB OVR</span>
            </div>
          </div>

          <div class="dc-panel-mid">
            <div class="dc-pick-label">Overall Pick</div>
            <div class="dc-pick-num">#{_pick_no}</div>
            <div class="dc-player-name">{html.escape(_player)}</div>
            <div class="dc-player-sub">Round {_rnd} &nbsp;·&nbsp; {_nfl_ovr} NFL Rookie OVR</div>
            <div class="dc-chips" style="justify-content:center;margin-top:10px;">
              {_tier_chip}
              {_role_chip}
            </div>
            <div class="dc-story">{_story_tag}</div>
          </div>

          <div class="dc-panel">
            <div class="dc-panel-label" style="text-align:right;">Drafted By</div>
            <div class="dc-nfl-row">
              <div>
                <div class="dc-nfl-name">{html.escape(_nfl_team)}</div>
              </div>
              {_nfl_logo_html}
            </div>
          </div>

        </div>
      </div>
    </div>
    """, height=340, scrolling=False)

                # ── Year selector — zero-height, invisible, driven by session state ──
                st.markdown("<div style='height:0;overflow:hidden;margin:0;padding:0;'>", unsafe_allow_html=True)
                _sel_idx = years.index(sel_year) if sel_year in years else len(years) - 1
                _new_year = st.selectbox("Draft Year", years, index=_sel_idx, key="draft_central_year_select", label_visibility="collapsed")
                st.markdown("</div>", unsafe_allow_html=True)
                if _new_year != sel_year:
                    st.session_state["draft_central_year"] = _new_year
                    st.rerun()

                st.markdown("#### Draft Results")

                view_cols = [
                    "GeneratedOverallPick", "DraftRoundCanon", "Player", "CollegeTeam", "CollegeUser",
                    "Pos", "PosBucket", "CollegeOVR", "OVR", "GeneratedNFLTeam",
                    "RookieRole", "CareerTier", "StoryTag"
                ]

                show_df = yr_df[view_cols].copy().rename(columns={
                    "GeneratedOverallPick": "Pick",
                    "DraftRoundCanon": "Rnd",
                    "CollegeTeam": "School",
                    "CollegeUser": "User",
                    "CollegeOVR": "College OVR",
                    "OVR": "NFL Rookie OVR",
                    "GeneratedNFLTeam": "NFL Team",
                })

                def _draft_team_cell(_team_name, _kind="school"):
                    _team = clean_display(_team_name, "—")
                    if _kind == "nfl":
                        _logo = get_nfl_logo_html(_team, width=28, margin="0")
                        _color = html.escape(str(get_team_primary_color(_team) or "#e5e7eb")) if 'get_team_primary_color' in globals() else "#e5e7eb"
                    else:
                        _logo = get_school_logo_html(_team, width=28, margin="0")
                        _color = html.escape(str(get_team_primary_color(_team) or "#e5e7eb")) if 'get_team_primary_color' in globals() else "#e5e7eb"
                    return (
                        f"<div style='display:flex;align-items:center;gap:10px;justify-content:flex-start;min-width:0;'>"
                        f"<div style='display:flex;align-items:center;justify-content:center;flex:0 0 28px;'>{_logo}</div>"
                        f"<div style='font-weight:800;color:{_color};white-space:nowrap;'>"
                        f"{html.escape(_team)}"
                        f"</div></div>"
                    )

                _draft_rows_html = []
                for _, _r in show_df.iterrows():
                    _pick = clean_display(_r.get("Pick", "—"), "—")
                    _rnd = clean_display(_r.get("Rnd", "—"), "—")
                    _player = clean_display(_r.get("Player", "—"), "—")
                    _school = clean_display(_r.get("School", "—"), "—")
                    _user = clean_display(_r.get("User", "—"), "—") or "—"
                    _pos = clean_display(_r.get("Pos", "—"), "—")
                    _bucket = clean_display(_r.get("PosBucket", "—"), "—")
                    _covr = clean_display(_r.get("College OVR", "—"), "—")
                    _novr = clean_display(_r.get("NFL Rookie OVR", "—"), "—")
                    _nfl = clean_display(_r.get("NFL Team", "—"), "—")
                    _role = clean_display(_r.get("RookieRole", "—"), "—")
                    _tier = clean_display(_r.get("CareerTier", "—"), "—")
                    _story = clean_display(_r.get("StoryTag", "—"), "—")
                    _user_badge = (
                        f"<span style='display:inline-block;padding:2px 8px;border-radius:999px;background:rgba(34,197,94,0.16);border:1px solid rgba(34,197,94,0.30);color:#86efac;font-weight:800;font-size:0.72rem;'>"
                        f"{html.escape(_user)}"
                        f"</span>" if _user != "—" else "<span style='color:#94a3b8;'>—</span>"
                    )
                    _draft_rows_html.append(
                        f"<tr style='background:rgba(15,23,42,0.88);'>"
                        f"<td style='padding:10px 12px;border-bottom:1px solid #334155;text-align:center;color:#f8fafc;font-weight:800;white-space:nowrap;'>{html.escape(str(_pick))}</td>"
                        f"<td style='padding:10px 12px;border-bottom:1px solid #334155;text-align:center;color:#e5e7eb;white-space:nowrap;'>{html.escape(str(_rnd))}</td>"
                        f"<td style='padding:10px 12px;border-bottom:1px solid #334155;color:#f8fafc;font-weight:800;white-space:nowrap;'>{html.escape(_player)}</td>"
                        f"<td style='padding:10px 12px;border-bottom:1px solid #334155;white-space:nowrap;'>{_draft_team_cell(_school, 'school')}</td>"
                        f"<td style='padding:10px 12px;border-bottom:1px solid #334155;text-align:center;white-space:nowrap;'>{_user_badge}</td>"
                        f"<td style='padding:10px 12px;border-bottom:1px solid #334155;text-align:center;color:#e5e7eb;white-space:nowrap;'>{html.escape(_pos)}</td>"
                        f"<td style='padding:10px 12px;border-bottom:1px solid #334155;text-align:center;color:#94a3b8;white-space:nowrap;'>{html.escape(_bucket)}</td>"
                        f"<td style='padding:10px 12px;border-bottom:1px solid #334155;text-align:center;color:#e5e7eb;white-space:nowrap;'>{html.escape(str(_covr))}</td>"
                        f"<td style='padding:10px 12px;border-bottom:1px solid #334155;text-align:center;color:#e5e7eb;white-space:nowrap;'>{html.escape(str(_novr))}</td>"
                        f"<td style='padding:10px 12px;border-bottom:1px solid #334155;white-space:nowrap;'>{_draft_team_cell(_nfl, 'nfl')}</td>"
                        f"<td style='padding:10px 12px;border-bottom:1px solid #334155;text-align:center;color:#e5e7eb;white-space:nowrap;'>{html.escape(_role)}</td>"
                        f"<td style='padding:10px 12px;border-bottom:1px solid #334155;text-align:center;color:#e5e7eb;white-space:nowrap;'>{html.escape(_tier)}</td>"
                        f"<td style='padding:10px 12px;border-bottom:1px solid #334155;color:#cbd5e1;white-space:nowrap;'>{html.escape(_story)}</td>"
                        f"</tr>"
                    )

                _draft_table_html = f"""
                <div style='overflow-x:auto;border:1px solid #334155;border-radius:14px;background:linear-gradient(180deg,rgba(2,6,23,.98),rgba(15,23,42,.94));box-shadow:0 10px 24px rgba(0,0,0,.30);'>
                  <table style='width:100%;border-collapse:collapse;font-size:0.86rem;min-width:1400px;'>
                    <thead>
                      <tr style='background:linear-gradient(180deg,rgba(30,41,59,.98),rgba(15,23,42,.98));'>
                        <th style='padding:10px 12px;color:#f8fafc;font-weight:800;text-align:center;'>Pick</th>
                        <th style='padding:10px 12px;color:#f8fafc;font-weight:800;text-align:center;'>Rnd</th>
                        <th style='padding:10px 12px;color:#f8fafc;font-weight:800;text-align:left;'>Player</th>
                        <th style='padding:10px 12px;color:#f8fafc;font-weight:800;text-align:left;'>College Team</th>
                        <th style='padding:10px 12px;color:#f8fafc;font-weight:800;text-align:center;'>User</th>
                        <th style='padding:10px 12px;color:#f8fafc;font-weight:800;text-align:center;'>Pos</th>
                        <th style='padding:10px 12px;color:#f8fafc;font-weight:800;text-align:center;'>Bucket</th>
                        <th style='padding:10px 12px;color:#f8fafc;font-weight:800;text-align:center;'>College OVR</th>
                        <th style='padding:10px 12px;color:#f8fafc;font-weight:800;text-align:center;'>NFL Rookie OVR</th>
                        <th style='padding:10px 12px;color:#f8fafc;font-weight:800;text-align:left;'>NFL Team</th>
                        <th style='padding:10px 12px;color:#f8fafc;font-weight:800;text-align:center;'>Rookie Role</th>
                        <th style='padding:10px 12px;color:#f8fafc;font-weight:800;text-align:center;'>Career Tier</th>
                        <th style='padding:10px 12px;color:#f8fafc;font-weight:800;text-align:left;'>Story Tag</th>
                      </tr>
                    </thead>
                    <tbody>{''.join(_draft_rows_html)}</tbody>
                  </table>
                </div>
                """
                st.markdown(_draft_table_html, unsafe_allow_html=True)
                st.markdown("#### User Summary")
                user_sum = (
                    yr_df.groupby("CollegeUser", dropna=False)
                    .agg(
                        Players=("Player", "count"),
                        FirstRounders=("DraftRoundCanon", lambda s: int((pd.to_numeric(s, errors="coerce") == 1).sum())),
                        AvgPick=("GeneratedOverallPick", lambda s: round(pd.to_numeric(s, errors="coerce").mean(), 1)),
                    )
                    .reset_index()
                    .rename(columns={"CollegeUser": "User"})
                    .sort_values(["Players", "FirstRounders"], ascending=False)
                )
                st.dataframe(user_sum, hide_index=True, use_container_width=True)
            
    # ── Season Recap ────────────────────────────────────────────────
        with nfl_tabs[1]:
            st.subheader("🏁 NFL Season Recap")

            if nfl_standings_hist.empty and nfl_super_bowl.empty:
                st.info("No NFL season has been simulated yet.")
            else:
                available_seasons = set()

                if nfl_standings_hist is not None and not nfl_standings_hist.empty and "Season" in nfl_standings_hist.columns:
                    available_seasons.update(
                        pd.to_numeric(nfl_standings_hist["Season"], errors="coerce").dropna().astype(int).tolist()
                    )

                if nfl_super_bowl is not None and not nfl_super_bowl.empty and "Season" in nfl_super_bowl.columns:
                    available_seasons.update(
                        pd.to_numeric(nfl_super_bowl["Season"], errors="coerce").dropna().astype(int).tolist()
                    )

                available_seasons = sorted(list(available_seasons))
                if not available_seasons:
                    st.info("No NFL season recap data yet.")
                else:
                    sel_season = st.selectbox(
                        "Select NFL Season",
                        available_seasons,
                        index=len(available_seasons) - 1,
                        key="nfl_season_recap_select"
                    )

                    season_standings = pd.DataFrame()
                    if nfl_standings_hist is not None and not nfl_standings_hist.empty:
                        tmp = nfl_standings_hist.copy()
                        tmp["Season"] = pd.to_numeric(tmp["Season"], errors="coerce")
                        season_standings = tmp[tmp["Season"].fillna(-1).astype(int) == int(sel_season)].copy()

                    season_sb = pd.DataFrame()
                    if nfl_super_bowl is not None and not nfl_super_bowl.empty:
                        tmp_sb = nfl_super_bowl.copy()
                        tmp_sb["Season"] = pd.to_numeric(tmp_sb["Season"], errors="coerce")
                        season_sb = tmp_sb[tmp_sb["Season"].fillna(-1).astype(int) == int(sel_season)].copy()

                    season_players = pd.DataFrame()
                    if nfl_player_hist is not None and not nfl_player_hist.empty:
                        tmp_ph = nfl_player_hist.copy()
                        tmp_ph["Season"] = pd.to_numeric(tmp_ph["Season"], errors="coerce")
                        season_players = tmp_ph[tmp_ph["Season"].fillna(-1).astype(int) == int(sel_season)].copy()

                    if not season_sb.empty:
                        sb_row = season_sb.iloc[0]
                        champ = str(sb_row.get("Champion", "Unknown Team"))
                        runner = str(sb_row.get("RunnerUp", "Unknown Team"))
                        score = str(sb_row.get("Score", ""))
                        mvp = str(sb_row.get("MVP", ""))
                        headline = str(sb_row.get("Headline", ""))
                        game_moment = clean_display(sb_row.get("GameMoment", ""), "")
                        user_note = clean_display(sb_row.get("UserAlumniNote", ""), "")

                        champ_logo = get_nfl_logo_src(champ)
                        runner_logo = get_nfl_logo_src(runner)

                        short_headline = f"{champ} def. {runner}" if champ and runner else headline

                        st.markdown("#### 🏆 Super Bowl")

                        sb_left, sb_mid, sb_right = st.columns([1.15, 1.5, 1.15])

                        with sb_left:
                            c1, c2, c3 = st.columns([1, 2, 1])
                            with c2:
                                if champ_logo:
                                    st.image(champ_logo, width=68)
                            st.caption("CHAMPION")
                            st.markdown(f"## {champ}")

                        with sb_mid:
                            st.caption("FINAL")
                            st.markdown(f"# {score if score else '—'}")
                            st.write(short_headline)

                            if mvp:
                                st.markdown(
                                    f"""
                                    <div style="margin-top:8px; margin-bottom:4px;">
                                        <span style="
                                            display:inline-block;
                                            background:rgba(234,179,8,0.18);
                                            color:#fef3c7;
                                            border:1px solid rgba(234,179,8,0.32);
                                            font-size:0.82rem;
                                            font-weight:800;
                                            padding:6px 10px;
                                            border-radius:999px;
                                        ">
                                            Super Bowl MVP: {html.escape(mvp)}
                                        </span>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )

                            if game_moment:
                                st.caption(game_moment)

                            if user_note:
                                st.caption(user_note)

                        with sb_right:
                            c1, c2, c3 = st.columns([1, 2, 1])
                            with c2:
                                if runner_logo:
                                    st.image(runner_logo, width=68)
                            st.caption("RUNNER-UP")
                            st.markdown(f"## {runner}")

                        st.markdown("---")

                    if not season_standings.empty:
                        st.markdown("#### Final Standings")

                        standings_show = season_standings.copy().sort_values(
                            ["Seed", "Wins", "TeamPower"],
                            ascending=[True, False, False]
                        )

                        standings_show.insert(1, "Logo", standings_show["Team"].map(get_nfl_logo_src))

                        standings_show = standings_show[[
                            "Seed", "Logo", "Team", "Wins", "Losses", "WinPct",
                            "TeamPower", "QBScore", "OffenseScore", "DefenseScore", "StarPower"
                        ]]

                        st.dataframe(
                            standings_show,
                            hide_index=True,
                            use_container_width=True,
                            column_config={
                                "Logo": st.column_config.ImageColumn(""),
                                "WinPct": st.column_config.NumberColumn(format="%.3f"),
                                "TeamPower": st.column_config.NumberColumn(format="%.1f"),
                                "QBScore": st.column_config.NumberColumn(format="%.1f"),
                                "OffenseScore": st.column_config.NumberColumn(format="%.1f"),
                                "DefenseScore": st.column_config.NumberColumn(format="%.1f"),
                            }
                        )

                    season_playoff = pd.DataFrame()
                    if nfl_playoff_hist is not None and not nfl_playoff_hist.empty:
                        tmp_po = nfl_playoff_hist.copy()
                        tmp_po["Season"] = pd.to_numeric(tmp_po["Season"], errors="coerce")
                        season_playoff = tmp_po[
                            tmp_po["Season"].fillna(-1).astype(int) == int(sel_season)
                        ].copy()

                    if not season_playoff.empty:
                        st.markdown("#### Playoff Path")

                        round_order = {
                            "Wild Card": 1,
                            "Divisional": 2,
                            "Conference Championship": 3,
                            "Super Bowl": 4
                        }

                        season_playoff["__round_order"] = season_playoff["Round"].astype(str).map(round_order).fillna(99)
                        season_playoff = season_playoff.sort_values(["__round_order", "Winner", "Loser"]).copy()

                        for round_name in ["Wild Card", "Divisional", "Conference Championship", "Super Bowl"]:
                            round_df = season_playoff[season_playoff["Round"].astype(str) == round_name].copy()
                            if round_df.empty:
                                continue

                            st.markdown(f"##### {round_name}")

                            round_show = round_df.copy()
                            round_show.insert(1, "Winner Logo", round_show["Winner"].map(get_nfl_logo_src))
                            round_show.insert(4, "Loser Logo", round_show["Loser"].map(get_nfl_logo_src))

                            round_show = round_show[[
                                "Winner", "Winner Logo", "Score", "Loser", "Loser Logo"
                            ]]

                            st.dataframe(
                                round_show,
                                hide_index=True,
                                use_container_width=True,
                                column_config={
                                    "Winner Logo": st.column_config.ImageColumn(""),
                                    "Loser Logo": st.column_config.ImageColumn(""),
                                }
                            )

                    if not season_players.empty:
                        st.markdown("#### Top Alumni Seasons")

                        season_players["CareerValue"] = pd.to_numeric(season_players["CareerValue"], errors="coerce").fillna(0)
                        season_players["OverallEnd"] = pd.to_numeric(season_players["OverallEnd"], errors="coerce").fillna(0)

                        top_alumni = season_players.sort_values(
                            ["CareerValue", "OverallEnd"],
                            ascending=[False, False]
                        ).head(15).copy()

                        draft_lookup = {}
                        if nfl_draft_hist is not None and not nfl_draft_hist.empty:
                            for _, dr in nfl_draft_hist.iterrows():
                                draft_lookup[str(dr.get("PlayerID", ""))] = {
                                    "CollegeTeam": dr.get("CollegeTeam", ""),
                                    "CollegeUser": dr.get("CollegeUser", "")
                                }

                        top_alumni["CollegeTeam"] = top_alumni["PlayerID"].map(lambda x: draft_lookup.get(str(x), {}).get("CollegeTeam", ""))
                        top_alumni["CollegeUser"] = top_alumni["PlayerID"].map(lambda x: draft_lookup.get(str(x), {}).get("CollegeUser", ""))
                        top_alumni.insert(1, "NFL Logo", top_alumni["NFLTeam"].map(get_nfl_logo_src))
                        top_alumni.insert(4, "School Logo", top_alumni["CollegeTeam"].map(get_school_logo_src))

                        top_alumni = top_alumni[[
                            "Player", "NFL Logo", "NFLTeam", "School Logo", "CollegeTeam", "CollegeUser",
                            "Pos", "Role", "OverallEnd", "Games", "Starts", "StatLine",
                            "ProBowl", "AllPro", "SuperBowlWin", "CareerValue"
                        ]]

                        st.dataframe(
                            top_alumni,
                            hide_index=True,
                            use_container_width=True,
                            column_config={
                                "NFL Logo": st.column_config.ImageColumn(""),
                                "School Logo": st.column_config.ImageColumn(""),
                                "CareerValue": st.column_config.NumberColumn(format="%.1f"),
                            }
                        )
                    
                    
    # ── Awards ───────────────────────────────────────────────────────
        with nfl_tabs[2]:
            st.subheader("🏅 NFL Awards")

            if nfl_awards_hist.empty:
                st.info("No NFL awards have been generated yet.")
            else:
                award_seasons = sorted(
                    pd.to_numeric(nfl_awards_hist["Season"], errors="coerce")
                    .dropna()
                    .astype(int)
                    .unique()
                    .tolist()
                )

                if not award_seasons:
                    st.info("No NFL awards have been generated yet.")
                else:
                    sel_award_season = st.selectbox(
                        "Award Season",
                        award_seasons,
                        index=len(award_seasons) - 1,
                        key="nfl_awards_season_select"
                    )

                    awards_df = nfl_awards_hist.copy()
                    awards_df["Season"] = pd.to_numeric(awards_df["Season"], errors="coerce")
                    awards_df = awards_df[
                        awards_df["Season"].fillna(-1).astype(int) == int(sel_award_season)
                    ].copy()

                    if awards_df.empty:
                        st.info("No awards found for that season.")
                    else:
                        draft_lookup = {}
                        if nfl_draft_hist is not None and not nfl_draft_hist.empty:
                            for _, dr in nfl_draft_hist.iterrows():
                                draft_lookup[str(dr.get("PlayerID", ""))] = {
                                    "CollegeTeam": dr.get("CollegeTeam", ""),
                                    "CollegeUser": dr.get("CollegeUser", "")
                                }

                        awards_df["CollegeTeam"] = awards_df["PlayerID"].map(
                            lambda x: draft_lookup.get(str(x), {}).get("CollegeTeam", "")
                        )
                        awards_df["CollegeUser"] = awards_df["PlayerID"].map(
                            lambda x: draft_lookup.get(str(x), {}).get("CollegeUser", "")
                        )

                        major_awards = awards_df[
                                awards_df["Award"].astype(str).isin([
                                    "NFL MVP",
                                    "Offensive Player of the Year",
                                    "Defensive Player of the Year",
                                    "Offensive Rookie of the Year",
                                    "Defensive Rookie of the Year"
                                ])
                            ].copy()

                        if not major_awards.empty:
                            st.markdown("#### Major Awards")

                            for _, r in major_awards.iterrows():
                                nfl_team = str(r.get("NFLTeam", ""))
                                school = str(r.get("CollegeTeam", ""))
                                player = str(r.get("Player", ""))
                                award = str(r.get("Award", ""))
                                notes = str(r.get("Notes", ""))
                                college_user = clean_display(r.get("CollegeUser", ""), "")

                                school_logo_src = get_school_logo_src(school)
                                nfl_logo_src = get_nfl_logo_src(nfl_team)

                                a1, a2 = st.columns([6, 1])

                                with a1:
                                    left1, left2 = st.columns([1, 8])

                                    with left1:
                                        if school_logo_src:
                                            st.image(school_logo_src, width=42)

                                    with left2:
                                        st.markdown(
                                            f"""
                                            <div style="
                                                padding:0.9rem 1rem;
                                                border-radius:12px;
                                                margin-bottom:0.75rem;
                                                background:linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
                                                border-left:5px solid #eab308;
                                            ">
                                                <div style="font-weight:800; font-size:1rem; color:#ffffff;">
                                                    {html.escape(player)}
                                                </div>
                                                <div style="font-size:0.9rem; color:#facc15; font-weight:700;">
                                                    {html.escape(award)}
                                                </div>
                                                <div style="font-size:0.9rem; color:#d1d5db; margin-top:4px;">
                                                    {html.escape(school)} • {html.escape(str(r.get("Pos", "")))} • {html.escape(nfl_team)}
                                                </div>
                                                <div style="font-size:0.86rem; color:#cbd5e1; margin-top:4px;">
                                                    {html.escape(notes)}
                                                </div>
                                                <div style="margin-top:8px;">
                                                    <span style="display:inline-block;background:{'rgba(34,197,94,0.18)' if college_user else 'rgba(59,130,246,0.18)'};color:{'#dcfce7' if college_user else '#dbeafe'};border:1px solid {'rgba(34,197,94,0.35)' if college_user else 'rgba(59,130,246,0.30)'};font-size:0.78rem;font-weight:700;padding:4px 8px;border-radius:999px;">
                                                        {html.escape(college_user) if college_user else 'CPU'}
                                                    </span>
                                                </div>
                                            </div>
                                            """,
                                            unsafe_allow_html=True
                                        )

                                with a2:
                                    if nfl_logo_src:
                                        st.image(nfl_logo_src, width=42)

                        st.markdown("#### Awards Table")

                        awards_show = awards_df.copy()
                        awards_show.insert(1, "NFL Logo", awards_show["NFLTeam"].map(get_nfl_logo_src))
                        awards_show.insert(5, "School Logo", awards_show["CollegeTeam"].map(get_school_logo_src))

                        awards_show = awards_show[[
                            "Award", "Player", "NFL Logo", "NFLTeam", "Pos",
                            "School Logo", "CollegeTeam", "CollegeUser", "Result", "Notes"
                        ]].copy().rename(columns={
                            "NFLTeam": "NFL Team",
                            "CollegeTeam": "School",
                            "CollegeUser": "User"
                        })

                        st.dataframe(
                            awards_show,
                            hide_index=True,
                            use_container_width=True,
                            column_config={
                                "NFL Logo": st.column_config.ImageColumn(""),
                                "School Logo": st.column_config.ImageColumn(""),
                            }
                        )

                        st.markdown("#### Award Counts by NFL Team")
                        team_award_counts = (
                            awards_df.groupby("NFLTeam")
                            .size()
                            .reset_index(name="Awards")
                            .sort_values(["Awards", "NFLTeam"], ascending=[False, True])
                        )
                        team_award_counts.insert(1, "Logo", team_award_counts["NFLTeam"].map(get_nfl_logo_src))

                        st.dataframe(
                            team_award_counts,
                            hide_index=True,
                            use_container_width=True,
                            column_config={
                                "Logo": st.column_config.ImageColumn("")
                            }
                        )

    # ── Offseason Recap ───────────────────────────────────────────────
        with nfl_tabs[3]:
            st.subheader("🧾 NFL Offseason Recap")

            offseason_season = get_current_nfl_season()

            if nfl_current_rosters is None or nfl_current_rosters.empty:
                st.info("No offseason roster data is available yet.")
            else:
                offseason_roster = nfl_current_rosters.copy()
                if "Season" in offseason_roster.columns:
                    offseason_roster["Season"] = pd.to_numeric(offseason_roster["Season"], errors="coerce")
                    available_roster_seasons = sorted(
                        offseason_roster["Season"].dropna().astype(int).unique().tolist()
                    )
                else:
                    available_roster_seasons = []

                if not available_roster_seasons:
                    st.info("No offseason roster data is available yet.")
                else:
                    sel_offseason_year = st.selectbox(
                        "Offseason For Season",
                        available_roster_seasons,
                        index=len(available_roster_seasons) - 1,
                        key="nfl_offseason_recap_year"
                    )

                    roster_year_df = offseason_roster[
                        offseason_roster["Season"].fillna(-1).astype(int) == int(sel_offseason_year)
                    ].copy()

                    player_hist_work = nfl_player_hist.copy() if nfl_player_hist is not None else pd.DataFrame()
                    if not player_hist_work.empty and "Season" in player_hist_work.columns:
                        player_hist_work["Season"] = pd.to_numeric(player_hist_work["Season"], errors="coerce")

                    prior_season = int(sel_offseason_year) - 1
                    prior_hist_df = player_hist_work[
                        player_hist_work["Season"].fillna(-1).astype(int) == prior_season
                    ].copy() if not player_hist_work.empty else pd.DataFrame()

                    retire_df = prior_hist_df[
                        prior_hist_df["Status"].astype(str) == "Retired"
                    ].copy() if not prior_hist_df.empty else pd.DataFrame()

                    out_df = prior_hist_df[
                        prior_hist_df["Status"].astype(str) == "Out of League"
                    ].copy() if not prior_hist_df.empty else pd.DataFrame()

                    udfa_df = roster_year_df[
                        roster_year_df["Source"].astype(str) == "udfa_fill"
                    ].copy() if not roster_year_df.empty and "Source" in roster_year_df.columns else pd.DataFrame()

                    vet_fill_df = roster_year_df[
                        roster_year_df["Source"].astype(str) == "free_agent_fill"
                    ].copy() if not roster_year_df.empty and "Source" in roster_year_df.columns else pd.DataFrame()

                    rookie_add_df = roster_year_df[
                        roster_year_df["Source"].astype(str).isin(["dynasty_player", "udfa_fill"])
                    ].copy() if not roster_year_df.empty and "Source" in roster_year_df.columns else pd.DataFrame()

                    k1, k2, k3, k4, k5 = st.columns(5)
                    with k1:
                        st.metric("Retirements", len(retire_df))
                    with k2:
                        st.metric("Out of League", len(out_df))
                    with k3:
                        st.metric("UDFA Adds", len(udfa_df))
                    with k4:
                        st.metric("Veteran Fill Adds", len(vet_fill_df))
                    with k5:
                        st.metric("Dynasty / UDFA Adds", len(rookie_add_df))

                    c1, c2 = st.columns(2)

                    with c1:
                        st.markdown("#### Retirements")
                        if retire_df.empty:
                            st.caption("No retirements recorded.")
                        else:
                            retire_show = retire_df.copy()
                            retire_show = retire_show[[
                                c for c in ["Player", "NFLTeam", "Pos", "Age", "OverallEnd", "Status"] if c in retire_show.columns
                            ]]
                            st.dataframe(retire_show.head(20), hide_index=True, use_container_width=True)

                    with c2:
                        st.markdown("#### Out of League")
                        if out_df.empty:
                            st.caption("No washouts recorded.")
                        else:
                            out_show = out_df.copy()
                            out_show = out_show[[
                                c for c in ["Player", "NFLTeam", "Pos", "Age", "OverallEnd", "Status"] if c in out_show.columns
                            ]]
                            st.dataframe(out_show.head(20), hide_index=True, use_container_width=True)

                    c3, c4 = st.columns(2)

                    with c3:
                        st.markdown("#### UDFA Signings")
                        if udfa_df.empty:
                            st.caption("No UDFA additions recorded.")
                        else:
                            udfa_show = udfa_df.copy()
                            if "Name" in udfa_show.columns and "Player" not in udfa_show.columns:
                                udfa_show["Player"] = udfa_show["Name"]
                            udfa_show = udfa_show[[
                                c for c in ["Player", "Team", "Pos", "OVR", "Age", "CollegeTeam", "CollegeUser"] if c in udfa_show.columns
                            ]]
                            udfa_show = udfa_show.rename(columns={"Team": "NFL Team", "CollegeTeam": "School", "CollegeUser": "User"})
                            st.dataframe(udfa_show.head(25), hide_index=True, use_container_width=True)

                    with c4:
                        st.markdown("#### Veteran Fill Signings")
                        if vet_fill_df.empty:
                            st.caption("No veteran fill additions recorded.")
                        else:
                            vet_show = vet_fill_df.copy()
                            if "Name" in vet_show.columns and "Player" not in vet_show.columns:
                                vet_show["Player"] = vet_show["Name"]
                            vet_show = vet_show[[
                                c for c in ["Player", "Team", "Pos", "OVR", "Age", "Source"] if c in vet_show.columns
                            ]]
                            vet_show = vet_show.rename(columns={"Team": "NFL Team"})
                            if "Source" in vet_show.columns:
                                vet_show["Source"] = vet_show["Source"].replace({"free_agent_fill": "Veteran Fill"})
                            st.dataframe(vet_show.head(25), hide_index=True, use_container_width=True)

                    st.markdown("#### Top Rookie / New Additions by Team")
                    if rookie_add_df.empty:
                        st.caption("No new additions found.")
                    else:
                        rookie_show = rookie_add_df.copy()
                        if "Name" in rookie_show.columns and "Player" not in rookie_show.columns:
                            rookie_show["Player"] = rookie_show["Name"]

                        rookie_show["OVR"] = pd.to_numeric(rookie_show["OVR"], errors="coerce").fillna(0)
                        rookie_show = rookie_show.sort_values(["Team", "OVR"], ascending=[True, False]).copy()

                        rookie_show = rookie_show[[
                            c for c in ["Team", "Player", "Pos", "OVR", "Age", "Source", "CollegeTeam", "CollegeUser"] if c in rookie_show.columns
                        ]].rename(columns={
                            "Team": "NFL Team",
                            "CollegeTeam": "School",
                            "CollegeUser": "User"
                        })

                        if "Source" in rookie_show.columns:
                            rookie_show["Source"] = rookie_show["Source"].replace({
                                "dynasty_player": "Drafted Dynasty",
                                "udfa_fill": "UDFA"
                            })

                        st.dataframe(rookie_show.head(50), hide_index=True, use_container_width=True)          
                        # ── NFL Player Database ───────────────────────────────────────────
        with nfl_tabs[4]:
            st.subheader("📚 NFL Player Database")

            if nfl_player_hist is None or nfl_player_hist.empty:
                st.info("No NFL player history exists yet.")
            else:
                db_hist = nfl_player_hist.copy()
                db_hist["Season"] = pd.to_numeric(db_hist["Season"], errors="coerce")
                db_hist["Age"] = pd.to_numeric(db_hist.get("Age", 0), errors="coerce")
                db_hist["OverallStart"] = pd.to_numeric(db_hist.get("OverallStart", 0), errors="coerce")
                db_hist["OverallEnd"] = pd.to_numeric(db_hist.get("OverallEnd", 0), errors="coerce")
                db_hist["CareerValue"] = pd.to_numeric(db_hist.get("CareerValue", 0), errors="coerce")

                draft_lookup = {}
                if nfl_draft_hist is not None and not nfl_draft_hist.empty:
                    for _, dr in nfl_draft_hist.iterrows():
                        draft_lookup[str(dr.get("PlayerID", ""))] = {
                            "CollegeTeam": dr.get("CollegeTeam", ""),
                            "CollegeUser": dr.get("CollegeUser", ""),
                            "DraftYear": dr.get("DraftYear", ""),
                            "DraftRoundCanon": dr.get("DraftRoundCanon", ""),
                            "GeneratedOverallPick": dr.get("GeneratedOverallPick", ""),
                            "OVR": dr.get("OVR", ""),
                            "PeakOVR": dr.get("PeakOVR", ""),
                            "CareerTier": dr.get("CareerTier", ""),
                            "RookieRole": dr.get("RookieRole", ""),
                            "DraftSource": dr.get("DraftSource", "")
                        }

                latest_rows = db_hist.sort_values(["PlayerID", "Season"]).drop_duplicates(subset=["PlayerID"], keep="last").copy()
                latest_rows["PlayerLabel"] = latest_rows.apply(
                    lambda r: f"{r.get('Player', 'Unknown')} | {r.get('NFLTeam', '')} | {r.get('Pos', '')}",
                    axis=1
                )

                search_text = st.text_input("Search Player", key="nfl_player_db_search").strip().lower()

                filtered_latest = latest_rows.copy()
                if search_text:
                    filtered_latest = filtered_latest[
                        filtered_latest["PlayerLabel"].astype(str).str.lower().str.contains(search_text, na=False)
                    ].copy()

                filtered_latest = filtered_latest.sort_values(["Player", "NFLTeam"], ascending=[True, True]).copy()

                if filtered_latest.empty:
                    st.info("No players match that search.")
                else:
                    selected_label = st.selectbox(
                        "Select NFL Player",
                        filtered_latest["PlayerLabel"].tolist(),
                        key="nfl_player_db_select"
                    )

                    selected_row = filtered_latest[filtered_latest["PlayerLabel"] == selected_label].iloc[0].copy()
                    selected_player_id = str(selected_row.get("PlayerID", ""))

                    player_hist_df = db_hist[
                        db_hist["PlayerID"].astype(str) == selected_player_id
                    ].copy().sort_values("Season")

                    draft_meta = draft_lookup.get(selected_player_id, {})
                    school = clean_display(draft_meta.get("CollegeTeam", ""), "")
                    college_user = clean_display(draft_meta.get("CollegeUser", ""), "")
                    current_team = clean_display(selected_row.get("NFLTeam", ""), "")
                    player_name = clean_display(selected_row.get("Player", "Unknown Player"), "Unknown Player")
                    pos = clean_display(selected_row.get("Pos", ""), "")
                    current_age = int(safe_num(selected_row.get("Age", 0), 0))
                    current_status = clean_display(selected_row.get("Status", ""), "")
                    draft_year = clean_display(draft_meta.get("DraftYear", ""), "")
                    draft_round = clean_display(draft_meta.get("DraftRoundCanon", ""), "")
                    draft_pick = clean_display(draft_meta.get("GeneratedOverallPick", ""), "")
                    rookie_ovr = clean_display(draft_meta.get("OVR", ""), "")
                    peak_ovr = clean_display(draft_meta.get("PeakOVR", ""), "")
                    career_tier = clean_display(draft_meta.get("CareerTier", ""), "")
                    rookie_role = clean_display(draft_meta.get("RookieRole", ""), "")

                    school_logo_src = get_school_logo_src(school) if school else None
                    team_logo_src = get_nfl_logo_src(current_team) if current_team else None

                    h1, h2, h3 = st.columns([1, 4, 1])

                    with h1:
                        if school_logo_src:
                            st.image(school_logo_src, width=58)

                    with h2:
                        st.markdown(f"### {player_name}")
                        meta_line = f"{current_team} • {pos}"
                        if school:
                            meta_line += f" • {school}"
                        st.caption(meta_line)

                        badge_text = college_user if college_user else ("NFL Vet" if not school else "CPU")
                        badge_bg = "rgba(34,197,94,0.18)" if college_user else "rgba(59,130,246,0.18)"
                        badge_fg = "#dcfce7" if college_user else "#dbeafe"
                        badge_bd = "rgba(34,197,94,0.35)" if college_user else "rgba(59,130,246,0.30)"

                        st.markdown(
                            f"""
                            <span style="display:inline-block;background:{badge_bg};color:{badge_fg};border:1px solid {badge_bd};font-size:0.78rem;font-weight:700;padding:4px 8px;border-radius:999px;">
                                {html.escape(badge_text)}
                            </span>
                            """,
                            unsafe_allow_html=True
                        )

                    with h3:
                        if team_logo_src:
                            st.image(team_logo_src, width=58)

                    k1, k2, k3, k4, k5, k6 = st.columns(6)
                    with k1:
                        st.metric("Age", current_age if current_age else "—")
                    with k2:
                        st.metric("Status", current_status if current_status else "—")
                    with k3:
                        st.metric("Draft Yr", draft_year if draft_year else "—")
                    with k4:
                        st.metric("Rnd/Pick", f"{draft_round}/{draft_pick}" if draft_round and draft_pick else (draft_round if draft_round else "—"))
                    with k5:
                        st.metric("Rookie OVR", rookie_ovr if rookie_ovr else "—")
                    with k6:
                        st.metric("Peak OVR", peak_ovr if peak_ovr else "—")

                    s1, s2, s3, s4, s5 = st.columns(5)
                    with s1:
                        st.metric("Seasons", len(player_hist_df))
                    with s2:
                        st.metric("Pro Bowls", int((player_hist_df.get("ProBowl", pd.Series(dtype=str)).astype(str) == "Yes").sum()))
                    with s3:
                        st.metric("All-Pros", int((player_hist_df.get("AllPro", pd.Series(dtype=str)).astype(str) == "Yes").sum()))
                    with s4:
                        st.metric("SB Wins", int((player_hist_df.get("SuperBowlWin", pd.Series(dtype=str)).astype(str) == "Yes").sum()))
                    with s5:
                        st.metric("Best OVR", int(player_hist_df["OverallEnd"].max()) if not player_hist_df.empty else "—")

                    info_cols = st.columns(2)
                    with info_cols[0]:
                        st.markdown("#### Draft / Career Info")
                        st.write(f"Career Tier: {career_tier if career_tier else '—'}")
                        st.write(f"Rookie Role: {rookie_role if rookie_role else '—'}")

                    with info_cols[1]:
                        st.markdown("#### Awards Summary")
                        player_awards = pd.DataFrame()
                        if nfl_awards_hist is not None and not nfl_awards_hist.empty:
                            player_awards = nfl_awards_hist[
                                nfl_awards_hist["PlayerID"].astype(str) == selected_player_id
                            ].copy()

                        if player_awards.empty:
                            st.caption("No awards recorded.")
                        else:
                            award_counts = player_awards["Award"].astype(str).value_counts().reset_index()
                            award_counts.columns = ["Award", "Count"]
                            st.dataframe(award_counts, hide_index=True, use_container_width=True)

                    st.markdown("#### Season-by-Season Career Log")

                    if player_hist_df.empty:
                        st.info("No season history recorded for this player.")
                    else:
                        history_show = player_hist_df[[
                            c for c in [
                                "Season", "NFLTeam", "Pos", "Age", "Role",
                                "OverallStart", "OverallEnd", "Games", "Starts",
                                "StatLine", "ProBowl", "AllPro",
                                "SuperBowlAppear", "SuperBowlWin", "Status", "CareerValue"
                            ] if c in player_hist_df.columns
                        ]].copy()

                        st.dataframe(
                            history_show,
                            hide_index=True,
                            use_container_width=True,
                            column_config={
                                "CareerValue": st.column_config.NumberColumn(format="%.1f")
                            }
                        )                        
                                                                                                                  
        # ── Alumni Tracker ────────────────────────────────────────────────
        with nfl_tabs[5]:
            st.subheader("👤 Alumni Tracker")

            if nfl_draft_hist.empty:
                st.info("No alumni tracked yet.")
            else:
                users = ["All"] + sorted([u for u in nfl_draft_hist["CollegeUser"].dropna().astype(str).unique().tolist() if u.strip()])
                teams = ["All"] + sorted([t for t in nfl_draft_hist["CollegeTeam"].dropna().astype(str).unique().tolist() if t.strip()])
                buckets = ["All"] + sorted([b for b in nfl_draft_hist["PosBucket"].dropna().astype(str).unique().tolist() if b.strip()])

                f1, f2, f3 = st.columns(3)
                with f1:
                    sel_user = st.selectbox("Filter by User", users, index=0)
                with f2:
                    sel_team = st.selectbox("Filter by College Team", teams, index=0)
                with f3:
                    sel_bucket = st.selectbox("Filter by Position Bucket", buckets, index=0)

                alum = nfl_draft_hist.copy()

                if sel_user != "All":
                    alum = alum[alum["CollegeUser"].astype(str) == sel_user]
                if sel_team != "All":
                    alum = alum[alum["CollegeTeam"].astype(str) == sel_team]
                if sel_bucket != "All":
                    alum = alum[alum["PosBucket"].astype(str) == sel_bucket]

                alum = alum.sort_values(["GeneratedOverallPick", "PeakOVR"], ascending=[True, False])

                display_cols = [
                    "Player", "CollegeTeam", "CollegeUser", "Pos", "PosBucket", "DraftYear", "DraftRoundCanon",
                    "GeneratedOverallPick", "GeneratedNFLTeam", "CareerTier", "RookieRole", "PeakOVR", "StoryTag"
                ]

                alum_show = alum[display_cols].copy().rename(columns={
                    "CollegeTeam": "School",
                    "CollegeUser": "User",
                    "DraftRoundCanon": "Rnd",
                    "GeneratedOverallPick": "Pick",
                    "GeneratedNFLTeam": "NFL Team"
                })

                alum_show.insert(1, "School Logo", alum_show["School"].map(get_school_logo_src))
                alum_show.insert(10, "NFL Logo", alum_show["NFL Team"].map(get_nfl_logo_src))

                st.dataframe(
                    alum_show,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "School Logo": st.column_config.ImageColumn(""),
                        "NFL Logo": st.column_config.ImageColumn(""),
                    }
                )

        # ── Super Bowl History ────────────────────────────────────────────
        with nfl_tabs[6]:
            st.subheader("🏆 Super Bowl History")

            if nfl_super_bowl.empty:
                st.info("No fictional Super Bowl history entered yet.")
            else:
                sb = nfl_super_bowl.copy().sort_values("Season", ascending=False)
                sb.insert(1, "Champion Logo", sb["Champion"].map(get_nfl_logo_src))
                sb.insert(3, "RunnerUp Logo", sb["RunnerUp"].map(get_nfl_logo_src))

                st.dataframe(
                    sb,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Champion Logo": st.column_config.ImageColumn(""),
                        "RunnerUp Logo": st.column_config.ImageColumn(""),
                    }
                )

                st.markdown("#### Franchise Ring Count")
                ring_counts = (
                    sb.groupby("Champion")
                    .size()
                    .reset_index(name="Rings")
                    .sort_values(["Rings", "Champion"], ascending=[False, True])
                )
                ring_counts.insert(1, "Logo", ring_counts["Champion"].map(get_nfl_logo_src))

                st.dataframe(
                    ring_counts,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Logo": st.column_config.ImageColumn(""),
                    }
                )

    # ── Storylines ────────────────────────────────────────────────────
        with nfl_tabs[7]:
            st.subheader("📰 Storylines")

            if nfl_story.empty and not nfl_draft_hist.empty:
                fallback = nfl_draft_hist.copy().sort_values(
                    ["DraftYear", "GeneratedOverallPick"],
                    ascending=[False, True]
                ).head(12)

                for _, r in fallback.iterrows():
                    school = str(r.get("CollegeTeam", ""))
                    nfl_team = str(r.get("GeneratedNFLTeam", ""))
                    headline = f"{str(r.get('Player', ''))} lands with the {nfl_team}"
                    desc = (
                        f"{school} • {str(r.get('Pos', ''))} / {str(r.get('PosBucket', ''))} • "
                        f"Round {int(safe_num(r.get('DraftRoundCanon', 0), 0))} • "
                        f"Pick {int(safe_num(r.get('GeneratedOverallPick', 0), 0))} • "
                        f"{str(r.get('StoryTag', ''))}"
                    )

                    school_logo_src = get_school_logo_src(school)
                    nfl_logo_src = get_nfl_logo_src(nfl_team)

                    st.markdown(
                        "<div style='padding:0.75rem 0.9rem;border-left:5px solid #4f46e5;background:#4f46e510;border-radius:12px;margin-bottom:0.75rem;'>",
                        unsafe_allow_html=True
                    )
                    c1, c2, c3 = st.columns([1, 10, 1])

                    with c1:
                        if school_logo_src:
                            st.image(school_logo_src, width=42)

                    with c2:
                        st.markdown(f"**{headline}**")
                        st.caption(desc)

                    with c3:
                        if nfl_logo_src:
                            st.image(nfl_logo_src, width=42)

                    st.markdown("</div>", unsafe_allow_html=True)

            elif nfl_story.empty:
                st.info("No story events yet.")

            else:
                story_df = nfl_story.copy().sort_values(
                    ["Season", "ImpactScore"],
                    ascending=[False, False]
                ).head(20)

                draft_lookup = {}
                if nfl_draft_hist is not None and not nfl_draft_hist.empty:
                    for _, dr in nfl_draft_hist.iterrows():
                        draft_lookup[str(dr.get("PlayerID", ""))] = {
                            "CollegeTeam": dr.get("CollegeTeam", ""),
                            "CollegeUser": dr.get("CollegeUser", "")
                        }

                for _, r in story_df.iterrows():
                    player_id = str(r.get("PlayerID", ""))
                    school = draft_lookup.get(player_id, {}).get("CollegeTeam", "")
                    college_user = clean_display(draft_lookup.get(player_id, {}).get("CollegeUser", ""), "")
                    nfl_team = str(r.get("NFLTeam", ""))

                    school_logo_src = get_school_logo_src(school)
                    nfl_logo_src = get_nfl_logo_src(nfl_team)

                    event_type = str(r.get("EventType", "")).strip()
                    headline = str(r.get("Headline", "")).strip()
                    description = str(r.get("Description", "")).strip()

                    border_color = "#22c55e" if event_type == "Award" else "#4f46e5" if event_type == "SeasonOutcome" else "#eab308" if event_type == "SuperBowl" else "#334155"
                    bg_color = "rgba(34,197,94,0.08)" if event_type == "Award" else "rgba(79,70,229,0.08)" if event_type == "SeasonOutcome" else "rgba(234,179,8,0.08)" if event_type == "SuperBowl" else "rgba(148,163,184,0.08)"

                    school_logo_html = f"<img src='{school_logo_src}' style='width:42px;height:42px;object-fit:contain;'/>" if school_logo_src else ""
                    nfl_logo_html = f"<img src='{nfl_logo_src}' style='width:42px;height:42px;object-fit:contain;'/>" if nfl_logo_src else ""
                    source_badge = (
                        f"<span style='display:inline-block;background:rgba(34,197,94,0.18);color:#dcfce7;border:1px solid rgba(34,197,94,0.35);font-size:0.78rem;font-weight:700;padding:4px 8px;border-radius:999px;margin-top:8px;'>{html.escape(college_user)}</span>"
                        if college_user else
                        "<span style='display:inline-block;background:rgba(59,130,246,0.18);color:#dbeafe;border:1px solid rgba(59,130,246,0.30);font-size:0.78rem;font-weight:700;padding:4px 8px;border-radius:999px;margin-top:8px;'>CPU</span>"
                    )

                    st.markdown(
                        f'''
                        <div style="padding:0.85rem 1rem;border-left:5px solid {border_color};background:{bg_color};border-radius:12px;margin-bottom:0.8rem;border:1px solid rgba(255,255,255,0.06);">
                          <div style="display:grid;grid-template-columns:48px 1fr 48px;gap:12px;align-items:start;">
                            <div style="display:flex;justify-content:center;align-items:flex-start;min-height:42px;">{school_logo_html}</div>
                            <div>
                              <div style="font-weight:800;color:#f8fafc;font-size:1rem;line-height:1.25;">{html.escape(headline)}</div>
                              <div style="font-size:0.86rem;color:#cbd5e1;margin-top:6px;line-height:1.45;">{html.escape(description)}</div>
                              <div style="margin-top:8px;">{source_badge}</div>
                            </div>
                            <div style="display:flex;justify-content:center;align-items:flex-start;min-height:42px;">{nfl_logo_html}</div>
                          </div>
                        </div>
                        ''',
                        unsafe_allow_html=True
                    )

        # ── NFL Teams ─────────────────────────────────────────────────────
        with nfl_tabs[8]:
            st.subheader("🏟️ NFL Teams")

            if nfl_roster.empty:
                st.info("NFLroster26_MASTER.csv is missing.")
            else:
                team_needs = build_nfl_team_needs(nfl_roster)
                nfl_teams = sorted(nfl_roster["Team"].dropna().astype(str).unique().tolist())
                sel_nfl_team = st.selectbox("Select NFL Team", nfl_teams)

                team_logo = get_nfl_logo_html(sel_nfl_team, width=52, margin="0 12px 0 0")

                st.markdown(
                    f"""
                    <div style="
                        display:flex;
                        align-items:center;
                        gap:12px;
                        padding:0.8rem 1rem;
                        border-radius:12px;
                        background:linear-gradient(135deg, rgba(255,255,255,0.07), rgba(255,255,255,0.02));
                        border:1px solid rgba(255,255,255,0.10);
                        margin-bottom:12px;
                    ">
                        {team_logo}
                        <div>
                            <div style="font-size:0.82rem; color:#9ca3af; text-transform:uppercase; letter-spacing:1px;">
                                NFL Franchise View
                            </div>
                            <div style="font-size:1.3rem; font-weight:800; color:#ffffff;">
                                {html.escape(sel_nfl_team)}
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                selected_team_key = normalize_nfl_team_key(sel_nfl_team)

                selected_team_key = normalize_nfl_team_key(sel_nfl_team)

                selected_team_key = normalize_nfl_team_key(sel_nfl_team)

                current_roster_df = nfl_current_rosters.copy() if nfl_current_rosters is not None and not nfl_current_rosters.empty else pd.DataFrame()
                base_roster_df = nfl_roster.copy() if nfl_roster is not None and not nfl_roster.empty else pd.DataFrame()

                def _prep_roster(df):
                    if df is None or df.empty:
                        return pd.DataFrame()

                    df = df.copy()

                    if "Team" not in df.columns:
                        df["Team"] = ""

                    if "Player" not in df.columns:
                        df["Player"] = pd.NA
                    if "Name" not in df.columns:
                        df["Name"] = pd.NA

                    df["Player"] = df["Player"].where(
                        df["Player"].notna() & (df["Player"].astype(str).str.strip() != ""),
                        df["Name"]
                    )
                    df["Player"] = df["Player"].fillna("Unknown Player")

                    if "Pos" not in df.columns:
                        df["Pos"] = ""

                    if "OVR" not in df.columns:
                        df["OVR"] = 0
                    df["OVR"] = pd.to_numeric(df["OVR"], errors="coerce").fillna(0)

                    df["__team_key"] = df["Team"].astype(str).map(normalize_nfl_team_key)
                    df["PosBucket"] = df["Pos"].map(clean_bucket)
                    return df

                current_roster_df = _prep_roster(current_roster_df)
                base_roster_df = _prep_roster(base_roster_df)

                roster_team_current = current_roster_df[
                    current_roster_df["__team_key"] == selected_team_key
                ].copy() if not current_roster_df.empty else pd.DataFrame()

                roster_team_base = base_roster_df[
                    base_roster_df["__team_key"] == selected_team_key
                ].copy() if not base_roster_df.empty else pd.DataFrame()

                roster_team = roster_team_current.copy() if not roster_team_current.empty else roster_team_base.copy()

                if not roster_team.empty:
                    roster_team = roster_team.sort_values("OVR", ascending=False).copy()
                    roster_team = roster_team.drop(columns=["__team_key"], errors="ignore")
                if not nfl_draft_hist.empty:
                    drafted_here = nfl_draft_hist[nfl_draft_hist["GeneratedNFLTeam"].astype(str) == sel_nfl_team].copy()
                    drafted_here = drafted_here.sort_values(["DraftYear", "GeneratedOverallPick"], ascending=[False, True])

                left, right = st.columns([1.2, 1])

                with left:
                    st.markdown("#### Projected Starters")

                    if roster_team.empty:
                        st.caption("No roster rows found for this team.")
                    else:
                        starter_targets = {
                            "QB": 1,
                            "RB": 1,
                            "WR": 3,
                            "TE": 1,
                            "OL": 5,
                            "EDGE": 2,
                            "IDL": 2,
                            "LB": 3,
                            "CB": 2,
                            "S": 2
                        }

                        roster_work = roster_team.copy()
                        roster_work["OVR"] = pd.to_numeric(roster_work["OVR"], errors="coerce").fillna(0)
                        roster_work["Age"] = pd.to_numeric(roster_work.get("Age", 25), errors="coerce").fillna(25)

                        starter_frames = []
                        for bucket, starter_n in starter_targets.items():
                            room_df = roster_work[
                                roster_work["PosBucket"].astype(str) == str(bucket)
                            ].copy().sort_values(["OVR", "Age"], ascending=[False, True])

                            if room_df.empty:
                                continue

                            starter_frames.append(room_df.head(starter_n).copy())

                        starters_df = pd.concat(starter_frames, ignore_index=True) if starter_frames else pd.DataFrame()

                        if starters_df.empty:
                            st.caption("No projected starters found.")
                        else:
                            show_cols = [c for c in ["Player", "Pos", "PosBucket", "OVR", "Age", "Status", "Source"] if c in starters_df.columns]
                            starters_show = starters_df[show_cols].copy()

                            if "Source" in starters_show.columns:
                                starters_show["Source"] = starters_show["Source"].replace({
                                    "dynasty_player": "Dynasty",
                                    "base_nfl_roster": "Base",
                                    "free_agent_fill": "Veteran Fill",
                                    "udfa_fill": "UDFA"
                                })

                            roster_logo_src = get_nfl_logo_src(sel_nfl_team)
                            starters_show.insert(0, "Team Logo", roster_logo_src if roster_logo_src else "")

                            st.dataframe(
                                starters_show,
                                hide_index=True,
                                use_container_width=True,
                                column_config={
                                    "Team Logo": st.column_config.ImageColumn("")
                                }
                            )

                        st.markdown("#### Depth / Reserves")

                        if starters_df.empty:
                            depth_df = roster_work.copy()
                        else:
                            starter_keys = set(
                                starters_df.apply(
                                    lambda r: f"{str(r.get('Player','')).strip().lower()}||{str(r.get('PosBucket','')).strip().upper()}",
                                    axis=1
                                ).tolist()
                            )

                            roster_work["__starter_key"] = roster_work.apply(
                                lambda r: f"{str(r.get('Player','')).strip().lower()}||{str(r.get('PosBucket','')).strip().upper()}",
                                axis=1
                            )

                            used_keys = set()
                            starter_key_multiset = {}
                            for key in starters_df.apply(
                                lambda r: f"{str(r.get('Player','')).strip().lower()}||{str(r.get('PosBucket','')).strip().upper()}",
                                axis=1
                            ).tolist():
                                starter_key_multiset[key] = starter_key_multiset.get(key, 0) + 1

                            keep_rows = []
                            seen_counts = {}
                            for _, rr in roster_work.iterrows():
                                key = rr["__starter_key"]
                                seen_counts[key] = seen_counts.get(key, 0) + 1
                                if seen_counts[key] > starter_key_multiset.get(key, 0):
                                    keep_rows.append(True)
                                else:
                                    keep_rows.append(False)

                            depth_df = roster_work[keep_rows].copy()
                            depth_df = depth_df.drop(columns=["__starter_key"], errors="ignore")

                        if depth_df.empty:
                            st.caption("No depth/reserve players found.")
                        else:
                            depth_show_cols = [c for c in ["Player", "Pos", "PosBucket", "OVR", "Age", "Status", "Source"] if c in depth_df.columns]
                            depth_show = depth_df[depth_show_cols].head(25).copy()

                            if "Source" in depth_show.columns:
                                depth_show["Source"] = depth_show["Source"].replace({
                                    "dynasty_player": "Dynasty",
                                    "base_nfl_roster": "Base",
                                    "free_agent_fill": "Veteran Fill",
                                    "udfa_fill": "UDFA"
                                })

                            roster_logo_src = get_nfl_logo_src(sel_nfl_team)
                            depth_show.insert(0, "Team Logo", roster_logo_src if roster_logo_src else "")

                            st.dataframe(
                                depth_show,
                                hide_index=True,
                                use_container_width=True,
                                column_config={
                                    "Team Logo": st.column_config.ImageColumn("")
                                }
                            )

                st.markdown("#### Dynasty Alumni on This Team")
                if drafted_here.empty:
                    st.caption("No tracked dynasty alumni generated onto this roster yet.")
                else:
                    drafted_show = drafted_here.copy()

                    if "PosBucket" not in drafted_show.columns and "Pos" in drafted_show.columns:
                        drafted_show["PosBucket"] = drafted_show["Pos"].map(clean_bucket)

                    if "DraftSource" not in drafted_show.columns:
                        drafted_show["DraftSource"] = "user_results"

                    wanted_cols = [
                        "DraftYear", "Player", "CollegeTeam", "CollegeUser", "Pos", "PosBucket",
                        "DraftRoundCanon", "GeneratedOverallPick", "CareerTier", "RookieRole", "DraftSource"
                    ]
                    keep_cols = [c for c in wanted_cols if c in drafted_show.columns]

                    drafted_show = drafted_show[keep_cols].copy().rename(columns={
                        "CollegeTeam": "School",
                        "CollegeUser": "User",
                        "DraftRoundCanon": "Rnd",
                        "GeneratedOverallPick": "Pick",
                        "DraftSource": "Source"
                    })

                    if "School" in drafted_show.columns:
                        drafted_show.insert(2, "School Logo", drafted_show["School"].map(get_school_logo_src))
                    else:
                        drafted_show.insert(2, "School Logo", None)

                    drafted_show.insert(len(drafted_show.columns), "NFL Logo", get_nfl_logo_src(sel_nfl_team))

                    st.dataframe(
                        drafted_show,
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            "School Logo": st.column_config.ImageColumn(""),
                            "NFL Logo": st.column_config.ImageColumn(""),
                        }
                    )

                    # Featured alumni cards
                    st.markdown("#### Featured Alumni")
                    featured = drafted_here.sort_values(
        ["GeneratedOverallPick", "PeakOVR"],
        ascending=[True, False]
    ).head(6).copy()

                    for _, r in featured.iterrows():
                        school = str(r.get("CollegeTeam", ""))
                        nfl_team = str(r.get("GeneratedNFLTeam", ""))
                        college_user = clean_display(r.get("CollegeUser", ""), "")
                        school_logo = get_school_logo_html(school, width=42, margin="0 10px 0 0")
                        nfl_logo = get_nfl_logo_html(nfl_team, width=42, margin="0 0 0 10px")
                        draft_source = str(r.get("DraftSource", "user_results")).strip().lower()

                        if draft_source == "background_r1":
                            badge_html = (
                                '<span style="display:inline-block;background:rgba(148,163,184,0.18);color:#e2e8f0;border:1px solid rgba(148,163,184,0.30);font-size:0.78rem;font-weight:700;padding:4px 8px;border-radius:999px;margin-top:8px;">League Prospect</span>'
                            )
                        elif college_user:
                            badge_html = (
                                f'<span style="display:inline-block;background:rgba(34,197,94,0.18);color:#dcfce7;border:1px solid rgba(34,197,94,0.35);font-size:0.78rem;font-weight:700;padding:4px 8px;border-radius:999px;margin-top:8px;">{html.escape(college_user)}</span>'
                            )
                        else:
                            badge_html = (
                                '<span style="display:inline-block;background:rgba(59,130,246,0.18);color:#dbeafe;border:1px solid rgba(59,130,246,0.30);font-size:0.78rem;font-weight:700;padding:4px 8px;border-radius:999px;margin-top:8px;">CPU</span>'
                            )

                        st.markdown(
                            f"""
                            <div style="
                                padding:0.9rem 1rem;
                                border-radius:12px;
                                margin-bottom:0.75rem;
                                background:linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
                                border-left:5px solid #2563eb;
                            ">
                                <div style="display:flex; justify-content:space-between; align-items:center; gap:12px;">
                                    <div style="display:flex; align-items:center; min-width:0;">
                                        {school_logo}
                                        <div>
                                            <div style="font-weight:800; font-size:1rem; color:#ffffff;">
                                                {html.escape(str(r.get("Player", "")))}
                                            </div>
                                            <div style="font-size:0.9rem; color:#d1d5db;">
                                                {html.escape(school)} • {html.escape(str(r.get("Pos", "")))} / {html.escape(str(r.get("PosBucket", "")))} •
                                                Round {int(safe_num(r.get("DraftRoundCanon", 0), 0))} • Pick {int(safe_num(r.get("GeneratedOverallPick", 0), 0))}
                                            </div>
                                            <div style="font-size:0.86rem; color:#93c5fd; margin-top:4px;">
                                                {html.escape(str(r.get("RookieRole", "")))} • {html.escape(str(r.get("CareerTier", "")))}
                                            </div>
                                            {badge_html}
                                        </div>
                                    </div>
                                    <div style="display:flex; align-items:center;">
                                        {nfl_logo}
                                    </div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    
                        st.markdown("#### Recent Team Transactions")

                current_nfl_season = get_current_nfl_season()
                prior_nfl_season = max(0, int(current_nfl_season) - 1)

                current_roster_team = pd.DataFrame()
                if nfl_current_rosters is not None and not nfl_current_rosters.empty:
                    current_roster_team = nfl_current_rosters[
                        nfl_current_rosters["Team"].astype(str).map(normalize_nfl_team_key) == selected_team_key
                    ].copy()

                    if "Season" in current_roster_team.columns:
                        current_roster_team["Season"] = pd.to_numeric(current_roster_team["Season"], errors="coerce")
                        current_roster_team = current_roster_team[
                            current_roster_team["Season"].fillna(-1).astype(int) == int(current_nfl_season)
                        ].copy()

                additions_df = pd.DataFrame()
                if not current_roster_team.empty and "Source" in current_roster_team.columns:
                    additions_df = current_roster_team[
                        current_roster_team["Source"].astype(str).isin(["dynasty_player", "udfa_fill", "free_agent_fill"])
                    ].copy()

                    if "Name" in additions_df.columns and "Player" not in additions_df.columns:
                        additions_df["Player"] = additions_df["Name"]
                    elif "Name" in additions_df.columns:
                        additions_df["Player"] = additions_df["Player"].where(
                            additions_df["Player"].notna() & (additions_df["Player"].astype(str).str.strip() != ""),
                            additions_df["Name"]
                        )

                    additions_df["SourceLabel"] = additions_df["Source"].astype(str).replace({
                        "dynasty_player": "Drafted / Dynasty Add",
                        "udfa_fill": "UDFA Add",
                        "free_agent_fill": "Veteran Fill"
                    })

                    additions_df["OVR"] = pd.to_numeric(additions_df["OVR"], errors="coerce").fillna(0)
                    additions_df = additions_df.sort_values(["OVR", "Player"], ascending=[False, True]).copy()

                if additions_df.empty:
                    st.caption("No recent additions found for this team.")
                else:
                    add_show = additions_df[[
                        c for c in ["Player", "Pos", "OVR", "Age", "SourceLabel", "CollegeTeam", "CollegeUser"] if c in additions_df.columns
                    ]].copy().rename(columns={
                        "SourceLabel": "Move",
                        "CollegeTeam": "School",
                        "CollegeUser": "User"
                    })

                    st.dataframe(add_show.head(20), hide_index=True, use_container_width=True)

                st.markdown("#### Recent Team Losses")

                team_losses = pd.DataFrame()
                if nfl_player_hist is not None and not nfl_player_hist.empty:
                    hist_tmp = nfl_player_hist.copy()
                    hist_tmp["Season"] = pd.to_numeric(hist_tmp["Season"], errors="coerce")

                    team_losses = hist_tmp[
                        (hist_tmp["NFLTeam"].astype(str).map(normalize_nfl_team_key) == selected_team_key) &
                        (hist_tmp["Season"].fillna(-1).astype(int) == int(prior_nfl_season)) &
                        (hist_tmp["Status"].astype(str).isin(["Retired", "Out of League"]))
                    ].copy()

                if team_losses.empty:
                    st.caption("No recent losses recorded for this team.")
                else:
                    loss_show = team_losses[[
                        c for c in ["Player", "Pos", "Age", "OverallEnd", "Status"] if c in team_losses.columns
                    ]].copy().rename(columns={
                        "OverallEnd": "Last OVR"
                    })

                    st.dataframe(loss_show.head(20), hide_index=True, use_container_width=True)


        st.markdown("---")
        st.subheader("NFL Universe Status")

        s1, s2, s3 = st.columns(3)
        with s1:
            st.metric("Latest Input Draft Year", latest_input_draft_year if latest_input_draft_year else "—")
        with s2:
            st.metric("Latest Saved Draft Year", latest_saved_draft_year if latest_saved_draft_year else "—")
        with s3:
            st.metric("Tracked Drafted Players", len(nfl_draft_hist) if nfl_draft_hist is not None else 0)

        st.caption("Commissioner tools and draft admin controls live below the public NFL Universe sections.")

        with st.expander("🔒 Commissioner Controls", expanded=False):
            commissioner_key = st.text_input(
                "Enter commissioner password",
                type="password",
                key="nfl_commissioner_password"
            )

            if commissioner_key == "Chicken83$":
                st.session_state["nfl_commissioner_unlocked"] = True
                is_commissioner = True
                st.success("Commissioner mode unlocked.")
            elif commissioner_key:
                st.error("Incorrect password.")

        if is_commissioner:
            st.subheader("Commissioner Tools")

            c1, c2 = st.columns([1.15, 1.0])

            with c1:
                reveal_speed = st.selectbox(
                    "Replay Speed",
                    ["Broadcast", "Fast", "Turbo"],
                    index=0,
                    key="nfl_draft_reveal_speed"
                )

            with c2:
                allow_rerun = st.checkbox(
                    "Allow rerun of latest class",
                    value=False,
                    key="nfl_allow_rerun_latest"
                )

            audio_l, audio_c, audio_r = st.columns([1, 1.3, 1])

            with audio_c:
                if st.button("🔊 Enable Draft Audio", use_container_width=True, key="enable_draft_audio_btn_commish"):
                    enable_draft_audio()
                    st.success("Draft audio enabled for this session.")

            st.caption("If Chrome blocks sound, click Enable Draft Audio once before running or replaying the draft.")

            b1, b2, b3 = st.columns(3)

            with b1:
                if st.button("💾 Lock Official Draft", use_container_width=True, key="lock_official_nfl_draft_btn_commish"):
                    try:
                        nfl_draft_hist, processed_year, status_msg = refresh_nfl_draft_history(
                            live_mode=False,
                            speed_mode=reveal_speed,
                            force_latest=False
                        )

                        if processed_year is not None and nfl_draft_hist is not None and not nfl_draft_hist.empty:
                            just_added_class = nfl_draft_hist[
                                pd.to_numeric(nfl_draft_hist["DraftYear"], errors="coerce").fillna(-1).astype(int) == int(processed_year)
                            ].copy()

                            if status_msg and "officially added" in status_msg.lower():
                                existing_story = (
                                    pd.read_csv("nfl_story_events.csv")
                                    if os.path.exists("nfl_story_events.csv")
                                    else pd.DataFrame(columns=NFL_STORY_EVENTS_COLS)
                                )
                                seed_story_events_from_draft_class(just_added_class, existing_story)

                        if status_msg:
                            if "already locked in" in status_msg.lower():
                                st.info(status_msg)
                            elif "officially added" in status_msg.lower():
                                st.success(status_msg)
                            else:
                                st.warning(status_msg)

                    except Exception as e:
                        st.error(f"NFL draft error: {type(e).__name__}: {e}")

            with b2:
                if st.button("▶️ Replay Saved Draft", use_container_width=True, key="replay_saved_nfl_draft_commish"):
                    if latest_saved_draft_year is None:
                        st.warning("No saved draft exists yet.")
                    else:
                        replay_saved_nfl_draft(latest_saved_draft_year, speed_mode=reveal_speed)

            with b3:
                if st.button("🛠️ Admin Rerun Latest", use_container_width=True, key="rerun_latest_nfl_draft"):
                    if not allow_rerun:
                        st.warning("Enable 'Allow rerun of latest class' first.")
                    else:
                        try:
                            nfl_draft_hist, processed_year, status_msg = refresh_nfl_draft_history(
                                live_mode=False,
                                speed_mode=reveal_speed,
                                force_latest=True
                            )

                            if processed_year is not None and nfl_draft_hist is not None and not nfl_draft_hist.empty:
                                just_added_class = nfl_draft_hist[
                                    pd.to_numeric(nfl_draft_hist["DraftYear"], errors="coerce").fillna(-1).astype(int) == int(processed_year)
                                ].copy()

                                if status_msg and "rerun for testing" in status_msg.lower():
                                    existing_story = (
                                        pd.read_csv("nfl_story_events.csv")
                                        if os.path.exists("nfl_story_events.csv")
                                        else pd.DataFrame(columns=NFL_STORY_EVENTS_COLS)
                                    )
                                    seed_story_events_from_draft_class(just_added_class, existing_story)

                            st.warning(status_msg if status_msg else "Latest draft rerun complete.")

                        except Exception as e:
                            import traceback
                            st.error(f"NFL draft rerun error: {type(e).__name__}: {e}")
                            st.code(traceback.format_exc())

            sim_l, sim_c, sim_r = st.columns([1, 1.4, 1])

            with sim_c:
                if st.button("🏆 Advance NFL Season", use_container_width=True, key="advance_nfl_season_btn_commish"):
                    try:
                        sim_result, sim_msg = simulate_nfl_season()
                        if sim_result is None:
                            st.warning(sim_msg)
                        else:
                            st.success(sim_msg)
                            st.rerun()
                    except Exception as e:
                        st.error(f"NFL season sim error: {type(e).__name__}: {e}")

                if st.button("Rebuild Current NFL Rosters Now", use_container_width=True, key="rebuild_current_nfl_rosters_now"):
                    try:
                        season_to_rebuild = get_current_nfl_season()
                        rebuilt = build_nfl_current_roster_for_season(
                            season_year=season_to_rebuild,
                            nfl_roster_df=nfl_roster,
                            nfl_draft_hist_df=nfl_draft_hist,
                            nfl_player_hist_df=nfl_player_hist,
                            existing_current_rosters_df=universe["nfl_current_rosters"] if "nfl_current_rosters" in universe else None
                        )
                        st.success(f"Rebuilt nfl_current_rosters.csv for season {season_to_rebuild}. Rows: {len(rebuilt)}")
                        st.rerun()
                    except Exception as e:
                        import traceback
                        st.error(f"Roster rebuild error: {type(e).__name__}: {e}")
                        st.code(traceback.format_exc())

            if st.button("🧱 Create NFL Settings File", use_container_width=True, key="create_nfl_settings_file_btn"):
                try:
                    initialize_nfl_universe_settings()
                    st.success("nfl_universe_settings.csv created.")
                except Exception as e:
                    st.error(f"Settings file create error: {type(e).__name__}: {e}")

            if os.path.exists("nfl_universe_settings.csv"):
                with open("nfl_universe_settings.csv", "rb") as f:
                    st.download_button(
                        label="⬇️ Download NFL Settings",
                        data=f.read(),
                        file_name="nfl_universe_settings.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="download_nfl_universe_settings"
                    )

            zip_bytes, included_files = build_nfl_export_zip()

            if zip_bytes:
                st.download_button(
                    label="📦 Download Full NFL Universe ZIP",
                    data=zip_bytes,
                    file_name="nfl_universe_export.zip",
                    mime="application/zip",
                    use_container_width=True,
                    key="download_nfl_universe_zip"
                )
                if included_files:
                    st.caption("Included files: " + ", ".join(included_files))
            else:
                st.info("No NFL files found yet to include in the ZIP export.")

            # ── NFL Universe file status / downloads ──────────────────────────
            st.markdown("---")
            st.markdown("#### Commissioner Downloads")

            if os.path.exists("cfb_user_draft_results.csv"):
                with open("cfb_user_draft_results.csv", "rb") as f:
                    st.download_button(
                        label="⬇️ Download Draft Input",
                        data=f.read(),
                        file_name="cfb_user_draft_results.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="download_cfb_user_draft_results"
                    )

            if os.path.exists("nfl_draft_history.csv"):
                with open("nfl_draft_history.csv", "rb") as f:
                    st.download_button(
                        label="⬇️ Download Draft History",
                        data=f.read(),
                        file_name="nfl_draft_history.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="download_nfl_draft_history"
                    )

            if os.path.exists("nfl_player_history.csv"):
                with open("nfl_player_history.csv", "rb") as f:
                    st.download_button(
                        label="⬇️ Download Player History",
                        data=f.read(),
                        file_name="nfl_player_history.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="download_nfl_player_history"
                    )

            if os.path.exists("nfl_super_bowl_history.csv"):
                with open("nfl_super_bowl_history.csv", "rb") as f:
                    st.download_button(
                        label="⬇️ Download Super Bowl History",
                        data=f.read(),
                        file_name="nfl_super_bowl_history.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="download_nfl_super_bowl_history"
                    )

            if os.path.exists("nfl_story_events.csv"):
                with open("nfl_story_events.csv", "rb") as f:
                    st.download_button(
                        label="⬇️ Download Story Events",
                        data=f.read(),
                        file_name="nfl_story_events.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="download_nfl_story_events"
                    )

            if os.path.exists("nfl_current_rosters.csv"):
                with open("nfl_current_rosters.csv", "rb") as f:
                    st.download_button(
                        label="⬇️ Download Current Rosters",
                        data=f.read(),
                        file_name="nfl_current_rosters.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="download_nfl_current_rosters"
                    )


    # --- ROSTER ATTRITION ---
with tabs[5]:
    # --- 0. Logos & Header ---
    def get_attrition_logo(team_name, width=45, margin="0"):
        if 'image_file_to_data_uri' in globals() and 'get_local_logo_path' in globals():
            local_path = get_local_logo_path(team_name)
            if local_path:
                uri = image_file_to_data_uri(local_path)
                if uri:
                    return f'<img src="{uri}" width="{width}" style="margin: {margin}; drop-shadow: 2px 2px 4px rgba(0,0,0,0.5);">'

        slug = TEAM_VISUALS.get(team_name, {}).get("slug", team_name.lower().replace(" ", "-"))
        url = f"https://a.espncdn.com/i/teamlogos/ncaa/500/{slug}.png"
        return f'<img src="{url}" width="{width}" style="margin: {margin}; drop-shadow: 2px 2px 4px rgba(0,0,0,0.5);">'

    if 'USER_TEAMS' in globals():
        user_teams_list = sorted(list(USER_TEAMS.values()))
    else:
        user_teams_list = ["Florida State", "Florida", "Bowling Green", "USF", "Texas Tech", "San Jose State"]

    mid_idx = len(user_teams_list) // 2
    left_teams = user_teams_list[:mid_idx]
    right_teams = user_teams_list[mid_idx:]

    all_logos_html = "".join([
        get_attrition_logo(t, width=45, margin="0 8px")
        for t in user_teams_list
    ])

    st.markdown(f"""
        <div style="text-align:center; margin-bottom: 6px;">
            <h2 style="margin: 0 0 10px 0;">🚪 Roster Turnover</h2>
            <div style="display:flex; justify-content:center; align-items:center; flex-wrap:wrap; gap:4px;">
                {all_logos_html}
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.caption("<div style='text-align: center;'>Tracking players leaving for the NFL, transferring, or graduating, compared against incoming talent.</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    current_yr = CURRENT_YEAR if 'CURRENT_YEAR' in globals() else 2041

# --- 1. CSV Loading Logic (Schema-Safe) ---
    def load_attrition_data(roster_path, cur_year):
        def safe_read_csv(path, fallback_cols):
            try:
                df = pd.read_csv(path)
                if df is None:
                    df = pd.DataFrame(columns=fallback_cols)
            except Exception:
                df = pd.DataFrame(columns=fallback_cols)

            for col in fallback_cols:
                if col not in df.columns:
                    df[col] = pd.NA
            return df

        _rec_all = _load_recruiting_csv()
        _std_rec_cols = ['Year', 'Rank', 'Team', 'User', 'TotalCommits', 'FiveStar', 'FourStar', 'ThreeStar', 'TwoStar', 'OneStar', 'Points']
        if not _rec_all.empty and 'ClassType' in _rec_all.columns:
            hs_df = _rec_all[_rec_all['ClassType'].str.upper() == 'HS'].copy().reset_index(drop=True)
            tp_df = _rec_all[_rec_all['ClassType'].str.upper() == 'TRANSFER'].copy().reset_index(drop=True)
        else:
            hs_df = _rec_all.copy()
            tp_df = pd.DataFrame(columns=_std_rec_cols)

        nfl = safe_read_csv(
            'attrition_nfl.csv',
            ['Year', 'Team', 'Player', 'Position', 'OVR', 'Round', 'Left Early', 'Class', 'Was Starter']
        )

        transfers = safe_read_csv(
            'attrition_transfers.csv',
            ['Team', 'Player', 'Pos', 'Class', 'Year', 'OVR', 'Reason', 'ReasonDetail', 'TransferStatus', 'Persuaded']
        )

        graduates = safe_read_csv(
            'attrition_graduates.csv',
            ['Year', 'Team', 'Player', 'Position', 'OVR', 'Class', 'Was Starter']
        )

        incoming = safe_read_csv(
            'attrition_incoming.csv',
            [
                'Year', 'User', 'Team', 'RecruitSlot', 'Name', 'Pos', 'HT', 'WT',
                'ClassLabel', 'RecruitType', 'State', 'StarRating',
                'NationalRank', 'PositionRank', 'StateRank', 'OverallClassRank',
                'Type', 'Player', 'Position', 'Stars', 'Class', 'ProjectedRole'
            ]
        )

        user_draft_results = safe_read_csv(
            'cfb_user_draft_results.csv',
            ['DraftYear', 'Player', 'CollegeTeam', 'CollegeUser', 'Pos', 'Class', 'OVR', 'DraftRound']
        )

        # --- Normalize NFL departures ---
        if not nfl.empty:
            if 'Position' not in nfl.columns and 'Pos' in nfl.columns:
                nfl['Position'] = nfl['Pos']
            if 'Was Starter' not in nfl.columns:
                nfl['Was Starter'] = False
            if 'Class' not in nfl.columns:
                nfl['Class'] = pd.NA

        # --- Normalize transfers schema ---
        if not transfers.empty:
            if 'Position' in transfers.columns and 'Pos' not in transfers.columns:
                transfers['Pos'] = transfers['Position']

            if 'Pos' in transfers.columns and 'Position' not in transfers.columns:
                transfers['Position'] = transfers['Pos']

            if 'TransferStatus' not in transfers.columns:
                transfers['TransferStatus'] = pd.NA

            transfers['TransferStatus'] = (
                transfers['TransferStatus']
                .fillna('')
                .astype(str)
                .str.strip()
                .str.title()
            )

            if 'ReasonDetail' not in transfers.columns and 'Reason' in transfers.columns:
                transfers['ReasonDetail'] = transfers['Reason']

            if 'Reason' not in transfers.columns:
                transfers['Reason'] = 'Transfer'

            if 'Persuaded' not in transfers.columns:
                transfers['Persuaded'] = pd.NA

            transfers['Persuaded'] = (
                transfers['Persuaded']
                .fillna('')
                .astype(str)
                .str.strip()
                .str.title()
            )

            if 'Was Starter' not in transfers.columns:
                transfers['Was Starter'] = False

            if 'Destination' not in transfers.columns:
                transfers['Destination'] = pd.NA

        # --- Normalize graduates schema ---
        if not graduates.empty:
            if 'Position' not in graduates.columns and 'Pos' in graduates.columns:
                graduates['Position'] = graduates['Pos']
            if 'Was Starter' not in graduates.columns:
                graduates['Was Starter'] = False
            if 'Class' not in graduates.columns:
                graduates['Class'] = pd.NA

        # --- Normalize incoming schema ---
        if not incoming.empty:
            incoming = incoming.copy()

            if 'Player' not in incoming.columns or incoming['Player'].isna().all():
                if 'Name' in incoming.columns:
                    incoming['Player'] = incoming['Name']

            if 'Position' not in incoming.columns or incoming['Position'].isna().all():
                if 'Pos' in incoming.columns:
                    incoming['Position'] = incoming['Pos']

            if 'Stars' not in incoming.columns or incoming['Stars'].isna().all():
                if 'StarRating' in incoming.columns:
                    incoming['Stars'] = pd.to_numeric(incoming['StarRating'], errors='coerce')

            if 'Type' not in incoming.columns or incoming['Type'].isna().all():
                if 'RecruitType' in incoming.columns:
                    incoming['Type'] = (
                        incoming['RecruitType']
                        .fillna('')
                        .astype(str)
                        .str.strip()
                        .str.upper()
                        .replace({
                            'HIGH SCHOOL': 'HS',
                            'HS': 'HS',
                            'TRANSFER': 'TRANSFER',
                            'TR': 'TRANSFER'
                        })
                    )
                elif 'ClassLabel' in incoming.columns:
                    incoming['Type'] = incoming['ClassLabel'].fillna('').astype(str).apply(
                        lambda x: 'TRANSFER' if str(x).upper().startswith('TR(') else ('HS' if str(x).upper() == 'HS' else '')
                    )

            if 'Class' not in incoming.columns or incoming['Class'].isna().all():
                if 'ClassLabel' in incoming.columns:
                    def _map_incoming_class(val):
                        s = str(val).strip().upper()
                        if s == 'HS':
                            return 'FR'
                        if s.startswith('TR(') and s.endswith(')'):
                            return s[3:-1].strip()
                        return s
                    incoming['Class'] = incoming['ClassLabel'].apply(_map_incoming_class)

            if 'ProjectedRole' not in incoming.columns:
                incoming['ProjectedRole'] = pd.NA

            incoming['Year'] = pd.to_numeric(incoming['Year'], errors='coerce')
            incoming['Year'] = incoming['Year'].fillna(cur_year - 1).astype(int) + 1

            for col in ['Team', 'Player', 'Position', 'Type', 'Class', 'ProjectedRole', 'User', 'State', 'HT', 'WT']:
                if col in incoming.columns:
                    incoming[col] = incoming[col].fillna('').astype(str).str.strip()

            for col in ['Stars', 'RecruitSlot', 'NationalRank', 'PositionRank', 'StateRank', 'OverallClassRank']:
                if col in incoming.columns:
                    incoming[col] = pd.to_numeric(incoming[col], errors='coerce')

            # Infer projected role when blank
            def _infer_projected_role(row):
                existing = str(row.get('ProjectedRole', '')).strip()
                if existing:
                    return existing.title()

                stars = pd.to_numeric(row.get('Stars', pd.NA), errors='coerce')
                nat_rank = pd.to_numeric(row.get('NationalRank', pd.NA), errors='coerce')
                pos_rank = pd.to_numeric(row.get('PositionRank', pd.NA), errors='coerce')
                recruit_type = str(row.get('Type', '')).strip().upper()
                class_val = str(row.get('Class', '')).strip().upper()

                # Veteran transfer boost
                veteran_transfer = (
                    recruit_type == 'TRANSFER' and
                    class_val in {'SO', 'JR', 'SR', 'RS SO', 'RS JR', 'RS SR'}
                )

                # Starter rules
                if pd.notna(stars):
                    if stars >= 5:
                        return 'Starter'
                    if veteran_transfer and stars >= 4:
                        return 'Starter'
                    if pd.notna(nat_rank) and stars >= 4 and nat_rank <= 75:
                        return 'Starter'
                    if pd.notna(pos_rank) and stars >= 4 and pos_rank <= 8:
                        return 'Starter'
                    if veteran_transfer and stars >= 3 and pd.notna(pos_rank) and pos_rank <= 5:
                        return 'Starter'

                # Rotation rules
                if pd.notna(stars):
                    if stars >= 4:
                        return 'Rotation'
                    if veteran_transfer and stars >= 3:
                        return 'Rotation'
                    if pd.notna(nat_rank) and stars >= 3 and nat_rank <= 300:
                        return 'Rotation'
                    if pd.notna(pos_rank) and stars >= 3 and pos_rank <= 25:
                        return 'Rotation'

                return 'Depth'

            incoming['ProjectedRole'] = incoming.apply(_infer_projected_role, axis=1)

        # --- Normalize actual user draft results schema ---
        if not user_draft_results.empty:
            if 'CollegeTeam' not in user_draft_results.columns:
                user_draft_results['CollegeTeam'] = pd.NA
            if 'Player' not in user_draft_results.columns:
                user_draft_results['Player'] = pd.NA
            if 'Pos' not in user_draft_results.columns:
                user_draft_results['Pos'] = pd.NA
            if 'DraftRound' not in user_draft_results.columns:
                user_draft_results['DraftRound'] = pd.NA
            if 'OVR' not in user_draft_results.columns:
                user_draft_results['OVR'] = pd.NA
            if 'Class' not in user_draft_results.columns:
                user_draft_results['Class'] = pd.NA

            user_draft_results['DraftYear'] = pd.to_numeric(user_draft_results['DraftYear'], errors='coerce')
            user_draft_results['OVR'] = pd.to_numeric(user_draft_results['OVR'], errors='coerce')
            user_draft_results['DraftRound'] = pd.to_numeric(user_draft_results['DraftRound'], errors='coerce')

        # --- Build live OVR lookup from current roster ---
        try:
            rosters = pd.read_csv(roster_path)
            # Filter to current season if Season column exists
            if 'Season' in rosters.columns:
                rosters['Season'] = pd.to_numeric(rosters['Season'], errors='coerce')
                _avail = rosters['Season'].dropna().unique()
                _tgt = cur_year if cur_year in _avail else (int(max(_avail)) if len(_avail) else cur_year)
                rosters = rosters[rosters['Season'] == _tgt].copy()
            if 'Team' in rosters.columns and 'Name' in rosters.columns:
                rosters['LookupKey'] = rosters['Team'].astype(str) + "_" + rosters['Name'].astype(str)
                ovr_dict = dict(zip(rosters['LookupKey'], rosters['OVR'])) if 'OVR' in rosters.columns else {}
            else:
                ovr_dict = {}
        except Exception:
            ovr_dict = {}

        def inject_live_ovr(df):
            df = df.copy()
            if not df.empty and 'Team' in df.columns and 'Player' in df.columns and 'Year' in df.columns:
                if 'OVR' not in df.columns:
                    df['OVR'] = pd.NA

                curr_mask = df['Year'].astype(str) == str(cur_year)
                if curr_mask.any():
                    lookup_keys = (
                        df.loc[curr_mask, 'Team'].astype(str) + "_" +
                        df.loc[curr_mask, 'Player'].astype(str)
                    )
                    df.loc[curr_mask, 'OVR'] = lookup_keys.map(ovr_dict).fillna(df.loc[curr_mask, 'OVR'])

                df['OVR'] = pd.to_numeric(df['OVR'], errors='coerce')
            return df

        return (
            hs_df,
            tp_df,
            inject_live_ovr(nfl),
            inject_live_ovr(transfers),
            inject_live_ovr(graduates),
            incoming,
            user_draft_results
        )

    hs_df, tp_df, nfl_df, transfers_df, manual_graduates_df, incoming_df, user_draft_results_df = load_attrition_data(
        'cfb26_rosters_full.csv',
        current_yr
    )

    # --- 1B. Starter Inference Helpers ---
    def truthy_series(series):
        return (
            series.fillna(False)
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(['true', '1', 'yes', 'y'])
        )

    def build_team_starter_map(roster_df, team_name):
        starter_slots = {
            'QB': 1,
            'HB': 1,
            'FB': 1,
            'WR': 3,
            'TE': 1,
            'LT': 1,
            'LG': 1,
            'C': 1,
            'RG': 1,
            'RT': 1,
            'OL': 5,
            'LEDG': 1,
            'REDG': 1,
            'DE': 2,
            'DT': 2,
            'SAM': 1,
            'MIKE': 1,
            'WILL': 1,
            'LB': 3,
            'CB': 3,
            'FS': 1,
            'SS': 1,
            'S': 2,
            'K': 1,
            'P': 1
        }

        if roster_df.empty or 'Team' not in roster_df.columns:
            return set()

        team_roster = roster_df[roster_df['Team'] == team_name].copy()
        if team_roster.empty or 'Name' not in team_roster.columns or 'Pos' not in team_roster.columns:
            return set()

        team_roster['OVR'] = pd.to_numeric(team_roster.get('OVR', 0), errors='coerce').fillna(0)
        starter_names = set()

        for pos, slot_count in starter_slots.items():
            pos_df = team_roster[team_roster['Pos'].astype(str) == pos].sort_values(by='OVR', ascending=False)
            if not pos_df.empty:
                starter_names.update(pos_df.head(slot_count)['Name'].astype(str).tolist())

        return starter_names

    def infer_departure_starters(departures_df, roster_df, team_name):
        if departures_df.empty:
            return departures_df.assign(InferredStarter=False)

        df = departures_df.copy()
        starter_names = build_team_starter_map(roster_df, team_name)

        explicit_starter = pd.Series(False, index=df.index)
        if 'Was Starter' in df.columns:
            explicit_starter = truthy_series(df['Was Starter'])

        projected_starter = pd.Series(False, index=df.index)
        if 'ProjectedRole' in df.columns:
            projected_starter = (
                df['ProjectedRole']
                .fillna('')
                .astype(str)
                .str.strip()
                .str.lower()
                .eq('starter')
            )

        roster_inferred = pd.Series(False, index=df.index)
        if 'Player' in df.columns:
            roster_inferred = df['Player'].astype(str).isin(starter_names)

        df['InferredStarter'] = explicit_starter | projected_starter | roster_inferred
        return df

    # --- 1C. Auto-Pull Current Seniors from Roster ---
    def get_auto_seniors(roster_path, cur_year):
        try:
            rosters = pd.read_csv(roster_path).copy()

            if rosters.empty:
                return pd.DataFrame(columns=['Year', 'Team', 'Player', 'Position', 'OVR', 'Class', 'Was Starter'])

            if 'Team' not in rosters.columns or 'Name' not in rosters.columns:
                return pd.DataFrame(columns=['Year', 'Team', 'Player', 'Position', 'OVR', 'Class', 'Was Starter'])

            # Filter to current season if Season column exists (multi-season roster file)
            if 'Season' in rosters.columns:
                rosters['Season'] = pd.to_numeric(rosters['Season'], errors='coerce')
                _avail = rosters['Season'].dropna().unique()
                _tgt = cur_year if cur_year in _avail else (int(max(_avail)) if len(_avail) else cur_year)
                rosters = rosters[rosters['Season'] == _tgt].copy()

            rosters['Year'] = rosters['Year'].astype(str) if 'Year' in rosters.columns else ""
            rosters['Pos'] = rosters['Pos'].astype(str) if 'Pos' in rosters.columns else ""
            rosters['OVR'] = pd.to_numeric(rosters['OVR'], errors='coerce') if 'OVR' in rosters.columns else 0

            seniors = rosters[rosters['Year'].str.contains('SR', na=False)].copy()

            if seniors.empty:
                return pd.DataFrame(columns=['Year', 'Team', 'Player', 'Position', 'OVR', 'Class', 'Was Starter'])

            # Infer starters by position — loop avoids pandas groupby.apply version issues
            _starter_slots = {
                'QB':1,'HB':1,'FB':1,'WR':3,'TE':1,
                'LT':1,'LG':1,'C':1,'RG':1,'RT':1,
                'LEDG':1,'REDG':1,'DE':2,'DT':2,
                'SAM':1,'MIKE':1,'WILL':1,'LB':3,
                'CB':3,'FS':1,'SS':1,'S':2,'K':1,'P':1
            }
            rosters['Inferred Starter'] = False
            for _t in rosters['Team'].unique():
                _tmask = rosters['Team'] == _t
                for _pos, _n in _starter_slots.items():
                    _pidx = rosters[_tmask & (rosters['Pos'] == _pos)].sort_values('OVR', ascending=False).head(_n).index
                    rosters.loc[_pidx, 'Inferred Starter'] = True

            seniors = rosters[rosters['Year'].str.contains('SR', na=False)].reset_index(drop=True)

            if seniors.empty:
                return pd.DataFrame(columns=['Year', 'Team', 'Player', 'Position', 'OVR', 'Class', 'Was Starter'])

            auto_df = pd.DataFrame({
                'Year': cur_year,
                'Team': seniors['Team'].values,
                'Player': seniors['Name'].values,
                'Position': seniors['Pos'].values,
                'OVR': seniors['OVR'].values,
                'Class': seniors['Year'].values,
                'Was Starter': seniors['Inferred Starter'].fillna(False).astype(bool).values
            })

            return auto_df

        except Exception as e:
            st.warning(f"⚠️ get_auto_seniors error: {type(e).__name__}: {e}")
            return pd.DataFrame(columns=['Year', 'Team', 'Player', 'Position', 'OVR', 'Class', 'Was Starter'])

    auto_seniors_df = get_auto_seniors('cfb26_rosters_full.csv', current_yr)

    graduates_df = pd.concat([manual_graduates_df, auto_seniors_df], ignore_index=True).drop_duplicates(
        subset=['Year', 'Team', 'Player']
    )

    # available_years = outlook seasons. A year appears when its departure data exists
    # (i.e. data tagged as year-1 in the CSVs), plus always include current_yr+1 (next outlook)
    _departure_years = set()
    for df in [hs_df, tp_df, nfl_df, transfers_df, graduates_df, incoming_df]:
        if 'Year' in df.columns:
            _departure_years.update(df['Year'].dropna().unique())
    if not user_draft_results_df.empty and 'DraftYear' in user_draft_results_df.columns:
        _departure_years.update(user_draft_results_df['DraftYear'].dropna().astype(int).tolist())

    # Outlook year = departure year + 1
    _outlook_years = {int(y) + 1 for y in _departure_years if str(y).isdigit()}
    _outlook_years.add(current_yr + 1)  # always include next season
    available_years = sorted(_outlook_years, reverse=True)
    if not available_years:
        available_years = [current_yr + 1]

    try:
        full_roster_df = pd.read_csv('cfb26_rosters_full.csv')
        if 'Season' in full_roster_df.columns:
            full_roster_df['Season'] = pd.to_numeric(full_roster_df['Season'], errors='coerce')
            _avail = full_roster_df['Season'].dropna().unique()
            _tgt = current_yr if current_yr in _avail else (int(max(_avail)) if len(_avail) else current_yr)
            full_roster_df = full_roster_df[full_roster_df['Season'] == _tgt].copy()
    except Exception:
        full_roster_df = pd.DataFrame()

    # --- 2. Selectors ---
    col_sel1, col_sel2, col_sel3 = st.columns([1, 1, 1])
    with col_sel1:
        selected_team = st.selectbox("🏈 Select Team to View", user_teams_list, key="attrition_team_select")
    with col_sel2:
        _default_outlook = available_years[0]  # highest year = most recent data
        _default_yr_idx = 0
        selected_year = st.selectbox("🔮 Outlook Season", available_years, index=_default_yr_idx, key="attrition_year_select")
    with col_sel3:
        outlook_mode = st.selectbox(
            "⚙️ Outlook Mode",
            ["Conservative", "Aggressive"],
            index=1,
            help="Conservative = only confirmed departures. Aggressive = confirmed departures plus possible early leavers."
        )

    st.markdown("---")

    sel_color = TEAM_VISUALS.get(selected_team, {}).get("primary", "#FFFFFF")

    # --- 3. Filter Data by Selected Team & Year ---
    # selected_year = the OUTLOOK season (e.g. 2043)
    # departures/transfers/NFL = selected_year - 1 (what happened after last season)
    # incoming recruits = selected_year (who's arriving for this outlook season)
    # roster base = selected_year - 1 (the roster they're building from)
    departure_year = selected_year - 1   # e.g. 2042 departures when viewing 2043 outlook
    incoming_year  = selected_year       # e.g. 2043 incoming class

    def filter_team_year(df, t, y):
        if 'Team' in df.columns and 'Year' in df.columns:
            return df[(df['Team'] == t) & (df['Year'].astype(str) == str(y))].copy()
        return pd.DataFrame(columns=df.columns)

    team_hs       = filter_team_year(hs_df,      selected_team, departure_year)
    team_tp       = filter_team_year(tp_df,       selected_team, departure_year)
    team_incoming = filter_team_year(incoming_df, selected_team, incoming_year)

    if not team_incoming.empty and 'RecruitSlot' in team_incoming.columns:
        team_incoming = team_incoming.sort_values(by='RecruitSlot', ascending=True)

    # Prefer actual draft results from cfb_user_draft_results.csv
    team_actual_draft = pd.DataFrame()
    if not user_draft_results_df.empty:
        team_actual_draft = user_draft_results_df[
            (user_draft_results_df['DraftYear'] == int(departure_year)) &
            (user_draft_results_df['CollegeTeam'].astype(str).str.strip() == str(selected_team).strip())
        ].copy()

    if not team_actual_draft.empty:
        team_nfl = pd.DataFrame({
            'Year': team_actual_draft['DraftYear'],
            'Team': team_actual_draft['CollegeTeam'],
            'Player': team_actual_draft['Player'],
            'Position': team_actual_draft['Pos'],
            'OVR': team_actual_draft['OVR'],
            'Round': team_actual_draft['DraftRound'],
            'Left Early': False,
            'Class': team_actual_draft['Class'],
            'Was Starter': False
        })
    else:
        team_nfl = filter_team_year(nfl_df, selected_team, departure_year)

    team_transfers_all = filter_team_year(transfers_df, selected_team, departure_year)
    team_grads         = filter_team_year(graduates_df,  selected_team, departure_year)

    if not team_transfers_all.empty:
        if 'Position' not in team_transfers_all.columns and 'Pos' in team_transfers_all.columns:
            team_transfers_all['Position'] = team_transfers_all['Pos']

        if 'TransferStatus' not in team_transfers_all.columns:
            team_transfers_all['TransferStatus'] = ''

        team_transfers_all['TransferStatus'] = (
            team_transfers_all['TransferStatus']
            .fillna('')
            .astype(str)
            .str.strip()
            .str.title()
        )

        team_transfers = team_transfers_all[
            team_transfers_all['TransferStatus'].eq('Leaving')
        ].drop_duplicates(subset=["Year", "Team", "Player"]).copy()

        team_transfer_stayed = team_transfers_all[
            team_transfers_all['TransferStatus'].eq('Staying')
        ].copy()

        team_transfer_undecided = team_transfers_all[
            ~team_transfers_all['TransferStatus'].isin(['Leaving', 'Staying'])
        ].copy()
    else:
        team_transfers = pd.DataFrame(columns=transfers_df.columns)
        team_transfer_stayed = pd.DataFrame(columns=transfers_df.columns)
        team_transfer_undecided = pd.DataFrame(columns=transfers_df.columns)

    if not team_grads.empty:
        nfl_names = team_nfl['Player'].astype(str).tolist() if 'Player' in team_nfl.columns else []
        transfer_names = team_transfers['Player'].astype(str).tolist() if 'Player' in team_transfers.columns else []
        leave_names = set(nfl_names + transfer_names)
        team_grads = team_grads[~team_grads['Player'].astype(str).isin(leave_names)].copy()

    if not team_nfl.empty and 'OVR' in team_nfl.columns:
        team_nfl['OVR'] = pd.to_numeric(team_nfl['OVR'], errors='coerce')
        team_nfl = team_nfl.sort_values(by='OVR', ascending=False)

    if not team_transfers.empty and 'OVR' in team_transfers.columns:
        team_transfers['OVR'] = pd.to_numeric(team_transfers['OVR'], errors='coerce')
        team_transfers = team_transfers.sort_values(by='OVR', ascending=False)

    if not team_grads.empty and 'OVR' in team_grads.columns:
        team_grads['OVR'] = pd.to_numeric(team_grads['OVR'], errors='coerce')
        team_grads = team_grads.sort_values(by='OVR', ascending=False)

    # --- 4. Talent Balance Math ---
    confirmed_departures_df = pd.concat([
        team_nfl.assign(DepartureType='NFL') if not team_nfl.empty else pd.DataFrame(columns=list(team_nfl.columns) + ['DepartureType']),
        team_transfers.assign(DepartureType='Transfer') if not team_transfers.empty else pd.DataFrame(columns=list(team_transfers.columns) + ['DepartureType']),
        team_grads.assign(DepartureType='Graduate') if not team_grads.empty else pd.DataFrame(columns=list(team_grads.columns) + ['DepartureType'])
    ], ignore_index=True)

    if 'Position' in confirmed_departures_df.columns and 'Pos' not in confirmed_departures_df.columns:
        confirmed_departures_df['Pos'] = confirmed_departures_df['Position']

    confirmed_departures_df = infer_departure_starters(
        confirmed_departures_df, full_roster_df, selected_team
    )

    confirmed_departure_names = (
        confirmed_departures_df['Player'].dropna().astype(str).unique().tolist()
        if 'Player' in confirmed_departures_df.columns else []
    )
    total_departures = len(confirmed_departure_names)

    if not team_incoming.empty and 'Type' in team_incoming.columns:
        hs_individual = len(
            team_incoming[team_incoming['Type'].astype(str).str.upper() == 'HS']
        )
        tp_individual = len(
            team_incoming[team_incoming['Type'].astype(str).str.upper() == 'TRANSFER']
        )
    else:
        hs_individual = 0
        tp_individual = 0

    # Prefer individual incoming player rows when available
    if hs_individual > 0 or tp_individual > 0:
        hs_recruits = hs_individual
        transfers_in = tp_individual
    else:
        hs_recruits = (
            int(pd.to_numeric(team_hs['TotalCommits'], errors='coerce').fillna(0).sum())
            if 'TotalCommits' in team_hs.columns and not team_hs.empty else 0
        )
        transfers_in = (
            int(pd.to_numeric(team_tp['TotalCommits'], errors='coerce').fillna(0).sum())
            if 'TotalCommits' in team_tp.columns and not team_tp.empty else 0
        )

    net_talent = (hs_recruits + transfers_in) - total_departures
    net_str = f"+{net_talent}" if net_talent > 0 else str(net_talent)
    net_color = "#10B981" if net_talent > 0 else ("#EF4444" if net_talent < 0 else "#AAAAAA")

    confirmed_starter_losses = (
        int(confirmed_departures_df['InferredStarter'].sum())
        if 'InferredStarter' in confirmed_departures_df.columns else 0
    )

    impact_incoming_count = 0
    if not team_incoming.empty and 'ProjectedRole' in team_incoming.columns:
        impact_incoming_count = int(
            team_incoming['ProjectedRole']
            .fillna('')
            .astype(str)
            .str.lower()
            .isin(['starter', 'rotation'])
            .sum()
        )

    # --- 5. Live NFL Prospect Generation / Actual Draft Results ---
    @st.cache_data
    def get_nfl_prospects(roster_path):
        try:
            rosters = pd.read_csv(roster_path)

            # Filter to current season
            if 'Season' in rosters.columns:
                rosters['Season'] = pd.to_numeric(rosters['Season'], errors='coerce')
                _avail = rosters['Season'].dropna().unique()
                _tgt = current_yr if current_yr in _avail else (int(max(_avail)) if len(_avail) else current_yr)
                rosters = rosters[rosters['Season'] == _tgt].copy()

            if 'USER_TEAMS' in globals():
                rosters = rosters[rosters['Team'].isin(USER_TEAMS.values())]

            prospects = []
            for _, row in rosters.iterrows():
                year_val = str(row['Year']) if 'Year' in row else ''
                ovr = int(row['OVR']) if 'OVR' in row and pd.notna(row['OVR']) else 0

                is_senior = 'SR' in year_val
                is_eligible_early = ('JR' in year_val) or ('SO (RS)' in year_val)

                if is_senior:
                    if ovr >= 92:
                        projection = 'Day 1-3'
                    elif ovr >= 88:
                        projection = 'Day 3 / UDFA'
                    else:
                        projection = 'Undrafted'

                    prospects.append({
                        'Team': row['Team'],
                        'Player': row['Name'],
                        'Pos': row['Pos'],
                        'Year': row['Year'],
                        'OVR': ovr,
                        'Draft Projection': projection,
                        'Status': 'Graduating',
                        'Confirmed Risk': 'Confirmed Departure'
                    })

                elif is_eligible_early and ovr >= 90:
                    prospects.append({
                        'Team': row['Team'],
                        'Player': row['Name'],
                        'Pos': row['Pos'],
                        'Year': row['Year'],
                        'OVR': ovr,
                        'Draft Projection': 'Day 1-2' if ovr >= 94 else 'Day 2-3',
                        'Status': '🚨 Leaving Early Risk',
                        'Confirmed Risk': 'Possible Early Leaver'
                    })

            df = pd.DataFrame(prospects)
            if not df.empty:
                df = df.sort_values(by=['Team', 'OVR'], ascending=[True, False])
            return df
        except Exception:
            return pd.DataFrame(columns=['Team', 'Player', 'Pos', 'Year', 'OVR', 'Draft Projection', 'Status', 'Confirmed Risk'])

    predictions_df = get_nfl_prospects('cfb26_rosters_full.csv')
    team_preds = predictions_df[predictions_df['Team'] == selected_team].copy() if 'Team' in predictions_df.columns else pd.DataFrame(columns=predictions_df.columns)

    confirmed_current_nfl = team_nfl.copy() if team_nfl is not None else pd.DataFrame()
    confirmed_current_names = set(confirmed_current_nfl['Player'].astype(str).tolist()) if 'Player' in confirmed_current_nfl.columns else set()

    possible_early_df = pd.DataFrame(columns=['Team', 'Player', 'Pos', 'Year', 'OVR', 'Draft Projection', 'Status', 'Confirmed Risk'])
    confirmed_live_df = pd.DataFrame(columns=[
        'Team', 'Player', 'Pos', 'Year', 'OVR',
        'Draft Projection', 'Status', 'Confirmed Risk'
    ])

    grad_confirmed_df = pd.DataFrame(columns=confirmed_live_df.columns)

    if not team_preds.empty:
        grad_confirmed_df = team_preds[team_preds['Status'] == 'Graduating'].copy()

        if not grad_confirmed_df.empty:
            if 'Draft Projection' not in grad_confirmed_df.columns:
                grad_confirmed_df['Draft Projection'] = "—"
            grad_confirmed_df['Confirmed Risk'] = 'Confirmed Departure'

    # If actual draft results exist for this team/year, add those as confirmed too
    if not team_actual_draft.empty:
        drafted_confirmed_df = pd.DataFrame({
            'Team': team_actual_draft['CollegeTeam'],
            'Player': team_actual_draft['Player'],
            'Pos': team_actual_draft['Pos'],
            'Year': team_actual_draft['Class'],
            'OVR': team_actual_draft['OVR'],
            'Draft Projection': team_actual_draft['DraftRound'].apply(
                lambda x: f"Round {int(x)}" if pd.notna(x) else "Drafted"
            ),
            'Status': 'Drafted',
            'Confirmed Risk': 'Confirmed Departure'
        })

        confirmed_live_df = pd.concat(
            [drafted_confirmed_df, grad_confirmed_df],
            ignore_index=True,
            sort=False
        ).drop_duplicates(subset=['Player'], keep='first').copy()

        # Once actual draft results exist, only keep projected early-leavers
        # who are not already in the actual drafted list or graduating list
        if not team_preds.empty:
            confirmed_names_for_filter = set()
            if 'Player' in confirmed_live_df.columns:
                confirmed_names_for_filter = set(
                    confirmed_live_df['Player'].astype(str).str.strip().tolist()
                )

            possible_early_df = team_preds[team_preds['Status'] == '🚨 Leaving Early Risk'].copy()
            if 'Player' in possible_early_df.columns:
                possible_early_df = possible_early_df[
                    ~possible_early_df['Player'].astype(str).str.strip().isin(confirmed_names_for_filter)
                ].copy()

    else:
        confirmed_live_df = grad_confirmed_df.copy()

        if not team_preds.empty:
            confirmed_names_for_filter = set()
            if 'Player' in confirmed_live_df.columns:
                confirmed_names_for_filter = set(
                    confirmed_live_df['Player'].astype(str).str.strip().tolist()
                )

            possible_early_df = team_preds[team_preds['Status'] == '🚨 Leaving Early Risk'].copy()

            if 'Player' in possible_early_df.columns:
                possible_early_df = possible_early_df[
                    ~possible_early_df['Player'].astype(str).str.strip().isin(confirmed_names_for_filter)
                ].copy()

    # --- 6. Next Season Outlook & Dynamic Championship Odds ---
    try:
        USER_TEAM_COLLISION_GROUPS = [
            {"Florida State", "Florida", "Bowling Green"},
            {"Texas Tech", "San Jose State", "USF"}
        ]

        current_roster = pd.read_csv('cfb26_rosters_full.csv')
        if 'Season' in current_roster.columns:
            current_roster['Season'] = pd.to_numeric(current_roster['Season'], errors='coerce')
            _avail = current_roster['Season'].dropna().unique()
            _tgt = departure_year if departure_year in _avail else (int(max(_avail)) if len(_avail) else departure_year)
            current_roster = current_roster[current_roster['Season'] == _tgt].copy()
        team_roster = current_roster[current_roster['Team'] == selected_team].copy()

        confirmed_leaving_names = set(confirmed_departure_names)

        possible_early_names = set()
        if not possible_early_df.empty and 'Player' in possible_early_df.columns:
            possible_early_names = set(possible_early_df['Player'].astype(str).tolist())

        if outlook_mode == "Aggressive":
            leaving_names = confirmed_leaving_names.union(possible_early_names)
        else:
            leaving_names = confirmed_leaving_names

        returning_players = team_roster[~team_roster['Name'].astype(str).isin(leaving_names)].copy()

        if not returning_players.empty and 'OVR' in returning_players.columns:
            prog_weights = [0.40, 0.35, 0.15, 0.08, 0.02]
            progression_bumps = np.random.choice([3, 4, 5, 6, 7], size=len(returning_players), p=prog_weights)
            returning_players['Prog_OVR'] = returning_players['OVR'] + progression_bumps
            base_ovr = (
                returning_players.nlargest(25, 'Prog_OVR')['Prog_OVR'].mean()
                if len(returning_players) >= 20
                else returning_players['Prog_OVR'].mean()
            )
        else:
            base_ovr = 80

        inc_5_stars = (
            team_hs['FiveStar'].sum() if 'FiveStar' in team_hs.columns and not team_hs.empty else 0
        ) + (
            team_tp['FiveStar'].sum() if 'FiveStar' in team_tp.columns and not team_tp.empty else 0
        )

        inc_4_stars = (
            team_hs['FourStar'].sum() if 'FourStar' in team_hs.columns and not team_hs.empty else 0
        ) + (
            team_tp['FourStar'].sum() if 'FourStar' in team_tp.columns and not team_tp.empty else 0
        )

        incoming_role_bonus = 0.0
        if not team_incoming.empty and 'ProjectedRole' in team_incoming.columns:
            starter_bonus = team_incoming['ProjectedRole'].fillna('').astype(str).str.lower().eq('starter').sum() * 0.40
            rotation_bonus = team_incoming['ProjectedRole'].fillna('').astype(str).str.lower().eq('rotation').sum() * 0.15
            incoming_role_bonus = starter_bonus + rotation_bonus

        veteran_transfer_bonus = 0.0
        blue_chip_ratio = 0.0
        veteran_portal_count = 0
        blue_chip_veteran_count = 0

        if not team_incoming.empty:
            incoming_tmp = team_incoming.copy()

            if 'Type' in incoming_tmp.columns:
                incoming_tmp = incoming_tmp[incoming_tmp['Type'].astype(str).str.upper() == 'TRANSFER']

            if not incoming_tmp.empty and 'Class' in incoming_tmp.columns:
                incoming_tmp['Class'] = incoming_tmp['Class'].fillna('').astype(str).str.upper().str.strip()

                veteran_transfers = incoming_tmp[
                    incoming_tmp['Class'].isin(['SO', 'SO (RS)', 'RS SO', 'JR', 'SR'])
                ].copy()

                if not veteran_transfers.empty and 'ProjectedRole' in veteran_transfers.columns:
                    veteran_transfers['ProjectedRole'] = (
                        veteran_transfers['ProjectedRole']
                        .fillna('')
                        .astype(str)
                        .str.strip()
                        .str.lower()
                    )

                    veteran_transfers = veteran_transfers[
                        veteran_transfers['ProjectedRole'].isin(['starter', 'rotation'])
                    ].copy()

                veteran_portal_count = len(veteran_transfers)

                if veteran_portal_count > 0 and 'Stars' in veteran_transfers.columns:
                    veteran_transfers['Stars'] = pd.to_numeric(veteran_transfers['Stars'], errors='coerce').fillna(0)
                    blue_chip_veteran_count = int(veteran_transfers['Stars'].isin([4, 5]).sum())
                    blue_chip_ratio = blue_chip_veteran_count / veteran_portal_count

                    avg_star = veteran_transfers['Stars'].mean()

                    veteran_transfer_bonus = blue_chip_ratio * 1.5

                    if avg_star >= 4.5:
                        veteran_transfer_bonus += 0.35
                    elif avg_star >= 4.0:
                        veteran_transfer_bonus += 0.15

        talent_boost = (inc_5_stars * 1.0) + (inc_4_stars * 0.4) + incoming_role_bonus + veteran_transfer_bonus
        projected_ovr = base_ovr + talent_boost

        qbs = returning_players[returning_players['Pos'] == 'QB'] if 'Pos' in returning_players.columns else pd.DataFrame()
        ret_qb_name = "Unknown QB"
        ret_qb_ovr = 75

        if not qbs.empty and 'Prog_OVR' in qbs.columns and 'Name' in qbs.columns:
            best_ret_qb_row = qbs.nlargest(1, 'Prog_OVR').iloc[0]
            ret_qb_name = best_ret_qb_row['Name']
            ret_qb_ovr = best_ret_qb_row['Prog_OVR']

        inc_qbs = (
            team_incoming[team_incoming['Position'] == 'QB']
            if not team_incoming.empty and 'Position' in team_incoming.columns
            else pd.DataFrame()
        )
        inc_qb_name = ""
        inc_qb_stars = 0
        inc_qb_ovr = 0

        if not inc_qbs.empty and 'Stars' in inc_qbs.columns:
            best_inc_qb = inc_qbs.sort_values(by='Stars', ascending=False).iloc[0]
            inc_qb_name = best_inc_qb['Player'] if 'Player' in best_inc_qb.index else "Incoming Recruit"
            inc_qb_stars = int(best_inc_qb['Stars']) if pd.notna(best_inc_qb['Stars']) else 0

            if inc_qb_stars == 5:
                inc_qb_ovr = 82
            elif inc_qb_stars == 4:
                inc_qb_ovr = 78
            elif inc_qb_stars == 3:
                inc_qb_ovr = 73
            else:
                inc_qb_ovr = 68

        if inc_qb_ovr > ret_qb_ovr:
            best_qb_desc = f"Incoming Recruit {inc_qb_name} ({inc_qb_stars}⭐)"
            starting_qb_ovr = inc_qb_ovr
        else:
            best_qb_desc = f"{ret_qb_name} ({int(ret_qb_ovr)} OVR)"
            starting_qb_ovr = ret_qb_ovr

        if starting_qb_ovr >= 96:
            qb_mod = 4.0
        elif starting_qb_ovr >= 94:
            qb_mod = 2.5
        elif starting_qb_ovr >= 92:
            qb_mod = 1.0
        else:
            qb_mod = 0.0

        current_starter_names = build_team_starter_map(current_roster, selected_team)

        confirmed_starter_names = set()
        if not confirmed_departures_df.empty and 'InferredStarter' in confirmed_departures_df.columns:
            confirmed_starter_names = set(
                confirmed_departures_df.loc[
                    confirmed_departures_df['InferredStarter'] == True, 'Player'
                ].astype(str).tolist()
            )

        possible_early_starter_names = set()
        if not possible_early_df.empty and 'Player' in possible_early_df.columns:
            possible_early_starter_names = set(
                [p for p in possible_early_df['Player'].astype(str).tolist() if p in current_starter_names]
            )

        if outlook_mode == "Aggressive":
            starters_lost_names = confirmed_starter_names.union(possible_early_starter_names)
        else:
            starters_lost_names = confirmed_starter_names

        returning_starter_names = [name for name in current_starter_names if str(name) not in starters_lost_names]
        est_returning_starters = max(0, min(22, len(returning_starter_names)))
        starters_lost_for_mode = max(0, 22 - est_returning_starters)

        starter_mod = (est_returning_starters - 13) * 0.35

        starter_exp_mod = 0.0
        young_starter_count = 0
        senior_starter_count = 0

        starter_rows = pd.DataFrame()
        if not team_roster.empty and 'Name' in team_roster.columns and 'Year' in team_roster.columns:
            starter_rows = team_roster[team_roster['Name'].astype(str).isin(returning_starter_names)].copy()
            starter_rows['Year'] = starter_rows['Year'].astype(str)

            fr_count = starter_rows['Year'].str.fullmatch(r'FR', case=False, na=False).sum()
            rs_fr_count = starter_rows['Year'].str.contains(r'FR \(RS\)|RS FR', case=False, na=False).sum()
            so_count = starter_rows['Year'].str.fullmatch(r'SO', case=False, na=False).sum()
            sr_count = starter_rows['Year'].str.contains(r'^SR$|SR ', case=False, na=False).sum()

            young_starter_count = int(fr_count + rs_fr_count + so_count)
            senior_starter_count = int(sr_count)

            starter_exp_mod -= young_starter_count * 0.8
            starter_exp_mod += senior_starter_count * 0.25

        speed_mod = 0.0
        skill_speed_avg = None
        db_speed_avg = None

        if not starter_rows.empty:
            speed_col = None
            for col in ['SPD', 'Speed', 'Spd']:
                if col in starter_rows.columns:
                    speed_col = col
                    break

            if speed_col is not None:
                starter_rows[speed_col] = pd.to_numeric(starter_rows[speed_col], errors='coerce')

                skill_rows = starter_rows[starter_rows['Pos'].isin(['HB', 'WR'])].copy()
                if not skill_rows.empty and skill_rows[speed_col].notna().any():
                    skill_speed_avg = float(skill_rows[speed_col].dropna().mean())
                    if skill_speed_avg < 90:
                        speed_mod -= (90 - skill_speed_avg) * 0.35

                db_rows = starter_rows[starter_rows['Pos'].isin(['CB', 'FS', 'SS', 'S'])].copy()
                if not db_rows.empty and db_rows[speed_col].notna().any():
                    db_speed_avg = float(db_rows[speed_col].dropna().mean())
                    if db_speed_avg < 90:
                        speed_mod -= (90 - db_speed_avg) * 0.35

        final_power_rating = projected_ovr + qb_mod + starter_mod + starter_exp_mod + speed_mod + np.random.uniform(-1.0, 1.0)

        cfp_prob_raw = 100 / (1 + np.exp(-0.24 * (final_power_rating - 91.0)))
        title_prob_raw = 100 / (1 + np.exp(-0.13 * (final_power_rating - 105.0)))

        collision_group_size = 1
        for group in USER_TEAM_COLLISION_GROUPS:
            if selected_team in group:
                collision_group_size = len(group)
                break

        if collision_group_size >= 2:
            cfp_prob_raw *= (0.70 ** (collision_group_size - 1))
            title_prob_raw *= (0.35 ** (collision_group_size - 1))

        def prob_to_ratio_odds(prob):
            if prob >= 50:
                return "Even"
            elif prob >= 0.1:
                implied_ratio = max(1, round((100 / prob) - 1))
                return f"{implied_ratio}:1"
            else:
                return "1000:1+"

        cfp_odds = prob_to_ratio_odds(cfp_prob_raw)
        title_odds = prob_to_ratio_odds(title_prob_raw)

        if final_power_rating >= 92.5:
            tier_title = "🏆 National Title Contender"
            tier_color = "#FACC15"
            tier_desc = f"With {est_returning_starters} returning starters and elite talent arriving, this roster is primed for a deep playoff run. Handing the keys to {best_qb_desc} at QB gives them a very real chance at immortality."
        elif final_power_rating >= 88.0:
            tier_title = "⭐ Playoff Threat"
            tier_color = "#38BDF8"
            tier_desc = f"A dangerous roster returning {est_returning_starters} starters. If {best_qb_desc} can command the offense efficiently and a few breaks go their way, they will easily steal a playoff spot."
        elif final_power_rating >= 83.5:
            tier_title = "🏈 Bowl Bound"
            tier_color = "#A7F3D0"
            tier_desc = f"A solid team returning {est_returning_starters} starters, but evident talent gaps keep them out of the elite tier. {best_qb_desc} will need a Cinderella season to reach the CFP."
        else:
            tier_title = "🛠️ Rebuilding Year"
            tier_color = "#9CA3AF"
            tier_desc = f"High roster turnover (only {est_returning_starters} returning starters) and a lack of elite depth points toward a challenging season. Developing {best_qb_desc} and building for the future is the priority."

        next_yr = selected_year
        mode_color = "#F59E0B" if outlook_mode == "Aggressive" else "#10B981"

        skill_speed_text = f"{skill_speed_avg:.1f}" if skill_speed_avg is not None else "N/A"
        db_speed_text = f"{db_speed_avg:.1f}" if db_speed_avg is not None else "N/A"
        blue_chip_ratio_text = f"{blue_chip_ratio:.0%}" if veteran_portal_count > 0 else "N/A"

        outlook_logo_html = get_attrition_logo(selected_team, width=55, margin="0 15px 0 0")

        st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.02) 100%); padding: 20px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); border-top: 5px solid {sel_color}; box-shadow: 0 8px 16px rgba(0,0,0,0.4); margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 12px; margin-bottom: 15px;">
                    <div style="display: flex; align-items: center;">
                        {outlook_logo_html}
                        <div>
                            <h3 style="margin: 0; padding: 0; font-size: 1.6rem; text-align: left !important; color: #FFFFFF;">🔮 {next_yr} Season Outlook</h3>
                            <p style="margin: 4px 0 0 0; font-size: 0.95rem; color: #BBBBBB; text-align: left !important;">
                                Mode: <span style="color:{mode_color}; font-weight:bold;">{outlook_mode}</span> |
                                Returning starters: {est_returning_starters} |
                                Starters lost: {starters_lost_for_mode} |
                                Young starters: {young_starter_count} |
                                Senior starters: {senior_starter_count}
                            </p>
                            <p style="margin: 4px 0 0 0; font-size: 0.90rem; color: #9CA3AF; text-align: left !important;">
                                Skill starter speed avg: {skill_speed_text} |
                                DB starter speed avg: {db_speed_text}
                            </p>
                            <p style="margin: 4px 0 0 0; font-size: 0.90rem; color: #9CA3AF; text-align: left !important;">
                                Veteran portal blue-chip rate: {blue_chip_ratio_text} |
                                Veteran portal bonus: {veteran_transfer_bonus:.2f}
                            </p>
                        </div>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; gap: 20px;">
                    <div style="flex: 2;">
                        <div style="font-size: 1.8rem; font-weight: bold; color: {tier_color}; margin-bottom: 8px;">{tier_title}</div>
                        <div style="font-size: 1rem; color: #DDDDDD; line-height: 1.5;">{tier_desc}</div>
                    </div>
                    <div style="flex: 1; display: flex; flex-direction: column; gap: 10px;">
                        <div style="background-color: rgba(0,0,0,0.3); padding: 12px; border-radius: 8px; text-align: center;">
                            <div style="font-size: 0.8rem; text-transform: uppercase; color: #AAAAAA; letter-spacing: 1px;">Make CFP Odds</div>
                            <div style="font-size: 1.8rem; font-weight: bold; color: #FFFFFF;">{cfp_odds}</div>
                        </div>
                        <div style="background-color: rgba(0,0,0,0.3); padding: 12px; border-radius: 8px; text-align: center;">
                            <div style="font-size: 0.8rem; text-transform: uppercase; color: #AAAAAA; letter-spacing: 1px;">National Title Odds</div>
                            <div style="font-size: 1.8rem; font-weight: bold; color: {tier_color};">{title_odds}</div>
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    except Exception:
        pass

    # --- 7. Summary Cards ---
    def get_stat_card(label, value, color, delta=None, delta_color=None):
        delta_html = f"<div style='font-size: 0.9rem; color: {delta_color}; margin-top: 5px; font-weight: bold;'>{delta}</div>" if delta else ""
        return f"""
        <div style="background-color: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 8px; border-top: 4px solid {color}; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); height: 100%;">
            <div style="font-size: 0.85rem; color: #BBBBBB; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">{label}</div>
            <div style="font-size: 2.2rem; font-weight: bold; color: #FFFFFF; line-height: 1;">{value}</div>
            {delta_html}
        </div>
        """

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.markdown(get_stat_card(f"{selected_year} HS Recruits", str(hs_recruits), sel_color, delta=f"{hs_individual} named", delta_color="#9CA3AF"), unsafe_allow_html=True)
    with col_m2:
        st.markdown(get_stat_card(f"{selected_year} Transfers In", str(transfers_in), sel_color, delta=f"{tp_individual} named", delta_color="#9CA3AF"), unsafe_allow_html=True)
    with col_m3:
        st.markdown(get_stat_card(f"{selected_year} Confirmed Departures", str(total_departures), sel_color, delta=f"{confirmed_starter_losses} starters lost", delta_color="#F59E0B"), unsafe_allow_html=True)
    with col_m4:
        st.markdown(get_stat_card("Net Talent Change", str(net_talent), sel_color, delta=net_str, delta_color=net_color), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 8. Actual Departures Split View ---
    def get_mini_card(title, color):
        return f"""
        <div style="background-color: rgba(255, 255, 255, 0.05); padding: 12px; border-radius: 8px; border-top: 4px solid {color}; margin-bottom: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
            <h4 style="margin: 0; padding: 0; font-size: 1.2rem; text-align: center !important; color: #FFFFFF;">{title}</h4>
        </div>
        """

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(get_mini_card("🏈 NFL Draft", sel_color), unsafe_allow_html=True)
        with st.expander(f"View {len(team_nfl)} Players", expanded=False):
            if not team_nfl.empty:
                team_nfl_display = infer_departure_starters(team_nfl, full_roster_df, selected_team)

                edited_nfl = st.data_editor(
                    team_nfl_display.drop(columns=['Team', 'Year'], errors='ignore'),
                    column_config={
                        "Left Early": st.column_config.CheckboxColumn("Left Early"),
                        "Was Starter": st.column_config.CheckboxColumn("Was Starter"),
                        "InferredStarter": st.column_config.CheckboxColumn("Starter Lost"),
                        "OVR": st.column_config.NumberColumn(format="%d ⭐")
                    },
                    hide_index=True,
                    use_container_width=True,
                    key=f"nfl_editor_{selected_team}_{selected_year}"
                )

                left_early_count = int(edited_nfl['Left Early'].fillna(False).astype(bool).sum()) if 'Left Early' in edited_nfl.columns else 0
                if left_early_count > 0:
                    st.caption(f"🚨 Players officially left early: **{left_early_count}**")
            else:
                st.caption("No NFL departures logged.")

    with col2:
        st.markdown(get_mini_card("🎒 Transfers Out", sel_color), unsafe_allow_html=True)
        with st.expander(f"View {len(team_transfers)} Players", expanded=False):
            if not team_transfers.empty:
                team_transfers_display = infer_departure_starters(team_transfers, full_roster_df, selected_team)
                st.dataframe(
                    team_transfers_display.drop(columns=['Team', 'Year'], errors='ignore'),
                    column_config={
                        "Was Starter": st.column_config.CheckboxColumn("Was Starter"),
                        "InferredStarter": st.column_config.CheckboxColumn("Starter Lost"),
                        "OVR": st.column_config.NumberColumn(format="%d ⭐")
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.caption("No transfers logged.")

    with col3:
        st.markdown(get_mini_card("🎓 Graduates", sel_color), unsafe_allow_html=True)
        with st.expander(f"View {len(team_grads)} Players", expanded=False):
            if not team_grads.empty:
                team_grads_display = infer_departure_starters(team_grads, full_roster_df, selected_team)
                st.dataframe(
                    team_grads_display.drop(columns=['Team', 'Year'], errors='ignore'),
                    column_config={
                        "Was Starter": st.column_config.CheckboxColumn("Was Starter"),
                        "InferredStarter": st.column_config.CheckboxColumn("Starter Lost"),
                        "OVR": st.column_config.NumberColumn(format="%d ⭐")
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.caption("No graduates found.")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 9. Incoming Talent Detail ---
    st.markdown(get_mini_card("📥 Incoming Individual Talent", sel_color), unsafe_allow_html=True)
    with st.expander(f"View {len(team_incoming)} Incoming Players", expanded=False):
        if not team_incoming.empty:
            st.dataframe(
                team_incoming.drop(columns=['Team', 'Year'], errors='ignore'),
                hide_index=True,
                use_container_width=True
            )
            if 'ProjectedRole' in team_incoming.columns:
                starter_proj = int(team_incoming['ProjectedRole'].fillna('').astype(str).str.lower().eq('starter').sum())
                rotation_proj = int(team_incoming['ProjectedRole'].fillna('').astype(str).str.lower().eq('rotation').sum())
                st.caption(f"Projected impact newcomers: **{starter_proj} starters**, **{rotation_proj} rotation players**")
        else:
            st.caption("No incoming individual players logged.")

    st.markdown("<br><br>", unsafe_allow_html=True)

    # --- 10. In-Season Predictions Header ---
    sel_logo_html = get_attrition_logo(selected_team, width=65, margin="0")

    st.markdown(f"""
        <div style="background-color: rgba(255, 255, 255, 0.05); padding: 15px 20px; border-radius: 8px; border-left: 6px solid {sel_color}; display: flex; align-items: center; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
            <div style="margin-right: 20px; display: flex; align-items: center;">
                {sel_logo_html}
            </div>
            <div>
                <h3 style="margin: 0; padding: 0; font-size: 1.5rem; text-align: left !important; color: #FFFFFF;">Current {selected_team} Flight Risk</h3>
                <p style="margin: 5px 0 0 0; font-size: 0.9rem; color: #BBBBBB; text-align: left !important;">
                    Confirmed departures are separated from possible early leavers so the outlook can be viewed in Aggressive or Conservative mode.
                </p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(get_mini_card("Current Flight Risk Breakdown", sel_color), unsafe_allow_html=True)

    with st.expander(f"✅ Confirmed Departures ({len(confirmed_live_df)})", expanded=False):
        if not confirmed_live_df.empty:
            st.dataframe(
                confirmed_live_df.drop(columns=['Team'], errors='ignore'),
                hide_index=True,
                use_container_width=True,
                column_config={"OVR": st.column_config.NumberColumn(format="%d ⭐")}
            )
        else:
            st.info("No confirmed graduating NFL-related departures found.")

    with st.expander(f"⚠️ Possible Early Leavers ({len(possible_early_df)})", expanded=False):
        if not possible_early_df.empty:
            st.dataframe(
                possible_early_df.drop(columns=['Team'], errors='ignore'),
                hide_index=True,
                use_container_width=True,
                column_config={"OVR": st.column_config.NumberColumn(format="%d ⭐")}
            )
        else:
            st.info("No underclassmen currently flagged as possible early leavers.")

    # --- ROSTER MATCHUP ---
    with tabs[8]:
        render_roster_matchup_tab()

    # --- SIDEBAR CONTENT ---
    with st.sidebar:
        st.markdown("---")
        st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.02) 100%); padding: 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); border-top: 4px solid #10B981; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 20px;">
                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                    <div style="font-size: 1.5rem; margin-right: 10px;">📱</div>
                    <h4 style="margin: 0; color: #FFFFFF; font-size: 1.1rem;">Install Mobile App</h4>
                </div>
                <p style="font-size: 0.85rem; color: #BBBBBB; margin: 0 0 12px 0; line-height: 1.4;">Add this dynasty hub directly to your phone's home screen for fullscreen, one-tap access.</p>
                <div style="background-color: rgba(239, 68, 68, 0.15); border-left: 3px solid #EF4444; padding: 8px; margin-bottom: 12px; font-size: 0.8rem; color: #DDDDDD;">
                    <b>Note:</b> If opening from Discord or Messages, tap the menu and select <b>"Open in Safari/Chrome"</b> first!
                </div>
                <div style="margin-bottom: 10px;">
                    <strong style="color: #FFFFFF; font-size: 0.85rem;">🍎 iOS (Safari)</strong>
                    <ol style="font-size: 0.8rem; color: #DDDDDD; padding-left: 20px; margin: 3px 0 0 0;">
                        <li>Tap the <b>Share</b> icon at the bottom.</li>
                        <li>Scroll down and tap <b>Add to Home Screen</b>.</li>
                    </ol>
                </div>
                <div>
                    <strong style="color: #FFFFFF; font-size: 0.85rem;">🤖 Android (Chrome)</strong>
                    <ol style="font-size: 0.8rem; color: #DDDDDD; padding-left: 20px; margin: 3px 0 0 0;">
                        <li>Tap the <b>Three Dots</b> menu at the top right.</li>
                        <li>Tap <b>Open Streamlit</b>, <b>Install App</b>, or <b>Add to Home Screen</b>.</li>
                    </ol>
                </div>
            </div>
        """, unsafe_allow_html=True)

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.markdown("---")

    st.sidebar.markdown(
        "<p style='font-size:11px;font-weight:500;color:#64748b;text-transform:uppercase;"
        "letter-spacing:.05em;margin-bottom:6px;'>Commissioner Tools</p>",
        unsafe_allow_html=True,
    )

    if st.sidebar.button("📊 Sync Derived Stats", use_container_width=True,
                         help="Auto-updates CFP wins/losses, natty counts & appearances in UserDraftPicks.csv and coach_records.csv"):
        with st.sidebar:
            with st.spinner("Syncing…"):
                _ok, _msgs = sync_derived_stats()
            for _m in _msgs:
                if _m.startswith("✅"):
                    st.success(_m, icon=None)
                elif _m.startswith("⚠️"):
                    st.warning(_m, icon=None)
                else:
                    st.error(_m, icon=None)
            if _ok:
                st.cache_data.clear()