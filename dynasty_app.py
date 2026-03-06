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
        # LOAD CORE FILES
        scores = pd.read_csv('scores.csv')
        rec = pd.read_csv('recruiting.csv')
        champs = pd.read_csv('champs.csv')
        draft = pd.read_csv('UserDraftPicks.csv') # Now contains Career Stats
        ratings = pd.read_csv('TeamRatingsHistory.csv') # Now contains BCR
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

        # RECRUITING & TENURE
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

        # MASTER STATS ENGINE
        stats_list, h2h_rows, h2h_numeric = [], [], []
        natty_counts = champs[champs[champ_user_key].str.upper() != 'CPU'][champ_user_key].str.strip().str.title().value_counts().to_dict()
        
        for user in all_users:
            h_games = scores[scores['H_User_Final'] == user]
            v_games = scores[scores['V_User_Final'] == user]
            all_u_games = pd.concat([h_games, v_games])
            wins = len(h_games[h_games['H_Pts'] > h_games['V_Pts']]) + len(v_games[v_games['V_Pts'] > v_games['H_Pts']])
            u_draft = draft[draft['USER'] == user.title()]
            n_sent = u_draft['Guys Sent to NFL'].iloc[0] if not u_draft.empty else 0
            n_1st = u_draft['1st Rounders'].iloc[0] if not u_draft.empty else 0
            
            # CAREER STATS FOR HARDENED LOGIC
            conf_t = u_draft['Conference Titles'].iloc[0] if not u_draft.empty else 0
            cfp_w = u_draft['CFP Wins'].iloc[0] if not u_draft.empty else 0
            cfp_l = u_draft['CFP Losses'].iloc[0] if not u_draft.empty else 0
            natty_a = u_draft['National Title Appearances'].iloc[0] if not u_draft.empty else 0
            
            avg_rec = user_avg_rec.get(user.title(), 50)
            win_pct = (wins / len(all_u_games)) if len(all_u_games) > 0 else 0
            hof_points = (natty_counts.get(user, 0) * 50) + (n_1st * 10)

            stats_list.append({
                'User': user, 'HoF Points': int(hof_points), 'Record': f"{wins}-{len(all_u_games)-wins}", 
                'Natties': natty_counts.get(user, 0), 'Drafted': n_sent, '1st Rounders': n_1st,
                'Win Pct': win_pct, 'Avg Recruiting Rank': round(avg_rec, 1),
                'Conf Titles': conf_t, 'CFP Wins': cfp_w, 'CFP Losses': cfp_l, 'Natty Apps': natty_a
            })

            h2h_row = {'User': user}
            h2h_num_row = []
            for opp in all_users:
                if user == opp: h2h_row[opp] = "-"; h2h_num_row.append(0)
                else:
                    vs = scores[((scores['V_User_Final']==user) & (scores['H_User_Final']==opp)) | ((scores['V_User_Final']==opp) & (scores['H_User_Final']==user))]
                    vw = len(vs[((vs['V_User_Final']==user) & (vs['V_Pts'] > vs['H_Pts'])) | ((vs['H_User_Final']==user) & (vs['H_Pts'] > vs['V_Pts']))])
                    vl = len(vs) - vw
                    h2h_row[opp] = f"{vw}-{vl}"; h2h_num_row.append(vw - vl)
            h2h_rows.append(h2h_row); h2h_numeric.append(h2h_num_row)

        stats_df = pd.DataFrame(stats_list).sort_values(by='HoF Points', ascending=False)
        r_2041 = ratings[ratings['YEAR'] == 2041].copy()
        r_2040 = ratings[ratings['YEAR'] == 2040].copy()
        r_2041['USER'] = r_2041['USER'].str.strip().str.title()
        r_2041['Tenure'] = r_2041.apply(lambda x: calculate_tenure(x['USER'], x['TEAM']), axis=1)
        
        # PARSE BLUE CHIP RATIO
        bcr_col = 'Blue Chip Ratio (4 & 5 star recruit ratio on roster)'
        r_2041['BCR_Val'] = pd.to_numeric(r_2041[bcr_col].astype(str).str.replace('%', ''), errors='coerce').fillna(0)

        def get_improvement(row):
            prev = r_2040[r_2040['TEAM'] == row['TEAM']]
            return row['OVERALL'] - prev['OVERALL'].values[0] if not prev.empty else 0
        r_2041['Improvement'] = r_2041.apply(get_improvement, axis=1)

        def define_archetype(row):
            off_spd, def_spd = row.get('Off Speed (90+ speed)', 0), row.get('Def Speed (90+ speed)', 0)
            gens = row.get('Generational (96+ speed or 96+ Acceleration)', 0)
            if off_spd < 5 and def_spd < 5: return "Under-Speed", "🐢", "Low athletic floor."
            if gens >= 2 and off_spd >= 5 and def_spd >= 5: return "Sonic Boom", "🚀", "Elite roster speed."
            elif def_spd >= 6: return "Iron Curtain", "🛡️", "Range-based defense."
            else: return "Balanced Contender", "⚖️", "Solid all-around."

        r_2041[['Archetype', 'Icon', 'Outlook Description']] = r_2041.apply(lambda x: pd.Series(define_archetype(x)), axis=1)
        
        col_meta = {'yr': yr_key, 'vt': smart_col(scores, ['Visitor']), 'vs': v_score_key, 'ht': smart_col(scores, ['Home']), 'hs': h_score_key, 'cyr': champ_yr_key, 'cu': champ_user_key}
        return scores, stats_df, all_users, years_available, col_meta, champs, r_2041, pd.DataFrame(h2h_rows), pd.DataFrame(h2h_numeric, index=all_users, columns=all_users)
    except Exception as e:
        st.error(f"⚠️ Load Error: {e}")
        return None

data = load_data()
if data:
    scores, stats, all_users, years, meta, champs_df, r_2041, h2h_df, h2h_heat = data
    tabs = st.tabs(["🚀 2041 Scout & Projections", "🏆 Prestige", "⚔️ H2H & Risk Map", "📺 Season Recap", "📊 Team Analysis", "🔍 Talent Profile", "🌐 2041 Executive Outlook"])

    with tabs[4]: # TEAM ANALYSIS (ALL METRICS PRESERVED + HARDENED LOGIC)
        st.header("📊 2041 Team Deep-Dive")
        target = st.selectbox("Select Team", r_2041['USER'].tolist())
        row = r_2041[r_2041['USER'] == target].iloc[0]
        u_stats = stats[stats['User'] == target].iloc[0]
        
        # --- HARDENED NATTY PROBABILITY MATH ---
        p_talent = (row['OVERALL'] - 75) * 2.0
        p_speed = (row['Off Speed (90+ speed)'] + row['Def Speed (90+ speed)']) * 2.0
        p_gens = row['Generational (96+ speed or 96+ Acceleration)'] * 2.0
        p_bcr = row['BCR_Val'] * 0.2
        
        # Legacy Buffs
        p_legacy_base = (u_stats['Natties'] * 15) + (u_stats['Natty Apps'] * 10) + (u_stats['Conf Titles'] * 5) + (u_stats['CFP Wins'] * 4)
        
        # Penalties/Docks
        p_loss_tax = (u_stats['CFP Losses'] * 6)
        heartbreak_tax = (u_stats['Natty Apps'] - u_stats['Natties']) * 8 if u_stats['Natty Apps'] > u_stats['Natties'] else 0
        
        p_def_bonus = 10 if row['Def Speed (90+ speed)'] >= 7 else 0
        
        penalty = 0
        if row['OVERALL'] < 82: penalty -= 30
        elif row['OVERALL'] < 90: penalty -= 15
        if u_stats['Natties'] == 0: penalty -= 25
        elif u_stats['Natties'] == 1: penalty -= 10

        prob_score = min(99, max(1, int(p_talent + p_speed + p_gens + p_bcr + p_legacy_base - p_loss_tax - heartbreak_tax + p_def_bonus + penalty)))

        # --- CHAMPIONSHIP WINDOW LOGIC ---
        window = "⚖️ Neutral"
        if row['OVERALL'] >= 90 and prob_score > 60: window = "🏔️ Peak - Win Now"
        elif row['Improvement'] > 1.5: window = "📈 Rising - Rebuild"
        elif row['OVERALL'] < 85: window = "🏚️ Rebuilding"

        # ALL REQUESTED METRICS RESTORED
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Tenure", f"{int(row['Tenure'])} Yrs", row['TEAM'])
        c2.metric("Overall", row['OVERALL'])
        c3.metric("Natty Prob", f"{prob_score}%")
        c4.metric("Window", window)
        c5.metric("Star Player", row['⭐ STAR SKILL GUY (Top OVR)'])
        
        # New Metrics Row
        st.write("---")
        cx1, cx2, cx3 = st.columns(3)
        cx1.metric("Blue Chip Ratio", f"{int(row['BCR_Val'])}%")
        cx2.metric("Postseason Record", f"{int(u_stats['CFP Wins'])}-{int(u_stats['CFP Losses'])}")
        cx3.metric("Conf Titles", int(u_stats['Conf Titles']))

        st.markdown("### 📋 Robust Scouting Report & DNA")
        col_scout_1, col_scout_2 = st.columns(2)
        with col_scout_1:
            st.markdown(f"**Talent & Window:**")
            st.write(f"Coach {target} has a {row['OVERALL']} OVR roster with a BCR of {int(row['BCR_Val'])}%. Their current window is **{window}**.")
            if p_def_bonus > 0: st.success("🛡️ **Elite Defense Bonus:** The 7+ Def Speed is providing a 10% buff.")
        with col_scout_2:
            st.markdown("**Dynasty DNA Audit:**")
            st.write(f"Legacy: {u_stats['Natties']} Natties on {u_stats['Natty Apps']} Apps. Postseason Efficiency is being monitored.")
            if heartbreak_tax > 0: st.warning(f"⚠️ **Heartbreak Factor:** Logic is docking {heartbreak_tax}% for failed Natty appearances.")
            if u_stats['Natties'] == 0: st.error("❌ **Ringless Penalty:** Zero rings is causing a 25% drag on title odds.")

    with tabs[1]: # PRESTIGE
        st.dataframe(stats[['User', 'HoF Points', 'Record', 'Natties', 'Natty Apps', 'Conf Titles', 'CFP Wins', 'CFP Losses', 'Avg Recruiting Rank']], hide_index=True)
    
    with tabs[2]: # H2H
        st.plotly_chart(px.imshow(h2h_heat, text_auto=True, color_continuous_scale='RdBu_r'), use_container_width=True)
        st.table(h2h_df.set_index('User'))
        
    with tabs[3]: # SEASON RECAP
        sel_year = st.selectbox("Select Season", years)
        st.dataframe(scores[scores[meta['yr']] == sel_year][[meta['vt'], meta['vs'], meta['hs'], meta['ht'], 'Margin']], hide_index=True)
        
    with tabs[5]: # TALENT PROFILE
        for _, r in r_2041.sort_values('Generational (96+ speed or 96+ Acceleration)', ascending=False).iterrows():
            st.info(f"🚀 **{r['USER']}** at {r['TEAM']} has **{int(r['Generational (96+ speed or 96+ Acceleration)'])}** generational talents and a **{int(r['BCR_Val'])}%** BCR.")
            
    with tabs[6]: # EXECUTIVE OUTLOOK
        best_imp = r_2041.sort_values(by='Improvement', ascending=False).iloc[0]
        sm1, sm2, sm3, sm4, sm5 = st.columns(5)
        sm1.metric("Sonic Booms 🚀", len(r_2041[r_2041['Archetype'] == "Sonic Boom"]))
        sm3.metric("Most Improved", best_imp['USER'], f"+{int(best_imp['Improvement'])} OVR")
        st.plotly_chart(px.scatter(r_2041, x="Off Speed (90+ speed)", y="Def Speed (90+ speed)", color="Archetype", size="OVERALL", text="USER"), use_container_width=True)
        st.dataframe(r_2041[['USER', 'TEAM', 'OVERALL', 'Archetype', 'Outlook Description', 'Improvement', 'BCR_Val']], hide_index=True)

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()