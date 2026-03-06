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
        heis_counts = heisman['USER'].str.strip().str.title().value_counts().to_dict()
        coty_counts = coty[coty['User'].str.upper() != 'CPU']['User'].str.strip().str.title().value_counts().to_dict()
        natty_counts = champs[champs[champ_user_key].str.upper() != 'CPU'][champ_user_key].str.strip().str.title().value_counts().to_dict()

        # MASTER STATS ENGINE
        stats_list, h2h_rows = [], []
        for user in all_users:
            h_games = scores[scores['H_User_Final'] == user]
            v_games = scores[scores['V_User_Final'] == user]
            all_u_games = pd.concat([h_games, v_games])
            wins = len(h_games[h_games['H_Pts'] > h_games['V_Pts']]) + len(v_games[v_games['V_Pts'] > v_games['H_Pts']])
            
            u_draft = draft[draft['USER'] == user]
            n_sent = u_draft['Guys Sent to NFL'].iloc[0] if not u_draft.empty else 0
            n_1st = u_draft['1st Rounders'].iloc[0] if not u_draft.empty else 0
            
            avg_rec = user_avg_rec.get(user.title(), 0)
            if pd.isna(avg_rec): avg_rec = 0

            hof_points = (natty_counts.get(user, 0) * 50) + (coty_counts.get(user, 0) * 15) + (n_1st * 10)

            stats_list.append({
                'User': user, 
                'HoF Points': int(hof_points), 
                'Record': f"{wins}-{len(all_u_games)-wins}", 
                'Natties': natty_counts.get(user, 0), 
                'Drafted': n_sent,
                '1st Rounders': n_1st,
                'Avg Recruiting Rank': round(avg_rec, 1) if avg_rec > 0 else "N/A"
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
            w = 6 + ((row['OVERALL'] - 80) / 2.5)
            if str(row['Star Skill Guy is Generational Speed?']).strip().lower() == 'yes': w += 1.2
            fw = round(min(12, max(0, w)))
            return f"{fw}-{12-fw}"
        r_2041['2041 Projection'] = r_2041.apply(project_wins, axis=1)

        # --- ARCHETYPE LOGIC (NEW 2041 OUTLOOK ENGINE) ---
        def define_archetype(row):
            off_spd = row.get('Off Speed (90+ speed)', 0)
            def_spd = row.get('Def Speed (90+ speed)', 0)
            gens = row.get('Generational (96+ speed or 96+ Acceleration)', 0)
            
            if gens >= 2 and off_spd >= 5 and def_spd >= 5:
                return "Sonic Boom", "🚀", "Elite speed floor + multiple game-breakers. Statistical favorite."
            elif gens >= 1 and off_spd >= 6 and def_spd < 5:
                return "Glass Cannon", "🔫", "High-octane scoring threats but the defense can't chase. High shootout potential."
            elif def_spd >= 6:
                return "Iron Curtain", "🛡️", "Elite defensive range. Specifically built to punish speed-reliant offenses."
            elif gens == 0 and (off_spd < 5 or def_spd < 5):
                return "Sluggish Giant", "🕯️", "Heavy on OVR but low on velocity. Must win through pure user skill."
            else:
                return "Balanced Contender", "⚖️", "Solid all-around roster with no glaring athletic deficiencies."

        r_2041[['Archetype', 'Icon', 'Outlook Description']] = r_2041.apply(
            lambda x: pd.Series(define_archetype(x)), axis=1
        )
        
        col_meta = {'yr': yr_key, 'vt': smart_col(scores, ['Visitor']), 'vs': v_score_key, 'ht': smart_col(scores, ['Home']), 'hs': h_score_key, 'cyr': champ_yr_key, 'cu': champ_user_key}
        return scores, stats_df, all_users, years_available, col_meta, champs, r_2041, h2h_df, rec_long
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
        f"Looking at the {year} tapes, it's clear {winner} had the juice. Meanwhile, {blowout[meta['vt']] if blowout is not None else 'someone'} lost by {int(blowout['Margin']) if blowout is not None else 'a lot'} points.",
        f"History will remember {year} as the year {winner} stood above the rest.",
        f"The {year} campaign was defined by {winner}'s dominance.",
        f"{year}: A year of broken controllers and shattered dreams, courtesy of {winner}.",
        f"If {year} was a movie, {winner} was the main character and everyone else was the comic relief.",
        f"The record books for {year} are mostly just {winner} flex-tweeting while {blowout[meta['vt']] if blowout is not None else 'their victims'} stared at the ceiling.",
        f"In {year}, {winner} didn't just win the Natty; they took everyone's lunch money and the lunch lady's keys too.",
        f"The {year} season was less of a competition and more of a victory lap for {winner}."
    ]
    return random.choice(pool)

def get_gen_freak_commentary(user, team, count):
    if count == 0:
        pool = [
            f"🕯️ Faith Alone: **{user}** at {team} has **{count}** generational freaks. They are currently just praying for that one magical guy to lead them to the promised land.",
            f"🔮 The Vision: With **{count}** elite burners, **{user}** is simply waiting on a miracle recruit to magically descend upon {team}.",
            f"⛪ The Sanctuary: {team} roster lacks any generational specimens (**{count}**). **{user}** has decided to wait for a chosen one to lead them to the promised land.",
            f"🙏 Pious Patience: **{user}** is standing at the gates of {team} with **{count}** freaks, waiting for a savior to magically carry them to the promised land.",
            f"✨ Hope & Dreams: There are **{count}** generational talents here. **{user}** is biding time until the right player magically emerges for {team}."
        ]
    elif count == 1:
        pool = [
            f"⚔️ **Cloud Strife** has arrived. **{user}** at {team} has **{count}** generational talent wielding a buster sword.",
            f"🧪 Maximum Effort! **{user}** found their **Deadpool**. **{count}** freakish talent at {team} who refuses to be stopped.",
            f"🕶️ **{user}** has found **Neo**. There is **{count}** generational freak at {team} who can see the code.",
            f"💍 The One Ring! **{user}** has their **Frodo**. Just **{count}** freak, but he’s carrying {team} to Mount Doom.",
            f"⚡ Yer a wizard, **{user}**. You've got **Harry Potter** at {team} as your **{count}** generational spark.",
            f"🔨 **Thor** has landed. **{user}** has **{count}** generational freak at {team}. Are you worthy?",
            f"🏀 **Michael Jordan** energy. **{user}** at {team} has **{count}** generational freak who takes everything personally.",
            f"🍄 It’s-a-me! **{user}** has **Mario**. **{count}** generational star at {team} leaping over the competition.",
            f"🛡️ It’s dangerous to go alone! **{user}** has **Link**. This **{count}** generational talent is the only hero {team} needs.",
            f"🪓 **Kratos** is on the warpath. **{user}** at {team} has **{count}** generational 'God of War' ready to dismantle defenses.",
            f"🔫 Finish the Fight. **{user}** has **Master Chief** at {team}. **{count}** generational Spartan on the field.",
            f"🍻 **Stone Cold Steve Austin** energy. **{user}** has **{count}** generational freak at {team} ready to stun the league.",
            f"🤨 The most electrifying man! **{user}** has **The Rock** at {team} as their **{count}** generational talent.",
            f"🚫 **John Cena** is here. **{user}** has **{count}** generational freak at {team}, but You Can’t See Him!",
            f"🤘 Rated R Superstar! **{user}** has **Edge**. **{count}** generational freak ready to spear the competition at {team}.",
            f"🦂 It’s Showtime! **{user}** has **Sting**. **{count}** generational vigilante at {team} dropping from the rafters.",
            f"👑 OHHH YEAH! **{user}** has the **Macho Man**. **{count}** generational talent at {team} and the cream is rising."
        ]
    elif count == 2:
        pool = [
            f"🍄 **Mario & Luigi** have entered! **{user}** at {team} has **{count}** generational freaks making everyone else look like Koopas.",
            f"🪵 GET THE TABLES! **{user}** has the **Dudley Boyz**. **{count}** generational specimens at {team} ready for a 3-D.",
            f"🤘 **Edge & Christian**! **{user}** at {team} has **{count}** generational freaks reeking of awesomeness.",
            f"🦅 **The Road Warriors**! **{user}** has **{count}** generational monsters at {team}. What a rush!",
            f"👯 **The Bella Twins**! **{user}** at {team} has **{count}** generational freaks running twin magic on the field.",
            f"🎨 **The Hardy Boyz**! **{user}** has **{count}** generational high-flyers at {team} ready to Twist Fate.",
            f"🐺 **The Outsiders**! **{user}** has **{count}** generational freaks at {team} taking over the league.",
            f"🔥 **Brothers of Destruction**! **{user}** has **{count}** terrifying generational talents at {team}.",
            f"🐶 **The Steiner Brothers**! **{user}** at {team} has **{count}** generational freaks. The math says you're gonna lose!",
            f"⚔️ **Han Solo & Chewbacca**! **{user}** has the perfect pairing of **{count}** generational talents at {team}."
        ]
    else:
        pool = [
            f"🦸 **The Avengers** have assembled! **{user}** is leading **{count}** generational freaks at {team}. Earth's mightiest roster.",
            f"⚖️ **The Justice League** is here! **{user}** has **{count}** generational specimens at {team} ready to save the season.",
            f"🎤 Bye Bye Bye! **{user}** has **{count}** generational freaks at {team} moving like **N'Sync** in a music video.",
            f"🎶 I Want It That Way! **{user}** is managing a **Backstreet Boys** level lineup of **{count}** generational talents at {team}.",
            f"🌡️ It's getting hot in here! **{user}** has **{count}** generational freaks at {team} bringing that **98 Degrees** heat.",
            f"🐢 **Teenage Mutant Ninja Turtles**! **{user}** has **{count}** generational freaks at {team} ready to come out of the shells.",
            f"⚡ **The X-Men**! **{user}** at {team} has **{count}** generational mutants that the league simply cannot contain.",
            f"🕵️ **The Fellowship**! **{user}** has **{count}** generational freaks at {team} on a quest for the title.",
            f"🏎️ **The Fast Family**! **{user}** has **{count}** generational freaks at {team}. It's all about family (and 99 speed).",
            f"🌟 **The Spice Girls**! **{user}** at {team} has **{count}** generational freaks. Tell them what you want, what you really, really want."
        ]
    return random.choice(pool)

# --- UI EXECUTION ---
data = load_data()
if data:
    scores, stats, all_users, years, meta, champs_df, r_2041, h2h_df, rec_long = data
    tabs = st.tabs([
        "🏆 Prestige", 
        "⚔️ H2H Records", 
        "📺 Season Recap", 
        "📊 Team Analysis", 
        "🚀 2041 Scout & Projections", 
        "🔍 Talent Profile",
        "🌐 2041 Executive Outlook"
    ])

    with tabs[0]:
        st.subheader("The Dynasty Hall of Fame")
        st.dataframe(stats[['User', 'HoF Points', 'Record', 'Natties', 'Drafted', '1st Rounders', 'Avg Recruiting Rank']], hide_index=True)

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
        c2.metric("Overall", row['OVERALL'])
        c3.metric("Projected Record", row['2041 Projection'])
        c4.metric("Star Player", row['⭐ STAR SKILL GUY (Top OVR)'])

        st.markdown(f"### 📋 Scouting Report: {target}")
        
        is_star_gen = "is a **Generational Speed Talent**" if str(row['Star Skill Guy is Generational Speed?']).lower() == 'yes' else "does not possess generational speed metrics"
        off_speed_val = row['Off Speed (90+ speed)']
        def_speed_val = row['Def Speed (90+ speed)']
        
        if off_speed_val >= 5 and def_speed_val >= 5:
            speed_narrative = "possesses **good speed on both sides of the ball**."
        elif off_speed_val >= 5:
            speed_narrative = "features **good speed on offense**."
        elif def_speed_val >= 5:
            speed_narrative = "boasts **good speed on defense**."
        else:
            speed_narrative = "currently **lacks elite team-wide speed**."

        analysis = f"Under Coach {target}, **{row['TEAM']}** has established a **{row['OVERALL']} OVR** roster. "
        analysis += f"Their primary star, **{row['⭐ STAR SKILL GUY (Top OVR)']}**, {is_star_gen}. "
        analysis += f"This team {speed_narrative} "
        
        if row['Generational (96+ speed or 96+ Acceleration)'] > 0:
            analysis += f"Furthermore, opponents must account for **{int(row['Generational (96+ speed or 96+ Acceleration)'])}** total generational freaks. "
        
        analysis += f"Historically, this coach has an average recruiting rank of **{u_stats['Avg Recruiting Rank']}**."
        st.write(analysis)

    with tabs[4]:
        st.header("🚀 2041 Scout & Full Ratings")
        st.dataframe(r_2041, hide_index=True)

    with tabs[5]:
        st.header("🔍 Generational Talent Tracker")
        gen_df = r_2041.sort_values('Generational (96+ speed or 96+ Acceleration)', ascending=False)
        for _, r in gen_df.iterrows():
            cnt = int(r['Generational (96+ speed or 96+ Acceleration)'])
            msg = get_gen_freak_commentary(r['USER'], r['TEAM'], cnt)
            if cnt >= 3:
                st.error(msg)
            elif cnt == 2:
                st.warning(msg)
            elif cnt == 1:
                st.success(msg)
            else:
                st.info(msg)

    with tabs[6]:
        st.header("🌐 2041 Executive League Outlook")
        
        # Summary Metrics
        sm1, sm2, sm3, sm4 = st.columns(4)
        sm1.metric("Sonic Booms 🚀", len(r_2041[r_2041['Archetype'] == "Sonic Boom"]))
        sm2.metric("Glass Cannons 🔫", len(r_2041[r_2041['Archetype'] == "Glass Cannon"]))
        sm3.metric("Iron Curtains 🛡️", len(r_2041[r_2041['Archetype'] == "Iron Curtain"]))
        sm4.metric("Sluggish Giants 🕯️", len(r_2041[r_2041['Archetype'] == "Sluggish Giant"]))
        
        st.markdown("---")
        
        # Velocity Analysis Chart
        st.subheader("📉 The Velocity Gap: Team Speed Correlation")
        fig = px.scatter(r_2041, x="Off Speed (90+ speed)", y="Def Speed (90+ speed)", 
                         color="Archetype", size="OVERALL", hover_name="TEAM",
                         text="USER", title="2041 Speed Landscape (Size = Team OVR)")
        st.plotly_chart(fig, use_container_width=True)
        
        # Archetype Table
        st.subheader("📋 Team Archetype Classifications")
        outlook_tbl = r_2041[['USER', 'TEAM', 'Archetype', 'Icon', 'Outlook Description']].sort_values(by='Archetype')
        st.dataframe(outlook_tbl, hide_index=True, use_container_width=True)

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()