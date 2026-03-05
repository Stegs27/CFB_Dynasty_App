import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- PAGE SETUP ---
st.set_page_config(page_title="Island Dynasty HQ", layout="wide", page_icon="🏈")
st.title("🏈 Island Dynasty: SportsCenter HQ")

def smart_col(df, target_names):
    for target in target_names:
        for col in df.columns:
            if col.strip().lower() == target.lower():
                return col
    return None

@st.cache_data
def load_data():
    try:
        scores = pd.read_csv('scores.csv')
        rec = pd.read_csv('recruiting.csv')
        champs = pd.read_csv('champs.csv')

        # 1. COLUMN IDENTIFICATION
        v_user_key = smart_col(scores, ['Vis_User', 'Visitor User', 'Vis User'])
        h_user_key = smart_col(scores, ['Home_User', 'Home User'])
        v_score_key = smart_col(scores, ['Vis Score', 'Vis_Score'])
        h_score_key = smart_col(scores, ['Home Score', 'Home_Score'])
        v_team_key = smart_col(scores, ['Visitor', 'Vis Team'])
        h_team_key = smart_col(scores, ['Home', 'Home Team'])
        cfp_key = smart_col(scores, ['CFP'])
        yr_key = smart_col(scores, ['YEAR', 'Year'])
        champ_user_key = smart_col(champs, ['user', 'User', 'User of team'])

        # 2. DATA CLEANING
        scores['V_User_Final'] = scores[v_user_key].astype(str).str.strip().str.title()
        scores['H_User_Final'] = scores[h_user_key].astype(str).str.strip().str.title()
        scores['V_Pts'] = pd.to_numeric(scores[v_score_key], errors='coerce')
        scores['H_Pts'] = pd.to_numeric(scores[h_score_key], errors='coerce')
        scores = scores.dropna(subset=['V_Pts', 'H_Pts'])
        scores['Margin'] = (scores['H_Pts'] - scores['V_Pts']).abs()
        
        all_users = sorted([u for u in pd.concat([scores['V_User_Final'], scores['H_User_Final']]).unique() if u.upper() != 'CPU' and u != 'Nan'])

        # 3. RECRUITING & TEAM MAPPING
        r_team_col = rec.columns[0]
        rec_long = rec.melt(id_vars=r_team_col, var_name='Year', value_name='Rank')
        rec_long = rec_long.rename(columns={r_team_col: 'Team'})
        rec_long['Rank'] = pd.to_numeric(rec_long['Rank'].astype(str).str.replace(r'[*\-]', '', regex=True), errors='coerce')
        rec_long = rec_long.dropna()

        team_to_user = {}
        for _, row in scores.iterrows():
            if row['V_User_Final'] != 'Cpu': team_to_user[row[v_team_key]] = row['V_User_Final']
            if row['H_User_Final'] != 'Cpu': team_to_user[row[h_team_key]] = row['H_User_Final']
        
        rec_long['User_Mapped'] = rec_long['Team'].map(team_to_user)
        user_avg_rec = rec_long.groupby('User_Mapped')['Rank'].mean().to_dict()

        # 4. PRIMARY STATS ENGINE
        stats_list = []
        user_team_history = []
        latest_year = scores[yr_key].max()

        for user in all_users:
            h_games = scores[scores['H_User_Final'] == user]
            v_games = scores[scores['V_User_Final'] == user]
            all_u_games = pd.concat([h_games, v_games])
            
            # Season specific for recap
            current_yr_games = all_u_games[all_u_games[yr_key] == latest_year]
            cy_wins = len(current_yr_games[((current_yr_games['H_User_Final']==user)&(current_yr_games['H_Pts']>current_yr_games['V_Pts'])) | 
                                          ((current_yr_games['V_User_Final']==user)&(current_yr_games['V_Pts']>current_yr_games['H_Pts']))])
            
            wins = len(h_games[h_games['H_Pts'] > h_games['V_Pts']]) + len(v_games[v_games['V_Pts'] > v_games['H_Pts']])
            losses = len(all_u_games) - wins
            h_mov = h_games['H_Pts'].mean() - h_games['V_Pts'].mean() if not h_games.empty else 0
            v_mov = v_games['V_Pts'].mean() - v_games['H_Pts'].mean() if not v_games.empty else 0
            
            def get_ppg(df, u):
                p = [r['H_Pts'] if r['H_User_Final'] == u else r['V_Pts'] for _, r in df.iterrows()]
                return sum(p)/len(p) if p else 0

            n_wins = len(champs[champs[champ_user_key].astype(str).str.strip().str.title() == user]) if champ_user_key else 0
            avg_rec = user_avg_rec.get(user, 50.0)
            
            p_score = ((h_mov + v_mov)/2 * 5) + (n_wins * 25) + (50 - avg_rec)

            stats_list.append({
                'User': user, 'Power Score': round(p_score, 1), 'Wins': wins, 'Losses': losses,
                'Avg Rec Rank': round(avg_rec, 1), 'Nattys': n_wins, 'Points Against': round(get_ppg(all_u_games, user), 1),
                'Home MOV': round(h_mov, 1), 'Away MOV': round(v_mov, 1), 'Season Wins': cy_wins
            })

            # Team History
            u_t = pd.concat([h_games[[h_team_key, yr_key]].rename(columns={h_team_key:'Team', yr_key:'Year'}), 
                             v_games[[v_team_key, yr_key]].rename(columns={v_team_key:'Team', yr_key:'Year'})])
            for t_name in u_t['Team'].unique():
                user_team_history.append({'User': user, 'Team': t_name})

        stats_df = pd.DataFrame(stats_list).sort_values(by='Power Score', ascending=False)
        p_map = stats_df.set_index('User')['Power Score'].to_dict()

        # 5. SOS & HEISMAN
        sos_map = {}
        for user in all_users:
            opps = scores[scores['H_User_Final'] == user]['V_User_Final'].tolist() + scores[scores['V_User_Final'] == user]['H_User_Final'].tolist()
            powers = [p_map.get(o, 0) for o in opps if o != 'Cpu']
            sos_map[user] = round(sum(powers)/len(powers), 1) if powers else 0

        stats_df['SOS'] = stats_df['User'].map(sos_map)
        stats_df['Heisman Points'] = (stats_df['Wins'] * 2) + (stats_df['Nattys'] * 10) + (stats_df['SOS'] / 10)
        
        return scores, rec_long, stats_df, latest_year, all_users, pd.DataFrame(user_team_history)

    except Exception as e:
        st.error(f"⚠️ Error: {e}")
        return None

# --- UI ---
data = load_data()

if data:
    scores, rec, stats, latest_year, all_users, history = data
    tabs = st.tabs(["🏆 Rankings", "📺 Season Recap", "🏅 Hall of Fame", "🎲 Vegas/H2H", "📉 Recruiting", "🏛️ History", "🏟️ Logs"])

    with tabs[0]:
        st.subheader("Leaderboard")
        st.dataframe(stats[['User', 'Power Score', 'Heisman Points', 'SOS', 'Nattys']], hide_index=True)
        st.plotly_chart(px.bar(stats, x='User', y='Power Score', color='Power Score'))

    with tabs[1]:
        st.header(f"📺 Year {latest_year} News Wrap-Up")
        top_dog = stats.sort_values('Season Wins', ascending=False).iloc[0]['User']
        sos_king = stats.sort_values('SOS', ascending=False).iloc[0]['User']
        
        st.markdown(f"""
        ### 🚨 HEADLINES
        * **DOMINANCE:** {top_dog} finished the year as the winningest user.
        * **BATTLE TESTED:** {sos_king} faced the toughest schedule in the league.
        * **RECRUITING WATCH:** {stats.sort_values('Avg Rec Rank').iloc[0]['User']} is currently building a super-team.
        """)
        st.info("💡 Tip: Update your CSVs with the latest season results and hit refresh to generate the next recap!")

    with tabs[2]:
        st.header("🏅 Hall of Fame")
        c1, c2, c3 = st.columns(3)
        c1.metric("Defensive Mastermind", stats.sort_values('Points Against').iloc[0]['User'])
        c2.metric("Recruiting Guru", stats.sort_values('Avg Rec Rank').iloc[0]['User'])
        c3.metric("Clutch Performer", stats.sort_values('Nattys', ascending=False).iloc[0]['User'])

    with tabs[3]:
        st.header("🎲 Vegas & H2H")
        f = st.selectbox("Select Favorite", all_users, index=0)
        u = st.selectbox("Select Underdog", all_users, index=1)
        if f != u:
            line = (stats[stats['User']==f]['Power Score'].values[0] - stats[stats['User']==u]['Power Score'].values[0]) / 5
            st.markdown(f"### Spread: {f} -{round(abs(line), 1)}")
            vs = scores[((scores['V_User_Final']==f)&(scores['H_User_Final']==u)) | ((scores['V_User_Final']==u)&(scores['H_User_Final']==f))]
            st.dataframe(vs, hide_index=True)

    with tabs[4]:
        st.plotly_chart(px.line(rec, x='Year', y='Rank', color='Team').update_yaxes(autorange="reversed"))

    with tabs[5]:
        sel_u = st.selectbox("Coach Profile", all_users)
        st.write(f"**Coached:** {', '.join(history[history['User']==sel_u]['Team'].unique())}")
        st.dataframe(scores[(scores['V_User_Final']==sel_u) | (scores['H_User_Final']==sel_u)], hide_index=True)

    with tabs[6]:
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
        st.dataframe(scores, hide_index=True)