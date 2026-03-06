import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

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
        # LOAD ALL CORE FILES
        scores = pd.read_csv('scores.csv')
        rec = pd.read_csv('recruiting.csv')
        champs = pd.read_csv('champs.csv')
        draft = pd.read_csv('UserDraftPicks.csv') 
        ratings = pd.read_csv('TeamRatingsHistory.csv') 
        heisman = pd.read_csv('Heisman_History.csv')
        coty = pd.read_csv('COTY.csv')

        # STANDARDIZE KEYS
        v_user_key = smart_col(scores, ['Vis_User', 'Visitor User', 'Vis User'])
        h_user_key = smart_col(scores, ['Home_User', 'Home User'])
        v_score_key = smart_col(scores, ['Vis Score', 'Vis_Score'])
        h_score_key = smart_col(scores, ['Home Score', 'Home_Score'])
        yr_key = smart_col(scores, ['YEAR', 'Year'])
        champ_user_key = smart_col(champs, ['user', 'User', 'User of team'])
        
        # STANDARDIZE KEYS FOR AWARDS
        h_yr_key = smart_col(heisman, ['Year', 'YEAR'])
        h_player_key = smart_col(heisman, ['Player', 'Winner', 'Name'])
        h_school_key = smart_col(heisman, ['School', 'Team', 'University'])
        c_yr_key = smart_col(coty, ['Year', 'YEAR'])
        c_coach_key = smart_col(coty, ['Coach', 'Winner', 'Name'])
        c_school_key = smart_col(coty, ['School', 'Team', 'University'])

        # CLEAN SCORES
        scores['V_User_Final'] = scores[v_user_key].astype(str).str.strip().str.title()
        scores['H_User_Final'] = scores[h_user_key].astype(str).str.strip().str.title()
        scores['V_Pts'] = pd.to_numeric(scores[v_score_key], errors='coerce')
        scores['H_Pts'] = pd.to_numeric(scores[h_score_key], errors='coerce')
        scores = scores.dropna(subset=['V_Pts', 'H_Pts'])
        scores['Margin'] = (scores['H_Pts'] - scores['V_Pts']).abs()
        
        all_users = sorted([u for u in pd.concat([scores['V_User_Final'], scores['H_User_Final']]).unique() if u.upper() != 'CPU' and u != 'Nan'])
        years_available = sorted(scores[yr_key].unique(), reverse=True)

        # MASTER STATS ENGINE
        stats_list, h2h_rows, h2h_numeric = [], [], []
        natty_counts = champs[champs[champ_user_key].str.upper() != 'CPU'][champ_user_key].str.strip().str.title().value_counts().to_dict()
        
        for user in all_users:
            h_games = scores[scores['H_User_Final'] == user]
            v_games = scores[scores['V_User_Final'] == user]
            all_u_games = pd.concat([h_games, v_games])
            wins = len(h_games[h_games['H_Pts'] > h_games['V_Pts']]) + len(v_games[v_games['V_Pts'] > v_games['H_Pts']])
            u_draft = draft[draft['USER'].str.title() == user.title()]
            n_sent = u_draft['Guys Sent to NFL'].iloc[0] if not u_draft.empty else 0
            n_1st = u_draft['1st Rounders'].iloc[0] if not u_draft.empty else 0
            conf_t = u_draft['Conference Titles'].iloc[0] if not u_draft.empty else 0
            cfp_w = u_draft['CFP Wins'].iloc[0] if not u_draft.empty else 0
            cfp_l = u_draft['CFP Losses'].iloc[0] if not u_draft.empty else 0
            natty_a = u_draft['National Title Appearances'].iloc[0] if not u_draft.empty else 0
            
            hof_points = (natty_counts.get(user, 0) * 50) + (n_1st * 10)

            stats_list.append({
                'User': user, 'HoF Points': int(hof_points), 'Record': f"{wins}-{len(all_u_games)-wins}", 
                'Natties': natty_counts.get(user, 0), 'Drafted': n_sent, '1st Rounders': n_1st,
                'Conf Titles': int(conf_t), 'CFP Wins': int(cfp_w), 'CFP Losses': int(cfp_l), 'Natty Apps': int(natty_a)
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

        stats_df = pd.DataFrame(stats_list)
        r_2041 = ratings[ratings['YEAR'] == 2041].copy()
        r_2040 = ratings[ratings['YEAR'] == 2040].copy()
        r_2041['USER'] = r_2041['USER'].str.strip().str.title()
        
        # BCR & Improvement
        bcr_col = 'Blue Chip Ratio (4 & 5 star recruit ratio on roster)'
        r_2041['BCR_Val'] = pd.to_numeric(r_2041[bcr_col].astype(str).str.replace('%', ''), errors='coerce').fillna(0)
        
        def get_improvement(row):
            prev = r_2040[r_2040['TEAM'] == row['TEAM']]
            return row['OVERALL'] - prev['OVERALL'].values[0] if not prev.empty else 0
        r_2041['Improvement'] = r_2041.apply(get_improvement, axis=1)

        meta = {
            'yr': yr_key, 'vt': smart_col(scores, ['Visitor']), 'vs': v_score_key, 'ht': smart_col(scores, ['Home']), 'hs': h_score_key,
            'h_yr': h_yr_key, 'h_player': h_player_key, 'h_school': h_school_key,
            'c_yr': c_yr_key, 'c_coach': c_coach_key, 'c_school': c_school_key
        }

        return scores, stats_df, all_users, years_available, meta, r_2041, pd.DataFrame(h2h_rows), pd.DataFrame(h2h_numeric, index=all_users, columns=all_users), coty, heisman
    except Exception as e:
        st.error(f"⚠️ Load Error: {e}")
        return None

def calculate_hardened_prob(row, stats_df):
    u_s = stats_df[stats_df['User'] == row['USER']].iloc[0]
    p_talent = (row['OVERALL'] - 75) * 2.0
    p_speed = (row['Off Speed (90+ speed)'] + row['Def Speed (90+ speed)']) * 2.0
    p_gens = row['Generational (96+ speed or 96+ Acceleration)'] * 2.0
    p_bcr = row['BCR_Val'] * 0.2
    p_legacy = (u_s['Natties'] * 15) + (u_s['Natty Apps'] * 10) + (u_s['Conf Titles'] * 5) + (u_s['CFP Wins'] * 4)
    p_loss_tax = (u_s['CFP Losses'] * 6)
    heartbreak_tax = (u_s['Natty Apps'] - u_s['Natties']) * 8 if u_s['Natty Apps'] > u_s['Natties'] else 0
    penalty = -25 if u_s['Natties'] == 0 else 0
    if row['OVERALL'] < 82: penalty -= 30
    return min(99, max(1, int(p_talent + p_speed + p_gens + p_bcr + p_legacy - p_loss_tax - heartbreak_tax + penalty)))

data = load_data()
if data:
    scores, stats, all_users, years, meta, r_2041, h2h_df, h2h_heat, coty, heisman = data
    tabs = st.tabs(["🚀 2041 Scout & Projections", "🏆 Prestige", "⚔️ H2H & Risk Map", "📺 Season Recap", "📊 Team Analysis", "🔍 Talent Profile", "🌐 2041 Executive Outlook"])

    # --- 1. SCOUT & PROJECTIONS (FULL RESTORE) ---
    with tabs[0]:
        st.header("🚀 2041 Executive Projections")
        r_2041['Natty Prob'] = r_2041.apply(lambda x: calculate_hardened_prob(x, stats), axis=1)
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Title Contender Odds")
            st.dataframe(r_2041.sort_values('Natty Prob', ascending=False)[['USER', 'TEAM', 'OVERALL', 'Natty Prob']], hide_index=True)
        with c2:
            st.subheader("Projected Risers")
            st.dataframe(r_2041.sort_values('Improvement', ascending=False)[['USER', 'TEAM', 'OVERALL', 'Improvement']], hide_index=True)

    # --- 4. SEASON RECAP (FULL AI NARRATIVE) ---
    with tabs[3]:
        st.header("📺 AI Dynasty Recap Engine")
        sel_year = st.selectbox("Select Season", years)
        y_data = scores[scores[meta['yr']] == sel_year]
        if not y_data.empty:
            biggest_win = y_data.loc[y_data['Margin'].idxmax()]
            avg_m = round(y_data['Margin'].mean(), 1)
            st.info(f"🏟️ **Game of the Year:** {biggest_win['H_User_Final']} vs {biggest_win['V_User_Final']} (Margin: {int(biggest_win['Margin'])})")
            
            y_h = heisman[heisman[meta['h_yr']] == sel_year]
            y_c = coty[coty[meta['c_yr']] == sel_year]
            ca1, ca2 = st.columns(2)
            with ca1:
                if not y_h.empty: st.success(f"🏅 **Heisman:** {y_h.iloc[0][meta['h_player']]} ({y_h.iloc[0][meta['h_school']]})")
            with ca2:
                if not y_c.empty: st.success(f"👔 **COTY:** {y_c.iloc[0][meta['c_coach']]} ({y_c.iloc[0][meta['c_school']]})")
            
            st.markdown(f"**Narrative:** {sel_year} featured {len(y_data)} user battles. The margin of {avg_m} suggests a season of {'dominant runs' if avg_m > 20 else 'tactical grit'}.")
        st.dataframe(y_data[[meta['vt'], meta['vs'], meta['hs'], meta['ht'], 'Margin']], hide_index=True)

    # --- 6. TALENT PROFILE (FULL FREAK ADJUSTMENTS) ---
    with tabs[5]:
        st.header("🔍 The 2041 Freak List")
        st.write("Detailed scouting of high-end athletic ceiling.")
        
        for _, r in r_2041.sort_values('Generational (96+ speed or 96+ Acceleration)', ascending=False).iterrows():
            gens = int(r['Generational (96+ speed or 96+ Acceleration)'])
            
            # THE "MISSING" GENERATIONAL ADJUSTMENTS
            if gens == 0:
                gen_desc = "📉 **Fundamentalist Squad:** No track stars found. This team relies on high-IQ play and heavy scheme to win."
                tier = "🐢 GROUND & POUND"
            elif gens == 1:
                gen_desc = "🎯 **The Specialist:** One elite game-breaker. If you stop this one player, you stop the whole engine."
                tier = "🏎️ ROADRUNNER"
            elif gens == 2:
                gen_desc = "⚔️ **Double Trouble:** A lethal duo of track stars. You can't double-team both."
                tier = "🚀 SONIC BOOM"
            elif gens == 3:
                gen_desc = "🔬 **The Speed Lab:** Experimental levels of velocity. This roster erases coaching mistakes with pure foot-speed."
                tier = "🧨 DYNAMITE DEPTH"
            elif gens >= 4:
                gen_desc = "⚡ **Flash Point:** You are officially accessing the Speed Force. This is illegal in 48 states."
                tier = "☣️ GOD-TIER VELOCITY"
            
            with st.expander(f"{r['USER']} | {r['TEAM']} - {tier}"):
                st.write(gen_desc)
                st.metric("Blue Chip Ratio", f"{int(r['BCR_Val'])}%")
                st.write(f"**90+ Speed Depth:** {int(r['Team Speed (90+ Speed Guys)'])} total burners.")
                st.progress(min(1.0, r['BCR_Val']/100))

    # --- OTHER TABS ---
    with tabs[1]: st.dataframe(stats.sort_values('HoF Points', ascending=False), hide_index=True)
    with tabs[2]: st.plotly_chart(px.imshow(h2h_heat, text_auto=True, color_continuous_scale='RdBu_r'), use_container_width=True)
    with tabs[4]:
        target = st.selectbox("Select Team", r_2041['USER'].tolist())
        row = r_2041[r_2041['USER'] == target].iloc[0]
        st.metric("Natty Prob", f"{calculate_hardened_prob(row, stats)}%")
        st.metric("Improvement", f"+{row['Improvement']} OVR")
    with tabs[6]:
        st.plotly_chart(px.scatter(r_2041, x="Off Speed (90+ speed)", y="Def Speed (90+ speed)", color="USER", size="OVERALL", text="TEAM"), use_container_width=True)

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()