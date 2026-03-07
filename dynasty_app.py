
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- PAGE SETUP ---
st.set_page_config(page_title="Island Dynasty HQ", layout="wide", page_icon="🏈")
st.title("🏈 Island Dynasty: The Executive Suite")

st.markdown("""
<style>
.block-container {padding-top: 1rem; padding-bottom: 1rem; padding-left: 0.8rem; padding-right: 0.8rem;}
[data-testid="stHorizontalBlock"] {gap: 0.75rem;}
.stTabs [data-baseweb="tab-list"] {gap: 0.25rem; flex-wrap: wrap;}
.stTabs [data-baseweb="tab"] {height: auto; white-space: normal; padding-top: 0.35rem; padding-bottom: 0.35rem;}
@media (max-width: 768px) {
  .block-container {padding-left: 0.5rem; padding-right: 0.5rem;}
  h1 {font-size: 1.5rem !important;}
  h2 {font-size: 1.2rem !important;}
  h3 {font-size: 1.05rem !important;}
}
</style>
""", unsafe_allow_html=True)


TEAM_VISUALS = {
    "Florida": {"slug": "florida", "primary": "#0021A5"},
    "Florida State": {"slug": "florida-state", "primary": "#782F40"},
    "Texas Tech": {"slug": "texas-tech", "primary": "#CC0000"},
    "USF": {"slug": "south-florida", "primary": "#006747"},
    "San Jose State": {"slug": "san-jose-state", "primary": "#0055A2"},
    "Bowling Green": {"slug": "bowling-green", "primary": "#4F2D7F"},
}

def get_team_logo_url(team):
    team = str(team).strip()
    if not team or team.lower() == 'nan':
        return ""
    slug = TEAM_VISUALS.get(team, {}).get("slug")
    if not slug:
        slug = team.lower().replace("&", "and").replace(".", "").replace("'", "").replace(" ", "-")
    return f"https://a.espncdn.com/i/teamlogos/ncaa/500/{slug}.png"

def get_team_primary_color(team):
    team = str(team).strip()
    return TEAM_VISUALS.get(team, {}).get("primary", "#1f77b4")

def build_user_color_map(model_df):
    if model_df is None or model_df.empty:
        return {}
    return {str(r["USER"]).strip().title(): get_team_primary_color(r["TEAM"]) for _, r in model_df[["USER", "TEAM"]].drop_duplicates().iterrows()}

def build_team_color_map(model_df):
    if model_df is None or model_df.empty:
        return {}
    return {str(r["TEAM"]).strip(): get_team_primary_color(r["TEAM"]) for _, r in model_df[["TEAM"]].drop_duplicates().iterrows()}

def render_logo(url, width=52):
    try:
        if isinstance(url, str) and url.strip():
            st.image(url, width=width)
        else:
            st.markdown("<div style='font-size:2rem;line-height:1;'>🏈</div>", unsafe_allow_html=True)
    except Exception:
        st.markdown("<div style='font-size:2rem;line-height:1;'>🏈</div>", unsafe_allow_html=True)

def ensure_columns(df, defaults):
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default
    return df



def smart_col(df, target_names):
    for target in target_names:
        for col in df.columns:
            if col.strip().lower() == target.lower():
                return col
    return None


def get_pop_culture_speed_comp(gens):
    gens = int(max(0, gens))
    one_refs = [
        "Neo bending the code of the Matrix",
        "Sonic hitting turbo with zero respect for physics",
        "The Flash turning the corner before the defense blinks",
        "Mario grabbing a Starman and refusing to be tackled",
        "John Wick with a clean lane and a personal grudge"
    ]
    multi_refs = {
        2: [
            "Batman and Robin",
            "Mario and Luigi",
            "Han Solo and Chewbacca",
            "Abbott and Costello in shoulder pads",
            "Shawn Michaels and Triple H, a.k.a. D-Generation X"
        ],
        3: [
            "the Three Hunters from Halo 3 co-op",
            "the Powerpuff Girls on a sugar rush",
            "Destiny's Child harmonizing in open space",
            "the Three Amigos riding into your secondary"
        ],
        4: [
            "the Teenage Mutant Ninja Turtles",
            "the Ghostbusters pulling up with proton packs",
            "the A-Team if every member ran a 4.2",
            "the Fantastic Four with track spikes"
        ],
        5: [
            "the Avengers core lineup assembling in the slot",
            "the Fellowship's fastest five skipping the walking montage",
            "the Jackson 5 but all of them are vertical threats"
        ],
        6: [
            "the Sinister Six if they majored in yards after catch",
            "the original Mighty Morphin Power Rangers plus the Green Ranger",
            "a six-man ladder match where everyone somehow runs sub-4.4"
        ],
        7: [
            "the Seven from The Boys if every one of them played skill positions",
            "the Seven Dwarfs after a suspicious offseason speed program",
            "Seven Samurai in spread formation"
        ],
        8: [
            "the Ocean's Eleven scouting department trimmed down to its fastest eight",
            "the eight gym leaders before your badge case is full",
            "a Mario Kart lobby where nobody lifts off the gas"
        ]
    }
    if gens == 0:
        return "No crossover event here. This roster is light on comic-book speed and has to win the old-fashioned way."
    if gens == 1:
        return f"This team has one true superweapon: think {one_refs[gens % len(one_refs)]}. Everything dangerous starts with that one mutant."
    if gens in multi_refs:
        ref = multi_refs[gens][gens % len(multi_refs[gens])]
        return f"This is no longer one problem. It's {ref} showing up on the same depth chart."
    return f"{gens} generational freaks is basically an Avengers-level crossover event. The scouting report just says 'good luck.'"




def team_speed_to_mph(team_speed_score):
    team_speed_score = float(max(0, team_speed_score))
    # 40 points is the posted 65 MPH speed limit. Above that, the program is officially speeding.
    return round((team_speed_score / 40.0) * 65.0, 1)


def get_speeding_label(team_speed_score, gens=0):
    mph = team_speed_to_mph(team_speed_score)
    over = round(mph - 65.0, 1)
    gens = int(max(0, gens))

    freak_flair = {
        0: "No generational freaks under the hood, so this is more tuned machine than nitrous dragster.",
        1: "One generational freak is riding shotgun like the hero in the third act.",
        2: "Two freaks means this is a buddy-cop chase scene with both leads outrunning helicopters.",
        3: "Three freaks turns this into a full-on superteam convoy.",
        4: "Four freaks means the whole crew just jumped into the van together.",
        5: "Five freaks means the road is basically full of boss-fight energy.",
        6: "Six freaks means this roster is running a Fast & Furious crossover under the hood.",
    }
    freak_note = freak_flair.get(gens, f"{gens} freaks means this is less a car and more a comic-book pursuit sequence.")

    if over <= 0:
        base = f"{mph} MPH in a 65 — technically legal, but the engine is humming."
    elif over <= 10:
        base = f"{mph} MPH in a 65 — light speeding, officer is taking a second look."
    elif over <= 20:
        base = f"{mph} MPH in a 65 — this team is getting pulled over on sight."
    elif over <= 35:
        base = f"{mph} MPH in a 65 — reckless acceleration with no regard for public safety."
    else:
        base = f"{mph} MPH in a 65 — felony-level speed. Defensive coordinators should call a lawyer."
    return f"{base} {freak_note}"

def get_speed_tier(team_speed_score):
    if team_speed_score >= 92:
        return "☣️ MULTIVERSE THREAT"
    if team_speed_score >= 82:
        return "⚡ GOD-TIER VELOCITY"
    if team_speed_score >= 72:
        return "🧨 DYNAMITE DEPTH"
    if team_speed_score >= 62:
        return "🚀 SONIC BOOM"
    if team_speed_score >= 52:
        return "🏎️ ROADRUNNER"
    if team_speed_score >= 42:
        return "🔥 TRACK TEAM ENERGY"
    return "🐢 GROUND & POUND"


def clean_rank_value(val):
    if pd.isna(val):
        return np.nan
    s = str(val).strip().replace('*', '')
    try:
        return float(s)
    except Exception:
        return np.nan


def safe_title_series(series):
    return series.astype(str).str.strip().str.title()


def yes_no_flag(val):
    return str(val).strip().lower() == 'yes'

def normalize_yes_no_columns(df, cols):
    for col in cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()
    return df

def qb_label(row):
    if yes_no_flag(row.get('QB is Elite (90+)', 'No')):
        return 'Elite'
    if yes_no_flag(row.get('QB is Leader (85+)', 'No')):
        return 'Leader'
    if yes_no_flag(row.get('QB is Average Joe (between 80 and 84)', 'No')):
        return 'Average Joe'
    if yes_no_flag(row.get('Qb is Ass (under 80)', 'No')):
        return 'Ass'
    qb_ovr = pd.to_numeric(row.get('QB OVR', np.nan), errors='coerce')
    if pd.isna(qb_ovr):
        return 'Unknown'
    if qb_ovr >= 90:
        return 'Elite'
    if qb_ovr >= 85:
        return 'Leader'
    if qb_ovr >= 80:
        return 'Average Joe'
    return 'Ass'

def cfp_rank_bonus(rank_value):
    rank = pd.to_numeric(rank_value, errors='coerce')
    if pd.isna(rank):
        return 0.0
    rank = max(1.0, float(rank))
    return max(0.0, 28.0 - rank) * 2.2


def get_record_parts(record_str):
    try:
        wins, losses = str(record_str).split('-')
        return int(wins), int(losses)
    except Exception:
        return 0, 0


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

        # STANDARDIZE MAJOR TEXT FIELDS
        draft['USER'] = safe_title_series(draft['USER'])
        rec['USER'] = safe_title_series(rec['USER'])
        if 'Teams' in rec.columns:
            rec['Teams'] = rec['Teams'].astype(str).str.strip()
        champs['user'] = safe_title_series(champs['user'])
        champs['Team'] = champs['Team'].astype(str).str.strip()
        ratings['USER'] = safe_title_series(ratings['USER'])
        ratings['TEAM'] = ratings['TEAM'].astype(str).str.strip()
        heisman['USER'] = safe_title_series(heisman['USER'])
        heisman['TEAM'] = heisman['TEAM'].astype(str).str.strip()
        coty['User'] = safe_title_series(coty['User'])
        coty['Team'] = coty['Team'].astype(str).str.strip()

        # STANDARDIZE KEYS
        v_user_key = smart_col(scores, ['Vis_User', 'Visitor User', 'Vis User'])
        h_user_key = smart_col(scores, ['Home_User', 'Home User'])
        v_score_key = smart_col(scores, ['Vis Score', 'Vis_Score'])
        h_score_key = smart_col(scores, ['Home Score', 'Home_Score'])
        yr_key = smart_col(scores, ['YEAR', 'Year'])
        champ_user_key = smart_col(champs, ['user', 'User', 'User of team'])

        # STANDARDIZE KEYS FOR AWARDS
        h_yr_key = smart_col(heisman, ['Year', 'YEAR'])
        h_player_key = smart_col(heisman, ['Player', 'Winner', 'Name', 'NAME'])
        h_school_key = smart_col(heisman, ['School', 'Team', 'University', 'TEAM'])
        h_user_key_award = smart_col(heisman, ['User', 'USER'])
        c_yr_key = smart_col(coty, ['Year', 'YEAR'])
        c_coach_key = smart_col(coty, ['Coach', 'Winner', 'Name'])
        c_school_key = smart_col(coty, ['School', 'Team', 'University'])
        c_user_key_award = smart_col(coty, ['User', 'USER'])

        # CLEAN SCORES
        scores['V_User_Final'] = safe_title_series(scores[v_user_key])
        scores['H_User_Final'] = safe_title_series(scores[h_user_key])
        scores['Visitor_Final'] = scores[smart_col(scores, ['Visitor'])].astype(str).str.strip()
        scores['Home_Final'] = scores[smart_col(scores, ['Home'])].astype(str).str.strip()
        scores['V_Pts'] = pd.to_numeric(scores[v_score_key], errors='coerce')
        scores['H_Pts'] = pd.to_numeric(scores[h_score_key], errors='coerce')
        scores = scores.dropna(subset=['V_Pts', 'H_Pts']).copy()
        scores['Margin'] = (scores['H_Pts'] - scores['V_Pts']).abs()
        scores['Total Points'] = scores['H_Pts'] + scores['V_Pts']
        scores['Winner_User'] = np.where(scores['H_Pts'] > scores['V_Pts'], scores['H_User_Final'], scores['V_User_Final'])
        scores['Loser_User'] = np.where(scores['H_Pts'] > scores['V_Pts'], scores['V_User_Final'], scores['H_User_Final'])
        scores['Winner_Team'] = np.where(scores['H_Pts'] > scores['V_Pts'], scores['Home_Final'], scores['Visitor_Final'])
        scores['Loser_Team'] = np.where(scores['H_Pts'] > scores['V_Pts'], scores['Visitor_Final'], scores['Home_Final'])

        all_users = sorted([
            u for u in pd.concat([scores['V_User_Final'], scores['H_User_Final']]).dropna().unique()
            if str(u).upper() != 'CPU' and str(u).lower() != 'nan'
        ])
        years_available = sorted(pd.to_numeric(scores[yr_key], errors='coerce').dropna().astype(int).unique(), reverse=True)

        # MASTER STATS ENGINE
        stats_list, h2h_rows, h2h_numeric, rivalry_rows = [], [], [], []
        natty_counts = champs[champs[champ_user_key].str.upper() != 'CPU'][champ_user_key].value_counts().to_dict()

        for user in all_users:
            h_games = scores[scores['H_User_Final'] == user]
            v_games = scores[scores['V_User_Final'] == user]
            all_u_games = pd.concat([h_games, v_games], ignore_index=True)

            wins = len(h_games[h_games['H_Pts'] > h_games['V_Pts']]) + len(v_games[v_games['V_Pts'] > v_games['H_Pts']])
            losses = len(all_u_games) - wins

            u_draft = draft[draft['USER'] == user]
            n_sent = int(u_draft['Guys Sent to NFL'].iloc[0]) if not u_draft.empty else 0
            n_1st = int(u_draft['1st Rounders'].iloc[0]) if not u_draft.empty else 0
            conf_t = int(u_draft['Conference Titles'].iloc[0]) if not u_draft.empty else 0
            cfp_w = int(u_draft['CFP Wins'].iloc[0]) if not u_draft.empty else 0
            cfp_l = int(u_draft['CFP Losses'].iloc[0]) if not u_draft.empty else 0
            natty_a = int(u_draft['National Title Appearances'].iloc[0]) if not u_draft.empty else 0
            career_wins = int(u_draft['Career Wins'].iloc[0]) if not u_draft.empty else wins
            career_losses = int(u_draft['Career Losses'].iloc[0]) if not u_draft.empty else losses
            career_win_pct = round((career_wins / max(1, career_wins + career_losses)) * 100, 1)

            hof_points = (natty_counts.get(user, 0) * 50) + (n_1st * 10)
            goat_score = (
                natty_counts.get(user, 0) * 200
                + natty_a * 80
                + cfp_w * 40
                + conf_t * 25
                + n_1st * 12
                + n_sent * 4
            )
            dynasty_score = (
                natty_counts.get(user, 0) * 100
                + natty_a * 40
                + cfp_w * 25
                + conf_t * 15
                + n_1st * 8
                + n_sent * 3
            )

            stats_list.append({
                'User': user,
                'HoF Points': int(hof_points),
                'GOAT Score': int(goat_score),
                'Dynasty Score': int(dynasty_score),
                'Record': f"{wins}-{losses}",
                'Career Record': f"{career_wins}-{career_losses}",
                'Career Win %': career_win_pct,
                'Natties': natty_counts.get(user, 0),
                'Drafted': n_sent,
                '1st Rounders': n_1st,
                'Conf Titles': conf_t,
                'CFP Wins': cfp_w,
                'CFP Losses': cfp_l,
                'Natty Apps': natty_a,
            })

            h2h_row = {'User': user}
            h2h_num_row = []
            for opp in all_users:
                if user == opp:
                    h2h_row[opp] = "-"
                    h2h_num_row.append(0)
                else:
                    vs = scores[
                        ((scores['V_User_Final'] == user) & (scores['H_User_Final'] == opp)) |
                        ((scores['V_User_Final'] == opp) & (scores['H_User_Final'] == user))
                    ]
                    vw = len(vs[
                        ((vs['V_User_Final'] == user) & (vs['V_Pts'] > vs['H_Pts'])) |
                        ((vs['H_User_Final'] == user) & (vs['H_Pts'] > vs['V_Pts']))
                    ])
                    vl = len(vs) - vw
                    h2h_row[opp] = f"{vw}-{vl}"
                    h2h_num_row.append(vw - vl)

                    if user < opp and len(vs) > 0:
                        balance = 1 - (abs(vw - vl) / max(1, len(vs)))
                        rivalry_score = round((len(vs) * 2.5) + (balance * 10), 1)
                        rivalry_rows.append({
                            'Matchup': f"{user} vs {opp}",
                            'Games': int(len(vs)),
                            user: vw,
                            opp: vl,
                            'Balance': round(balance, 2),
                            'Avg Margin': round(vs['Margin'].mean(), 1),
                            'Rivalry Score': rivalry_score
                        })

            h2h_rows.append(h2h_row)
            h2h_numeric.append(h2h_num_row)

        stats_df = pd.DataFrame(stats_list)
        h2h_df = pd.DataFrame(h2h_rows)
        h2h_heat = pd.DataFrame(h2h_numeric, index=all_users, columns=all_users)
        rivalry_df = pd.DataFrame(rivalry_rows).sort_values(['Rivalry Score', 'Games'], ascending=[False, False]) if rivalry_rows else pd.DataFrame()

        # Ratings prep
        r_2041 = ratings[ratings['YEAR'] == 2041].copy()
        r_2040 = ratings[ratings['YEAR'] == 2040].copy()
        r_2041['USER'] = safe_title_series(r_2041['USER'])
        r_2040['USER'] = safe_title_series(r_2040['USER'])
        r_2041['TEAM'] = r_2041['TEAM'].astype(str).str.strip()
        r_2040['TEAM'] = r_2040['TEAM'].astype(str).str.strip()

        bcr_col = 'Blue Chip Ratio (4 & 5 star recruit ratio on roster)'
        r_2041['BCR_Val'] = pd.to_numeric(r_2041[bcr_col].astype(str).str.replace('%', '', regex=False), errors='coerce').fillna(0)
        r_2040['BCR_Val'] = pd.to_numeric(r_2040[bcr_col].astype(str).str.replace('%', '', regex=False), errors='coerce').fillna(0)

        yes_no_cols = [
            'QB is Elite (90+)',
            'QB is Leader (85+)',
            'QB is Average Joe (between 80 and 84)',
            'Qb is Ass (under 80)',
            'Star Skill Guy is Generational Speed?'
        ]
        r_2041 = normalize_yes_no_columns(r_2041, yes_no_cols)
        r_2040 = normalize_yes_no_columns(r_2040, yes_no_cols)

        for num_col in [
            'OVERALL', 'OFFENSE', 'DEFENSE', 'Team Speed (90+ Speed Guys)',
            'Def Speed (90+ speed)', 'Off Speed (90+ speed)',
            'Game Breakers (90+ Speed & 90+ Acceleration)',
            'Generational (96+ speed or 96+ Acceleration)',
            'Current CFP Ranking', 'QB OVR'
        ]:
            if num_col in r_2041.columns:
                r_2041[num_col] = pd.to_numeric(r_2041[num_col], errors='coerce')
            if num_col in r_2040.columns:
                r_2040[num_col] = pd.to_numeric(r_2040[num_col], errors='coerce')

        def get_improvement(row):
            prev = r_2040[r_2040['TEAM'].str.lower() == str(row['TEAM']).strip().lower()]
            return int(row['OVERALL'] - prev['OVERALL'].values[0]) if not prev.empty else 0

        r_2041['Improvement'] = r_2041.apply(get_improvement, axis=1)

        meta = {
            'yr': yr_key,
            'vt': smart_col(scores, ['Visitor']),
            'vs': v_score_key,
            'ht': smart_col(scores, ['Home']),
            'hs': h_score_key,
            'h_yr': h_yr_key,
            'h_player': h_player_key,
            'h_school': h_school_key,
            'h_user': h_user_key_award,
            'c_yr': c_yr_key,
            'c_coach': c_coach_key,
            'c_school': c_school_key,
            'c_user': c_user_key_award,
        }

        return {
            'scores': scores,
            'stats': stats_df,
            'all_users': all_users,
            'years': years_available,
            'meta': meta,
            'r_2041': r_2041,
            'h2h_df': h2h_df,
            'h2h_heat': h2h_heat,
            'rivalry_df': rivalry_df,
            'coty': coty,
            'heisman': heisman,
            'rec': rec,
            'draft': draft,
            'champs': champs,
        }
    except Exception as e:
        st.error(f"⚠️ Load Error: {e}")
        return None


def get_recent_recruiting_score(rec_df, user, team=None, current_year=2041, lookback=3):
    user = str(user).strip().title()
    rows = rec_df[rec_df['USER'] == user].copy()

    if team is not None and 'Teams' in rec_df.columns:
        rows_team = rows[rows['Teams'].astype(str).str.strip().str.lower() == str(team).strip().lower()]
        if not rows_team.empty:
            rows = rows_team

    if rows.empty:
        return 50.0

    vals = []
    for y in range(current_year - lookback + 1, current_year + 1):
        col = str(y)
        if col in rows.columns:
            for _, row in rows.iterrows():
                v = clean_rank_value(row[col])
                if not pd.isna(v):
                    vals.append(v)

    if not vals:
        historic_cols = [c for c in rows.columns if str(c).isdigit()]
        for col in historic_cols[-lookback:]:
            for _, row in rows.iterrows():
                v = clean_rank_value(row[col])
                if not pd.isna(v):
                    vals.append(v)

    if not vals:
        return 50.0

    avg_rank = float(np.mean(vals))
    return float(max(1, min(100, 101 - avg_rank)))



def build_2041_model_table(r_2041, stats_df, rec_df):
    df = r_2041.copy()

    stats_lookup = stats_df[['User', 'Career Win %', 'Career Record', 'Natties', 'Natty Apps', 'CFP Wins', 'CFP Losses', 'Conf Titles']].copy()
    stats_lookup = stats_lookup.rename(columns={'User': 'USER'})
    df = df.merge(stats_lookup, on='USER', how='left')

    df['Career Win %'] = pd.to_numeric(df['Career Win %'], errors='coerce').fillna(50.0)
    df['Recruit Score'] = df.apply(lambda x: get_recent_recruiting_score(rec_df, x['USER'], x['TEAM']), axis=1)
    df['QB Tier'] = df.apply(qb_label, axis=1)

    def qb_natty_bonus(row):
        if row['QB Tier'] == 'Elite':
            return 30.0
        if row['QB Tier'] == 'Leader':
            return 18.0
        if row['QB Tier'] == 'Average Joe':
            return -10.0
        if row['QB Tier'] == 'Ass':
            return -26.0
        return 0.0

    def qb_playoff_bonus(row):
        if row['QB Tier'] == 'Elite':
            return 22.0
        if row['QB Tier'] == 'Leader':
            return 13.0
        if row['QB Tier'] == 'Average Joe':
            return -8.0
        if row['QB Tier'] == 'Ass':
            return -20.0
        return 0.0

    def raw_contender_score(row):
        u_s = stats_df[stats_df['User'] == row['USER']].iloc[0]

        pedigree_bonus = (
            u_s['Natties'] * 18
            + u_s['Natty Apps'] * 11
            + u_s['CFP Wins'] * 3.0
            + u_s['Conf Titles'] * 1.4
        )
        heartbreak_penalty = max(0, u_s['Natty Apps'] - u_s['Natties']) * 1.2
        playoff_fail_penalty = u_s['CFP Losses'] * 1.2

        team_speed_component = (
            row['Team Speed (90+ Speed Guys)'] * 2.7
            + row['Off Speed (90+ speed)'] * 1.45
            + row['Def Speed (90+ speed)'] * 1.45
        )
        cfp_bonus = cfp_rank_bonus(row.get('Current CFP Ranking', np.nan))

        raw = (
            row['OVERALL'] * 3.45
            + row['OFFENSE'] * 0.66
            + row['DEFENSE'] * 0.66
            + team_speed_component
            + row['Game Breakers (90+ Speed & 90+ Acceleration)'] * 1.55
            + row['Generational (96+ speed or 96+ Acceleration)'] * 6.8
            + row['BCR_Val'] * 0.52
            + row['Recruit Score'] * 0.30
            + row['Career Win %'] * 0.34
            + cfp_bonus
            + qb_natty_bonus(row)
            + pedigree_bonus
            - heartbreak_penalty
            - playoff_fail_penalty
        )

        if row['OVERALL'] < 88:
            raw -= 24
        if row['OFFENSE'] < 85:
            raw -= 6
        if row['DEFENSE'] < 85:
            raw -= 6
        if row['BCR_Val'] < 35:
            raw -= 6
        if row['Team Speed (90+ Speed Guys)'] < 10:
            raw -= 5
        return raw

    df['Contender Raw'] = df.apply(raw_contender_score, axis=1)

    temp = max(10.5, df['Contender Raw'].std() * 0.95)
    raw_shift = df['Contender Raw'] - df['Contender Raw'].max()
    exp_scores = np.exp(raw_shift / temp)
    natty_probs = (exp_scores / exp_scores.sum()) * 100
    df['Natty Odds'] = natty_probs.round(1)

    def stock_label(row):
        if row['Natty Odds'] >= 24 and row['Improvement'] >= 0:
            return "🚀 Surging"
        if row['Natty Odds'] >= 17:
            return "📈 Rising"
        if row['Improvement'] <= -2 or row['OVERALL'] < 82:
            return "📉 In Trouble"
        return "➖ Stable"

    df['Program Stock'] = df.apply(stock_label, axis=1)

    def power_index(row):
        return round(
            row['OVERALL'] * 2.15
            + row['OFFENSE'] * 0.82
            + row['DEFENSE'] * 0.82
            + row['Team Speed (90+ Speed Guys)'] * 2.0
            + row['Game Breakers (90+ Speed & 90+ Acceleration)'] * 1.55
            + row['Generational (96+ speed or 96+ Acceleration)'] * 5.1
            + row['BCR_Val'] * 0.56
            + row['Recruit Score'] * 0.46
            + row['Improvement'] * 4.0
            + row['Career Win %'] * 0.72
            + cfp_rank_bonus(row.get('Current CFP Ranking', np.nan)) * 0.75
            + qb_playoff_bonus(row) * 0.9
            + row['Natties'] * 10.5
            + row['Natty Apps'] * 3.2
            + row['CFP Wins'] * 1.2
            - row['CFP Losses'] * 1.2,
            1
        )

    df['Power Index'] = df.apply(power_index, axis=1)
    df['Team Speed Score'] = (
        df['Team Speed (90+ Speed Guys)'] * 2.2
        + df['Off Speed (90+ speed)'] * 1.0
        + df['Def Speed (90+ speed)'] * 1.0
        + df['Game Breakers (90+ Speed & 90+ Acceleration)'] * 1.8
    ) * (1 + df['Generational (96+ speed or 96+ Acceleration)'] * 0.16)
    df['Team Speed Score'] = df['Team Speed Score'].round(1)
    df['Speedometer'] = df['Team Speed Score'].apply(team_speed_to_mph)

    def where_is_the_speed(row):
        off_fast = row['Off Speed (90+ speed)'] > 5
        def_fast = row['Def Speed (90+ speed)'] > 5
        mph = pd.to_numeric(row.get('Speedometer', np.nan), errors='coerce')
        if (not off_fast) and (not def_fast) and (not pd.isna(mph)) and mph < 65:
            return 'Non-Existent'
        if off_fast and def_fast:
            return 'Off & Def'
        if off_fast:
            return 'Offense'
        if def_fast:
            return 'Defense'
        return 'Balanced'

    df['Where is the Speed?'] = df.apply(where_is_the_speed, axis=1)

    playoff_raw = (
        df['Power Index'] * 0.70
        + df['OVERALL'] * 1.25
        + df['Team Speed (90+ Speed Guys)'] * 1.8
        + df['Off Speed (90+ speed)'] * 0.7
        + df['Def Speed (90+ speed)'] * 0.7
        + df['Game Breakers (90+ Speed & 90+ Acceleration)'] * 1.2
        + df['Generational (96+ speed or 96+ Acceleration)'] * 3.0
        + df['Recruit Score'] * 0.22
        + df['Career Win %'] * 0.20
        + df['Current CFP Ranking'].apply(cfp_rank_bonus) * 1.7
        + df.apply(qb_playoff_bonus, axis=1)
        + df['Natty Apps'] * 1.9
        + df['Natties'] * 2.7
    )
    playoff_min = playoff_raw.min()
    playoff_spread = max(1, playoff_raw.max() - playoff_min)
    df['CFP Odds'] = (18 + ((playoff_raw - playoff_min) / playoff_spread * 62)).round(0).astype(int)
    df['CFP Odds'] = df['CFP Odds'].clip(lower=14, upper=80)

    power_min = df['Power Index'].min()
    power_max = df['Power Index'].max()
    power_spread = max(1, power_max - power_min)
    df['Projected Wins'] = (6.2 + ((df['Power Index'] - power_min) / power_spread * 5.3)).round(1)
    df['Projected Wins'] = df['Projected Wins'].clip(lower=5.5, upper=11.5)

    df['Collapse Risk'] = (
        66
        - (df['OVERALL'] - 80) * 2.0
        - df['Improvement'] * 4.5
        - df['BCR_Val'] * 0.35
        - df['Recruit Score'] * 0.20
        - df['Generational (96+ speed or 96+ Acceleration)'] * 3.0
        - df['Current CFP Ranking'].apply(cfp_rank_bonus) * 0.25
        - df.apply(qb_playoff_bonus, axis=1) * 0.4
    ).round(0).astype(int)
    df['Collapse Risk'] = df['Collapse Risk'].clip(lower=8, upper=72)

    return df.sort_values(['Power Index', 'Natty Odds'], ascending=False).reset_index(drop=True)



def project_loss_scenarios(row):
    natty = float(pd.to_numeric(row.get('Natty Odds', 0), errors='coerce'))
    cfp = float(pd.to_numeric(row.get('CFP Odds', 0), errors='coerce'))
    overall = float(pd.to_numeric(row.get('OVERALL', 0), errors='coerce'))
    team_speed = float(pd.to_numeric(row.get('Team Speed (90+ Speed Guys)', 0), errors='coerce'))
    qb_tier = str(row.get('QB Tier', '')).strip()
    cfp_rank = row.get('Current CFP Ranking', np.nan)
    ranked_now = pd.notna(cfp_rank)

    base_unranked_natty_drop = 7.5
    base_ranked_natty_drop = 4.0
    base_unranked_cfp_drop = 16.0
    base_ranked_cfp_drop = 8.0

    if overall >= 90:
        base_unranked_natty_drop += 2.0
        base_unranked_cfp_drop += 2.5
    elif overall <= 84:
        base_ranked_natty_drop += 1.0
        base_ranked_cfp_drop += 2.0

    if team_speed >= 12:
        base_unranked_natty_drop += 1.5
        base_unranked_cfp_drop += 1.5

    if qb_tier == 'Elite':
        base_unranked_natty_drop += 1.8
        base_ranked_natty_drop += 0.8
        base_unranked_cfp_drop += 1.8
        base_ranked_cfp_drop += 0.8
    elif qb_tier == 'Leader':
        base_unranked_natty_drop += 1.0
        base_ranked_natty_drop += 0.4
        base_unranked_cfp_drop += 1.0
        base_ranked_cfp_drop += 0.4
    elif qb_tier == 'Ass':
        base_unranked_natty_drop -= 1.0
        base_ranked_natty_drop -= 0.5
        base_unranked_cfp_drop -= 1.5
        base_ranked_cfp_drop -= 1.0

    if ranked_now:
        base_unranked_natty_drop += 1.8
        base_unranked_cfp_drop += 3.0

    natty_unranked = max(0.1, round(natty - base_unranked_natty_drop, 1))
    natty_ranked = max(0.1, round(natty - base_ranked_natty_drop, 1))
    cfp_unranked = max(1, int(round(cfp - base_unranked_cfp_drop, 0)))
    cfp_ranked = max(1, int(round(cfp - base_ranked_cfp_drop, 0)))

    return pd.Series({
        'Natty if Lose to Unranked': natty_unranked,
        'Natty if Lose to Ranked': natty_ranked,
        'CFP if Lose to Unranked': cfp_unranked,
        'CFP if Lose to Ranked': cfp_ranked
    })


def get_team_schedule_summary(scores_df, user):
    user = str(user).strip().title()
    games = scores_df[(scores_df['V_User_Final'] == user) | (scores_df['H_User_Final'] == user)].copy()

    if games.empty:
        return 0, 0, 0.0, 0.0

    wins = len(games[
        ((games['V_User_Final'] == user) & (games['V_Pts'] > games['H_Pts'])) |
        ((games['H_User_Final'] == user) & (games['H_Pts'] > games['V_Pts']))
    ])
    losses = len(games) - wins

    points_for = np.where(games['V_User_Final'] == user, games['V_Pts'], games['H_Pts']).sum()
    points_against = np.where(games['V_User_Final'] == user, games['H_Pts'], games['V_Pts']).sum()
    avg_margin = round((points_for - points_against) / max(1, len(games)), 1)

    return wins, losses, round(points_for / max(1, len(games)), 1), avg_margin


def infer_best_fun_stat(y_data):
    if y_data.empty:
        return "No games found for that season."

    closest = y_data[y_data['Margin'] == y_data['Margin'].min()].iloc[0]
    highest_scoring = y_data[y_data['Total Points'] == y_data['Total Points'].max()].iloc[0]
    blowout = y_data[y_data['Margin'] == y_data['Margin'].max()].iloc[0]

    options = [
        f"Closest game: {closest['Visitor_Final']} vs {closest['Home_Final']} ended with just a {int(closest['Margin'])}-point margin.",
        f"Track meet alert: {highest_scoring['Visitor_Final']} vs {highest_scoring['Home_Final']} combined for {int(highest_scoring['Total Points'])} points.",
        f"Beatdown of the year: {blowout['Winner_Team']} handled business by {int(blowout['Margin'])}."
    ]

    avg_margin = y_data['Margin'].mean()
    if avg_margin <= 7:
        options.append("The whole season played like a knife fight. Average margin was under one score.")
    elif avg_margin >= 20:
        options.append("A lot of Saturdays turned into statements. Average margin cleared 20 points.")

    return options[len(y_data) % len(options)]


def tier_from_dynasty_score(score):
    if score >= 650:
        return "Blue Blood"
    if score >= 450:
        return "Contender"
    if score >= 250:
        return "Builder"
    return "Upstart"


data = load_data()

if data:
    scores = data['scores']
    stats = data['stats']
    all_users = data['all_users']
    years = data['years']
    meta = data['meta']
    r_2041 = data['r_2041']
    h2h_df = data['h2h_df']
    h2h_heat = data['h2h_heat']
    rivalry_df = data['rivalry_df']
    coty = data['coty']
    heisman = data['heisman']
    rec = data['rec']
    draft = data['draft']
    champs = data['champs']

    model_2041 = build_2041_model_table(r_2041, stats, rec)
    model_2041['Logo'] = model_2041['TEAM'].apply(get_team_logo_url)
    user_color_map = build_user_color_map(model_2041)
    team_color_map = build_team_color_map(model_2041)
    # Defensive fill so UI sections never fail if a derived column is absent.
    for col, default in {
        'Program Stock': '➖ Stable',
        'Career Win %': 50.0,
        'Recruit Score': 50.0,
        'Projected Wins': 6.5,
        'CFP Odds': 20,
        'Natty Odds': 5.0,
        'Collapse Risk': 35,
        'Power Index': 200.0
    }.items():
        if col not in model_2041.columns:
            model_2041[col] = default

    scenario_df = model_2041.apply(project_loss_scenarios, axis=1)
    model_2041 = pd.concat([model_2041, scenario_df], axis=1)

    tabs = st.tabs([
        "📰 Dynasty War Room",
        "📺 Season Recap",
        "🔍 Talent Profile",
        "📊 Team Analysis",
        "🏆 Prestige & Power",
        "⚔️ H2H Matrix",
        "🚀 2041 Scout & Projections",
        "🌐 2041 Executive Outlook",
        "🧠 AI Dynasty Predictor",
        "🏫 Recruiting Momentum",
        "🚨 Upset Tracker",
        "🐐 GOAT Rankings",
    ])

    # --- WAR ROOM ---
    with tabs[0]:
        st.header("📰 Dynasty War Room")

        title_favorite = model_2041.sort_values('Natty Odds', ascending=False).iloc[0]
        most_dangerous = model_2041.sort_values('Power Index', ascending=False).iloc[0]
        best_recruiter_user = model_2041.sort_values('Recruit Score', ascending=False).iloc[0]
        collapse_team = model_2041.sort_values('Collapse Risk', ascending=False).iloc[0]
        pipeline_king = stats.sort_values('Drafted', ascending=False).iloc[0]

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Title Favorite", f"{title_favorite['USER']} ({title_favorite['Natty Odds']}%)")
        c2.metric("Power Index Leader", f"{most_dangerous['USER']}", f"{most_dangerous['Power Index']}")
        c3.metric("Recruiting King", f"{best_recruiter_user['USER']}", f"{best_recruiter_user['Recruit Score']}")
        c4.metric("Collapse Watch", collapse_team['USER'], f"{collapse_team['Collapse Risk']}%")
        c5.metric("NFL Pipeline", pipeline_king['User'], f"{pipeline_king['Drafted']} drafted")

        st.markdown("---")
        wc1, wc2 = st.columns([1.1, 0.9])

        with wc1:
            st.subheader("War Room Board")
            board_defaults = {
                'Logo': '',
                'Current CFP Ranking': np.nan,
                'Power Index': 0.0,
                'Natty Odds': 0.0,
                'CFP Odds': 0,
                'Natty if Lose to Unranked': 0.0,
                'Natty if Lose to Ranked': 0.0,
                'CFP if Lose to Unranked': 0,
                'CFP if Lose to Ranked': 0,
                'Collapse Risk': 0,
                'Program Stock': '➖ Stable'
            }
            model_2041 = ensure_columns(model_2041, board_defaults)
            board_cols = ['Logo', 'USER', 'TEAM', 'Current CFP Ranking', 'Power Index', 'Natty Odds', 'CFP Odds', 'Natty if Lose to Unranked', 'Natty if Lose to Ranked', 'CFP if Lose to Unranked', 'CFP if Lose to Ranked', 'Collapse Risk', 'Program Stock', 'QB Tier']
            board = model_2041[board_cols].copy().sort_values(['Natty Odds', 'CFP Odds', 'Power Index'], ascending=False)

            for _, r in board.iterrows():
                team_color = get_team_primary_color(r['TEAM'])
                c_logo, c_info, c_natty, c_cfp = st.columns([0.7, 1.7, 1.0, 1.0])
                with c_logo:
                    render_logo(r['Logo'])
                with c_info:
                    rank_txt = 'Unranked' if pd.isna(r['Current CFP Ranking']) else int(r['Current CFP Ranking'])
                    st.markdown(f"<div style='border-left: 6px solid {team_color}; padding-left: 0.6rem; margin-bottom: 0.35rem;'><div style='font-weight:800; font-size:1.02rem; color:{team_color};'>{r['TEAM']}</div><div style='font-size:0.93rem;'>{r['USER']} | CFP Rank: {rank_txt} | QB: {r['QB Tier']}</div><div style='font-size:0.86rem; opacity:0.88;'>Stock: {r['Program Stock']} | Power Index: {r['Power Index']}</div></div>", unsafe_allow_html=True)
                with c_natty:
                    st.metric("Natty Win %", f"{r['Natty Odds']}%")
                    st.caption(f"Unranked L: {r['Natty if Lose to Unranked']}% | Ranked L: {r['Natty if Lose to Ranked']}%")
                with c_cfp:
                    st.metric("CFP %", f"{int(r['CFP Odds'])}%")
                    st.caption(f"Unranked L: {int(r['CFP if Lose to Unranked'])}% | Ranked L: {int(r['CFP if Lose to Ranked'])}%")
                st.markdown("---")

            with st.expander("Open compact War Room table"):
                compact_board = board.rename(columns={'Current CFP Ranking': 'CFP Rank'})[[
                    'USER', 'TEAM', 'CFP Rank', 'QB Tier', 'Power Index', 'Natty Odds', 'CFP Odds',
                    'Natty if Lose to Unranked', 'Natty if Lose to Ranked',
                    'CFP if Lose to Unranked', 'CFP if Lose to Ranked', 'Collapse Risk', 'Program Stock'
                ]]
                st.dataframe(compact_board, hide_index=True, use_container_width=True)


        with wc2:
            st.subheader("Headlines")
            st.success(f"**{title_favorite['USER']}** has the strongest title case entering 2041 because the model now leans hardest on overall roster quality and raw team speed, with CFP position and pedigree finishing the damn job.")
            st.info(f"**{most_dangerous['USER']}** owns the highest overall Power Index, which blends team strength, speed, blue-chip makeup, and dynasty history.")
            st.warning(f"**{collapse_team['USER']}** carries the highest volatility marker. The model sees real downside if things break wrong.")

            qb_boost_board = model_2041[model_2041['QB Tier'].isin(['Elite', 'Leader'])].sort_values(['Natty Odds', 'Power Index'], ascending=False)
            if not qb_boost_board.empty:
                qb_star = qb_boost_board.iloc[0]
                if qb_star['QB Tier'] == 'Elite':
                    st.write(f"🧠 **QB headline:** {qb_star['USER']} has an **Elite** quarterback, and that spikes the ceiling like hell. The model treats that shit as a real title accelerator, not fluff.")
                else:
                    st.write(f"🧠 **QB headline:** {qb_star['USER']} has a **Leader** at quarterback. Not quite superhero mode, but it's still a damn meaningful bump to CFP and natty odds.")

            qb_disaster_board = model_2041[model_2041['QB Tier'] == 'Ass'].sort_values(['Natty Odds', 'Power Index'], ascending=True)
            if not qb_disaster_board.empty:
                qb_disaster = qb_disaster_board.iloc[0]
                st.write(f"💀 **QB disaster watch:** {qb_disaster['USER']} is rolling out an **Ass** QB situation. That's the kind of setup that can take a good roster and make it play like it forgot where the fuck the sticks are.")

            doug_florida = model_2041[(model_2041['USER'].astype(str).str.strip().str.title() == 'Doug') & (model_2041['TEAM'].astype(str).str.strip() == 'Florida')]
            if not doug_florida.empty:
                doug_row = doug_florida.iloc[0]
                if str(doug_row.get('QB Tier', '')).strip() == 'Ass':
                    st.write("☠️ **Doug/Florida QB update:** Florida's QB room is still ass. The Gators have enough brand power to scare people in the tunnel, then that quarterback strolls out and turns the whole damn thing into a liability test.")
                else:
                    st.write(f"ℹ️ **Doug/Florida QB check:** Latest file currently labels the Florida QB tier as **{doug_row.get('QB Tier', 'Unknown')}**.")

            if not rivalry_df.empty:
                top_rivalry = rivalry_df.sort_values('Rivalry Score', ascending=False).iloc[0]
                st.write(f"🔥 **Rivalry of the year:** {top_rivalry['Matchup']} — {int(top_rivalry['Games'])} meetings, rivalry score {top_rivalry['Rivalry Score']}.")

    # --- SCOUT & PROJECTIONS ---
    with tabs[6]:
        st.header("🚀 2041 Executive Projections")

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Title Contender Odds")
            st.dataframe(
                model_2041.sort_values('Natty Odds', ascending=False)[['USER', 'TEAM', 'OVERALL', 'Natty Odds', 'CFP Odds', 'Program Stock']],
                hide_index=True,
                use_container_width=True
            )

        with c2:
            st.subheader("Projected Risers")
            st.dataframe(
                model_2041.sort_values('Improvement', ascending=False)[['USER', 'TEAM', 'OVERALL', 'Improvement', 'Recruit Score', 'Program Stock']],
                hide_index=True,
                use_container_width=True
            )

        st.plotly_chart(
            px.bar(
                model_2041.sort_values('Natty Odds', ascending=False),
                x='USER',
                y='Natty Odds',
                color='Program Stock',
                hover_data=['TEAM', 'OVERALL', 'CFP Odds', 'Recruit Score']
            ),
            use_container_width=True
        )

    # --- PRESTIGE & POWER ---
    with tabs[4]:
        st.header("🏆 Prestige & Power")

        prestige = stats.copy()
        prestige['Dynasty Tier'] = prestige['Dynasty Score'].apply(tier_from_dynasty_score)

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Dynasty Power Rankings")
            st.dataframe(
                prestige.sort_values('Dynasty Score', ascending=False)[['User', 'Dynasty Score', 'Dynasty Tier', 'Natties', 'Natty Apps', 'CFP Wins', 'Conf Titles']],
                hide_index=True,
                use_container_width=True
            )

        with c2:
            st.subheader("Prestige Board")
            st.dataframe(
                prestige.sort_values('HoF Points', ascending=False)[['User', 'HoF Points', 'Record', 'Natties', 'Drafted', '1st Rounders']],
                hide_index=True,
                use_container_width=True
            )

        st.plotly_chart(
            px.bar(
                prestige.sort_values('Dynasty Score', ascending=False),
                x='User',
                y='Dynasty Score',
                color='Dynasty Tier',
                hover_data=['Natties', 'Natty Apps', 'CFP Wins', 'Conf Titles', 'Drafted']
            ),
            use_container_width=True
        )

    # --- H2H MATRIX ---
    with tabs[5]:
        st.header("⚔️ Head-to-Head Matrix")

        st.subheader("Full H2H Matrix")
        st.dataframe(h2h_df, hide_index=True, use_container_width=True)

        st.subheader("Rivalry Meter")
        if not rivalry_df.empty:
            st.dataframe(
                rivalry_df[['Matchup', 'Games', 'Avg Margin', 'Rivalry Score']].sort_values(['Rivalry Score', 'Games'], ascending=[False, False]),
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("No rivalry data available yet.")

        selected_user = st.selectbox("Select a user for H2H drilldown", all_users, key="h2h_select")
        drill = []
        for opp in all_users:
            if opp == selected_user:
                continue
            matchup = h2h_df[h2h_df['User'] == selected_user][opp].iloc[0]
            diff = h2h_heat.loc[selected_user, opp]
            games = 0
            wins = 0
            losses = 0
            if matchup != "-":
                parts = str(matchup).split('-')
                if len(parts) == 2:
                    wins = int(parts[0])
                    losses = int(parts[1])
                    games = wins + losses
            drill.append({
                'Opponent': opp,
                'Record': matchup,
                'Games': games,
                'Net Edge': diff
            })
        st.dataframe(pd.DataFrame(drill).sort_values(['Games', 'Net Edge'], ascending=[False, False]), hide_index=True, use_container_width=True)

    # --- SEASON RECAP ---
    with tabs[1]:
        st.header("📺 AI Dynasty Recap Engine")
        sel_year = st.selectbox("Select Season", years, key="season_year")
        y_data = scores[scores[meta['yr']] == sel_year].copy()

        champ_row = champs[champs['YEAR'] == sel_year]
        heisman_row = heisman[heisman[meta['h_yr']] == sel_year]
        coty_row = coty[coty[meta['c_yr']] == sel_year]

        c1, c2, c3 = st.columns(3)
        with c1:
            if not champ_row.empty:
                champ_text = f"{champ_row.iloc[0]['Team']} ({champ_row.iloc[0]['user']})"
                st.success(f"🏆 National Champion: {champ_text}")
            else:
                st.info("🏆 National Champion: not found")
        with c2:
            if not heisman_row.empty:
                st.success(f"🏅 Heisman: {heisman_row.iloc[0][meta['h_player']]} ({heisman_row.iloc[0][meta['h_school']]})")
            else:
                st.info("🏅 Heisman: not found")
        with c3:
            if not coty_row.empty:
                st.success(f"👔 COTY: {coty_row.iloc[0][meta['c_coach']]} ({coty_row.iloc[0][meta['c_school']]})")
            else:
                st.info("👔 COTY: not found")

        if not y_data.empty:
            user_games = y_data[
                (y_data['V_User_Final'].astype(str).str.upper() != 'CPU') &
                (y_data['H_User_Final'].astype(str).str.upper() != 'CPU') &
                (y_data['V_User_Final'] != y_data['H_User_Final'])
            ].copy()

            avg_m = round(y_data['Margin'].mean(), 1)

            if not user_games.empty:
                goty = user_games.loc[user_games['Margin'].idxmin()]

                if goty['V_Pts'] > goty['H_Pts']:
                    winner_user = goty['V_User_Final']
                    loser_user = goty['H_User_Final']
                    winner_team = goty['Visitor_Final']
                    loser_team = goty['Home_Final']
                else:
                    winner_user = goty['H_User_Final']
                    loser_user = goty['V_User_Final']
                    winner_team = goty['Home_Final']
                    loser_team = goty['Visitor_Final']

                roast_lines = [
                    f"{loser_user} snatched defeat from the jaws of competence.",
                    f"{loser_user} managed to turn a pressure moment into performance art.",
                    f"{loser_user} got all the way to the finish line and face-planted in front of the cameras."
                ]
                roast_line = roast_lines[int(goty['Margin']) % len(roast_lines)]

                st.info(
                    f"🏟️ Game of the Year: {goty['Visitor_Final']} at {goty['Home_Final']} | "
                    f"{winner_user} ({winner_team}) escaped by {int(goty['Margin'])}. "
                    f"{loser_user} ({loser_team}) was one stop away and still found a way to wear it. {roast_line}"
                )
            else:
                st.info("🏟️ Game of the Year: no user-vs-user games found for that season.")

            st.caption(f"Fun stat: {infer_best_fun_stat(y_data)}")
            st.write(
                f"**Narrative:** {sel_year} featured {len(user_games)} user battles. "
                f"The average margin across all logged games was {avg_m}, which points to "
                f"{'a season of wars' if avg_m <= 10 else 'a season with clear pecking-order moments'}."
            )

        st.dataframe(
            y_data[['Visitor_Final', 'V_User_Final', 'V_Pts', 'H_Pts', 'H_User_Final', 'Home_Final', 'Margin', 'Total Points']],
            hide_index=True,
            use_container_width=True
        )

    # --- TEAM ANALYSIS ---
    with tabs[3]:
        st.header("📊 Speed Analysis")
        target = st.selectbox("Select Team", model_2041['USER'].tolist(), key="team_analysis_user")
        row = model_2041[model_2041['USER'] == target].iloc[0]

        wins, losses, ppg, avg_margin = get_team_schedule_summary(scores, target)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Natty Odds", f"{row['Natty Odds']}%")
        m2.metric("CFP Odds", f"{row['CFP Odds']}%")
        m3.metric("Projected Wins", row['Projected Wins'])
        m4.metric("Power Index", row['Power Index'])

        st.markdown("---")

        c1, c2 = st.columns(2)
        with c1:
            st.subheader(f"{row['USER']} | {row['TEAM']}")
            st.write(f"**Program Stock:** {row['Program Stock']}")
            st.write(f"**Current User Record in scores file:** {wins}-{losses}")
            st.write(f"**Average Points Per Game:** {ppg}")
            st.write(f"**Average Margin:** {avg_margin}")
            st.write(f"**Recruit Score:** {row['Recruit Score']}")
            st.write(f"**Current CFP Ranking:** {int(row['Current CFP Ranking']) if pd.notna(row['Current CFP Ranking']) else 'Unranked'}")
            st.write(f"**QB OVR:** {int(row['QB OVR']) if pd.notna(row['QB OVR']) else 'N/A'}")
            st.write(f"**QB Tier:** {row['QB Tier']}")
            st.write(f"**Improvement from prior year:** {row['Improvement']} OVR")

        with c2:
            st.subheader("Star Skill Profile")
            st.write(f"**Star Skill Player:** {row['⭐ STAR SKILL GUY (Top OVR)']}")
            st.write(f"**Generational Speed?** {row['Star Skill Guy is Generational Speed?']}")
            st.write(
                "This profile blends pure roster power with game-breaking speed. "
                "If the star player is also a generational athlete, the offense can erase mistakes fast."
            )

        stat_table = pd.DataFrame([
            {'Metric': 'Overall', 'Value': row['OVERALL']},
            {'Metric': 'Offense', 'Value': row['OFFENSE']},
            {'Metric': 'Defense', 'Value': row['DEFENSE']},
            {'Metric': 'Off 90+ Speed Players', 'Value': row['Off Speed (90+ speed)']},
            {'Metric': 'Def 90+ Speed Players', 'Value': row['Def Speed (90+ speed)']},
            {'Metric': 'Total Team Speed', 'Value': row['Team Speed (90+ Speed Guys)']},
            {'Metric': 'Game Breakers', 'Value': row['Game Breakers (90+ Speed & 90+ Acceleration)']},
            {'Metric': 'Generational Talent Count', 'Value': row['Generational (96+ speed or 96+ Acceleration)']},
            {'Metric': 'Where is the Speed?', 'Value': row['Where is the Speed?']},
            {'Metric': 'Speedometer', 'Value': f"{row['Speedometer']} MPH"},
            {'Metric': 'Blue Chip Ratio', 'Value': f"{row['BCR_Val']}%"},
        ])

        st.subheader("Detailed Team Metrics")
        st.dataframe(stat_table, hide_index=True, use_container_width=True)

        detail_chart = pd.DataFrame({
            'Category': ['Overall', 'Offense', 'Defense', 'Off Speed', 'Def Speed', 'Game Breakers', 'Generational'],
            'Score': [
                row['OVERALL'],
                row['OFFENSE'],
                row['DEFENSE'],
                row['Off Speed (90+ speed)'],
                row['Def Speed (90+ speed)'],
                row['Game Breakers (90+ Speed & 90+ Acceleration)'],
                row['Generational (96+ speed or 96+ Acceleration)']
            ]
        })
        st.plotly_chart(px.bar(detail_chart, x='Category', y='Score', text='Score'), use_container_width=True)

    # --- TALENT PROFILE ---
    with tabs[2]:
        st.header("🔍 The 2041 Freak List")
        st.write("Detailed scouting of high-end athletic ceiling. TEAM SPEED is driven by total 90+ speed depth, but generational freaks act like multipliers that can launch a roster way up the board. On this dashboard, a TEAM SPEED score of 40 equals 65 MPH — anything above that is officially speeding.")

        talent_board = model_2041.copy()
        talent_board = talent_board.sort_values(
            ['Team Speed Score', 'Generational (96+ speed or 96+ Acceleration)', 'Team Speed (90+ Speed Guys)'],
            ascending=False
        ).reset_index(drop=True)
        talent_board['TEAM SPEED Rank'] = np.arange(1, len(talent_board) + 1)

        st.subheader("⚡ TEAM SPEED Rankings")
        st.dataframe(
            talent_board[[
                'TEAM SPEED Rank', 'USER', 'TEAM', 'Speedometer', 'Team Speed Score',
                'Where is the Speed?', 'Team Speed (90+ Speed Guys)', 'Game Breakers (90+ Speed & 90+ Acceleration)',
                'Generational (96+ speed or 96+ Acceleration)'
            ]],
            hide_index=True,
            use_container_width=True
        )

        for _, r in talent_board.iterrows():
            gens = int(r['Generational (96+ speed or 96+ Acceleration)'])
            team_speed = float(r.get('Team Speed Score', 0))
            tier = get_speed_tier(team_speed)
            gen_desc = get_pop_culture_speed_comp(gens)

            if gens == 0:
                bonus_desc = "No multiplier bonus here. This is a depth-and-discipline operation."
            elif gens == 1:
                bonus_desc = "One generational freak means the whole scouting report bends around a single superhero."
            else:
                bonus_desc = f"{gens} generational freaks means the speed depth gets turbocharged. This many cheat codes can vault a roster several spots higher than raw depth alone."

            with st.expander(f"#{int(r['TEAM SPEED Rank'])} {r['USER']} | {r['TEAM']} - {tier}"):
                st.write(gen_desc)
                st.write(bonus_desc)
                s1, s2, s3, s4 = st.columns(4)
                s1.metric("Speedometer", f"{float(r.get('Speedometer', r.get('Speed Limit MPH', 0)))} MPH")
                s2.metric("TEAM SPEED Score", f"{team_speed}")
                s3.metric("90+ Speed Players", int(r['Team Speed (90+ Speed Guys)']))
                s4.metric("Generational Freaks", gens)
                st.write(get_speeding_label(team_speed, gens))
                st.write(f"**Game breakers:** {int(r['Game Breakers (90+ Speed & 90+ Acceleration)'])}")
                st.write(f"**Offense 90+ speed:** {int(r['Off Speed (90+ speed)'])} | **Defense 90+ speed:** {int(r['Def Speed (90+ speed)'])}")
                st.write(f"**Where is the Speed?** {r['Where is the Speed?']}")
                st.write(f"**Blue Chip Ratio:** {int(r['BCR_Val'])}%")
                st.progress(min(1.0, team_speed / 100.0))

    # --- EXECUTIVE OUTLOOK ---
    with tabs[7]:
        st.header("🌐 2041 Executive Outlook")
        st.plotly_chart(
            px.scatter(
                model_2041,
                x="Off Speed (90+ speed)",
                y="Def Speed (90+ speed)",
                color="USER",
                color_discrete_map=user_color_map,
                size="OVERALL",
                text="TEAM",
                hover_data=["Natty Odds", "CFP Odds", "Collapse Risk", "Recruit Score"]
            ),
            use_container_width=True
        )

        st.plotly_chart(
            px.scatter(
                model_2041,
                x="BCR_Val",
                y="Power Index",
                color="Program Stock",
                size="Natty Odds",
                text="USER",
                hover_data=["TEAM", "Recruit Score", "CFP Odds"]
            ),
            use_container_width=True
        )

    # --- AI DYNASTY PREDICTOR ---
    with tabs[8]:
        st.header("🧠 AI Dynasty Predictor")
        st.write("Forward-looking program projections based on roster quality, speed, blue-chip composition, recruiting momentum, coaching pedigree, and dynasty stability. Natty Odds here mean odds to **win** the national title, not just make it.")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.subheader("🏆 Title Favorites")
            st.dataframe(
                model_2041[['USER', 'TEAM', 'Power Index', 'Projected Wins', 'CFP Odds', 'Natty Odds', 'Program Stock']]
                .sort_values("Natty Odds", ascending=False),
                hide_index=True,
                use_container_width=True
            )

        with c2:
            st.subheader("⚠️ Collapse Watch")
            st.dataframe(
                model_2041[['USER', 'TEAM', 'Collapse Risk', 'Projected Wins', 'Recruit Score', 'Program Stock']]
                .sort_values("Collapse Risk", ascending=False),
                hide_index=True,
                use_container_width=True
            )

        with c3:
            st.subheader("📈 Best Program Stock")
            st.dataframe(
                model_2041[['USER', 'TEAM', 'Power Index', 'Recruit Score', 'Career Win %', 'Program Stock']]
                .sort_values("Power Index", ascending=False),
                hide_index=True,
                use_container_width=True
            )

        st.markdown("---")

        st.subheader("Power Index Board")
        st.plotly_chart(
            px.bar(
                model_2041.sort_values("Power Index", ascending=False),
                x="USER",
                y="Power Index",
                color="Program Stock",
                hover_data=["TEAM", "Projected Wins", "CFP Odds", "Natty Odds", "Collapse Risk"]
            ),
            use_container_width=True
        )

        st.subheader("CFP Odds vs Collapse Risk")
        st.plotly_chart(
            px.scatter(
                model_2041,
                x="Collapse Risk",
                y="CFP Odds",
                size="Power Index",
                color="USER",
                color_discrete_map=user_color_map,
                text="TEAM",
                hover_data=["Projected Wins", "Natty Odds", "Recruit Score", "Career Win %", "Program Stock"]
            ),
            use_container_width=True
        )

        st.subheader("Full AI Projection Table")
        st.dataframe(
            model_2041[[
                "USER",
                "TEAM",
                "OVERALL",
                "OFFENSE",
                "DEFENSE",
                "Improvement",
                "BCR_Val",
                "Recruit Score",
                "Career Win %",
                "Current CFP Ranking",
                "QB OVR",
                "QB Tier",
                "Power Index",
                "Projected Wins",
                "CFP Odds",
                "Natty Odds",
                "Collapse Risk",
                "Program Stock"
            ]],
            hide_index=True,
            use_container_width=True
        )

        selected_user = st.selectbox("Select program for executive briefing", model_2041["USER"].tolist(), key="briefing_user")
        p_row = model_2041[model_2041["USER"] == selected_user].iloc[0]

        st.markdown("---")
        st.subheader(f"📋 Executive Briefing: {p_row['USER']} | {p_row['TEAM']}")

        b1, b2, b3, b4 = st.columns(4)
        b1.metric("Power Index", p_row["Power Index"])
        b2.metric("Projected Wins", p_row["Projected Wins"])
        b3.metric("CFP Odds", f"{int(p_row['CFP Odds'])}%")
        b4.metric("Natty Odds", f"{p_row['Natty Odds']}%")

        st.progress(min(1.0, float(p_row["CFP Odds"]) / 100))
        st.caption(f"Collapse Risk: {int(p_row['Collapse Risk'])}% | Program Stock: {p_row['Program Stock']}")

        if p_row["Natty Odds"] >= 24:
            st.success(f"{p_row['USER']} enters 2041 as a real title threat. The model loves the talent base, athletic ceiling, and overall program health.")
        elif p_row["Collapse Risk"] >= 50:
            st.warning(f"{p_row['USER']} has real volatility signals. There is enough downside here for a season to wobble fast.")
        else:
            st.info(f"{p_row['USER']} profiles as a postseason-capable program, but not as the clear favorite entering the year.")

    # --- RECRUITING MOMENTUM ---
    with tabs[9]:
        st.header("🏫 Recruiting Momentum")

        year_cols = [c for c in rec.columns if str(c).isdigit()]
        rec_view = rec.copy()

        recent_cols = [c for c in year_cols if int(c) <= 2041][-4:]
        rec_view['Recent Avg Rank'] = rec_view[recent_cols].applymap(clean_rank_value).mean(axis=1)
        rec_view['Momentum Score'] = (101 - rec_view['Recent Avg Rank']).fillna(0).round(1)

        user_momentum = rec_view.groupby('USER', as_index=False).agg({
            'Recent Avg Rank': 'min',
            'Momentum Score': 'max'
        }).sort_values('Momentum Score', ascending=False)

        st.dataframe(user_momentum, hide_index=True, use_container_width=True)

        st.plotly_chart(
            px.bar(
                user_momentum,
                x='USER',
                y='Momentum Score',
                color='USER',
                color_discrete_map=user_color_map,
                hover_data=['Recent Avg Rank']
            ),
            use_container_width=True
        )

        selected_recruit_user = st.selectbox("Select recruiter", sorted(rec['USER'].unique()), key="recruiting_user")
        recruit_rows = rec[rec['USER'] == selected_recruit_user].copy()
        st.dataframe(recruit_rows, hide_index=True, use_container_width=True)

    # --- UPSET TRACKER ---
    with tabs[10]:
        st.header("🚨 Upset Tracker")

        upset_df = scores.copy()
        rating_map = model_2041.set_index('TEAM')['OVERALL'].to_dict()
        upset_df['Visitor OVR Proxy'] = upset_df['Visitor_Final'].map(rating_map)
        upset_df['Home OVR Proxy'] = upset_df['Home_Final'].map(rating_map)

        upset_df['Expected Winner'] = np.where(
            upset_df['Home OVR Proxy'].fillna(-999) >= upset_df['Visitor OVR Proxy'].fillna(-999),
            upset_df['Home_Final'],
            upset_df['Visitor_Final']
        )
        upset_df['Actual Winner'] = upset_df['Winner_Team']
        upset_df['Underdog Delta'] = np.where(
            upset_df['Actual Winner'] == upset_df['Home_Final'],
            upset_df['Visitor OVR Proxy'].fillna(upset_df['Home OVR Proxy']) - upset_df['Home OVR Proxy'].fillna(upset_df['Visitor OVR Proxy']),
            upset_df['Home OVR Proxy'].fillna(upset_df['Visitor OVR Proxy']) - upset_df['Visitor OVR Proxy'].fillna(upset_df['Home OVR Proxy'])
        )

        upset_df = upset_df[upset_df['Actual Winner'] != upset_df['Expected Winner']].copy()
        upset_df['Upset Score'] = (upset_df['Underdog Delta'].abs().fillna(0) + upset_df['Margin']).round(1)
        upset_df = upset_df.sort_values('Upset Score', ascending=False)

        if upset_df.empty:
            st.info("No upsets were detected with the current proxy model.")
        else:
            st.dataframe(
                upset_df[['YEAR', 'Visitor_Final', 'V_Pts', 'H_Pts', 'Home_Final', 'Actual Winner', 'Expected Winner', 'Upset Score']],
                hide_index=True,
                use_container_width=True
            )

            st.plotly_chart(
                px.bar(
                    upset_df.head(15),
                    x='Actual Winner',
                    y='Upset Score',
                    color='YEAR',
                    hover_data=['Visitor_Final', 'Home_Final', 'Expected Winner']
                ),
                use_container_width=True
            )

    # --- GOAT RANKINGS ---
    with tabs[11]:
        st.header("🐐 Dynasty GOAT Rankings")
        goat = stats.copy().sort_values("GOAT Score", ascending=False).reset_index(drop=True)

        st.dataframe(
            goat[['User', 'GOAT Score', 'Career Record', 'Career Win %', 'Natties', 'Natty Apps', 'CFP Wins', 'Conf Titles', '1st Rounders', 'Drafted']],
            hide_index=True,
            use_container_width=True
        )

        st.plotly_chart(
            px.bar(
                goat,
                x="User",
                y="GOAT Score",
                color="User",
                hover_data=['Natties', 'Natty Apps', 'CFP Wins', 'Conf Titles', '1st Rounders', 'Drafted']
            ),
            use_container_width=True
        )

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
