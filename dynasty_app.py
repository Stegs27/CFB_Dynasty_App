import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import random

# --- PAGE SETUP ---
st.set_page_config(page_title="Island Dynasty HQ", layout="wide", page_icon="🏈")
st.title("🏈 Island Dynasty: Prestige & Scouting")

def smart_col(df, target_names):
    for target in target_names:
        for col in df.columns:
            if col.strip().lower() == target.lower():
                return col
    return None

@st.cache_data
def load_data():
    try:
        # 1. LOAD ALL FILES
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

        # RECRUITING & TENURE RECONSTRUCTION
        non_year_cols = [c for c in rec.columns if not str(c).strip().isdigit()]
        rec_long = rec.melt(id_vars=non_year_cols, var_name='Year', value_name='Rank')
        rec_long['Rank'] = rec_long['Rank'].astype(str).str.replace(r'[*\-]', '', regex=True).replace('nan', np.nan)
        rec_long['Rank'] = pd.to_numeric(rec_long['Rank'], errors='coerce')
        rec_long['Year'] = pd.to_numeric(rec_long['Year'], errors='coerce')
        
        # Calculate Tenure per (User, Team)
        tenure_df = rec_long.dropna(subset=['Rank']).groupby(['USER', 'Teams'])['Year'].min().reset_index()
        tenure_df['Tenure'] = 2041 - tenure_df['Year'] + 1
        tenure_map = tenure_df.set_index(['USER', 'Teams'])['Tenure'].to_dict()

        rec_user_col = smart_col(rec, ['USER', 'User'])
        user_avg_rec = rec_long.groupby(rec_user_col)['Rank'].mean().to_dict()
        num_1_classes = rec_long[rec_long['Rank'] == 1].groupby(rec_user_col).size().to_dict()

        # DRAFT & AWARD AGGREGATION
        draft.columns = [c.strip() for c in draft.columns]
        draft['USER'] = draft['USER'].str.strip().str.title()
        heis_counts = heisman['USER'].str.strip().str.title().value_counts().to_dict()
        coty_counts = coty[coty['User'].str.upper() != 'CPU']['User'].str.strip().str.title().value_counts().to_dict()
        natty_counts = champs[champs[champ_user_key].str.upper() != 'CPU'][champ_user_key].str.strip().str.title().value_counts().to_dict()

        # MASTER STATS ENGINE
        stats_list, h2h_rows = [], []
        for i, user in enumerate(all_users):
            h_games = scores[scores['H_User_Final'] == user]
            v_games = scores[scores['V_User_Final'] == user]
            all_u_games = pd.concat([h_games, v_games])
            wins = len(h_games[h_games['H_Pts'] > h_games['V_Pts']]) + len(v_games[v_games['V_Pts'] > v_games['H_Pts']])
            
            # Use sum of individual comparisons to avoid series label errors
            v_conf = v_games[(v_games['Conf Title'].str.lower() == 'yes') & (v_games['V_Pts'] > v_games['H_Pts'])]
            h_conf = h_games[(h_games['Conf Title'].str.lower() == 'yes') & (h_games['H_Pts'] > v_games['H_Pts'])]
            conf_titles = len(v_conf) + len(h_conf)
            
            cfp_apps = pd.concat([v_games[v_games['CFP'].str.lower() == 'yes'], h_games[h_games['CFP'].str.lower() == 'yes']])['YEAR'].nunique()

            u_draft = draft[draft['USER'] == user]
            n_sent = u_draft['Guys Sent to NFL'].iloc[0] if not u_draft.empty else 0
            n_1st = u_draft['1st Rounders'].iloc[0] if not u_draft.empty else 0
            
            hof_points = (natty_counts.get(user, 0) * 50) + (cfp_apps * 20) + (conf_titles * 15) + \
                         (coty_counts.get(user, 0) * 15) + (n_1st * 10) + (heis_counts.get(user, 0) * 10) + \
                         ((n_sent - n_1st) * 3) + (num_1_classes.get(user, 0) * 10)

            # Defensive/Offensive Averages
            def get_u_off(row): return row['H_Pts'] if row['H_User_Final'] == user else row['V_Pts']
            def get_u_def(row): return row['V_Pts'] if row['H_User_Final'] == user else row['H_Pts']
            
            stats_list.append({
                'User': user, 'HoF Points': int(hof_points), 'Record': f"{wins}-{len(all_u_games)-wins}", 
                'NFL Guys': int(n_sent), '1st Rounders': int(n_1st), 'Natties': natty_counts.get(user, 0),
                'Off_Avg': all_u_games.apply(get_u_off, axis=1).mean() if not all_u_games.empty else 0,
                'Def_Avg': all_u_games.apply(get_u_def, axis=1).mean() if not all_u_games.empty else 0,
                'Home Strength': round(h_games['H_Pts'].mean() - h_games['V_Pts'].mean(), 1) if not h_games.empty else 0,
                'Away Strength': round(v_games['V_Pts'].mean() - v_games['H_Pts'].mean(), 1) if not v_games.empty else 0
            })
            
            h2h_row = {'User': user}
            for opp in all_users:
                if user == opp: h2h_row[opp] = "-"
                else:
                    vs = scores[((scores['V_User_Final']==user) & (scores['H_User_Final']==opp)) | ((scores['V_User_Final']==opp) & (scores['H_User_Final']==user))]
                    vw = len(vs[((vs['V_User_Final']==user) & (vs['V_Pts'] > vs['H_Pts'])) | ((vs['H_User_Final']==user) & (vs['H_Pts'] > vs['V_Pts']))])
                    h2h_row[opp] = f"{vw}-{len(vs)-vw}"
            h2h_rows.append(h2h_row)

        stats_df = pd.DataFrame(stats_list).sort_values(by='HoF Points', ascending=False)
        adj = stats_df['HoF Points'] - stats_df['HoF Points'].min() + 10
        stats_df['Prestige %'] = round((adj / adj.sum()) * 100, 1)

        # 2041 DATA
        ratings_2041 = ratings[ratings['YEAR'] == 2041].copy()
        ratings_2041['USER'] = ratings_2041['USER'].str.strip().str.title()
        
        def project_wins(row):
            w = 6 + ((row['OVERALL'] - 80) / 2.5)
            if str(row['Star Skill Guy is Generational Speed?']).strip().lower() == 'yes': w += 1.0
            if row['Off Speed (90+ speed)'] > 8: w += 0.5
            fw = round(min(12, max(0, w)))
            return f"{fw}-{12-fw}"
        ratings_2041['2041 Projection'] = ratings_2041.apply(project_wins, axis=1)
        
        # Merge Tenure into Ratings
        ratings_2041['Tenure'] = ratings_2041.apply(lambda x: tenure_map.get((x['USER'], x['TEAM']), 1), axis=1)

        col_meta = {'yr': yr_key, 'vt': smart_col(scores, ['Visitor']), 'vs': v_score_key, 'ht': smart_col(scores, ['Home']), 'hs': h_score_key, 'cyr': champ_yr_key, 'cu': champ_user_key}
        return scores, rec_long, stats_df, pd.DataFrame(h2h_rows), all_users, years_available, col_meta, champs, ratings_2041
    except Exception as e:
        st.error(f"⚠️ Load Error: {e}")
        return None

# --- DYNAMIC AI GENERATORS ---
def get_dynamic_recap(year, scores_df, champs_df, meta, stats_df):
    yr_data = scores_df[scores_df[meta['yr']] == year]
    natty_row = champs_df[champs_df[meta['cyr']].astype(str) == str(year)]
    winner = natty_row[meta['cu']].values[0] if not natty_row.empty else "Nobody"
    
    avg_margin = round(yr_data['Margin'].mean(), 1)
    blowout = yr_data.loc[yr_data['Margin'].idxmax()]
    
    intros = [
        f"In {year}, the league was basically {winner}'s personal playground.",
        f"{year} will be remembered as the year {winner} stopped being polite and started being a problem.",
        f"Looking back at {year}, the hierarchy was clear: {winner} at the top, and everyone else in the dumpster."
    ]
    
    roasts = [
        f"While {winner} was lifting trophies, {blowout[meta['vt']]} was busy losing by {int(blowout['Margin'])} points. A masterclass in failure.",
        f"The average margin was {avg_margin}, which is higher than most of your IQs during the redzone.",
        f"Shoutout to {blowout[meta['ht']]} for providing the comedy of the year with that {int(blowout['Margin'])}-point beatdown."
    ]
    
    recap = f"### 🎙️ The {year} Season Breakdown\n"
    recap += f"**Champion:** {winner}\n\n"
    recap += f"{random.choice(intros)}\n\n"
    recap += f"**The AI Audit:** {random.choice(roasts)}\n\n"
    recap += f"**Historical Context:** Defense was optional this year. If you weren't scoring, you weren't trying."
    return recap

def get_gen_writeup(user, team, count):
    templates = [
        f"🚀 **{user}**'s lab has produced {count} generational freaks. Defensive coordinators are checking into therapy.",
        f"💎 {team} is currently running a 40-yard dash competition instead of a football team. {count} specimens with 96+ speed/accel found.",
        f"☣️ Biological hazard: {user} has {count} players who break the physics of the game. Catching them is legally impossible.",
        f"🏎️ The speed limit in {team} is officially 'Whenever we feel like it'. {count} generational burners on one roster is a war crime."
    ]
    return random.choice(templates)

# --- UI ---
data = load_data()
if data:
    scores, rec_long, stats, h2h_df, all_users, years, meta, champs_df, ratings_2041 = data
    tabs = st.tabs(["🏆 Prestige", "⚔️ H2H Matrix", "📺 Season Recap", "📊 Team Analysis", "🚀 2041 Scout & Projections", "📈 Recruiting", "🔍 2041 Talent Profile"])

    with tabs[0]:
        st.subheader("The Dynasty Hall of Fame")
        c1, c2 = st.columns([2.5,1])
        c1.dataframe(stats[['User', 'HoF Points', 'Record', 'NFL Guys', '1st Rounders', 'Natties']], hide_index=True)
        c2.plotly_chart(px.pie(stats, values='Prestige %', names='User', hole=0.4, title="Legacy Share"))

    with tabs[1]:
        st.header("Head-to-Head Matrix")
        st.table(h2h_df.set_index('User'))

    with tabs[2]:
        st.header("📺 Season Recap")
        sel_year = st.selectbox("Select Season", years)
        st.markdown(get_dynamic_recap(sel_year, scores, champs_df, meta, stats))
        st.dataframe(scores[scores[meta['yr']] == sel_year][[meta['vt'], meta['vs'], meta['hs'], meta['ht']]], hide_index=True)

    with tabs[3]:
        st.header("📊 In-Depth Team Analysis (2041)")
        sel_u = st.selectbox("Select Team to Analyze", all_users)
        u_stats = stats[stats['User'] == sel_u].iloc[0]
        u_2041 = ratings_2041[ratings_2041['USER'] == sel_u].iloc[0]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Tenure", f"{int(u_2041['Tenure'])} Years", f"With {u_2041['TEAM']}")
        c2.metric("Prestige Rank", f"#{stats.index[stats['User']==sel_u][0] + 1}", f"{u_stats['HoF Points']} pts")
        c3.metric("Projected Record", u_2041['2041 Projection'])
        
        st.markdown(f"### 📋 {u_2041['TEAM']} Scouting Report")
        sc_col1, sc_col2 = st.columns(2)
        with sc_col1:
            st.write(f"**Offensive Identity:** {u_2041['OFFENSE']} OVR. They feature **{int(u_2041['Off Speed (90+ speed)'])}** elite speedsters. ")
            st.write(f"**Defensive Identity:** {u_2041['DEFENSE']} OVR. Perimeters are locked by **{int(u_2041['Def Speed (90+ speed)'])}** fast defenders.")
        with sc_col2:
            st.write(f"**Star Player:** {u_2041['⭐ STAR SKILL GUY (Top OVR)']}")
            is_gen = "Yes - Pure Speed" if str(u_2041['Star Skill Guy is Generational Speed?']).lower() == 'yes' else "No"
            st.write(f"**Generational Star Status:** {is_gen}")
            st.write(f"**Total Track Team Count:** {int(u_2041['Team Speed (90+ Speed Guys)'])} players.")

    with tabs[4]:
        st.header("🚀 2041 Scout & Projections")
        # Display all columns from the ratings file as requested
        st.dataframe(ratings_2041, hide_index=True)

    with tabs[5]:
        st.header("📈 Recruiting Trends")
        sel_users = st.multiselect("Users to Compare", all_users, default=all_users[:3])
        filtered_rec = rec_long[rec_long['USER'].isin(sel_users)].dropna()
        if not filtered_rec.empty:
            fig = px.line(filtered_rec, x='Year', y='Rank', color='USER', markers=True, title="Class Rank History")
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)

    with tabs[6]:
        st.header("🔍 2041 Talent & Speed Analysis")
        st.subheader("Generational Talent Tracker")
        gen_players = ratings_2041[ratings_2041['Generational (96+ speed or 96+ Acceleration)'] > 0].sort_values('Generational (96+ speed or 96+ Acceleration)', ascending=False)
        for _, row in gen_players.iterrows():
            st.info(get_gen_writeup(row['USER'], row['TEAM'], int(row['Generational (96+ speed or 96+ Acceleration)'])))
            
        st.markdown("---")
        st.subheader("Team Speed Comparison")
        fig_speed = px.bar(ratings_2041.sort_values('Team Speed (90+ Speed Guys)', ascending=False), 
                          x='USER', y='Team Speed (90+ Speed Guys)', color='TEAM',
                          title="90+ Speed Players by User")
        st.plotly_chart(fig_speed, use_container_width=True)

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()