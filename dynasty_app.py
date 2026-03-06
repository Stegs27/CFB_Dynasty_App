import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import random

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
        # 1. LOAD CORE FILES
        scores = pd.read_csv('scores.csv')
        rec = pd.read_csv('recruiting.csv')
        champs = pd.read_csv('champs.csv')
        draft = pd.read_csv('UserDraftPicks.csv')
        ratings = pd.read_csv('TeamRatingsHistory.csv')
        heisman = pd.read_csv('Heisman_History.csv')
        coty = pd.read_csv('COTY.csv')

        # STANDARDIZE COLUMN KEYS
        v_user_key = smart_col(scores, ['Vis_User', 'Visitor User', 'Vis User'])
        h_user_key = smart_col(scores, ['Home_User', 'Home User'])
        v_score_key = smart_col(scores, ['Vis Score', 'Vis_Score'])
        h_score_key = smart_col(scores, ['Home Score', 'Home_Score'])
        yr_key = smart_col(scores, ['YEAR', 'Year'])
        champ_user_key = smart_col(champs, ['user', 'User', 'User of team'])
        champ_yr_key = smart_col(champs, ['Year', 'YEAR'])

        # CLEAN SCORES
        scores['V_User_Final'] = scores[v_user_key].astype(str).str.strip().str.title()
        scores['H_User_Final'] = scores[h_user_key].astype(str).str.strip().str.title()
        scores['V_Pts'] = pd.to_numeric(scores[v_score_key], errors='coerce')
        scores['H_Pts'] = pd.to_numeric(scores[h_score_key], errors='coerce')
        scores = scores.dropna(subset=['V_Pts', 'H_Pts'])
        scores['Margin'] = (scores['H_Pts'] - scores['V_Pts']).abs()
        
        all_users = sorted([u for u in pd.concat([scores['V_User_Final'], scores['H_User_Final']]).unique() if u.upper() != 'CPU' and u != 'Nan'])
        years_available = sorted(scores[yr_key].unique(), reverse=True)

        # RECRUITING & TENURE LOGIC
        year_cols = [c for c in rec.columns if c.isdigit()]
        def calculate_tenure(user, team):
            # Find the row for this specific user and team
            row = rec[(rec['USER'].str.title() == user.title()) & (rec['Teams'].str.strip() == team.strip())]
            if not row.empty:
                return row[year_cols].notna().sum(axis=1).values[0]
            return 1

        # DRAFT & AWARD AGGREGATION
        draft.columns = [c.strip() for c in draft.columns]
        draft['USER'] = draft['USER'].str.strip().str.title()
        heis_counts = heisman['USER'].str.strip().str.title().value_counts().to_dict()
        coty_counts = coty[coty['User'].str.upper() != 'CPU']['User'].str.strip().str.title().value_counts().to_dict()
        natty_counts = champs[champs[champ_user_key].str.upper() != 'CPU'][champ_user_key].str.strip().str.title().value_counts().to_dict()

        # MASTER STATS ENGINE
        stats_list = []
        for user in all_users:
            h_games = scores[scores['H_User_Final'] == user]
            v_games = scores[scores['V_User_Final'] == user]
            all_u_games = pd.concat([h_games, v_games])
            wins = len(h_games[h_games['H_Pts'] > h_games['V_Pts']]) + len(v_games[v_games['V_Pts'] > v_games['H_Pts']])
            
            # FIXED LOGIC: Comparisons strictly within the same subset
            v_conf = v_games[(v_games['Conf Title'].str.lower() == 'yes') & (v_games['V_Pts'] > v_games['H_Pts'])]
            h_conf = h_games[(h_games['Conf Title'].str.lower() == 'yes') & (h_games['H_Pts'] > h_games['V_Pts'])]
            conf_titles = len(v_conf) + len(h_conf)
            
            cfp_apps = pd.concat([v_games[v_games['CFP'].str.lower() == 'yes'], h_games[h_games['CFP'].str.lower() == 'yes']])['YEAR'].nunique()
            
            u_draft = draft[draft['USER'] == user]
            n_sent = u_draft['Guys Sent to NFL'].iloc[0] if not u_draft.empty else 0
            n_1st = u_draft['1st Rounders'].iloc[0] if not u_draft.empty else 0
            
            hof_points = (natty_counts.get(user, 0) * 50) + (cfp_apps * 20) + (conf_titles * 15) + \
                         (coty_counts.get(user, 0) * 15) + (n_1st * 10) + (heis_counts.get(user, 0) * 10)

            stats_list.append({
                'User': user, 'HoF Points': int(hof_points), 'Record': f"{wins}-{len(all_u_games)-wins}", 
                'Total Wins': wins, 'Natties': natty_counts.get(user, 0), 'Drafted': n_sent
            })

        stats_df = pd.DataFrame(stats_list).sort_values(by='HoF Points', ascending=False)

        # 2041 DATA & TENURE
        r_2041 = ratings[ratings['YEAR'] == 2041].copy()
        r_2041['USER'] = r_2041['USER'].str.strip().str.title()
        r_2041['Tenure'] = r_2041.apply(lambda x: calculate_tenure(x['USER'], x['TEAM']), axis=1)
        
        col_meta = {'yr': yr_key, 'vt': smart_col(scores, ['Visitor']), 'vs': v_score_key, 'ht': smart_col(scores, ['Home']), 'hs': h_score_key, 'cyr': champ_yr_key, 'cu': champ_user_key}
        return scores, stats_df, all_users, years_available, col_meta, champs, r_2041, rec
    except Exception as e:
        st.error(f"⚠️ Load Error: {e}")
        return None

# --- DYNAMIC AI FUNCTIONS ---
def get_ai_recap(year, scores_df, champs_df, meta):
    natty_row = champs_df[champs_df[meta['cyr']].astype(str) == str(year)]
    winner = natty_row[meta['cu']].values[0] if not natty_row.empty else "The CPUs"
    blowout = scores_df[scores_df[meta['yr']] == year].sort_values('Margin', ascending=False).iloc[0]
    
    templates = [
        f"In {year}, {winner} played like they had a cheat code enabled, while the rest of the league looked like they were holding the controller upside down.",
        f"{year} was a total bloodbath. {winner} stood at the top of the mountain, while {blowout[meta['vt']]} was getting dismantled by {int(blowout['Margin'])} points. Embarrassing stuff.",
        f"The history books will record {year} as the time {winner} finally realized they were better than everyone else. Shoutout to {blowout[meta['ht']]} for being the official punching bag of the season.",
        f"While {winner} was celebrating a Natty, half the users in this league were probably searching 'how to play defense' on YouTube. A {int(blowout['Margin'])}-point blowout really sums up the lack of effort."
    ]
    return random.choice(templates)

def get_gen_freak_commentary(user, team, count):
    templates = [
        f"🚨 **{user}** at {team} is currently running a track meet. They have **{count}** generational freaks. Defensive coordinators are literally quitting their jobs.",
        f"💎 BIOLOGICAL ANOMALY: {team} roster contains **{count}** players who break the game's physics. {user} isn't recruiting, he's cloning specimens in a lab.",
        f"🏎️ The speed limit in {team} has been officially repealed. {user} has **{count}** players with 96+ Speed/Accel. Catching them is legally impossible.",
        f"☣️ WARNING: {team} has **{count}** generational burners. If you don't have a 99-speed corner, just don't even bother showing up to the game."
    ]
    return random.choice(templates)

# --- UI EXECUTION ---
data = load_data()
if data:
    scores, stats, all_users, years, meta, champs_df, r_2041, rec_raw = data
    tabs = st.tabs(["🏆 Prestige", "📺 Season Recap", "📊 Team Analysis", "🚀 2041 Scout & Projections", "📈 Recruiting", "🔍 Talent Profile"])

    with tabs[0]:
        st.subheader("The Dynasty Hall of Fame")
        st.dataframe(stats[['User', 'HoF Points', 'Record', 'Natties', 'Drafted']], hide_index=True)

    with tabs[1]:
        st.header("📺 Season Recap")
        sel_year = st.selectbox("Select Season", years)
        st.info(get_ai_recap(sel_year, scores, champs_df, meta))
        st.dataframe(scores[scores[meta['yr']] == sel_year][[meta['vt'], meta['vs'], meta['hs'], meta['ht'], 'Margin']], hide_index=True)

    with tabs[2]:
        st.header("📊 2041 Team Deep-Dive")
        target = st.selectbox("Select Team to Analyze", r_2041['USER'].tolist())
        row = r_2041[r_2041['USER'] == target].iloc[0]
        u_stats = stats[stats['User'] == target].iloc[0]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("School Tenure", f"{int(row['Tenure'])} Years", f"At {row['TEAM']}")
        c2.metric("Overall", row['OVERALL'])
        c3.metric("HoF Ranking", f"Rank #{stats.index[stats['User']==target][0] + 1}")
        c4.metric("Star Player", f"OVR {row['OFFENSE']}")

        st.markdown(f"### 📑 Scouting Narrative: {target}")
        analysis = f"Under Coach {target}, **{row['TEAM']}** has built a **{row['OVERALL']} OVR** juggernaut. "
        analysis += f"The offensive engine is fueled by **{int(row['Off Speed (90+ speed)'])}** elite burners, centered around **{row['⭐ STAR SKILL GUY (Top OVR)']}**. "
        
        if row['Generational (96+ speed or 96+ Acceleration)'] > 0:
            analysis += f"The X-factor is the presence of **{int(row['Generational (96+ speed or 96+ Acceleration)'])}** generational talents that cannot be schemed against. "
        
        analysis += f"With a tenure of {int(row['Tenure'])} years, {target} has fully implemented their system. "
        analysis += f"Historically, this coach has sent **{u_stats['Drafted']}** players to the NFL and secured **{u_stats['Natties']}** National Titles. "
        
        if row['DEFENSE'] > row['OFFENSE']:
            analysis += "This is a defensive-first squad that relies on speed to erase perimeter mistakes."
        else:
            analysis += "This team is a high-octane scoring machine that looks to out-track opponents."
            
        st.write(analysis)

    with tabs[3]:
        st.header("🚀 2041 Scout & Full Ratings")
        # Included all columns from TeamRatingsHistory as requested
        st.dataframe(r_2041, hide_index=True)

    with tabs[4]:
        st.header("📈 Recruiting Trends")
        sel_users = st.multiselect("Compare Users", all_users, default=all_users[:3])
        # Reshape recruiting for chart
        yr_cols = [c for c in rec_raw.columns if c.isdigit()]
        rec_long = rec_raw.melt(id_vars=['USER'], value_vars=yr_cols, var_name='Year', value_name='Rank')
        rec_long['Rank'] = pd.to_numeric(rec_long['Rank'].astype(str).str.replace(r'[*\-]', '', regex=True), errors='coerce')
        
        filtered = rec_long[rec_long['USER'].isin(sel_users)].dropna()
        if not filtered.empty:
            fig = px.line(filtered, x='Year', y='Rank', color='USER', markers=True)
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)

    with tabs[5]:
        st.header("🔍 Generational Talent Tracker")
        gen_df = r_2041[r_2041['Generational (96+ speed or 96+ Acceleration)'] > 0].sort_values('Generational (96+ speed or 96+ Acceleration)', ascending=False)
        for _, r in gen_df.iterrows():
            st.warning(get_gen_freak_commentary(r['USER'], r['TEAM'], int(r['Generational (96+ speed or 96+ Acceleration)'])))

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()