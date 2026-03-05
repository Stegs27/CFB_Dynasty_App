import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import random

# --- PAGE SETUP ---
st.set_page_config(page_title="Island Dynasty HQ", layout="wide", page_icon="🏈")
st.title("🏈 Island Dynasty: The No-Error HQ")

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

        # 4. H2H & RIVALRY ENGINE
        stats_list = []
        h2h_rows = []
        rivalry_data_list = []
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
                        if close_count > 0: rivalry_data_list.append({'Matchup': f"{user} vs {opp}", 'Close Games': close_count})
            h2h_rows.append(h2h_row)

        stats_df = pd.DataFrame(stats_list).sort_values(by='Power Score', ascending=False)
        adj = stats_df['Power Score'] - stats_df['Power Score'].min() + 10
        stats_df['Natty Prob %'] = round((adj / adj.sum()) * 100, 1)

        col_meta = {'yr': yr_key, 'vt': v_team_key, 'vs': v_score_key, 'ht': h_team_key, 'hs': h_score_key, 'cyr': champ_yr_key, 'cu': champ_user_key}
        return scores, rec_long, stats_df, pd.DataFrame(h2h_rows), pd.DataFrame(rivalry_data_list), all_users, years_available, col_meta, champs

    except Exception as e:
        st.error(f"⚠️ Error loading data: {e}")
        return None

# --- UI EXECUTION ---
data_bundle = load_data()
if data_bundle:
    scores, rec, stats, h2h_df, rivalry_df, all_users, years, meta, champs_df = data_bundle
    tabs = st.tabs(["🏆 Rankings", "⚔️ H2H Matrix", "📺 Season Recap", "🎰 Vegas Odds", "📉 Recruiting", "📜 Record Books"])

    with tabs[0]:
        st.subheader("Leaderboard")
        c1, c2 = st.columns([2,1])
        c1.dataframe(stats[['User', 'Power Score', 'Overall Record', 'Avg Recruiting', 'Natty Prob %', 'Nattys']], hide_index=True)
        c2.plotly_chart(px.pie(stats, values='Natty Prob %', names='User', hole=0.4))

    with tabs[1]:
        st.header("Head-to-Head & Rivalries")
        st.table(h2h_df.set_index('User'))
        if not rivalry_df.empty:
            st.subheader("🔥 Most Intense Matchups")
            top_riv = rivalry_df.sort_values('Close Games', ascending=False).head(3)
            for _, r in top_riv.iterrows():
                st.write(f"**{r['Matchup']}**: {r['Close Games']} Instant Classics")

    with tabs[2]:
        st.header("📺 Season Archives")
        sel_year = st.selectbox("Select Season", years)
        yr_scores = scores[scores[meta['yr']] == sel_year]
        natty_row = champs_df[champs_df[meta['cyr']].astype(str) == str(sel_year)]
        nat_win = natty_row[meta['cu']].values[0] if not natty_row.empty else "Nobody"
        
        # --- THE INFINITE PROFANITY ENGINE ---
        random.seed(int(sel_year) * 123)
        o = ["Listen up, fuckers. {Y} was a goddamn catastrophe.", "Holy fuck, {Y} was a dark time for this league.", "You call {Y} football? I call it a collective mental breakdown.", "If {Y} was a movie, it would be a fucking snuff film.", "Another year, {Y}, another bunch of you losers failing at life."]
        c = ["**{W}** took the Natty, mostly because the rest of you play like toddlers.", "**{W}** is the King of {Y}, while you lot are just the fucking court jesters.", "Somehow **{W}** won it all. The bar is officially on the fucking floor.", "**{W}** hoisted the trophy, probably while laughing at your pathetic schemes.", "Enjoy the throne, **{W}**, you’re ruling over a kingdom of fucking idiots."]
        s = ["The average margin was {AM}. Fucking embarrassing.", "A {MM}-point blowout? That’s not a loss, that’s a hate crime.", "Scores were high, but the IQ in the room was clearly sub-zero.", "Imagine losing by {MM} points and still acting like you know ball.", "Average margin was {AM}. It’s like some of you weren’t even holding the controller."]
        f = ["Fuck off and get better.", "This was a goddamn disgrace.", "I’m losing brain cells just reading these scores.", "Absolutely pathetic. Every single one of you.", "Get the fuck out of my sight."]
        
        full_story = f"{random.choice(o).format(Y=sel_year)} {random.choice(c).format(W=nat_win, Y=sel_year)} {random.choice(s).format(AM=round(yr_scores['Margin'].mean(),1), MM=int(yr_scores['Margin'].max()))} {random.choice(f)}"
        st.error(full_story)

        # --- DYNAMIC INTERVIEW ---
        st.markdown("---")
        st.subheader(f"🎤 Post-Game Presser: Coach {nat_win}")
        
        qs = ["Reporter: How do you respond to the 'luck' allegations?", "Reporter: What do you have to say to the users you blew out?", "Reporter: Is there anyone in this league that can actually challenge you?", "Reporter: How does it feel to be the only person here who doesn't suck?"]
        ans = [
            f"Coach {nat_win}: Luck? I worked my fucking ass off while these losers were playing with themselves. It's called talent, look it up.",
            f"Coach {nat_win}: To the people I beat? Get a new hobby. Maybe try knitting. You're fucking terrible at football.",
            f"Coach {nat_win}: Honestly, it’s boring at the top when the rest of the league is this f***ing pathetic. I need a real opponent.",
            f"Coach {nat_win}: I see the stats. I see the scores. I'm the only one here who knows how a fucking controller works. Cry about it.",
            f"Coach {nat_win}: Next question. I don't have time to explain basic strategy to a bunch of fucking amateurs."
        ]
        st.info(f"*{random.choice(qs)}*\n\n**{random.choice(ans)}**")
        st.markdown("---")
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
            st.markdown(f"<h1 style='text-align: center;'>{h_choice if spread > 0 else a_choice} -{round(abs(spread), 1)}</h1>", unsafe_allow_html=True)

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