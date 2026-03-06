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

        # TENURE LOGIC
        year_cols = [c for c in rec.columns if c.isdigit()]
        def calculate_tenure(user, team):
            row = rec[(rec['USER'].str.title() == user.title()) & (rec['Teams'].str.strip() == team.strip())]
            if not row.empty:
                # Count non-NaN recruiting ranks across the year columns
                return row[year_cols].notna().sum(axis=1).values[0]
            return 1

        # DRAFT & AWARD AGGREGATION
        draft.columns = [c.strip() for c in draft.columns]
        draft['USER'] = draft['USER'].str.strip().str.title()
        heis_counts = heisman['USER'].str.strip().str.title().value_counts().to_dict()
        coty_counts = coty[coty['User'].str.upper() != 'CPU']['User'].str.strip().str.title().value_counts().to_dict()
        natty_counts = champs[champs[champ_user_key].str.upper() != 'CPU'][champ_user_key].str.strip().str.title().value_counts().to_dict()

        # MASTER STATS ENGINE (Including H2H Matrix Generation)
        stats_list, h2h_rows = [], []
        for user in all_users:
            h_games = scores[scores['H_User_Final'] == user]
            v_games = scores[scores['V_User_Final'] == user]
            all_u_games = pd.concat([h_games, v_games])
            wins = len(h_games[h_games['H_Pts'] > h_games['V_Pts']]) + len(v_games[v_games['V_Pts'] > v_games['H_Pts']])
            
            u_draft = draft[draft['USER'] == user]
            n_sent = u_draft['Guys Sent to NFL'].iloc[0] if not u_draft.empty else 0
            n_1st = u_draft['1st Rounders'].iloc[0] if not u_draft.empty else 0
            
            hof_points = (natty_counts.get(user, 0) * 50) + (coty_counts.get(user, 0) * 15) + (n_1st * 10)

            stats_list.append({
                'User': user, 
                'HoF Points': int(hof_points), 
                'Record': f"{wins}-{len(all_u_games)-wins}", 
                'Natties': natty_counts.get(user, 0), 
                'Drafted': n_sent,
                '1st Rounders': n_1st
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
        h2h_df = pd.DataFrame(h2h_rows)

        # 2041 DATA & TENURE
        r_2041 = ratings[ratings['YEAR'] == 2041].copy()
        r_2041['USER'] = r_2041['USER'].str.strip().str.title()
        r_2041['Tenure'] = r_2041.apply(lambda x: calculate_tenure(x['USER'], x['TEAM']), axis=1)
        
        def project_wins(row):
            # Basic win projection formula
            w = 6 + ((row['OVERALL'] - 80) / 2.5)
            if str(row['Star Skill Guy is Generational Speed?']).strip().lower() == 'yes': w += 1.2
            fw = round(min(12, max(0, w)))
            return f"{fw}-{12-fw}"
        r_2041['2041 Projection'] = r_2041.apply(project_wins, axis=1)
        
        col_meta = {'yr': yr_key, 'vt': smart_col(scores, ['Visitor']), 'vs': v_score_key, 'ht': smart_col(scores, ['Home']), 'hs': h_score_key, 'cyr': champ_yr_key, 'cu': champ_user_key}
        return scores, stats_df, all_users, years_available, col_meta, champs, r_2041, h2h_df
    except Exception as e:
        st.error(f"⚠️ Load Error: {e}")
        return None

# --- DYNAMIC AI FUNCTIONS ---
def get_ai_recap(year, scores_df, champs_df, meta):
    natty_row = champs_df[champs_df[meta['cyr']].astype(str) == str(year)]
    winner = natty_row[meta['cu']].values[0] if not natty_row.empty else "The CPUs"
    blowouts = scores_df[scores_df[meta['yr']] == year].sort_values('Margin', ascending=False)
    blowout = blowouts.iloc[0] if not blowouts.empty else None
    
    pool = [
        f"In {year}, {winner} played like they had a cheat code enabled. Everyone else was just an NPC in their story.",
        f"{year} was a total bloodbath. {winner} stood at the top while the rest of you were struggling to call a basic slant route.",
        f"Looking at the {year} tapes, it's clear {winner} had the juice. Meanwhile, {blowout[meta['vt']] if blowout is not None else 'someone'} lost by {int(blowout['Margin']) if blowout is not None else 'a lot'} points. Get better.",
        f"History will remember {year} as the year {winner} stopped being polite and started being a nightmare for defensive coordinators.",
        f"The {year} campaign was defined by {winner}'s dominance. If you weren't on their team, you were just a speed bump on the road to glory."
    ]
    return random.choice(pool)

def get_gen_freak_commentary(user, team, count):
    pool = [
        f"🚨 **{user}** at {team} is currently running a track meet. They have **{count}** generational freaks. Defensive coordinators are checking into therapy.",
        f"💎 BIOLOGICAL ANOMALY: {team} roster contains **{count}** players who break the game's physics. {user} isn't recruiting, he's cloning.",
        f"🏎️ The speed limit in {team} has been repealed. {user} has **{count}** players with 96+ Speed/Accel. You aren't catching them.",
        f"☣️ WARNING: {team} has **{count}** generational burners. If you don't have a 99-speed corner, just stay on the bus.",
        f"✈️ Air {user} is cleared for takeoff. With **{count}** generational specimens, {team} is moving at a speed the human eye can barely track."
    ]
    return random.choice(pool)

# --- UI EXECUTION ---
data = load_data()
if data:
    scores, stats, all_users, years, meta, champs_df, r_2041, h2h_df = data
    tabs = st.tabs(["🏆 Prestige", "⚔️ H2H Records", "📺 Season Recap", "📊 Team Analysis", "🚀 2041 Scout & Projections", "🔍 Talent Profile"])

    with tabs[0]:
        st.subheader("The Dynasty Hall of Fame")
        # Added 1st Rounders back to the table
        st.dataframe(stats[['User', 'HoF Points', 'Record', 'Natties', 'Drafted', '1st Rounders']], hide_index=True)

    with tabs[1]:
        st.header("⚔️ Head-to-Head Records")
        st.table(h2h_df.set_index('User'))

    with tabs[2]:
        st.header("📺 Season Recap")
        sel_year = st.selectbox("Select Season", years)
        st.info(get_ai_recap(sel_year, scores, champs_df, meta))
        st.dataframe(scores[scores[meta['yr']] == sel_year][[meta['vt'], meta['vs'], meta['hs'], meta['ht'], 'Margin']], hide_index=True)

    with tabs[3]:
        st.header("📊 2041 Team Deep-Dive")
        target = st.selectbox("Select Team to Analyze", r_2041['USER'].tolist())
        row = r_2041[r_2041['USER'] == target].iloc[0]
        u_stats = stats[stats['User'] == target].iloc[0]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("School Tenure", f"{int(row['Tenure'])} Years", f"At {row['TEAM']}")
        c2.metric("Overall", row['OVERALL']) # Correctly uses the OVERALL column
        c3.metric("Projected Record", row['2041 Projection']) # Replaced HOF Rank with Projection
        c4.metric("Star Player", row['⭐ STAR SKILL GUY (Top OVR)']) # Shows player name

        st.markdown(f"### 📋 Scouting Report: {target}")
        
        # Determine generational status of star player
        is_star_gen = "is a **Generational Speed Talent**" if str(row['Star Skill Guy is Generational Speed?']).lower() == 'yes' else "does not possess generational speed metrics"
        
        # Determine speed quality
        off_speed_val = row['Off Speed (90+ speed)']
        def_speed_val = row['Def Speed (90+ speed)']
        speed_threshold = 5 # Defined "Good speed" as 5 or more 90+ speed players
        
        if off_speed_val >= speed_threshold and def_speed_val >= speed_threshold:
            speed_narrative = "possesses **good speed on both sides of the ball**, making them a nightmare in transition."
        elif off_speed_val >= speed_threshold:
            speed_narrative = "features **good speed on offense**, capable of scoring from anywhere, though the defense may lack similar recovery speed."
        elif def_speed_val >= speed_threshold:
            speed_narrative = "boasts **good speed on defense**, allowing them to erase perimeter mistakes, even if the offense is more methodical."
        else:
            speed_narrative = "currently **lacks elite speed on both offense and defense**, meaning they must rely on technical execution and scheme to win."

        analysis = f"Under Coach {target}, **{row['TEAM']}** has established a **{row['OVERALL']} OVR** roster. "
        analysis += f"Their primary star, **{row['⭐ STAR SKILL GUY (Top OVR)']}**, {is_star_gen}. "
        analysis += f"When it comes to pure roster velocity, this team {speed_narrative} "
        
        if row['Generational (96+ speed or 96+ Acceleration)'] > 0:
            analysis += f"Furthermore, opponents must account for **{int(row['Generational (96+ speed or 96+ Acceleration)'])}** total generational freaks scattered across the depth chart. "
        
        analysis += f"With {int(row['Tenure'])} years at the helm, {target} has fully implemented their system. "
        analysis += f"Historically, this coach has sent **{u_stats['Drafted']}** players to the NFL and secured **{u_stats['Natties']}** National Titles. "
        
        if row['DEFENSE'] > row['OFFENSE']:
            analysis += "Expect a stingy, defensive-minded approach that punishes offensive mistakes with raw closing speed."
        else:
            analysis += "Expect a high-octane scoring machine that looks to out-run opponents in a track meet."
            
        st.write(analysis)

    with tabs[4]:
        st.header("🚀 2041 Scout & Full Ratings")
        # Shows every single column from the TeamRatingsHistory file as requested
        st.dataframe(r_2041, hide_index=True)

    with tabs[5]:
        st.header("🔍 Generational Talent Tracker")
        gen_df = r_2041[r_2041['Generational (96+ speed or 96+ Acceleration)'] > 0].sort_values('Generational (96+ speed or 96+ Acceleration)', ascending=False)
        for _, r in gen_df.iterrows():
            st.warning(get_gen_freak_commentary(r['USER'], r['TEAM'], int(r['Generational (96+ speed or 96+ Acceleration)'])))

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()