import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import random

# --- PAGE SETUP ---
st.set_page_config(page_title="Island Dynasty HQ", layout="wide", page_icon="🏈")
st.title("🏈 Island Dynasty: Total Filth Edition")

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
        yr_key = smart_col(scores, ['YEAR', 'Year'])
        champ_user_key = smart_col(champs, ['user', 'User', 'User of team'])
        champ_yr_key = smart_col(champs, ['Year', 'YEAR'])

        # 2. DATA CLEANING
        scores['V_User_Final'] = scores[v_user_key].astype(str).str.strip().str.title()
        scores['H_User_Final'] = scores[h_user_key].astype(str).str.strip().str.title()
        scores['V_Pts'] = pd.to_numeric(scores[v_score_key], errors='coerce')
        scores['H_Pts'] = pd.to_numeric(scores[h_score_key], errors='coerce')
        scores = scores.dropna(subset=['V_Pts', 'H_Pts'])
        scores['Margin'] = (scores['H_Pts'] - scores['V_Pts']).abs()
        
        all_users = sorted([u for u in pd.concat([scores['V_User_Final'], scores['H_User_Final']]).unique() if u.upper() != 'CPU' and u != 'Nan'])
        years_available = sorted(scores[yr_key].unique(), reverse=True)

        # 3. RECRUITING & STATS
        r_team_col = rec.columns[0]
        rec_long = rec.melt(id_vars=r_team_col, var_name='Year', value_name='Rank')
        rec_long['Rank'] = pd.to_numeric(rec_long['Rank'].astype(str).str.replace(r'[*\-]', '', regex=True), errors='coerce')
        team_to_user = {}
        for _, row in scores.iterrows():
            if row['V_User_Final'] != 'Cpu': team_to_user[row[v_team_key]] = row['V_User_Final']
            if row['H_User_Final'] != 'Cpu': team_to_user[row[h_team_key]] = row['H_User_Final']
        rec_long['User_Mapped'] = rec_long[r_team_col].map(team_to_user)
        user_avg_rec = rec_long.groupby('User_Mapped')['Rank'].mean().to_dict()

        # 4. H2H & RIVALRY
        stats_list = []
        h2h_rows = []
        rivalry_list = []
        nail_biters = scores[(scores['Margin'] <= 7) & (scores['V_User_Final'] != 'Cpu') & (scores['H_User_Final'] != 'Cpu')]
        
        for i, user in enumerate(all_users):
            h_games = scores[scores['H_User_Final'] == user]
            v_games = scores[scores['V_User_Final'] == user]
            all_u_games = pd.concat([h_games, v_games])
            wins = len(h_games[h_games['H_Pts'] > h_games['V_Pts']]) + len(v_games[v_games['V_Pts'] > v_games['H_Pts']])
            n_wins = len(champs[champs[champ_user_key].astype(str).str.strip().str.title() == user]) if champ_user_key else 0
            h_mov = h_games['H_Pts'].mean() - h_games['V_Pts'].mean() if not h_games.empty else 0
            v_mov = v_games['V_Pts'].mean() - v_games['H_Pts'].mean() if not v_games.empty else 0
            avg_rec = user_avg_rec.get(user, 50.0)
            p_score = ((h_mov + v_mov)/2 * 5) + (n_wins * 25) + (50 - avg_rec)

            stats_list.append({
                'User': user, 'Power Score': round(p_score, 1), 'Overall Record': f"{wins}-{len(all_u_games)-wins}",
                'Avg Recruiting': round(avg_rec, 1), 'Nattys': n_wins, 'Home Strength': round(h_mov, 1), 'Away Strength': round(v_mov, 1)
            })

            h2h_row = {'User': user, 'OVERALL': f"{wins}-{len(all_u_games)-wins}"}
            for opp in all_users:
                if user == opp: h2h_row[opp] = "-"
                else:
                    vs = scores[((scores['V_User_Final']==user) & (scores['H_User_Final']==opp)) | 
                                ((scores['V_User_Final']==opp) & (scores['H_User_Final']==user))]
                    vw = len(vs[((vs['V_User_Final']==user) & (vs['V_Pts'] > vs['H_Pts'])) | 
                                ((vs['H_User_Final']==user) & (vs['H_Pts'] > vs['V_Pts']))])
                    h2h_row[opp] = f"{vw}-{len(vs)-vw}"
                    if i < all_users.index(opp):
                        close_count = len(nail_biters[((nail_biters['V_User_Final']==user) & (nail_biters['H_User_Final']==opp)) | 
                                                      ((nail_biters['V_User_Final']==opp) & (nail_biters['H_User_Final']==user))])
                        if close_count > 0: rivalry_list.append({'Matchup': f"{user} vs {opp}", 'Close Games': close_count})
            h2h_rows.append(h2h_row)

        stats_df = pd.DataFrame(stats_list).sort_values(by='Power Score', ascending=False)
        adj = stats_df['Power Score'] - stats_df['Power Score'].min() + 10
        stats_df['Natty Prob %'] = round((adj / adj.sum()) * 100, 1)

        col_meta = {'yr': yr_key, 'vt': v_team_key, 'vs': v_score_key, 'ht': h_team_key, 'hs': h_score_key, 'cyr': champ_yr_key, 'cu': champ_user_key}
        return scores, rec_long, stats_df, pd.DataFrame(h2h_rows), pd.DataFrame(rivalry_list), all_users, years_available, col_meta, champs

    except Exception as e:
        st.error(f"⚠️ Error: {e}")
        return None

# --- UI ---
data = load_data()
if data:
    scores, rec, stats, h2h, rivalries, all_users, years, meta, champs = data
    tabs = st.tabs(["🏆 Rankings", "⚔️ H2H Matrix", "📺 Season Recap", "🎰 Vegas Odds", "📉 Recruiting", "📜 Record Books"])

    with tabs[0]:
        st.subheader("Leaderboard")
        c1, c2 = st.columns([2,1])
        c1.dataframe(stats[['User', 'Power Score', 'Overall Record', 'Avg Recruiting', 'Natty Prob %', 'Nattys']], hide_index=True)
        c2.plotly_chart(px.pie(stats, values='Natty Prob %', names='User', hole=0.4))

    with tabs[1]:
        st.header("Head-to-Head & Rivalries")
        st.table(h2h.set_index('User'))
        if not rivalries.empty:
            st.subheader("🔥 Most Intense Matchups")
            top_riv = rivalries.sort_values('Close Games', ascending=False).head(3)
            for _, r in top_riv.iterrows():
                st.write(f"**{r['Matchup']}**: {r['Close Games']} Instant Classics")

    with tabs[2]:
        st.header("📺 Season Archives")
        sel_year = st.selectbox("Select Season", years)
        yr_scores = scores[scores[meta['yr']] == sel_year]
        natty_row = champs[champs[meta['cyr']].astype(str) == str(sel_year)]
        nat_win = natty_row[meta['cu']].values[0] if not natty_row.empty else "Nobody"
        
        # --- THE MODULAR CHAOS ENGINE ---
        # Seeded by year to ensure consistency per year but uniqueness across years
        random.seed(int(sel_year))
        
        openers = [
            f"Buckle up, because {sel_year} was a goddamn dumpster fire.",
            f"If you're looking for quality football in {sel_year}, you're in the wrong place.",
            f"The {sel_year} season archive is basically a crime scene report.",
            f"Look at {sel_year}, a year defined by broken controllers and hurt feelings.",
            f"In {sel_year}, the league reached new heights of total incompetence."
        ]
        
        champ_parts = [
            f"**{nat_win}** won the Natty, which is proof that even a blind squirrel finds a nut occasionally.",
            f"Somehow, **{nat_win}** ended up with the trophy. The rest of you should be ashamed.",
            f"**{nat_win}** sat on the throne this year, mostly because the rest of you played like garbage.",
            f"The history books say **{nat_win}** won, but we all know the league just collectively choked.",
            f"**{nat_win}** hoisted the hardware, leaving a trail of salty tears behind them."
        ]
        
        stat_roasts = [
            f"The average margin was {round(yr_scores['Margin'].mean(), 1)}. Half of you weren't even in the same zip code as your opponent.",
            f"We saw a {int(yr_scores['Margin'].max())}-point blowout. That's not a game; that's a public execution.",
            f"The scores were higher than your blood pressure, which is saying something for this group.",
            f"With {len(yr_scores)} games played, you'd think one of you would've learned to play defense.",
            f"A margin of {int(yr_scores['Margin'].max())} points? Go back to playing Minecraft, seriously."
        ]
        
        closers = [
            "What a pathetic display. Do better.",
            "I've seen more competitive games in a retirement home. F***ing disgraceful.",
            "Burn the tapes. Let's never speak of this again.",
            "If this is the best you can do, just delete the app now.",
            "Stay mad. See you in the next archive."
        ]

        st.markdown(f"### 🤖 The Unfiltered Truth of {sel_year}")
        full_story = f"{random.choice(openers)} {random.choice(champ_parts)} {random.choice(stat_roasts)} {random.choice(closers)}"
        st.error(full_story)
        st.dataframe(yr_scores[[meta['vt'], meta['vs'], meta['hs'], meta['ht']]], hide_index=True)

    with tabs[3]:
        st.header("🎰 Vegas Spreads")
        c1, c2 = st.columns(2)
        h_choice = c1.selectbox("Home", all_users, index=0)
        a_choice = c2.selectbox("Away", all_users, index=1)
        if h_choice != a_choice:
            h_data = stats[stats['User']==h_choice].iloc[0]
            a_data = stats[stats['User']==a_choice].iloc[0]
            spread = (h_data['Home Strength'] - a_data['Away Strength']) / 2
            fav = h_choice if spread > 0 else a_choice
            st.markdown(f"<h1 style='text-align: center;'>{fav} -{round(abs(spread), 1)}</h1>", unsafe_allow_html=True)

    with tabs[4]:
        st.header("📉 Recruiting Trends")
        st.plotly_chart(px.line(rec.dropna(), x='Year', y='Rank', color=rec.columns[0]).update_yaxes(autorange="reversed"))

    with tabs[5]:
        st.header("📜 Record Books")
        st.subheader("🏈 Biggest Blowouts")
        st.dataframe(scores.sort_values(by='Margin', ascending=False).head(10)[[meta['yr'], meta['vt'], meta['vs'], meta['hs'], meta['ht'], 'Margin']], hide_index=True)

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()