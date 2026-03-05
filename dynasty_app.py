import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- PAGE SETUP ---
st.set_page_config(page_title="Island Dynasty HQ", layout="wide", page_icon="🏈")
st.title("🏈 Island Dynasty: The Grand Slam Edition")

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

        # 4. STATS ENGINE
        stats_list = []
        h2h_rows = []
        user_team_history = []
        latest_year = scores[yr_key].max()

        for user in all_users:
            h_games = scores[scores['H_User_Final'] == user]
            v_games = scores[scores['V_User_Final'] == user]
            all_u_games = pd.concat([h_games, v_games])
            
            wins = len(h_games[h_games['H_Pts'] > h_games['V_Pts']]) + len(v_games[v_games['V_Pts'] > v_games['H_Pts']])
            losses = len(all_u_games) - wins
            h_mov = h_games['H_Pts'].mean() - h_games['V_Pts'].mean() if not h_games.empty else 0
            v_mov = v_games['V_Pts'].mean() - v_games['H_Pts'].mean() if not v_games.empty else 0
            
            n_wins = len(champs[champs[champ_user_key].astype(str).str.strip().str.title() == user]) if champ_user_key else 0
            avg_rec = user_avg_rec.get(user, 50.0)
            
            p_score = ((h_mov + v_mov)/2 * 5) + (n_wins * 25) + (50 - avg_rec)

            stats_list.append({
                'User': user, 'Power Score': round(p_score, 1), 'Wins': wins, 'Losses': losses,
                'Avg Rec Rank': round(avg_rec, 1), 'Nattys': n_wins,
                'Home Strength': round(h_mov, 1), 'Away Strength': round(v_mov, 1)
            })

            h2h_row = {'User': user}
            for opp in all_users:
                if user == opp: h2h_row[opp] = "-"
                else:
                    vs = scores[((scores['V_User_Final']==user) & (scores['H_User_Final']==opp)) | 
                                ((scores['V_User_Final']==opp) & (scores['H_User_Final']==user))]
                    vw = len(vs[((vs['V_User_Final']==user) & (vs['V_Pts'] > vs['H_Pts'])) | 
                                ((vs['H_User_Final']==user) & (vs['H_Pts'] > vs['V_Pts']))])
                    vl = len(vs) - vw
                    h2h_row[opp] = f"{vw}-{vl}"
            h2h_rows.append(h2h_row)

            u_t = pd.concat([h_games[[h_team_key]].rename(columns={h_team_key:'T'}), v_games[[v_team_key]].rename(columns={v_team_key:'T'})])
            for t_name in u_t['T'].unique(): user_team_history.append({'User': user, 'Team': t_name})

        stats_df = pd.DataFrame(stats_list).sort_values(by='Power Score', ascending=False)
        p_map = stats_df.set_index('User')['Power Score'].to_dict()
        
        # 5. NATTY PROB & UPSETS
        adj = stats_df['Power Score'] - stats_df['Power Score'].min() + 10
        stats_df['Natty Prob %'] = round((adj / adj.sum()) * 100, 1)

        upsets = []
        for _, r in scores.iterrows():
            v, h = r['V_User_Final'], r['H_User_Final']
            if v in p_map and h in p_map:
                if r['V_Pts'] > r['H_Pts'] and (p_map[h] - p_map[v]) > 15: upsets.append(r)
                elif r['H_Pts'] > r['V_Pts'] and (p_map[v] - p_map[h]) > 15: upsets.append(r)

        # 6. PACKAGE FOR UI
        col_meta = {'yr': yr_key, 'vt': v_team_key, 'vs': v_score_key, 'ht': h_team_key, 'hs': h_score_key}

        return scores, rec_long, stats_df, pd.DataFrame(h2h_rows), pd.DataFrame(upsets), all_users, pd.DataFrame(user_team_history), latest_year, col_meta

    except Exception as e:
        st.error(f"⚠️ Error: {e}")
        return None

# --- UI ---
data = load_data()

if data:
    scores, rec, stats, h2h, upsets, all_users, history, latest_year, meta = data
    tabs = st.tabs(["🏆 Rankings", "⚔️ H2H Matrix", "📺 Season Recap", "🎰 Vegas Odds", "📉 Recruiting", "🏛️ History", "📜 Record Books", "🏟️ Logs"])

    with tabs[0]:
        st.subheader("Current Dynasty Standing")
        c1, c2 = st.columns([2,1])
        c1.dataframe(stats[['User', 'Power Score', 'Natty Prob %', 'Nattys', 'Wins', 'Losses']], hide_index=True)
        c2.plotly_chart(px.pie(stats, values='Natty Prob %', names='User', hole=0.4, title="Championship Probability"))

    with tabs[1]:
        st.header("Head-to-Head Matrix")
        st.table(h2h.set_index('User'))

    with tabs[2]:
        st.header(f"📺 Year {latest_year} Wrap-Up")
        st.info(f"The top coach this season is {stats.iloc[0]['User']}. Check back after the next set of scores are uploaded!")

    with tabs[3]:
        st.header("🎰 Interactive Vegas Spreads")
        c1, c2 = st.columns(2)
        h_choice = c1.selectbox("Home Venue", all_users, index=0)
        a_choice = c2.selectbox("Visiting Team", all_users, index=1)
        if h_choice != a_choice:
            h_stat = stats[stats['User'] == h_choice].iloc[0]
            a_stat = stats[stats['User'] == a_choice].iloc[0]
            spread = (h_stat['Home Strength'] - a_stat['Away Strength']) / 2
            fav = h_choice if spread > 0 else a_choice
            st.markdown(f"<h1 style='text-align: center;'>{fav} -{round(abs(spread), 1)}</h1>", unsafe_allow_html=True)

    with tabs[4]:
        st.plotly_chart(px.line(rec, x='Year', y='Rank', color='Team').update_yaxes(autorange="reversed"))

    with tabs[5]:
        sel_u = st.selectbox("View Coach Profile", all_users)
        st.write(f"**Coached:** {', '.join(history[history['User']==sel_u]['Team'].unique())}")
        st.dataframe(scores[(scores['V_User_Final']==sel_u) | (scores['H_User_Final']==sel_u)], hide_index=True)

    with tabs[6]:
        st.header("📜 Dynasty Record Books")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🚨 All-Time Upsets")
            if not upsets.empty:
                st.dataframe(upsets[[meta['yr'], meta['vt'], meta['vs'], meta['hs'], meta['ht']]], hide_index=True)
            else:
                st.write("No major upsets recorded yet.")
        with c2:
            st.subheader("🏈 Biggest Blowouts")
            st.dataframe(scores.sort_values(by='Margin', ascending=False).head(10)[[meta['yr'], meta['vt'], meta['vs'], meta['hs'], meta['ht'], 'Margin']], hide_index=True)

    with tabs[7]:
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
        st.dataframe(scores, hide_index=True)