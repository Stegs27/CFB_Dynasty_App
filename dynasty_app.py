import streamlit as st
import pandas as pd
import plotly.express as px

# --- PAGE SETUP ---
st.set_page_config(page_title="Island Dynasty HQ", layout="wide", page_icon="🏈")
st.title("🏈 Island Dynasty: The Final Form")

def smart_col(df, target_names):
    for target in target_names:
        for col in df.columns:
            if col.strip().lower() == target.lower():
                return col
    return None

# --- DATA LOADING ---
@st.cache_data
def load_data():
    try:
        scores = pd.read_csv('scores.csv')
        rec = pd.read_csv('recruiting.csv')
        champs = pd.read_csv('champs.csv')

        # 1. IDENTIFY COLUMNS
        v_user_key = smart_col(scores, ['Vis_User', 'Visitor User', 'Vis User'])
        h_user_key = smart_col(scores, ['Home_User', 'Home User'])
        v_score_key = smart_col(scores, ['Vis Score', 'Vis_Score'])
        h_score_key = smart_col(scores, ['Home Score', 'Home_Score'])
        v_team_key = smart_col(scores, ['Visitor', 'Vis Team'])
        h_team_key = smart_col(scores, ['Home', 'Home Team'])
        cfp_key = smart_col(scores, ['CFP'])
        champ_user_key = smart_col(champs, ['user', 'User', 'User of team'])

        # 2. CLEAN SCORES
        scores['V_User_Final'] = scores[v_user_key].astype(str).str.strip().str.title()
        scores['H_User_Final'] = scores[h_user_key].astype(str).str.strip().str.title()
        scores['V_Pts'] = pd.to_numeric(scores[v_score_key], errors='coerce')
        scores['H_Pts'] = pd.to_numeric(scores[h_score_key], errors='coerce')
        scores = scores.dropna(subset=['V_Pts', 'H_Pts'])
        scores['Margin'] = (scores['H_Pts'] - scores['V_Pts']).abs()
        scores['Total_Pts'] = scores['H_Pts'] + scores['V_Pts']

        all_users = sorted([u for u in pd.concat([scores['V_User_Final'], scores['H_User_Final']]).unique() if u.upper() != 'CPU' and u != 'Nan'])

        # 3. RECRUITING & USER MAPPING
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

        for user in all_users:
            h_games = scores[scores['H_User_Final'] == user]
            v_games = scores[scores['V_User_Final'] == user]
            all_u_games = pd.concat([h_games, v_games])
            
            h_mov = h_games['H_Pts'].mean() - h_games['V_Pts'].mean() if not h_games.empty else 0
            v_mov = v_games['V_Pts'].mean() - v_games['H_Pts'].mean() if not v_games.empty else 0
            
            reg_games = all_u_games[all_u_games[cfp_key].astype(str).str.lower() != 'yes']
            cfp_games = all_u_games[all_u_games[cfp_key].astype(str).str.lower() == 'yes']
            
            def get_avg_pts(df, u):
                p = [r['H_Pts'] if r['H_User_Final'] == u else r['V_Pts'] for _, r in df.iterrows()]
                return sum(p)/len(p) if p else 0

            reg_ppg, cfp_ppg = get_avg_pts(reg_games, user), get_avg_pts(cfp_games, user)
            n_wins = len(champs[champs[champ_user_key].astype(str).str.strip().str.title() == user]) if champ_user_key else 0
            avg_rec = user_avg_rec.get(user, 50.0)
            
            p_score = (((h_mov + v_mov)/2) * 5) + (n_wins * 25) + (50 - avg_rec)

            stats_list.append({
                'User': user,
                'Power Score': round(p_score, 1),
                'Avg Rec Rank': round(avg_rec, 1),
                'Nattys': n_wins,
                'Clutch Factor': round(cfp_ppg - reg_ppg, 1),
                'Home MOV': round(h_mov, 1),
                'Away MOV': round(v_mov, 1)
            })

            h2h_row = {'User': user}
            tw, tl = 0, 0
            for opp in all_users:
                if user == opp: h2h_row[f"vs {opp}"] = "-"
                else:
                    vs = scores[((scores['V_User_Final'] == user) & (scores['H_User_Final'] == opp)) | 
                                ((scores['V_User_Final'] == opp) & (scores['H_User_Final'] == user))]
                    vw, vl = 0, 0
                    for _, g in vs.iterrows():
                        is_h = g['H_User_Final'] == user
                        if (is_h and g['H_Pts'] > g['V_Pts']) or (not is_h and g['V_Pts'] > g['H_Pts']): 
                            vw += 1; tw += 1
                        else: vl += 1; tl += 1
                    h2h_row[f"vs {opp}"] = f"{vw}-{vl}"
            h2h_row['OVERALL'] = f"{tw}-{tl}"
            h2h_rows.append(h2h_row)

        stats_df = pd.DataFrame(stats_list).sort_values(by='Power Score', ascending=False)
        
        # 5. NATTY PROBABILITY LOGIC
        # Ensure non-negative probability scores
        min_p = stats_df['Power Score'].min()
        adj_score = stats_df['Power Score'] - min_p + 10
        total_p = adj_score.sum()
        stats_df['Natty Prob %'] = round((adj_score / total_p) * 100, 1)

        # 6. UPSET CALCULATOR
        upsets = []
        p_map = stats_df.set_index('User')['Power Score'].to_dict()
        for _, row in scores.iterrows():
            v, h = row['V_User_Final'], row['H_User_Final']
            if v in p_map and h in p_map:
                if row['V_Pts'] > row['H_Pts'] and (p_map[h] - p_map[v]) > 15: upsets.append(row)
                elif row['H_Pts'] > row['V_Pts'] and (p_map[v] - p_map[h]) > 15: upsets.append(row)

        return scores, rec_long, stats_df, pd.DataFrame(h2h_rows), pd.DataFrame(upsets), all_users

    except Exception as e:
        st.error(f"⚠️ Error: {e}")
        return None

# --- RUN APP ---
data = load_data()

if data:
    scores, rec, stats, h2h, upsets, all_users = data
    tabs = st.tabs(["🏆 Rankings", "⚔️ H2H Matrix", "📈 Recruiting", "🎰 Vegas Odds", "📜 Records", "🏟️ Logs"])

    with tabs[0]:
        st.subheader("The Dynasty Leaderboard")
        st.dataframe(stats[['User', 'Power Score', 'Natty Prob %', 'Avg Rec Rank', 'Nattys', 'Clutch Factor']], hide_index=True, use_container_width=True)
        st.plotly_chart(px.pie(stats, values='Natty Prob %', names='User', title="Projected Championship Probability", hole=0.4))

    with tabs[1]:
        st.header("The User Rivalry Grid")
        st.table(h2h.set_index('User'))

    with tabs[2]:
        st.header("Recruiting History")
        st.subheader("Average Career Rank by User")
        st.dataframe(stats[['User', 'Avg Rec Rank']].sort_values(by='Avg Rec Rank'), hide_index=True)
        sel = st.multiselect("Compare Team Trends", rec['Team'].unique(), default=rec['Team'].unique()[:3])
        if sel:
            fig = px.line(rec[rec['Team'].isin(sel)], x='Year', y='Rank', color='Team', markers=True)
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)

    with tabs[3]:
        st.header("🎰 Vegas Spreads")
        c1, c2 = st.columns(2)
        f = c1.selectbox("Favorite", all_users, index=0)
        u = c2.selectbox("Underdog", all_users, index=1)
        if f != u:
            fav_mov = stats[stats['User'] == f]['Home MOV'].values[0]
            und_mov = stats[stats['User'] == u]['Away MOV'].values[0]
            line = fav_mov - und_mov
            st.markdown(f"<h1 style='text-align: center;'>{f} -{round(max(0.5, line), 1)}</h1>", unsafe_allow_html=True)

    with tabs[4]:
        st.header("Record Books")
        st.subheader("🚨 Major Upsets")
        st.dataframe(upsets, hide_index=True)
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🏆 Biggest Blowouts")
            st.table(scores.sort_values(by='Margin', ascending=False).head(5)[['Visitor', 'V_Pts', 'H_Pts', 'Home', 'Margin']])
        with c2:
            st.subheader("🏠 Home Field Advantage (HFA)")
            stats['HFA'] = stats['Home MOV'] - stats['Away MOV']
            st.dataframe(stats[['User', 'HFA']].sort_values(by='HFA', ascending=False), hide_index=True)

    with tabs[5]:
        st.header("Game Logs & Settings")
        if st.button("🔄 Refresh Data (Clear Cache)"):
            st.cache_data.clear()
            st.rerun()
        st.dataframe(scores, hide_index=True)