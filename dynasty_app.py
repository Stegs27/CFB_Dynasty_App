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

        # RECRUITING & TENURE LOGIC
        year_cols = [c for c in rec.columns if str(c).strip().isdigit()]
        non_year_cols = [c for c in rec.columns if not str(c).strip().isdigit()]
        rec_long = rec.melt(id_vars=non_year_cols, var_name='Year', value_name='Rank')
        rec_long['Rank'] = rec_long['Rank'].astype(str).str.replace(r'[*\-]', '', regex=True).replace('nan', np.nan)
        rec_long['Rank'] = pd.to_numeric(rec_long['Rank'], errors='coerce')
        
        user_avg_rec = rec_long.groupby('USER')['Rank'].mean().to_dict()

        def calculate_tenure(user, team):
            row = rec[(rec['USER'].str.title() == user.title()) & (rec['Teams'].str.strip() == team.strip())]
            if not row.empty:
                return row[year_cols].notna().sum(axis=1).values[0]
            return 1

        # DRAFT & AWARD AGGREGATION
        draft.columns = [c.strip() for c in draft.columns]
        draft['USER'] = draft['USER'].str.strip().str.title()
        natty_counts = champs[champs[champ_user_key].str.upper() != 'CPU'][champ_user_key].str.strip().str.title().value_counts().to_dict()
        coty_counts = coty[coty['User'].str.upper() != 'CPU']['User'].str.strip().str.title().value_counts().to_dict()

        # MASTER STATS ENGINE
        stats_list, h2h_rows, h2h_numeric = [], [], []
        for user in all_users:
            h_games = scores[scores['H_User_Final'] == user]
            v_games = scores[scores['V_User_Final'] == user]
            all_u_games = pd.concat([h_games, v_games])
            wins = len(h_games[h_games['H_Pts'] > h_games['V_Pts']]) + len(v_games[v_games['V_Pts'] > v_games['H_Pts']])
            
            u_draft = draft[draft['USER'] == user]
            n_sent = u_draft['Guys Sent to NFL'].iloc[0] if not u_draft.empty else 0
            n_1st = u_draft['1st Rounders'].iloc[0] if not u_draft.empty else 0
            
            avg_rec = user_avg_rec.get(user.title(), 0)
            win_pct = (wins / len(all_u_games)) if len(all_u_games) > 0 else 0
            hof_points = (natty_counts.get(user, 0) * 50) + (coty_counts.get(user, 0) * 15) + (n_1st * 10)

            stats_list.append({
                'User': user, 
                'HoF Points': int(hof_points), 
                'Record': f"{wins}-{len(all_u_games)-wins}", 
                'Natties': natty_counts.get(user, 0), 
                'Drafted': n_sent,
                '1st Rounders': n_1st,
                'Win Pct': win_pct,
                'Avg Recruiting Rank': round(avg_rec, 1) if not pd.isna(avg_rec) else "N/A"
            })

            h2h_row = {'User': user}
            h2h_num_row = []
            for opp in all_users:
                if user == opp: 
                    h2h_row[opp] = "-"
                    h2h_num_row.append(0)
                else:
                    vs = scores[((scores['V_User_Final']==user) & (scores['H_User_Final']==opp)) | ((scores['V_User_Final']==opp) & (scores['H_User_Final']==user))]
                    vw = len(vs[((vs['V_User_Final']==user) & (vs['V_Pts'] > vs['H_Pts'])) | ((vs['H_User_Final']==user) & (vs['H_Pts'] > vs['V_Pts']))])
                    vl = len(vs) - vw
                    h2h_row[opp] = f"{vw}-{vl}"
                    h2h_num_row.append(vw - vl)
            h2h_rows.append(h2h_row)
            h2h_numeric.append(h2h_num_row)

        stats_df = pd.DataFrame(stats_list).sort_values(by='HoF Points', ascending=False)
        h2h_df = pd.DataFrame(h2h_rows)
        h2h_heat_df = pd.DataFrame(h2h_numeric, index=all_users, columns=all_users)

        # 2041 DATA & IMPROVEMENT
        r_2041 = ratings[ratings['YEAR'] == 2041].copy()
        r_2040 = ratings[ratings['YEAR'] == 2040].copy()
        r_2041['USER'] = r_2041['USER'].str.strip().str.title()
        r_2041['Tenure'] = r_2041.apply(lambda x: calculate_tenure(x['USER'], x['TEAM']), axis=1)
        
        def get_improvement(row):
            prev = r_2040[r_2040['TEAM'] == row['TEAM']]
            return row['OVERALL'] - prev['OVERALL'].values[0] if not prev.empty else 0
        r_2041['Improvement'] = r_2041.apply(get_improvement, axis=1)

        def project_wins(row):
            w = 6 + ((row['OVERALL'] - 80) / 2.5)
            if str(row['Star Skill Guy is Generational Speed?']).strip().lower() == 'yes': w += 1.2
            fw = round(min(12, max(0, w)))
            return f"{fw}-{12-fw}"
        r_2041['2041 Projection'] = r_2041.apply(project_wins, axis=1)

        # --- ARCHETYPE LOGIC ---
        def define_archetype(row):
            off_spd = row.get('Off Speed (90+ speed)', 0)
            def_spd = row.get('Def Speed (90+ speed)', 0)
            gens = row.get('Generational (96+ speed or 96+ Acceleration)', 0)
            if off_spd < 5 and def_spd < 5: return "Under-Speed", "🐢", "Critically low speed metrics."
            if gens >= 2 and off_spd >= 5 and def_spd >= 5: return "Sonic Boom", "🚀", "Elite speed floor."
            elif gens >= 1 and off_spd >= 6 and def_spd < 5: return "Glass Cannon", "🔫", "High-octane scoring, vulnerable defense."
            elif def_spd >= 6: return "Iron Curtain", "🛡️", "Elite defensive range."
            elif gens == 0: return "Sluggish Giant", "🕯️", "Heavy on OVR, light on speed."
            else: return "Balanced Contender", "⚖️", "Solid all-around roster."

        r_2041[['Archetype', 'Icon', 'Outlook Description']] = r_2041.apply(lambda x: pd.Series(define_archetype(x)), axis=1)
        
        col_meta = {'yr': yr_key, 'vt': smart_col(scores, ['Visitor']), 'vs': v_score_key, 'ht': smart_col(scores, ['Home']), 'hs': h_score_key, 'cyr': champ_yr_key, 'cu': champ_user_key}
        return scores, stats_df, all_users, years_available, col_meta, champs, r_2041, h2h_df, h2h_heat_df
    except Exception as e:
        st.error(f"⚠️ Load Error: {e}")
        return None

# --- AI FUNCTIONS ---
def get_ai_recap(year, scores_df, champs_df, meta):
    natty_row = champs_df[champs_df[meta['cyr']].astype(str) == str(year)]
    winner = natty_row[meta['cu']].values[0] if not natty_row.empty else "The CPUs"
    user_games = scores_df[(scores_df[meta['yr']] == year) & (scores_df['V_User_Final'] != 'Cpu') & (scores_df['H_User_Final'] != 'Cpu')].sort_values('Margin', ascending=False)
    blowout_str = f" Never forget the blowout by {int(user_games.iloc[0]['Margin'])}." if not user_games.empty else ""
    return f"In {year}, {winner} proved dominance. {blowout_str}"

def get_gen_freak_commentary(user, team, count):
    if count == 0: return f"🕯️ Faith Alone: **{user}** at {team} has **{count}** generational freaks."
    return f"🚀 **{user}** at {team} has **{count}** generational talents."

# --- UI EXECUTION ---
data = load_data()
if data:
    scores, stats, all_users, years, meta, champs_df, r_2041, h2h_df, h2h_heat = data
    tabs = st.tabs(["🚀 2041 Scout & Projections", "🏆 Prestige", "⚔️ H2H & Risk Map", "📺 Season Recap", "📊 Team Analysis", "🔍 Talent Profile", "🌐 2041 Executive Outlook"])

    with tabs[0]:
        st.header("🚀 2041 Scout & Full Ratings")
        st.dataframe(r_2041, hide_index=True)

    with tabs[1]:
        st.subheader("The Dynasty Hall of Fame")
        st.dataframe(stats, hide_index=True)

    with tabs[2]:
        st.header("⚔️ Rivalry Risk & H2H Records")
        st.plotly_chart(px.imshow(h2h_heat, text_auto=True, color_continuous_scale='RdBu_r'), use_container_width=True)

    with tabs[3]:
        st.header("📺 Season Recap")
        sel_year = st.selectbox("Select Season", years)
        st.info(get_ai_recap(sel_year, scores, champs_df, meta))

    with tabs[4]: # NATTY PROBABILITY LOGIC ADDED HERE
        st.header("📊 2041 Team Deep-Dive")
        target = st.selectbox("Select Team", r_2041['USER'].tolist())
        row = r_2041[r_2041['USER'] == target].iloc[0]
        u_stats = stats[stats['User'] == target].iloc[0]
        
        # PROBABILITY ENGINE
        p_natty = (u_stats['Natties'] * 15) # Pedigree
        p_speed = (row['Off Speed (90+ speed)'] + row['Def Speed (90+ speed)']) * 2 # Velocity
        p_gens = row['Generational (96+ speed or 96+ Acceleration)'] * 8 # Gamebreakers
        p_form = u_stats['Win Pct'] * 30 # Skill/History
        p_draft = u_stats['1st Rounders'] * 3 # Recruiting/Development
        
        prob_score = min(99, max(5, int(p_natty + p_speed + p_gens + p_form + p_draft)))

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Tenure", f"{int(row['Tenure'])} Yrs", row['TEAM'])
        c2.metric("Overall", row['OVERALL'])
        c3.metric("Win Projection", row['2041 Projection'])
        c4.metric("Natty Probability", f"{prob_score}%", "Dynasty Odds")
        c5.metric("Star Player", row['⭐ STAR SKILL GUY (Top OVR)'])
        
        st.markdown(f"### 🎯 Probability Analysis: {target}")
        if prob_score > 75:
            st.success(f"**Heavy Favorite:** With {u_stats['Natties']} Natties and an elite speed profile, the data suggests {target} is the team to beat.")
        elif prob_score > 40:
            st.warning(f"**Dark Horse:** {target} has the speed floor, but history shows they need to stay consistent to secure a title.")
        else:
            st.error(f"**Long Shot:** Low historic win percentage and speed gaps make a Natty run unlikely for {target} this year.")

    with tabs[5]:
        st.header("🔍 Generational Talent Tracker")
        for _, r in r_2041.sort_values('Generational (96+ speed or 96+ Acceleration)', ascending=False).iterrows():
            st.info(get_gen_freak_commentary(r['USER'], r['TEAM'], int(r['Generational (96+ speed or 96+ Acceleration)'])))

    with tabs[6]:
        st.header("🌐 2041 Executive League Outlook")
        best_imp = r_2041.sort_values(by='Improvement', ascending=False).iloc[0]
        sm1, sm2, sm3, sm4, sm5 = st.columns(5)
        sm1.metric("Sonic Booms 🚀", len(r_2041[r_2041['Archetype'] == "Sonic Boom"]))
        sm3.metric("Most Improved", best_imp['USER'], f"+{int(best_imp['Improvement'])} OVR")
        st.plotly_chart(px.scatter(r_2041, x="Off Speed (90+ speed)", y="Def Speed (90+ speed)", color="Archetype", size="OVERALL", text="USER"), use_container_width=True)

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()