import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import random

# --- PAGE SETUP ---
st.set_page_config(page_title="Island Dynasty HQ", layout="wide", page_icon="🏈")
st.title("🏈 Island Dynasty: Prestige & Projections")

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
        
        # 2. PRESTIGE FILES (New Today)
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

        # PRESTIGE & HOF CALCULATIONS
        # Draft Points
        draft.columns = [c.strip() for c in draft.columns]
        draft['USER'] = draft['USER'].str.strip().str.title()
        
        # Heisman Points
        heis_counts = heisman['USER'].str.strip().str.title().value_counts().to_dict()
        
        # COTY Points
        coty_counts = coty[coty['User'].str.upper() != 'CPU']['User'].str.strip().str.title().value_counts().to_dict()
        
        # Natties
        natty_counts = champs[champs[champ_user_key].str.upper() != 'CPU'][champ_user_key].str.strip().str.title().value_counts().to_dict()

        # Recruiting #1 Classes
        year_cols = [c for c in rec.columns if c.isdigit()]
        rec_long = rec.melt(id_vars=rec.columns[0], var_name='Year', value_name='Rank')
        rec_long['Rank'] = pd.to_numeric(rec_long['Rank'].astype(str).str.replace(r'[*\-]', '', regex=True), errors='coerce')
        num_1_classes = rec_long[rec_long['Rank'] == 1].groupby(rec.columns[0]).size().to_dict()

        # RECRUITING MAPPING
        team_to_user = {row[v_team_key]: row['V_User_Final'] for _, row in scores.iterrows() if row['V_User_Final'] != 'Cpu'}
        team_to_user.update({row[h_team_key]: row['H_User_Final'] for _, row in scores.iterrows() if row['H_User_Final'] != 'Cpu'})
        rec_long['User_Mapped'] = rec_long[rec.columns[0]].map(team_to_user)
        user_avg_rec = rec_long.groupby('User_Mapped')['Rank'].mean().to_dict()

        # MASTER STATS LOOP
        stats_list, h2h_rows, rivalry_data_list = [], [], []
        nail_biters = scores[(scores['Margin'] <= 7) & (scores['V_User_Final'] != 'Cpu') & (scores['H_User_Final'] != 'Cpu')]
        
        for i, user in enumerate(all_users):
            h_games = scores[scores['H_User_Final'] == user]
            v_games = scores[scores['V_User_Final'] == user]
            all_u_games = pd.concat([h_games, v_games])
            wins = len(h_games[h_games['H_Pts'] > h_games['V_Pts']]) + len(v_games[v_games['V_Pts'] > v_games['H_Pts']])
            
            # CFP & Conf Titles from Scores
            conf_titles = len(v_games[(v_games['Conf Title'].str.lower() == 'yes') & (v_games['V_Pts'] > v_games['H_Pts'])]) + \
                          len(h_games[(h_games['Conf Title'].str.lower() == 'yes') & (h_games['H_Pts'] > h_games['V_Pts'])])
            cfp_apps = pd.concat([v_games[v_games['CFP'].str.lower() == 'yes'], h_games[h_games['CFP'].str.lower() == 'yes']])['YEAR'].nunique()

            # Draft data
            u_draft = draft[draft['USER'] == user]
            n_sent = u_draft['Guys Sent to NFL'].iloc[0] if not u_draft.empty else 0
            n_1st = u_draft['1st Rounders'].iloc[0] if not u_draft.empty else 0
            
            # Aggregate Prestige
            n_natties = natty_counts.get(user, 0)
            n_heis = heis_counts.get(user, 0)
            n_coty = coty_counts.get(user, 0)
            n_top_rec = num_1_classes.get(user, 0)
            avg_rec = user_avg_rec.get(user, 50.0)

            # HOll OF FAME POINTS FORMULA
            hof_points = (n_natties * 50) + (cfp_apps * 20) + (conf_titles * 15) + \
                         (n_coty * 15) + (n_1st * 10) + (n_heis * 10) + \
                         ((n_sent - n_1st) * 3) + (n_top_rec * 10)

            h_mov = h_games['H_Pts'].mean() - h_games['V_Pts'].mean() if not h_games.empty else 0
            v_mov = v_games['V_Pts'].mean() - v_games['H_Pts'].mean() if not v_games.empty else 0
            p_score = ((h_mov + v_mov)/2 * 5) + (n_natties * 25) + (50 - avg_rec)

            stats_list.append({
                'User': user, 'HoF Points': int(hof_points), 'Power Score': round(p_score, 1), 
                'Overall Record': f"{wins}-{len(all_u_games)-wins}", 'Avg Recruiting': round(avg_rec, 1), 
                'Natties': n_natties, 'CFP Apps': cfp_apps, '1st Rounders': n_1st, 'Home Strength': round(h_mov, 1), 'Away Strength': round(v_mov, 1)
            })
            
            # H2H Matrix Logic
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
            if row['Star Skill Guy is Generational Speed?'] == 'Yes': w += 1.0
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

def procedural_writeup(year, champion, avg_m, max_m):
    random.seed(int(year) * 111)
    intro = ["Listen here you little shits.", "Year {Y} was a goddamn travesty.", "Welcome to the absolute shit-show of {Y}.", "Looking at {Y} makes me want to delete my own code.", "This year was a massive fucking dumpster fire."]
    natty_news = [f"**{champion}** won the Natty, likely because the rest of you are lobotomized.", f"Against all logic, **{champion}** ended up on top of this trash heap.", f"**{champion}** took the hardware home while the rest of you choked on your own incompetence.", f"History records **{champion}** as the winner, but we all know it was a fluke in a league of losers."]
    stat_burn = [f"An average margin of {avg_m}? You guys play defense like a bunch of blind toddlers.", f"Someone actually lost by {max_m} points. How do you even look at yourself in the mirror?", f"With a {avg_m} point margin, it’s clear most of you were playing with one hand on your dicks.", f"A {max_m} point blowout proves half this league belongs in a retirement home."]
    sign_off = ["Fuck off and try harder next time.", "Get out of my face.", "Delete your accounts.", "Pathetic fucking display.", "I'm embarrassed to know you."]
    return f"{random.choice(intro).format(Y=year)} {random.choice(natty_news)} {random.choice(stat_burn)} {random.choice(sign_off)}"

def procedural_interview(year, champion):
    random.seed(int(year) * 222)
    questions = ["Reporter: Coach, how did it feel to finally stop being a loser?", "Reporter: People are saying you're a total fraud. Your thoughts?", "Reporter: You absolute destroyed the competition. Was it even a challenge?", "Reporter: What is your message to the idiots you beat this year?", "Reporter: How much of this title was just you getting lucky as fuck?"]
    answers = ["I'm the best to ever do it. These other fuckheads can kiss my ass. It's talent, something the rest of this league wouldn't know if it hit them in the face.", "They can stay mad. I’ve got the trophy, they’ve got nothing but tears. Tell them to stop crying and start practicing because they fucking suck at this game.", "Why would I feel bad for smoking losers? If they didn't want to get fucked on national TV, they should've played better. It was a goddamn execution.", "It’s boring at the top when the rest of the league is this pathetic. I need a real opponent, not these fucking amateurs.", "Luck? I worked my ass off while these losers were playing with themselves in the group chat. It's called being elite. Deal with it."]
    q_idx = random.randint(0, len(questions)-1); a_idx = random.randint(0, len(answers)-1)
    return f"*{questions[q_idx]}*\n\n**Coach {champion}:** {answers[a_idx]}"

# --- UI EXECUTION ---
data_bundle = load_data()
if data_bundle:
    scores, rec, stats, h2h_df, rivalry_df, all_users, years, meta, champs_df, ratings_2041 = data_bundle
    tabs = st.tabs(["🏆 Prestige Rankings", "⚔️ H2H Matrix", "📺 Season Recap", "🎰 Vegas Odds", "🚀 2041 Projections", "📉 Recruiting", "📜 Records"])

    with tabs[0]:
        st.subheader("The Dynasty Hall of Fame")
        c1, c2 = st.columns([2,1])
        # Display new Prestige metrics
        c1.dataframe(stats[['User', 'HoF Points', 'Overall Record', 'Natties', 'CFP Apps', '1st Rounders', 'Avg Recruiting']], hide_index=True)
        c2.plotly_chart(px.pie(stats, values='Prestige %', names='User', hole=0.4, title="Total Dynasty Share"))

    with tabs[1]:
        st.header("Head-to-Head & Rivalries")
        st.table(h2h_df.set_index('User'))
        if not rivalry_df.empty:
            st.subheader("🔥 Most Intense Matchups")
            top_riv = rivalry_df.sort_values('Close Games', ascending=False).head(3)
            for _, r in top_riv.iterrows(): st.write(f"**{r['Matchup']}**: {r['Close Games']} Instant Classics")

    with tabs[2]:
        st.header("📺 Season Archives")
        sel_year = st.selectbox("Select Season", years)
        yr_scores = scores[scores[meta['yr']] == sel_year]
        natty_row = champs_df[champs_df[meta['cyr']].astype(str) == str(sel_year)]
        nat_win = natty_row[meta['cu']].values[0] if not natty_row.empty else "Nobody"
        story = procedural_writeup(sel_year, nat_win, round(yr_scores['Margin'].mean(),1), int(yr_scores['Margin'].max()))
        interview = procedural_interview(sel_year, nat_win)
        st.error(story); st.markdown("---"); st.subheader("🎤 Post-Game Presser"); st.info(interview); st.markdown("---")
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
        st.header("🚀 2041 Talent & Projections")
        st.dataframe(ratings_2041[['USER', 'TEAM', 'OVERALL', '2041 Projection', 'Game Breakers (90+ Speed & 90+ Acceleration)', 'Generational (96+ speed or 96+ Acceleration)']], hide_index=True)
        st.plotly_chart(px.scatter(ratings_2041, x='OVERALL', y='Game Breakers (90+ Speed & 90+ Acceleration)', text='USER', size='OFFENSE', title="2041 Explosiveness vs OVR"))

    with tabs[5]:
        st.header("📉 Recruiting Trends")
        st.plotly_chart(px.line(rec.dropna(), x='Year', y='Rank', color=rec.columns[0]).update_yaxes(autorange="reversed"))

    with tabs[6]:
        st.header("📜 Record Books")
        st.subheader("🏈 Biggest Blowouts")
        st.dataframe(scores.sort_values(by='Margin', ascending=False).head(10)[[meta['yr'], meta['vt'], meta['vs'], meta['hs'], meta['ht'], 'Margin']], hide_index=True)

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()