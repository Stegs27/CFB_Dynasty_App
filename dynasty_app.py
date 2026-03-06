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
        stats_list, h2h_rows = [], []
        for i, user in enumerate(all_users):
            h_games = scores[scores['H_User_Final'] == user]
            v_games = scores[scores['V_User_Final'] == user]
            all_u_games = pd.concat([h_games, v_games])
            wins = len(h_games[h_games['H_Pts'] > h_games['V_Pts']]) + len(v_games[v_games['V_Pts'] > v_games['H_Pts']])
            
            conf_titles = len(v_games[(v_games['Conf Title'].str.lower() == 'yes') & (v_games['V_Pts'] > v_games['H_Pts'])]) + \
                          len(h_games[(h_games['Conf Title'].str.lower() == 'yes') & (h_games['H_Pts'] > v_games['H_Pts'])])
            
            cfp_apps = pd.concat([v_games[v_games['CFP'].str.lower() == 'yes'], h_games[h_games['CFP'].str.lower() == 'yes']])['YEAR'].nunique()

            u_draft = draft[draft['USER'] == user]
            n_sent = u_draft['Guys Sent to NFL'].iloc[0] if not u_draft.empty else 0
            n_1st = u_draft['1st Rounders'].iloc[0] if not u_draft.empty else 0
            
            hof_points = (natty_counts.get(user, 0) * 50) + (cfp_apps * 20) + (conf_titles * 15) + \
                         (coty_counts.get(user, 0) * 15) + (n_1st * 10) + (heis_counts.get(user, 0) * 10) + \
                         ((n_sent - n_1st) * 3) + (num_1_classes.get(user, 0) * 10)

            stats_list.append({
                'User': user, 'HoF Points': int(hof_points), 'Record': f"{wins}-{len(all_u_games)-wins}", 
                'NFL Guys': int(n_sent), '1st Rounders': int(n_1st), 'Natties': natty_counts.get(user, 0), 
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

        # 2041 PROJECTION
        current_2041 = ratings[ratings['YEAR'] == 2041].copy()
        current_2041['USER'] = current_2041['USER'].str.strip().str.title()
        def project_wins(row):
            w = 6 + ((row['OVERALL'] - 80) / 2.5)
            if str(row['Star Skill Guy is Generational Speed?']).strip().lower() == 'yes': w += 1.0
            fw = round(min(12, max(0, w)))
            return f"{fw}-{12-fw}"
        current_2041['2041 Projection'] = current_2041.apply(project_wins, axis=1)

        col_meta = {'yr': yr_key, 'vt': smart_col(scores, ['Visitor']), 'vs': v_score_key, 'ht': smart_col(scores, ['Home']), 'hs': h_score_key, 'cyr': champ_yr_key, 'cu': champ_user_key}
        return scores, rec_long, stats_df, pd.DataFrame(h2h_rows), all_users, years_available, col_meta, champs, current_2041
    except Exception as e:
        st.error(f"⚠️ Load Error: {e}")
        return None

# --- AI ANALYTICS ---
def get_season_recap(year, scores_df, champs_df, meta):
    yr_data = scores_df[scores_df[meta['yr']] == year]
    natty_row = champs_df[champs_df[meta['cyr']].astype(str) == str(year)]
    winner = natty_row[meta['cu']].values[0] if not natty_row.empty else "Nobody"
    
    avg_margin = round(yr_data['Margin'].mean(), 1)
    biggest_blowout = yr_data.loc[yr_data['Margin'].idxmax()]
    
    recap = f"### 🎙️ The {year} Post-Mortem\n"
    recap += f"**Champion:** {winner}\n\n"
    
    if winner != "Nobody":
        recap += f"**How they won:** {winner} survived a season where the average margin was {avg_margin}. "
        recap += f"While the rest of you were busy sniffing glue, {winner} actually remembered how to call a play.\n\n"
    
    recap += f"**The 'Should Have Stayed Home' Award:** Goes to **{biggest_blowout[meta['vt']]}** or **{biggest_blowout[meta['ht']]}** for that {int(biggest_blowout['Margin'])} point disaster. Absolute embarrassment.\n\n"
    
    trash_talk = ["If defense was a crime, most of you would be innocent.", "I've seen better clock management in a kindergarten cafeteria.", "Some of these 'Users' are clearly just CPUs in human masks."]
    recap += f"**The AI's Take:** {random.choice(trash_talk)}"
    return recap

# --- UI ---
data = load_data()
if data:
    scores, rec_long, stats, h2h_df, all_users, years, meta, champs_df, ratings_2041 = data
    tabs = st.tabs(["🏆 Prestige", "⚔️ H2H Matrix", "📺 Season Recap", "🎰 Vegas Odds", "🚀 2041 Scout & Projections", "📈 Recruiting", "📝 2041 Talent Analysis"])

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
        st.markdown(get_season_recap(sel_year, scores, champs_df, meta))
        st.dataframe(scores[scores[meta['yr']] == sel_year][[meta['vt'], meta['vs'], meta['hs'], meta['ht']]], hide_index=True)

    with tabs[4]:
        st.header("🚀 2041 Scout & Win Projections")
        scout_cols = ['USER', 'TEAM', 'OVERALL', '2041 Projection', '⭐ STAR SKILL GUY (Top OVR)', 'Star Skill Guy is Generational Speed?', 'Generational (96+ speed or 96+ Acceleration)', 'Off Speed (90+ speed)', 'Def Speed (90+ speed)']
        st.dataframe(ratings_2041[scout_cols], hide_index=True)

    with tabs[5]:
        st.header("📈 Recruiting Trends")
        sel_users = st.multiselect("Users to Compare", all_users, default=all_users[:3])
        filtered_rec = rec_long[rec_long['USER'].isin(sel_users)].dropna()
        if not filtered_rec.empty:
            fig = px.line(filtered_rec, x='Year', y='Rank', color='USER', markers=True, title="Class Rank History")
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)

    with tabs[6]:
        st.header("📝 2041 Recruiting & Talent Analysis")
        fastest_team = ratings_2041.loc[ratings_2041['Off Speed (90+ speed)'].idxmax()]
        scary_def = ratings_2041.loc[ratings_2041['Def Speed (90+ speed)'].idxmax()]
        
        st.subheader("The Speed Report")
        st.write(f"🏃 **Offensive Burners:** {fastest_team['USER']} ({fastest_team['TEAM']}) is currently leading the league with {fastest_team['Off Speed (90+ speed)']} players over 90 speed on offense. Good luck catching them in the open field.")
        st.write(f"🔒 **Defensive Lockdown:** {scary_def['USER']} ({scary_def['TEAM']}) has {scary_def['Def Speed (90+ speed)']} speedsters on defense. They are effectively erasing the perimeter.")
        
        st.subheader("Generational Talent")
        gen_players = ratings_2041[ratings_2041['Generational (96+ speed or 96+ Acceleration)'] > 0]
        for _, row in gen_players.iterrows():
            st.write(f"💎 **{row['USER']}** has **{int(row['Generational (96+ speed or 96+ Acceleration)'])}** generational freak(s) on the roster. This is the difference between a good season and a Natty.")

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()