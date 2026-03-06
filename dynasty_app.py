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
        # 1. CORE FILES
        scores = pd.read_csv('scores.csv')
        rec = pd.read_csv('recruiting.csv')
        champs = pd.read_csv('champs.csv')
        
        # 2. PRESTIGE & SCOUTING FILES
        draft = pd.read_csv('UserDraftPicks.csv')
        ratings = pd.read_csv('TeamRatingsHistory.csv')
        heisman = pd.read_csv('Heisman_History.csv')
        coty = pd.read_csv('COTY.csv')

        # STANDARDIZE COLUMN KEYS
        v_user_key = smart_col(scores, ['Vis_User', 'Visitor User', 'Vis User'])
        h_user_key = smart_col(scores, ['Home_User', 'Home User'])
        v_score_key = smart_col(scores, ['Vis Score', 'Vis_Score'])
        h_score_key = smart_col(scores, ['Home Score', 'Home_Score'])
        v_team_key = smart_col(scores, ['Visitor', 'Vis Team'])
        h_team_key = smart_col(scores, ['Home', 'Home Team'])
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

        # RECRUITING RECONSTRUCTION
        non_year_cols = [c for c in rec.columns if not str(c).strip().isdigit()]
        rec_long = rec.melt(id_vars=non_year_cols, var_name='Year', value_name='Rank')
        rec_long['Rank'] = rec_long['Rank'].astype(str).str.replace(r'[*\-]', '', regex=True).replace('nan', np.nan)
        rec_long['Rank'] = pd.to_numeric(rec_long['Rank'], errors='coerce')
        
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
        stats_list, h2h_rows, rivalry_data_list = [], [], []
        nail_biters = scores[(scores['Margin'] <= 7) & (scores['V_User_Final'] != 'Cpu') & (scores['H_User_Final'] != 'Cpu')]
        
        for i, user in enumerate(all_users):
            h_games = scores[scores['H_User_Final'] == user]
            v_games = scores[scores['V_User_Final'] == user]
            all_u_games = pd.concat([h_games, v_games])
            wins = len(h_games[h_games['H_Pts'] > h_games['V_Pts']]) + len(v_games[v_games['V_Pts'] > v_games['H_Pts']])
            
            # FIXED LOGIC: Compare columns within the same dataframe subset
            conf_titles = len(v_games[(v_games['Conf Title'].str.lower() == 'yes') & (v_games['V_Pts'] > v_games['H_Pts'])]) + \
                          len(h_games[(h_games['Conf Title'].str.lower() == 'yes') & (h_games['H_Pts'] > h_games['V_Pts'])])
            
            cfp_apps = pd.concat([v_games[v_games['CFP'].str.lower() == 'yes'], h_games[h_games['CFP'].str.lower() == 'yes']])['YEAR'].nunique()

            # Draft stats
            u_draft = draft[draft['USER'] == user]
            n_sent = u_draft['Guys Sent to NFL'].iloc[0] if not u_draft.empty else 0
            n_1st = u_draft['1st Rounders'].iloc[0] if not u_draft.empty else 0
            
            n_natties = natty_counts.get(user, 0)
            n_heis = heis_counts.get(user, 0)
            n_coty = coty_counts.get(user, 0)
            n_top_rec = num_1_classes.get(user, 0)
            avg_rec = user_avg_rec.get(user, 50.0)

            # HoF POINT CALCULATION
            hof_points = (n_natties * 50) + (cfp_apps * 20) + (conf_titles * 15) + \
                         (n_coty * 15) + (n_1st * 10) + (n_heis * 10) + \
                         ((n_sent - n_1st) * 3) + (n_top_rec * 10)

            h_mov = h_games['H_Pts'].mean() - h_games['V_Pts'].mean() if not h_games.empty else 0
            v_mov = v_games['V_Pts'].mean() - v_games['H_Pts'].mean() if not v_games.empty else 0
            
            stats_list.append({
                'User': user, 'HoF Points': int(hof_points), 'Record': f"{wins}-{len(all_u_games)-wins}", 
                'NFL Guys': int(n_sent), '1st Rounders': int(n_1st), 'Natties': n_natties, 'CFP Apps': cfp_apps, 
                'Avg Recruiting': round(avg_rec, 1), 'Home Strength': round(h_mov, 1), 'Away Strength': round(v_mov, 1)
            })
            
            # H2H Matrix
            h2h_row = {'User': user, 'OVERALL': f"{wins}-{len(all_u_games)-wins}"}
            for opp in all_users:
                if user == opp: h2h_row[opp] = "-"
                else:
                    vs = scores[((scores['V_User_Final']==user) & (scores['H_User_Final']==opp)) | ((scores['V_User_Final']==opp) & (scores['H_User_Final']==user))]
                    vw = len(vs[((vs['V_User_Final']==user) & (vs['V_Pts'] > vs['H_Pts'])) | ((vs['H_User_Final']==user) & (vs['H_Pts'] > vs['V_Pts']))])
                    h2h_row[opp] = f"{vw}-{len(vs)-vw}"
                    if i < all_users.index(opp):
                        close = len(nail_biters[((nail_biters['V_User_Final']==user) & (nail_biters['H_User_Final']==opp)) | ((nail_biters['V_User_Final']==opp) & (nail_biters['H_User_Final']==user))])
                        if close > 0: rivalry_data_list.append({'Matchup': f"{user} vs {opp}", 'Close Games': close})
            h2h_rows.append(h2h_row)

        stats_df = pd.DataFrame(stats_list).sort_values(by='HoF Points', ascending=False)
        adj = stats_df['HoF Points'] - stats_df['HoF Points'].min() + 10
        stats_df['Prestige %'] = round((adj / adj.sum()) * 100, 1)

        # 2041 PROJECTION LOGIC
        current_2041 = ratings[ratings['YEAR'] == 2041].copy()
        current_2041['USER'] = current_2041['USER'].str.strip().str.title()
        
        def project_wins(row):
            w = 6 + ((row['OVERALL'] - 80) / 2.5)
            if str(row['Star Skill Guy is Generational Speed?']).strip().lower() == 'yes': w += 1.0
            if row['Off Speed (90+ speed)'] > 8: w += 0.5
            if row['Def Speed (90+ speed)'] > 8: w += 0.5
            fw = round(min(12, max(0, w)))
            return f"{fw}-{12-fw}"
        
        current_2041['2041 Projection'] = current_2041.apply(project_wins, axis=1)

        col_meta = {'yr': yr_key, 'vt': v_team_key, 'vs': v_score_key, 'ht': h_team_key, 'hs': h_score_key, 'cyr': champ_yr_key, 'cu': champ_user_key}
        return scores, rec_long, stats_df, pd.DataFrame(h2h_rows), pd.DataFrame(rivalry_data_list), all_users, years_available, col_meta, champs, current_2041
    except Exception as e:
        st.error(f"⚠️ Load Error: {e}")
        return None

# --- UI EXECUTION ---
data_bundle = load_data()
if data_bundle:
    scores, rec_long, stats, h2h_df, rivalry_df, all_users, years, meta, champs_df, ratings_2041 = data_bundle
    tabs = st.tabs(["🏆 Prestige", "⚔️ H2H Matrix", "📺 Season Recap", "🎰 Vegas Odds", "🚀 2041 Scout & Projections", "📈 Recruiting", "📜 Records"])

    with tabs[0]:
        st.subheader("The Dynasty Hall of Fame")
        c1, c2 = st.columns([2.5,1])
        # Visible NFL Data
        c1.dataframe(stats[['User', 'HoF Points', 'Record', 'NFL Guys', '1st Rounders', 'Natties', 'CFP Apps', 'Avg Recruiting']], hide_index=True)
        c2.plotly_chart(px.pie(stats, values='Prestige %', names='User', hole=0.4, title="Legacy Share"))

    with tabs[1]:
        st.header("Head-to-Head & Rivalries")
        st.table(h2h_df.set_index('User'))
        if not rivalry_df.empty:
            st.subheader("🔥 Most Intense Matchups")
            top_riv = rivalry_df.sort_values('Close Games', ascending=False).head(3)
            for _, r in top_riv.iterrows(): st.write(f"**{r['Matchup']}**: {r['Close Games']} Instant Classics")

    with tabs[4]:
        st.header("🚀 2041 Talent Profile")
        # Visible Generational Status and Team Speed metrics
        scout_cols = [
            'USER', 'TEAM', 'OVERALL', '2041 Projection', 
            '⭐ STAR SKILL GUY (Top OVR)', 'Star Skill Guy is Generational Speed?', 
            'Off Speed (90+ speed)', 'Def Speed (90+ speed)', 'Game Breakers (90+ Speed & 90+ Acceleration)'
        ]
        st.dataframe(ratings_2041[scout_cols], hide_index=True)
        st.plotly_chart(px.scatter(ratings_2041, x='OVERALL', y='Game Breakers (90+ Speed & 90+ Acceleration)', text='USER', size='OFFENSE', title="Explosiveness Profile"))

    with tabs[5]:
        st.header("📈 Recruiting Trends")
        # IMPROVED: User selection to make the graph readable
        sel_users = st.multiselect("Filter Users to Compare", all_users, default=all_users[:3])
        filtered_rec = rec_long[rec_long['USER'].isin(sel_users)].dropna()
        if not filtered_rec.empty:
            fig = px.line(filtered_rec, x='Year', y='Rank', color='USER', markers=True, 
                          title="Class Rank History (Lower is Better)")
            fig.update_yaxes(autorange="reversed") # Standard for ranks
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Select users to compare recruiting performance.")

    with tabs[2]:
        st.header("📺 Season Archives")
        sel_year = st.selectbox("Select Season", years)
        yr_scores = scores[scores[meta['yr']] == sel_year]
        st.dataframe(yr_scores[[meta['vt'], meta['vs'], meta['hs'], meta['ht']]], hide_index=True)

    with tabs[3]:
        st.header("🎰 Vegas Spreads")
        c1, c2 = st.columns(2)
        h_choice = c1.selectbox("Home", all_users, index=0)
        a_choice = c2.selectbox("Away", all_users, index=1)
        if h_choice != a_choice:
            h_data, a_data = stats[stats['User']==h_choice].iloc[0], stats[stats['User']==a_choice].iloc[0]
            spread = (h_data['Home Strength'] - a_data['Away Strength']) / 2
            st.markdown(f"<h1 style='text-align: center;'>{h_choice if spread > 0 else a_choice} -{round(abs(spread), 1)}</h1>", unsafe_allow_html=True)

    with tabs[6]:
        st.header("📜 Record Books")
        st.subheader("🏈 Biggest Blowouts")
        st.dataframe(scores.sort_values(by='Margin', ascending=False).head(10)[[meta['yr'], meta['vt'], meta['vs'], meta['hs'], meta['ht'], 'Margin']], hide_index=True)

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()