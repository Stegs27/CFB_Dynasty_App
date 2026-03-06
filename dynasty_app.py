import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- PAGE SETUP ---
st.set_page_config(page_title="Island Dynasty HQ", layout="wide", page_icon="🏈")
st.title("🏈 Island Dynasty: The Executive Suite")


def smart_col(df, target_names):
    for target in target_names:
        for col in df.columns:
            if col.strip().lower() == target.lower():
                return col
    return None


def clean_rank_value(val):
    if pd.isna(val):
        return np.nan
    s = str(val).strip().replace('*', '')
    try:
        return float(s)
    except Exception:
        return np.nan


def get_recent_recruiting_score(rec_df, user, team=None, current_year=2041, lookback=3):
    """
    Converts recent recruiting ranks into a 0-100 style score.
    Lower class rank = better score.
    Uses the latest non-null classes from the matching user/team row.
    """
    rec_work = rec_df.copy()
    rec_work['USER_CLEAN'] = rec_work['USER'].astype(str).str.strip().str.title()
    rec_work['TEAM_CLEAN'] = rec_work['Teams'].astype(str).str.strip().str.title()

    user_clean = str(user).strip().title()
    team_clean = str(team).strip().title() if team is not None else None

    row = pd.DataFrame()
    if team_clean:
        row = rec_work[(rec_work['USER_CLEAN'] == user_clean) & (rec_work['TEAM_CLEAN'] == team_clean)]

    if row.empty:
        row = rec_work[rec_work['USER_CLEAN'] == user_clean]

    if row.empty:
        return 50.0

    # Prefer the first exact current-team match; otherwise most recent row for the user.
    row = row.iloc[0]

    year_cols = sorted([c for c in rec_df.columns if str(c).isdigit() and int(c) <= current_year], key=lambda x: int(x), reverse=True)
    vals = []
    for col in year_cols:
        v = clean_rank_value(row[col])
        if not pd.isna(v):
            vals.append(v)
        if len(vals) >= lookback:
            break

    if not vals:
        return 50.0

    avg_rank = float(np.mean(vals))
    # Rank 1 -> 100, Rank 100 -> 1
    score = max(1, min(100, 101 - avg_rank))
    return round(score, 1)


def get_user_win_pct(user, draft_df):
    row = draft_df[draft_df['USER'].astype(str).str.strip().str.title() == str(user).strip().title()]
    if row.empty:
        return 0.500

    wins = pd.to_numeric(row.iloc[0]['Career Wins'], errors='coerce')
    losses = pd.to_numeric(row.iloc[0]['Career Losses'], errors='coerce')

    if pd.isna(wins) or pd.isna(losses) or (wins + losses) == 0:
        return 0.500

    return float(wins / (wins + losses))


@st.cache_data
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

        # NORMALIZE KEY TEXT FIELDS
        draft['USER'] = draft['USER'].astype(str).str.strip().str.title()
        rec['USER'] = rec['USER'].astype(str).str.strip().str.title()
        rec['Teams'] = rec['Teams'].astype(str).str.strip().str.title()
        ratings['USER'] = ratings['USER'].astype(str).str.strip().str.title()
        ratings['TEAM'] = ratings['TEAM'].astype(str).str.strip().str.title()
        champs['user'] = champs['user'].astype(str).str.strip().str.title()

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
        c_yr_key = smart_col(coty, ['Year', 'YEAR'])
        c_coach_key = smart_col(coty, ['Coach', 'Winner', 'Name'])
        c_school_key = smart_col(coty, ['School', 'Team', 'University'])

        # CLEAN SCORES
        scores['V_User_Final'] = scores[v_user_key].astype(str).str.strip().str.title()
        scores['H_User_Final'] = scores[h_user_key].astype(str).str.strip().str.title()
        scores['V_Pts'] = pd.to_numeric(scores[v_score_key], errors='coerce')
        scores['H_Pts'] = pd.to_numeric(scores[h_score_key], errors='coerce')
        scores = scores.dropna(subset=['V_Pts', 'H_Pts'])
        scores['Margin'] = (scores['H_Pts'] - scores['V_Pts']).abs()
        scores['Winner'] = np.where(scores['H_Pts'] > scores['V_Pts'], scores['H_User_Final'], scores['V_User_Final'])
        scores['Loser'] = np.where(scores['H_Pts'] > scores['V_Pts'], scores['V_User_Final'], scores['H_User_Final'])

        all_users = sorted([
            u for u in pd.concat([scores['V_User_Final'], scores['H_User_Final']]).unique()
            if u.upper() != 'CPU' and u != 'Nan'
        ])
        years_available = sorted(scores[yr_key].dropna().unique(), reverse=True)

        # MASTER STATS ENGINE
        stats_list, h2h_rows, h2h_numeric = [], [], []
        natty_counts = champs[champs[champ_user_key].str.upper() != 'CPU'][champ_user_key].value_counts().to_dict()

        for user in all_users:
            h_games = scores[scores['H_User_Final'] == user]
            v_games = scores[scores['V_User_Final'] == user]
            all_u_games = pd.concat([h_games, v_games])
            wins = len(h_games[h_games['H_Pts'] > h_games['V_Pts']]) + len(v_games[v_games['V_Pts'] > v_games['H_Pts']])
            losses = len(all_u_games) - wins
            win_pct = round((wins / len(all_u_games)) * 100, 1) if len(all_u_games) else 0.0

            u_draft = draft[draft['USER'] == user]
            n_sent = u_draft['Guys Sent to NFL'].iloc[0] if not u_draft.empty else 0
            n_1st = u_draft['1st Rounders'].iloc[0] if not u_draft.empty else 0
            conf_t = u_draft['Conference Titles'].iloc[0] if not u_draft.empty else 0
            cfp_w = u_draft['CFP Wins'].iloc[0] if not u_draft.empty else 0
            cfp_l = u_draft['CFP Losses'].iloc[0] if not u_draft.empty else 0
            natty_a = u_draft['National Title Appearances'].iloc[0] if not u_draft.empty else 0

            hof_points = (natty_counts.get(user, 0) * 50) + (n_1st * 10)

            stats_list.append({
                'User': user,
                'HoF Points': int(hof_points),
                'Record': f"{wins}-{losses}",
                'Win %': win_pct,
                'Natties': int(natty_counts.get(user, 0)),
                'Drafted': int(n_sent),
                '1st Rounders': int(n_1st),
                'Conf Titles': int(conf_t),
                'CFP Wins': int(cfp_w),
                'CFP Losses': int(cfp_l),
                'Natty Apps': int(natty_a)
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
            h2h_rows.append(h2h_row)
            h2h_numeric.append(h2h_num_row)

        stats_df = pd.DataFrame(stats_list)

        r_2041 = ratings[ratings['YEAR'] == 2041].copy()
        r_2040 = ratings[ratings['YEAR'] == 2040].copy()

        # BCR & Improvement
        bcr_col = 'Blue Chip Ratio (4 & 5 star recruit ratio on roster)'
        r_2041['BCR_Val'] = pd.to_numeric(r_2041[bcr_col].astype(str).str.replace('%', '', regex=False), errors='coerce').fillna(0)

        def get_improvement(row):
            prev = r_2040[(r_2040['TEAM'] == row['TEAM']) & (r_2040['USER'] == row['USER'])]
            if prev.empty:
                prev = r_2040[r_2040['TEAM'] == row['TEAM']]
            return row['OVERALL'] - prev['OVERALL'].values[0] if not prev.empty else 0

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
            'c_yr': c_yr_key,
            'c_coach': c_coach_key,
            'c_school': c_school_key
        }

        return (
            scores,
            stats_df,
            all_users,
            years_available,
            meta,
            r_2041,
            pd.DataFrame(h2h_rows),
            pd.DataFrame(h2h_numeric, index=all_users, columns=all_users),
            coty,
            heisman,
            rec,
            draft
        )
    except Exception as e:
        st.error(f"⚠️ Load Error: {e}")
        return None


def calculate_hardened_prob(row, stats_df):
    u_s = stats_df[stats_df['User'] == row['USER']].iloc[0]
    p_talent = (row['OVERALL'] - 75) * 2.0
    p_speed = (row['Off Speed (90+ speed)'] + row['Def Speed (90+ speed)']) * 2.0
    p_gens = row['Generational (96+ speed or 96+ Acceleration)'] * 2.0
    p_bcr = row['BCR_Val'] * 0.2
    p_legacy = (u_s['Natties'] * 15) + (u_s['Natty Apps'] * 10) + (u_s['Conf Titles'] * 5) + (u_s['CFP Wins'] * 4)
    p_loss_tax = u_s['CFP Losses'] * 6
    heartbreak_tax = (u_s['Natty Apps'] - u_s['Natties']) * 8 if u_s['Natty Apps'] > u_s['Natties'] else 0
    penalty = -25 if u_s['Natties'] == 0 else 0
    if row['OVERALL'] < 82:
        penalty -= 30
    return min(99, max(1, int(p_talent + p_speed + p_gens + p_bcr + p_legacy - p_loss_tax - heartbreak_tax + penalty)))



def calculate_dynasty_predictor(row, stats_df, rec_df, draft_df):
    """
    Forward-looking program projection using:
    roster strength, explosiveness, blue-chip ratio, recruiting momentum,
    coaching pedigree, historical win rate, and recent improvement.
    """
    user = str(row['USER']).strip().title()
    team = str(row['TEAM']).strip().title()
    u_stats = stats_df[stats_df['User'] == user].iloc[0]

    overall = pd.to_numeric(row['OVERALL'], errors='coerce')
    offense = pd.to_numeric(row['OFFENSE'], errors='coerce')
    defense = pd.to_numeric(row['DEFENSE'], errors='coerce')
    off_speed = pd.to_numeric(row['Off Speed (90+ speed)'], errors='coerce')
    def_speed = pd.to_numeric(row['Def Speed (90+ speed)'], errors='coerce')
    team_speed = pd.to_numeric(row['Team Speed (90+ Speed Guys)'], errors='coerce')
    breakers = pd.to_numeric(row['Game Breakers (90+ Speed & 90+ Acceleration)'], errors='coerce')
    generational = pd.to_numeric(row['Generational (96+ speed or 96+ Acceleration)'], errors='coerce')
    bcr = pd.to_numeric(row['BCR_Val'], errors='coerce')
    improvement = pd.to_numeric(row['Improvement'], errors='coerce')

    recruit_score = get_recent_recruiting_score(rec_df, user, team=team, current_year=2041, lookback=3)
    win_pct = get_user_win_pct(user, draft_df)

    pedigree_score = (
        u_stats['Natties'] * 12 +
        u_stats['Natty Apps'] * 6 +
        u_stats['CFP Wins'] * 3 +
        u_stats['Conf Titles'] * 2
    )

    heartbreak_penalty = max(0, (u_stats['Natty Apps'] - u_stats['Natties'])) * 2
    playoff_fail_penalty = u_stats['CFP Losses'] * 1.5

    power_index = (
        (overall * 2.4) +
        (offense * 0.8) +
        (defense * 0.8) +
        ((off_speed + def_speed) * 1.8) +
        (team_speed * 0.7) +
        (breakers * 1.4) +
        (generational * 3.5) +
        (bcr * 0.45) +
        (recruit_score * 0.55) +
        (improvement * 3.0) +
        (win_pct * 100 * 0.7) +
        pedigree_score -
        heartbreak_penalty -
        playoff_fail_penalty
    )
    power_index = round(power_index, 1)

    projected_wins = round(max(5.0, min(12.0, 4.0 + ((power_index - 180) / 18))), 1)
    playoff_odds = int(max(1, min(99, (power_index - 150) * 0.9)))
    natty_odds = int(max(1, min(95, playoff_odds * 0.42 + u_stats['Natties'] * 4 + generational * 2)))

    collapse_risk = int(max(
        1,
        min(
            95,
            55
            - (improvement * 5)
            - ((overall - 80) * 1.2)
            - (bcr * 0.25)
            - (recruit_score * 0.18)
            - (team_speed * 0.5)
            + (u_stats['CFP Losses'] * 1.8)
            + heartbreak_penalty
        )
    ))

    if power_index >= 380:
        stock = "🚀 Surging"
    elif power_index >= 340:
        stock = "📈 Rising"
    elif collapse_risk >= 55:
        stock = "⚠️ Volatile"
    elif power_index < 300:
        stock = "📉 In Trouble"
    else:
        stock = "➖ Stable"

    return pd.Series({
        'Recruit Score': round(recruit_score, 1),
        'Career Win %': round(win_pct * 100, 1),
        'Power Index': power_index,
        'Projected Wins': projected_wins,
        'Playoff Odds': playoff_odds,
        'Natty Odds': natty_odds,
        'Collapse Risk': collapse_risk,
        'Stock': stock
    })


data = load_data()
if data:
    scores, stats, all_users, years, meta, r_2041, h2h_df, h2h_heat, coty, heisman, rec, draft = data

    tabs = st.tabs([
        "🚀 2041 Scout & Projections",
        "🏆 Prestige",
        "⚔️ H2H & Risk Map",
        "📺 Season Recap",
        "📊 Team Analysis",
        "🔍 Talent Profile",
        "🌐 2041 Executive Outlook",
        "🧠 AI Dynasty Predictor"
    ])

    # --- 1. SCOUT & PROJECTIONS ---
    with tabs[0]:
        st.header("🚀 2041 Executive Projections")
        scout_df = r_2041.copy()
        scout_df['Natty Prob'] = scout_df.apply(lambda x: calculate_hardened_prob(x, stats), axis=1)
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Title Contender Odds")
            st.dataframe(
                scout_df.sort_values('Natty Prob', ascending=False)[['USER', 'TEAM', 'OVERALL', 'Natty Prob']],
                hide_index=True,
                use_container_width=True
            )
        with c2:
            st.subheader("Projected Risers")
            st.dataframe(
                scout_df.sort_values('Improvement', ascending=False)[['USER', 'TEAM', 'OVERALL', 'Improvement']],
                hide_index=True,
                use_container_width=True
            )

    # --- 2. PRESTIGE ---
    with tabs[1]:
        st.header("🏆 Prestige Board")
        st.dataframe(stats.sort_values('HoF Points', ascending=False), hide_index=True, use_container_width=True)

    # --- 3. H2H ---
    with tabs[2]:
        st.header("⚔️ Head-to-Head & Risk Map")
        st.plotly_chart(
            px.imshow(h2h_heat, text_auto=True, color_continuous_scale='RdBu_r', aspect='auto'),
            use_container_width=True
        )

    # --- 4. SEASON RECAP ---
    with tabs[3]:
        st.header("📺 AI Dynasty Recap Engine")
        sel_year = st.selectbox("Select Season", years)
        y_data = scores[scores[meta['yr']] == sel_year]
        if not y_data.empty:
            biggest_win = y_data.loc[y_data['Margin'].idxmax()]
            avg_m = round(y_data['Margin'].mean(), 1)
            st.info(
                f"🏟️ **Game of the Year:** {biggest_win['H_User_Final']} vs {biggest_win['V_User_Final']} "
                f"(Margin: {int(biggest_win['Margin'])})"
            )

            y_h = heisman[heisman[meta['h_yr']] == sel_year]
            y_c = coty[coty[meta['c_yr']] == sel_year]
            ca1, ca2 = st.columns(2)
            with ca1:
                if not y_h.empty:
                    st.success(f"🏅 **Heisman:** {y_h.iloc[0][meta['h_player']]} ({y_h.iloc[0][meta['h_school']]})")
            with ca2:
                if not y_c.empty:
                    st.success(f"👔 **COTY:** {y_c.iloc[0][meta['c_coach']]} ({y_c.iloc[0][meta['c_school']]})")

            st.markdown(
                f"**Narrative:** {sel_year} featured {len(y_data)} user battles. "
                f"The average margin of {avg_m} suggests a season of {'dominant runs' if avg_m > 20 else 'tactical grit'}."
            )
        st.dataframe(y_data[[meta['vt'], meta['vs'], meta['hs'], meta['ht'], 'Margin']], hide_index=True, use_container_width=True)

    # --- 5. TEAM ANALYSIS ---
    with tabs[4]:
        st.header("📊 Team Analysis")
        target = st.selectbox("Select Team", r_2041['USER'].tolist())
        row = r_2041[r_2041['USER'] == target].iloc[0]
        t1, t2, t3 = st.columns(3)
        t1.metric("Natty Prob", f"{calculate_hardened_prob(row, stats)}%")
        t2.metric("Improvement", f"{row['Improvement']:+.0f} OVR")
        t3.metric("Blue Chip Ratio", f"{row['BCR_Val']:.0f}%")

    # --- 6. TALENT PROFILE ---
    with tabs[5]:
        st.header("🔍 The 2041 Freak List")
        st.write("Detailed scouting of high-end athletic ceiling.")

        for _, r in r_2041.sort_values('Generational (96+ speed or 96+ Acceleration)', ascending=False).iterrows():
            gens = int(r['Generational (96+ speed or 96+ Acceleration)'])

            if gens == 0:
                gen_desc = "📉 **Fundamentalist Squad:** No track stars found. This team relies on high-IQ play and scheme to win."
                tier = "🐢 GROUND & POUND"
            elif gens == 1:
                gen_desc = "🎯 **The Specialist:** One elite game-breaker. If you stop this one player, you stop the whole engine."
                tier = "🏎️ ROADRUNNER"
            elif gens == 2:
                gen_desc = "⚔️ **Double Trouble:** A lethal duo of track stars. You can't double-team both."
                tier = "🚀 SONIC BOOM"
            elif gens == 3:
                gen_desc = "🔬 **The Speed Lab:** Experimental levels of velocity. This roster erases coaching mistakes with pure foot-speed."
                tier = "🧨 DYNAMITE DEPTH"
            else:
                gen_desc = "⚡ **Flash Point:** You are officially accessing the Speed Force. This is illegal in 48 states."
                tier = "☣️ GOD-TIER VELOCITY"

            with st.expander(f"{r['USER']} | {r['TEAM']} - {tier}"):
                st.write(gen_desc)
                st.metric("Blue Chip Ratio", f"{int(r['BCR_Val'])}%")
                st.write(f"**90+ Speed Depth:** {int(r['Team Speed (90+ Speed Guys)'])} total burners.")
                st.progress(min(1.0, r['BCR_Val'] / 100))

    # --- 7. EXECUTIVE OUTLOOK ---
    with tabs[6]:
        st.header("🌐 2041 Executive Outlook")
        st.plotly_chart(
            px.scatter(
                r_2041,
                x="Off Speed (90+ speed)",
                y="Def Speed (90+ speed)",
                color="USER",
                size="OVERALL",
                text="TEAM",
                hover_data=["BCR_Val", "Improvement", "Generational (96+ speed or 96+ Acceleration)"]
            ),
            use_container_width=True
        )

    # --- 8. AI DYNASTY PREDICTOR ---
    with tabs[7]:
        st.header("🧠 AI Dynasty Predictor")
        st.write(
            "Forward-looking program projections based on roster quality, speed, blue-chip composition, "
            "recruiting momentum, coaching pedigree, and dynasty stability."
        )

        predictor_df = r_2041.copy()
        predictor_metrics = predictor_df.apply(
            lambda x: calculate_dynasty_predictor(x, stats, rec, draft),
            axis=1
        )
        predictor_df = pd.concat([predictor_df, predictor_metrics], axis=1)
        predictor_df = predictor_df.sort_values("Power Index", ascending=False).reset_index(drop=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.subheader("🏆 Title Favorites")
            st.dataframe(
                predictor_df[["USER", "TEAM", "Power Index", "Projected Wins", "Playoff Odds", "Natty Odds", "Stock"]]
                .sort_values("Natty Odds", ascending=False),
                hide_index=True,
                use_container_width=True
            )

        with c2:
            st.subheader("⚠️ Collapse Watch")
            st.dataframe(
                predictor_df[["USER", "TEAM", "Collapse Risk", "Projected Wins", "Recruit Score", "Stock"]]
                .sort_values("Collapse Risk", ascending=False),
                hide_index=True,
                use_container_width=True
            )

        with c3:
            st.subheader("📈 Best Program Stock")
            st.dataframe(
                predictor_df[["USER", "TEAM", "Power Index", "Recruit Score", "Career Win %", "Stock"]]
                .sort_values("Power Index", ascending=False),
                hide_index=True,
                use_container_width=True
            )

        st.markdown("---")

        st.subheader("Power Index Board")
        st.plotly_chart(
            px.bar(
                predictor_df.sort_values("Power Index", ascending=False),
                x="USER",
                y="Power Index",
                color="Stock",
                hover_data=["TEAM", "Projected Wins", "Playoff Odds", "Natty Odds", "Collapse Risk"]
            ),
            use_container_width=True
        )

        st.subheader("Playoff Odds vs Collapse Risk")
        st.plotly_chart(
            px.scatter(
                predictor_df,
                x="Collapse Risk",
                y="Playoff Odds",
                size="Power Index",
                color="USER",
                text="TEAM",
                hover_data=["Projected Wins", "Natty Odds", "Recruit Score", "Career Win %", "Stock"]
            ),
            use_container_width=True
        )

        st.subheader("Full AI Projection Table")
        st.dataframe(
            predictor_df[[
                "USER",
                "TEAM",
                "OVERALL",
                "OFFENSE",
                "DEFENSE",
                "Improvement",
                "BCR_Val",
                "Recruit Score",
                "Career Win %",
                "Power Index",
                "Projected Wins",
                "Playoff Odds",
                "Natty Odds",
                "Collapse Risk",
                "Stock"
            ]],
            hide_index=True,
            use_container_width=True
        )

        selected_user = st.selectbox("Select program for executive briefing", predictor_df["USER"].tolist())
        p_row = predictor_df[predictor_df["USER"] == selected_user].iloc[0]

        st.markdown("---")
        st.subheader(f"📋 Executive Briefing: {p_row['USER']} | {p_row['TEAM']}")

        b1, b2, b3, b4 = st.columns(4)
        b1.metric("Power Index", p_row["Power Index"])
        b2.metric("Projected Wins", p_row["Projected Wins"])
        b3.metric("Playoff Odds", f"{int(p_row['Playoff Odds'])}%")
        b4.metric("Natty Odds", f"{int(p_row['Natty Odds'])}%")

        st.progress(min(1.0, float(p_row["Playoff Odds"]) / 100))
        st.caption(f"Collapse Risk: {int(p_row['Collapse Risk'])}% | Program Stock: {p_row['Stock']}")

        if p_row["Natty Odds"] >= 30:
            st.success(
                f"{p_row['USER']} enters 2041 as a legitimate title threat. "
                f"The model sees enough talent, explosiveness, and institutional pedigree to make a serious run."
            )
        elif p_row["Collapse Risk"] >= 55:
            st.warning(
                f"{p_row['USER']} has real volatility signals. The roster has enough warning signs "
                f"that a disappointing season is very live."
            )
        else:
            st.info(
                f"{p_row['USER']} profiles as a competitive program with a credible postseason path, "
                f"but the model stops short of calling them a top-tier title favorite."
            )

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
