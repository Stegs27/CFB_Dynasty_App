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

        # STANDARDIZE KEYS FOR SCORES
        v_user_key = smart_col(scores, ['Vis_User', 'Visitor User', 'Vis User'])
        h_user_key = smart_col(scores, ['Home_User', 'Home User'])
        v_score_key = smart_col(scores, ['Vis Score', 'Vis_Score'])
        h_score_key = smart_col(scores, ['Home Score', 'Home_Score'])
        yr_key = smart_col(scores, ['YEAR', 'Year'])
        champ_user_key = smart_col(champs, ['user', 'User', 'User of team'])
        
        # STANDARDIZE KEYS FOR AWARDS
        h_yr_key = smart_col(heisman, ['Year', 'YEAR'])
        h_player_key = smart_col(heisman, ['Player', 'Winner', 'Name'])
        h_school_key = smart_col(heisman, ['School', 'Team', 'University'])
        
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
        
        all_users = sorted([u for u in pd.concat([scores['V_User_Final'], scores['H_User_Final']]).unique() if u.upper() != 'CPU' and u != 'Nan'])
        years_available = sorted(scores[yr_key].unique(), reverse=True)

        # MASTER STATS ENGINE
        stats_list, h2h_rows, h2h_numeric = [], [], []
        natty_counts = champs[champs[champ_user_key].str.upper() != 'CPU'][champ_user_key].str.strip().str.title().value_counts().to_dict()
        
        for user in all_users:
            h_games = scores[scores['H_User_Final'] == user]
            v_games = scores[scores['V_User_Final'] == user]
            all_u_games = pd.concat([h_games, v_games])
            wins = len(h_games[h_games['H_Pts'] > h_games['V_Pts']]) + len(v_games[v_games['V_Pts'] > v_games['H_Pts']])
            u_draft = draft[draft['USER'].str.title() == user.title()]
            n_sent = u_draft['Guys Sent to NFL'].iloc[0] if not u_draft.empty else 0
            n_1st = u_draft['1st Rounders'].iloc[0] if not u_draft.empty else 0
            conf_t = u_draft['Conference Titles'].iloc[0] if not u_draft.empty else 0
            cfp_w = u_draft['CFP Wins'].iloc[0] if not u_draft.empty else 0
            cfp_l = u_draft['CFP Losses'].iloc[0] if not u_draft.empty else 0
            natty_a = u_draft['National Title Appearances'].iloc[0] if not u_draft.empty else 0
            
            hof_points = (natty_counts.get(user, 0) * 50) + (n_1st * 10)

            stats_list.append({
                'User': user, 'HoF Points': int(hof_points), 'Record': f"{wins}-{len(all_u_games)-wins}", 
                'Natties': natty_counts.get(user, 0), 'Drafted': n_sent, '1st Rounders': n_1st,
                'Conf Titles': int(conf_t), 'CFP Wins': int(cfp_w), 'CFP Losses': int(cfp_l), 'Natty Apps': int(natty_a)
            })

            h2h_row = {'User': user}
            h2h_num_row = []
            for opp in all_users:
                if user == opp: h2h_row[opp] = "-"; h2h_num_row.append(0)
                else:
                    vs = scores[((scores['V_User_Final']==user) & (scores['H_User_Final']==opp)) | ((scores['V_User_Final']==opp) & (scores['H_User_Final']==user))]
                    vw = len(vs[((vs['V_User_Final']==user) & (vs['V_Pts'] > vs['H_Pts'])) | ((vs['H_User_Final']==user) & (vs['H_Pts'] > vs['V_Pts']))])
                    vl = len(vs) - vw
                    h2h_row[opp] = f"{vw}-{vl}"; h2h_num_row.append(vw - vl)
            h2h_rows.append(h2h_row); h2h_numeric.append(h2h_num_row)

        stats_df = pd.DataFrame(stats_list)
        r_2041 = ratings[ratings['YEAR'] == 2041].copy()
        r_2040 = ratings[ratings['YEAR'] == 2040].copy()
        r_2041['USER'] = r_2041['USER'].str.strip().str.title()
        
        # BCR & Improvement
        bcr_col = 'Blue Chip Ratio (4 & 5 star recruit ratio on roster)'
        r_2041['BCR_Val'] = pd.to_numeric(r_2041[bcr_col].astype(str).str.replace('%', ''), errors='coerce').fillna(0)
        
        def get_improvement(row):
            prev = r_2040[r_2040['TEAM'] == row['TEAM']]
            return row['OVERALL'] - prev['OVERALL'].values[0] if not prev.empty else 0
        r_2041['Improvement'] = r_2041.apply(get_improvement, axis=1)

        meta = {
            'yr': yr_key, 'vt': smart_col(scores, ['Visitor']), 'vs': v_score_key, 'ht': smart_col(scores, ['Home']), 'hs': h_score_key,
            'h_yr': h_yr_key, 'h_player': h_player_key, 'h_school': h_school_key,
            'c_yr': c_yr_key, 'c_coach': c_coach_key, 'c_school': c_school_key
        }

        return scores, stats_df, all_users, years_available, meta, r_2041, pd.DataFrame(h2h_rows), pd.DataFrame(h2h_numeric, index=all_users, columns=all_users), coty, heisman
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
    p_loss_tax = (u_s['CFP Losses'] * 6)
    heartbreak_tax = (u_s['Natty Apps'] - u_s['Natties']) * 8 if u_s['Natty Apps'] > u_s['Natties'] else 0
    penalty = -25 if u_s['Natties'] == 0 else 0
    if row['OVERALL'] < 82: penalty -= 30
    return min(99, max(1, int(p_talent + p_speed + p_gens + p_bcr + p_legacy - p_loss_tax - heartbreak_tax + penalty)))

data = load_data()
if data:
    scores, stats, all_users, years, meta, r_2041, h2h_df, h2h_heat, coty, heisman = data
    tabs = st.tabs(["🚀 2041 Scout & Projections", "🏆 Prestige", "⚔️ H2H & Risk Map", "📺 Season Recap", "📊 Team Analysis", "🔍 Talent Profile", "🌐 2041 Executive Outlook"])

    # --- 1. SCOUT & PROJECTIONS ---
    with tabs[0]:
        st.header("🚀 2041 Executive Projections")
        r_2041['Natty Prob'] = r_2041.apply(lambda x: calculate_hardened_prob(x, stats), axis=1)
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Title Contender Odds")
            st.dataframe(r_2041.sort_values('Natty Prob', ascending=False)[['USER', 'TEAM', 'OVERALL', 'Natty Prob']], hide_index=True)
        with c2:
            st.subheader("Projected Risers")
            st.dataframe(r_2041.sort_values('Improvement', ascending=False)[['USER', 'TEAM', 'OVERALL', 'Improvement']], hide_index=True)

    # --- 2. PRESTIGE ---
    with tabs[1]:
        st.subheader("Dynasty Career Leaderboard")
        st.dataframe(stats.sort_values('HoF Points', ascending=False), hide_index=True)

    # --- 3. H2H & RISK MAP ---
    with tabs[2]:
        st.subheader("Head-to-Head Risk Map")
        st.plotly_chart(px.imshow(h2h_heat, text_auto=True, color_continuous_scale='RdBu_r'), use_container_width=True)
        st.table(h2h_df.set_index('User'))

    # --- 4. SEASON RECAP (FULLY RESTORED NARRATIVE + AWARDS) ---
    with tabs[3]:
        st.header("📺 AI Dynasty Recap Engine")
        sel_year = st.selectbox("Select Season to Recap", years)
        year_data = scores[scores[meta['yr']] == sel_year]
        
        st.subheader(f"The Story of {sel_year}")
        if not year_data.empty:
            # Game of the Year Calculation
            biggest_win = year_data.loc[year_data['Margin'].idxmax()]
            avg_margin = round(year_data['Margin'].mean(), 1)
            
            st.info(f"🏟️ **Game of the Year Performance:** {biggest_win['H_User_Final']} vs {biggest_win['V_User_Final']} (Margin: {int(biggest_win['Margin'])})")
            
            # Award Integration
            st.markdown("### 🏆 Award Ceremonies")
            year_heisman = heisman[heisman[meta['h_yr']] == sel_year]
            year_coty = coty[coty[meta['c_yr']] == sel_year]

            ca1, ca2 = st.columns(2)
            with ca1:
                if not year_heisman.empty:
                    h_win = year_heisman.iloc[0]
                    st.success(f"🏅 **Heisman Trophy:** {h_win[meta['h_player']]} ({h_win[meta['h_school']]})")
                else:
                    st.write("No Heisman data for this year.")
            with ca2:
                if not year_coty.empty:
                    c_win = year_coty.iloc[0]
                    st.success(f"👔 **Coach of the Year:** {c_win[meta['c_coach']]} ({c_win[meta['c_school']]})")
                else:
                    st.write("No COTY data for this year.")

            st.markdown(f"""
            ### 📝 Executive Summary
            The {sel_year} campaign was defined by high-stakes efficiency. 
            Looking at the data, we saw a total of **{len(year_data)}** high-profile user matchups. 
            The average margin of victory was **{avg_margin}**, suggesting a season of {'absolute dominance' if avg_margin > 20 else 'nail-biting finishes and tactical chess matches'}.
            """)
        
        st.subheader("Full Scoreboard")
        st.dataframe(year_data[[meta['vt'], meta['vs'], meta['hs'], meta['ht'], 'Margin']], hide_index=True)

    # --- 5. TEAM ANALYSIS ---
    with tabs[4]:
        st.header("📊 Executive Deep-Dive")
        target = st.selectbox("Select Program", r_2041['USER'].tolist())
        row = r_2041[r_2041['USER'] == target].iloc[0]
        u_s = stats[stats['User'] == target].iloc[0]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Natty Prob", f"{calculate_hardened_prob(row, stats)}%")
        c2.metric("BCR Score", f"{int(row['BCR_Val'])}%")
        c3.metric("Postseason", f"{u_s['CFP Wins']}-{u_s['CFP Losses']}")
        c4.metric("Legacy Rings", u_s['Natties'])
        st.write(f"**Top Star:** {row['⭐ STAR SKILL GUY (Top OVR)']}")

    # --- 6. TALENT PROFILE (POPCULTURE REFS) ---
    with tabs[5]:
        st.header("🔍 The 2041 Freak List")
        for _, r in r_2041.sort_values('Generational (96+ speed or 96+ Acceleration)', ascending=False).iterrows():
            gens = int(r['Generational (96+ speed or 96+ Acceleration)'])
            if gens >= 4: tier = "⚡ FLASH POINT (Accessing the Speed Force)"
            elif gens >= 2: tier = "🚀 SONIC BOOM (Mach 1 Roster)"
            elif r['Team Speed (90+ Speed Guys)'] >= 12: tier = "🏎️ THE FAST & THE FURIOUS"
            else: tier = "🏎️ ROADRUNNER (Elite High-End Speed)"
            
            st.info(f"**{tier}**\n\n**{r['USER']}** ({r['TEAM']}) has **{gens}** Generational Talents and a **{int(r['BCR_Val'])}%** Blue Chip Ratio.")

    # --- 7. EXECUTIVE OUTLOOK ---
    with tabs[6]:
        st.header("🌐 2041 Executive Outlook")
        st.plotly_chart(px.scatter(r_2041, x="Off Speed (90+ speed)", y="Def Speed (90+ speed)", color="USER", size="OVERALL", text="TEAM", title="The Speed vs Talent Landscape"), use_container_width=True)
        st.dataframe(r_2041[['USER', 'TEAM', 'OVERALL', 'Improvement', 'BCR_Val']], hide_index=True)

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()