# island_gameday.py -- ISPN College Football Gameday (v2)
# Streamlined 6-tab dynasty companion app
# Tabs: Dynasty News | Rankings & Metrics | Roster Attrition | Season Recap | User Legacies | Roster Matchup

import streamlit as st

_GLOBAL_WEEK_RANK_LOOKUP={}

def _safe_int(v,default=0):
    """Convert to int safely handling NaN and non-numeric values."""
    try:
        r=pd.to_numeric(v,errors='coerce')
        return default if (r is None or (isinstance(r,float) and r!=r)) else int(r)
    except: return default

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os, io, re, html, time, base64, hashlib, math, random, textwrap
from pathlib import Path

# ── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ISPN College Football Gameday",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── DYNASTY STATE ─────────────────────────────────────────────────────────────
def load_dynasty_state(path='dynasty_state.csv'):
    defaults = {'CurrentWeek': 16, 'CurrentYear': 2042, 'IsBowlWeek': False, 'BowlRound': 1}
    try:
        state_df = pd.read_csv(path)
        if state_df.empty: return defaults
        row = state_df.iloc[0].to_dict()
        def _int(v, fb): 
            try: return int(float(v)) if pd.notna(v) else fb
            except: return fb
        def _bool(v, fb):
            if pd.isna(v): return fb
            s = str(v).strip().lower()
            return True if s in ('1','true','yes','y','on') else (False if s in ('0','false','no','n','off') else fb)
        return {
            'CurrentWeek': _int(row.get('CurrentWeek', defaults['CurrentWeek']), defaults['CurrentWeek']),
            'CurrentYear': _int(row.get('CurrentYear', defaults['CurrentYear']), defaults['CurrentYear']),
            'IsBowlWeek':  _bool(row.get('IsBowlWeek', defaults['IsBowlWeek']), defaults['IsBowlWeek']),
            'BowlRound':   _int(row.get('BowlRound', defaults['BowlRound']), defaults['BowlRound']),
        }
    except: return defaults

_DYNASTY_STATE      = load_dynasty_state()
CURRENT_WEEK_NUMBER = _DYNASTY_STATE['CurrentWeek']
CURRENT_YEAR        = _DYNASTY_STATE['CurrentYear']
IS_BOWL_WEEK        = _DYNASTY_STATE['IsBowlWeek']
BOWL_ROUND          = _DYNASTY_STATE['BowlRound']
IS_OFFSEASON        = CURRENT_WEEK_NUMBER >= 25

# ── LEAGUE CONSTANTS ─────────────────────────────────────────────────────────
USER_TEAMS = {
    'Mike':  'San Jose State',
    'Devin': 'Bowling Green',
    'Josh':  'USF',
    'Noah':  'Texas Tech',
    'Doug':  'Florida',
    'Nick':  'Florida State',
}
EXPANSION_TEAMS = ['Death Valley','Hammond','Rapid City','Alabaster','Gate City','Panama City']
ALL_USER_TEAMS  = set(USER_TEAMS.values())

_ABBREV = {
    "San Jose State":"SJSU","Bowling Green":"BGSU","USF":"USF","Texas Tech":"TTU",
    "Florida":"UF","Florida State":"FSU","Alabama":"BAMA","Ohio State":"OSU",
    "Georgia":"UGA","Michigan":"MICH","Penn State":"PSU","Notre Dame":"ND",
    "USC":"USC","Oklahoma":"OU","Texas":"TEX","LSU":"LSU","Auburn":"AUB",
    "Tennessee":"TENN","Oregon":"ORE","Washington":"UW","Wisconsin":"WIS",
    "Iowa":"IOWA","Nebraska":"NEB","Missouri":"MIZZ","Kansas State":"KSU",
    "Iowa State":"ISU","TCU":"TCU","Oklahoma State":"OKST","West Virginia":"WVU",
    "BYU":"BYU","South Carolina":"SCAR","Kentucky":"UK","Ole Miss":"MISS",
    "Mississippi State":"MSST","Miami":"UM","Virginia Tech":"VT",
    "North Carolina":"UNC","NC State":"NCST","Clemson":"CLEM",
    "Georgia Tech":"GT","Stanford":"STAN","UCLA":"UCLA","Utah":"UTAH",
    "Arizona State":"ASU","Arizona":"ARIZ","San Diego State":"SDSU",
    "Boise State":"BSU","Colorado":"COLO","Colorado State":"CSU",
    "Minnesota":"MINN","Arkansas":"ARK","Duke":"DUKE","SMU":"SMU",
    "Rutgers":"RU","Purdue":"PUR","Syracuse":"CUSE","UCF":"UCF",
    "Cincinnati":"CIN","Memphis":"MEM","Tulane":"TUL","Houston":"HOU",
    "Air Force":"AF","Wyoming":"WYO","Hawaii":"HAW","Vanderbilt":"VANDY",
    "Louisville":"LOU","Virginia":"UVA","Maryland":"UMD","Indiana":"IND",
    "Michigan State":"MSU","Kansas":"KU","Texas A&M":"TAMU",
    "Death Valley":"DV","Hammond":"HAM","Rapid City":"RC",
    "Alabaster":"ALA","Gate City":"GC","Panama City":"PC",
}
def _abbrev(t):
    t = str(t).strip()
    if t in _ABBREV: return _ABBREV[t]
    w = t.split()
    return "".join(x[0] for x in w if x)[:5].upper() if len(w)>1 else t[:5].upper()

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow+Condensed:ital,wght@0,400;0,600;0,700;1,600&family=Barlow:wght@400;500;600;700&display=swap');
html,body,[class*="css"],.stApp{font-family:'Barlow',sans-serif!important;}
h1,h2,h3,[data-testid="stHeading"],.stMarkdown h1,.stMarkdown h2,.stMarkdown h3{
    font-family:'Barlow Condensed',sans-serif!important;font-weight:900!important;
    letter-spacing:.01em;text-transform:uppercase;color:#f8fafc!important;line-height:1.05!important;}
h1{font-size:2.4rem!important;}h2{font-size:1.8rem!important;}h3{font-size:1.35rem!important;}
h4,h5,h6{font-family:'Barlow Condensed',sans-serif!important;font-weight:700!important;
    letter-spacing:.04em;text-transform:uppercase;}
.stMarkdown h2::before{content:'';display:block;height:2px;width:32px;
    background:#ef4444;margin-bottom:6px;border-radius:2px;}
button[data-testid="stBaseButton-tertiary"],div[data-testid="stTabList"] button{
    font-family:'Barlow Condensed',sans-serif!important;font-weight:600!important;letter-spacing:.04em;}
[data-testid="stMetricValue"]{font-family:'Bebas Neue',sans-serif!important;
    font-size:2rem!important;letter-spacing:.03em;}
.stDeployButton{display:none;}[data-testid="stDecoration"]{display:none;}
#MainMenu{visibility:hidden;}footer{visibility:hidden;}header{background:transparent;}
.main .block-container{max-width:1200px;padding-top:0rem;padding-right:1rem;
    padding-left:1rem;padding-bottom:2rem;}
h1,h2,h3{text-align:center!important;width:100%;margin-top:0rem!important;}
.stCaption{text-align:center!important;display:block;width:100%;}
div[data-testid="stTabList"]{display:flex;overflow-x:auto;white-space:nowrap;
    scrollbar-width:none;-ms-overflow-style:none;gap:8px;padding-bottom:5px;}
div[data-testid="stTabList"]::-webkit-scrollbar{display:none;}
button[data-testid="stBaseButton-tertiary"]{flex:0 0 auto;padding:10px 15px;}
@media(max-width:768px){
    .main .block-container{padding-right:.5rem;padding-left:.5rem;}
    h1{font-size:1.8rem!important;}h2{font-size:1.5rem!important;}}
.isp-table-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch;
    border:1px solid #334155;border-radius:14px;background:#0f172a;max-width:100%;}
.isp-table{width:100%;min-width:480px;border-collapse:collapse;font-size:13px;}
.isp-power-table-wrap{overflow-x:auto;border:1px solid #1e293b;border-radius:8px;}
.isp-power-table{width:100%;border-collapse:collapse;background:#06090f;}
@media(max-width:768px){
    .isp-power-table th{padding:4px 4px!important;font-size:.50rem!important;}
    .isp-power-table td{padding:4px 4px!important;}
    .isp-power-table .isp-power-rank{width:18px!important;font-size:.55rem!important;}
    .isp-power-table .isp-power-team{font-size:.68rem!important;}
    .isp-power-table .isp-power-logo{width:16px!important;height:16px!important;}
    .isp-power-table .isp-power-fpi{font-size:.78rem!important;}
    .isp-power-table .isp-power-chaos{font-size:.72rem!important;}}
</style>
""", unsafe_allow_html=True)

# ── TEAM VISUALS ──────────────────────────────────────────────────────────────
def load_team_visuals(csv_path="team_visuals.csv"):
    try:
        _tv = pd.read_csv(csv_path)
        if _tv.empty or 'Team' not in _tv.columns: return {}
        visuals = {}
        for _, _r in _tv.iterrows():
            _team = str(_r.get('Team','')).strip()
            if not _team: continue
            visuals[_team] = {
                'slug': str(_r.get('Slug','')).strip(),
                'primary': str(_r.get('Primary','')).strip() or '#38bdf8',
                'secondary': str(_r.get('Secondary','')).strip() or '#94a3b8',
            }
        return visuals
    except: return {}

TEAM_VISUALS = load_team_visuals()

TEAM_ALIASES = {
    "Florida":["florida","florida gators"],
    "Florida State":["florida state","florida state seminoles","fsu"],
    "Texas Tech":["texas tech","texas tech red raiders"],
    "USF":["usf","south florida","south florida bulls"],
    "South Florida":["usf","south florida","south florida bulls"],
    "San Jose State":["san jose state","san jose state spartans","sjsu"],
    "Bowling Green":["bowling green","bowling green falcons"],
    "Rapid City":["rapid city"],"Panama City":["panama city"],
    "Hammond":["hammond"],"Alabaster":["alabaster"],
    "Death Valley":["death valley"],"Gate City":["gate city"],
}

def normalize_key(s):
    return re.sub(r'[^a-z0-9]','',str(s).strip().lower())

def get_team_slug(team):
    team=str(team).strip()
    if not team or team.lower()=='nan': return ""
    slug=TEAM_VISUALS.get(team,{}).get("slug")
    if not slug:
        slug=team.lower().replace("&","and").replace(".","").replace("'","").replace(" ","-")
    return slug

def get_team_aliases(team):
    team=str(team).strip()
    aliases=TEAM_ALIASES.get(team,[team])
    slug=get_team_slug(team)
    if slug:
        aliases.append(slug.replace("-"," "))
        aliases.append(slug)
    aliases.append(team)
    seen=set(); out=[]
    for a in aliases:
        n=normalize_key(a)
        if n and n not in seen:
            out.append(a); seen.add(n)
    return out

def clean_team_name_for_lookup(team):
    team=str(team).strip()
    if not team or team.lower()=="nan": return ""
    team=re.sub(r'^\#?\d+\s+','',team).strip()
    team=re.sub(r'\*+$','',team).strip()
    return team

def _build_logo_index(search_dir="."):
    candidate_dirs=[Path('logos'),Path('/mnt/data/logos'),
        Path('/mount/src/cfb_dynasty_app/logos'),Path('/mount/src/cfb_dynasty_app')]
    found={}
    for d in candidate_dirs:
        if d.exists():
            for fp in d.rglob('*'):
                if fp.is_file() and fp.suffix.lower() in {'.png','.jpg','.jpeg','.webp'}:
                    for k in {normalize_key(fp.stem), normalize_key(fp.name)}:
                        if k and k not in found: found[k]=fp
    return found

LOGO_FILE_INDEX=_build_logo_index()

def get_local_logo_path(team):
    aliases=get_team_aliases(clean_team_name_for_lookup(team))
    for key in [normalize_key(a) for a in aliases]:
        if key in LOGO_FILE_INDEX: return str(LOGO_FILE_INDEX[key])
    return ""

def get_logo_source(team):
    local=get_local_logo_path(team)
    return local if local else ""

def image_file_to_data_uri(path_str):
    try:
        if path_str and os.path.exists(path_str):
            ext=Path(path_str).suffix.lower().replace('.','') or 'png'
            with open(path_str,'rb') as f:
                encoded=base64.b64encode(f.read()).decode('ascii')
            return f"data:image/{ext};base64,{encoded}"
    except: pass
    return ""

def get_school_logo_src(team_name):
    try:
        path=get_logo_source(team_name)
        if path: return image_file_to_data_uri(path)
    except: pass
    return ""

def get_header_logo(team_name):
    try:
        path=get_logo_source(team_name)
        uri=image_file_to_data_uri(path)
        if uri: return uri
        slug=TEAM_VISUALS.get(team_name,{}).get('slug',normalize_key(team_name))
        return f"https://raw.githubusercontent.com/j99p/ispn_2041/main/logos/{slug}.png"
    except:
        return "https://raw.githubusercontent.com/j99p/ispn_2041/main/logos/ncaa.png"

def get_team_primary_color(team):
    team=clean_team_name_for_lookup(team)
    if team in TEAM_VISUALS: return TEAM_VISUALS[team].get("primary","#1f77b4")
    nteam=normalize_key(team)
    for name,meta in TEAM_VISUALS.items():
        if normalize_key(name)==nteam: return meta.get("primary","#1f77b4")
    for name,meta in TEAM_VISUALS.items():
        for alias in [name]+TEAM_ALIASES.get(name,[]):
            if normalize_key(alias)==nteam: return meta.get("primary","#1f77b4")
    return "#1f77b4"

def get_team_secondary_color(team):
    team=clean_team_name_for_lookup(team)
    if team in TEAM_VISUALS: return TEAM_VISUALS[team].get("secondary","#ffffff")
    nteam=normalize_key(team)
    for name,meta in TEAM_VISUALS.items():
        if normalize_key(name)==nteam: return meta.get("secondary","#ffffff")
    return "#ffffff"

def hex_to_rgba(hex_color,alpha=0.25):
    try:
        h=str(hex_color).strip().lstrip("#")
        if len(h)==3: h=h[0]*2+h[1]*2+h[2]*2
        if len(h)!=6: return f"rgba(100,100,100,{alpha})"
        r,g,b=int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
        return f"rgba({r},{g},{b},{alpha})"
    except: return f"rgba(100,100,100,{alpha})"

def safe_num(value, default=0):
    try:
        if pd.isna(value): return default
        return float(value)
    except: return default

def safe_title_series(series):
    try: return series.astype(str).str.strip().str.title()
    except: return series

def smart_col(df, target_names):
    for t in target_names:
        if t in df.columns: return t
    for t in target_names:
        for c in df.columns:
            if c.lower().replace(' ','_')==t.lower().replace(' ','_'): return c
    return target_names[0] if target_names else ''

def ensure_columns(df, defaults):
    for col, val in defaults.items():
        if col not in df.columns: df[col]=val
    return df

def is_user_team(team_name):
    return str(team_name).strip() in ALL_USER_TEAMS

def is_senior_label(year_val):
    s=str(year_val).strip().upper()
    return 'SR' in s or 'GR' in s or 'GRAD' in s

def format_pct(val, digits=1):
    try: return f"{float(val)*100:.{digits}f}%" if float(val)<=1 else f"{float(val):.{digits}f}%"
    except: return "--"

# ── DATA LOADERS ──────────────────────────────────────────────────────────────
def load_scores_master(year=None, multi_year=False, **kwargs):
    import glob as _glob
    def _clean(df):
        for _col in ('Visitor','Home','VISITOR','HOME'):
            if _col in df.columns:
                df[_col]=df[_col].astype(str).apply(lambda t: re.sub(r'^\d+\s+','',t.strip()))
        return df
    def _read(path,**kw):
        try: return _clean(pd.read_csv(path,**kw))
        except: return pd.DataFrame()
    if multi_year:
        parts=[]
        if os.path.exists('CPUscores_MASTER.csv'): parts.append(_read('CPUscores_MASTER.csv',**kwargs))
        for yf in sorted(_glob.glob('CPUscores_MASTER_*.csv')): parts.append(_read(yf,**kwargs))
        for yf in sorted(_glob.glob('schedule_*.csv')): parts.append(_read(yf,**kwargs))
        if not parts: return pd.DataFrame()
        combined=pd.concat(parts,ignore_index=True)
        for c in ['YEAR','Week']:
            if c in combined.columns:
                combined[c]=pd.to_numeric(combined[c],errors='coerce')
        dk=[c for c in ['YEAR','Week','Visitor','Home'] if c in combined.columns]
        if dk: combined=combined.drop_duplicates(subset=dk,keep='last')
        return combined
    target_year=int(year) if year else CURRENT_YEAR
    schedule_file=f'schedule_{target_year}.csv'
    if os.path.exists(schedule_file): return _read(schedule_file,**kwargs)
    year_master=f'CPUscores_MASTER_{target_year}.csv'
    if os.path.exists(year_master): return _read(year_master,**kwargs)
    if os.path.exists('CPUscores_MASTER.csv'):
        df=_read('CPUscores_MASTER.csv',**kwargs)
        if not df.empty and 'YEAR' in df.columns:
            df['YEAR']=pd.to_numeric(df['YEAR'],errors='coerce')
            return df[df['YEAR'].fillna(-1).astype(int)==target_year]
        return df
    return pd.DataFrame()

def normalize_game_summaries(df):
    if df is None or df.empty: return df
    rename_map={
        'VISITOR':'Visitor','HOME':'Home',
        'VIS_FINAL':'VisitorScore','HOME_FINAL':'HomeScore',
        'VIS_Q1':'Q1_Visitor','VIS_Q2':'Q2_Visitor','VIS_Q3':'Q3_Visitor','VIS_Q4':'Q4_Visitor','VIS_OT':'Visitor_OT',
        'HOME_Q1':'Q1_Home','HOME_Q2':'Q2_Home','HOME_Q3':'Q3_Home','HOME_Q4':'Q4_Home','HOME_OT':'Home_OT',
        'VIS_PASS_YDS':'PassYds_Visitor','HOME_PASS_YDS':'PassYds_Home',
        'VIS_RUSH_YDS':'RushYds_Visitor','HOME_RUSH_YDS':'RushYds_Home',
        'VIS_TURNOVERS':'Turnovers_Visitor','HOME_TURNOVERS':'Turnovers_Home',
        'VIS_USER':'Vis_User','HOME_USER':'Home_User',
        'VIS_RANK':'Visitor Rank','HOME_RANK':'Home Rank',
        'VIS_TOTAL_YDS':'TotalYds_Visitor','HOME_TOTAL_YDS':'TotalYds_Home',
        'VIS_3RD_CONV':'ThirdConv_Visitor','VIS_3RD_ATT':'ThirdAtt_Visitor',
        'HOME_3RD_CONV':'ThirdConv_Home','HOME_3RD_ATT':'ThirdAtt_Home',
        'VIS_RZ_TD':'RZ_TD_Visitor','VIS_RZ_FG':'RZ_FG_Visitor','VIS_RZ_PCT':'RZ_Pct_Visitor',
        'HOME_RZ_TD':'RZ_TD_Home','HOME_RZ_FG':'RZ_FG_Home','HOME_RZ_PCT':'RZ_Pct_Home',
        'VIS_TOP':'TOP_Visitor','HOME_TOP':'TOP_Home',
        'VIS_FIRST_DOWNS':'FD_Visitor','HOME_FIRST_DOWNS':'FD_Home',
    }
    actual={k:v for k,v in rename_map.items() if k in df.columns and v not in df.columns}
    if actual: df=df.rename(columns=actual)
    return df

def load_game_summaries(year=None):
    target_year=int(year) if year else CURRENT_YEAR
    try:
        df=pd.read_csv('game_summaries.csv')
        df.columns=[str(c).strip() for c in df.columns]
        df=normalize_game_summaries(df)
        for c in ('YEAR','WEEK'):
            if c in df.columns:
                df[c]=pd.to_numeric(df[c],errors='coerce')
        df=df[df['YEAR'].fillna(-1).astype(int)==target_year].copy()
        return df
    except: return pd.DataFrame()

def parse_top_minutes(val):
    if pd.isna(val): return 0.0
    text=str(val).strip()
    if not text: return 0.0
    parts=text.split(':')
    try:
        if len(parts)>=2:
            return int(parts[0])+int(parts[1])/60.0
        return float(text)
    except: return 0.0

def compute_game_control_score(row, user_is_home):
    """Compute 0-100 game control score for a single game from game_summaries row."""
    import math
    def _n(v): 
        try: return float(v) if pd.notna(v) else 0.0
        except: return 0.0
    def tanh_c(x, scale): return math.tanh(x/scale) if scale else 0.0

    if user_is_home:
        us_score   = _n(row.get('HomeScore',0))
        opp_score  = _n(row.get('VisitorScore',0))
        us_yds     = _n(row.get('TotalYds_Home', row.get('HOME_TOTAL_YDS',0)))
        opp_yds    = _n(row.get('TotalYds_Visitor', row.get('VIS_TOTAL_YDS',0)))
        us_to      = _n(row.get('Turnovers_Home',0))
        opp_to     = _n(row.get('Turnovers_Visitor',0))
        us_3c      = _n(row.get('ThirdConv_Home',0)); us_3a=_n(row.get('ThirdAtt_Home',1))
        opp_3c     = _n(row.get('ThirdConv_Visitor',0)); opp_3a=_n(row.get('ThirdAtt_Visitor',1))
        us_rz_pct  = _n(row.get('RZ_Pct_Home',0)); opp_rz_pct=_n(row.get('RZ_Pct_Visitor',0))
        us_top_raw = row.get('TOP_Home','0:00'); opp_top_raw=row.get('TOP_Visitor','0:00')
        us_fd      = _n(row.get('FD_Home',0)); opp_fd=_n(row.get('FD_Visitor',0))
    else:
        us_score   = _n(row.get('VisitorScore',0))
        opp_score  = _n(row.get('HomeScore',0))
        us_yds     = _n(row.get('TotalYds_Visitor', row.get('VIS_TOTAL_YDS',0)))
        opp_yds    = _n(row.get('TotalYds_Home', row.get('HOME_TOTAL_YDS',0)))
        us_to      = _n(row.get('Turnovers_Visitor',0))
        opp_to     = _n(row.get('Turnovers_Home',0))
        us_3c      = _n(row.get('ThirdConv_Visitor',0)); us_3a=_n(row.get('ThirdAtt_Visitor',1))
        opp_3c     = _n(row.get('ThirdConv_Home',0)); opp_3a=_n(row.get('ThirdAtt_Home',1))
        us_rz_pct  = _n(row.get('RZ_Pct_Visitor',0)); opp_rz_pct=_n(row.get('RZ_Pct_Home',0))
        us_top_raw = row.get('TOP_Visitor','0:00'); opp_top_raw=row.get('TOP_Home','0:00')
        us_fd      = _n(row.get('FD_Visitor',0)); opp_fd=_n(row.get('FD_Home',0))

    us_top=parse_top_minutes(us_top_raw); opp_top=parse_top_minutes(opp_top_raw)
    us_3pct=(us_3c/max(us_3a,1)); opp_3pct=(opp_3c/max(opp_3a,1))
    # normalize rz_pct: if stored as >1 (raw count style), skip
    if us_rz_pct>1: us_rz_pct=us_rz_pct/100.0
    if opp_rz_pct>1: opp_rz_pct=opp_rz_pct/100.0

    components={
        'score_margin':     (us_score-opp_score, 28.0, 14.0),
        'yards_gap':        (us_yds-opp_yds, 200.0, 10.0),
        'to_margin':        (opp_to-us_to, 3.0, 8.0),
        'first_downs':      (us_fd-opp_fd, 10.0, 5.0),
        'third_down':       (us_3pct-opp_3pct, 0.35, 4.5),
        'red_zone':         (us_rz_pct-opp_rz_pct, 0.40, 3.5),
        'time_of_poss':     (us_top-opp_top, 12.0, 2.5),
    }
    raw=sum(tanh_c(val,scale)*weight for val,scale,weight in components.values())
    total_weight=sum(w for _,_,w in components.values())
    normalized=raw/total_weight  # -1 to +1
    score=round(50+normalized*50,1)
    return max(0.0, min(100.0, score))

def build_ratings_from_sources(year):
    """Build team ratings DataFrame from year-stamped CSVs. Replaces the old locked function."""
    _tr_file  = f'team_ratings_{year}.csv'
    _ros_file = f'cfb_136_top30_rosters_{year}.csv'
    _bcr_file = f'bluechip_ratio_{year}.csv'
    _tc_file  = 'team_conferences.csv'
    _tr_prev  = f'team_ratings_{year-1}.csv'
    if not os.path.exists(_tr_file): return pd.DataFrame()
    try:
        _tr=pd.read_csv(_tr_file)
        if _tr.empty: return pd.DataFrame()
    except: return pd.DataFrame()
    _tr['TEAM']=_tr['TEAM'].astype(str).str.strip()
    _tr['YEAR']=int(year)
    _tr['OVERALL']=pd.to_numeric(_tr.get('OVR',_tr.get('OVERALL',82)),errors='coerce').fillna(82).astype(int)
    _tr['OFFENSE']=pd.to_numeric(_tr.get('OFF',_tr.get('OFFENSE',82)),errors='coerce').fillna(82).astype(int)
    _tr['DEFENSE']=pd.to_numeric(_tr.get('DEF',_tr.get('DEFENSE',82)),errors='coerce').fillna(82).astype(int)
    _tr['USER']=''; _tr['CONFERENCE']=''
    if os.path.exists(_tc_file):
        try:
            _tc=pd.read_csv(_tc_file); _tc['TEAM']=_tc['TEAM'].astype(str).str.strip()
            if 'CONFERENCE' in _tc.columns:
                _tr['CONFERENCE']=_tr['TEAM'].map(dict(zip(_tc['TEAM'],_tc['CONFERENCE'].fillna(''))))
            if 'USER' in _tc.columns:
                _tr['USER']=_tr['TEAM'].map(lambda t: str(dict(zip(_tc['TEAM'],_tc['USER'].fillna(''))).get(t,'')).strip())
        except: pass
    _tr['BCR_Val']=0.0
    if os.path.exists(_bcr_file):
        try:
            _bcr=pd.read_csv(_bcr_file); _bcr['TEAM']=_bcr['TEAM'].astype(str).str.strip()
            _bcr_col=next((c for c in _bcr.columns if any(x in c.upper() for x in ('BCR','BLUE','RATIO','CHIP','PERCENT'))),None)
            if _bcr_col:
                _bcr['_v']=pd.to_numeric(_bcr[_bcr_col].astype(str).str.replace('%','',regex=False),errors='coerce').fillna(0)
                _bcr_map=dict(zip(_bcr['TEAM'],_bcr['_v']))
                _tr['BCR_Val']=_tr['TEAM'].map(lambda t: _bcr_map.get(t,0.0))
        except: pass
    _speed_defaults={'Team Speed (90+ Speed Guys)':0,'Quad 90 (90+ SPD, ACC, AGI & COD)':0,
        'Generational (96+ speed or 96+ Acceleration)':0,'Off Speed (90+ speed)':0,
        'Def Speed (90+ speed)':0,'Monsters':0,'Quick Hogs':0,'QB OVR':80}
    for sc,sd in _speed_defaults.items(): _tr[sc]=sd
    if os.path.exists(_ros_file):
        try:
            _ros=pd.read_csv(_ros_file)
            _ros['TEAM']=_ros['TEAM'].astype(str).str.strip()
            for _c in ('SPD','ACC','AGI','COD','OVR','STR'):
                if _c in _ros.columns: _ros[_c]=pd.to_numeric(_ros[_c],errors='coerce').fillna(0)
            _ros['POS_U']=_ros['POS'].astype(str).str.upper().str.strip()
            _off_pos={'QB','HB','WR','TE','LT','LG','C','RG','RT'}
            _def_pos={'CB','FS','SS','MLB','OLB','DE','DT','LEDG','REDG','SAM','MIKE','WILL','ILB','LB'}
            _front7={'DE','DT','LEDG','REDG','SAM','MIKE','WILL','MLB','ILB','OLB','LB'}
            _ol_pos={'LT','LG','C','RG','RT'}
            for team,grp in _ros.groupby('TEAM'):
                sc={'Team Speed (90+ Speed Guys)':int((grp['SPD']>=90).sum()),
                    'Quad 90 (90+ SPD, ACC, AGI & COD)':int(((grp['SPD']>=90)&(grp['ACC']>=90)&(grp['AGI']>=90)&(grp['COD']>=90)).sum()),
                    'Generational (96+ speed or 96+ Acceleration)':int(((grp['SPD']>=96)|(grp['ACC']>=96)).sum()),
                    'Off Speed (90+ speed)':int(((grp['SPD']>=90)&(grp['POS_U'].isin(_off_pos))).sum()),
                    'Def Speed (90+ speed)':int(((grp['SPD']>=90)&(grp['POS_U'].isin(_def_pos))).sum()),
                    'Monsters':int((grp['POS_U'].isin(_front7)&(((grp['ACC']>=90)&(grp['SPD']>=84))|((grp['SPD']>=90)&(grp['ACC']>=84)))).sum()),
                    'Quick Hogs':int((grp['POS_U'].isin(_ol_pos)&(grp['AGI']>=85)&(grp['STR']>=90)).sum())}
                _qbs=grp[grp['POS_U']=='QB']
                _qb_ovr=int(_qbs['OVR'].max()) if not _qbs.empty else 80
                mask=_tr['TEAM']==team
                for col,val in sc.items(): _tr.loc[mask,col]=val
                _tr.loc[mask,'QB OVR']=_qb_ovr
        except: pass
    _tr['Improvement']=0
    if os.path.exists(_tr_prev):
        try:
            _prev=pd.read_csv(_tr_prev); _prev['TEAM']=_prev['TEAM'].astype(str).str.strip()
            _prev['OVERALL']=pd.to_numeric(_prev.get('OVR',_prev.get('OVERALL',82)),errors='coerce').fillna(82)
            _prev_map=dict(zip(_prev['TEAM'],_prev['OVERALL']))
            _tr['Improvement']=_tr.apply(lambda row: int(row['OVERALL']-_prev_map.get(row['TEAM'],row['OVERALL'])),axis=1)
        except: pass
    return _tr

def compute_power_ratings(scores_df, year=None, week_cap=None, iterations=50):
    """
    Iterative Colley-matrix-inspired power ratings (FPI).

    FPI for team i = avg(margin_of_victory_adjusted) vs opponent FPI.
    Iterates until stable. Returns dict: {team: fpi_score}

    MOV is capped at 28 to prevent blowouts dominating.
    Home-field adjustment: -3 from home team's margin.
    """
    df = scores_df.copy()
    if year:
        df = df[df['YEAR'].fillna(-1).astype(int) == int(year)]
    if week_cap:
        df = df[df['Week'].fillna(0).astype(int) <= int(week_cap)]
    df = df[df['Status'].astype(str).str.upper() == 'FINAL'].copy()
    df['Vis Score']  = pd.to_numeric(df['Vis Score'],  errors='coerce')
    df['Home Score'] = pd.to_numeric(df['Home Score'], errors='coerce')
    df = df.dropna(subset=['Vis Score', 'Home Score'])
    if df.empty:
        return {}

    all_teams = set(df['Visitor'].dropna().astype(str).str.strip().tolist() +
                    df['Home'].dropna().astype(str).str.strip().tolist())

    # Strip watcher misread artifacts like "2 Panama City" → "Panama City"
    # GPT sometimes prepends a row number to the team name
    import re as _re
    def _clean_team(t):
        return _re.sub(r'^\d+\s+', '', str(t).strip())
    df['Visitor'] = df['Visitor'].astype(str).apply(_clean_team)
    df['Home']    = df['Home'].astype(str).apply(_clean_team)
    all_teams = set(df['Visitor'].tolist() + df['Home'].tolist())
    fpi = {t: 0.0 for t in all_teams}

    for _ in range(iterations):
        new_fpi = {}
        for team in all_teams:
            t_games = df[(df['Visitor'].astype(str).str.strip() == team) |
                         (df['Home'].astype(str).str.strip() == team)]
            if t_games.empty:
                new_fpi[team] = 0.0
                continue
            values = []
            for _, g in t_games.iterrows():
                vis = str(g['Visitor']).strip()
                vs  = float(g['Vis Score'])
                hs  = float(g['Home Score'])
                is_home = vis != team
                # Raw MOV from team's perspective, home adjustment
                raw_mov = (hs - vs) if is_home else (vs - hs)
                ha_adj  = 3.0 if is_home else -3.0  # home field ~3 pts
                adj_mov = raw_mov - ha_adj
                adj_mov = max(-28, min(28, adj_mov))  # cap at 28
                opp = str(g['Home']).strip() if vis == team else vis
                opp_fpi = fpi.get(opp, 0.0)
                # FPI component: adjusted MOV + opponent quality adjustment
                values.append(adj_mov + opp_fpi * 0.5)
            new_fpi[team] = round(sum(values) / len(values), 3) if values else 0.0
        # Normalize to mean=0
        vals = list(new_fpi.values())
        mean = sum(vals) / len(vals) if vals else 0
        new_fpi = {t: round(v - mean, 3) for t, v in new_fpi.items()}
        if all(abs(new_fpi.get(t, 0) - fpi.get(t, 0)) < 0.001 for t in all_teams):
            break
        fpi = new_fpi

    return fpi


def compute_sos(scores_df, team, year=None, week_cap=None, fpi_ratings=None):
    """
    Strength of Schedule: average FPI of all opponents faced.
    If fpi_ratings not provided, uses opponent win percentage instead.
    Returns (sos_score, opponents_list)
    """
    df = scores_df.copy()
    if year:
        df = df[df['YEAR'].fillna(-1).astype(int) == int(year)]
    if week_cap:
        df = df[df['Week'].fillna(0).astype(int) <= int(week_cap)]

    team_games = df[(df['Visitor'].astype(str).str.strip() == team) |
                    (df['Home'].astype(str).str.strip() == team)]
    if team_games.empty:
        return 0.0, []

    opponents = []
    for _, g in team_games.iterrows():
        vis = str(g['Visitor']).strip()
        opp = str(g['Home']).strip() if vis == team else vis
        opponents.append(opp)

    if fpi_ratings:
        opp_scores = [fpi_ratings.get(o, 0.0) for o in opponents]
        sos = round(sum(opp_scores) / len(opp_scores), 3) if opp_scores else 0.0
    else:
        # Fallback: win percentage of opponents
        completed = df[df['Status'].astype(str).str.upper() == 'FINAL'].copy()
        completed['Vis Score']  = pd.to_numeric(completed['Vis Score'],  errors='coerce')
        completed['Home Score'] = pd.to_numeric(completed['Home Score'], errors='coerce')
        opp_wpcts = []
        for opp in opponents:
            w, l = get_team_record(completed, opp, week_cap)
            wpct = w / max(1, w + l)
            opp_wpcts.append(wpct)
        sos = round(sum(opp_wpcts) / len(opp_wpcts), 3) if opp_wpcts else 0.0

    return sos, opponents


def compute_sor(scores_df, team, year=None, week_cap=None, fpi_ratings=None):
    """
    Strength of Record: credit wins over good opponents, penalize losses to weak ones.
    Each win = +opponent_fpi_percentile, each loss = -inverse_fpi_percentile.
    Returns sor_score (higher = better résumé).
    """
    df = scores_df.copy()
    if year:
        df = df[df['YEAR'].fillna(-1).astype(int) == int(year)]
    if week_cap:
        df = df[df['Week'].fillna(0).astype(int) <= int(week_cap)]
    completed = df[df['Status'].astype(str).str.upper() == 'FINAL'].copy()
    completed['Vis Score']  = pd.to_numeric(completed['Vis Score'],  errors='coerce')
    completed['Home Score'] = pd.to_numeric(completed['Home Score'], errors='coerce')
    completed = completed.dropna(subset=['Vis Score', 'Home Score'])

    team_games = completed[(completed['Visitor'].astype(str).str.strip() == team) |
                           (completed['Home'].astype(str).str.strip() == team)]
    if team_games.empty:
        return 0.0

    if not fpi_ratings:
        return 0.0

    # Build percentile ranks of FPI
    all_fpis = sorted(fpi_ratings.values())
    n = len(all_fpis)

    def _pct(fpi_val):
        if n == 0: return 0.5
        pos = sum(1 for v in all_fpis if v <= fpi_val)
        return pos / n

    score_parts = []
    for _, g in team_games.iterrows():
        vis = str(g['Visitor']).strip()
        vs  = float(g['Vis Score'])
        hs  = float(g['Home Score'])
        opp = str(g['Home']).strip() if vis == team else vis
        won = (vs > hs) if vis == team else (hs > vs)
        opp_pct = _pct(fpi_ratings.get(opp, 0.0))
        if won:
            score_parts.append(opp_pct)         # win over good team = high value
        else:
            score_parts.append(-(1.0 - opp_pct))  # loss to weak team = big penalty

    return round(sum(score_parts) / len(score_parts), 4) if score_parts else 0.0


def compute_chaos_rating(scores_df, team, year=None, week_cap=None, fpi_ratings=None):
    """
    Chaos Rating -- volatility/unpredictability score for a team's season.

    Non-linear MOV scaling gives real variance between a 3-pt upset and a 31-pt blowout upset.
    Ranked opponent bonus makes taking down a top-25 team as an underdog the money moment.
    FCS opponents excluded entirely.

    Scale:  80+ = PURE CHAOS  |  50-79 = VOLATILE  |  25-49 = DISRUPTIVE
            5-24 = WILD CARD  |  <0 = CHOKER
    """
    df = scores_df.copy()
    if year:
        df = df[df['YEAR'].fillna(-1).astype(int) == int(year)]
    if week_cap:
        df = df[df['Week'].fillna(0).astype(int) <= int(week_cap)]
    df = df[df['Status'].astype(str).str.upper() == 'FINAL'].copy()
    df['Vis Score']  = pd.to_numeric(df['Vis Score'],  errors='coerce')
    df['Home Score'] = pd.to_numeric(df['Home Score'], errors='coerce')
    df = df.dropna(subset=['Vis Score', 'Home Score'])

    _FCS_P = {'FCS', 'FCSMW', 'FCSW', 'FCSS', 'FCSE'}

    team_games = df[
        (df['Visitor'].astype(str).str.strip() == team) |
        (df['Home'].astype(str).str.strip()    == team)
    ]
    if team_games.empty:
        return 0.0

    fpi = fpi_ratings or {}
    my_fpi = fpi.get(team, 0.0)
    scores = []

    for _, g in team_games.iterrows():
        vis    = str(g['Visitor']).strip()
        vs     = float(g['Vis Score'])
        hs     = float(g['Home Score'])
        margin = abs(vs - hs)
        is_vis = vis == team
        opp    = str(g['Home']).strip() if is_vis else vis
        won    = (vs > hs) if is_vis else (hs > vs)

        # Skip FCS placeholder teams -- meaningless for chaos
        if any(opp.upper().startswith(p) for p in _FCS_P):
            continue

        opp_fpi  = fpi.get(opp, 0.0)
        fpi_gap  = my_fpi - opp_fpi   # positive = I'm favored

        opp_rank_col = 'Home Rank' if is_vis else 'Visitor Rank'
        try:
            opp_ranked = pd.notna(g.get(opp_rank_col)) and int(float(g[opp_rank_col])) <= 25
        except Exception:
            opp_ranked = False

        if won:
            if fpi_gap < -2:
                # Non-linear MOV: (margin/7)^0.65 * 9 gives fractional variance
                # 3pt  upset → ~6pts mov_bonus
                # 14pt upset → ~14pts mov_bonus
                # 35pt upset → ~22pts mov_bonus
                underdog_mag = abs(fpi_gap) * 1.2         # uncapped -- real FPI gap matters
                mov_bonus    = (margin / 7.0) ** 0.65 * 9  # fractional power = spread
                ranked_bonus = 20 if opp_ranked else 0     # knocking off a ranked team = big deal
                scores.append(round(12 + underdog_mag + mov_bonus + ranked_bonus, 2))
            elif fpi_gap > 10:
                scores.append(1.0)    # dominant win -- expected, boring
            else:
                scores.append(3.0)    # close expected win
        else:
            if fpi_gap > 2:
                # Lost as favorite -- penalty scales with how big a favorite you were
                fav_mag          = fpi_gap * 0.8   # uncapped
                unranked_penalty = 12 if not opp_ranked else 0
                scores.append(-(10 + fav_mag + unranked_penalty))
            elif opp_ranked:
                scores.append(-2.0)   # lost to ranked as underdog -- expected
            else:
                scores.append(-6.0)   # lost to unranked as underdog

    return round(sum(scores), 1) if scores else 0.0


@st.cache_data(ttl=600)
def build_full_ratings_table(year=None, week_cap=None):
    """
    Build a complete ratings table for all teams with FPI, SOS, SOR, Chaos, record.
    Returns DataFrame sorted by FPI desc. FCS teams excluded.

    """
    target_year = int(year) if year else CURRENT_YEAR
    df = load_scores_master(target_year)
    if df.empty:
        return pd.DataFrame()

    df['YEAR'] = pd.to_numeric(df.get('YEAR'), errors='coerce')
    df['Week'] = pd.to_numeric(df.get('Week'), errors='coerce')

    # Multi-year data for streak calculation so cross-season streaks carry forward
    _df_multi = load_scores_master(multi_year=True)
    for _c in ('YEAR', 'Week'):
        if _c in _df_multi.columns:
            _df_multi[_c] = pd.to_numeric(_df_multi[_c], errors='coerce')

    # Compute FPI first (needed for SOS/SOR)
    fpi = compute_power_ratings(df, year=target_year, week_cap=week_cap)
    if not fpi:
        return pd.DataFrame()

    completed = df[df['Status'].astype(str).str.upper() == 'FINAL'].copy()
    wk = int(week_cap) if week_cap else None

    # FCS placeholder teams to exclude from display
    _FCS_PREFIXES = {'FCS', 'FCSMW', 'FCSW', 'FCSS', 'FCSE'}

    rows = []
    for team in sorted(fpi.keys()):
        # Skip FCS placeholder teams
        if any(str(team).upper().startswith(p) for p in _FCS_PREFIXES):
            continue
        w, l = get_team_record(completed, team, wk)
        sos, opps = compute_sos(df, team, year=target_year, week_cap=wk, fpi_ratings=fpi)
        sor = compute_sor(df, team, year=target_year, week_cap=wk, fpi_ratings=fpi)
        chaos = compute_chaos_rating(df, team, year=target_year, week_cap=wk, fpi_ratings=fpi)
        streak_n, streak_t = get_team_current_streak(_df_multi if not _df_multi.empty else completed, team, wk or 99)
        qw, best_rk = get_quality_win_context(completed, team, wk or 99)
        rows.append({
            'Team':        team,
            'W':           w,
            'L':           l,
            'WinPct':      round(w / max(1, w + l), 3),
            'FPI':         fpi[team],
            'SOS':         sos,
            'SOR':         sor,
            'Chaos':       chaos,
            'Streak':      f"{streak_n}{streak_t}" if streak_n else '',
            'QualityWins': qw,
            'BestWin':     f"#{best_rk}" if best_rk else '',
            'GamesPlayed': w + l,
        })

    out = pd.DataFrame(rows).sort_values('FPI', ascending=False).reset_index(drop=True)
    if 'Rank' not in out.columns:
        out.insert(0, 'Rank', range(1, len(out) + 1))
    return out



@st.cache_data(ttl=600)
def compute_ms_plus(year=None, week_cap=None):
    """
    MS+ Ratings -- CFB26-tuned composite rating inspired by SP+.
    Returns DataFrame with Team, MSPlus, and component scores.
    """
    target_year = int(year) if year else CURRENT_YEAR

    # ── Load data sources ─────────────────────────────────────────────
    try:
        ratings_df = pd.read_csv('TeamRatingsHistory.csv')
        ratings_df['YEAR'] = pd.to_numeric(ratings_df['YEAR'], errors='coerce')
        ratings_df['TEAM'] = ratings_df['TEAM'].astype(str).str.strip()
    except Exception:
        ratings_df = pd.DataFrame()

    try:
        recruit_df = pd.read_csv('recruiting_class_history_all.csv')
        recruit_df['Year'] = pd.to_numeric(recruit_df.get('Year', recruit_df.get('YEAR', 0)), errors='coerce')
    except Exception:
        recruit_df = pd.DataFrame()

    try:
        # Prefer the new year-keyed top-20 roster file; fall back to full roster
        _top20_file = f'cfb_136_top30_rosters_{target_year}.csv'
        if os.path.exists(_top20_file):
            roster_df = pd.read_csv(_top20_file)
            roster_df['YEAR'] = pd.to_numeric(roster_df.get('YEAR', target_year), errors='coerce')
            roster_df = roster_df[roster_df['YEAR'].fillna(-1).astype(int) == target_year].copy()

            # ── Column rename: watcher writes TEAM/POS/YEAR_CLASS, components expect Team/Pos/Year
            roster_df = roster_df.rename(columns={
                'TEAM':       'Team',
                'POS':        'Pos',
                'YEAR_CLASS': 'Year',
            })

            # ── Team name normalization -- GPT sometimes uses full names or mascots
            _team_norm = {
                'University of Nevada, Las Vegas': 'UNLV',
                'University of South Florida':     'USF',
                'University of Southern California': 'USC',
                'University of Texas at San Antonio': 'UTSA',
                'University of Massachusetts':     'Massachusetts',
                'Southern Methodist':              'SMU',
                'Brigham Young':                   'BYU',
                'Pittsburgh Panthers':             'Pittsburgh',
                # Expansion/created dynasty teams -- mascot variant → canonical name
                'Alabaster Bulldogs':              'Alabaster',
                'Hammond Carnivores':              'Hammond',
                'Rapid City Stegos':               'Rapid City',
            }
            roster_df['Team'] = roster_df['Team'].map(
                lambda t: _team_norm.get(str(t).strip(), str(t).strip())
            )

            # ── Drop only true FCS placeholders GPT hallucinates -- NOT dynasty created teams
            _junk_teams = set()  # no real junk after normalization above
            if _junk_teams:
                roster_df = roster_df[~roster_df['Team'].isin(_junk_teams)].copy()

            # ── Dedup: keep highest-OVR row per (Team, Name, Pos)
            _name_col = 'NAME' if 'NAME' in roster_df.columns else 'Name'
            roster_df = (roster_df
                .sort_values('OVR', ascending=False)
                .drop_duplicates(subset=['Team', _name_col, 'Pos'], keep='first')
                .reset_index(drop=True))

        else:
            roster_df = _load_rosters_full_csv()
            roster_df['Season'] = pd.to_numeric(roster_df.get('Season', roster_df.get('YEAR', target_year)), errors='coerce')
            roster_df = roster_df[roster_df['Season'].fillna(-1).astype(int) == target_year].copy()

        for _rc in ('OVR', 'SPD', 'ACC', 'AGI', 'COD', 'STR', 'AWR'):
            if _rc in roster_df.columns:
                roster_df[_rc] = pd.to_numeric(roster_df[_rc], errors='coerce').fillna(0)
    except Exception:
        roster_df = pd.DataFrame()

    try:
        champs_df = pd.read_csv('champs.csv')
        champs_df['year'] = pd.to_numeric(champs_df.get('year', champs_df.get('Year', 0)), errors='coerce')
    except Exception:
        champs_df = pd.DataFrame()

    try:
        heisman_watch = pd.read_csv('Heisman_watch_history.csv')
        heisman_watch['YEAR'] = pd.to_numeric(heisman_watch.get('YEAR', 0), errors='coerce')
        hw_current = heisman_watch[heisman_watch['YEAR'] == target_year].copy()
        hw_current['RANK'] = pd.to_numeric(hw_current.get('RANK', 99), errors='coerce').fillna(99)
    except Exception:
        hw_current = pd.DataFrame()

    # Get FPI for Clobber Rating component
    fpi_scores = {}
    try:
        _sched = load_scores_master(target_year)
        if not _sched.empty:
            fpi_scores = compute_power_ratings(_sched, year=target_year, week_cap=week_cap)
    except Exception:
        pass

    # Load multi-year schedule for Recent Performance W/L history (last 4 seasons)
    # Priority: schedule_{YEAR}.csv (full league, 2042+) → CPUscores for older years
    _hist_sched = pd.DataFrame()
    try:
        import glob as _glob
        _hist_parts = []
        # Years in range: target_year-4 to target_year-1
        for _hy in range(target_year - 4, target_year):
            _sf = f'schedule_{_hy}.csv'
            if os.path.exists(_sf):
                # schedule_{YEAR}.csv -- full league, preferred
                _hp = pd.read_csv(_sf)
                _hp['YEAR'] = _hy
                _hist_parts.append(_hp)
            else:
                # Fall back to CPUscores year file (user teams only pre-2042)
                _cf = f'CPUscores_MASTER_{_hy}.csv'
                if os.path.exists(_cf):
                    _hp = pd.read_csv(_cf)
                    _hp['YEAR'] = _hy
                    _hist_parts.append(_hp)
        # Also check legacy CPUscores_MASTER.csv for any years not covered above
        if os.path.exists('CPUscores_MASTER.csv'):
            _legacy = pd.read_csv('CPUscores_MASTER.csv')
            if 'YEAR' in _legacy.columns:
                _legacy['YEAR'] = pd.to_numeric(_legacy['YEAR'], errors='coerce')
                _legacy = _legacy[
                    (_legacy['YEAR'] >= target_year - 4) &
                    (_legacy['YEAR'] <  target_year)
                ]
                # Only append years not already covered by schedule_ files
                _covered_years = {int(_hp['YEAR'].iloc[0]) for _hp in _hist_parts if not _hp.empty and 'YEAR' in _hp.columns}
                _legacy = _legacy[~_legacy['YEAR'].isin(_covered_years)]
                if not _legacy.empty:
                    _hist_parts.append(_legacy)

        if _hist_parts:
            _hist_sched = pd.concat(_hist_parts, ignore_index=True)
            _hist_sched['YEAR'] = pd.to_numeric(_hist_sched.get('YEAR', target_year), errors='coerce')
            _hist_sched['Vis Score']  = pd.to_numeric(_hist_sched.get('Vis Score', 0),  errors='coerce')
            _hist_sched['Home Score'] = pd.to_numeric(_hist_sched.get('Home Score', 0), errors='coerce')
            # Only completed games
            _status_col = next((c for c in ('Status','STATUS') if c in _hist_sched.columns), None)
            if _status_col:
                _hist_sched = _hist_sched[
                    _hist_sched[_status_col].astype(str).str.upper() == 'FINAL'
                ].copy()
            _hist_sched = _hist_sched.reset_index(drop=True)
    except Exception:
        _hist_sched = pd.DataFrame()

    # Build team list from ratings
    if ratings_df.empty:
        return pd.DataFrame()
    yr_ratings = ratings_df[ratings_df['YEAR'].fillna(-1).astype(int) == target_year].copy()
    if yr_ratings.empty:
        yr_ratings = ratings_df[ratings_df['YEAR'].fillna(-1).astype(int) == target_year - 1].copy()
    if yr_ratings.empty:
        return pd.DataFrame()

    ratings_teams = yr_ratings['TEAM'].dropna().unique().tolist()

    # If TeamRatingsHistory only has user teams (sparse, < 20 entries),
    # supplement from schedule_{YEAR}.csv so MS+ covers the full field.
    _sched_teams = set()
    try:
        _sm = load_scores_master(target_year)
        if not _sm.empty:
            for _col in ('Visitor', 'Home', 'VISITOR', 'HOME'):
                if _col in _sm.columns:
                    _sched_teams.update(
                        _sm[_col].dropna().astype(str).str.strip().tolist()
                    )
    except Exception:
        pass

    if len(ratings_teams) < 20 and _sched_teams:
        # Sparse -- build from full schedule, ratings_teams values take priority in loop
        all_teams = sorted(set(ratings_teams) | _sched_teams)
    else:
        all_teams = ratings_teams

    # Veteran presence mean (league-wide 86+ JR/SR OVR) for relative comparison
    _VET_YEARS = {'JR','JR (RS)','SR','SR (RS)','JR(RS)','SR(RS)'}
    vet_mean = 0.0
    if not roster_df.empty and 'Year' in roster_df.columns:
        _vet_all = roster_df[
            (roster_df['OVR'] >= 86) &
            (roster_df['Year'].astype(str).str.strip().str.upper().isin({y.upper() for y in _VET_YEARS}))
        ]
        vet_mean = _vet_all['OVR'].mean() if not _vet_all.empty else 86.0

    rows = []
    for team in all_teams:
        team = str(team).strip()
        components = {}

        # ── 1. Team Ratings (OVR, OFF, DEF) -- weight 0.20 ────────────
        tr = yr_ratings[yr_ratings['TEAM'] == team]
        if not tr.empty:
            r0 = tr.iloc[0]
            t_ovr = safe_num(r0.get('OVERALL', r0.get('OVR', 75)), 75)
            t_off = safe_num(r0.get('OFFENSE', r0.get('OFF', 75)), 75)
            t_def = safe_num(r0.get('DEFENSE', r0.get('DEF', 75)), 75)
        else:
            t_ovr = t_off = t_def = 75.0
        components['ratings'] = round((t_ovr * 0.5 + t_off * 0.25 + t_def * 0.25 - 70) / 30 * 100, 1)

        # ── 2. Recruiting Pipeline (last 4 class ranks) -- weight 0.15 ─
        # Use OVERALL class rank only -- avoids mixing HS/Transfer ranks with overall rank
        rec_score = None
        if not recruit_df.empty and 'Team' in recruit_df.columns and 'Rank' in recruit_df.columns:
            _rc = recruit_df[
                (recruit_df['Team'].astype(str).str.strip() == team) &
                (recruit_df['Year'] >= target_year - 4) &
                (recruit_df['Year'] < target_year)
            ].copy()
            # Prefer OVERALL rank; fall back to any ClassType if OVERALL not present
            if 'ClassType' in _rc.columns:
                _rc_overall = _rc[_rc['ClassType'].astype(str).str.upper() == 'OVERALL'].copy()
                if not _rc_overall.empty:
                    _rc = _rc_overall
            _rc['Rank'] = pd.to_numeric(_rc['Rank'], errors='coerce')
            if not _rc.empty:
                avg_rk = _rc['Rank'].dropna().mean()
                rec_score = max(0, min(100, round((130 - avg_rk) / 130 * 100, 1)))
        if rec_score is None:
            # No recruiting history -- proxy from team OVR
            rec_score = max(0, min(100, round((t_ovr - 70) / 30 * 100, 1)))
        components['recruiting'] = rec_score
        xfer_score = 50.0
        if not recruit_df.empty and 'ClassType' in recruit_df.columns:
            _xf = recruit_df[
                (recruit_df['Team'].astype(str).str.strip() == team) &
                (recruit_df['Year'] >= target_year - 4) &
                (recruit_df['Year'] < target_year) &
                (recruit_df['ClassType'].astype(str).str.upper().isin({'TRANSFER','PORTAL'}))
            ].copy()
            if not _xf.empty and 'Rank' in _xf.columns:
                _xf['Rank'] = pd.to_numeric(_xf['Rank'], errors='coerce')
                avg_xf = _xf['Rank'].dropna().mean()
                xfer_score = max(0, min(100, round((130 - avg_xf) / 130 * 100, 1)))
        components['transfer'] = xfer_score

        # ── 4. Veteran Presence (86+ OVR JR/SR) -- weight 0.10 ────────
        vet_score = 50.0
        if not roster_df.empty and 'Team' in roster_df.columns and 'Year' in roster_df.columns:
            _tv = roster_df[
                (roster_df['Team'].astype(str).str.strip() == team) &
                (roster_df['OVR'] >= 86) &
                (roster_df['Year'].astype(str).str.strip().str.upper().isin({y.upper() for y in _VET_YEARS}))
            ]
            if not _tv.empty:
                team_vet_avg = _tv['OVR'].mean()
                vet_score = min(100, max(0, 50 + (team_vet_avg - vet_mean) * 5))
                vet_score = round(vet_score + len(_tv) * 0.5, 1)  # bonus for depth
        components['veteran'] = min(100, vet_score)

        # ── 5. Starting Speed (90+ SPD at JR/SR level) -- weight 0.07 ─
        spd_score = 50.0
        if not roster_df.empty and 'Team' in roster_df.columns:
            _ts = roster_df[
                (roster_df['Team'].astype(str).str.strip() == team) &
                (roster_df['SPD'] >= 90) &
                (roster_df['Year'].astype(str).str.strip().str.upper().isin({y.upper() for y in _VET_YEARS}))
            ]
            spd_score = min(100, 50 + len(_ts) * 4)
        components['speed'] = spd_score

        # ── 6. Captain of the Ship (QB rating) -- weight 0.12 ─────────
        qb_score = 50.0
        if not roster_df.empty and 'Pos' in roster_df.columns:
            _qbs = roster_df[
                (roster_df['Team'].astype(str).str.strip() == team) &
                (roster_df['Pos'].astype(str).str.upper().isin({'QB'}))
            ].sort_values('OVR', ascending=False)
            if not _qbs.empty:
                _qb1 = _qbs.iloc[0]
                _qb_ovr = float(_qb1.get('OVR', 75))
                _qb_spd = float(_qb1.get('SPD', 75))
                _qb_acc = float(_qb1.get('ACC', 75))
                if _qb_ovr >= 91:
                    qb_score = 90.0
                elif _qb_ovr >= 85:
                    qb_score = 70.0
                elif _qb_ovr >= 80:
                    qb_score = 55.0
                else:
                    qb_score = 35.0
                # Dual-threat bonus
                if _qb_spd >= 88 and _qb_acc >= 85:
                    qb_score = min(100, qb_score + 10)
        components['qb'] = qb_score

        # ── 7. Recent Performance (last 4 seasons) -- weight 0.10 ──────
        # Blends: titles (natty +15, conf +8) + win rate from schedule history
        perf_score = 50.0

        # Title component -- from champs.csv
        natty_count = 0
        conf_count  = 0
        if not champs_df.empty and 'Team' in champs_df.columns:
            _cp = champs_df[
                (champs_df['Team'].astype(str).str.strip() == team) &
                (champs_df['year'] >= target_year - 4) &
                (champs_df['year'] <  target_year)
            ]
            if not _cp.empty:
                _type_col = 'type' if 'type' in _cp.columns else ('Type' if 'Type' in _cp.columns else None)
                if _type_col:
                    natty_count = len(_cp[_cp[_type_col].astype(str).str.upper().str.contains('NATTY|NATIONAL', na=False)])
                    conf_count  = len(_cp[_cp[_type_col].astype(str).str.upper().str.contains('CONF', na=False)])
        title_boost = natty_count * 15 + conf_count * 8

        # Win rate component -- only fires when schedule_{YEAR}.csv files exist in the lookback window.
        # This ensures CPU and user teams are always on equal footing:
        # - Season 2042: no schedule_ history yet → everyone gets neutral 50
        # - Season 2043+: schedule_2042.csv in window → all 136 teams get real win rates
        win_rate_score = 50.0
        _has_schedule_history = any(
            os.path.exists(f'schedule_{_hy}.csv')
            for _hy in range(target_year - 4, target_year)
        )
        if _has_schedule_history and not _hist_sched.empty:
            _vis_col = next((c for c in ('Visitor','VISITOR','visitor') if c in _hist_sched.columns), None)
            _hom_col = next((c for c in ('Home','HOME','home')         if c in _hist_sched.columns), None)
            if _vis_col and _hom_col:
                _tm_games = _hist_sched[
                    (_hist_sched[_vis_col].astype(str).str.strip() == team) |
                    (_hist_sched[_hom_col].astype(str).str.strip() == team)
                ]
                if not _tm_games.empty:
                    _wins = 0
                    for _, _g in _tm_games.iterrows():
                        _vs = float(_g.get('Vis Score', 0) or 0)
                        _hs = float(_g.get('Home Score', 0) or 0)
                        _is_vis = str(_g.get(_vis_col, '')).strip() == team
                        _won = (_vs > _hs) if _is_vis else (_hs > _vs)
                        if _won: _wins += 1
                    _win_pct = _wins / len(_tm_games)
                    win_rate_score = max(0, min(100, round((_win_pct - 0.200) / 0.600 * 100, 1)))

        # Blend: 60% win rate, 40% titles
        perf_score = min(100, round(win_rate_score * 0.60 + (50 + title_boost) * 0.40, 1))
        components['performance'] = perf_score

        # ── 8. Clobber Rating (FPI) -- weight 0.08 ────────────────────
        fpi_val = fpi_scores.get(team, None)
        if fpi_val is not None and fpi_scores:
            all_fpi   = list(fpi_scores.values())
            fpi_mean  = sum(all_fpi) / len(all_fpi)
            fpi_stdev = max((sum((x - fpi_mean)**2 for x in all_fpi) / len(all_fpi))**0.5, 1)
            clobber   = round(50 + (fpi_val - fpi_mean) / fpi_stdev * 15, 1)
            clobber   = max(0, min(100, clobber))
        else:
            clobber = 50.0
        components['clobber'] = clobber

        # ── 8b. Chaos Rating -- weight 0.03 ───────────────────────────
        try:
            _chaos_sched = load_scores_master(target_year)
            raw_chaos = compute_chaos_rating(
                _chaos_sched, team, year=target_year,
                week_cap=week_cap, fpi_ratings=fpi_scores
            )
        except Exception:
            raw_chaos = 0.0
        chaos_score = max(0, min(100, round(50 + raw_chaos * 1.5, 1)))
        components['chaos'] = chaos_score

        # ── 9. Generational Talent -- weight 0.05 ─────────────────────
        # A player qualifies if OVR >= 90 AND at least 2 of these are >= 95:
        #   Speed (SPD), Acceleration (ACC), Agility (AGI), Change of Direction (COD)
        gen_score = 50.0
        if not roster_df.empty and 'Team' in roster_df.columns:
            _candidates = roster_df[
                (roster_df['Team'].astype(str).str.strip() == team) &
                (roster_df['OVR'] >= 90)
            ].copy()
            def _is_generational(r):
                attrs = [
                    float(r.get('SPD', 0) or 0),
                    float(r.get('ACC', 0) or 0),
                    float(r.get('AGI', 0) or 0),
                    float(r.get('COD', 0) or 0),
                ]
                return sum(1 for a in attrs if a >= 95) >= 2
            _gen_count = _candidates.apply(_is_generational, axis=1).sum() if not _candidates.empty else 0
            gen_score = min(100, 50 + int(_gen_count) * 12)
        components['generational'] = round(gen_score, 1)

        # ── 10. Heisman Hopeful -- weight 0.02 ────────────────────────
        hh_score = 50.0
        if not hw_current.empty and 'TEAM' in hw_current.columns:
            _hh = hw_current[hw_current['TEAM'].astype(str).str.strip() == team]
            top5 = _hh[_hh['RANK'] <= 5]
            if len(top5) >= 2:
                hh_score = 100.0
            elif len(top5) == 1:
                hh_score = 80.0
            elif not _hh.empty:
                hh_score = 65.0
        components['heisman'] = hh_score

        # ── Composite MS+ score ───────────────────────────────────────
        # Weights total = 1.00
        weights = {
            'ratings': 0.20, 'recruiting': 0.15, 'transfer': 0.08,
            'veteran': 0.10, 'speed': 0.07,      'qb': 0.12,
            'performance': 0.10, 'clobber': 0.08,
            'generational': 0.05, 'heisman': 0.02, 'chaos': 0.03,
        }
        ms_plus = sum(components.get(k, 50) * v for k, v in weights.items())
        ms_plus = round(ms_plus, 1)

        # Get FPI data to include in same row
        fpi_rk_row = {}
        rows.append({
            'Team': team,
            'MSPlus': ms_plus,
            **{f'_{k}': v for k, v in components.items()},
        })

    if not rows:
        return pd.DataFrame()

    msp_df = pd.DataFrame(rows).sort_values('MSPlus', ascending=False).reset_index(drop=True)
    # FPI/SOS/SOR columns are intentionally NOT merged here.
    # Use get_ratings_and_ms_plus() at render sites so FPI is computed once and shared.
    for _c in ['W','L','FPI','SOS','SOR','QualityWins']:
        msp_df[_c] = 0.0
    msp_df['Streak']  = ''
    msp_df['BestWin'] = ''
    return msp_df


def get_ratings_and_ms_plus(year=None, week_cap=None):
    """
    Returns (fpi_df, msp_df) -- reads from pre-computed CSVs on first boot if available,
    falls back to live computation otherwise.

    Pre-computed files (written by COMPUTE_RATINGS.bat):
      FPI/fpi_ratings_{YEAR}_wk{WEEK}.csv  -- FPI/SOS/SOR table
      FPI/ms_plus_{YEAR}_wk{WEEK}.csv      -- MS+ component table

    Falls back to repo root for backwards compatibility if FPI/ subfolder not found.
    If no pre-computed file exists, computes live (slow on first boot).
    """
    target_year = int(year) if year else CURRENT_YEAR
    wk          = int(week_cap) if week_cap else CURRENT_WEEK_NUMBER

    base_name_fpi = f'fpi_ratings_{target_year}_wk{wk}.csv'
    base_name_msp = f'ms_plus_{target_year}_wk{wk}.csv'

    # Check FPI/ subfolder first, then root fallback
    def _find_file(base_name):
        subfolder = os.path.join('FPI', base_name)
        if os.path.exists(subfolder):
            return subfolder
        if os.path.exists(base_name):
            return base_name
        return None

    fpi_path = _find_file(base_name_fpi)
    msp_path = _find_file(base_name_msp)

    fpi_df = pd.DataFrame()
    msp_df = pd.DataFrame()

    if fpi_path:
        try:
            fpi_df = pd.read_csv(fpi_path)
        except Exception:
            fpi_df = pd.DataFrame()

    if msp_path:
        try:
            msp_df = pd.read_csv(msp_path)
        except Exception:
            msp_df = pd.DataFrame()

    # ── Fall back to live computation if CSVs missing ─────────────────
    if fpi_df.empty:
        fpi_df = build_full_ratings_table(year=year, week_cap=week_cap)
    if msp_df.empty:
        msp_df = compute_ms_plus(year=year, week_cap=week_cap)

    # ── Merge FPI columns into MS+ df ─────────────────────────────────
    if not fpi_df.empty and not msp_df.empty:
        try:
            _fpi_cols = ['Team','W','L','FPI','SOS','SOR','Chaos','Streak','QualityWins','BestWin']
            _fpi_slim = fpi_df[[c for c in _fpi_cols if c in fpi_df.columns]].copy()
            msp_df = msp_df.drop(
                columns=[c for c in ['W','L','FPI','SOS','SOR','Chaos','Streak','QualityWins','BestWin']
                         if c in msp_df.columns],
                errors='ignore'
            )
            msp_df = msp_df.merge(_fpi_slim, on='Team', how='left')
            for _c in ['W','L','FPI','SOS','SOR','Chaos','QualityWins']:
                if _c in msp_df.columns:
                    msp_df[_c] = pd.to_numeric(msp_df[_c], errors='coerce').fillna(0)
            for _c in ['Streak','BestWin']:
                if _c in msp_df.columns:
                    msp_df[_c] = msp_df[_c].fillna('')
        except Exception:
            pass

    return fpi_df, msp_df


# ── SPEED FREAKS -- LIVE COMPUTATION ──────────────────────────────────────────
@st.cache_data(ttl=300)
def build_speed_freaks_live(year=None):
    """Build Speed Freaks table live from cfb_136_top30_rosters_{YEAR}.csv for all teams."""
    target_year=int(year) if year else CURRENT_YEAR
    ros_file=f'cfb_136_top30_rosters_{target_year}.csv'
    if not os.path.exists(ros_file): return pd.DataFrame()
    try:
        ros=pd.read_csv(ros_file)
        ros.columns=[str(c).strip() for c in ros.columns]
        ros['TEAM']=ros['TEAM'].astype(str).str.strip()
        for c in ('SPD','ACC','AGI','COD','OVR','STR'):
            if c in ros.columns: ros[c]=pd.to_numeric(ros[c],errors='coerce').fillna(0)
        if 'YEAR' in ros.columns:
            ros['YEAR']=pd.to_numeric(ros['YEAR'],errors='coerce')
            ros=ros[ros['YEAR'].fillna(-1).astype(int)==target_year].copy()
        # Enforce top 30 per team by OVR — consistent with CSV name convention
        if 'OVR' in ros.columns:
            ros=ros.sort_values('OVR',ascending=False).groupby('TEAM').head(30).copy()
        ros['POS_U']=ros['POS'].astype(str).str.upper().str.strip()
        _off_pos={'QB','HB','WR','TE','LT','LG','C','RG','RT'}
        _def_pos={'CB','FS','SS','MLB','OLB','DE','DT','LEDG','REDG','SAM','MIKE','WILL','ILB','LB'}
        _front7={'DE','DT','LEDG','REDG','SAM','MIKE','WILL','MLB','ILB','OLB','LB'}
        _ol_pos={'LT','LG','C','RG','RT'}
        rows=[]
        for team,grp in ros.groupby('TEAM'):
            s90   = int((grp['SPD']>=90).sum())
            cheat = int(((grp['SPD']>=90)&(grp['ACC']>=90)&(grp['AGI']>=90)&(grp['COD']>=90)).sum())
            gen   = int(((grp['SPD']>=96)|(grp['ACC']>=96)).sum())
            off_s = int(((grp['SPD']>=90)&(grp['POS_U'].isin(_off_pos))).sum())
            def_s = int(((grp['SPD']>=90)&(grp['POS_U'].isin(_def_pos))).sum())
            mon   = int((grp['POS_U'].isin(_front7)&(((grp['ACC']>=90)&(grp['SPD']>=84))|((grp['SPD']>=90)&(grp['ACC']>=84)))).sum())
            hogs  = int((grp['POS_U'].isin(_ol_pos)&(grp['AGI']>=85)&(grp['STR']>=90)).sum())
            score = s90*2 + cheat*3 + gen*5 + mon*2 + hogs*1.5
            mph   = round(score * 1.8, 1)  # composite speed index, no cap
            where = ('Off & Def' if off_s>0 and def_s>0 else
                     'Offense' if off_s>def_s else
                     'Defense' if def_s>off_s else 'Balanced')
            rows.append({'TEAM':team,'S90':s90,'CHEAT':cheat,'MONSTER':mon,
                         'QUICK_HOG':hogs,'GEN':gen,'OFF_SPD':off_s,'DEF_SPD':def_s,
                         'SCORE':score,'MPH':mph,'WHERE':where,
                         'IS_USER':team in ALL_USER_TEAMS})
        if not rows: return pd.DataFrame()
        df=pd.DataFrame(rows).sort_values('SCORE',ascending=False).reset_index(drop=True)
        df.insert(0,'RANK',range(1,len(df)+1))
        return df
    except: return pd.DataFrame()

def render_speed_freaks_table(df, show_n=25):
    """Render compact FPI-style Speed Freaks table."""
    if df.empty:
        st.info("No roster data found. Push cfb_136_top30_rosters_{YEAR}.csv to enable Speed Freaks.")
        return
    st.markdown("""
    <style>
    .sf-wrap{overflow-x:auto;border:1px solid #1e293b;border-radius:8px;}
    .sf-table{width:100%;border-collapse:collapse;background:#06090f;}
    @media(max-width:768px){
        .sf-table th{padding:3px 3px!important;font-size:.48rem!important;}
        .sf-table td{padding:3px 3px!important;font-size:.65rem!important;}}
    </style>""", unsafe_allow_html=True)
    _sf_sort_opts={"Speed Rank":"RANK","90+SPD":"S90","Cheat Codes":"CHEAT","Monsters":"MONSTER","Q-Hogs":"QUICK_HOG","Gen Freaks":"GEN","MPH":"MPH"}
    c1,c2,c3,c4=st.columns([2,1,1,1])
    with c1: st.caption(f"Speed profile for {len(df)} teams — live from rosters.")
    with c2:
        _sf_sort_lbl=st.selectbox("Sort by",list(_sf_sort_opts.keys()),index=0,key="sf_sort_col")
        _sf_sort_key=_sf_sort_opts[_sf_sort_lbl]
    with c3:
        show_all=st.checkbox("Show all",key="sf_show_all")
    with c4:
        _sf_user_only=st.checkbox("Users only",value=False,key="sf_user_only")
    _df_sort=df.sort_values(_sf_sort_key,ascending=_sf_sort_key=="RANK").reset_index(drop=True)
    if _sf_user_only: _df_sort=_df_sort[_df_sort["IS_USER"]]
    display=_df_sort if show_all else _df_sort.head(show_n)
    thead=(
        "<tr style='background:#0a1220;'>"
        "<th style='padding:5px 6px;color:#1e293b;font-size:.58rem;width:24px;text-align:center;'>#</th>"
        "<th style='padding:5px 6px;color:#475569;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:left;'>Team</th>"
        "<th style='padding:5px 6px;color:#38bdf8;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:center;'>90+SPD</th>"
        "<th style='padding:5px 6px;color:#60a5fa;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:center;'>Cheat</th>"
        "<th style='padding:5px 6px;color:#f97316;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:center;'>Monster</th>"
        "<th style='padding:5px 6px;color:#22c55e;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:center;'>Q-Hog</th>"
        "<th style='padding:5px 6px;color:#fbbf24;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:center;'>Gen</th>"
        "<th style='padding:5px 6px;color:#94a3b8;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:center;'>MPH</th>"
        "</tr>"
    )
    rows_html=""
    for _,r in display.iterrows():
        tm=str(r['TEAM']); is_u=r['IS_USER']
        uc=get_team_primary_color(tm) if is_u else "#0f172a"
        lg=get_school_logo_src(tm)
        lh=f"<img src='{lg}' style='width:18px;height:18px;object-fit:contain;vertical-align:middle;margin-right:4px;'/>" if lg else ""
        ab=_abbrev(tm)
        nw="font-weight:900;color:#f8fafc;" if is_u else "font-weight:400;color:#64748b;"
        bg=f"background:linear-gradient(90deg,{uc}22 0%,#06090f 30%);" if is_u else "background:#06090f;"
        bl=f"border-left:3px solid {uc};" if is_u else "border-left:2px solid #0f172a;"
        s90=int(r['S90']); cheat=int(r['CHEAT']); mon=int(r['MONSTER'])
        hog=int(r['QUICK_HOG']); gen=int(r['GEN']); mph=float(r['MPH'])
        rk=int(r['RANK'])
        s90c="#38bdf8" if s90>=15 else ("#60a5fa" if s90>=8 else "#475569")
        chc="#60a5fa" if cheat>=8 else ("#94a3b8" if cheat>=3 else "#1e293b")
        mc="#f97316" if mon>=5 else ("#fbbf24" if mon>=2 else "#334155")
        hgc="#22c55e" if hog>=3 else ("#94a3b8" if hog>=1 else "#334155")
        gc="#fbbf24" if gen>=3 else ("#94a3b8" if gen>=1 else "#334155")
        rows_html+=(
            f"<tr style='{bg}{bl}'>"
            f"<td style='padding:4px 5px;color:#1e293b;font-size:.65rem;text-align:center;'>{rk}</td>"
            f"<td style='padding:4px 5px;white-space:nowrap;'>{lh}"
            f"<span style='{nw}font-size:.8rem;font-family:Barlow Condensed,sans-serif;'>{html.escape(ab)}</span></td>"
            f"<td style='padding:4px 5px;text-align:center;font-family:Bebas Neue,sans-serif;color:{s90c};font-size:.9rem;'>{s90}</td>"
            f"<td style='padding:4px 5px;text-align:center;font-family:Bebas Neue,sans-serif;color:{chc};font-size:.9rem;'>{cheat}</td>"
            f"<td style='padding:4px 5px;text-align:center;font-family:Bebas Neue,sans-serif;color:{mc};font-size:.9rem;'>{mon}</td>"
            f"<td style='padding:4px 5px;text-align:center;font-family:Bebas Neue,sans-serif;color:{hgc};font-size:.9rem;'>{hog}</td>"
            f"<td style='padding:4px 5px;text-align:center;font-family:Bebas Neue,sans-serif;color:{gc};font-size:.9rem;'>{gen}</td>"
            f"<td style='padding:4px 5px;text-align:center;color:#94a3b8;font-size:.78rem;'>{mph:.0f}</td>"
            f"</tr>"
        )
    st.markdown(
        f"<div class='sf-wrap'><table class='sf-table'>"
        f"<thead>{thead}</thead><tbody>{rows_html}</tbody></table></div>",
        unsafe_allow_html=True
    )

# ── ATTRITION RATING ENGINE ───────────────────────────────────────────────────
STARTER_SLOTS = {
    'QB':1,'HB':2,'WR':3,'TE':2,'FB':1,
    'LT':1,'LG':1,'C':1,'RG':1,'RT':1,
    'LEDG':2,'REDG':2,'DE':2,'DT':2,
    'WILL':2,'SAM':2,'MLB':2,'ILB':2,'OLB':2,'LB':2,
    'CB':3,'FS':1,'SS':1,'K':1,'P':1,
}

def infer_starter(pos, ovr, team, roster_df):
    """Return True if player is a starter based on OVR rank at position on team."""
    pos_u=str(pos).strip().upper()
    slots=STARTER_SLOTS.get(pos_u, 1)
    try:
        if roster_df.empty: return ovr>=80
        team_grp=roster_df[roster_df['TEAM'].astype(str).str.strip()==team]
        pos_grp=team_grp[team_grp['POS'].astype(str).str.upper().str.strip()==pos_u]
        if pos_grp.empty: return ovr>=80
        ranked=pos_grp['OVR'].sort_values(ascending=False).reset_index(drop=True)
        if len(ranked)==0: return False
        rank=ranked.searchsorted(-ovr, side='left')
        return int(rank) < slots
    except: return ovr>=80

@st.cache_data(ttl=300)
def compute_attrition_ratings(year=None):
    """Compute per-team attrition rating from transfers + NFL draft data."""
    target_year=int(year) if year else CURRENT_YEAR
    results={}
    # Load full roster for starter inference
    roster_df=pd.DataFrame()
    for ros_file in [f'cfb26_rosters_full.csv', f'cfb_136_top30_rosters_{target_year}.csv']:
        if os.path.exists(ros_file):
            try:
                _r=pd.read_csv(ros_file)
                if 'TEAM' in _r.columns and 'POS' in _r.columns and 'OVR' in _r.columns:
                    _r['OVR']=pd.to_numeric(_r['OVR'],errors='coerce').fillna(0)
                    if 'Season' in _r.columns:
                        _r['Season']=pd.to_numeric(_r['Season'],errors='coerce')
                        _r=_r[_r['Season'].fillna(-1).astype(int)==target_year]
                    roster_df=_r.copy()
                    break
            except: pass
    # Load transfers
    transfers=pd.DataFrame()
    try:
        transfers=pd.read_csv('attrition_transfers.csv')
        transfers.columns=[str(c).strip() for c in transfers.columns]
        # Transfers with Year == target_year are this season's attrition
        transfers['Year']=pd.to_numeric(transfers.get('Year',transfers.get('YEAR',target_year)),errors='coerce')
        transfers=transfers[(transfers['Year'].fillna(-1).astype(int)==target_year) &
                           (transfers['TransferStatus'].astype(str).str.strip()=='Leaving')].copy()
        transfers['OVR']=pd.to_numeric(transfers['OVR'],errors='coerce').fillna(0)
    except: pass
    # Load NFL draft
    draft=pd.DataFrame()
    try:
        draft=pd.read_csv('cfb_draft_results.csv')
        draft.columns=[str(c).strip() for c in draft.columns]
        draft['DraftYear']=pd.to_numeric(draft['DraftYear'],errors='coerce')
        # Draft results for current year's outgoing class = CURRENT_YEAR draft
        draft=draft[draft['DraftYear'].fillna(-1).astype(int)==target_year].copy()
        draft['DraftRound']=pd.to_numeric(draft['DraftRound'],errors='coerce').fillna(8)
    except: pass
    for user,team in USER_TEAMS.items():
        pts=0.0; breakdown=[]
        # Departing seniors (year col = target_year in roster CSV)
        try:
            _sr_file=f'cfb_136_top30_rosters_{target_year}.csv'
            if os.path.exists(_sr_file):
                _sr_df=pd.read_csv(_sr_file)
                _sr_df.columns=[str(c).strip() for c in _sr_df.columns]
                _tc_s=next((c for c in _sr_df.columns if c.upper()=='TEAM'),'TEAM')
                if _tc_s!='TEAM': _sr_df=_sr_df.rename(columns={_tc_s:'TEAM'})
                _sr_df['TEAM']=_sr_df['TEAM'].astype(str).str.strip()
                _sr_df['OVR']=pd.to_numeric(_sr_df.get('OVR',0),errors='coerce').fillna(0)
                if 'YEAR' in _sr_df.columns: _sr_df=_sr_df[pd.to_numeric(_sr_df['YEAR'],errors='coerce').fillna(-1).astype(int)==target_year]
                _yr_cs=next((c for c in ('YEAR_CLASS','Class','CLASS') if c in _sr_df.columns),None)
                _team_srs=_sr_df[(_sr_df['TEAM']==team)&(_sr_df[_yr_cs].astype(str).apply(is_senior_label))].copy() if _yr_cs else pd.DataFrame()
                for _,_sr in _team_srs.iterrows():
                    _sr_ovr=float(_sr.get('OVR',70)); _sr_pos=str(_sr.get('POS',_sr.get('Pos','?')))
                    _sr_nm=str(_sr.get('NAME',_sr.get('Name','?')))
                    is_start_s=infer_starter(_sr_pos,_sr_ovr,team,roster_df)
                    if is_start_s: _sadd=1.5; _slbl=f'🎓 {_sr_nm} ({_sr_pos}, {int(_sr_ovr)} OVR) -- Sr Graduating (Starter)'
                    else: _sadd=0.5; _slbl=f'🎓 {_sr_nm} ({_sr_pos}, {int(_sr_ovr)} OVR) -- Sr Graduating (Backup)'
                    pts+=_sadd
                    breakdown.append({'type':'senior','label':_slbl,'pts':_sadd,'player':_sr_nm,'pos':_sr_pos,'ovr':_sr_ovr})
        except: pass

        # NFL draft losses
        team_draft=pd.DataFrame()
        if not draft.empty:
            dc=next((c for c in ('CollegeTeam','Team','TEAM') if c in draft.columns),None)
            if dc: team_draft=draft[draft[dc].astype(str).str.strip()==team]
        for _,dr in team_draft.iterrows():
            rnd=int(safe_num(dr.get('DraftRound',8),8))
            player=str(dr.get('Player','?')); pos=str(dr.get('Pos','?')); ovr=int(safe_num(dr.get('OVR',0),0))
            if rnd==1:
                pts+=3.0; label=f"🥇 {player} ({pos}, {ovr} OVR) -- Rd 1 NFL"
            elif rnd<=3:
                pts+=2.0; label=f"📈 {player} ({pos}, {ovr} OVR) -- Rd {rnd} NFL"
            else:
                pts+=1.0; label=f"🏈 {player} ({pos}, {ovr} OVR) -- Rd {rnd} NFL"
            breakdown.append({'type':'nfl','label':label,'pts':pts,'rnd':rnd,'player':player,'pos':pos,'ovr':ovr})
        # Transfer losses
        team_xf=pd.DataFrame()
        if not transfers.empty:
            tc=next((c for c in ('Team','TEAM') if c in transfers.columns),None)
            if tc: team_xf=transfers[transfers[tc].astype(str).str.strip()==team]
        for _,xr in team_xf.iterrows():
            pos=str(xr.get('Pos','?')); ovr=float(xr.get('OVR',70))
            player=str(xr.get('Player','?')); reason=str(xr.get('ReasonDetail',''))
            is_start=infer_starter(pos,ovr,team,roster_df)
            if is_start:
                add=1.5; lbl=f"🚪 {player} ({pos}, {int(ovr)} OVR) -- Transfer Out (Starter)"
            else:
                add=0.5; lbl=f"🚶 {player} ({pos}, {int(ovr)} OVR) -- Transfer Out (Backup)"
            pts+=add
            breakdown.append({'type':'transfer','label':lbl,'pts':add,'player':player,'pos':pos,'ovr':ovr,'is_starter':is_start})
        # Reduce pts if strong incoming class offsets losses
        try:
            _inc_r=pd.read_csv('attrition_incoming.csv') if os.path.exists('attrition_incoming.csv') else pd.DataFrame()
            if not _inc_r.empty:
                _inc_r.columns=[str(c).strip() for c in _inc_r.columns]
                _inc_r['Year']=pd.to_numeric(_inc_r['Year'],errors='coerce').fillna(0).astype(int)
                _inc_r['StarRating']=pd.to_numeric(_inc_r.get('StarRating',0),errors='coerce').fillna(0)
                _inc_r_team=_inc_r[(_inc_r['Year']==target_year)&(_inc_r['Team'].astype(str).str.strip()==team)]
                if not _inc_r_team.empty:
                    _avg_star=_inc_r_team['StarRating'].mean(); _cnt=len(_inc_r_team)
                    # 5-star avg class of 10 = 5pt reduction; scales with stars and count
                    _reduction=round(max(0.0,min(6.0,(_avg_star-3.0)*1.5+(_cnt-4)*0.15)),1)
                    pts=max(0,pts-_reduction)
        except: pass
        # Tier
        if pts<=4:   tier="Manageable"; tier_c="#10b981"; tier_emoji="✅"
        elif pts<=8:  tier="Hurting";    tier_c="#f59e0b"; tier_emoji="⚠️"
        elif pts<=12: tier="Rebuilding"; tier_c="#f97316"; tier_emoji="🔥"
        else:         tier="Total Teardown"; tier_c="#ef4444"; tier_emoji="💀"
        results[user]={'team':team,'pts':round(pts,1),'tier':tier,'tier_c':tier_c,
                       'tier_emoji':tier_emoji,'breakdown':breakdown,
                       'nfl_count':len(team_draft),'transfer_count':len(team_xf)}
    return results

# ── TICKER ─────────────────────────────────────────────────────────────────────
def _team_color_span(team, text):
    c=get_team_primary_color(team)
    try:
        r,g,b=int(c[1:3],16),int(c[3:5],16),int(c[5:7],16)
        lum=0.299*r+0.587*g+0.114*b
        if lum<60: c=f'#{min(255,r+80):02x}{min(255,g+80):02x}{min(255,b+80):02x}'
    except: pass
    return f"<span style='color:{c};font-weight:900;'>{html.escape(str(text))}</span>"

def _colorize_headline(text):
    escaped=html.escape(str(text)).upper()
    team_names=sorted(TEAM_VISUALS.keys(),key=len,reverse=True)
    pattern=re.compile(r'(?<![A-Z0-9])('+'|'.join(re.escape(t.upper()) for t in team_names)+r')(?![A-Z0-9])')
    def _safe_color(tn):
        c=TEAM_VISUALS.get(tn,{}).get('primary','#fbbf24')
        try:
            r,g,b=int(c[1:3],16),int(c[3:5],16),int(c[5:7],16)
            if 0.299*r+0.587*g+0.114*b<60: c=f'#{min(255,r+80):02x}{min(255,g+80):02x}{min(255,b+80):02x}'
        except: pass
        return c
    cmap={t.upper():_safe_color(t) for t in team_names}
    def repl(m):
        tu=m.group(1); col=cmap.get(tu,'#fbbf24')
        return f"<span style='color:{col};font-weight:900;'>{tu}</span>"
    return pattern.sub(repl,escaped)

def _badge_color(badge):
    if badge=='FINAL SCORE': return('#dc2626','white')
    if 'CFP' in badge: return('#059669','white')
    if 'HEISMAN' in badge: return('#f59e0b','#451a03')
    if 'NATTY' in badge or 'CHAMPION' in badge: return('#f59e0b','#451a03')
    if 'UPSET' in badge: return('#dc2626','white')
    if 'FPI' in badge: return('#3b82f6','white')
    if 'RATED' in badge: return('#7c3aed','white')
    return('#3b82f6','white')

@st.cache_data(ttl=300)
def build_ticker_items(year, week, is_bowl_week):
    """Build simplified ticker headlines: scores, top 4 CFP, FPI leader, Heisman winner, Natty champ."""
    headlines=[]
    CY=year; CW=week

    # ── 0. NATIONAL CHAMPION ─────────────────────────────────────────────────
    try:
        champ_df=pd.read_csv('champs.csv') if os.path.exists('champs.csv') else pd.DataFrame()
        if not champ_df.empty:
            champ_df['YEAR']=pd.to_numeric(champ_df.get('YEAR',champ_df.get('year',0)),errors='coerce')
            champ_df=champ_df.dropna(subset=['YEAR'])
            champ_df['YEAR']=champ_df['YEAR'].astype(int)
            champ_df=champ_df[champ_df['Team'].notna()&(champ_df['Team'].astype(str).str.strip()!='')]
            if not champ_df.empty:
                nc=champ_df.sort_values('YEAR',ascending=False).iloc[0]
                nc_year=int(nc['YEAR']); nc_team=str(nc.get('Team','')).strip()
                nc_user=str(nc.get('user','')).strip()
                if nc_team and nc_team.lower()!='nan' and nc_year==CY:
                    ut=f"({nc_user})" if nc_user and nc_user.lower() not in ('nan','') else ''
                    headlines.append({'badge':'🏆 NATIONAL CHAMPIONS','priority':999,
                        'text':f"🏆 {nc_year} NATIONAL CHAMPIONS -- {nc_team.upper()}",
                        'blurb':f"{nc_team} {ut} crowned National Champions after the {nc_year} CFP."})
    except: pass

    # ── 1. GAME RESULTS (current week) ──────────────────────────────────────
    try:
        _sched=load_scores_master(CY)
        if not _sched.empty:
            _wc=next((c for c in ('Week','WEEK') if c in _sched.columns),None)
            if _wc: _sched[_wc]=pd.to_numeric(_sched[_wc],errors='coerce')
            _sc=next((c for c in ('Vis Score','Vis_Score') if c in _sched.columns),None)
            _hc=next((c for c in ('Home Score','Home_Score') if c in _sched.columns),None)
            _sts=next((c for c in ('Status','STATUS') if c in _sched.columns),None)
            if _wc and _sc and _hc and _sts:
                _final=_sched[(_sched[_wc]==CW)&(_sched[_sts].astype(str).str.upper()=='FINAL')].copy()
                _final[_sc]=pd.to_numeric(_final[_sc],errors='coerce')
                _final[_hc]=pd.to_numeric(_final[_hc],errors='coerce')
                for _,gr in _final.iterrows():
                    vis=str(gr.get('Visitor','')).strip(); hom=str(gr.get('Home','')).strip()
                    vs=float(gr.get(_sc,0) or 0); hs=float(gr.get(_hc,0) or 0)
                    if vs==0 and hs==0: continue
                    vu=str(gr.get('Vis_User',gr.get('VIS_USER',''))).strip()
                    hu=str(gr.get('Home_User',gr.get('HOME_USER',''))).strip()
                    is_user_game=(vis in ALL_USER_TEAMS or hom in ALL_USER_TEAMS)
                    w=vis if vs>hs else hom; l=hom if vs>hs else vis
                    ws=int(vs) if vs>hs else int(hs); ls=int(hs) if vs>hs else int(vs)
                    diff=ws-ls
                    if diff>=28: blurb=f"{w} put it on {l}. Dominant from start to finish."
                    elif diff<=3: blurb=f"Last-second thriller. {w} edges {l} in a game that came down to the wire."
                    elif diff<=7: blurb=f"{w} survives a tough one against {l}."
                    else: blurb=f"{w} handles {l} {ws}-{ls}."
                    txt_html=(_team_color_span(w,ws)+
                        "<span style='color:#64748b;'> - </span>"+
                        _team_color_span(l,ls))
                    headlines.append({'badge':'FINAL SCORE','priority':200 if is_user_game else 100,
                        'text':f"{w} {ws} - {ls} {l}",'text_html':txt_html,'blurb':blurb})
    except: pass

    # ── 2. CFP TOP 4 ────────────────────────────────────────────────────────
    try:
        _cfp=pd.read_csv('cfp_rankings_history.csv')
        _cfp['YEAR']=pd.to_numeric(_cfp['YEAR'],errors='coerce')
        _cfp['WEEK']=pd.to_numeric(_cfp['WEEK'],errors='coerce')
        _cfp['RANK']=pd.to_numeric(_cfp['RANK'],errors='coerce')
        _cy=_cfp[_cfp['YEAR']==CY]
        if not _cy.empty:
            _lw=int(_cy['WEEK'].max())
            _snap=_cy[_cy['WEEK']==_lw][_cfp['RANK']<=4].sort_values('RANK')
            if not _snap.empty and not is_bowl_week:
                top4_str=' · '.join(f"#{int(r['RANK'])} {str(r['TEAM']).strip()}" for _,r in _snap.iterrows())
                no1=str(_snap.iloc[0]['TEAM']).strip()
                # Build logo strip for hero display
                _top4_logo_html=''
                try:
                    _logo_chips=[]
                    for _,_tr4 in _snap.iterrows():
                        _rk4=int(_tr4['RANK']); _tm4=str(_tr4['TEAM']).strip()
                        _lsrc4=image_file_to_data_uri(get_logo_source(_tm4))
                        _limg4=f"<img src='{_lsrc4}' style='width:36px;height:36px;object-fit:contain;'/>" if _lsrc4 else _tm4
                        _tc4=get_team_primary_color(_tm4)
                        _rk_c4='#fbbf24' if _rk4==1 else '#94a3b8'
                        _logo_chips.append(
                            f"<div style='display:inline-flex;flex-direction:column;align-items:center;gap:2px;margin:0 6px;'>"
                            f"<span style='font-family:Bebas Neue,sans-serif;font-size:.75rem;color:{_rk_c4};'>#{_rk4}</span>"
                            f"{_limg4}"
                            f"<span style='font-size:.52rem;color:{_tc4};font-weight:700;max-width:48px;text-align:center;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'>{html.escape(_tm4[:12])}</span>"
                            f"</div>")
                    _top4_logo_html=("<div style='display:inline-flex;align-items:flex-end;justify-content:center;"
                        "gap:4px;background:rgba(0,0,0,.25);border-radius:10px;padding:6px 10px;"
                        "margin-top:6px;margin-bottom:2px;'>"+''.join(_logo_chips)+"</div>")
                except: pass
                headlines.append({'badge':'CFP TOP 4','priority':85,
                    'text':f"Wk {_lw} CFP: {top4_str}",
                    'logo_html':_top4_logo_html,
                    'blurb':f"{no1} holds the #1 spot. The committee has spoken."})
    except: pass

    # ── 3. FPI LEADER / BIGGEST MOVER ────────────────────────────────────────
    try:
        _fpi_file=f'FPI/fpi_ratings_{CY}_wk{CW}.csv'
        if not os.path.exists(_fpi_file): _fpi_file=f'fpi_ratings_{CY}_wk{CW}.csv'
        if os.path.exists(_fpi_file):
            _fdf=pd.read_csv(_fpi_file)
            if not _fdf.empty and 'FPI' in _fdf.columns and 'Team' in _fdf.columns:
                _fdf['FPI']=pd.to_numeric(_fdf['FPI'],errors='coerce')
                _leader=_fdf.nlargest(1,'FPI').iloc[0]
                _lt=str(_leader['Team']); _lf=float(_leader['FPI'])
                headlines.append({'badge':'FPI LEADER','priority':70,
                    'text':f"FPI Leader: {_lt} ({_lf:+.1f})",
                    'blurb':f"{_lt} tops the power index at {_lf:+.1f}. The model says this is the best team in the dynasty."})
    except: pass

    # ── 4. HIGHEST RATED GAME ────────────────────────────────────────────────
    try:
        _gs=load_game_summaries(CY)
        if not _gs.empty:
            _gs['VIS_RANK']=pd.to_numeric(_gs.get('Visitor Rank',_gs.get('VIS_RANK',None)),errors='coerce')
            _gs['HOME_RANK']=pd.to_numeric(_gs.get('Home Rank',_gs.get('HOME_RANK',None)),errors='coerce')
            _gs['_game_rating']=_gs.apply(lambda r:
                (min(26-float(r['VIS_RANK']),25) if pd.notna(r['VIS_RANK']) and float(r['VIS_RANK'])>0 else 0)+
                (min(26-float(r['HOME_RANK']),25) if pd.notna(r['HOME_RANK']) and float(r['HOME_RANK'])>0 else 0),axis=1)
            _top_game=_gs[_gs['_game_rating']>0].nlargest(1,'_game_rating')
            if not _top_game.empty:
                _tg=_top_game.iloc[0]
                _tv=str(_tg.get('Visitor','')); _th=str(_tg.get('Home',''))
                _tvr=_tg.get('VIS_RANK',None); _thr=_tg.get('HOME_RANK',None)
                _tvs=int(float(_tg.get('VisitorScore',0) or 0))
                _ths=int(float(_tg.get('HomeScore',0) or 0))
                _vr=f"#{int(_tvr)} " if pd.notna(_tvr) and float(_tvr)>0 else ""
                _hr=f"#{int(_thr)} " if pd.notna(_thr) and float(_thr)>0 else ""
                headlines.append({'badge':'RATED GAME','priority':60,
                    'text':f"Top Matchup: {_vr}{_tv} vs {_hr}{_th} -- {_tvs}-{_ths}",
                    'blurb':f"The highest-rated matchup of the season. Both programs had something to prove."})
    except: pass

    # ── 5. HEISMAN WINNER ────────────────────────────────────────────────────
    try:
        _hwin=pd.read_csv('Heisman_History.csv') if os.path.exists('Heisman_History.csv') else pd.DataFrame()
        if not _hwin.empty:
            _hwin['Year']=pd.to_numeric(_hwin.get('Year',_hwin.get('YEAR',0)),errors='coerce')
            _hy=_hwin[_hwin['Year']==CY]
            if not _hy.empty:
                _hr=_hy.iloc[0]
                _hp=str(_hr.get('Player',_hr.get('Winner',_hr.get('NAME','?')))).strip()
                _ht=str(_hr.get('Team',_hr.get('School','?'))).strip()
                headlines.append({'badge':'🏆 HEISMAN','priority':150,
                    'text':f"Heisman Winner: {_hp}, {_ht}",
                    'blurb':f"{_hp} from {_ht} wins the {CY} Heisman Trophy. Best player in college football."})
    except: pass

    headlines.sort(key=lambda h: h['priority'],reverse=True)
    if not headlines:
        headlines=[{'badge':'LIVE','priority':1,'text':'ISPN Dynasty Gameday -- live coverage all season','blurb':'Your dynasty. Your data. All season long.'}]
    return headlines

def render_ticker(headlines):
    _char_count=sum(len(h['badge'])+len(h['text'])+4 for h in headlines)
    _dur=max(15,int(_char_count*0.20))
    items_html=''
    for h in headlines:
        _bg,_fg=_badge_color(h['badge'])
        _content=h.get('text_html') or _colorize_headline(h['text'])
        items_html+=(f"<div class='slide'>"
            f"<span class='badge' style='background:{_bg};color:{_fg};'>{h['badge']}</span>"
            f"<span class='hl'>{_content}</span></div>")
    st.markdown(f"""
<style>
.sticky-news-ticker{{position:fixed;top:3.75rem;z-index:9999;background:#0d1b2e;
    border-top:2px solid #dc2626;border-bottom:1px solid #1e293b;padding:9px 0;overflow:hidden;width:100%;}}
.sticky-news-ticker::before,.sticky-news-ticker::after{{content:'';position:absolute;top:0;bottom:0;
    width:80px;z-index:2;pointer-events:none;}}
.sticky-news-ticker::before{{left:0;background:linear-gradient(to right,#0d1b2e 40%,transparent);}}
.sticky-news-ticker::after{{right:0;background:linear-gradient(to left,#0d1b2e 40%,transparent);}}
.sticky-news-ticker .ticker-track{{display:inline-flex;white-space:nowrap;
    animation:scroll-left {_dur}s linear infinite;}}
@keyframes scroll-left{{0%{{transform:translateX(0);}}100%{{transform:translateX(-50%);}}}}
.sticky-news-ticker .slide{{display:inline-flex;align-items:center;padding:0 36px;
    font-size:15px;font-weight:600;color:#cbd5e1;white-space:nowrap;letter-spacing:.01em;}}
.sticky-news-ticker .slide+.slide::before{{content:'●';color:#f59e0b;font-size:6px;
    margin-right:36px;opacity:.6;vertical-align:middle;}}
.sticky-news-ticker .badge{{display:inline-block;padding:3px 9px;border-radius:4px;
    font-size:10px;font-weight:900;letter-spacing:.1em;margin-right:10px;vertical-align:middle;
    line-height:1.8;text-transform:uppercase;flex-shrink:0;}}
.sticky-news-ticker .hl{{font-weight:700;color:#f8fafc;font-size:15px;letter-spacing:.03em;text-transform:uppercase;}}
</style>
<div class="sticky-news-ticker">
  <div class="ticker-track">{items_html}{items_html}</div>
</div>""", unsafe_allow_html=True)

# ── FPI/MS+/GAME CONTROL TABLE RENDERER ──────────────────────────────────────
def _power_table(df_in, tab_key, primary_col="#fbbf24", caption_txt="", has_msp=False, gc_mode=False):
    if df_in is None or df_in.empty:
        st.caption("No data yet -- push schedule data with results to enable."); return
    c1,c2,c3=st.columns([3,1,1])
    with c1:
        if caption_txt: st.caption(caption_txt)
    if gc_mode:
        sort_opts=["AVG Control","Best Game","Worst Game","Games"]
        with c2: _sb=st.selectbox("Sort",sort_opts,key=f"sb_{tab_key}")
        with c3: _uo=st.checkbox("User only",key=f"uo_{tab_key}")
        _d=df_in.copy()
        if _uo: _d=_d[_d['TEAM'].isin(ALL_USER_TEAMS)]
        sc_map={"AVG Control":"AVG_GAME_CONTROL","Best Game":"BEST_GAME_CONTROL",
                "Worst Game":"WORST_GAME_CONTROL","Games":"GAMES"}
        sc=sc_map.get(_sb,"AVG_GAME_CONTROL")
        if sc in _d.columns: _d=_d.sort_values(sc,ascending=False).reset_index(drop=True)
        _d.insert(0,"RANK",range(1,len(_d)+1))
        thead=(
            "<tr style='background:#0a1220;'>"
            "<th style='padding:5px 6px;color:#1e293b;width:24px;text-align:center;font-size:.58rem;'>#</th>"
            "<th style='padding:5px 6px;color:#475569;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:left;'>Team</th>"
            "<th style='padding:5px 6px;color:#fbbf24;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:center;'>Avg</th>"
            "<th style='padding:5px 6px;color:#4ade80;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:center;'>Best</th>"
            "<th style='padding:5px 6px;color:#f87171;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:center;'>Worst</th>"
            "<th style='padding:5px 6px;color:#475569;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:center;'>Gms</th>"
            "<th style='padding:5px 6px;color:#94a3b8;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:center;'>USER</th>"
            "</tr>"
        )
        rows_html=""
        for _,r in _d.iterrows():
            tm=str(r.get('TEAM','')); is_u=tm in ALL_USER_TEAMS
            uc=get_team_primary_color(tm) if is_u else "#0f172a"
            lg=get_school_logo_src(tm)
            lh=f"<img src='{lg}' style='width:18px;height:18px;object-fit:contain;vertical-align:middle;'/>" if lg else ""
            ab=_abbrev(tm)
            nw="font-weight:900;color:#f8fafc;" if is_u else "font-weight:400;color:#64748b;"
            bg=f"background:linear-gradient(90deg,{uc}22 0%,#06090f 30%);" if is_u else "background:#06090f;"
            bl=f"border-left:3px solid {uc};" if is_u else "border-left:2px solid #0f172a;"
            avg=float(r.get('AVG_GAME_CONTROL',50)); best=float(r.get('BEST_GAME_CONTROL',50))
            worst=float(r.get('WORST_GAME_CONTROL',50)); gms=int(r.get('GAMES',0))
            avc="#4ade80" if avg>=65 else ("#fbbf24" if avg>=50 else "#f87171")
            usr=str(r.get('USER',''))
            rows_html+=(
                f"<tr style='{bg}{bl}'>"
                f"<td style='padding:4px 5px;color:#1e293b;font-size:.65rem;text-align:center;'>{int(r.get('RANK',0))}</td>"
                f"<td style='padding:4px 5px;white-space:nowrap;'>{lh}"
                f"<span style='{nw}font-size:.8rem;font-family:Barlow Condensed,sans-serif;'>{html.escape(ab)}</span></td>"
                f"<td style='padding:4px 5px;text-align:center;font-family:Bebas Neue,sans-serif;color:{avc};font-size:.92rem;'>{avg:.1f}</td>"
                f"<td style='padding:4px 5px;text-align:center;color:#4ade80;font-size:.78rem;'>{best:.1f}</td>"
                f"<td style='padding:4px 5px;text-align:center;color:#f87171;font-size:.78rem;'>{worst:.1f}</td>"
                f"<td style='padding:4px 5px;text-align:center;color:#475569;font-size:.7rem;'>{gms}</td>"
                f"<td style='padding:4px 5px;text-align:center;color:#64748b;font-size:.68rem;'>{html.escape(usr)}</td>"
                f"</tr>"
            )
        st.markdown(
            f"<div class='isp-power-table-wrap'><table class='isp-power-table'>"
            f"<thead>{thead}</thead><tbody>{rows_html}</tbody></table></div>",
            unsafe_allow_html=True)
        return
    # FPI / MS+ mode
    _sort_cols=["FPI","MS+","SOS","SOR","Chaos","W-L"] if has_msp else ["FPI","SOS","SOR","Chaos","W-L"]
    with c2: _sb=st.selectbox("Sort",_sort_cols,key=f"sb_{tab_key}")
    with c3: _uo=st.checkbox("User only",key=f"uo_{tab_key}")
    _d=df_in.copy()
    if _uo: _d=_d[_d['Team'].isin(ALL_USER_TEAMS)]
    _scol_map={"FPI":"FPI","SOS":"SOS","SOR":"SOR","Chaos":"Chaos","W-L":"W","MS+":"MSPlus"}
    _sc=_scol_map.get(_sb,"FPI")
    if _sc in _d.columns: _d=_d.sort_values(_sc,ascending=False).reset_index(drop=True)
    if "Rank" in _d.columns: _d=_d.drop(columns=["Rank"])
    _d.insert(0,"Rank",range(1,len(_d)+1))
    # CFP rank map
    _cfp_rank_map={}
    try:
        _ch=pd.read_csv('cfp_rankings_history.csv')
        _ch['YEAR']=pd.to_numeric(_ch['YEAR'],errors='coerce')
        _ch['WEEK']=pd.to_numeric(_ch['WEEK'],errors='coerce')
        _ch['RANK']=pd.to_numeric(_ch['RANK'],errors='coerce')
        _cy2=_ch[_ch['YEAR']==CURRENT_YEAR]
        if not _cy2.empty:
            _lw=int(_cy2['WEEK'].max())
            _snap=_cy2[_cy2['WEEK']==_lw]
            _cfp_rank_map=dict(zip(_snap['TEAM'].astype(str).str.strip(),_snap['RANK'].astype(int)))
    except: pass
    def _rows_html(subset):
        rh=""
        for _,_r in subset.iterrows():
            _tm=str(_r["Team"]); _is_u=_tm in ALL_USER_TEAMS
            _uc=get_team_primary_color(_tm) if _is_u else "#0f172a"
            _lg=get_school_logo_src(_tm)
            _lh=(f"<img src='{_lg}' style='width:20px;height:20px;object-fit:contain;vertical-align:middle;'/>" if _lg else "")
            _ab=_abbrev(_tm)
            _nw="font-weight:900;color:#f8fafc;" if _is_u else "font-weight:400;color:#64748b;"
            _bg=f"background:linear-gradient(90deg,{_uc}25 0%,#06090f 30%);" if _is_u else "background:#06090f;"
            _bl=f"border-left:3px solid {_uc};" if _is_u else "border-left:2px solid #0f172a;"
            _w=int(_r.get("W",0)); _l=int(_r.get("L",0))
            _wlc="#4ade80" if _w>_l else ("#f87171" if _l>_w else "#64748b")
            _fv=float(_r.get("FPI",0)); _fc="#4ade80" if _fv>=5 else ("#fbbf24" if _fv>=0 else "#f87171")
            _sv=float(_r.get("SOS",0))
            _orv=float(_r.get("SOR",0)); _orc="#4ade80" if _orv>=0.05 else ("#fbbf24" if _orv>=-0.05 else "#f87171")
            _chv=float(_r.get("Chaos",0)); _chc="#f97316" if _chv>=20 else ("#fbbf24" if _chv>=0 else "#f87171")
            _stk=str(_r.get("Streak","")); _stkc="#4ade80" if "W" in _stk else ("#f87171" if "L" in _stk else "#334155")
            try: _qw=int(float(_r.get("QualityWins",0)))
            except: _qw=0
            _bw=str(_r.get("BestWin",""))
            _bw="" if _bw.strip() in ('nan','NaN','None','') else _bw
            _rk=int(_r.get("Rank",0))
            _cfp_rk=_cfp_rank_map.get(_tm)
            _cfp_cell=(f"<td style='padding:4px 5px;text-align:center;color:#fbbf24;font-family:Bebas Neue,sans-serif;font-size:.85rem;'>#{_cfp_rk}</td>"
                if _cfp_rk and _cfp_rk<=25 else "<td style='padding:4px 5px;text-align:center;color:#1e293b;font-size:.7rem;'>--</td>")
            _msc=""
            if has_msp and "MSPlus" in _r.index:
                _mv=float(_r.get("MSPlus",0)); _mc="#4ade80" if _mv>=70 else ("#fbbf24" if _mv>=55 else "#f87171")
                _msc=f"<td style='padding:4px 5px;text-align:center;font-family:Bebas Neue,sans-serif;color:{_mc};font-size:.9rem;font-weight:700;'>{_mv:.1f}</td>"
            rh+=(f"<tr style='{_bg}{_bl}'>"
                f"<td style='padding:4px 5px;color:#1e293b;font-size:.65rem;text-align:center;width:24px;'>{_rk}</td>"
                f"<td style='padding:4px 5px;white-space:nowrap;'>{_lh}"
                f"<span style='{_nw}font-size:.8rem;font-family:Barlow Condensed,sans-serif;'>{html.escape(_ab)}</span></td>"
                +(_msc if has_msp else "")
                +f"<td style='padding:4px 5px;text-align:center;color:{_wlc};font-weight:700;font-size:.75rem;'>{_w}-{_l}</td>"
                f"<td style='padding:4px 5px;text-align:center;font-family:Bebas Neue,sans-serif;font-size:.92rem;color:{_fc};'>{_fv:+.1f}</td>"
                f"<td style='padding:4px 5px;text-align:center;color:#334155;font-size:.7rem;'>{_sv:+.1f}</td>"
                f"<td style='padding:4px 5px;text-align:center;color:{_orc};font-size:.7rem;'>{_orv:+.3f}</td>"
                f"<td style='padding:4px 5px;text-align:center;font-family:Bebas Neue,sans-serif;color:{_chc};font-size:.85rem;'>{_chv:+.0f}</td>"
                +_cfp_cell
                +f"<td style='padding:4px 5px;text-align:center;color:{_stkc};font-size:.7rem;'>{_stk}</td>"
                f"<td style='padding:4px 5px;text-align:center;color:#3b82f6;font-size:.68rem;'>"
                f"{(str(_qw) if _qw else chr(8212))+(' '+_bw if _bw else '')}</td>"
                f"</tr>")
        return rh
    _msp_th="<th style='padding:5px 6px;color:#a78bfa;font-size:.6rem;letter-spacing:.1em;text-transform:uppercase;'>MS+</th>" if has_msp else ""
    _thead=(f"<tr style='background:#0a1220;'>"
        f"<th style='padding:5px 6px;color:#1e293b;font-size:.58rem;text-align:center;width:24px;'>#</th>"
        f"<th style='padding:5px 6px;color:#475569;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:left;'>Team</th>"
        +(_msp_th if has_msp else "")
        +f"<th style='padding:5px 6px;color:#475569;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:center;'>W-L</th>"
        f"<th style='padding:5px 6px;color:{primary_col};font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:center;'>FPI</th>"
        f"<th style='padding:5px 6px;color:#475569;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:center;'>SOS</th>"
        f"<th style='padding:5px 6px;color:#475569;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:center;'>SOR</th>"
        f"<th style='padding:5px 6px;color:#f97316;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:center;'>Chaos</th>"
        f"<th style='padding:5px 6px;color:#fbbf24;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:center;'>CFP</th>"
        f"<th style='padding:5px 6px;color:#475569;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:center;'>STK</th>"
        f"<th style='padding:5px 6px;color:#475569;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:center;'>Q-Wins</th>"
        f"</tr>")
    top50=_d.head(50); rest=_d.iloc[50:]
    st.markdown(f"<div class='isp-power-table-wrap'><table class='isp-power-table'>"
        f"<thead>{_thead}</thead><tbody>{_rows_html(top50)}</tbody></table></div>",
        unsafe_allow_html=True)
    if not rest.empty:
        with st.expander(f"Show remaining {len(rest)} teams"):
            st.markdown(f"<div class='isp-power-table-wrap'><table class='isp-power-table'>"
                f"<thead>{_thead}</thead><tbody>{_rows_html(rest)}</tbody></table></div>",
                unsafe_allow_html=True)

def normalize_history_team_name(team):
    t = str(team).strip()
    lower = t.lower()
    aliases = {
        'south florida': 'USF',
        'usf': 'USF',
        'texas a&m': 'Texas A&M',
        'san jose st': 'San Jose State',
        'bowling green state': 'Bowling Green',
    }
    return aliases.get(lower, t)



def get_program_history_cards(user, ratings_df, champs_df, rec_df):
    user_clean = str(user).strip().title()
    team_years = {}

    # Recruiting is the source of truth for coaching stops and year spans.
    if rec_df is not None and not rec_df.empty and 'USER' in rec_df.columns and 'Teams' in rec_df.columns:
        rec_user = rec_df[rec_df['USER'].astype(str).str.strip().str.title() == user_clean].copy()
        year_cols = [c for c in rec_user.columns if str(c).isdigit()]
        for _, r in rec_user.iterrows():
            team = normalize_history_team_name(r.get('Teams', ''))
            if not team or str(team).lower() == 'nan':
                continue
            active_years = [int(col) for col in year_cols if recruiting_value_means_coached(r.get(col))]
            if active_years:
                team_years.setdefault(team, set()).update(active_years)

    # Fallback to ratings only if recruiting has nothing for this user.
    if not team_years and ratings_df is not None and not ratings_df.empty and 'USER' in ratings_df.columns and 'TEAM' in ratings_df.columns and 'YEAR' in ratings_df.columns:
        history = ratings_df[ratings_df['USER'].astype(str).str.strip().str.title() == user_clean].copy()
        history['YEAR'] = pd.to_numeric(history['YEAR'], errors='coerce')
        for _, r in history.dropna(subset=['YEAR']).iterrows():
            team = normalize_history_team_name(r.get('TEAM', ''))
            if team and str(team).lower() != 'nan':
                team_years.setdefault(team, set()).add(int(r['YEAR']))

    if not team_years:
        return []

    champs_local = champs_df.copy()
    # ── SAFE LOOKUP: Find 'user', 'User', or 'USER' dynamically ──
    user_col = next((c for c in champs_local.columns if str(c).strip().lower() == 'user'), None)
    if user_col:
        champs_local['user'] = champs_local[user_col].astype(str).str.strip().str.title()
    else:
        champs_local['user'] = "" 

    champs_local['Team'] = champs_local['Team'].astype(str).str.strip().map(normalize_history_team_name)
    # ── SAFE LOOKUP: Find 'YEAR' dynamically to avoid hidden character crashes ──
    year_col = next((c for c in champs_local.columns if str(c).replace('\ufeff', '').strip().upper() == 'YEAR'), None)
    if year_col:
        champs_local['YEAR'] = pd.to_numeric(champs_local[year_col], errors='coerce')
    else:
        champs_local['YEAR'] = 0  # Fallback so the math doesn't crash


    cards = []
    for team, years_set in sorted(team_years.items(), key=lambda kv: min(kv[1]) if kv[1] else 9999):
        years = sorted(int(y) for y in years_set if pd.notna(y))
        title_count = int(champs_local[
            (champs_local['user'] == user_clean) &
            (champs_local['Team'] == team) &
            (champs_local['YEAR'].isin(years))
        ].shape[0])

        if years:
            ranges = []
            start = prev = years[0]
            for y in years[1:]:
                if y == prev + 1:
                    prev = y
                else:
                    ranges.append(f"{start}-{prev}" if start != prev else str(start))
                    start = prev = y
            ranges.append(f"{start}-{prev}" if start != prev else str(start))
            years_display = ', '.join(ranges)
        else:
            years_display = '--'

        cards.append({
            'team': team,
            'logo': get_logo_source(team),
            'years': years_display,
            'titles': title_count,
            'first_year': years[0] if years else 9999,
        })

    cards = sorted(cards, key=lambda x: (x.get('first_year', 9999), x['team']))
    for c in cards:
        c.pop('first_year', None)
    return cards


def render_history_cards(cards):
    if not cards:
        st.caption("No prior school history found.")
        return
    cols = st.columns(min(4, len(cards)))
    for i, card in enumerate(cards):
        with cols[i % len(cols)]:
            render_logo(card['logo'], width=44)
            st.caption(card['team'])
            st.caption(card['years'])
            trophies = "🏆" * max(1, int(card['titles'])) if int(card['titles']) > 0 else "--"
            st.caption(f"Titles: {trophies}")

def _mini_stat_chip(label, value, color='#94a3b8'):
    """Compact stat chip for season-in-numbers bars."""
    return (f"<div style='background:#0a1628;border:1px solid #1e293b;border-radius:8px;"
            f"padding:8px 10px;text-align:center;'>"
            f"<div style='font-weight:900;font-size:1.0rem;color:{color};'>{html.escape(str(value))}</div>"
            f"<div style='font-size:0.6rem;color:#475569;letter-spacing:.05em;margin-top:2px;'>{html.escape(label)}</div>"
            f"</div>")



def get_record_parts(record_str):
    try:
        wins, losses = str(record_str).split('-')
        return int(wins), int(losses)
    except Exception:
        return 0, 0



def build_ispn_classics(scores_df, ratings_df):
    """
    Returns a DataFrame of the most iconic games in dynasty history.
    Blends closeness (low margin) + stakes (game type) + upset factor (OVR delta).
    Each row includes all context needed to render a broadcast-style card.
    """
    if scores_df is None or scores_df.empty:
        return pd.DataFrame()

    # Build team OVR lookup: (team, year) -> OVR
    _ovr = {}
    if ratings_df is not None and not ratings_df.empty:
        for _, _r in ratings_df.iterrows():
            try:
                _ovr[(str(_r['TEAM']).strip(), int(_r['YEAR']))] = float(_r.get('OVERALL', 75))
            except Exception:
                pass

    def _get_ovr(team, year):
        t = str(team).strip()
        v = _ovr.get((t, year))
        if v is None:
            v = _ovr.get((t, year - 1))
        return float(v) if v is not None else 75.0

    rows = []
    for _, g in scores_df.iterrows():
        try:
            yr   = int(g.get('YEAR', 0))
            vis  = str(g.get('Visitor_Final', g.get('Visitor', ''))).strip()
            hom  = str(g.get('Home_Final',    g.get('Home', ''))).strip()
            vpts = int(g.get('V_Pts', g.get('Vis Score', 0)))
            hpts = int(g.get('H_Pts', g.get('Home Score', 0)))
            vu   = str(g.get('V_User_Final', g.get('Vis_User', ''))).strip()
            hu   = str(g.get('H_User_Final', g.get('Home_User', ''))).strip()
            margin = abs(vpts - hpts)
            vis_won = vpts > hpts
            winner      = vis if vis_won else hom
            loser       = hom if vis_won else vis
            winner_user = vu  if vis_won else hu
            loser_user  = hu  if vis_won else vu
            winner_pts  = vpts if vis_won else hpts
            loser_pts   = hpts if vis_won else vpts

            # Game type
            def _flag_yes(v):
                _s = str(v).strip().lower()
                return _s in {'yes', 'true', '1', 'y'}

            _nat = g.get('Natty Game', 'NO')
            _cfp = g.get('CFP', 'No')
            _cft = g.get('Conf Title', 'No')
            _bwl = g.get('Bowl', 'No')

            if _flag_yes(_nat):
                gtype = 'National Championship'
                gtype_weight = 20
            elif _flag_yes(_cfp):
                gtype = 'CFP Playoff'
                gtype_weight = 12
            elif _flag_yes(_cft):
                gtype = 'Conf Title'
                gtype_weight = 8
            elif _flag_yes(_bwl):
                gtype = 'Bowl Game'
                gtype_weight = 4
            else:
                gtype = 'Regular Season'
                gtype_weight = 0

            # OVR delta -- positive means underdog won
            w_ovr = _get_ovr(winner, yr)
            l_ovr = _get_ovr(loser, yr)
            ovr_diff = round(l_ovr - w_ovr, 1)   # positive = underdog won
            is_upset = ovr_diff >= 3.0

            # Classic score: closeness is the main driver, stakes + upset are bonuses
            closeness = max(0, 35 - margin)       # max 35 for OT thriller
            classic_score = closeness + gtype_weight + max(0, ovr_diff * 0.6)
            classic_score = round(classic_score, 1)

            rows.append({
                'Year': yr, 'Visitor': vis, 'VisPts': vpts,
                'HomePts': hpts, 'Home': hom,
                'VisUser': vu, 'HomeUser': hu,
                'Margin': margin, 'Winner': winner, 'Loser': loser,
                'WinnerUser': winner_user, 'LoserUser': loser_user,
                'WinnerPts': winner_pts, 'LoserPts': loser_pts,
                'WinnerOVR': w_ovr, 'LoserOVR': l_ovr,
                'OVR_Diff': ovr_diff, 'IsUpset': is_upset,
                'GameType': gtype, 'ClassicScore': classic_score,
            })
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).sort_values('ClassicScore', ascending=False).reset_index(drop=True)
    return df


# ══════════════════════════════════════════════════════════════════════
# LOAD MAIN DATA
# ══════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300)
def load_data(current_year=None):
    if current_year is None: current_year=CURRENT_YEAR
    try:
        scores=load_scores_master(multi_year=True)
        champs=pd.read_csv('champs.csv')
        draft=pd.read_csv('UserDraftPicks.csv')
        try: heisman=pd.read_csv('Heisman_History.csv')
        except: heisman=pd.DataFrame()
        try: coty=pd.read_csv('COTY.csv')
        except: coty=pd.DataFrame()
        scores.columns=[str(c).strip() for c in scores.columns]
        champs['user']=safe_title_series(champs['user'])
        champs['Team']=champs['Team'].astype(str).str.strip()
        draft['USER']=safe_title_series(draft['USER'])
        v_user_key=smart_col(scores,['Vis_User','Visitor User'])
        h_user_key=smart_col(scores,['Home_User','Home User'])
        v_score_key=smart_col(scores,['Vis Score','Vis_Score'])
        h_score_key=smart_col(scores,['Home Score','Home_Score'])
        yr_key=smart_col(scores,['YEAR','Year'])
        scores['V_User_Final']=safe_title_series(scores[v_user_key])
        scores['H_User_Final']=safe_title_series(scores[h_user_key])
        scores['Visitor_Final']=scores[smart_col(scores,['Visitor'])].astype(str).str.strip()
        scores['Home_Final']=scores[smart_col(scores,['Home'])].astype(str).str.strip()
        scores['V_Pts']=pd.to_numeric(scores[v_score_key],errors='coerce')
        scores['H_Pts']=pd.to_numeric(scores[h_score_key],errors='coerce')
        scores=scores.dropna(subset=['V_Pts','H_Pts']).copy()
        scores['Margin']=(scores['H_Pts']-scores['V_Pts']).abs()
        scores['Total Points']=scores['H_Pts']+scores['V_Pts']
        scores['Winner_User']=np.where(scores['H_Pts']>scores['V_Pts'],scores['H_User_Final'],scores['V_User_Final'])
        scores['Winner_Team']=np.where(scores['H_Pts']>scores['V_Pts'],scores['Home_Final'],scores['Visitor_Final'])
        scores['Loser_Team']=np.where(scores['H_Pts']>scores['V_Pts'],scores['Visitor_Final'],scores['Home_Final'])
        all_users=sorted([u for u in pd.concat([scores['V_User_Final'],scores['H_User_Final']]).dropna().unique()
            if str(u).upper()!='CPU' and str(u).lower()!='nan'])
        natty_counts=champs[champs['user'].str.upper()!='CPU']['user'].value_counts().to_dict()
        stats_list=[]; h2h_rows=[]; h2h_numeric=[]; rivalry_rows=[]
        for user in all_users:
            h_games=scores[scores['H_User_Final']==user]
            v_games=scores[scores['V_User_Final']==user]
            all_u_games=pd.concat([h_games,v_games],ignore_index=True)
            wins=len(h_games[h_games['H_Pts']>h_games['V_Pts']])+len(v_games[v_games['V_Pts']>v_games['H_Pts']])
            losses=len(all_u_games)-wins
            u_draft=draft[draft['USER']==user]
            n_sent=int(u_draft['Guys Sent to NFL'].iloc[0]) if not u_draft.empty and 'Guys Sent to NFL' in u_draft.columns else 0
            n_1st=int(u_draft['1st Rounders'].iloc[0]) if not u_draft.empty and '1st Rounders' in u_draft.columns else 0
            conf_t=int(u_draft['Conference Titles'].iloc[0]) if not u_draft.empty and 'Conference Titles' in u_draft.columns else 0
            cfp_w=int(u_draft['CFP Wins'].iloc[0]) if not u_draft.empty and 'CFP Wins' in u_draft.columns else 0
            cfp_l=int(u_draft['CFP Losses'].iloc[0]) if not u_draft.empty and 'CFP Losses' in u_draft.columns else 0
            natty_a=int(u_draft['National Title Appearances'].iloc[0]) if not u_draft.empty and 'National Title Appearances' in u_draft.columns else 0
            career_wins=int(u_draft['Career Wins'].iloc[0]) if not u_draft.empty and 'Career Wins' in u_draft.columns else wins
            career_losses=int(u_draft['Career Losses'].iloc[0]) if not u_draft.empty and 'Career Losses' in u_draft.columns else losses
            goat_score=(natty_counts.get(user,0)*200+natty_a*80+cfp_w*40+conf_t*25+n_1st*12+n_sent*4)
            stats_list.append({'User':user,'GOAT Score':int(goat_score),'Record':f"{wins}-{losses}",
                'Career Record':f"{career_wins}-{career_losses}",
                'Career Win %':round((career_wins/max(1,career_wins+career_losses))*100,1),
                'Natties':natty_counts.get(user,0),'Drafted':n_sent,'1st Rounders':n_1st,
                'Conf Titles':conf_t,'CFP Wins':cfp_w,'CFP Losses':cfp_l,'Natty Apps':natty_a})
            h2h_row={'User':user}; h2h_num_row=[]
            for opp in all_users:
                if user==opp: h2h_row[opp]="-"; h2h_num_row.append(0)
                else:
                    vs=scores[((scores['V_User_Final']==user)&(scores['H_User_Final']==opp))|
                              ((scores['V_User_Final']==opp)&(scores['H_User_Final']==user))]
                    vw=len(vs[((vs['V_User_Final']==user)&(vs['V_Pts']>vs['H_Pts']))|
                               ((vs['H_User_Final']==user)&(vs['H_Pts']>vs['V_Pts']))])
                    vl=len(vs)-vw; h2h_row[opp]=f"{vw}-{vl}"; h2h_num_row.append(vw-vl)
                    if user<opp and len(vs)>0:
                        balance=1-(abs(vw-vl)/max(1,len(vs)))
                        rivalry_rows.append({'Matchup':f"{user} vs {opp}",'Games':int(len(vs)),
                            user:vw,opp:vl,'Balance':round(balance,2),
                            'Avg Margin':round(vs['Margin'].mean(),1),
                            'Rivalry Score':round((len(vs)*2.5)+(balance*10),1)})
            h2h_rows.append(h2h_row); h2h_numeric.append(h2h_num_row)
        stats_df=pd.DataFrame(stats_list)
        h2h_df=pd.DataFrame(h2h_rows)
        h2h_heat=pd.DataFrame(h2h_numeric,index=all_users,columns=all_users)
        rivalry_df=pd.DataFrame(rivalry_rows).sort_values(['Rivalry Score','Games'],ascending=[False,False]) if rivalry_rows else pd.DataFrame()
        # Build model_2041-equivalent
        r_current=build_ratings_from_sources(current_year)
        if r_current.empty:
            try:
                _legacy=pd.read_csv('TeamRatingsHistory.csv')
                _legacy['YEAR']=pd.to_numeric(_legacy['YEAR'],errors='coerce')
                r_current=_legacy[_legacy['YEAR'].fillna(-1).astype(int)==current_year].copy()
            except: r_current=pd.DataFrame()
        return (scores,stats_df,h2h_df,h2h_heat,rivalry_df,r_current,champs,draft,heisman,coty,all_users)
    except Exception as e:
        st.error(f"Data load error: {e}")
        return (pd.DataFrame(),pd.DataFrame(),pd.DataFrame(),pd.DataFrame(),pd.DataFrame(),pd.DataFrame(),pd.DataFrame(),pd.DataFrame(),pd.DataFrame(),pd.DataFrame(),[])

# ── GAME STATUS + CARD SECTION ────────────────────────────────────────────────
def render_status_banner(year, week, is_bowl):
    _is_offseason=week>=25
    if _is_offseason: wk_label='OFFSEASON'
    elif is_bowl or week>=16:
        _bowl_names={16:'Bowl Season',17:'CFP First Round',18:'CFP Quarterfinals',
                     19:'CFP Semifinals',20:'CFP Championship',21:'CFP Championship'}
        wk_label=_bowl_names.get(week,'Bowl Season')
    else: wk_label=f"Week {week}"
    _ncaa=image_file_to_data_uri(get_logo_source('NCAA') or '') or ''
    _ncaa_img=f"<img src='{_ncaa}' style='height:36px;object-fit:contain;vertical-align:middle;margin-right:8px;'/>" if _ncaa else ""
    st.markdown(f"""
<div style='display:flex;align-items:center;justify-content:center;gap:18px;
    background:linear-gradient(90deg,rgba(59,130,246,.08),rgba(251,191,36,.05));
    border:1px solid rgba(255,255,255,.07);border-radius:10px;padding:14px 20px;margin-bottom:18px;
    flex-wrap:wrap;'>
    <div style='text-align:center;display:flex;align-items:center;'>
        {_ncaa_img}
        <div>
            <div style='font-family:Bebas Neue,sans-serif;font-size:2.8rem;color:#fbbf24;line-height:1;'>{year}</div>
            <div style='font-size:.6rem;color:#475569;text-transform:uppercase;letter-spacing:.12em;'>Season</div>
        </div>
    </div>
    <div style='width:1px;height:40px;background:rgba(255,255,255,.1);'></div>
    <div style='text-align:center;'>
        <div style='font-family:Bebas Neue,sans-serif;font-size:2.8rem;color:#60a5fa;line-height:1;'>{wk_label}</div>
        <div style='font-size:.6rem;color:#475569;text-transform:uppercase;letter-spacing:.12em;'>Current Week</div>
    </div>
    <div style='width:1px;height:40px;background:rgba(255,255,255,.1);'></div>
    <div style='text-align:center;'>
        <div style='font-family:Bebas Neue,sans-serif;font-size:2.8rem;color:#4ade80;line-height:1;'>{year+1}</div>
        <div style='font-size:.6rem;color:#475569;text-transform:uppercase;letter-spacing:.12em;'>Draft Class</div>
    </div>
</div>""", unsafe_allow_html=True)

def render_game_cards_with_boxscore(year, week, model_df):
    """Status grid + full detail cards matching original style."""
    import hashlib as _hlib

    # ── Load FPI table ────────────────────────────────────────────────
    _cf=f'FPI/fpi_ratings_{year}_wk{week}.csv'
    if not os.path.exists(_cf): _cf=f'fpi_ratings_{year}_wk{week}.csv'
    _card_fpi_df=pd.DataFrame()
    try:
        if os.path.exists(_cf):
            _card_fpi_df=pd.read_csv(_cf)
            _card_fpi_df['FPI']=pd.to_numeric(_card_fpi_df['FPI'],errors='coerce').fillna(0)
            _card_fpi_df=_card_fpi_df.sort_values('FPI',ascending=False).reset_index(drop=True)
            _card_fpi_df['_fpi_rank']=range(1,len(_card_fpi_df)+1)
    except: pass
    def _fpi_for(team):
        if _card_fpi_df.empty: return 0.0,0
        r=_card_fpi_df[_card_fpi_df['Team']==team]
        return (float(r.iloc[0]['FPI']),int(r.iloc[0]['_fpi_rank'])) if not r.empty else (0.0,0)

    # ── Speed Freaks rank ─────────────────────────────────────────────
    _sf_df=build_speed_freaks_live(year)
    def _sf_rank_for(team):
        if _sf_df.empty: return 0
        r=_sf_df[_sf_df['TEAM']==team]
        return int(r.iloc[0]['RANK']) if not r.empty else 0

    # ── CFP rankings ──────────────────────────────────────────────────
    official_rank_map={}
    try:
        _cfp=pd.read_csv('cfp_rankings_history.csv')
        _cfp['YEAR']=pd.to_numeric(_cfp['YEAR'],errors='coerce')
        _cfp['WEEK']=pd.to_numeric(_cfp['WEEK'],errors='coerce')
        _cfp_cy=_cfp[_cfp['YEAR']==year]
        if not _cfp_cy.empty:
            _lw=int(_cfp_cy['WEEK'].max())
            _snap=_cfp_cy[_cfp_cy['WEEK']==_lw]
            _snap=_snap[_snap['RANK'].fillna(0).astype(float)>0]
            official_rank_map=dict(zip(_snap['TEAM'].str.strip(),_snap['RANK'].astype(int)))
    except: pass

    # ── Bracket / eliminated ──────────────────────────────────────────
    official_cfp_teams=[]; eliminated_teams=[]
    try:
        if os.path.exists('CFPbracketresults.csv'):
            _b=pd.read_csv('CFPbracketresults.csv')
            _cy=_b[_b['YEAR']==year].copy()
            if not _cy.empty:
                def _cbt(raw):
                    s=str(raw).strip(); s=re.sub(r'^#\d+\s+','',s)
                    return None if re.match(r'(?i)^(winner|loser|tbd|bye)',s) else s.strip().lower() if s else None
                official_cfp_teams=[c for t in _cy['TEAM1'].dropna().tolist()+_cy['TEAM2'].dropna().tolist() for c in [_cbt(t)] if c]
                if 'LOSER' in _cy.columns:
                    eliminated_teams=[c for t in _cy['LOSER'].dropna().tolist() for c in [_cbt(t)] if c]
    except: pass

    # ── Schedule matchup lookup ────────────────────────────────────────
    _user_matchup={}
    _week_has_games=False
    try:
        _sf=f'schedule_{year}.csv'
        if os.path.exists(_sf):
            _raw=pd.read_csv(_sf,dtype={'YEAR':str,'Week':str})
            _raw.columns=[str(c).strip() for c in _raw.columns]
            _yc=next((c for c in ('YEAR','Year') if c in _raw.columns),None)
            _wc=next((c for c in ('Week','WEEK') if c in _raw.columns),None)
            _ym=str(int(year)); _wm=str(int(week))
            _yr_ok=_raw[_yc].astype(str).str.strip().str.split('.').str[0]==_ym if _yc else pd.Series([True]*len(_raw))
            _wk_ok=_raw[_wc].astype(str).str.strip().str.split('.').str[0]==_wm if _wc else pd.Series([True]*len(_raw))
            _sc=_raw[_yr_ok&_wk_ok].copy()
            _week_has_games=not _sc.empty
            for tc in ('Visitor','Home'):
                if tc in _sc.columns: _sc[tc]=_sc[tc].astype(str).apply(lambda t:re.sub(r'^\d+\s+','',t.strip()))
            _vc=next((c for c in ('Visitor','VISITOR') if c in _sc.columns),None)
            _hc=next((c for c in ('Home','HOME') if c in _sc.columns),None)
            _vsc=next((c for c in ('Vis Score','Vis_Score') if c in _sc.columns),None)
            _hsc=next((c for c in ('Home Score','Home_Score') if c in _sc.columns),None)
            if _vc: _sc['_VL']=_sc[_vc].astype(str).str.strip().str.lower()
            if _hc: _sc['_HL']=_sc[_hc].astype(str).str.strip().str.lower()
            for user,team in USER_TEAMS.items():
                tl=team.lower()
                _vr=_sc[_sc['_VL']==tl] if '_VL' in _sc.columns else pd.DataFrame()
                _hr=_sc[_sc['_HL']==tl] if '_HL' in _sc.columns else pd.DataFrame()
                if not _vr.empty:
                    gr=_vr.iloc[0]; opp=str(gr.get(_hc,'')).strip() if _hc else '?'
                    vp=pd.to_numeric(gr.get(_vsc),errors='coerce') if _vsc else float('nan')
                    hp=pd.to_numeric(gr.get(_hsc),errors='coerce') if _hsc else float('nan')
                    if pd.notna(vp) and pd.notna(hp) and float(vp)+float(hp)>0:
                        _user_matchup[user]={'opp':opp,'score':f"{int(vp)}-{int(hp)}",'result':'W' if float(vp)>float(hp) else 'L','home':False}
                    else: _user_matchup[user]={'opp':opp,'score':None,'result':None,'home':False}
                elif not _hr.empty:
                    gr=_hr.iloc[0]; opp=str(gr.get(_vc,'')).strip() if _vc else '?'
                    vp=pd.to_numeric(gr.get(_vsc),errors='coerce') if _vsc else float('nan')
                    hp=pd.to_numeric(gr.get(_hsc),errors='coerce') if _hsc else float('nan')
                    if pd.notna(vp) and pd.notna(hp) and float(vp)+float(hp)>0:
                        _user_matchup[user]={'opp':opp,'score':f"{int(hp)}-{int(vp)}",'result':'W' if float(hp)>float(vp) else 'L','home':True}
                    else: _user_matchup[user]={'opp':opp,'score':None,'result':None,'home':True}
                else: _user_matchup[user]='BYE' if _week_has_games else 'UNSCHEDULED'
    except: pass

    # ── Game status map ────────────────────────────────────────────────
    _game_status_map={}
    try:
        if os.path.exists('week_game_status.csv'):
            _wgs=pd.read_csv('week_game_status.csv')
            _wgs['Year']=pd.to_numeric(_wgs.get('Year'),errors='coerce').fillna(0).astype(int)
            _wgs['Week']=pd.to_numeric(_wgs.get('Week'),errors='coerce').fillna(0).astype(int)
            _wgs_cur=_wgs[(_wgs['Year']==int(year))&(_wgs['Week']==int(week))].copy()
            if not _wgs_cur.empty:
                _game_status_map=dict(zip(_wgs_cur['User'].astype(str).str.strip(),_wgs_cur['Status'].astype(str).str.strip()))
    except: pass

    # ── Manual scores built once (keyed by user) ─────────────────────
    _manual_score_map={}
    try:
        _msc_path='week_manual_scores.csv'
        if os.path.exists(_msc_path):
            _msc=pd.read_csv(_msc_path)
            _msc.columns=[str(c).strip() for c in _msc.columns]
            _yr_c=next((c for c in _msc.columns if c.lower() in ('year','season_year')),None)
            _wk_c=next((c for c in _msc.columns if c.lower()=='week'),None)
            _us_c=next((c for c in _msc.columns if c.lower()=='user'),None)
            _uss_c=next((c for c in _msc.columns if c.lower() in ('userscore','user_score')),None)
            _ops_c=next((c for c in _msc.columns if c.lower() in ('oppscore','opp_score')),None)
            if _yr_c: _msc[_yr_c]=pd.to_numeric(_msc[_yr_c],errors='coerce').fillna(0).astype(int)
            if _wk_c: _msc[_wk_c]=pd.to_numeric(_msc[_wk_c],errors='coerce').fillna(0).astype(int)
            _fil=_msc
            if _yr_c: _fil=_fil[_fil[_yr_c]==int(year)]
            if _wk_c: _fil=_fil[_fil[_wk_c]==int(week)]
            for _,_mr in _fil.iterrows():
                _uraw=str(_mr[_us_c]).strip() if _us_c else ''
                _ukey=_uraw.title()
                # accept both title-case and original
                for _uk in (_ukey,_uraw):
                    if _uk in USER_TEAMS:
                        _manual_score_map[_uk]={
                            'user_score':_safe_int(_mr[_uss_c] if _uss_c else 0),
                            'opp_score': _safe_int(_mr[_ops_c] if _ops_c else 0),
                        }
                        break
    except: pass

    # ── Record from CFP rankings ───────────────────────────────────────
    _record_map={}
    try:
        _ch=pd.read_csv('cfp_rankings_history.csv')
        _ch['YEAR']=pd.to_numeric(_ch['YEAR'],errors='coerce')
        _ch['WEEK']=pd.to_numeric(_ch['WEEK'],errors='coerce')
        _cy2=_ch[_ch['YEAR']==year]
        if not _cy2.empty:
            _lw2=int(_cy2['WEEK'].max())
            _snap2=_cy2[_cy2['WEEK']==_lw2]
            if 'RECORD' in _snap2.columns:
                _record_map=dict(zip(_snap2['TEAM'].astype(str).str.strip(),_snap2['RECORD'].astype(str)))
    except: pass

    # ── Previous week box scores ───────────────────────────────────────
    prev_week=week-1 if week>1 else None
    prev_gs=pd.DataFrame()
    if prev_week and prev_week>0:
        try:
            _pgs=load_game_summaries(year)
            if not _pgs.empty and 'WEEK' in _pgs.columns:
                _pgs['WEEK']=pd.to_numeric(_pgs['WEEK'],errors='coerce')
                prev_gs=_pgs[_pgs['WEEK']==prev_week].copy()
        except: pass

    # ── Sort users by FPI ──────────────────────────────────────────────
    _sorted_users=sorted(USER_TEAMS.keys(),key=lambda u:_fpi_for(USER_TEAMS.get(u,''))[0],reverse=True)

    # ═══════════════════════════════════════════════════════════════════
    # SECTION A — STATUS GRID
    # ═══════════════════════════════════════════════════════════════════
    st.subheader("🏈 Game Status")
    _grid_parts=[]
    for user in _sorted_users:
        team=USER_TEAMS.get(user,'')
        tc=get_team_primary_color(team)
        try:
            r,g,b=int(tc[1:3],16),int(tc[3:5],16),int(tc[5:7],16)
            if 0.299*r+0.587*g+0.114*b<55:
                tc=f'#{min(255,r+80):02x}{min(255,g+80):02x}{min(255,b+80):02x}'
        except: pass
        gl_uri=image_file_to_data_uri(get_logo_source(team))
        matchup=_user_matchup.get(user,'UNSCHEDULED')
        has_score=(isinstance(matchup,dict) and matchup.get('score'))
        _man_g=_manual_score_map.get(user,{}); _has_manual=(_man_g.get('user_score',0)>0 or _man_g.get('opp_score',0)>0)
        is_ready=_game_status_map.get(user,'')=='Ready' or has_score or _has_manual
        tc_lower=team.lower()
        is_cfp_alive=tc_lower in official_cfp_teams and tc_lower not in eliminated_teams and len(official_cfp_teams)>0
        is_elim=tc_lower in eliminated_teams
        if is_cfp_alive:
            sq_bg='linear-gradient(135deg,#0f0b00 0%,#050505 55%,#0a0800 100%)'
            sq_bdr='#fbbf24'; glow='box-shadow:0 0 16px rgba(251,191,36,.5);'
            lbl_col='#fbbf24'; lf='drop-shadow(0 0 5px rgba(251,191,36,.7))' if is_ready else 'grayscale(100%) opacity(.45)'
            dot=f"<span style='width:7px;height:7px;border-radius:50%;background:#fbbf24;box-shadow:0 0 6px #fbbf24;display:inline-block;margin-bottom:2px;'></span>"
        elif is_ready:
            sq_bg=f'linear-gradient(135deg,{tc}28 0%,#0a0d14 100%)'; sq_bdr=tc
            glow=f'box-shadow:0 0 14px {tc}88;'; lbl_col=tc; lf=f'drop-shadow(0 0 4px {tc}88)'
            dot="<span style='width:7px;height:7px;border-radius:50%;background:#4ade80;box-shadow:0 0 6px #4ade80;display:inline-block;margin-bottom:2px;'></span>"
        elif is_elim:
            sq_bg='linear-gradient(135deg,#0d1117 0%,#080d14 100%)'; sq_bdr='#374151'
            glow='box-shadow:0 2px 6px rgba(0,0,0,.5);'; lbl_col='#4b5563'; lf='grayscale(100%) opacity(.35)'
            dot="<span style='width:7px;height:7px;border-radius:50%;background:#4b5563;display:inline-block;margin-bottom:2px;'></span>"
        else:
            sq_bg='linear-gradient(135deg,#0f172a 0%,#080d14 100%)'; sq_bdr='#1e293b'
            glow='box-shadow:0 2px 6px rgba(0,0,0,.4);'; lbl_col='#475569'; lf='opacity(.6)'
            dot="<span style='width:7px;height:7px;border-radius:50%;background:#334155;display:inline-block;margin-bottom:2px;'></span>"
        gl_img=(f"<img src='{gl_uri}' style='width:44px;height:44px;object-fit:contain;filter:{lf};'/>" if gl_uri else "🏈")
        _grid_parts.append(
            f"<div style='display:flex;flex-direction:column;align-items:center;justify-content:center;"
            f"gap:3px;width:100%;aspect-ratio:1/1;background:{sq_bg};border-radius:14px;"
            f"border:2px solid {sq_bdr};{glow}padding:6px;box-sizing:border-box;'>"
            f"{dot}{gl_img}"
            f"<span style='font-size:.68rem;font-weight:800;color:{lbl_col};"
            f"font-family:Barlow Condensed,sans-serif;letter-spacing:.06em;text-transform:uppercase;"
            f"width:100%;text-align:center;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'>"
            f"{html.escape(user)}</span></div>"
        )
    if _grid_parts:
        st.markdown(
            "<div style='margin-bottom:16px;'>"
            "<div style='display:grid;grid-template-columns:repeat(3,1fr);gap:10px;"
            "padding:12px;max-width:500px;margin:0 auto;"
            "background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.06);border-radius:16px;'>"
            +"".join(_grid_parts)
            +"</div></div>",
            unsafe_allow_html=True
        )

    # ═══════════════════════════════════════════════════════════════════
    # SECTION B — DETAIL CARDS (one per user)
    # ═══════════════════════════════════════════════════════════════════
    def _pct_to_odds(pct):
        try:
            p=float(pct)
            if p<=0 or p!=p: return '--'
            if p>=50: return 'Even'
            return f'{max(1,int(round((100.0/p)-1.0)))}:1'
        except: return '--'

    for user in _sorted_users:
        team=USER_TEAMS.get(user,'')
        tc=get_team_primary_color(team)
        logo_uri=image_file_to_data_uri(get_logo_source(team))
        fpi_val,fpi_rk=_fpi_for(team)
        sf_rk=_sf_rank_for(team)
        cfp_rank=official_rank_map.get(team)
        rec_str=_record_map.get(team,'')
        matchup=_user_matchup.get(user,'UNSCHEDULED')
        game_status=_game_status_map.get(user,'Not Set')
        tc_lower=team.lower()
        is_cfp_alive=tc_lower in official_cfp_teams and tc_lower not in eliminated_teams and len(official_cfp_teams)>0
        is_elim=tc_lower in eliminated_teams

        # CFP rank circle
        if cfp_rank:
            rk_int=int(cfp_rank)
            rk_c='#fbbf24' if rk_int<=4 else '#60a5fa'
            rank_circle=(f"<div style='min-width:40px;height:40px;width:40px;border-radius:50%;"
                f"border:2px solid {rk_c};display:flex;align-items:center;justify-content:center;"
                f"background:{rk_c}18;flex-shrink:0;'>"
                f"<span style='font-family:Bebas Neue,sans-serif;font-size:{'1rem' if rk_int<10 else '.85rem'};"
                f"color:{rk_c};line-height:1;'>#{rk_int}</span></div>")
        else:
            rank_circle=(f"<div style='min-width:40px;height:40px;width:40px;border-radius:50%;"
                f"border:2px solid #334155;display:flex;align-items:center;justify-content:center;"
                f"background:#33415518;flex-shrink:0;'>"
                f"<span style='font-family:Bebas Neue,sans-serif;font-size:.5rem;color:#475569;'>UR</span></div>")

        # Record chip
        if rec_str and str(rec_str).lower() not in ('nan',''):
            try:
                rw=int(str(rec_str).split('-')[0]); rl=int(str(rec_str).split('-')[1])
                rc='#4ade80' if rw>rl else ('#f87171' if rl>rw else '#94a3b8')
            except: rc='#94a3b8'
            rec_chip=(f"<span style='font-size:.72rem;font-weight:800;padding:2px 7px;"
                f"border-radius:3px;background:{rc}22;color:{rc};border:1px solid {rc}55;"
                f"font-family:Barlow Condensed,sans-serif;letter-spacing:.04em;'>{html.escape(str(rec_str))}</span>")
        else: rec_chip=""

        # Manual score from pre-built map
        _man=_manual_score_map.get(user,{})
        _mu2=_man.get('user_score',0); _mo2=_man.get('opp_score',0)
        _man_score_str=None; _man_result_str=None
        if _mu2>0 or _mo2>0:
            _man_result_str='W' if _mu2>_mo2 else ('L' if _mo2>_mu2 else 'TIE')
            _man_score_str=f'{_mu2}-{_mo2}'
        # Game strip
        _chip_style="font-weight:700;padding:3px 10px;border-radius:4px;font-family:Barlow Condensed,sans-serif;font-size:.92rem;letter-spacing:.07em;"
        if matchup=='BYE':
            game_strip=f"<span style='color:#475569;font-size:.9rem;'>BYE WEEK</span>"
        elif matchup=='UNSCHEDULED' or matchup is None:
            if _man_score_str:
                _rc_us='#4ade80' if _man_result_str=='W' else ('#f87171' if _man_result_str=='L' else '#94a3b8')
                _sc_chip2=f"<span style='background:#60a5fa22;color:#60a5fa;border:1px solid #60a5fa55;{_chip_style}'>FINAL</span>"
                game_strip=(f"<span style='font-family:Bebas Neue,sans-serif;font-size:.9rem;color:#475569;letter-spacing:.08em;'>WK {week}</span> {_sc_chip2} "
                    f"<span style='color:{_rc_us};font-weight:900;font-size:1.05rem;font-family:Barlow Condensed,sans-serif;'>{_man_result_str} {_man_score_str}</span>")
            else:
                game_strip=f"<span style='color:#334155;font-size:.88rem;'>Schedule pending</span>"
        elif isinstance(matchup,dict):
            opp=matchup.get('opp','?'); score=matchup.get('score'); result=matchup.get('result')
            ha='vs' if matchup.get('home') else '@'
            opp_logo_uri=image_file_to_data_uri(get_logo_source(opp))
            opp_img=(f"<img src='{opp_logo_uri}' style='width:24px;height:24px;object-fit:contain;vertical-align:middle;'/>"
                     if opp_logo_uri else "")
            opp_cfp_rk=official_rank_map.get(opp)
            opp_rk_html=(f"<span style='font-size:.72rem;color:#fbbf24;font-weight:700;'>#{opp_cfp_rk} </span>"
                         if opp_cfp_rk and opp_cfp_rk<=25 else "")
            if score and result:
                rc2='#4ade80' if result=='W' else '#f87171'
                status_chip=f"<span style='background:#60a5fa22;color:#60a5fa;border:1px solid #60a5fa55;{_chip_style}'>FINAL</span>"
                game_strip=(f"<span style='font-family:Bebas Neue,sans-serif;font-size:.9rem;color:#475569;"
                    f"letter-spacing:.08em;'>WK {week}</span> {status_chip} "
                    f"<span style='font-size:.95rem;color:#94a3b8;'>{ha}</span> {opp_rk_html}{opp_img} "
                    f"<span style='color:{rc2};font-weight:900;font-size:1.05rem;"
                    f"font-family:Barlow Condensed,sans-serif;'>{result} {score}</span>")
            else:
                if _man_score_str:
                    _rc_ms='#4ade80' if _man_result_str=='W' else ('#f87171' if _man_result_str=='L' else '#94a3b8')
                    status_chip=f"<span style='background:#4ade8022;color:#4ade80;border:1px solid #4ade8055;{_chip_style}'>✓ READY</span>"
                    game_strip=(f"<span style='font-family:Bebas Neue,sans-serif;font-size:.9rem;color:#475569;letter-spacing:.08em;'>WK {week}</span> {status_chip} "
                        f"<span style='font-size:.88rem;color:#94a3b8;'>{ha}</span> {opp_rk_html}{opp_img} "
                        f"<span style='color:{_rc_ms};font-weight:900;font-size:1.05rem;font-family:Barlow Condensed,sans-serif;'>{_man_result_str} {_man_score_str}</span>")
                elif game_status=='Ready' or _man_score_str:
                    status_chip=f"<span style='background:#4ade8022;color:#4ade80;border:1px solid #4ade8055;{_chip_style}'>✓ READY</span>"
                else:
                    status_chip=f"<span style='background:#dc262622;color:#ef4444;border:1px solid #dc262655;{_chip_style}'>NOT SET</span>"
                # Game line from live FPI spread
                line_html=""
                try:
                    _fv_t,_=_fpi_for(team); _fv_o,_=_fpi_for(opp)
                    if _fv_t!=0 or _fv_o!=0:
                        _hf_adj=3.0 if matchup.get('home') else -3.0
                        _raw=(_fv_t-_fv_o)*0.65+_hf_adj  # FPI->pts: ~0.65x, capped at 35
                        _spread=max(-35.0,min(35.0,_raw))
                        if abs(_spread)>=1.5:
                            _fav=team if _spread>0 else opp
                            _sp_val=round(abs(_spread),1)
                            _gl_str=f"{_fav} -{int(_sp_val) if _sp_val==int(_sp_val) else _sp_val}"
                            _ufav=_fav==team
                            _lc='#4ade80' if _ufav else '#f87171'
                            line_html=(f" <span style='font-family:Barlow Condensed,sans-serif;font-size:.95rem;"
                                f"font-weight:900;color:#94a3b8;'>LINE: "
                                f"<strong style='color:{_lc};font-size:1rem;'>{html.escape(_gl_str)}</strong></span>")
                        else:
                            line_html=" <span style='font-size:.82rem;color:#94a3b8;'>LINE: <strong style='color:#fbbf24;'>Pick'em</strong></span>"
                except: pass
                # Append manual score alongside LINE if available
                if _man_score_str:
                    _rc_app='#4ade80' if _man_result_str=='W' else ('#f87171' if _man_result_str=='L' else '#94a3b8')
                    line_html+=(f" <span style='color:#334155;'>&nbsp;·&nbsp;</span>"
                        f"<span style='font-family:Barlow Condensed,sans-serif;font-size:.95rem;"
                        f"font-weight:900;color:#94a3b8;'>SCORE: "
                        f"<strong style='color:{_rc_app};font-size:1rem;'>{_man_result_str} {_man_score_str}</strong></span>")
                game_strip=(f"<span style='font-family:Bebas Neue,sans-serif;font-size:.9rem;color:#475569;"
                    f"letter-spacing:.08em;'>WK {week}</span> {status_chip} "
                    f"<span style='font-size:.88rem;color:#94a3b8;'>{ha}</span> {opp_rk_html}{opp_img} "
                    f"<span style='font-size:.88rem;color:#f8fafc;font-family:Barlow Condensed,sans-serif;"
                    f"font-weight:700;'>{html.escape(opp)}</span>{line_html}")
        else: game_strip=""

        # Right panel: FPI, odds, speed rank
        fpi_c='#4ade80' if fpi_val>0 else ('#f87171' if fpi_val<0 else '#94a3b8')
        # Natty odds — computed from live FPI if no pre-computed CSV available
        natty_pct=0.0; cfp_pct_v=0.0
        try:
            _msp_path=f'FPI/ms_plus_{year}_wk{week}.csv'
            if not os.path.exists(_msp_path): _msp_path=f'ms_plus_{year}_wk{week}.csv'
            if os.path.exists(_msp_path):
                _msp_ck=pd.read_csv(_msp_path)
                _msp_r=_msp_ck[_msp_ck['Team'].astype(str).str.strip()==team] if 'Team' in _msp_ck.columns else pd.DataFrame()
                if not _msp_r.empty:
                    _noc=next((c for c in ('Natty Odds','Preseason Natty Odds','NattyOdds') if c in _msp_r.columns),None)
                    _coc=next((c for c in ('CFP Odds','Preseason CFP %','CFPOdds') if c in _msp_r.columns),None)
                    if _noc: natty_pct=float(safe_num(_msp_r.iloc[0][_noc],0))
                    if _coc: cfp_pct_v=float(safe_num(_msp_r.iloc[0][_coc],0))
        except: pass
        # FPI-based formula if CSV not available
        if natty_pct==0.0:
            try:
                _fv2,_fr2=_fpi_for(team)
                if _fv2!=0.0 and not _card_fpi_df.empty:
                    # Logistic model: FPI rank 1→~30% natty, rank 6→~8%, rank 13→~2%, unranked→~0.3%
                    _n_teams=max(1,len(_card_fpi_df))
                    _pct_ile=(_n_teams-_fr2+1)/_n_teams  # 0-1
                    # Curve: top team gets ~30%, steeper drop-off
                    natty_pct=round(max(0.1, min(35.0, 30.0*(_pct_ile**2.8))), 1)
                    cfp_pct_v=round(max(0.5, min(99.0, 95.0*(_pct_ile**1.2))), 1)
            except: pass
        # FPI-based formula when no pre-computed odds
        if natty_pct==0.0:
            try:
                _fv2,_fr2=_fpi_for(team)
                if not _card_fpi_df.empty and _fr2>0:
                    _n_teams=max(1,len(_card_fpi_df))
                    _pct_ile=(_n_teams-_fr2+1)/_n_teams
                    natty_pct=round(max(0.1,min(35.0,30.0*(_pct_ile**2.8))),1)
                    cfp_pct_v=round(max(0.5,min(99.0,95.0*(_pct_ile**1.1))),1)
            except: pass
        natty_odds=(f"{natty_pct:.1f}%" if natty_pct>0 else "--")
        cfp_show=(f"{cfp_pct_v:.0f}%" if cfp_pct_v>0 else "--")
        sf_chip=(f"<span style='background:{tc}22;color:{tc};border:1px solid {tc}55;"
            f"border-radius:6px;padding:3px 10px;font-size:.78rem;font-weight:800;"
            f"font-family:Barlow Condensed,sans-serif;letter-spacing:.04em;'>"
            f"Speed Freaks: #{sf_rk}</span>" if sf_rk>0 else "")

        # Has final score in CSV?
        _has_csv_score = False
        try:
            if os.path.exists('week_manual_scores.csv'):
                _msc_ck=pd.read_csv('week_manual_scores.csv')
                for _c in ['Year','Week']: _msc_ck[_c]=pd.to_numeric(_msc_ck.get(_c),errors='coerce').fillna(0).astype(int)
                _msc_ck_row=_msc_ck[(_msc_ck['User'].astype(str).str.strip()==user)&(_msc_ck['Year']==year)&(_msc_ck['Week']==week)]
                if not _msc_ck_row.empty:
                    _us_ck=int(_msc_ck_row.iloc[0].get('UserScore',0)); _os_ck=int(_msc_ck_row.iloc[0].get('OppScore',0))
                    _has_csv_score=(_us_ck>0 or _os_ck>0)
        except: pass
        is_ready_or_final = (game_status=='Ready' or _has_csv_score or bool(_man_score_str) or (isinstance(matchup,dict) and matchup.get('score')))
        # Card border / background: muted until Ready or has score
        if is_cfp_alive and is_ready_or_final:
            card_bg="linear-gradient(135deg,#0f0b00 0%,#050505 55%,#0a0800 100%)"
            card_border="#fbbf24"
        elif is_cfp_alive:
            card_bg="linear-gradient(135deg,#06090f 0%,#080d14 100%)"
            card_border="#334155"
        elif is_elim:
            card_bg="linear-gradient(90deg,#0d1117 0%,#080d14 100%)"
            card_border="#374151"
        elif is_ready_or_final:
            card_bg=f"linear-gradient(90deg,{tc}22 0%,{tc}08 25%,#0d1117 65%)"
            card_border=tc
        else:
            card_bg="linear-gradient(135deg,#0c111a 0%,#080d14 100%)"
            card_border="#1e293b"  # fully muted until ready

        _lf='' if is_ready_or_final else 'filter:grayscale(85%) opacity(0.45);'
        logo_img=(f"<img src='{logo_uri}' style='width:64px;height:64px;object-fit:contain;{_lf}'/>"
                  if logo_uri else "🏈")

        card=(
            f"<div style='background:{card_bg};border:1px solid {card_border}55;"
            f"border-left:4px solid {card_border};border-radius:14px;"
            f"padding:14px 16px;margin-bottom:10px;'>"
            # Top row
            f"<div style='display:flex;align-items:center;gap:12px;'>"
            f"<div style='display:flex;align-items:center;gap:10px;flex:1;min-width:0;'>"
            f"{rank_circle}{logo_img}"
            f"<div style='flex:1;min-width:0;'>"
            f"<div style='font-weight:900;font-size:1.1rem;color:{tc};white-space:nowrap;"
            f"overflow:hidden;text-overflow:ellipsis;font-family:Barlow Condensed,sans-serif;"
            f"letter-spacing:.02em;'>{html.escape(team)}</div>"
            f"<div style='font-size:.7rem;color:#64748b;'>{html.escape(user)}</div>"
            f"<div style='margin-top:3px;'>{rec_chip}</div>"
            f"</div></div>"
            # Right stats panel
            f"<div style='text-align:right;flex-shrink:0;'>"
            f"<div style='font-size:.75rem;color:#94a3b8;'>FPI: "
            f"<strong style='color:{fpi_c};font-size:.9rem;'>{fpi_val:+.1f}</strong>"
            +(f" <span style='color:#fbbf24;font-size:.7rem;'>#{fpi_rk}</span>" if fpi_rk>0 else "")
            +f"</div>"
            f"<div style='font-size:.72rem;color:#64748b;margin-top:2px;'>Committee Live <span style='color:#475569;'>(136-team)</span></div>"
            f"<div style='font-size:.78rem;color:#94a3b8;margin-top:3px;'>"
            f"<span style='color:#fbbf24;'>🏆 {natty_odds} Natty</span>"
            +(f"  <span style='color:#60a5fa;font-weight:700;'>CFP {cfp_show}</span>" if cfp_pct_v>0 else "")
            +f"</div>"
            +(f"<div style='margin-top:5px;'>{sf_chip}</div>" if sf_chip else "")
            +f"</div></div>"
            # Game strip
            f"<div style='border-top:1px solid rgba(255,255,255,.07);padding-top:8px;margin-top:8px;"
            f"display:flex;align-items:center;gap:8px;flex-wrap:wrap;'>"
            f"{game_strip}</div>"
            f"</div>"
        )
        st.markdown(card, unsafe_allow_html=True)

        # Previous week box score + game control
        if not prev_gs.empty:
            try:
                _vc2=next((c for c in ('Visitor','VISITOR') if c in prev_gs.columns),None)
                _hc2=next((c for c in ('Home','HOME') if c in prev_gs.columns),None)
                _tl=team.lower()
                _pg_v=prev_gs[prev_gs[_vc2].astype(str).str.strip().str.lower()==_tl] if _vc2 else pd.DataFrame()
                _pg_h=prev_gs[prev_gs[_hc2].astype(str).str.strip().str.lower()==_tl] if _hc2 else pd.DataFrame()
                _pg=_pg_v.iloc[0] if not _pg_v.empty else (_pg_h.iloc[0] if not _pg_h.empty else None)
                if _pg is not None:
                    _is_home=(_pg_h.shape[0]>0 and _pg_v.shape[0]==0)
                    if _is_home:
                        _us=int(float(_pg.get('HomeScore',0) or 0)); _ops=int(float(_pg.get('VisitorScore',0) or 0))
                        _uq=[int(float(_pg.get(f'Q{q}_Home',0) or 0)) for q in range(1,5)]
                        _oq=[int(float(_pg.get(f'Q{q}_Visitor',0) or 0)) for q in range(1,5)]
                        _opp_n=str(_pg.get(_vc2,'Opp')).strip()
                        _uyd=int(float(_pg.get('TotalYds_Home',_pg.get('HOME_TOTAL_YDS',0)) or 0))
                        _oyd=int(float(_pg.get('TotalYds_Visitor',_pg.get('VIS_TOTAL_YDS',0)) or 0))
                        _uto=int(float(_pg.get('Turnovers_Home',0) or 0))
                        _oto=int(float(_pg.get('Turnovers_Visitor',0) or 0))
                    else:
                        _us=int(float(_pg.get('VisitorScore',0) or 0)); _ops=int(float(_pg.get('HomeScore',0) or 0))
                        _uq=[int(float(_pg.get(f'Q{q}_Visitor',0) or 0)) for q in range(1,5)]
                        _oq=[int(float(_pg.get(f'Q{q}_Home',0) or 0)) for q in range(1,5)]
                        _opp_n=str(_pg.get(_hc2,'Opp')).strip()
                        _uyd=int(float(_pg.get('TotalYds_Visitor',_pg.get('VIS_TOTAL_YDS',0)) or 0))
                        _oyd=int(float(_pg.get('TotalYds_Home',_pg.get('HOME_TOTAL_YDS',0)) or 0))
                        _uto=int(float(_pg.get('Turnovers_Visitor',0) or 0))
                        _oto=int(float(_pg.get('Turnovers_Home',0) or 0))
                    _rc2='#4ade80' if _us>_ops else '#f87171'
                    _gc=compute_game_control_score(_pg.to_dict(),_is_home)
                    _gc_c='#4ade80' if _gc>=65 else ('#fbbf24' if _gc>=50 else '#f87171')
                    _opp_ab=_abbrev(_opp_n)
                    _tm_ab=html.escape(team[:6].upper()); _op_ab=html.escape(_opp_ab)
                    _bx=(
                        f"<div style='background:#06090f;border:1px solid #1e293b;border-radius:10px;"
                        f"padding:10px 12px;margin-bottom:10px;font-size:.72rem;margin-left:4px;"
                        f"border-left:3px solid {tc};'>"
                        f"<div style='color:#475569;margin-bottom:6px;font-size:.6rem;letter-spacing:.05em;text-transform:uppercase;'>"
                        f"Wk {prev_week} Box Score — vs {_op_ab}</div>"
                        f"<div style='display:grid;grid-template-columns:44px 28px 28px 28px 28px 40px;gap:2px;align-items:center;margin-bottom:3px;font-family:Barlow Condensed,sans-serif;'>"
                        f"<span style='color:#94a3b8;font-weight:700;font-size:.68rem;'>{_tm_ab}</span>"
                        f"<span style='color:#64748b;text-align:center;'>{_uq[0]}</span><span style='color:#64748b;text-align:center;'>{_uq[1]}</span>"
                        f"<span style='color:#64748b;text-align:center;'>{_uq[2]}</span><span style='color:#64748b;text-align:center;'>{_uq[3]}</span>"
                        f"<span style='color:{_rc2};font-weight:900;text-align:right;font-size:.95rem;'>{_us}</span>"
                        f"</div>"
                        f"<div style='display:grid;grid-template-columns:44px 28px 28px 28px 28px 40px;gap:2px;align-items:center;margin-bottom:6px;font-family:Barlow Condensed,sans-serif;'>"
                        f"<span style='color:#475569;font-size:.68rem;'>{_op_ab}</span>"
                        f"<span style='color:#475569;text-align:center;'>{_oq[0]}</span><span style='color:#475569;text-align:center;'>{_oq[1]}</span>"
                        f"<span style='color:#475569;text-align:center;'>{_oq[2]}</span><span style='color:#475569;text-align:center;'>{_oq[3]}</span>"
                        f"<span style='color:#64748b;font-weight:700;text-align:right;font-size:.95rem;'>{_ops}</span>"
                        f"</div>"
                        f"<div style='font-size:.62rem;color:#475569;margin-bottom:5px;'>{_uyd} yds · {_uto} TO &nbsp;|&nbsp; {_op_ab}: {_oyd} yds · {_oto} TO</div>"
                        f"<div style='font-size:.6rem;color:#64748b;margin-bottom:2px;text-transform:uppercase;letter-spacing:.05em;'>Game Control</div>"
                        f"<div style='background:#1e293b;border-radius:4px;height:8px;overflow:hidden;'>"
                        f"<div style='width:{int(_gc)}%;height:100%;background:linear-gradient(90deg,{_gc_c}cc,{_gc_c}55);border-radius:4px;'></div>"
                        f"</div>"
                        f"<div style='font-size:.62rem;color:{_gc_c};font-weight:700;margin-top:2px;'>{_gc:.1f} / 100</div>"
                        f"</div>"
                    )
                    st.markdown(_bx, unsafe_allow_html=True)
            except: pass


# ── INJURY REPORT ─────────────────────────────────────────────────────────────
def render_injury_report():
    st.subheader("🚑 Injury Report")
    try:
        _inj=pd.read_csv('injury_bulletin.csv')
        _inj.columns=[str(c).strip() for c in _inj.columns]
        # Filter to current year
        if 'Year' in _inj.columns:
            _inj['Year']=pd.to_numeric(_inj['Year'],errors='coerce')
            _inj=_inj[_inj['Year'].fillna(-1).astype(int)==CURRENT_YEAR].copy()
        elif 'YEAR' in _inj.columns:
            _inj['YEAR']=pd.to_numeric(_inj['YEAR'],errors='coerce')
            _inj=_inj[_inj['YEAR'].fillna(-1).astype(int)==CURRENT_YEAR].copy()
        _inj_u=_inj[_inj['Team'].astype(str).str.strip().isin(ALL_USER_TEAMS)].copy()
        _inj_u['OVR']=pd.to_numeric(_inj_u['OVR'],errors='coerce').fillna(0)
        _inj_u['WeeksOut']=pd.to_numeric(_inj_u['WeeksOut'],errors='coerce').fillna(0)
        # Compute weeks remaining using Week suffered + WeeksOut - current week
        if 'Week' in _inj_u.columns:
            _inj_u['WeekSuffered']=pd.to_numeric(_inj_u['Week'],errors='coerce').fillna(CURRENT_WEEK_NUMBER)
            _inj_u['WeeksRemaining']=(_inj_u['WeekSuffered']+_inj_u['WeeksOut']-CURRENT_WEEK_NUMBER).clip(lower=0).astype(int)
        else:
            _inj_u['WeeksRemaining']=_inj_u['WeeksOut'].astype(int)
        # Only show active (not yet recovered)
        _inj_u=_inj_u[_inj_u['WeeksRemaining']>0].sort_values(['Team','WeeksRemaining'],ascending=[True,False])
        if _inj_u.empty:
            st.info("No active injuries in the current season."); return
        st.caption(f"{CURRENT_YEAR} season -- {len(_inj_u)} active injury report entries")
        for _,row in _inj_u.iterrows():
            team=str(row.get('Team','')).strip()
            player=str(row.get('Player','')).strip()
            pos=str(row.get('Pos','')).strip()
            ovr=int(row.get('OVR',0))
            inj=str(row.get('Injury','')).strip()
            wks_rem=int(row.get('WeeksRemaining',0))
            _season_end=(CURRENT_WEEK_NUMBER+wks_rem)>21
            is_start=str(row.get('IsStarter','')).strip()
            primary=get_team_primary_color(team)
            logo=get_school_logo_src(team)
            lg_src=logo
            ovr_c="#fbbf24" if ovr>=90 else ("#60a5fa" if ovr>=85 else ("#94a3b8" if ovr>=80 else "#475569"))
            wks_c="#f87171" if wks_rem>=6 else ("#f97316" if wks_rem>=3 else "#fbbf24")
            starter_chip='<span style="background:#fbbf2420;color:#fbbf24;border-radius:3px;padding:1px 5px;font-size:.58rem;margin-left:2px;">STARTER</span>' if is_start.upper()=='YES' else ''
            lg_html=f'<img src="{lg_src}" style="width:22px;height:22px;object-fit:contain;vertical-align:middle;margin-right:6px;"/>' if lg_src else ''
            _inj_badge='🚫 SEASON ENDING' if _season_end else f"{wks_rem} wk{'s' if wks_rem!=1 else ''} remaining"
            _inj_badge_c='#ef4444' if _season_end else wks_c
            _team_lbl=html.escape(team) if team else ''
            card_html=(
                f"<div style='background:linear-gradient(135deg,{primary}18 0%,#060a11 50%);border:1px solid {primary}40;"
                f"border-left:4px solid {primary};border-radius:12px;padding:12px 16px;margin-bottom:6px;'>"
                f"<div style='display:flex;align-items:center;gap:10px;'>"
                f"<div style='flex-shrink:0;'>{lg_html}</div>"
                f"<div style='flex:1;min-width:0;'>"
                f"<div style='display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:3px;'>"
                f"<span style='font-weight:900;color:#f1f5f9;font-family:Barlow Condensed,sans-serif;font-size:1.05rem;'>{html.escape(player)}</span>"
                f"<span style='background:{primary}33;color:{primary};border-radius:4px;padding:1px 7px;font-size:.65rem;font-weight:700;'>{html.escape(pos)}</span>"
                f"<span style='color:{ovr_c};font-family:Bebas Neue,sans-serif;font-size:1rem;font-weight:900;'>{ovr} OVR</span>"
                f"{starter_chip}</div>"
                f"<div style='display:flex;align-items:center;gap:10px;flex-wrap:wrap;'>"
                f"<span style='color:#64748b;font-size:.78rem;font-style:italic;'>{html.escape(inj)}</span>"
                f"<span style='background:{_inj_badge_c}22;color:{_inj_badge_c};border:1px solid {_inj_badge_c}55;"
                f"border-radius:5px;padding:2px 8px;font-size:.72rem;font-weight:800;font-family:Barlow Condensed,sans-serif;"
                f"letter-spacing:.04em;'>{_inj_badge}</span>"
                f"</div></div>"
                f"<div style='font-size:.6rem;color:{primary}99;margin-top:2px;text-align:right;font-weight:600;'>{_team_lbl}</div>"
                f"</div></div>"
            )
            st.markdown(card_html, unsafe_allow_html=True)
    except Exception as e:
        st.caption(f"Injury report unavailable: {e}")

# ── HIGHEST RATED GAMES ───────────────────────────────────────────────────────
def get_rank_at_week(team, week, year):
    """Get CFP rank of a team at a specific week/year using prebuilt lookup."""
    try:
        k=(str(team).strip().lower(),int(year),int(week))
        if k in _GLOBAL_WEEK_RANK_LOOKUP: return int(_GLOBAL_WEEK_RANK_LOOKUP[k])
        # Fallback: find nearest week
        for wk in range(int(week),-1,-1):
            k2=(str(team).strip().lower(),int(year),wk)
            if k2 in _GLOBAL_WEEK_RANK_LOOKUP: return int(_GLOBAL_WEEK_RANK_LOOKUP[k2])
    except: pass
    return 0

def render_highest_rated_games(year, week):
    """TV-viewership-formula rated games -- matches original app."""
    import hashlib
    st.subheader("📺 Highest TV Rated Games of the Season")
    st.caption("Viewership formula: matchup stakes + rankings + margin + game context. Peak = broadcast moment.")
    try:
        # Read schedule directly (bypass cache) so newly-pushed CSVs always show
        _sched_path=f'schedule_{year}.csv'
        _tv=pd.DataFrame()
        if os.path.exists(_sched_path):
            try: _tv=pd.read_csv(_sched_path,on_bad_lines='skip',encoding='utf-8')
            except:
                try: _tv=pd.read_csv(_sched_path,on_bad_lines='skip',encoding='latin-1')
                except: pass
        # Also try load_scores_master as fallback
        if _tv.empty: _tv=load_scores_master(year)
        if _tv.empty:
            st.info(f"No schedule data (schedule_{year}.csv not found or empty).")
            return
        _tv.columns=[str(c).strip() for c in _tv.columns]
        # Flexible column name normalisation
        _col_map={'Vis Score':['Vis Score','Vis_Score','V_Score','VisScore'],
                  'Home Score':['Home Score','Home_Score','H_Score','HomeScore'],
                  'Visitor Rank':['Visitor Rank','Vis Rank','VIS_RANK'],
                  'Home Rank':['Home Rank','HOME_RANK'],
                  'Status':['Status','STATUS'],
                  'Vis_User':['Vis_User','VIS_USER','Visitor User'],
                  'Home_User':['Home_User','HOME_USER','Home User']}
        for canon,alts in _col_map.items():
            if canon not in _tv.columns:
                for alt in alts:
                    if alt in _tv.columns: _tv=_tv.rename(columns={alt:canon}); break
        for c in ('YEAR','Week','Vis Score','Home Score','Visitor Rank','Home Rank'):
            if c in _tv.columns: _tv[c]=pd.to_numeric(_tv[c],errors='coerce')
        # Filter to current year if YEAR column present
        if 'YEAR' in _tv.columns:
            _tv=_tv[_tv['YEAR'].fillna(-1).astype(int)==year]
        # Filter to FINAL games; be flexible about Status values
        if 'Status' in _tv.columns:
            _tv_cy=_tv[_tv['Status'].astype(str).str.upper().str.strip()=='FINAL'].copy()
        else:
            _tv_cy=_tv.dropna(subset=['Vis Score','Home Score']).copy()
        _tv_cy=_tv_cy.dropna(subset=['Vis Score','Home Score'])
        if _tv_cy.empty:
            st.info(f"Schedule loaded ({len(_tv)} rows) but no FINAL games yet this season.")
            return
        _tv_cy['Vis_User']=_tv_cy.get('Vis_User',pd.Series(dtype=str)).astype(str).str.strip().str.title()
        _tv_cy['Home_User']=_tv_cy.get('Home_User',pd.Series(dtype=str)).astype(str).str.strip().str.title()

        def _tv_rating(row):
            vs=float(row['Vis Score']); hs=float(row['Home Score'])
            vr=float(row['Visitor Rank']) if pd.notna(row.get('Visitor Rank')) else 99
            hr=float(row['Home Rank'])    if pd.notna(row.get('Home Rank'))    else 99
            margin=abs(vs-hs); total=vs+hs
            vu=str(row.get('Vis_User','')).strip(); hu=str(row.get('Home_User','')).strip()
            is_h2h=(vu in USER_TEAMS and hu in USER_TEAMS)
            is_user=(vu in USER_TEAMS or hu in USER_TEAMS)
            wk=float(row.get('Week',0) or 0)
            is_playoff=wk>=16
            top_rank=min(vr,hr); both_ranked=(vr<=25 and hr<=25)
            base=2.0
            if top_rank<=5: base+=6.5
            elif top_rank<=10: base+=4.5
            elif top_rank<=15: base+=2.8
            elif top_rank<=25: base+=1.5
            if both_ranked: base+=2.5
            if margin<=3: base+=3.5
            elif margin<=7: base+=2.0
            elif margin<=14: base+=0.8
            if total>=100: base+=1.5
            elif total>=80: base+=0.8
            if is_playoff: base+=3.2
            if is_h2h: base+=2.5
            elif is_user: base+=1.2
            if wk>=12: base+=1.0
            elif wk>=8: base+=0.4
            winner_rank=vr if vs>hs else hr; loser_rank=hr if vs>hs else vr
            is_upset=(loser_rank<=10 and winner_rank>loser_rank+5)
            if is_upset: base+=2.0
            seed_str=f"{int(row.get('YEAR',year))}{int(wk)}{row.get('Visitor','')}{row.get('Home','')}"
            _hash=int(hashlib.md5(seed_str.encode()).hexdigest()[:6],16)
            noise=(_hash%100)/100.0*0.8-0.4
            viewers=round(max(0.5,base+noise),2)
            if is_playoff: badge="🏟️ PLAYOFF"
            elif is_h2h: badge="⚔️ H2H"
            elif is_upset: badge="🚨 UPSET"
            elif both_ranked: badge="🔥 RANKED"
            elif margin<=3: badge="💀 THRILLER"
            else: badge="📺 MARQUEE"
            if is_playoff: peak="4th quarter, final drive"
            elif margin<=3: peak="Final possession"
            elif margin<=7: peak="4th quarter comeback"
            elif total>=90: peak=f"Back-to-back scoring drives"
            elif both_ranked: peak="3rd quarter lead change"
            else: peak="Opening drive + Q4"
            return viewers,badge,peak,is_upset

        _tv_rows=[]
        for _,trow in _tv_cy.iterrows():
            try:
                v,badge,peak,upset=_tv_rating(trow)
                _tv_rows.append({'row':trow,'viewers':v,'badge':badge,'peak':peak,'upset':upset})
            except: pass
        _tv_rows.sort(key=lambda x:x['viewers'],reverse=True)
        _tv_top=_tv_rows[:10]
        if not _tv_top: st.info("No games to rate yet."); return

        _badge_colors={
            "🏟️ PLAYOFF":("#22d3ee","#0c1a2e"),"⚔️ H2H":("#f97316","#2c0a00"),
            "🚨 UPSET":("#ef4444","#1a0000"),"🔥 RANKED":("#4ade80","#001a08"),
            "💀 THRILLER":("#f43f5e","#1a000a"),"📺 MARQUEE":("#60a5fa","#030f1f"),
            "🏆 NATTY":("#fbbf24","#451a03"),
        }
        # Try to enrich peak from game_summaries
        _gs_peak={}
        try:
            _gsdf=load_game_summaries(year)
            if not _gsdf.empty and 'WEEK' in _gsdf.columns:
                _gsdf['WEEK']=pd.to_numeric(_gsdf['WEEK'],errors='coerce')
                for _,gr in _gsdf.iterrows():
                    _gvt=str(gr.get('Visitor','')).strip().lower()
                    _ght=str(gr.get('Home','')).strip().lower()
                    _gwk=int(gr.get('WEEK',0) or 0)
                    _ghf=int(float(gr.get('HomeScore',0) or 0))
                    _gvf=int(float(gr.get('VisitorScore',0) or 0))
                    _gm=abs(_ghf-_gvf); _gt=_ghf+_gvf
                    _gq1h=int(float(gr.get('Q1_Home',0) or 0)); _gq2h=int(float(gr.get('Q2_Home',0) or 0))
                    _gq1v=int(float(gr.get('Q1_Visitor',0) or 0)); _gq2v=int(float(gr.get('Q2_Visitor',0) or 0))
                    _halfdiff=abs((_gq1h+_gq2h)-(_gq1v+_gq2v))
                    _vot=float(gr.get('Visitor_OT',0) or 0); _hot=float(gr.get('Home_OT',0) or 0)
                    if _vot>0 or _hot>0:
                        _pk="Overtime -- neither side would quit"
                    elif _gm<=3: _pk=f"One-score game to the end -- {_ghf}-{_gvf}"
                    elif _gm<=7 and _halfdiff>=10: _pk=f"Down big at half, held on"
                    elif _gt>=90: _pk=f"{_gt} total pts -- offensive shootout"
                    elif _gm>=28: _pk=f"Dominant -- won by {_gm} pts"
                    else: _pk=f"Final: {_ghf}-{_gvf}"
                    _gs_peak[(_gvt,_ght,_gwk)]=_pk
        except: pass

        for rank,tg in enumerate(_tv_top,1):
            r=tg['row']
            vis=str(r.get('Visitor','')).strip(); hom=str(r.get('Home','')).strip()
            vs=int(r['Vis Score']); hs=int(r['Home Score'])
            vr_raw=r.get('Visitor Rank'); hr_raw=r.get('Home Rank')
            vr=int(vr_raw) if pd.notna(vr_raw) and float(vr_raw)>0 else None
            hr=int(hr_raw) if pd.notna(hr_raw) and float(hr_raw)>0 else None
            wk=int(r['Week']) if pd.notna(r.get('Week')) else 0
            badge=tg['badge']; viewers=tg['viewers']
            resolved_peak=_gs_peak.get((vis.lower(),hom.lower(),wk),tg['peak'])
            vl=image_file_to_data_uri(get_logo_source(vis))
            hl=image_file_to_data_uri(get_logo_source(hom))
            vl_h=f"<img src='{vl}' style='width:36px;height:36px;object-fit:contain;'/>" if vl else "🏈"
            hl_h=f"<img src='{hl}' style='width:36px;height:36px;object-fit:contain;'/>" if hl else "🏈"
            vc=get_team_primary_color(vis); hc=get_team_primary_color(hom)
            vr_s=f"<span style='font-size:.65rem;color:#94a3b8;'>#{vr} </span>" if vr else ""
            hr_s=f"<span style='font-size:.65rem;color:#94a3b8;'>#{hr} </span>" if hr else ""
            vis_bold="font-weight:900;color:#f1f5f9;" if vs>hs else "color:#64748b;"
            hom_bold="font-weight:900;color:#f1f5f9;" if hs>vs else "color:#64748b;"
            bbg,bfg=_badge_colors.get(badge,("#3b82f6","#030f1f"))
            wk_labels={16:"CFP R1",17:"CFP R1",18:"CFP QF",19:"CFP SF",20:"NCG",21:"NCG"}
            wk_disp=wk_labels.get(wk,f"Wk {wk}") if wk else ""
            rk_medals={1:"🥇",2:"🥈",3:"🥉"}
            rk_disp=rk_medals.get(rank,f"#{rank}")
            rk_c="#fbbf24" if rank<=3 else ("#94a3b8" if rank<=6 else "#475569")
            vu=str(r.get('Vis_User','')).strip(); hu=str(r.get('Home_User','')).strip()
            def _utag(u):
                if u in USER_TEAMS:
                    _tc2=get_team_primary_color(USER_TEAMS.get(u,''))
                    return f"<span style='background:{_tc2}22;color:{_tc2};border:1px solid {_tc2}55;font-size:.6rem;font-weight:700;padding:1px 5px;border-radius:3px;margin-left:3px;'>{html.escape(u.upper())}</span>"
                return ""
            card=(
                f"<div style='background:linear-gradient(135deg,rgba(15,23,42,.98),rgba(8,15,28,.98));"
                f"border:1px solid #1e293b;border-radius:12px;padding:12px 14px;margin-bottom:8px;'>"
                f"<div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;'>"
                f"<div style='display:flex;align-items:center;gap:8px;'>"
                f"<span style='font-family:Bebas Neue,sans-serif;font-size:1.4rem;color:{rk_c};line-height:1;'>{rk_disp}</span>"
                f"<span style='background:{bbg};color:{bfg};font-size:.62rem;font-weight:900;"
                f"padding:3px 8px;border-radius:5px;font-family:Barlow Condensed,sans-serif;"
                f"letter-spacing:.08em;'>{badge}</span>"
                f"<span style='font-size:.65rem;color:#475569;font-family:Barlow Condensed,sans-serif;'>{wk_disp}</span>"
                f"</div>"
                f"<div style='text-align:right;'>"
                f"<div style='font-family:Bebas Neue,sans-serif;font-size:1.4rem;color:#fbbf24;line-height:1;'>{viewers:.1f}M</div>"
                f"<div style='font-size:.55rem;color:#475569;text-transform:uppercase;letter-spacing:.08em;'>viewers</div>"
                f"</div></div>"
                f"<div style='display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px;'>"
                f"<div style='display:flex;align-items:center;gap:8px;flex:1;min-width:0;'>"
                f"{vl_h}<div style='min-width:0;'>"
                f"<div style='font-size:.82rem;font-weight:800;color:{vc};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>"
                f"{vr_s}{html.escape(vis)}{_utag(vu)}</div>"
                f"<div style='font-size:.6rem;color:#475569;'>Away</div></div></div>"
                f"<div style='text-align:center;flex-shrink:0;padding:0 6px;'>"
                f"<div style='display:flex;align-items:center;gap:4px;'>"
                f"<span style='{vis_bold}font-family:Bebas Neue,sans-serif;font-size:1.5rem;line-height:1;'>{vs}</span>"
                f"<span style='color:#334155;font-weight:900;font-size:1rem;'>-</span>"
                f"<span style='{hom_bold}font-family:Bebas Neue,sans-serif;font-size:1.5rem;line-height:1;'>{hs}</span>"
                f"</div>"
                f"<div style='font-size:.55rem;color:#334155;text-transform:uppercase;letter-spacing:.06em;margin-top:1px;'>FINAL</div>"
                f"</div>"
                f"<div style='display:flex;align-items:center;gap:8px;flex:1;min-width:0;justify-content:flex-end;'>"
                f"<div style='min-width:0;text-align:right;'>"
                f"<div style='font-size:.82rem;font-weight:800;color:{hc};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>"
                f"{hr_s}{html.escape(hom)}{_utag(hu)}</div>"
                f"<div style='font-size:.6rem;color:#475569;'>Home</div></div>"
                f"{hl_h}</div></div>"
                f"<div style='border-top:1px solid #0f172a;padding-top:7px;font-size:.72rem;color:#64748b;font-style:italic;'>"
                f"{html.escape(resolved_peak)}</div></div>"
            )
            st.markdown(card,unsafe_allow_html=True)
        st.caption(f"📺 Viewership: matchup prestige + ranked status + margin + context. Seeded per game. {len(_tv_cy)} games rated.")
    except Exception as e:
        st.caption(f"Highest Rated Games unavailable: {e}")

# ── DISRUPTORS & CHOKERS ──────────────────────────────────────────────────────
def render_disruptors_chokers():
    st.subheader("⚔️ Spoiling the Moment")
    st.caption("**Disruptors** -- teams causing the most chaos by beating teams they shouldn't. "
               "**Chokers** -- teams taking losses they have no business taking. Both ranked by the Chaos formula.")
    try:
        _fpi_df,_=get_ratings_and_ms_plus(year=CURRENT_YEAR,week_cap=CURRENT_WEEK_NUMBER)
        if _fpi_df.empty or 'Chaos' not in _fpi_df.columns:
            st.info("Run COMPUTE_RATINGS.bat to enable Disruptors & Chokers."); return
        _sched=load_scores_master(CURRENT_YEAR)
        _sched_c=pd.DataFrame()
        if not _sched.empty:
            _sched_c=_sched[_sched['Status'].astype(str).str.upper()=='FINAL'].copy()
            for c in ('Vis Score','Home Score'): _sched_c[c]=pd.to_numeric(_sched_c.get(c),errors='coerce')
            _sched_c['Week']=pd.to_numeric(_sched_c.get('Week'),errors='coerce').fillna(0)
        _fpi_map=dict(zip(_fpi_df['Team'],_fpi_df['FPI']))
        _played=_fpi_df[_fpi_df['GamesPlayed']>0] if 'GamesPlayed' in _fpi_df.columns else _fpi_df
        _disruptors=_played.nlargest(3,'Chaos') if not _played.empty else pd.DataFrame()
        _chokers=_played.nsmallest(3,'Chaos') if not _played.empty else pd.DataFrame()
        def _best_upset(team, won):
            if _sched_c.empty: return ""
            my_fpi=_fpi_map.get(team,0.0)
            _FCS={'FCS','FCSMW','FCSW','FCSS','FCSE'}
            _tg=_sched_c[(_sched_c['Visitor'].astype(str).str.strip()==team)|(_sched_c['Home'].astype(str).str.strip()==team)]
            best_score=-999; best_line=""
            for _,gg in _tg.iterrows():
                vis=str(gg['Visitor']).strip(); vs=float(gg['Vis Score'] or 0); hs=float(gg['Home Score'] or 0)
                is_vis=vis==team; opp=str(gg['Home']).strip() if is_vis else vis
                _won=(vs>hs) if is_vis else (hs>vs)
                if _won!=won: continue
                if any(opp.upper().startswith(p) for p in _FCS): continue
                opp_fpi=_fpi_map.get(opp,0.0); fpi_gap=my_fpi-opp_fpi
                margin=abs(vs-hs)
                if won:
                    pts=12+abs(fpi_gap)*1.2+(margin/7.0)**0.65*9 if fpi_gap<-2 else (3.0 if fpi_gap<=2 else 1.0)
                else:
                    pts=12+abs(fpi_gap)*1.2+(margin/7.0)**0.65*9 if fpi_gap>2 else (3.0 if fpi_gap>=-2 else 1.0)
                if pts>best_score:
                    best_score=pts; wk=int(gg.get('Week',0) or 0)
                    our=int(vs if is_vis else hs); their=int(hs if is_vis else vs)
                    opp_rk_col='Home Rank' if is_vis else 'Visitor Rank'
                    try: opp_rk=int(float(gg.get(opp_rk_col,0))) if pd.notna(gg.get(opp_rk_col)) else None
                    except: opp_rk=None
                    rk_s=f" (#{opp_rk})" if opp_rk and opp_rk<=25 else ""
                    verb="def." if won else "lost to"
                    gap_s=f" as {abs(fpi_gap):.0f}-pt FPI {'underdogs' if won and fpi_gap<-2 else 'favorites'}" if abs(fpi_gap)>2 else ""
                    best_line=f"Wk {wk} {verb} {opp}{rk_s} <strong>{our}-{their}</strong>{gap_s}"
            return best_line
        def _render_group(df, label, icon, color):
            st.markdown(f"<div style='font-family:Barlow Condensed,sans-serif;font-weight:900;font-size:1rem;"
                f"color:{color};letter-spacing:.05em;margin:10px 0 6px;'>{icon} TOP 3 {label.upper()}</div>",unsafe_allow_html=True)
            for di,(_,dr) in enumerate(df.iterrows()):
                dteam=str(dr['Team']); dchaos=float(dr.get('Chaos',0))
                dfpi=float(dr.get('FPI',0)); dw=int(dr.get('W',0)); dl=int(dr.get('L',0))
                dcolor=get_team_primary_color(dteam); dlogo=get_school_logo_src(dteam)
                dlh=f"<img src='{dlogo}' style='width:24px;height:24px;object-fit:contain;vertical-align:middle;margin-right:6px;'/>" if dlogo else ""
                dis_user=dteam in ALL_USER_TEAMS
                bg=f"background:linear-gradient(90deg,{dcolor}15 0%,#06090f 35%);" if dis_user else "background:#06090f;"
                bl=f"border-left:4px solid {dcolor};" if dis_user else "border-left:2px solid #1e293b;"
                won_flag=label=='Disruptors'
                best=_best_upset(dteam,won_flag)
                best_html=f"<div style='margin-top:4px;font-size:.65rem;color:#64748b;padding-left:24px;'>{best}</div>" if best else ""
                st.markdown(f"""
<div style='{bg}{bl}border-radius:8px;padding:8px 12px;margin-bottom:5px;'>
  <div style='display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px;'>
    <div style='display:flex;align-items:center;gap:5px;'>
      <span style='color:#475569;font-size:.65rem;font-family:Bebas Neue,sans-serif;width:16px;'>#{di+1}</span>
      {dlh}<span style='font-family:Barlow Condensed,sans-serif;font-weight:900;font-size:.95rem;color:#f8fafc;'>{html.escape(_abbrev(dteam))}</span>
      <span style='font-size:.65rem;color:#64748b;'>{dw}-{dl} · FPI {dfpi:+.1f}</span>
    </div>
    <span style='font-family:Bebas Neue,sans-serif;font-size:1.1rem;color:{color};'>{dchaos:+.0f}</span>
  </div>{best_html}
</div>""", unsafe_allow_html=True)
        col1,col2=st.columns(2)
        with col1: _render_group(_disruptors,"Disruptors","💥","#f97316")
        with col2: _render_group(_chokers,"Chokers","💀","#f87171")
    except Exception as e:
        st.caption(f"Disruptors/Chokers unavailable: {e}")

# ── FLYING UNDER THE RADAR ────────────────────────────────────────────────────
def render_flying_under_radar():
    st.subheader("📡 Flying Under the Radar")
    st.caption("Teams whose FPI rank is significantly better than their CFP rank -- the computers see something the voters don't.")
    try:
        _fpi_df,_=get_ratings_and_ms_plus(year=CURRENT_YEAR,week_cap=CURRENT_WEEK_NUMBER)
        if _fpi_df.empty: return
        _cfp=pd.read_csv('cfp_rankings_history.csv')
        _cfp['YEAR']=pd.to_numeric(_cfp['YEAR'],errors='coerce')
        _cfp['WEEK']=pd.to_numeric(_cfp['WEEK'],errors='coerce')
        _cfp['RANK']=pd.to_numeric(_cfp['RANK'],errors='coerce')
        _cy=_cfp[_cfp['YEAR']==CURRENT_YEAR]
        if _cy.empty: st.info("No CFP rankings yet."); return
        _lw=int(_cy['WEEK'].max())
        _snap=_cy[_cy['WEEK']==_lw].copy()
        _cfp_map=dict(zip(_snap['TEAM'].astype(str).str.strip(),_snap['RANK'].astype(float)))
        _fpi_ranked=_fpi_df.copy().reset_index(drop=True)
        _fpi_ranked.insert(0,'FPI_Rank',range(1,len(_fpi_ranked)+1))
        _fpi_ranked['CFP_Rank']=_fpi_ranked['Team'].map(_cfp_map)
        _fpi_ranked=_fpi_ranked.dropna(subset=['CFP_Rank']).copy()
        _fpi_ranked['Gap']=_fpi_ranked['CFP_Rank']-_fpi_ranked['FPI_Rank']
        _ur=_fpi_ranked[_fpi_ranked['Gap']>=3].nlargest(5,'Gap').reset_index(drop=True)
        if _ur.empty: st.info("No significant FPI/CFP gaps found."); return
        for _,row in _ur.iterrows():
            tm=str(row['Team']); gap=int(row['Gap']); fpi_rk=int(row['FPI_Rank'])
            cfp_rk=int(row['CFP_Rank']); fpi_v=float(row.get('FPI',0))
            color=get_team_primary_color(tm); logo=get_school_logo_src(tm)
            lh=f"<img src='{logo}' style='width:24px;height:24px;object-fit:contain;vertical-align:middle;margin-right:6px;'/>" if logo else ""
            w=int(row.get('W',0)); l=int(row.get('L',0))
            st.markdown(f"""
<div style='background:#06090f;border:1px solid #1e293b;border-left:3px solid {color};
    border-radius:8px;padding:8px 12px;margin-bottom:5px;'>
  <div style='display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px;'>
    <div style='display:flex;align-items:center;gap:6px;'>
      {lh}<span style='font-family:Barlow Condensed,sans-serif;font-weight:900;font-size:.95rem;color:{color};'>{html.escape(_abbrev(tm))}</span>
      <span style='font-size:.65rem;color:#64748b;'>{w}-{l} · FPI {fpi_v:+.1f}</span>
    </div>
    <div style='display:flex;align-items:center;gap:8px;'>
      <span style='font-size:.68rem;color:#60a5fa;'>FPI #{fpi_rk}</span>
      <span style='color:#334155;'>→</span>
      <span style='font-size:.68rem;color:#f87171;'>CFP #{cfp_rk}</span>
      <span style='background:#fbbf2420;color:#fbbf24;border-radius:4px;padding:1px 7px;font-size:.62rem;font-weight:700;'>+{gap} spots undervalued</span>
    </div>
  </div>
</div>""", unsafe_allow_html=True)
    except Exception as e:
        st.caption(f"Flying Under the Radar unavailable: {e}")

# ── HEISMAN WATCH ─────────────────────────────────────────────────────────────
def render_heisman_watch(year):
    st.subheader(f"🏆 {year} Heisman Watch")
    try:
        _hw=pd.read_csv('Heisman_watch_history.csv')
        _hw['YEAR']=pd.to_numeric(_hw['YEAR'],errors='coerce')
        _hw['WEEK']=pd.to_numeric(_hw['WEEK'],errors='coerce')
        _hw['RANK']=pd.to_numeric(_hw['RANK'],errors='coerce')
        _cy=_hw[_hw['YEAR']==year].copy()
        if _cy.empty: st.info(f"No Heisman Watch data for {year}."); return
        _lw=int(_cy['WEEK'].max())
        _curr=_cy[_cy['WEEK']==_lw].sort_values('RANK').reset_index(drop=True)
        # Prior week for delta
        _prev_weeks=sorted(_cy['WEEK'].dropna().unique())
        _pw=int(_prev_weeks[-2]) if len(_prev_weeks)>=2 else None
        _prev_map={}
        if _pw:
            _prev_snap=_cy[_cy['WEEK']==_pw]
            _prev_map=dict(zip(_prev_snap['NAME'].astype(str).str.strip(),_prev_snap['RANK'].astype(int)))
        pos_colors={'QB':'#60a5fa','HB':'#4ade80','WR':'#f97316','TE':'#a78bfa',
                    'DE':'#f87171','DT':'#f87171','CB':'#fbbf24','LB':'#fbbf24','K':'#94a3b8'}
        thead=(
            "<tr style='background:#0a1220;'>"
            "<th style='padding:5px 8px;color:#1e293b;font-size:.58rem;width:28px;text-align:center;'>#</th>"
            "<th style='padding:5px 6px;color:#475569;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;width:36px;text-align:center;'>Δ</th>"
            "<th style='padding:5px 6px;color:#475569;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:left;'>Name</th>"
            "<th style='padding:5px 6px;color:#475569;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:center;'>Pos</th>"
            "<th style='padding:5px 6px;color:#fbbf24;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;text-align:left;'>Team</th>"
            "</tr>"
        )
        rows_html=""
        for _,row in _curr.iterrows():
            name=str(row.get('NAME',row.get('Name','?'))).strip()
            pos=str(row.get('POS',row.get('Pos','?'))).strip().upper()
            team=str(row.get('TEAM',row.get('Team','?'))).strip()
            rk=int(row['RANK'])
            prev_rk=_prev_map.get(name)
            if prev_rk:
                delta=prev_rk-rk
                if delta>0: delta_html=f"<span style='color:#4ade80;font-weight:700;font-size:.72rem;'>▲{delta}</span>"
                elif delta<0: delta_html=f"<span style='color:#f87171;font-weight:700;font-size:.72rem;'>▼{abs(delta)}</span>"
                else: delta_html="<span style='color:#475569;font-size:.7rem;'>--</span>"
            else:
                delta_html="<span style='background:#3b82f620;color:#60a5fa;border-radius:3px;padding:1px 4px;font-size:.58rem;'>NEW</span>"
            pos_c=pos_colors.get(pos,'#94a3b8')
            is_u=team in ALL_USER_TEAMS
            uc=get_team_primary_color(team) if is_u else "#0f172a"
            bg=f"background:linear-gradient(90deg,{uc}20 0%,#06090f 30%);" if is_u else "background:#06090f;"
            bl=f"border-left:3px solid {uc};" if is_u else "border-left:2px solid #0f172a;"
            nm_w="font-weight:900;color:#f8fafc;" if is_u else "font-weight:500;color:#94a3b8;"
            logo=get_school_logo_src(team)
            lh=f"<img src='{logo}' style='width:16px;height:16px;object-fit:contain;vertical-align:middle;margin-right:4px;'/>" if logo else ""
            rows_html+=(
                f"<tr style='{bg}{bl}'>"
                f"<td style='padding:5px 8px;text-align:center;font-family:Bebas Neue,sans-serif;font-size:.9rem;color:#f8fafc;'>{rk}</td>"
                f"<td style='padding:5px 6px;text-align:center;'>{delta_html}</td>"
                f"<td style='padding:5px 6px;{nm_w}font-family:Barlow Condensed,sans-serif;font-size:.88rem;letter-spacing:.02em;'>{html.escape(name)}</td>"
                f"<td style='padding:5px 6px;text-align:center;'>"
                f"<span style='background:{pos_c}25;color:{pos_c};border:1px solid {pos_c}55;border-radius:4px;padding:1px 7px;font-size:.65rem;font-weight:700;'>{pos}</span></td>"
                f"<td style='padding:5px 6px;'>{lh}<span style='font-size:.8rem;color:#64748b;'>{html.escape(_abbrev(team))}</span></td>"
                f"</tr>"
            )
        st.markdown(
            f"<div class='isp-power-table-wrap'><table class='isp-power-table' style='min-width:340px;'>"
            f"<thead>{thead}</thead><tbody>{rows_html}</tbody></table></div>",
            unsafe_allow_html=True
        )
        st.caption(f"Week {_lw} standings · {len(_curr)} candidates")
    except Exception as e:
        st.caption(f"Heisman Watch unavailable: {e}")

# ── WHO WOULD WIN ─────────────────────────────────────────────────────────────
def render_who_would_win():
    st.subheader("🏆 Who Would Win?")
    st.caption("Pit any two national title winners from dynasty history against each other.")
    try:
        _www_champs=pd.read_csv('champs.csv')
        _www_champs['YEAR']=pd.to_numeric(_www_champs.get('YEAR'),errors='coerce')
        _www_champs=_www_champs.dropna(subset=['YEAR']).copy()
        _www_champs['YEAR']=_www_champs['YEAR'].astype(int)
        _www_champs=_www_champs[_www_champs['Team'].notna()&
            (_www_champs['Team'].astype(str).str.strip()!='')&
            (_www_champs['Team'].astype(str).str.lower()!='nan')].copy()
        _www_champs['Team']=_www_champs['Team'].astype(str).str.strip()
        _www_champs['user']=_www_champs.get('user',pd.Series(dtype=str)).fillna('').astype(str).str.strip()
        if _www_champs.empty: st.info("No champion data found in champs.csv."); return
        # Build ratings snapshot for each natty year
        try:
            _www_ratings=pd.read_csv('TeamRatingsHistory.csv')
            _www_ratings['YEAR']=pd.to_numeric(_www_ratings['YEAR'],errors='coerce')
            _www_ratings['TEAM']=_www_ratings['TEAM'].astype(str).str.strip()
        except: _www_ratings=pd.DataFrame()
        _www_options=[f"{int(r['YEAR'])} -- {r['Team']} ({r['user']})" if r['user'] else f"{int(r['YEAR'])} -- {r['Team']}"
                      for _,r in _www_champs.sort_values('YEAR',ascending=False).iterrows()]
        if len(_www_options)<2: st.info("Need at least 2 championship seasons for this."); return
        c1,c2=st.columns(2)
        with c1:
            _www_a=st.selectbox("Team A",_www_options,index=0,key="www_a")
        with c2:
            _www_b=st.selectbox("Team B",_www_options,index=min(1,len(_www_options)-1),key="www_b")
        if _www_a==_www_b: st.warning("Pick two different seasons."); return
        def _parse_www(opt):
            yr=int(opt.split(' -- ')[0])
            team_part=opt.split(' -- ')[1].split(' (')[0].strip()
            row=_www_champs[(_www_champs['YEAR']==yr)&(_www_champs['Team']==team_part)]
            return yr,team_part,row.iloc[0] if not row.empty else None
        _ya,_ta,_ra=_parse_www(_www_a); _yb,_tb,_rb=_parse_www(_www_b)
        def _get_ratings(team,year):
            if not _www_ratings.empty:
                _yr=_www_ratings[(_www_ratings['TEAM']==team)&(_www_ratings['YEAR']==year)]
                if not _yr.empty:
                    r=_yr.iloc[0]
                    return (int(safe_num(r.get('OVERALL',r.get('OVR',82)),82)),
                            int(safe_num(r.get('OFFENSE',r.get('OFF',82)),82)),
                            int(safe_num(r.get('DEFENSE',r.get('DEF',82)),82)))
            _try_file=f'team_ratings_{year}.csv'
            if os.path.exists(_try_file):
                try:
                    _tr=pd.read_csv(_try_file); _tr['TEAM']=_tr['TEAM'].astype(str).str.strip()
                    _tr_row=_tr[_tr['TEAM']==team]
                    if not _tr_row.empty:
                        r=_tr_row.iloc[0]
                        return (int(safe_num(r.get('OVR',r.get('OVERALL',82)),82)),
                                int(safe_num(r.get('OFF',r.get('OFFENSE',82)),82)),
                                int(safe_num(r.get('DEF',r.get('DEFENSE',82)),82)))
                except: pass
            return (82,82,82)
        _ovr_a,_off_a,_def_a=_get_ratings(_ta,_ya)
        _ovr_b,_off_b,_def_b=_get_ratings(_tb,_yb)
        # Simulation
        _sims=1000; _a_wins=0
        for _ in range(_sims):
            _a_eff=(_off_a*0.6+_ovr_a*0.4)/100+(random.gauss(0,0.08))
            _b_eff=(_off_b*0.6+_ovr_b*0.4)/100+(random.gauss(0,0.08))
            _a_def=(_def_a*0.6+_ovr_a*0.4)/100+(random.gauss(0,0.06))
            _b_def=(_def_b*0.6+_ovr_b*0.4)/100+(random.gauss(0,0.06))
            _a_score=max(0,round((_a_eff-_b_def*0.5)*55+random.gauss(0,7)))
            _b_score=max(0,round((_b_eff-_a_def*0.5)*55+random.gauss(0,7)))
            if _a_score>_b_score: _a_wins+=1
        _a_pct=round(_a_wins/_sims*100,1); _b_pct=round(100-_a_pct,1)
        _ca=get_team_primary_color(_ta); _cb=get_team_primary_color(_tb)
        _la=image_file_to_data_uri(get_logo_source(_ta)); _lb=image_file_to_data_uri(get_logo_source(_tb))
        _lha=f"<img src='{_la}' style='width:48px;height:48px;object-fit:contain;'/>" if _la else "🏆"
        _lhb=f"<img src='{_lb}' style='width:48px;height:48px;object-fit:contain;'/>" if _lb else "🏆"
        _winner=_ta if _a_pct>=50 else _tb; _wpct=max(_a_pct,_b_pct)
        st.markdown(f"""
<div style='background:#06090f;border:1px solid #1e293b;border-radius:12px;padding:18px;margin:12px 0;'>
  <div style='display:flex;align-items:center;justify-content:space-around;flex-wrap:wrap;gap:12px;margin-bottom:14px;'>
    <div style='text-align:center;'>
      {_lha}
      <div style='font-family:Barlow Condensed,sans-serif;font-weight:900;color:{_ca};font-size:.95rem;margin-top:4px;'>{html.escape(_ta)}</div>
      <div style='font-size:.7rem;color:#64748b;'>{_ya} · {_ovr_a} OVR</div>
      <div style='font-family:Bebas Neue,sans-serif;font-size:2rem;color:{_ca};margin-top:4px;'>{_a_pct}%</div>
    </div>
    <div style='text-align:center;'>
      <div style='font-family:Bebas Neue,sans-serif;font-size:1.5rem;color:#475569;'>VS</div>
      <div style='font-size:.62rem;color:#334155;margin-top:4px;'>{_sims} sims</div>
    </div>
    <div style='text-align:center;'>
      {_lhb}
      <div style='font-family:Barlow Condensed,sans-serif;font-weight:900;color:{_cb};font-size:.95rem;margin-top:4px;'>{html.escape(_tb)}</div>
      <div style='font-size:.7rem;color:#64748b;'>{_yb} · {_ovr_b} OVR</div>
      <div style='font-family:Bebas Neue,sans-serif;font-size:2rem;color:{_cb};margin-top:4px;'>{_b_pct}%</div>
    </div>
  </div>
  <div style='background:#1e293b;border-radius:4px;height:10px;overflow:hidden;margin-bottom:8px;'>
    <div style='width:{_a_pct}%;height:100%;background:linear-gradient(90deg,{_ca},{_cb});border-radius:4px;'></div>
  </div>
  <div style='text-align:center;font-size:.78rem;color:#94a3b8;'>
    Model gives <strong style='color:#f8fafc;'>{html.escape(_winner)}</strong> the edge at <strong style='color:#fbbf24;'>{_wpct}%</strong>
  </div>
</div>""", unsafe_allow_html=True)
    except Exception as e:
        st.info(f"Who Would Win requires champs.csv and team ratings. ({e})")

# ── CFP BRACKET -- MOBILE FRIENDLY ────────────────────────────────────────────
def render_cfp_bracket():
    st.subheader("🏆 CFP Bracket")
    try:
        if not os.path.exists('CFPbracketresults.csv'):
            st.info("CFPbracketresults.csv not found."); return
        _b=pd.read_csv('CFPbracketresults.csv')
        _b['YEAR']=pd.to_numeric(_b['YEAR'],errors='coerce')
        _cy=_b[_b['YEAR']==CURRENT_YEAR].copy()
        if _cy.empty:
            st.info(f"No bracket data for {CURRENT_YEAR} yet."); return
        _round_order={'R1':1,'QF':2,'SF':3,'NCG':4}
        _round_names={'R1':'First Round','QF':'Quarterfinals','SF':'Semifinals','NCG':'Championship'}
        _cy['_rsort']=_cy['ROUND'].map(_round_order).fillna(0)
        # Render each round as cards
        for rnd_key in ['R1','QF','SF','NCG']:
            _rnd=_cy[_cy['ROUND']==rnd_key].sort_values('GAME_ID' if 'GAME_ID' in _cy.columns else 'ROUND')
            if _rnd.empty: continue
            st.markdown(f"<div style='font-family:Barlow Condensed,sans-serif;font-weight:900;"
                f"font-size:1rem;color:#fbbf24;letter-spacing:.05em;text-transform:uppercase;"
                f"margin:12px 0 6px;border-left:3px solid #fbbf24;padding-left:8px;'>"
                f"{_round_names.get(rnd_key,rnd_key)}</div>",unsafe_allow_html=True)
            n_games=len(_rnd)
            cols=st.columns(min(2,n_games)) if n_games>1 else [st.container()]
            for ci,(_,game) in enumerate(_rnd.iterrows()):
                t1=str(game.get('TEAM1','')).strip(); t2=str(game.get('TEAM2','')).strip()
                s1=pd.to_numeric(game.get('TEAM1_SCORE',0),errors='coerce')
                s2=pd.to_numeric(game.get('TEAM2_SCORE',0),errors='coerce')
                completed=str(game.get('COMPLETED','0')).strip() in ('1','True','true','yes')
                winner=str(game.get('WINNER','')).strip()
                loser=str(game.get('LOSER','')).strip()
                def _clean_team(raw):
                    s=str(raw).strip(); s=re.sub(r'^#\d+\s+','',s)
                    return s if not re.match(r'(?i)^(winner|loser|tbd|bye)',s) else '?'
                t1c=_clean_team(t1); t2c=_clean_team(t2)
                logo1=image_file_to_data_uri(get_logo_source(t1c)); logo2=image_file_to_data_uri(get_logo_source(t2c))
                l1h=f"<img src='{logo1}' style='width:32px;height:32px;object-fit:contain;'/>" if logo1 else "🏈"
                l2h=f"<img src='{logo2}' style='width:32px;height:32px;object-fit:contain;'/>" if logo2 else "🏈"
                c1_col=get_team_primary_color(t1c); c2_col=get_team_primary_color(t2c)
                if completed and winner:
                    w_is_t1=winner.lower()==t1c.lower() or (pd.notna(s1) and pd.notna(s2) and float(s1)>float(s2))
                    s1_d=int(float(s1)) if pd.notna(s1) else 0
                    s2_d=int(float(s2)) if pd.notna(s2) else 0
                    t1_bold="font-weight:900;color:#f1f5f9;" if w_is_t1 else "font-weight:400;color:#475569;"
                    t2_bold="font-weight:900;color:#f1f5f9;" if not w_is_t1 else "font-weight:400;color:#475569;"
                    s1_bold=f"color:#4ade80;font-weight:900;" if w_is_t1 else "color:#f87171;"
                    s2_bold=f"color:#4ade80;font-weight:900;" if not w_is_t1 else "color:#f87171;"
                    w_border=c1_col if w_is_t1 else c2_col
                    card_html=f"""
<div style='background:#06090f;border:1px solid {w_border}44;border-top:3px solid {w_border};
    border-radius:10px;padding:12px 14px;margin-bottom:8px;'>
  <div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;'>
    <div style='display:flex;align-items:center;gap:8px;'>
      {l1h}<span style='font-family:Barlow Condensed,sans-serif;{t1_bold}font-size:.9rem;'>{html.escape(_abbrev(t1c))}</span>
    </div>
    <span style='font-family:Bebas Neue,sans-serif;font-size:1.2rem;{s1_bold}'>{s1_d}</span>
  </div>
  <div style='display:flex;align-items:center;justify-content:space-between;'>
    <div style='display:flex;align-items:center;gap:8px;'>
      {l2h}<span style='font-family:Barlow Condensed,sans-serif;{t2_bold}font-size:.9rem;'>{html.escape(_abbrev(t2c))}</span>
    </div>
    <span style='font-family:Bebas Neue,sans-serif;font-size:1.2rem;{s2_bold}'>{s2_d}</span>
  </div>
  <div style='text-align:right;margin-top:5px;font-size:.58rem;color:#334155;text-transform:uppercase;letter-spacing:.08em;'>FINAL</div>
</div>"""
                else:
                    # Upcoming / TBD
                    t1_display=t1c if t1c!='?' else '?'
                    t2_display=t2c if t2c!='?' else '?'
                    card_html=f"""
<div style='background:#0a0f1a;border:1px solid #1e293b;border-radius:10px;padding:12px 14px;margin-bottom:8px;'>
  <div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;'>
    <div style='display:flex;align-items:center;gap:8px;'>
      {l1h}<span style='font-family:Barlow Condensed,sans-serif;font-weight:600;color:#94a3b8;font-size:.9rem;'>{html.escape(_abbrev(t1_display))}</span>
    </div>
    <span style='color:#334155;font-size:.75rem;'>--</span>
  </div>
  <div style='display:flex;align-items:center;justify-content:space-between;'>
    <div style='display:flex;align-items:center;gap:8px;'>
      {l2h}<span style='font-family:Barlow Condensed,sans-serif;font-weight:600;color:#94a3b8;font-size:.9rem;'>{html.escape(_abbrev(t2_display))}</span>
    </div>
    <span style='color:#334155;font-size:.75rem;'>--</span>
  </div>
  <div style='text-align:right;margin-top:5px;font-size:.58rem;color:#334155;text-transform:uppercase;letter-spacing:.08em;'>UPCOMING</div>
</div>"""
                with cols[ci%len(cols)]:
                    st.markdown(card_html,unsafe_allow_html=True)
    except Exception as e:
        st.caption(f"CFP Bracket unavailable: {e}")

# ── NATTY DNA (standalone for Metrics tab) ───────────────────────────────────
def render_natty_dna():
    st.subheader("🧬 Natty DNA")
    st.caption("Championship roster players who made it to the NFL -- the true measure of a dynasty program.")
    # Team selector
    _sel_team=st.selectbox("Select team",sorted(ALL_USER_TEAMS),key="natty_dna_team")
    _sel_color=get_team_primary_color(_sel_team)
    # Load draft data
    try:
        _draft_df=pd.read_csv('cfb_draft_results.csv') if os.path.exists('cfb_draft_results.csv') else pd.DataFrame()
        if not _draft_df.empty:
            _draft_df['DraftYear']=pd.to_numeric(_draft_df['DraftYear'],errors='coerce')
            _draft_df['DraftRound']=pd.to_numeric(_draft_df['DraftRound'],errors='coerce')
            _draft_df['OVR']=pd.to_numeric(_draft_df.get('OVR',_draft_df.get('CollegeOVR',80)),errors='coerce')
    except: _draft_df=pd.DataFrame()
    try:
        _natty=pd.read_csv('champs.csv')
        _natty.columns=[str(c).strip() for c in _natty.columns]
        _nc_year_col=next((c for c in _natty.columns if 'YEAR' in c.upper() or c.upper()=='SEASON'),None)
        _nc_team_col=next((c for c in _natty.columns if 'TEAM' in c.upper() and 'USER' not in c.upper()),None)
        _nc_user_col=next((c for c in _natty.columns if 'USER' in c.upper()),None)
        if not _nc_year_col: st.info("champs.csv missing YEAR column."); return
        _match_col=_nc_team_col if _nc_team_col else _nc_user_col
        _team_natties=_natty[_natty[_match_col].astype(str).str.strip()==_sel_team].copy()
        if _team_natties.empty and _nc_user_col:
            _rev_user={v:k for k,v in USER_TEAMS.items()}
            _sel_user=_rev_user.get(_sel_team,"")
            if _sel_user:
                _team_natties=_natty[_natty[_nc_user_col].astype(str).str.strip().str.lower()==_sel_user.lower()].copy()
        if _team_natties.empty:
            st.info(f"No championship seasons found for {_sel_team}. Win a natty first! 🏆"); return
        _natty_years=sorted(pd.to_numeric(_team_natties[_nc_year_col],errors='coerce').dropna().astype(int).tolist())
        total_dna=0; total_rd1=0
        for _ny in _natty_years:
            _ny_picks=pd.DataFrame()
            if not _draft_df.empty:
                _tc=next((c for c in ('CollegeTeam','Team','TEAM') if c in _draft_df.columns),None)
                if _tc:
                    _ny_picks=_draft_df[(_draft_df[_tc].astype(str).str.strip()==_sel_team)&
                        (_draft_df['DraftYear']>=_ny)&(_draft_df['DraftYear']<=_ny+5)].copy()
            total_dna+=len(_ny_picks)
            total_rd1+=int((_ny_picks['DraftRound']==1).sum()) if not _ny_picks.empty else 0
            # player chips
            _chips=""
            if not _ny_picks.empty:
                for _,pp in _ny_picks.sort_values('DraftRound').iterrows():
                    pname=html.escape(str(pp.get('Player','?'))); ppos=html.escape(str(pp.get('Pos','?')))
                    prnd=pp.get('DraftRound',pd.NA); povr=pp.get('OVR',pd.NA)
                    pyr=int(pp.get('DraftYear',_ny)) if pd.notna(pp.get('DraftYear')) else _ny
                    if pd.notna(prnd) and int(prnd)==1:
                        cbg="rgba(250,204,21,.18)"; cbrd="#FACC15"; crnd_s="🥇 Rd 1"
                    elif pd.notna(prnd) and int(prnd)<=3:
                        cbg="rgba(96,165,250,.14)"; cbrd="#60A5FA"; crnd_s=f"Rd {int(prnd)}"
                    else:
                        cbg="rgba(148,163,184,.10)"; cbrd="rgba(148,163,184,.3)"
                        crnd_s=f"Rd {int(prnd)}" if pd.notna(prnd) else "UDFA"
                    ovr_s=f" · {int(povr)} OVR" if pd.notna(povr) else ""
                    yr_s=f" '{str(pyr)[-2:]}" if pyr!=_ny else ""
                    _chips+=(f"<div style='display:inline-flex;align-items:center;gap:6px;background:{cbg};"
                        f"border:1px solid {cbrd};border-radius:6px;padding:5px 10px;margin:3px 4px 3px 0;'>"
                        f"<span style='font-weight:700;color:#f1f5f9;font-size:.78rem;'>{pname}</span>"
                        f"<span style='font-size:.65rem;color:#94a3b8;'>{ppos}{ovr_s}</span>"
                        f"<span style='font-size:.65rem;font-weight:700;color:{cbrd};'>{crnd_s}{yr_s}</span>"
                        f"</div>")
            else:
                _chips="<span style='color:#64748b;font-size:.8rem;font-style:italic;'>No NFL draft picks linked yet.</span>"
            _cnt=f"{len(_ny_picks)} player{'s' if len(_ny_picks)!=1 else ''} to the NFL"
            _rd1_s=f" · {int((_ny_picks['DraftRound']==1).sum())} 1st rounder(s)" if not _ny_picks.empty and int((_ny_picks['DraftRound']==1).sum())>0 else ""
            _nl=image_file_to_data_uri(get_logo_source(_sel_team))
            _nlh=f"<img src='{_nl}' style='width:40px;height:40px;object-fit:contain;margin-right:12px;'/>" if _nl else ""
            st.markdown(f"""
<div style='background:linear-gradient(135deg,rgba(250,204,21,.08),rgba(15,23,42,.95));
    border:1px solid rgba(250,204,21,.25);border-radius:12px;padding:16px 18px;margin-bottom:12px;'>
  <div style='display:flex;align-items:center;margin-bottom:10px;'>
    {_nlh}<div>
      <div style='font-size:1.1rem;font-weight:900;color:#FACC15;'>🏆 {_ny} National Champions</div>
      <div style='font-size:.75rem;color:#94a3b8;margin-top:2px;'>{_cnt}{_rd1_s}</div>
    </div>
  </div>
  <div style='display:flex;flex-wrap:wrap;gap:0;'>{_chips}</div>
</div>""", unsafe_allow_html=True)
        if _natty_years:
            _dna_per=total_dna/len(_natty_years)
            st.markdown(f"""
<div style='background:rgba(255,255,255,.04);border-radius:8px;padding:12px 16px;
    display:flex;gap:24px;flex-wrap:wrap;border:1px solid rgba(255,255,255,.08);margin-top:4px;'>
  <div style='text-align:center;'><div style='font-size:1.5rem;font-weight:900;color:#FACC15;'>{len(_natty_years)}</div>
    <div style='font-size:.65rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.07em;'>Championships</div></div>
  <div style='text-align:center;'><div style='font-size:1.5rem;font-weight:900;color:#f1f5f9;'>{total_dna}</div>
    <div style='font-size:.65rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.07em;'>Total NFL Picks</div></div>
  <div style='text-align:center;'><div style='font-size:1.5rem;font-weight:900;color:#FACC15;'>{total_rd1}</div>
    <div style='font-size:.65rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.07em;'>1st Rounders</div></div>
  <div style='text-align:center;'><div style='font-size:1.5rem;font-weight:900;color:#60a5fa;'>{_dna_per:.1f}</div>
    <div style='font-size:.65rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.07em;'>NFL Picks/Natty</div></div>
</div>""", unsafe_allow_html=True)
    except Exception as e:
        st.caption(f"Natty DNA unavailable: {e}")

# ── ROSTER ATTRITION TAB ──────────────────────────────────────────────────────
def render_roster_attrition_tab():
    _atr_col1,_atr_col2=st.columns([3,1])
    with _atr_col1:
        st.header("📋 Roster Attrition")
    with _atr_col2:
        target_year=st.selectbox("Season",[CURRENT_YEAR,CURRENT_YEAR+1],
            format_func=lambda y:f"{y} (Current)" if y==CURRENT_YEAR else f"{y} (Upcoming)",
            key="attrition_yr_sel")
    if target_year==CURRENT_YEAR:
        st.caption(f"Departing talent after {target_year}. NFL exits (2043 draft) + transfers out (2042) + seniors graduating.")
    else:
        st.caption(f"Projected {target_year} losses — known seniors from current rosters. NFL/transfer estimates.")
    attrition_data=compute_attrition_ratings(target_year)
    # Load raw data for detail tables
    try:
        xf_raw=pd.read_csv('attrition_transfers.csv')
        xf_raw.columns=[str(c).strip() for c in xf_raw.columns]
        for _ox,_nx in [('season_year','Year'),('YEAR','Year'),('team','Team'),('TEAM','Team')]:
            if _ox in xf_raw.columns and _nx not in xf_raw.columns: xf_raw=xf_raw.rename(columns={_ox:_nx})
        xf_raw['Year']=pd.to_numeric(xf_raw.get('Year',xf_raw.get('YEAR',target_year)),errors='coerce')
        xf_raw=xf_raw[(xf_raw['Year'].fillna(-1).astype(int)==target_year)&
                       (xf_raw['TransferStatus'].astype(str).str.strip()=='Leaving')].copy()
    except: xf_raw=pd.DataFrame()
    try:
        draft_raw=pd.read_csv('cfb_draft_results.csv')
        draft_raw.columns=[str(c).strip() for c in draft_raw.columns]
        draft_raw['DraftYear']=pd.to_numeric(draft_raw['DraftYear'],errors='coerce')
        # 2043 season attrition: use 2043 draft picks (players leaving after 2043)
        draft_raw=draft_raw[draft_raw['DraftYear'].fillna(-1).astype(int)==target_year].copy()
        draft_raw['DraftRound']=pd.to_numeric(draft_raw['DraftRound'],errors='coerce').fillna(8)
    except: draft_raw=pd.DataFrame()
    # ── ATTRITION RATING SUMMARY CARDS ───────────────────────────────
    st.markdown(f"### {CURRENT_YEAR} Attrition Ratings")
    _sorted_users=sorted(attrition_data.keys(),key=lambda u: attrition_data[u]['pts'],reverse=True)
    cols=st.columns(min(3,len(_sorted_users))); ci=0
    for user in _sorted_users:
        d=attrition_data[user]; team=d['team']
        primary=get_team_primary_color(team)
        logo=image_file_to_data_uri(get_logo_source(team))
        lh=f"<img src='{logo}' style='width:48px;height:48px;object-fit:contain;'/>" if logo else "🏈"
        # ── Attrition card with enriched data ────────────────────────
        # Senior count + biggest skill loss
        _sr_count=0; _biggest_loss=""
        _SKILL={'QB','HB','WR','TE','CB','FS','SS','LEDG','REDG','MLB','OLB','WILL','SAM','DE'}
        try:
            _ros_f=f'cfb_136_top30_rosters_{CURRENT_YEAR}.csv'
            if os.path.exists(_ros_f):
                _rdf2=pd.read_csv(_ros_f)
                _rdf2['TEAM']=_rdf2['TEAM'].astype(str).str.strip()
                _rdf2['OVR']=pd.to_numeric(_rdf2['OVR'],errors='coerce').fillna(0)
                if 'YEAR' in _rdf2.columns:
                    _rdf2['YEAR']=pd.to_numeric(_rdf2['YEAR'],errors='coerce')
                    _rdf2=_rdf2[_rdf2['YEAR'].fillna(-1).astype(int)==CURRENT_YEAR]
                _yr_c2=next((c for c in ('YEAR_CLASS','Class','CLASS') if c in _rdf2.columns),None)
                _t_ros=_rdf2[_rdf2['TEAM']==team]
                if _yr_c2:
                    _srs=_t_ros[_t_ros[_yr_c2].astype(str).apply(is_senior_label)]
                    _sr_count=len(_srs)
                    _skill_srs=_srs[_srs['POS'].astype(str).str.upper().str.strip().isin(_SKILL)]
                    if not _skill_srs.empty:
                        _top_sr=_skill_srs.nlargest(1,'OVR').iloc[0]
                        _nm_c=next((c for c in ('NAME','Name','PLAYER') if c in _top_sr.index),'NAME')
                        _biggest_loss=f"{str(_top_sr.get(_nm_c,'?')).strip()} ({_top_sr.get('POS','?')}, {int(_top_sr['OVR'])} OVR)"
        except: pass
        # Incoming recruits
        try:
            _inc=pd.read_csv('attrition_incoming.csv') if os.path.exists('attrition_incoming.csv') else pd.DataFrame()
            if not _inc.empty:
                _inc.columns=[str(c).strip() for c in _inc.columns]
                # Normalise renamed columns
                for _old,_new in [('season_year','Year'),('YEAR','Year'),('team','Team'),('TEAM','Team'),('Stars','StarRating'),('star_rating','StarRating'),('Natl_Rank','NationalRank'),('national_rank','NationalRank'),('recruit_type','RecruitType'),('pos','Pos'),('POS','Pos'),('name','Name'),('NAME','Name')]:
                    if _old in _inc.columns and _new not in _inc.columns: _inc=_inc.rename(columns={_old:_new})
                _inc['Year']=pd.to_numeric(_inc.get('Year',_inc.get('season_year',0)),errors='coerce').fillna(0).astype(int)
                _inc['Team']=_inc.get('Team',pd.Series(['']*len(_inc))).astype(str).str.strip()
                _inc['StarRating']=pd.to_numeric(_inc.get('StarRating',0),errors='coerce').fillna(0).astype(int)
                _team_inc=_inc[(_inc['Team']==team)&(_inc['Year']==target_year)].sort_values('StarRating',ascending=False)
            else:
                _team_inc=pd.DataFrame()
        except: _team_inc=pd.DataFrame()
        # Ideal class blurb
        _needs_str=""
        try:
            if not _t_ros.empty and _yr_c2:
                _pos_need=_srs['POS'].astype(str).str.upper().str.strip().value_counts().head(3)
                _skill_need=[p for p in _pos_need.index if p in _SKILL]
                if _skill_need: _needs_str="Needs: "+", ".join(_skill_need[:3])
        except: pass
        # BCR context
        _bcr_str=""
        try:
            _bcr_f2=f'bluechip_ratio_{target_year}.csv'
            if os.path.exists(_bcr_f2):
                _bcr2=pd.read_csv(_bcr_f2); _bcr2['TEAM']=_bcr2['TEAM'].astype(str).str.strip()
                _bcr_col2=next((c for c in _bcr2.columns if any(x in c.upper() for x in ('BCR','BLUE','RATIO','CHIP','PERCENT'))),None)
                if _bcr_col2:
                    _br=_bcr2[_bcr2['TEAM']==team]
                    if not _br.empty:
                        _bv=float(str(_br.iloc[0][_bcr_col2]).replace('%','') or 0)
                        _bcr_str=f"BCR {_bv:.0f}% · "+("🔴 Need elite recruits" if _bv<25 else ("🟡 Target 4-5★" if _bv<50 else "🟢 Elite BCR"))
        except: pass
        # Breakdown line
        _bp=[]
        if d["nfl_count"]>0: _bp.append(f"{d['nfl_count']} NFL exit{'s' if d['nfl_count']!=1 else ''}")
        if d["transfer_count"]>0: _bp.append(f"{d['transfer_count']} transfer{'s' if d['transfer_count']!=1 else ''} out")
        if _sr_count>0: _bp.append(f"{_sr_count} senior{'s' if _sr_count!=1 else ''} graduating")
        _bdown=", ".join(_bp) if _bp else "No confirmed departures yet"
        _in_count=len(_team_inc)
        _avg_star=int(round(_team_inc['StarRating'].mean())) if _in_count>0 and 'StarRating' in _team_inc.columns else 0
        # Build card
        with cols[ci%len(cols)]:
            card_html=(
                f"<div style='background:linear-gradient(135deg,{primary}15 0%,#0f172a 40%);"
                f"border:1px solid {primary}44;border-left:5px solid {primary};border-radius:12px;"
                f"padding:14px 16px;margin-bottom:8px;'>"
                f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:8px;'>"
                f"{lh}<div style='flex:1;'>"
                f"<div style='font-weight:900;color:{primary};font-size:.95rem;font-family:Barlow Condensed,sans-serif;'>{html.escape(team)}</div>"
                f"<div style='font-size:.68rem;color:#64748b;'>{html.escape(user)}</div>"
                f"</div>"
                f"<div style='text-align:right;'>"
                f"<div style='font-family:Bebas Neue,sans-serif;font-size:2rem;color:{d['tier_c']};line-height:1;'>{d['pts']}</div>"
                f"<div style='font-size:.55rem;color:#475569;text-transform:uppercase;letter-spacing:.05em;'>pts</div>"
                f"</div></div>"
                f"<div style='background:{d['tier_c']}22;border:1px solid {d['tier_c']}44;border-radius:6px;padding:4px 10px;text-align:center;'>"
                f"<span style='color:{d['tier_c']};font-weight:900;font-size:.78rem;font-family:Barlow Condensed,sans-serif;letter-spacing:.05em;'>"
                f"{d['tier_emoji']} {d['tier'].upper()}</span></div>"
                f"<div style='margin-top:6px;font-size:.62rem;color:#94a3b8;'>{_bdown}</div>"
                +( f"<div style='margin-top:3px;font-size:.62rem;color:#f87171;'>💔 <strong>Biggest loss:</strong> {html.escape(_biggest_loss)}</div>" if _biggest_loss else "" )
                +( f"<div style='margin-top:3px;font-size:.6rem;color:#fbbf24;'>📋 {html.escape(_needs_str)}</div>" if _needs_str else "" )
                +( f"<div style='margin-top:3px;font-size:.6rem;color:#60a5fa;'>💎 {html.escape(_bcr_str)}</div>" if _bcr_str else "" )
                +( f"<div style='margin-top:3px;font-size:.6rem;color:#4ade80;'>🎯 Class incoming: {_in_count} recruits"
                   +( f" · avg {_avg_star}★" if _avg_star else "" )+"</div>" if _in_count>0 else "" )
                +f"</div>"
            )
            st.markdown(card_html, unsafe_allow_html=True)
            if not _team_inc.empty:
                with st.expander(f"🎯 {team} {target_year} Incoming ({_in_count})"):
                    for _,_ir in _team_inc.iterrows():
                        _irn=str(_ir.get('Name','?')).strip(); _irp=str(_ir.get('Pos','?')).strip()
                        _irs=_safe_int(_ir.get('StarRating',_ir.get('Stars',_ir.get('star_rating',0))))
                        _irr=_safe_int(_ir.get('NationalRank',_ir.get('Natl_Rank',_ir.get('national_rank',0))))
                        _irt=str(_ir.get('RecruitType','HS')).strip()
                        _star_d="⭐"*_irs if _irs>0 else ""; _rank_d=f"#{_irr}" if _irr>0 else ""
                        _type_b=(f"<span style='background:#60a5fa22;color:#60a5fa;border-radius:3px;padding:1px 5px;font-size:.55rem;font-weight:700;'>{html.escape(_irt)}</span>"
                                 if _irt and _irt.upper()!='HS' else "")
                        st.markdown(
                            f"<div style='background:#06090f;border:1px solid #1e293b;border-left:3px solid {primary};"
                            f"border-radius:6px;padding:5px 10px;margin-bottom:3px;"
                            f"display:flex;align-items:center;justify-content:space-between;gap:8px;'>"
                            f"<div style='display:flex;align-items:center;gap:6px;'>"
                            f"<span style='background:{primary}33;color:{primary};border-radius:3px;padding:1px 5px;font-size:.58rem;font-weight:700;'>{html.escape(_irp)}</span>"
                            f"<span style='font-weight:700;color:#f1f5f9;font-size:.82rem;'>{html.escape(_irn)}</span>"
                            f"{_type_b}</div>"
                            f"<div style='display:flex;align-items:center;gap:4px;'>"
                            f"<span style='color:#fbbf24;font-size:.68rem;'>{_star_d}</span>"
                            f"<span style='color:#64748b;font-size:.6rem;'>{_rank_d}</span>"
                            f"</div></div>",
                            unsafe_allow_html=True
                        )
        ci+=1
    # Rating scale legend
    st.markdown("""
<div style='display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 16px;font-size:.65rem;'>
  <span style='background:#10b98120;color:#10b981;border:1px solid #10b98140;border-radius:4px;padding:2px 8px;'>✅ 0-4 Manageable</span>
  <span style='background:#f59e0b20;color:#f59e0b;border:1px solid #f59e0b40;border-radius:4px;padding:2px 8px;'>⚠️ 5-8 Hurting</span>
  <span style='background:#f9731620;color:#f97316;border:1px solid #f9731640;border-radius:4px;padding:2px 8px;'>🔥 9-12 Rebuilding</span>
  <span style='background:#ef444420;color:#ef4444;border:1px solid #ef444440;border-radius:4px;padding:2px 8px;'>💀 13+ Total Teardown</span>
</div>""", unsafe_allow_html=True)
    st.markdown("---")
    # ── DETAIL TABS ──────────────────────────────────────────────────
    # For upcoming year only seniors tab shown; others not yet available
    if target_year==CURRENT_YEAR+1:
        _at_tabs=st.tabs(["🎓 Departing Seniors","🎯 Incoming Recruits"])
        _tab_nfl=None; _tab_xfer=None; _tab_sr=0; _tab_inc=1
    else:
        _at_tabs=st.tabs(["🏈 NFL Draft Exits","🚪 Transfers Out","🎓 Departing Seniors","🎯 Incoming Recruits"])
        _tab_nfl=0; _tab_xfer=1; _tab_sr=2; _tab_inc=3
    if _tab_nfl is not None:
     with _at_tabs[_tab_nfl]:
        st.subheader(f"🏈 {target_year} NFL Draft Exits")
        if draft_raw.empty:
            st.info("No draft data for current year."); 
        else:
            _tc=next((c for c in ('CollegeTeam','Team','TEAM') if c in draft_raw.columns),None)
            _user_draft=draft_raw[draft_raw[_tc].astype(str).str.strip().isin(ALL_USER_TEAMS)] if _tc else pd.DataFrame()
            if _user_draft.empty: st.info("No user team players in draft data.")
            else:
                for _,dr in _user_draft.sort_values('DraftRound').iterrows():
                    team=str(dr.get(_tc,'')).strip()
                    player=str(dr.get('Player','?')).strip(); pos=str(dr.get('Pos','?')).strip()
                    rnd=int(safe_num(dr.get('DraftRound',8),8))
                    ovr=int(safe_num(dr.get('OVR',0),0)); cls=str(dr.get('Class','?')).strip()
                    primary=get_team_primary_color(team)
                    logo=get_school_logo_src(team)
                    lh=f"<img src='{logo}' style='width:20px;height:20px;object-fit:contain;vertical-align:middle;margin-right:6px;'/>" if logo else ""
                    rnd_c="#fbbf24" if rnd==1 else ("#60a5fa" if rnd<=3 else "#94a3b8")
                    rnd_bg=f"background:{rnd_c}20;border:1px solid {rnd_c}40;"
                    st.markdown(f"""
<div style='background:#06090f;border:1px solid #1e293b;border-left:3px solid {primary};
    border-radius:8px;padding:8px 12px;margin-bottom:4px;display:flex;align-items:center;
    justify-content:space-between;flex-wrap:wrap;gap:6px;'>
  <div style='display:flex;align-items:center;gap:6px;'>
    {lh}<span style='font-weight:900;color:#f1f5f9;font-family:Barlow Condensed,sans-serif;font-size:.9rem;'>{html.escape(player)}</span>
    <span style='background:{primary}33;color:{primary};border-radius:3px;padding:1px 5px;font-size:.6rem;font-weight:700;'>{pos}</span>
    <span style='font-size:.65rem;color:#64748b;'>{ovr} OVR · {cls}</span>
  </div>
  <div style='display:flex;align-items:center;gap:6px;'>
    <span style='font-size:.68rem;color:#64748b;'>{html.escape(team)}</span>
    <span style='{rnd_bg}border-radius:4px;padding:2px 7px;font-size:.65rem;font-weight:700;color:{rnd_c};'>Rd {rnd}</span>
  </div>
</div>""", unsafe_allow_html=True)
    if _tab_xfer is not None:
     with _at_tabs[_tab_xfer]:
        st.subheader(f"🚪 {target_year} Transfers Out")
        if xf_raw.empty:
            st.info("No transfer data for current year.")
        else:
            _tc2=next((c for c in ('Team','TEAM') if c in xf_raw.columns),None)
            _user_xf=xf_raw[xf_raw[_tc2].astype(str).str.strip().isin(ALL_USER_TEAMS)] if _tc2 else pd.DataFrame()
            if _user_xf.empty: st.info("No user team transfers found.")
            else:
                _user_xf_sorted=_user_xf.copy()
                _user_xf_sorted['OVR']=pd.to_numeric(_user_xf_sorted['OVR'],errors='coerce').fillna(0)
                _user_xf_sorted=_user_xf_sorted.sort_values('OVR',ascending=False)
                for _,xr in _user_xf_sorted.iterrows():
                    team=str(xr.get(_tc2,'')).strip(); player=str(xr.get('Player','?')).strip()
                    pos=str(xr.get('Pos','?')).strip(); ovr=int(safe_num(xr.get('OVR',0),0))
                    reason=str(xr.get('ReasonDetail',xr.get('Reason','?'))).strip(); cls=str(xr.get('Class','?')).strip()
                    primary=get_team_primary_color(team); logo=get_school_logo_src(team)
                    lh=f"<img src='{logo}' style='width:20px;height:20px;object-fit:contain;vertical-align:middle;margin-right:6px;'/>" if logo else ""
                    ovr_c="#fbbf24" if ovr>=88 else ("#94a3b8" if ovr>=80 else "#475569")
                    st.markdown(f"""
<div style='background:#06090f;border:1px solid #1e293b;border-left:3px solid {primary};
    border-radius:8px;padding:8px 12px;margin-bottom:4px;display:flex;align-items:center;
    justify-content:space-between;flex-wrap:wrap;gap:6px;'>
  <div style='display:flex;align-items:center;gap:6px;'>
    {lh}<span style='font-weight:900;color:#f1f5f9;font-family:Barlow Condensed,sans-serif;font-size:.9rem;'>{html.escape(player)}</span>
    <span style='background:{primary}33;color:{primary};border-radius:3px;padding:1px 5px;font-size:.6rem;font-weight:700;'>{pos}</span>
    <span style='color:{ovr_c};font-size:.65rem;font-weight:700;'>{ovr} OVR</span>
    <span style='font-size:.62rem;color:#475569;'>{cls}</span>
  </div>
  <div style='display:flex;align-items:center;gap:6px;'>
    <span style='font-size:.65rem;color:#64748b;'>{html.escape(team)}</span>
    <span style='font-size:.62rem;color:#475569;font-style:italic;'>{html.escape(reason)}</span>
  </div>
</div>""", unsafe_allow_html=True)
    with _at_tabs[_tab_sr]:
        st.subheader(f"🎓 {target_year} Departing Seniors")
        st.caption("Seniors who exhaust eligibility after the current season.")
        try:
            # Always use CURRENT_YEAR roster — 2043 seniors ARE the 2044 off-season departures
            _ros_yr=CURRENT_YEAR
            _ros_file=f'cfb_136_top30_rosters_{_ros_yr}.csv'
            _ros_fallback='cfb26_rosters_full.csv'
            _rdf=pd.DataFrame()
            for rf in [_ros_file,_ros_fallback]:
                if os.path.exists(rf):
                    _rdf=pd.read_csv(rf); break
            if _rdf.empty: st.info("No roster data found."); return
            _rdf.columns=[str(c).strip() for c in _rdf.columns]
            # Normalise TEAM column regardless of capitalisation in CSV
            _tc=next((c for c in _rdf.columns if c.upper()=='TEAM'),None)
            if _tc is None: st.info("No TEAM column in roster CSV."); return
            if _tc!='TEAM': _rdf=_rdf.rename(columns={_tc:'TEAM'})
            _rdf['TEAM']=_rdf['TEAM'].astype(str).str.strip()
            # Filter to current year rows when YEAR column present
            if 'YEAR' in _rdf.columns:
                _rdf['YEAR']=pd.to_numeric(_rdf['YEAR'],errors='coerce')
                _rdf=_rdf[_rdf['YEAR'].fillna(-1).astype(int)==_ros_yr]
            _rdf['OVR']=pd.to_numeric(_rdf['OVR'],errors='coerce').fillna(0)
            _yr_col=next((c for c in ('YEAR_CLASS','Class','CLASS','Year') if c in _rdf.columns),None)
            if not _yr_col: st.info("No class/year column in roster."); return
            _user_ros=_rdf[_rdf['TEAM'].isin(ALL_USER_TEAMS)].copy()
            _all_seniors=_user_ros[_user_ros[_yr_col].astype(str).apply(is_senior_label)].copy()
            if _all_seniors.empty: st.info("No departing seniors found in roster data."); return
            # Team dropdown
            _sr_teams=sorted(_all_seniors['TEAM'].unique().tolist())
            _sr_team_sel=st.selectbox("Select team",["All User Teams"]+_sr_teams,key="sr_team_sel")
            if _sr_team_sel=="All User Teams":
                _seniors=_all_seniors.sort_values(['TEAM','OVR'],ascending=[True,False])
            else:
                _seniors=_all_seniors[_all_seniors['TEAM']==_sr_team_sel].sort_values('OVR',ascending=False)
            st.caption(f"{len(_seniors)} departing senior{'s' if len(_seniors)!=1 else ''} {'across all user teams' if _sr_team_sel=='All User Teams' else f'for {_sr_team_sel}'}")
            for _,sr in _seniors.iterrows():
                team=str(sr['TEAM'])
                nm_col=next((c for c in ('NAME','Name','PLAYER') if c in sr.index),'NAME')
                player=str(sr.get(nm_col,'?')).strip()
                pos=str(sr.get('POS',sr.get('Pos','?'))).strip()
                ovr=int(sr['OVR']); cls=str(sr.get(_yr_col,'?')).strip()
                primary=get_team_primary_color(team)
                logo=get_school_logo_src(team)
                lh=f'<img src="{logo}" style="width:20px;height:20px;object-fit:contain;vertical-align:middle;margin-right:6px;"/>' if logo else ''
                ovr_c="#fbbf24" if ovr>=88 else ("#94a3b8" if ovr>=80 else "#475569")
                card=(
                    f"<div style='background:#06090f;border:1px solid #1e293b;border-left:3px solid {primary};"
                    f"border-radius:8px;padding:8px 12px;margin-bottom:4px;display:flex;align-items:center;"
                    f"justify-content:space-between;flex-wrap:wrap;gap:6px;'>"
                    f"<div style='display:flex;align-items:center;gap:6px;'>"
                    f"{lh}"
                    f"<span style='font-weight:900;color:#f1f5f9;font-family:Barlow Condensed,sans-serif;font-size:.9rem;'>{html.escape(player)}</span>"
                    f"<span style='background:{primary}33;color:{primary};border-radius:3px;padding:1px 5px;font-size:.6rem;font-weight:700;'>{pos}</span>"
                    f"<span style='color:{ovr_c};font-size:.65rem;font-weight:700;'>{ovr} OVR</span>"
                    f"</div>"
                    f"<div style='display:flex;align-items:center;gap:6px;'>"
                    f"<span style='font-size:.68rem;color:#64748b;'>{html.escape(team)}</span>"
                    f"<span style='font-size:.62rem;color:#475569;'>{html.escape(cls)}</span>"
                    f"</div></div>"
                )
                st.markdown(card, unsafe_allow_html=True)
        except Exception as e:
            st.caption(f"Departing seniors unavailable: {e}")

    with _at_tabs[_tab_inc]:
        st.subheader(f"🎯 {target_year} Incoming Recruiting Class")
        try:
            _inc_df=pd.read_csv('attrition_incoming.csv') if os.path.exists('attrition_incoming.csv') else pd.DataFrame()
            if _inc_df.empty:
                st.info("No attrition_incoming.csv found. Drop the file in the repo.")
            else:
                _inc_df.columns=[str(c).strip() for c in _inc_df.columns]
                for _o2,_n2 in [('season_year','Year'),('YEAR','Year'),('team','Team'),('TEAM','Team'),('Stars','StarRating'),('star_rating','StarRating'),('Natl_Rank','NationalRank'),('national_rank','NationalRank'),('recruit_type','RecruitType'),('pos','Pos'),('POS','Pos'),('name','Name'),('NAME','Name')]:
                    if _o2 in _inc_df.columns and _n2 not in _inc_df.columns: _inc_df=_inc_df.rename(columns={_o2:_n2})
                _inc_df['Year']=pd.to_numeric(_inc_df.get('Year',0),errors='coerce').fillna(0).astype(int)
                _inc_df['Team']=_inc_df.get('Team',pd.Series(['']*len(_inc_df))).astype(str).str.strip()
                _inc_df['StarRating']=pd.to_numeric(_inc_df.get('StarRating',0),errors='coerce').fillna(0).astype(int)
                # Use target_year directly — 2043 attrition = 2043 incoming class
                _inc_show=_inc_df[_inc_df['Year']==target_year].copy()
                if _inc_show.empty:
                    st.info(f"No incoming recruits data for year {_inc_yr}.")
                else:
                    _inc_teams=sorted(_inc_show['Team'].unique())
                    _inc_sel=st.selectbox("Team",["All User Teams"]+_inc_teams,key="inc_tab_team")
                    _inc_filtered=_inc_show if _inc_sel=="All User Teams" else _inc_show[_inc_show['Team']==_inc_sel]
                    _inc_filtered=_inc_filtered.sort_values(['Team','StarRating'],ascending=[True,False])
                    st.caption(f"{len(_inc_filtered)} incoming recruits")
                    for _,_ir in _inc_filtered.iterrows():
                        _irn=str(_ir.get('Name','?')).strip(); _irp=str(_ir.get('Pos','?')).strip()
                        _irt=str(_ir.get('Team','?')).strip()
                        _irs=int(_ir.get('StarRating',0) or 0); _irr=int(_ir.get('NationalRank',0) or 0)
                        _irtype=str(_ir.get('RecruitType','HS')).strip()
                        _pc=get_team_primary_color(_irt)
                        _tlg=get_school_logo_src(_irt)
                        _tlh=f"<img src='{_tlg}' style='width:18px;height:18px;object-fit:contain;vertical-align:middle;margin-right:4px;'/>" if _tlg else ""
                        _type_b=(f"<span style='background:#60a5fa22;color:#60a5fa;border-radius:3px;padding:1px 5px;font-size:.55rem;font-weight:700;'>{html.escape(_irtype)}</span>" if _irtype.upper()!='HS' else "")
                        st.markdown(
                            f"<div style='background:#06090f;border:1px solid #1e293b;border-left:3px solid {_pc};"
                            f"border-radius:6px;padding:6px 12px;margin-bottom:3px;"
                            f"display:flex;align-items:center;justify-content:space-between;gap:8px;'>"
                            f"<div style='display:flex;align-items:center;gap:6px;'>"
                            f"{_tlh}"
                            f"<span style='background:{_pc}33;color:{_pc};border-radius:3px;padding:1px 5px;font-size:.6rem;font-weight:700;'>{html.escape(_irp)}</span>"
                            f"<span style='font-weight:700;color:#f1f5f9;font-family:Barlow Condensed,sans-serif;font-size:.88rem;'>{html.escape(_irn)}</span>"
                            f"{_type_b}</div>"
                            f"<div style='display:flex;align-items:center;gap:6px;'>"
                            f"<span style='color:#fbbf24;font-size:.7rem;'>{"⭐"*_irs}</span>"
                            f"<span style='color:#64748b;font-size:.62rem;'>{"#"+str(_irr) if _irr else ""}</span>"
                            f"</div></div>",
                            unsafe_allow_html=True
                        )
        except Exception as e:
            st.caption(f"Incoming recruits unavailable: {e}")

def render_roster_matchup_tab():
    import plotly.graph_objects as go

    st.header("🎯 Roster Matchup Analyzer")
    st.caption("Full depth charts, positional battles, injury resilience, redshirt-aware eligibility, and future value pipeline analysis.")

    try:
        _rm_yr_file=f'cfb_136_top30_rosters_{CURRENT_YEAR}.csv'
        if os.path.exists(_rm_yr_file):
            roster=pd.read_csv(_rm_yr_file)
        else:
            roster=pd.read_csv('cfb26_rosters_full.csv')
        # Normalise column names: TEAM->Team, POS->Pos, NAME->Name, YEAR_CLASS->Class, etc.
        _col_norm={'TEAM':'Team','POS':'Pos','NAME':'Name','PLAYER':'Name',
                   'YEAR_CLASS':'Class','YEAR':'Season','SPD':'Spd','ACC':'Acc',
                   'AGI':'Agi','COD':'COD','STR':'Str','AWR':'Awr','OVR':'OVR',
                   'REDSHIRT':'REDSHIRT','ARCHETYPE':'Archetype','HEIGHT':'Height',
                   'WEIGHT':'Weight','HOMETOWN':'Hometown'}
        _actual_renames={k:v for k,v in _col_norm.items() if k in roster.columns and v not in roster.columns}
        if _actual_renames:
            roster=roster.rename(columns=_actual_renames)
        # Ensure Season column exists (used for year filtering)
        if 'Season' not in roster.columns and 'Class' in roster.columns:
            roster['Season']=CURRENT_YEAR
        elif 'Season' not in roster.columns:
            roster['Season']=CURRENT_YEAR
    except Exception:
        try:
            roster=pd.read_csv('cfb26_rosters_top30.csv')
            st.info("Using top-30 roster data.")
        except Exception as e2:
            st.error(f"Could not load roster data: {e2}")
            return

    # Filter to current season only -- without this every player appears
    # once per year they've been in the CSV (e.g. both their JR and SR rows show up)
    if 'Season' in roster.columns:
        roster['Season'] = pd.to_numeric(roster['Season'], errors='coerce')
        _avail_seasons = sorted(roster['Season'].dropna().astype(int).unique())
        _target_season = CURRENT_YEAR if CURRENT_YEAR in _avail_seasons else (
            max(_avail_seasons) if _avail_seasons else CURRENT_YEAR
        )
        roster = roster[roster['Season'].fillna(-1).astype(int) == int(_target_season)].copy()

    teams = sorted([t for t in roster['Team'].unique().tolist() if t in ALL_USER_TEAMS])
    if not teams: teams = sorted(roster['Team'].unique().tolist())

    # Default Team A and Team B to the 2 user teams with highest Natty Odds
    _matchup_default_a, _matchup_default_b = 0, 1
    try:
        _natty_col_m = 'Natty Odds' if 'Natty Odds' in model_2041.columns else 'Preseason Natty Odds'
        _top_natty = (
            model_2041[['TEAM', _natty_col_m]]
            .dropna()
            .sort_values(_natty_col_m, ascending=False)
        )
        _user_team_vals = list(USER_TEAMS.values())
        _top_user = _top_natty[_top_natty['TEAM'].isin(_user_team_vals)]['TEAM'].tolist()
        if len(_top_user) >= 2:
            _ta = _top_user[0]; _tb = _top_user[1]
            if _ta in teams: _matchup_default_a = teams.index(_ta)
            if _tb in teams: _matchup_default_b = teams.index(_tb)
    except Exception:
        pass

    POS_GROUPS = {
        "QB":            ["QB"],
        "Backfield":     ["HB", "FB"],
        "Pass Catchers": ["WR", "TE"],
        "O-Line":        ["LT", "LG", "C", "RG", "RT"],
        "D-Line":        ["DT", "LEDG", "REDG"],
        "Linebackers":   ["MIKE", "WILL", "SAM"],
        "Secondary":     ["CB", "FS", "SS"],
    }
    ATTRS = ["OVR", "SPD", "ACC", "AGI", "COD", "STR", "AWR"]

    col1, col2 = st.columns(2)
    with col1:
        team_a = st.selectbox("🏈 Team A", teams, index=_matchup_default_a, key="matchup_team_a")
    with col2:
        team_b = st.selectbox("🏈 Team B", teams, index=_matchup_default_b, key="matchup_team_b")

    if team_a == team_b:
        st.warning("Select two different teams to see a comparison.")
        return

    roster_a = roster[roster['Team'] == team_a].copy()
    roster_b = roster[roster['Team'] == team_b].copy()
    color_a  = get_team_primary_color(team_a)
    color_b  = get_team_primary_color(team_b)

    logo_uri_a  = image_file_to_data_uri(get_logo_source(team_a))
    logo_uri_b  = image_file_to_data_uri(get_logo_source(team_b))
    logo_html_a = f"<img src='{logo_uri_a}' style='width:72px;height:72px;object-fit:contain;display:block;margin:0 auto 6px auto;'/>" if logo_uri_a else "<div style='font-size:48px;text-align:center;'>🏈</div>"
    logo_html_b = f"<img src='{logo_uri_b}' style='width:72px;height:72px;object-fit:contain;display:block;margin:0 auto 6px auto;'/>" if logo_uri_b else "<div style='font-size:48px;text-align:center;'>🏈</div>"

    # ── YEAR / REDSHIRT HELPERS ──────────────────────────────────────────────
    def parse_year_info(yr_str):
        """
        Returns (base_class, is_redshirt, yrs_in_program, eligibility_remaining)
        Eligibility: FR=4, SO=3, JR=2, SR=1  |  RS adds 1 yr in program, not eligibility
        FR(RS)  = in program 2 yrs, 4 eligibility yrs left (hasn't burned one yet)
        SO(RS)  = in program 3 yrs, 3 eligibility yrs left
        JR(RS)  = in program 4 yrs, 2 eligibility yrs left
        SR(RS)  = in program 5 yrs, 1 eligibility yr  left (grad year)
        """
        s = str(yr_str).upper().strip()
        is_rs = "(RS)" in s
        base = s.replace("(RS)", "").strip()
        elig_map = {"FR": 4, "SO": 3, "JR": 2, "SR": 1}
        prog_map  = {"FR": 1, "SO": 2, "JR": 3, "SR": 4}
        elig = elig_map.get(base, 2)
        prog = prog_map.get(base, 2) + (1 if is_rs else 0)
        label_map = {"FR": "Freshman", "SO": "Sophomore", "JR": "Junior", "SR": "Senior"}
        label = label_map.get(base, "Unknown")
        return label, is_rs, prog, elig

    def enrich_roster(df):
        df = df.copy()
        _yr_col2=next((c for c in ('Year','Class','YEAR_CLASS','CLASS') if c in df.columns),'Year')
        if _yr_col2 not in df.columns: df[_yr_col2]='FR'
        parsed = df[_yr_col2].apply(parse_year_info)
        df['YrClass']   = parsed.apply(lambda x: x[0])
        df['IsRS']      = parsed.apply(lambda x: x[1])
        df['YrsInProg'] = parsed.apply(lambda x: x[2])
        df['EligLeft']  = parsed.apply(lambda x: x[3])

        # Future Value Score:
        # OVR at current age weighted by years remaining + athleticism upside
        # Athletes with high SPD/ACC/AGI but moderate OVR = high ceiling (they just need reps)
        # Formula: OVR * 0.55 + AthlScore * 0.25 + EligLeft * 3.0
        # AthlScore = avg of SPD, ACC, AGI, COD
        for _sc in ('SPD','ACC','AGI','COD','OVR','STR'):
            if _sc not in df.columns: df[_sc]=pd.to_numeric(df.get(_sc.title(),df.get(_sc.lower(),0)),errors='coerce').fillna(0)
            else: df[_sc]=pd.to_numeric(df[_sc],errors='coerce').fillna(0)
        for _sc2 in ('SPD','ACC','AGI','COD','OVR'):
            if _sc2 not in df.columns:
                df[_sc2]=pd.to_numeric(df.get(_sc2.lower(),df.get(_sc2.title(),0)),errors='coerce').fillna(0)
            else:
                df[_sc2]=pd.to_numeric(df[_sc2],errors='coerce').fillna(0)
        df['AthlScore'] = (df['SPD'] + df['ACC'] + df['AGI'] + df['COD']) / 4.0
        df['FV'] = (df['OVR'] * 0.55 + df['AthlScore'] * 0.25 + df['EligLeft'] * 3.0).round(1)

        # Ceiling flag: young + high athleticism but OVR not yet caught up
        df['HighCeiling'] = (df['EligLeft'] >= 3) & (df['AthlScore'] >= 82) & (df['OVR'] < 85)

        # Experience tag for display
        def exp_tag(row):
            rs_tag = "🔴" if row['IsRS'] else ""
            return f"{row['YrClass']}{rs_tag} ({row['EligLeft']}yr left)"
        df['ExpTag'] = df.apply(exp_tag, axis=1)

        return df

    roster_a = enrich_roster(roster_a)
    roster_b = enrich_roster(roster_b)
    

    # ── TEAM HEADER ──────────────────────────────────────────────────────────
    h1, hm, h2 = st.columns([5, 1, 5])
    h1.markdown(f"<div style='text-align:center;padding:12px 0;'>{logo_html_a}<span style='color:{color_a};font-size:1.4rem;font-weight:900;'>{team_a}</span></div>", unsafe_allow_html=True)
    hm.markdown("<div style='text-align:center;padding-top:28px;color:#6b7280;font-size:1.5rem;font-weight:700;'>vs</div>", unsafe_allow_html=True)
    h2.markdown(f"<div style='text-align:center;padding:12px 0;'>{logo_html_b}<span style='color:{color_b};font-size:1.4rem;font-weight:900;'>{team_b}</span></div>", unsafe_allow_html=True)

    # ── MAIN TABS ────────────────────────────────────────────────────────────
    tab_overview, tab_depth, tab_resilience, tab_class, tab_pipeline = st.tabs([
        "📊 Athletic Profile",
        "📋 Depth Chart",
        "🩺 Injury Resilience",
        "🎓 Roster Composition",
        "🚀 Future Value",
    ])

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1 -- ATHLETIC PROFILE
    # ════════════════════════════════════════════════════════════════════════
    with tab_overview:
        def team_summary(df):
            for _tc in ('AWR','SPD','ACC','AGI','COD','STR','OVR'):
                if _tc not in df.columns: df[_tc]=pd.to_numeric(df.get(_tc.lower(),df.get(_tc.title(),0)),errors='coerce').fillna(0)
                else: df[_tc]=pd.to_numeric(df[_tc],errors='coerce').fillna(0)
            return {
                "Avg OVR":       round(df["OVR"].mean(), 1),
                "Top OVR":       int(df["OVR"].max()),
                "90+ OVR Count": int((df["OVR"] >= 90).sum()),
                "Avg SPD":       round(df["SPD"].mean(), 1),
                "90+ SPD Count": int((df["SPD"] >= 90).sum()),
                "Avg AGI":       round(df["AGI"].mean(), 1),
                "Avg AWR":       round(df["AWR"].mean(), 1),
                "Roster Size":   len(df),
            }

        summ_a = team_summary(roster_a)
        summ_b = team_summary(roster_b)

        # Positional battles
        st.markdown("---")
        st.subheader("⚔️ Positional Battle Breakdown")
        st.caption("Top 3 players per group. Composite score = 70% OVR + 30% Speed.")
        group_results = []
        for group_name, positions in POS_GROUPS.items():
            grp_a = roster_a[roster_a["Pos"].isin(positions)].nlargest(3, "OVR")
            grp_b = roster_b[roster_b["Pos"].isin(positions)].nlargest(3, "OVR")
            if grp_a.empty and grp_b.empty:
                continue
            score_a = round((grp_a["OVR"].mean() if not grp_a.empty else 0) * 0.70 + (grp_a["SPD"].mean() if not grp_a.empty else 0) * 0.30, 1)
            score_b = round((grp_b["OVR"].mean() if not grp_b.empty else 0) * 0.70 + (grp_b["SPD"].mean() if not grp_b.empty else 0) * 0.30, 1)
            margin = abs(score_a - score_b)
            winner_team  = team_a if score_a >= score_b else team_b
            winner_color = color_a if score_a >= score_b else color_b
            group_results.append({"group": group_name, "winner": winner_team if margin >= 0.5 else "EVEN", "margin": margin, "score_a": score_a, "score_b": score_b})
            if margin < 0.5:    plain_label = f"{group_name}  --  = EVEN"
            elif margin < 2.0:  plain_label = f"{group_name}  --  Slight Edge: {winner_team}"
            elif margin < 4.0:  plain_label = f"{group_name}  --  Edge: {winner_team} ✅"
            else:               plain_label = f"{group_name}  --  BIG ADVANTAGE: {winner_team} 🔥"
            with st.expander(plain_label, expanded=False):
                if margin < 0.5:
                    st.markdown("🟰 <span style='color:#9ca3af;'>EVEN</span>", unsafe_allow_html=True)
                else:
                    badge_weight = "900" if margin >= 4.0 else ("700" if margin >= 2.0 else "400")
                    st.markdown(f"<span style='color:{winner_color};font-weight:{badge_weight};'>{'BIG ADVANTAGE' if margin >= 4.0 else ('EDGE' if margin >= 2.0 else 'SLIGHT EDGE')}: {html.escape(winner_team)}{' 🔥' if margin >= 4.0 else ''}</span>", unsafe_allow_html=True)
                sc1, sc2, sc3 = st.columns([2, 3, 2])
                sc1.metric(f"{team_a} Score", score_a)
                sc3.metric(f"{team_b} Score", score_b)
                sc2.markdown("<div style='text-align:center;padding-top:0.6rem;color:#6b7280;font-size:0.8rem;'>composite score</div>", unsafe_allow_html=True)
                pa, pb = st.columns(2)
                _want = ["Name","Pos","Year","OVR","SPD","ACC","AGI","STR","AWR"]
                disp_cols = [c for c in _want if c in roster_a.columns or c in roster_b.columns]
                sm_logo_a = f"<img src='{logo_uri_a}' style='width:28px;height:28px;object-fit:contain;vertical-align:middle;margin-right:6px;'/>" if logo_uri_a else "🏈 "
                sm_logo_b = f"<img src='{logo_uri_b}' style='width:28px;height:28px;object-fit:contain;vertical-align:middle;margin-right:6px;'/>" if logo_uri_b else "🏈 "
                with pa:
                    st.markdown(f"<div style='display:flex;align-items:center;gap:6px;margin-bottom:4px;'>{sm_logo_a}<span style='color:{color_a};font-weight:800;font-size:0.95rem;'>{team_a}</span></div>", unsafe_allow_html=True)
                    if not grp_a.empty:
                        _dc_a=[c for c in disp_cols if c in grp_a.columns]
                        st.dataframe(grp_a[_dc_a].reset_index(drop=True), hide_index=True, use_container_width=True)
                    else:
                        st.caption("No players.")
                with pb:
                    st.markdown(f"<div style='display:flex;align-items:center;gap:6px;margin-bottom:4px;'>{sm_logo_b}<span style='color:{color_b};font-weight:800;font-size:0.95rem;'>{team_b}</span></div>", unsafe_allow_html=True)
                    if not grp_b.empty:
                        _dc_b=[c for c in disp_cols if c in grp_b.columns]
                        st.dataframe(grp_b[_dc_b].reset_index(drop=True), hide_index=True, use_container_width=True)
                    else:
                        st.caption("No players.")

        st.markdown("---")
        st.subheader("📊 Athletic Comparison Chart")

        team_metric_map = {
            team_a: {
                "Players 90+ Speed": summ_a["90+ SPD Count"],
                "Roster Avg Speed": summ_a["Avg SPD"],
                "Roster Avg Overall": summ_a["Avg OVR"],
                "Best Player Overall": summ_a["Top OVR"],
                "Players 90+ Overall": summ_a["90+ OVR Count"],
                "Roster Avg Awareness": summ_a["Avg AWR"],
                "Roster Avg Agility": summ_a["Avg AGI"],
            },
            team_b: {
                "Players 90+ Speed": summ_b["90+ SPD Count"],
                "Roster Avg Speed": summ_b["Avg SPD"],
                "Roster Avg Overall": summ_b["Avg OVR"],
                "Best Player Overall": summ_b["Top OVR"],
                "Players 90+ Overall": summ_b["90+ OVR Count"],
                "Roster Avg Awareness": summ_b["Avg AWR"],
                "Roster Avg Agility": summ_b["Avg AGI"],
            }
        }

        render_team_athletic_profile_plotly(team_metric_map)

        

        # Scorecard
        st.markdown("---")
        st.subheader("🏟️ Battle Scorecard")
        wins_a = sum(1 for r in group_results if r["winner"] == team_a)
        wins_b = sum(1 for r in group_results if r["winner"] == team_b)
        ties   = sum(1 for r in group_results if r["winner"] == "EVEN")
        total  = len(group_results)
        sc1, sc2, sc3 = st.columns(3)
        sc1.markdown(f"<div style='text-align:center;'>{logo_html_a}<span style='font-size:0.8rem;color:{color_a};font-weight:700;'>{team_a}</span></div>", unsafe_allow_html=True)
        sc1.metric("Group Wins", wins_a)
        sc2.metric("Even Matchups", ties)
        sc3.markdown(f"<div style='text-align:center;'>{logo_html_b}<span style='font-size:0.8rem;color:{color_b};font-weight:700;'>{team_b}</span></div>", unsafe_allow_html=True)
        sc3.metric("Group Wins", wins_b)

        # Scouting report
        st.markdown("---")
        st.subheader("📋 Scouting Report")
        adv_a = sorted([r for r in group_results if r["winner"] == team_a], key=lambda x: x["margin"], reverse=True)
        adv_b = sorted([r for r in group_results if r["winner"] == team_b], key=lambda x: x["margin"], reverse=True)
        lines = []
        if adv_a:
            lines.append(f"**{team_a}** has the roster advantage at **{', '.join([r['group'] for r in adv_a[:2]])}**{' and ' + str(len(adv_a)-2) + ' more groups' if len(adv_a) > 2 else ''}.")
        if adv_b:
            lines.append(f"**{team_b}** counters with the edge at **{', '.join([r['group'] for r in adv_b[:2]])}**{' and ' + str(len(adv_b)-2) + ' more groups' if len(adv_b) > 2 else ''}.")
        spd_a, spd_b = summ_a["90+ SPD Count"], summ_b["90+ SPD Count"]
        if spd_a > spd_b + 1:
            lines.append(f"The speed gap is real -- **{team_a}** has **{spd_a}** players at 90+ SPD vs {team_b}'s **{spd_b}**.")
        elif spd_b > spd_a + 1:
            lines.append(f"**{team_b}** brings the burners -- **{spd_b}** players at 90+ SPD vs {team_a}'s **{spd_a}**.")
        else:
            lines.append(f"Speed depth is essentially equal -- **{spd_a}** vs **{spd_b}** players at 90+ SPD.")
        awr_a, awr_b = summ_a["Avg AWR"], summ_b["Avg AWR"]
        if abs(awr_a - awr_b) >= 3:
            smarter = team_a if awr_a > awr_b else team_b
            lines.append(f"**{smarter}** has the awareness edge ({max(awr_a, awr_b)} avg AWR) -- fewer blown assignments, faster reads.")
        for r in [r for r in adv_a if r["margin"] >= 4]:
            lines.append(f"The **{r['group']}** unit for **{team_a}** is a genuine mismatch.")
        for r in [r for r in adv_b if r["margin"] >= 4]:
            lines.append(f"**{team_b}** has a dominant edge at **{r['group']}**.")
        if wins_a > wins_b:
            verdict_team, verdict_color, verdict_desc = team_a, color_a, f"wins {wins_a} of {total} positional battles"
        elif wins_b > wins_a:
            verdict_team, verdict_color, verdict_desc = team_b, color_b, f"wins {wins_b} of {total} positional battles"
        else:
            verdict_team, verdict_color, verdict_desc = "Neither team", "#9ca3af", "-- this matchup is an absolute coin flip on paper"
        for line in lines:
            st.markdown(line)
        st.markdown(f"""<div style="padding:1rem 1.25rem;border-left:6px solid {verdict_color};background:{verdict_color}18;border-radius:8px;margin-top:1rem;"><strong>Roster Verdict:</strong> <span style="color:{verdict_color};font-size:1.05rem;font-weight:800;">{html.escape(verdict_team)}</span> {verdict_desc}. Paper never plays the game, but this one matters.</div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2 -- DEPTH CHART
    # ════════════════════════════════════════════════════════════════════════
    with tab_depth:
        st.subheader("📋 Full Depth Chart Comparison")
        st.caption("True 2-deep by position. 🔄 = redshirt. EligLeft = eligibility years remaining.")
        ALL_POSITIONS = {
            "Quarterback": ["QB"], "Halfback": ["HB", "FB"], "Wide Receiver": ["WR"],
            "Tight End": ["TE"], "Left Tackle": ["LT"], "Left Guard": ["LG"],
            "Center": ["C"], "Right Guard": ["RG"], "Right Tackle": ["RT"],
            "Defensive Tackle": ["DT"], "Left Edge": ["LEDG"], "Right Edge": ["REDG"],
            "MIKE LB": ["MIKE"], "WILL LB": ["WILL"], "SAM LB": ["SAM"],
            "Cornerback": ["CB"], "Free Safety": ["FS"], "Strong Safety": ["SS"],
        }
        for pos_label, pos_codes in ALL_POSITIONS.items():
            grp_a = roster_a[roster_a["Pos"].isin(pos_codes)].sort_values("OVR", ascending=False).reset_index(drop=True)
            grp_b = roster_b[roster_b["Pos"].isin(pos_codes)].sort_values("OVR", ascending=False).reset_index(drop=True)

            def fmt_player(df, idx):
                if len(df) > idx:
                    r = df.iloc[idx]
                    rs_tag = " 🔄" if r['IsRS'] else ""
                    return f"{r['Name']}{rs_tag} ({r['EligLeft']}yr) | {int(r['OVR'])} OVR / {int(r['SPD'])} SPD"
                return "--"

            st_a, bk_a = fmt_player(grp_a, 0), fmt_player(grp_a, 1)
            st_b, bk_b = fmt_player(grp_b, 0), fmt_player(grp_b, 1)
            ovr_a = grp_a.iloc[0]["OVR"] if len(grp_a) > 0 else 0
            ovr_b = grp_b.iloc[0]["OVR"] if len(grp_b) > 0 else 0
            edge = "A" if ovr_a > ovr_b + 1 else ("B" if ovr_b > ovr_a + 1 else "=")
            if edge == "A":   edge_html = f"<span style='color:{color_a};font-weight:700;font-size:0.75rem;'>▶ {team_a}</span>"
            elif edge == "B": edge_html = f"<span style='color:{color_b};font-weight:700;font-size:0.75rem;'>{team_b} ◀</span>"
            else:             edge_html = "<span style='color:#9ca3af;font-size:0.75rem;'>EVEN</span>"

            with st.expander(f"**{pos_label}**  |  {('▶ ' + team_a) if edge == 'A' else ((team_b + ' ◀') if edge == 'B' else 'Even')}", expanded=False):
                ca, cm, cb = st.columns([5, 2, 5])
                with ca:
                    st.markdown(f"<span style='color:{color_a};font-weight:700;font-size:0.85rem;'>{team_a}</span>", unsafe_allow_html=True)
                    st.markdown(f"**Starter:** {st_a}")
                    st.markdown(f"<span style='color:#9ca3af;font-size:0.8rem;'>Backup: {bk_a}</span>", unsafe_allow_html=True)
                with cm:
                    st.markdown(f"<div style='text-align:center;padding-top:1.2rem;'>{edge_html}</div>", unsafe_allow_html=True)
                with cb:
                    st.markdown(f"<span style='color:{color_b};font-weight:700;font-size:0.85rem;'>{team_b}</span>", unsafe_allow_html=True)
                    st.markdown(f"**Starter:** {st_b}")
                    st.markdown(f"<span style='color:#9ca3af;font-size:0.8rem;'>Backup: {bk_b}</span>", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 3 -- INJURY RESILIENCE
    # ════════════════════════════════════════════════════════════════════════
    with tab_resilience:
        st.subheader("🩺 Injury Resilience Score")
        st.caption("Score drop when each group's best player is removed. 🟢 Solid depth  🟡 Some risk 🔴 One injury from disaster.")

        def resilience_score(df, positions):
            grp = df[df["Pos"].isin(positions)].nlargest(5, "OVR")
            if grp.empty:
                return 0, 0, None
            with_star   = grp["OVR"].mean() * 0.70 + grp["SPD"].mean() * 0.30
            star_row    = grp.iloc[0]
            without     = grp.iloc[1:]
            without_star = (without["OVR"].mean() * 0.70 + without["SPD"].mean() * 0.30) if not without.empty else 0
            drop = round(with_star - without_star, 1)
            rs_tag = " 🔄" if star_row['IsRS'] else ""
            elig_tag = f"({int(star_row['EligLeft'])}yr left)"
            return round(with_star, 1), drop, f"{star_row['Name']}{rs_tag} {elig_tag} | {int(star_row['OVR'])} OVR"

        hdr_cols = st.columns([3, 2, 2, 1, 2, 2])
        for col, label in zip(hdr_cols, ["Position Group", f"{team_a} Star", f"{team_a} Drop", "vs", f"{team_b} Star", f"{team_b} Drop"]):
            col.markdown(f"**{label}**")
        st.markdown("---")

        total_drop_a, total_drop_b = 0, 0
        for group_name, positions in POS_GROUPS.items():
            w_a, drop_a, star_a = resilience_score(roster_a, positions)
            w_b, drop_b, star_b = resilience_score(roster_b, positions)
            total_drop_a += drop_a
            total_drop_b += drop_b
            dc_a = "#ef4444" if drop_a >= 5 else ("#f59e0b" if drop_a >= 2.5 else "#22c55e")
            dc_b = "#ef4444" if drop_b >= 5 else ("#f59e0b" if drop_b >= 2.5 else "#22c55e")
            row_cols = st.columns([3, 2, 2, 1, 2, 2])
            row_cols[0].markdown(f"**{group_name}**")
            row_cols[1].markdown(f"<span style='font-size:0.78rem;color:#d1d5db;'>{star_a or '--'}</span>", unsafe_allow_html=True)
            row_cols[2].markdown(f"<span style='color:{dc_a};font-weight:700;'>-{drop_a}</span>", unsafe_allow_html=True)
            row_cols[3].markdown("<div style='text-align:center;color:#6b7280;'>|</div>", unsafe_allow_html=True)
            row_cols[4].markdown(f"<span style='font-size:0.78rem;color:#d1d5db;'>{star_b or '--'}</span>", unsafe_allow_html=True)
            row_cols[5].markdown(f"<span style='color:{dc_b};font-weight:700;'>-{drop_b}</span>", unsafe_allow_html=True)

        st.markdown("---")
        r1, r2, r3 = st.columns([3, 1, 3])
        with r1:
            st.markdown(f"<div style='text-align:center;'>{logo_html_a}</div>", unsafe_allow_html=True)
            st.metric(f"{team_a} Total Fragility", f"-{round(total_drop_a, 1)}", help="Lower = more resilient")
        with r3:
            st.markdown(f"<div style='text-align:center;'>{logo_html_b}</div>", unsafe_allow_html=True)
            st.metric(f"{team_b} Total Fragility", f"-{round(total_drop_b, 1)}", help="Lower = more resilient")
        more_fragile  = team_a if total_drop_a > total_drop_b else team_b
        more_resilient = team_b if total_drop_a > total_drop_b else team_a
        res_color = color_a if total_drop_a > total_drop_b else color_b
        st.markdown(f"""<div style="padding:0.8rem 1.25rem;border-left:5px solid {res_color};background:{res_color}15;border-radius:8px;margin-top:0.8rem;font-size:0.9rem;"><strong>{html.escape(more_fragile)}</strong> is more depth-dependent. <strong>{html.escape(more_resilient)}</strong> has the more resilient roster if stars go down.</div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 4 -- ROSTER COMPOSITION
    # ════════════════════════════════════════════════════════════════════════
    with tab_class:
        st.subheader("🎓 Roster Composition Breakdown")
        st.markdown(
            f"<div style='color:#9ca3af; font-size:0.875rem; margin-top:-6px; margin-bottom:8px;'>"
            f"Class distribution with redshirt-aware eligibility. "
            f"{get_redshirt_logo_html(width=16, margin='0 4px -3px 4px')} = currently redshirting."
            f"</div>",
            unsafe_allow_html=True
        )

        def class_breakdown(df):
            total = len(df)
            rs_count   = int(df['IsRS'].sum())
            elig_avg   = round(df['EligLeft'].mean(), 1)
            young      = int((df['EligLeft'] >= 3).sum())
            veteran    = int((df['EligLeft'] <= 2).sum())
            class_counts = df['YrClass'].value_counts()
            return {
                "Freshmen": class_counts.get("Freshman", 0),
                "Sophomores": class_counts.get("Sophomore", 0),
                "Juniors": class_counts.get("Junior", 0),
                "Seniors": class_counts.get("Senior", 0),
                "Total": total,
                "Redshirts": rs_count,
                "Avg Elig": elig_avg,
                "Young (3-4yr elig)": young,
                "Veteran (1-2yr elig)": veteran,
            }

        cb_a = class_breakdown(roster_a)
        cb_b = class_breakdown(roster_b)

        classes = ["Freshmen", "Sophomores", "Juniors", "Seniors"]
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(name=team_a, x=classes, y=[cb_a[c] for c in classes], marker_color=color_a, opacity=0.85))
        fig2.add_trace(go.Bar(name=team_b, x=classes, y=[cb_b[c] for c in classes], marker_color=color_b, opacity=0.85))
        fig2.update_layout(barmode="group", height=320, margin=dict(t=30, b=30, l=20, r=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig2, use_container_width=True, config={'staticPlot': True})

        mobile_metrics([
            {"label": f"{team_a} Redshirts", "value": str(cb_a["Redshirts"])},
            {"label": f"{team_a} Avg Elig",  "value": str(cb_a["Avg Elig"])},
            {"label": f"{team_a} Young",     "value": str(cb_a["Young (3-4yr elig)"])},
            {"label": f"{team_b} Redshirts", "value": str(cb_b["Redshirts"])},
            {"label": f"{team_b} Avg Elig",  "value": str(cb_b["Avg Elig"])},
            {"label": f"{team_b} Young",     "value": str(cb_b["Young (3-4yr elig)"])},
        ], cols_desktop=6)

        st.markdown("---")
        st.markdown("#### 🌟 Top Young Talent (3-4 eligibility years remaining)")
        young_cols = ["Name", "Pos", "ExpTag", "OVR", "SPD", "FV"]
        young_a = roster_a[roster_a["EligLeft"] >= 3].nlargest(8, "OVR")[young_cols].reset_index(drop=True)
        young_b = roster_b[roster_b["EligLeft"] >= 3].nlargest(8, "OVR")[young_cols].reset_index(drop=True)
        yc1, yc2 = st.columns(2)
        with yc1:
            st.markdown(f"<span style='color:{color_a};font-weight:800;'>{team_a}</span>", unsafe_allow_html=True)
            st.dataframe(young_a.rename(columns={"ExpTag": "Status", "FV": "FV Score"}), hide_index=True, use_container_width=True)
        with yc2:
            st.markdown(f"<span style='color:{color_b};font-weight:800;'>{team_b}</span>", unsafe_allow_html=True)
            st.dataframe(young_b.rename(columns={"ExpTag": "Status", "FV": "FV Score"}), hide_index=True, use_container_width=True)

        st.markdown("#### 🏆 Senior Leaders (final year)")
        vets_a = roster_a[roster_a["EligLeft"] == 1].nlargest(6, "OVR")[["Name", "Pos", "ExpTag", "OVR", "SPD", "AWR"]].reset_index(drop=True)
        vets_b = roster_b[roster_b["EligLeft"] == 1].nlargest(6, "OVR")[["Name", "Pos", "ExpTag", "OVR", "SPD", "AWR"]].reset_index(drop=True)
        vc1, vc2 = st.columns(2)
        with vc1:
            st.markdown(f"<span style='color:{color_a};font-weight:800;'>{team_a}</span>", unsafe_allow_html=True)
            if not vets_a.empty:
                st.dataframe(vets_a.rename(columns={"ExpTag": "Status"}), hide_index=True, use_container_width=True)
            else:
                st.caption("No seniors.")
        with vc2:
            st.markdown(f"<span style='color:{color_b};font-weight:800;'>{team_b}</span>", unsafe_allow_html=True)
            if not vets_b.empty:
                st.dataframe(vets_b.rename(columns={"ExpTag": "Status"}), hide_index=True, use_container_width=True)
            else:
                st.caption("No seniors.")

        # Redshirt breakdown
        st.markdown("---")
        st.markdown(
            f"#### {get_redshirt_logo_html(width=18, margin='0 6px -3px 0')} Redshirt Inventory",
            unsafe_allow_html=True
        )
        st.caption("Redshirts = players who gained a year in the program without burning eligibility. These players have more development than their class label suggests.")
        rs_a = roster_a[roster_a['IsRS']].sort_values("OVR", ascending=False)[["Name", "Pos", "ExpTag", "OVR", "SPD", "FV"]].reset_index(drop=True)
        rs_b = roster_b[roster_b['IsRS']].sort_values("OVR", ascending=False)[["Name", "Pos", "ExpTag", "OVR", "SPD", "FV"]].reset_index(drop=True)
        rc1, rc2 = st.columns(2)
        with rc1:
            st.markdown(
                f"<span style='color:{color_a};font-weight:800;'>{team_a} -- "
                f"{get_redshirt_logo_html(width=16, margin='0 4px -3px 4px')} {len(rs_a)} redshirts</span>",
                unsafe_allow_html=True
            )
            if not rs_a.empty:
                st.dataframe(rs_a.rename(columns={"ExpTag": "Status", "FV": "FV Score"}), hide_index=True, use_container_width=True)
            else:
                st.caption("No redshirts.")
        with rc2:
            st.markdown(
                f"<span style='color:{color_b};font-weight:800;'>{team_b} -- "
                f"{get_redshirt_logo_html(width=16, margin='0 4px -3px 4px')} {len(rs_b)} redshirts</span>",
                unsafe_allow_html=True
            )
            if not rs_b.empty:
                st.dataframe(rs_b.rename(columns={"ExpTag": "Status", "FV": "FV Score"}), hide_index=True, use_container_width=True)
            else:
                st.caption("No redshirts.")

    # ════════════════════════════════════════════════════════════════════════
    # TAB 5 -- FUTURE VALUE / PIPELINE
    # ════════════════════════════════════════════════════════════════════════
    with tab_pipeline:
        st.subheader("🚀 Future Value & Pipeline Analysis")
        st.caption("Future Value (FV) = OVR x 0.55 + Athleticism x 0.25 + Eligibility Years x 3.0. High FV + low OVR = high-ceiling athlete who hasn't peaked yet. 🌠 = High Ceiling flag (young + 82+ athleticism + sub-85 OVR).")

        # FV scatter plot: OVR vs FV, bubble size = SPD
        fv_cols = ["Name", "Pos", "ExpTag", "OVR", "SPD", "AthlScore", "EligLeft", "FV", "HighCeiling"]

        fig3 = go.Figure()
        for df, color, name in [(roster_a, color_a, team_a), (roster_b, color_b, team_b)]:
            ceiling_mask = df["HighCeiling"]
            # Regular players
            reg = df[~ceiling_mask]
            fig3.add_trace(go.Scatter(
                x=reg["OVR"], y=reg["FV"],
                mode="markers",
                name=name,
                marker=dict(color=color, size=reg["SPD"].apply(lambda s: max(6, int((s-60)/3))), opacity=0.65, line=dict(width=0)),
                text=reg.apply(lambda r: f"{r['Name']} ({r['Pos']}) | {int(r['EligLeft'])}yr left | FV:{r['FV']}", axis=1),
                hoverinfo="text",
            ))
            # High ceiling players
            ceil_players = df[ceiling_mask]
            if not ceil_players.empty:
                fig3.add_trace(go.Scatter(
                    x=ceil_players["OVR"], y=ceil_players["FV"],
                    mode="markers+text",
                    name=f"{name} 🌠 High Ceiling",
                    marker=dict(color=color, size=14, symbol="star", line=dict(width=1.5, color="white")),
                    text=ceil_players["Name"],
                    textposition="top center",
                    textfont=dict(size=9, color=color),
                    hovertext=ceil_players.apply(lambda r: f"{r['Name']} ({r['Pos']}) | {int(r['EligLeft'])}yr left | FV:{r['FV']}", axis=1),
                    hoverinfo="text",
                ))

        fig3.update_layout(
            xaxis_title="Current OVR", yaxis_title="Future Value Score",
            height=460, margin=dict(t=40, b=40, l=40, r=40),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="#374151"), yaxis=dict(gridcolor="#374151"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        )
        st.plotly_chart(fig3, use_container_width=True, config={'staticPlot': True})
        st.caption("Bubble size = Speed rating. Stars (🌠) = High Ceiling players. Upper-left quadrant = low OVR but high future value -- the gems.")

        # Top 10 FV players each team
        st.markdown("---")
        st.markdown("#### 🏆 Top 10 Future Value Players")
        fv_disp = ["Name", "Pos", "ExpTag", "OVR", "SPD", "AthlScore", "EligLeft", "FV", "HighCeiling"]
        top_fv_a = roster_a.nlargest(10, "FV")[fv_disp].reset_index(drop=True)
        top_fv_b = roster_b.nlargest(10, "FV")[fv_disp].reset_index(drop=True)
        top_fv_a["HighCeiling"] = top_fv_a["HighCeiling"].apply(lambda x: "🌠" if x else "")
        top_fv_b["HighCeiling"] = top_fv_b["HighCeiling"].apply(lambda x: "🌠" if x else "")
        fv1, fv2 = st.columns(2)
        with fv1:
            st.markdown(f"<span style='color:{color_a};font-weight:800;'>{team_a}</span>", unsafe_allow_html=True)
            st.dataframe(top_fv_a.rename(columns={"ExpTag": "Status", "AthlScore": "Athl", "EligLeft": "Elig", "HighCeiling": "🌠"}), hide_index=True, use_container_width=True)
        with fv2:
            st.markdown(f"<span style='color:{color_b};font-weight:800;'>{team_b}</span>", unsafe_allow_html=True)
            st.dataframe(top_fv_b.rename(columns={"ExpTag": "Status", "AthlScore": "Athl", "EligLeft": "Elig", "HighCeiling": "🌠"}), hide_index=True, use_container_width=True)

        # High ceiling sleepers specifically
        st.markdown("---")
        st.markdown("#### 🌠 High Ceiling Sleepers")
        st.caption("Young athletes (3-4yr eligibility) with elite athleticism (82+ avg SPD/ACC/AGI/COD) but current OVR still under 85. These are the breakout candidates.")
        sleepers_a = roster_a[roster_a["HighCeiling"]].sort_values("FV", ascending=False)[["Name", "Pos", "ExpTag", "OVR", "SPD", "AthlScore", "EligLeft", "FV"]].reset_index(drop=True)
        sleepers_b = roster_b[roster_b["HighCeiling"]].sort_values("FV", ascending=False)[["Name", "Pos", "ExpTag", "OVR", "SPD", "AthlScore", "EligLeft", "FV"]].reset_index(drop=True)
        sl1, sl2 = st.columns(2)
        with sl1:
            st.markdown(f"<span style='color:{color_a};font-weight:800;'>{team_a} -- {len(sleepers_a)} sleepers</span>", unsafe_allow_html=True)
            if not sleepers_a.empty:
                st.dataframe(sleepers_a.rename(columns={"ExpTag": "Status", "AthlScore": "Athl", "EligLeft": "Elig"}), hide_index=True, use_container_width=True)
            else:
                st.caption("No high-ceiling sleepers found.")
        with sl2:
            st.markdown(f"<span style='color:{color_b};font-weight:800;'>{team_b} -- {len(sleepers_b)} sleepers</span>", unsafe_allow_html=True)
            if not sleepers_b.empty:
                st.dataframe(sleepers_b.rename(columns={"ExpTag": "Status", "AthlScore": "Athl", "EligLeft": "Elig"}), hide_index=True, use_container_width=True)
            else:
                st.caption("No high-ceiling sleepers found.")

        # Pipeline summary
        st.markdown("---")
        avg_fv_a = round(roster_a["FV"].mean(), 1)
        avg_fv_b = round(roster_b["FV"].mean(), 1)
        ceiling_a = int(roster_a["HighCeiling"].sum())
        ceiling_b = int(roster_b["HighCeiling"].sum())
        better_pipeline = team_a if avg_fv_a > avg_fv_b else team_b
        pipeline_color  = color_a if avg_fv_a > avg_fv_b else color_b
        st.markdown(f"""<div style="padding:0.9rem 1.25rem;border-left:6px solid {pipeline_color};background:{pipeline_color}15;border-radius:8px;font-size:0.92rem;">
        <strong>Pipeline Verdict:</strong> <span style="color:{pipeline_color};font-weight:800;">{html.escape(better_pipeline)}</span> has the stronger future value roster
        (avg FV: <strong>{avg_fv_a}</strong> vs <strong>{avg_fv_b}</strong>). High-ceiling sleepers: <strong style="color:{color_a};">{team_a} {ceiling_a}</strong> vs <strong style="color:{color_b};">{team_b} {ceiling_b}</strong>.
        The team with more sleepers is one progression cycle away from a significant talent jump.
        </div>""", unsafe_allow_html=True)


# ── AUTO-SYNC: Derive CFP/natty stats and write back to CSVs ─────────────────



def mobile_metrics(metrics, cols_desktop=4):
    """Responsive metric card grid. Auto-reflows on mobile."""
    cards_html=""
    for m in metrics:
        label=html.escape(str(m.get("label","")))
        value=html.escape(str(m.get("value","")))
        delta=m.get("delta",None)
        delta_html=""
        if delta is not None:
            ds=str(delta)
            dcm=m.get("delta_color","normal")
            is_pos=ds.startswith("+") or (not ds.startswith("-") and ds not in ["0","0.0","0%"])
            dc=("#9ca3af" if dcm=="off" else
                ("#f87171" if is_pos else "#4ade80") if dcm=="inverse" else
                ("#4ade80" if is_pos else "#f87171"))
            arrow="&#9650;" if is_pos else "&#9660;"
            delta_html=f"<div style='font-size:.72rem;color:{dc};font-weight:600;margin-top:2px;'>{arrow} {html.escape(ds)}</div>"
        cards_html+=(
            "<div style='background:#1f2937;border:1px solid #374151;border-radius:10px;"
            "padding:10px 12px;min-width:0;'>"
            f"<div style='font-size:.72rem;color:#9ca3af;font-weight:600;text-transform:uppercase;"
            f"letter-spacing:.04em;margin-bottom:4px;white-space:nowrap;overflow:hidden;"
            f"text-overflow:ellipsis;'>{label}</div>"
            f"<div style='font-size:1.15rem;font-weight:800;color:#f3f4f6;line-height:1.2;'>{value}</div>"
            f"{delta_html}</div>"
        )
    st.markdown(
        f"<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));"
        f"gap:8px;margin-bottom:1rem;'>{cards_html}</div>",
        unsafe_allow_html=True
    )

def send_score_email(user, team, user_score, opp_score, opp_name, week, year, status):
    """
    Send score notification email to commissioner.
    Reads credentials from st.secrets:
        [email]
        sender = "dynasty_bot@gmail.com"
        password = "app_password_here"
        recipient = "mike@example.com"
    Falls back to a mailto: link if secrets not configured.
    """
    subject=f"ISPN Score Update — {user} ({team}) Wk {week} {year}"
    body=(f"Score submitted by {user} ({team})\n"
          f"Week {week}, {year}\n"
          f"Result: {team} {user_score} — {opp_name} {opp_score}\n"
          f"Status: {status}\n"
          f"\nSubmitted via ISPN Dynasty App")
    try:
        import smtplib
        from email.mime.text import MIMEText
        _s=st.secrets.get("email",{})
        sender=_s.get("sender","")
        password=_s.get("password","")
        recipient=_s.get("recipient","")
        if sender and password and recipient:
            msg=MIMEText(body)
            msg['Subject']=subject
            msg['From']=sender
            msg['To']=recipient
            with smtplib.SMTP_SSL('smtp.gmail.com',465) as smtp:
                smtp.login(sender,password)
                smtp.sendmail(sender,recipient,msg.as_string())
            return True,"📧 Score sent to Mike!"
        else:
            # Secrets not configured — return mailto fallback
            import urllib.parse
            _encoded_body=urllib.parse.quote(body)
            _encoded_subj=urllib.parse.quote(subject)
            _mailto=f"mailto:{recipient or 'commissioner@ispn.com'}?subject={_encoded_subj}&body={_encoded_body}"
            return False,_mailto
    except Exception as e:
        return False,str(e)


def get_redshirt_logo_path():
    for path in ["REDSHIRT.png","logos/REDSHIRT.png",
                 "/mount/src/cfb_dynasty_app/REDSHIRT.png",
                 "/mount/src/cfb_dynasty_app/logos/REDSHIRT.png"]:
        try:
            if os.path.exists(path): return path
        except: pass
    return ""

def get_redshirt_logo_html(width=18, margin="0 4px -3px 4px"):
    try:
        path=get_redshirt_logo_path()
        if path:
            uri=image_file_to_data_uri(path)
            if uri: return f'<img src="{uri}" width="{width}" style="margin:{margin};vertical-align:middle;">'
    except: pass
    return "🔴"

def get_redshirt_logo_src():
    try:
        path=get_redshirt_logo_path()
        if path: return image_file_to_data_uri(path)
    except: pass
    return None

def render_team_athletic_profile_plotly(team_metric_map):
    if not team_metric_map:
        st.caption("No athletic profile data available.")
        return
    metric_order=["Players 90+ Speed","Roster Avg Speed","Roster Avg Overall",
        "Best Player Overall","Players 90+ Overall","Roster Avg Awareness","Roster Avg Agility"]
    first_team=list(team_metric_map.keys())[0]
    categories=[m for m in metric_order if m in team_metric_map[first_team]]
    if not categories:
        st.caption("No athletic profile metrics available."); return
    all_vals=[float(team_metric_map[t].get(c,0)) for t in team_metric_map for c in categories]
    if not all_vals: st.caption("No athletic profile values available."); return
    min_val=min(all_vals); max_val=max(all_vals)
    axis_floor=max(0,int(min_val)-3)
    axis_ceiling=min(100,int(max_val)+3) if max_val<=100 else int(max_val)+2
    fig=go.Figure()
    for team,metrics in team_metric_map.items():
        tc=TEAM_VISUALS.get(team,{}).get("primary","#38bdf8")
        vals=[float(metrics.get(c,0)) for c in categories]
        fig.add_trace(go.Bar(y=categories,x=vals,name=team,orientation="h",
            marker=dict(color=tc),
            text=[f"{v:.1f}" if isinstance(v,float) and not v.is_integer() else f"{int(v)}" for v in vals],
            textposition="outside",
            hovertemplate=f"<b>{team}</b><br>%{{y}}: %{{x}}<extra></extra>"))
    fig.update_layout(barmode="group",height=520,
        paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),margin=dict(l=20,r=40,t=20,b=20),
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="left",x=0),
        xaxis=dict(title="Value",range=[axis_floor,axis_ceiling],
            gridcolor="rgba(255,255,255,0.10)",zeroline=False),
        yaxis=dict(title="",autorange="reversed"))
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False,"staticPlot":True})

# ══════════════════════════════════════════════════════════════════════
# MAIN APP -- LOAD DATA + BUILD TICKER + RENDER TABS
# ══════════════════════════════════════════════════════════════════════
import time as _time
_time_now=_time.strftime("%I:%M %p")
time_display=_time_now

# Load main data
(scores, stats_df, h2h_df, h2h_heat, rivalry_df, 
 model_2041, champs, draft, heisman, coty, all_users) = load_data(CURRENT_YEAR)

# Alias for functions that reference model_df
model_df = model_2041

# Build USER_TEAMS from model if available, else use constants
if model_2041 is not None and not model_2041.empty and 'USER' in model_2041.columns and 'TEAM' in model_2041.columns:
    _u_teams_from_model={str(r['USER']).strip().title():str(r['TEAM']).strip()
        for _,r in model_2041[['USER','TEAM']].drop_duplicates().iterrows()
        if str(r['USER']).strip() and str(r['USER']).strip().lower() not in ('nan','')}
    _valid_users={k:v for k,v in _u_teams_from_model.items() if k in USER_TEAMS}
    if _valid_users: pass  # USER_TEAMS already set correctly

# also need user_draft_results_df alias for natty DNA
user_draft_results_df = draft.copy() if draft is not None and not draft.empty else pd.DataFrame()

# ── BUILD TICKER ─────────────────────────────────────────────────────
_ticker_headlines=build_ticker_items(CURRENT_YEAR, CURRENT_WEEK_NUMBER, IS_BOWL_WEEK)
_top=_ticker_headlines[0]

# ── HERO HEADER ─────────────────────────────────────────────────────
def _colorize_hl(text):
    escaped=html.escape(str(text)).upper()
    team_names=sorted(TEAM_VISUALS.keys(),key=len,reverse=True)
    if not team_names: return escaped
    pattern=re.compile(r'(?<![A-Z0-9])('+'|'.join(re.escape(t.upper()) for t in team_names)+r')(?![A-Z0-9])')
    def _safe_c(tn):
        c=TEAM_VISUALS.get(tn,{}).get('primary','#fbbf24')
        try:
            r,g,b=int(c[1:3],16),int(c[3:5],16),int(c[5:7],16)
            if 0.299*r+0.587*g+0.114*b<60: c=f'#{min(255,r+80):02x}{min(255,g+80):02x}{min(255,b+80):02x}'
        except: pass
        return c
    cmap={t.upper():_safe_c(t) for t in team_names}
    def repl(m):
        tu=m.group(1); col=cmap.get(tu,'#fbbf24')
        return f"<span style='color:{col};font-weight:900;'>{tu}</span>"
    return pattern.sub(repl,escaped)

_hero_html=_colorize_hl(_top['text'])
_logo_html=''
try:
    if 'logo_html' in _top: _logo_html=_top['logo_html']
    else:
        # try to find natty champ logo for hero
        _ct=re.search(r'CHAMPIONS -- (.+)$',_top['text'])
        if _ct:
            _ct_team=_ct.group(1).title()
            _cl=image_file_to_data_uri(get_logo_source(_ct_team))
            if _cl: _logo_html=f"<div style='text-align:center;margin-bottom:8px;'><img src='{_cl}' style='width:72px;height:72px;object-fit:contain;filter:drop-shadow(0 0 12px gold);'/></div>"
except: pass

st.markdown(f"""
<style>
@keyframes subtle-pulse{{0%,100%{{opacity:.8;transform:scale(1);}}50%{{opacity:1;transform:scale(1.03);}}}}
@keyframes live-blink{{0%,100%{{opacity:1;}}50%{{opacity:.4;}}}}
.top-story-badge{{display:inline-block;background:#f59e0b;color:#451a03;padding:2px 8px;
    border-radius:4px;font-size:.65rem;font-weight:900;margin-bottom:6px;
    animation:subtle-pulse 3s infinite ease-in-out;letter-spacing:1px;}}
.live-indicator{{animation:live-blink 2s infinite ease-in-out;color:#38bdf8;font-weight:900;}}
</style>
<div style="margin-top:-75px;margin-bottom:0;text-align:center;">
  <h2 style="margin-bottom:10px;font-weight:800;letter-spacing:-.5px;">📰 Dynasty News</h2>
  {_logo_html}
  {("" if _top.get('badge')=='CFP TOP 4' else f'<div class="top-story-badge">{html.escape(_top["badge"])}</div>')}
  <div style="font-size:1.15rem;font-weight:800;letter-spacing:.5px;margin-bottom:4px;line-height:1.4;">{"" if _top.get('badge')=='CFP TOP 4' else _hero_html}</div>
  <div style="color:#94a3b8;font-size:.85rem;font-style:italic;max-width:500px;margin:0 auto;">"{html.escape(_top['blurb'])}"</div>
  <div style="color:#38bdf8;font-size:.65rem;margin-top:8px;letter-spacing:1px;font-weight:800;">
    <span class="live-indicator">●</span> LIVE UPDATE: {time_display} ET
  </div>
</div>
""", unsafe_allow_html=True)

render_ticker(_ticker_headlines)

# ══════════════════════════════════════════════════════════════════════
# TAB STRUCTURE
# ══════════════════════════════════════════════════════════════════════
tabs=st.tabs([
    "🗞️ Dynasty News",        # tabs[0]
    "📊 Rankings & Metrics",  # tabs[1]
    "📋 Roster Attrition",    # tabs[2]
    "📺 Season Recap",        # tabs[3]
    "🏆 User Legacies",       # tabs[4]
    "🎯 Roster Matchup",      # tabs[5]
])

# ══════════════════════════════════════════════════════════════════════
# TAB 0 -- DYNASTY NEWS
# ══════════════════════════════════════════════════════════════════════
with tabs[0]:
    render_status_banner(CURRENT_YEAR, CURRENT_WEEK_NUMBER, IS_BOWL_WEEK)
    render_game_cards_with_boxscore(CURRENT_YEAR, CURRENT_WEEK_NUMBER, model_2041)

    # ── COMMISSIONER TOOLS ────────────────────────────────────────────────────
    _gs_week = CURRENT_WEEK_NUMBER
    _gs_year = CURRENT_YEAR

    # Load matchup data for controls
    _ctrl_matchup = {}
    try:
        _sf2=f'schedule_{_gs_year}.csv'
        if os.path.exists(_sf2):
            _rs2=pd.read_csv(_sf2,dtype={'YEAR':str,'Week':str})
            _rs2.columns=[str(c).strip() for c in _rs2.columns]
            _yc2=next((c for c in ('YEAR','Year') if c in _rs2.columns),None)
            _wc2=next((c for c in ('Week','WEEK') if c in _rs2.columns),None)
            _ym2=str(int(_gs_year)); _wm2=str(int(_gs_week))
            _yo2=_rs2[_yc2].astype(str).str.strip().str.split('.').str[0]==_ym2 if _yc2 else pd.Series([True]*len(_rs2))
            _wo2=_rs2[_wc2].astype(str).str.strip().str.split('.').str[0]==_wm2 if _wc2 else pd.Series([True]*len(_rs2))
            _sc2=_rs2[_yo2&_wo2].copy()
            for tc in ('Visitor','Home'):
                if tc in _sc2.columns: _sc2[tc]=_sc2[tc].astype(str).apply(lambda t:re.sub(r'\d+\s+','',t.strip()))
            _vc3=next((c for c in ('Visitor','VISITOR') if c in _sc2.columns),None)
            _hc3=next((c for c in ('Home','HOME') if c in _sc2.columns),None)
            _vsc3=next((c for c in ('Vis Score','Vis_Score') if c in _sc2.columns),None)
            _hsc3=next((c for c in ('Home Score','Home_Score') if c in _sc2.columns),None)
            if _vc3: _sc2['_VL2']=_sc2[_vc3].astype(str).str.strip().str.lower()
            if _hc3: _sc2['_HL2']=_sc2[_hc3].astype(str).str.strip().str.lower()
            for user,team in USER_TEAMS.items():
                tl=team.lower()
                _vr3=_sc2[_sc2['_VL2']==tl] if '_VL2' in _sc2.columns else pd.DataFrame()
                _hr3=_sc2[_sc2['_HL2']==tl] if '_HL2' in _sc2.columns else pd.DataFrame()
                if not _vr3.empty:
                    gr3=_vr3.iloc[0]; opp3=str(gr3.get(_hc3,'')).strip() if _hc3 else '?'
                    _ctrl_matchup[user]={'opp':opp3,'home':False}
                elif not _hr3.empty:
                    gr3=_hr3.iloc[0]; opp3=str(gr3.get(_vc3,'')).strip() if _vc3 else '?'
                    _ctrl_matchup[user]={'opp':opp3,'home':True}
                else:
                    _ctrl_matchup[user]='BYE'
    except: pass

    _game_status_map2={}
    try:
        if os.path.exists('week_game_status.csv'):
            _wgs2=pd.read_csv('week_game_status.csv')
            _wgs2['Year']=pd.to_numeric(_wgs2.get('Year'),errors='coerce').fillna(0).astype(int)
            _wgs2['Week']=pd.to_numeric(_wgs2.get('Week'),errors='coerce').fillna(0).astype(int)
            _wc2=_wgs2[(_wgs2['Year']==int(_gs_year))&(_wgs2['Week']==int(_gs_week))].copy()
            if not _wc2.empty:
                _game_status_map2=dict(zip(_wc2['User'].astype(str).str.strip(),_wc2['Status'].astype(str).str.strip()))
    except: pass

    _msc_map2={}
    try:
        if os.path.exists('week_manual_scores.csv'):
            _mdf2=pd.read_csv('week_manual_scores.csv')
            for _c in ['Year','Week']:
                _mdf2[_c]=pd.to_numeric(_mdf2.get(_c),errors='coerce').fillna(0).astype(int)
            _mdf2c=_mdf2[(_mdf2['Year']==int(_gs_year))&(_mdf2['Week']==int(_gs_week))].copy()
            for _,_mr2 in _mdf2c.iterrows():
                _msc_map2[str(_mr2.get('User','')).strip()]={
                    'opp':str(_mr2.get('Opponent','')).strip(),
                    'user_score':int(pd.to_numeric(_mr2.get('UserScore',0),errors='coerce') or 0),
                    'opp_score':int(pd.to_numeric(_mr2.get('OppScore',0),errors='coerce') or 0),
                }
    except: pass

    st.markdown("---")
    with st.expander(f"⚙️ Commissioner Tools — Wk {_gs_week} {_gs_year}", expanded=False):
        _comm_unlocked=st.session_state.get("_comm_unlocked",False)
        if not _comm_unlocked:
            st.markdown("<div style='color:#475569;font-size:.8rem;margin-bottom:8px;'>🔒 Commissioner access only.</div>",unsafe_allow_html=True)
            _pw_col,_=st.columns([1.5,2])
            with _pw_col:
                _pw_input=st.text_input("Password",type="password",key="comm_pw_input",
                    label_visibility="collapsed",placeholder="Commissioner password")
            if _pw_input:
                if _pw_input=="Chicken83$":
                    st.session_state["_comm_unlocked"]=True; st.rerun()
                else: st.error("Wrong password.")
        else:
            _cap_col,_lock_col=st.columns([4,1])
            with _cap_col:
                st.caption(f"Admin controls — Week {_gs_week}, {_gs_year}.")
            with _lock_col:
                if st.button("🔒 Lock",key="comm_lock_btn",use_container_width=True):
                    st.session_state["_comm_unlocked"]=False; st.rerun()
            col_ref,_=st.columns([1,3])
            with col_ref:
                if st.button("🔄 Refresh Data",use_container_width=True,key="comm_refresh_data"):
                    st.cache_data.clear(); st.rerun()
            st.markdown(f"#### 🏈 Week {_gs_week} Game Status & Scores")
            st.caption("Enter scores to auto-set Ready. Download CSVs and push to GitHub.")
            _comb_scores={}; _comb_status={}
            for _cmu in list(USER_TEAMS.keys()):
                _cm=_ctrl_matchup.get(_cmu,'UNSCHEDULED')
                _cur_msc=_msc_map2.get(_cmu,{})
                _cur_st=_game_status_map2.get(_cmu,'Not Set')
                if _cm=='BYE':
                    c1,c2=st.columns([2,2])
                    with c1:
                        st.markdown(f"<span style='font-family:Barlow Condensed,sans-serif;font-weight:700;color:#e2e8f0;'>{html.escape(_cmu)} <span style='color:#475569;'>— BYE</span></span>",unsafe_allow_html=True)
                    with c2:
                        _comb_status[_cmu]=st.selectbox("Status",['Not Set','Ready'],
                            index=1 if _cur_st=='Ready' else 0,
                            key=f"cst_{_cmu}_{_gs_week}_{_gs_year}",label_visibility="collapsed")
                    _comb_scores[_cmu]=None
                elif isinstance(_cm,dict):
                    _cm_opp=_cm.get('opp','?'); _ha='vs' if _cm.get('home') else '@'
                    _ol=image_file_to_data_uri(get_logo_source(_cm_opp))
                    _ol_h=f"<img src='{_ol}' style='width:18px;height:18px;object-fit:contain;vertical-align:middle;margin-right:3px;'/>" if _ol else ""
                    st.markdown(f"<div style='font-family:Barlow Condensed,sans-serif;font-weight:700;font-size:.9rem;color:#94a3b8;margin:6px 0 2px 0;'><strong style='color:#e2e8f0;'>{html.escape(_cmu)}</strong> — {_ha} {_ol_h}{html.escape(_cm_opp)}</div>",unsafe_allow_html=True)
                    sc1,sc2,sc3=st.columns([1,1,2])
                    with sc1:
                        _us=st.number_input("Us",min_value=0,max_value=99,value=_cur_msc.get('user_score',0),
                            key=f"msu_{_cmu}_{_gs_week}_{_gs_year}",label_visibility="collapsed")
                    with sc2:
                        _os=st.number_input("Opp",min_value=0,max_value=99,value=_cur_msc.get('opp_score',0),
                            key=f"mso_{_cmu}_{_gs_week}_{_gs_year}",label_visibility="collapsed")
                    with sc3:
                        if _us>0 or _os>0:
                            _rl="W" if _us>_os else ("L" if _os>_us else "TIE")
                            _rc3="#4ade80" if _rl=="W" else ("#f87171" if _rl=="L" else "#94a3b8")
                            st.markdown(f"<span style='color:{_rc3};font-weight:800;font-family:Bebas Neue,sans-serif;font-size:1.1rem;'>{_rl} {_us}-{_os}</span>",unsafe_allow_html=True)
                        else:
                            _comb_status[_cmu]=st.selectbox("Status",['Not Set','Ready'],
                                index=1 if _cur_st=='Ready' else 0,
                                key=f"cst_{_cmu}_{_gs_week}_{_gs_year}",label_visibility="collapsed")
                    if _us>0 or _os>0: _comb_status[_cmu]='Ready'
                    _comb_scores[_cmu]={'opp':_cm_opp,'user_score':_us,'opp_score':_os}
                else:
                    c1,c2=st.columns([2,2])
                    with c1:
                        st.markdown(f"<span style='color:#334155;font-size:.9rem;'>{html.escape(_cmu)} — schedule pending</span>",unsafe_allow_html=True)
                    with c2:
                        _comb_status[_cmu]=st.selectbox("Status",['Not Set','Ready'],
                            index=1 if _cur_st=='Ready' else 0,
                            key=f"cst_{_cmu}_{_gs_week}_{_gs_year}",label_visibility="collapsed")
                    _comb_scores[_cmu]=None
            if st.button("💾 Save All",use_container_width=True,key="save_combined_btn",type="primary"):
                try:
                    _mb=pd.read_csv('week_manual_scores.csv') if os.path.exists('week_manual_scores.csv') else pd.DataFrame(columns=['User','Year','Week','Opponent','UserScore','OppScore'])
                    for _c in ['Year','Week']: _mb[_c]=pd.to_numeric(_mb.get(_c),errors='coerce').fillna(0).astype(int)
                    _mb=_mb[~((_mb['Year']==int(_gs_year))&(_mb['Week']==int(_gs_week)))].copy()
                    _save_rows=[{'User':_u,'Year':int(_gs_year),'Week':int(_gs_week),'Opponent':v['opp'],'UserScore':v['user_score'],'OppScore':v['opp_score']} for _u,v in _comb_scores.items() if v and (v['user_score']>0 or v['opp_score']>0)]
                    if _save_rows: pd.concat([_mb,pd.DataFrame(_save_rows)],ignore_index=True).to_csv('week_manual_scores.csv',index=False)
                    _wb=pd.read_csv('week_game_status.csv') if os.path.exists('week_game_status.csv') else pd.DataFrame(columns=['User','Year','Week','Status'])
                    for _c in ['Year','Week']: _wb[_c]=pd.to_numeric(_wb.get(_c),errors='coerce').fillna(0).astype(int)
                    _wb=_wb[~((_wb['Year']==int(_gs_year))&(_wb['Week']==int(_gs_week)))].copy()
                    pd.concat([_wb,pd.DataFrame([{'User':_u,'Year':int(_gs_year),'Week':int(_gs_week),'Status':_s} for _u,_s in _comb_status.items()])],ignore_index=True).to_csv('week_game_status.csv',index=False)
                    st.success(f"✅ Saved Week {_gs_week}. Download CSVs below and push to GitHub.")
                    st.cache_data.clear()
                except Exception as _sve: st.error(f"Save error: {_sve}")
            dl1,dl2=st.columns(2)
            with dl1:
                if os.path.exists('week_manual_scores.csv'):
                    with open('week_manual_scores.csv','rb') as f2:
                        st.download_button("⬇️ Scores CSV",data=f2.read(),file_name="week_manual_scores.csv",mime="text/csv",use_container_width=True,key="dl_manual_scores")
            with dl2:
                if os.path.exists('week_game_status.csv'):
                    with open('week_game_status.csv','rb') as f3:
                        st.download_button("⬇️ Status CSV",data=f3.read(),file_name="week_game_status.csv",mime="text/csv",use_container_width=True,key="dl_game_status")

    # ── PLAYER LOGIN ───────────────────────────────────────────────────────────
    _user_pw_map={
        "Mike":"sjsu26","Devin":"BGKevin","Josh":"Yayshusf",
        "Noah":"DinnerTime","Doug":"Buttstuff","Nick":"Nads31",
    }
    try:
        if os.path.exists('user_passwords.csv'):
            _upw=pd.read_csv('user_passwords.csv')
            _upw['User']=_upw['User'].astype(str).str.strip().str.title()
            _upw['Password']=_upw['Password'].astype(str).str.strip()
            _user_pw_map=dict(zip(_upw['User'],_upw['Password']))
    except: pass

    _logged_in_user=st.session_state.get('_player_logged_in_as',None)
    with st.expander(f"🎮 {'Logged in as '+_logged_in_user if _logged_in_user else 'Player Login — Enter Your Score'}",expanded=bool(_logged_in_user)):
        if not _logged_in_user:
            st.caption("Log in with your team password to set your score and game status.")
            pl1,pl2=st.columns(2)
            with pl1:
                _pl_user_sel=st.selectbox("Who are you?",list(USER_TEAMS.keys()),key="player_login_user_select")
            with pl2:
                _pl_pw=st.text_input("Password",type="password",key="player_login_pw",placeholder="Your team password")
            if _pl_pw:
                if _pl_pw==_user_pw_map.get(_pl_user_sel,''):
                    st.session_state['_player_logged_in_as']=_pl_user_sel; st.rerun()
                else: st.error("Wrong password. Ask the commissioner.")
        else:
            _pl_name_col,_pl_logout_col=st.columns([4,1])
            with _pl_name_col:
                _pl_team=USER_TEAMS.get(_logged_in_user,_logged_in_user)
                _pl_tc=get_team_primary_color(_pl_team)
                st.markdown(f"<span style='font-weight:900;color:{_pl_tc};font-size:1.05rem;'>{html.escape(_logged_in_user)}</span> <span style='color:#475569;font-size:.85rem;'>— {html.escape(_pl_team)}</span>",unsafe_allow_html=True)
            with _pl_logout_col:
                if st.button("🔒 Logout",key="player_logout_btn",use_container_width=True):
                    st.session_state.pop('_player_logged_in_as',None); st.rerun()
            _pl_matchup=_ctrl_matchup.get(_logged_in_user,'UNSCHEDULED')
            _pl_cur_msc=_msc_map2.get(_logged_in_user,{})
            _pl_cur_st=_game_status_map2.get(_logged_in_user,'Not Set')
            if _pl_matchup=='BYE':
                st.info("BYE WEEK — no game this week.")
                _pl_status=st.selectbox("Set status",['Not Set','Ready'],index=1 if _pl_cur_st=='Ready' else 0,key=f"pl_status_bye_{_logged_in_user}")
                if st.button("💾 Save Status",key="pl_bye_save",type="primary",use_container_width=True):
                    try:
                        _wb2=pd.read_csv('week_game_status.csv') if os.path.exists('week_game_status.csv') else pd.DataFrame(columns=['User','Year','Week','Status'])
                        for _c in ['Year','Week']: _wb2[_c]=pd.to_numeric(_wb2.get(_c),errors='coerce').fillna(0).astype(int)
                        _wb2=_wb2[~((_wb2['User'].astype(str).str.strip()==_logged_in_user)&(_wb2['Year']==int(_gs_year))&(_wb2['Week']==int(_gs_week)))].copy()
                        pd.concat([_wb2,pd.DataFrame([{'User':_logged_in_user,'Year':int(_gs_year),'Week':int(_gs_week),'Status':_pl_status}])],ignore_index=True).to_csv('week_game_status.csv',index=False)
                        st.success("✅ Saved!"); st.cache_data.clear()
                    except Exception as e: st.error(f"Save error: {e}")
            elif isinstance(_pl_matchup,dict):
                _pl_opp=_pl_matchup.get('opp','?'); _pl_ha='vs' if _pl_matchup.get('home') else '@'
                _pl_ol=image_file_to_data_uri(get_logo_source(_pl_opp))
                _pl_ol_h=f"<img src='{_pl_ol}' style='width:20px;height:20px;object-fit:contain;vertical-align:middle;margin-right:4px;'/>" if _pl_ol else ""
                st.markdown(f"<div style='font-size:.9rem;color:#94a3b8;margin-bottom:8px;'><strong style='color:#f1f5f9;'>{html.escape(_logged_in_user)}</strong> — {_pl_ha} {_pl_ol_h}{html.escape(_pl_opp)}</div>",unsafe_allow_html=True)
                _pls1,_pls2,_pls3=st.columns([1,1,2])
                with _pls1:
                    _pl_us=st.number_input("Us",min_value=0,max_value=99,value=_pl_cur_msc.get('user_score',0),key=f"pl_us_{_logged_in_user}_{_gs_week}",label_visibility="collapsed")
                with _pls2:
                    _pl_os=st.number_input("Opp",min_value=0,max_value=99,value=_pl_cur_msc.get('opp_score',0),key=f"pl_os_{_logged_in_user}_{_gs_week}",label_visibility="collapsed")
                with _pls3:
                    if _pl_us>0 or _pl_os>0:
                        _rl2="W" if _pl_us>_pl_os else ("L" if _pl_os>_pl_us else "TIE")
                        _rc4="#4ade80" if _rl2=="W" else ("#f87171" if _rl2=="L" else "#94a3b8")
                        st.markdown(f"<span style='color:{_rc4};font-weight:800;font-family:Bebas Neue,sans-serif;font-size:1.4rem;'>{_rl2} {_pl_us}-{_pl_os}</span>",unsafe_allow_html=True)
                    else:
                        _pl_status2=st.selectbox("Status",['Not Set','Ready'],index=1 if _pl_cur_st=='Ready' else 0,key=f"pl_status_{_logged_in_user}_{_gs_week}")
                if st.button("💾 Save My Score",key="pl_save_btn",type="primary",use_container_width=True):
                    try:
                        _auto_st='Ready' if (_pl_us>0 or _pl_os>0) else st.session_state.get(f"pl_status_{_logged_in_user}_{_gs_week}",'Not Set')
                        if _pl_us>0 or _pl_os>0:
                            _mb3=pd.read_csv('week_manual_scores.csv') if os.path.exists('week_manual_scores.csv') else pd.DataFrame(columns=['User','Year','Week','Opponent','UserScore','OppScore'])
                            for _c in ['Year','Week']: _mb3[_c]=pd.to_numeric(_mb3.get(_c),errors='coerce').fillna(0).astype(int)
                            _mb3=_mb3[~((_mb3['User'].astype(str).str.strip().str.title()==_logged_in_user)&(_mb3['Year']==int(_gs_year))&(_mb3['Week']==int(_gs_week)))].copy()
                            pd.concat([_mb3,pd.DataFrame([{'User':_logged_in_user,'Year':int(_gs_year),'Week':int(_gs_week),'Opponent':_pl_opp,'UserScore':_pl_us,'OppScore':_pl_os}])],ignore_index=True).to_csv('week_manual_scores.csv',index=False)
                        _wb3=pd.read_csv('week_game_status.csv') if os.path.exists('week_game_status.csv') else pd.DataFrame(columns=['User','Year','Week','Status'])
                        for _c in ['Year','Week']: _wb3[_c]=pd.to_numeric(_wb3.get(_c),errors='coerce').fillna(0).astype(int)
                        _wb3=_wb3[~((_wb3['User'].astype(str).str.strip().str.title()==_logged_in_user)&(_wb3['Year']==int(_gs_year))&(_wb3['Week']==int(_gs_week)))].copy()
                        pd.concat([_wb3,pd.DataFrame([{'User':_logged_in_user,'Year':int(_gs_year),'Week':int(_gs_week),'Status':_auto_st}])],ignore_index=True).to_csv('week_game_status.csv',index=False)
                        st.success(f"✅ Saved! Download the CSVs and send to Mike, or Mike can grab them from Commissioner Tools.")
                        st.cache_data.clear()
                    except Exception as e: st.error(f"Save error: {e}")
                # Try to email score directly to commissioner
                try:
                    _pl_team4=USER_TEAMS.get(_logged_in_user,_logged_in_user)
                    _auto_st4='Ready' if (_pl_us>0 or _pl_os>0) else 'Not Set'
                    _ok4,_result4=send_score_email(
                        user=_logged_in_user,team=_pl_team4,
                        user_score=_pl_us,opp_score=_pl_os,
                        opp_name=_pl_opp,week=int(_gs_week),year=int(_gs_year),
                        status=_auto_st4)
                    if _ok4:
                        pass  # success toast shown by button save above
                    elif _result4.startswith("mailto:"):
                        st.markdown(f"<a href='{_result4}' target='_blank'><button style='background:#3b82f6;color:white;border:none;border-radius:6px;padding:8px 16px;font-size:.85rem;font-weight:700;cursor:pointer;width:100%;'>📧 Email Score to Mike</button></a>",unsafe_allow_html=True)
                        st.caption("Click above to open your email app pre-filled with your score.")
                    else:
                        st.caption(f"Email: {_result4[:80]}...")
                except Exception as _em_err:
                    if os.path.exists('week_manual_scores.csv'):
                        with open('week_manual_scores.csv','rb') as f4:
                            st.download_button("⬇️ Download & Send to Mike",data=f4.read(),file_name=f"score_{_logged_in_user}_wk{_gs_week}.csv",mime="text/csv",use_container_width=True,key="pl_dl_scores")
            else:
                st.info("No matchup found for this week yet. Check back after the schedule drops.")

    # ── SCORE SAVE ALERT — notify commissioner when a user saves ─────────
    try:
        if os.path.exists('week_manual_scores.csv') and os.path.exists('week_game_status.csv'):
            import time as _time2
            _score_mtime=os.path.getmtime('week_manual_scores.csv')
            _status_mtime=os.path.getmtime('week_game_status.csv')
            _last_seen=st.session_state.get('_last_score_mtime',0)
            _latest=max(_score_mtime,_status_mtime)
            if _latest>_last_seen and _last_seen>0:
                # A save happened since last check
                _ms_chk=pd.read_csv('week_manual_scores.csv')
                _ms_chk['Year']=pd.to_numeric(_ms_chk.get('Year'),errors='coerce').fillna(0).astype(int)
                _ms_chk['Week']=pd.to_numeric(_ms_chk.get('Week'),errors='coerce').fillna(0).astype(int)
                _new=_ms_chk[(_ms_chk['Year']==CURRENT_YEAR)&(_ms_chk['Week']==CURRENT_WEEK_NUMBER)]
                if not _new.empty:
                    _new_users=_new['User'].astype(str).str.strip().tolist()
                    for _nu in _new_users:
                        _nrow=_new[_new['User'].astype(str).str.strip()==_nu].iloc[0]
                        _nus=int(_nrow.get('UserScore',0)); _nos=int(_nrow.get('OppScore',0))
                        st.toast(f"✅ {_nu} saved Wk {CURRENT_WEEK_NUMBER}: {_nus}-{_nos}. Download CSVs in Commissioner Tools!", icon="🏈")
            st.session_state['_last_score_mtime']=_latest
    except: pass


    st.markdown("---")
    render_injury_report()
    st.markdown("---")
    render_highest_rated_games(CURRENT_YEAR, CURRENT_WEEK_NUMBER)
    st.markdown("---")
    render_disruptors_chokers()
    st.markdown("---")
    render_flying_under_radar()
    st.markdown("---")
    render_heisman_watch(CURRENT_YEAR)
    st.markdown("---")
    render_who_would_win()

# ══════════════════════════════════════════════════════════════════════
# TAB 1 -- RANKINGS & METRICS
# ══════════════════════════════════════════════════════════════════════
with tabs[1]:
    _rm_tabs=st.tabs(["📋 Rankings","📐 Metrics"])

    with _rm_tabs[0]:
        st.header("📋 CFP Rankings")
        st.caption("College Football Playoff rankings history and current standings.")
        try:
            _cfp_hist=pd.read_csv('cfp_rankings_history.csv')
            _cfp_hist['YEAR']=pd.to_numeric(_cfp_hist['YEAR'],errors='coerce')
            _cfp_hist['WEEK']=pd.to_numeric(_cfp_hist['WEEK'],errors='coerce')
            _cfp_hist['RANK']=pd.to_numeric(_cfp_hist['RANK'],errors='coerce')
            _cfp_years=sorted(_cfp_hist['YEAR'].dropna().unique().astype(int),reverse=True)
            _sel_yr=st.selectbox("Season",_cfp_years,index=0,key="cfp_year_sel") if _cfp_years else CURRENT_YEAR
            _cfp_cy=_cfp_hist[_cfp_hist['YEAR']==_sel_yr].copy()
            if not _cfp_cy.empty:
                _cfp_weeks=sorted(_cfp_cy['WEEK'].dropna().unique().astype(int),reverse=True)
                _sel_wk=st.selectbox("Week",_cfp_weeks,index=0,key="cfp_week_sel")
                _snap=_cfp_cy[_cfp_cy['WEEK']==_sel_wk].sort_values('RANK').copy()
                # Render as compact table
                # Build enriched data maps for rankings table
                _cfp_fpi_map={}; _cfp_msp_map={}; _cfp_sf_map={}; _cfp_natty_map={}; _cfp_ovr_map={}
                try:
                    import glob as _fg
                    _fp=f'FPI/fpi_ratings_{_sel_yr}_wk{_sel_wk}.csv'
                    if not os.path.exists(_fp): _fp=f'fpi_ratings_{_sel_yr}_wk{_sel_wk}.csv'
                    if not os.path.exists(_fp):
                        # fallback: latest available FPI for this year
                        _fps=sorted(_fg.glob(f'FPI/fpi_ratings_{_sel_yr}_wk*.csv')+_fg.glob(f'fpi_ratings_{_sel_yr}_wk*.csv'),reverse=True)
                        _fp=_fps[0] if _fps else ''
                    if _fp and os.path.exists(_fp):
                        _fdf=pd.read_csv(_fp)
                        _tm_col=next((c for c in _fdf.columns if c.lower()=='team'),'Team')
                        _fpi_col=next((c for c in _fdf.columns if c.upper()=='FPI'),'FPI')
                        _cfp_fpi_map=dict(zip(_fdf[_tm_col].astype(str).str.strip(),pd.to_numeric(_fdf[_fpi_col],errors='coerce').fillna(0)))
                except: pass
                try:
                    _mp=f'FPI/ms_plus_{_sel_yr}_wk{_sel_wk}.csv'
                    if not os.path.exists(_mp): _mp=f'ms_plus_{_sel_yr}_wk{_sel_wk}.csv'
                    if not os.path.exists(_mp):
                        _mps=sorted(_fg.glob(f'FPI/ms_plus_{_sel_yr}_wk*.csv')+_fg.glob(f'ms_plus_{_sel_yr}_wk*.csv'),reverse=True)
                        _mp=_mps[0] if _mps else ''
                    if _mp and os.path.exists(_mp):
                        _mdf=pd.read_csv(_mp)
                        _tm_col2=next((c for c in _mdf.columns if c.lower()=='team'),'Team')
                        _noc=next((c for c in ('Natty Odds','Preseason Natty Odds') if c in _mdf.columns),None)
                        _msc=next((c for c in ('MSPlus','MS+','MS_PLUS') if c in _mdf.columns),None)
                        if _msc: _cfp_msp_map=dict(zip(_mdf[_tm_col2].astype(str).str.strip(),pd.to_numeric(_mdf[_msc],errors='coerce').fillna(0)))
                        if _noc: _cfp_natty_map=dict(zip(_mdf[_tm_col2].astype(str).str.strip(),pd.to_numeric(_mdf[_noc],errors='coerce').fillna(0)))
                except: pass
                try:
                    _sf_tmp=build_speed_freaks_live(_sel_yr)
                    if not _sf_tmp.empty: _cfp_sf_map=dict(zip(_sf_tmp['TEAM'].astype(str),_sf_tmp['RANK'].astype(int)))
                except: pass
                try:
                    _tr_f=f'team_ratings_{_sel_yr}.csv'
                    if not os.path.exists(_tr_f): _tr_f=f'FPI/team_ratings_{_sel_yr}.csv'
                    if os.path.exists(_tr_f):
                        _trdf=pd.read_csv(_tr_f)
                        _trdf.columns=[str(c).strip() for c in _trdf.columns]
                        _tm_col3=next((c for c in _trdf.columns if c.upper() in ('TEAM','SCHOOL')),'TEAM')
                        _trdf[_tm_col3]=_trdf[_tm_col3].astype(str).str.strip()
                        _ovr_col=next((c for c in _trdf.columns if c.upper() in ('OVR','OVERALL','RATING')),'OVR')
                        if _ovr_col in _trdf.columns:
                            _cfp_ovr_map=dict(zip(_trdf[_tm_col3],pd.to_numeric(_trdf[_ovr_col],errors='coerce').fillna(0).astype(int)))
                except: pass
                thead_cfp=(
                    "<tr style='background:#0a1220;'>"
                    "<th style='padding:5px 6px;color:#fbbf24;font-size:.72rem;text-align:center;width:36px;'>RK</th>"
                    "<th style='padding:5px 6px;color:#475569;font-size:.55rem;text-align:left;'>Team</th>"
                    "<th style='padding:5px 6px;color:#94a3b8;font-size:.55rem;text-align:center;'>Rec</th>"
                    "<th style='padding:5px 6px;color:#60a5fa;font-size:.55rem;text-align:center;'>OVR</th>"
                    "<th style='padding:5px 6px;color:#fbbf24;font-size:.55rem;text-align:center;'>FPI</th>"
                    "<th style='padding:5px 6px;color:#a78bfa;font-size:.55rem;text-align:center;'>MS+</th>"
                    "<th style='padding:5px 6px;color:#38bdf8;font-size:.55rem;text-align:center;'>SPD</th>"
                    "<th style='padding:5px 6px;color:#4ade80;font-size:.55rem;text-align:center;'>Natty</th>"
                    "</tr>"
                )
                rows_cfp=""
                for _,cr in _snap.iterrows():
                    tm=str(cr.get('TEAM','')).strip(); rk=int(cr.get('RANK',0))
                    rec=str(cr.get('RECORD','')).strip()
                    is_u=tm in ALL_USER_TEAMS; uc=get_team_primary_color(tm) if is_u else "#0f172a"
                    lg=get_school_logo_src(tm)
                    lh=f"<img src='{lg}' style='width:20px;height:20px;object-fit:contain;vertical-align:middle;'/>" if lg else ""
                    bg=f"background:linear-gradient(90deg,{uc}22 0%,#06090f 30%);" if is_u else "background:#06090f;"
                    bl=f"border-left:3px solid {uc};" if is_u else "border-left:2px solid #0f172a;"
                    nw="font-weight:900;color:#f8fafc;" if is_u else "font-weight:400;color:#64748b;"
                    rk_c="#fbbf24" if rk<=4 else ("#f8fafc" if rk<=12 else "#64748b")
                    _ovr2=_cfp_ovr_map.get(tm,0); _ovr2_s=str(_ovr2) if _ovr2 else "--"
                    _fpi2=_cfp_fpi_map.get(tm); _fpi2_s=f"{_fpi2:+.1f}" if _fpi2 is not None else "--"
                    _fpi2_c="#4ade80" if (_fpi2 or 0)>=5 else ("#fbbf24" if (_fpi2 or 0)>=0 else "#f87171")
                    _msp2=_cfp_msp_map.get(tm); _msp2_s=f"{_msp2:.1f}" if _msp2 else "--"
                    _sfr2=_cfp_sf_map.get(tm); _sfr2_s=f"#{_sfr2}" if _sfr2 else "--"
                    _nat2=_cfp_natty_map.get(tm,0)
                    def __p2o2(p):
                        try:
                            if p<=0: return "--"
                            if p>=50: return "Even"
                            return f'{max(1,int(round((100.0/p)-1.0)))}:1'
                        except: return "--"
                    _nat2_s=__p2o2(_nat2)
                    rows_cfp+=(f"<tr style='{bg}{bl}'>"
                        f"<td style='padding:4px 6px;text-align:center;font-family:Bebas Neue,sans-serif;font-size:.95rem;color:{rk_c};'>{rk}</td>"
                        f"<td style='padding:4px 6px;white-space:nowrap;'>{lh}"
                        f"<span style='{nw}font-family:Barlow Condensed,sans-serif;font-size:.82rem;margin-left:4px;'>{html.escape(tm)}</span></td>"
                        f"<td style='padding:4px 6px;text-align:center;color:#64748b;font-size:.68rem;'>{html.escape(rec)}</td>"
                        f"<td style='padding:4px 6px;text-align:center;color:#60a5fa;font-size:.72rem;font-weight:700;'>{_ovr2_s}</td>"
                        f"<td style='padding:4px 6px;text-align:center;font-family:Bebas Neue,sans-serif;color:{_fpi2_c};font-size:.85rem;'>{_fpi2_s}</td>"
                        f"<td style='padding:4px 6px;text-align:center;color:#a78bfa;font-size:.72rem;'>{_msp2_s}</td>"
                        f"<td style='padding:4px 6px;text-align:center;color:#38bdf8;font-size:.72rem;'>{_sfr2_s}</td>"
                        f"<td style='padding:4px 6px;text-align:center;color:#4ade80;font-size:.68rem;'>{_nat2_s}</td>"
                        f"</tr>")
                st.markdown(f"<div class='isp-power-table-wrap'><table class='isp-power-table' style='min-width:300px;'>"
                    f"<thead>{thead_cfp}</thead><tbody>{rows_cfp}</tbody></table></div>",
                    unsafe_allow_html=True)
                st.caption(f"Week {_sel_wk} · {_sel_yr} season · {len(_snap)} teams ranked")
            else:
                st.info("No rankings data for selected season.")
        except Exception as e:
            st.caption(f"CFP Rankings unavailable: {e}")

        st.markdown("---")
        st.subheader("🎯 Projected CFP Field (Top 12)")
        st.caption("Projected playoff field based on current FPI, CFP rank, and remaining strength of schedule. Auto-selected based on latest data.")
        try:
            _pcfp_yr=CURRENT_YEAR; _pcfp_wk=CURRENT_WEEK_NUMBER
            _pcfp_fpi_f=f'FPI/fpi_ratings_{_pcfp_yr}_wk{_pcfp_wk}.csv'
            if not os.path.exists(_pcfp_fpi_f): _pcfp_fpi_f=f'fpi_ratings_{_pcfp_yr}_wk{_pcfp_wk}.csv'
            import glob as _pcfp_glob
            if not os.path.exists(_pcfp_fpi_f):
                _fps2=sorted(_pcfp_glob.glob(f'FPI/fpi_ratings_{_pcfp_yr}_wk*.csv')+_pcfp_glob.glob(f'fpi_ratings_{_pcfp_yr}_wk*.csv'),reverse=True)
                _pcfp_fpi_f=_fps2[0] if _fps2 else ''
            _pcfp_cfp=pd.read_csv('cfp_rankings_history.csv') if os.path.exists('cfp_rankings_history.csv') else pd.DataFrame()
            _pcfp_fpi_df=pd.read_csv(_pcfp_fpi_f) if _pcfp_fpi_f and os.path.exists(_pcfp_fpi_f) else pd.DataFrame()
            if not _pcfp_cfp.empty:
                _pcfp_cfp['YEAR']=pd.to_numeric(_pcfp_cfp['YEAR'],errors='coerce')
                _pcfp_cfp['WEEK']=pd.to_numeric(_pcfp_cfp['WEEK'],errors='coerce')
                _pcfp_cy=_pcfp_cfp[_pcfp_cfp['YEAR']==_pcfp_yr]
                if not _pcfp_cy.empty:
                    _pcfp_lw=int(_pcfp_cy['WEEK'].max())
                    _pcfp_snap=_pcfp_cy[_pcfp_cy['WEEK']==_pcfp_lw].sort_values('RANK').head(25).copy()
                    _pcfp_snap['TEAM']=_pcfp_snap['TEAM'].astype(str).str.strip()
                    # Merge FPI scores
                    if not _pcfp_fpi_df.empty:
                        _tm_c=next((c for c in _pcfp_fpi_df.columns if c.lower()=='team'),'Team')
                        _fpi_c=next((c for c in _pcfp_fpi_df.columns if c.upper()=='FPI'),'FPI')
                        _pcfp_fpi_df[_tm_c]=_pcfp_fpi_df[_tm_c].astype(str).str.strip()
                        _pcfp_snap=_pcfp_snap.merge(_pcfp_fpi_df[[_tm_c,_fpi_c]].rename(columns={_tm_c:'TEAM',_fpi_c:'FPI'}),on='TEAM',how='left')
                    else:
                        _pcfp_snap['FPI']=0.0
                    _pcfp_snap['FPI']=pd.to_numeric(_pcfp_snap.get('FPI',0),errors='coerce').fillna(0)
                    _pcfp_snap['RANK']=pd.to_numeric(_pcfp_snap['RANK'],errors='coerce').fillna(99)
                    # Projection score: weight CFP rank + FPI
                    # Rank 1=25pts...25=1pt; FPI adds bonus
                    _pcfp_snap['_rank_pts']=(26-_pcfp_snap['RANK'].clip(upper=25)).clip(lower=0)
                    _pcfp_snap['_proj_score']=_pcfp_snap['_rank_pts']*2+_pcfp_snap['FPI']
                    _pcfp_top12=_pcfp_snap.sort_values('_proj_score',ascending=False).head(12).reset_index(drop=True)
                    # Render as seeded bracket list
                    _pcfp_cols=st.columns(2)
                    for _pi,(_,_pr) in enumerate(_pcfp_top12.iterrows()):
                        _pseed=_pi+1; _ptm=str(_pr['TEAM'])
                        _pcfp_rk=int(_pr.get('RANK',99)); _pfpi=float(_pr.get('FPI',0))
                        _pfpi_s=f'{_pfpi:+.1f}'
                        _puc=get_team_primary_color(_ptm)
                        _plg=get_school_logo_src(_ptm)
                        _plh=f"<img src='{_plg}' style='width:22px;height:22px;object-fit:contain;vertical-align:middle;'/>" if _plg else ''
                        _pis_user=_ptm in ALL_USER_TEAMS
                        _pbg=f"background:linear-gradient(90deg,{_puc}22 0%,#06090f 60%);" if _pis_user else "background:#06090f;"
                        _pbl=f"border-left:3px solid {_puc};" if _pis_user else "border-left:2px solid #1e293b;"
                        _pseed_c='#fbbf24' if _pseed<=4 else ('#60a5fa' if _pseed<=8 else '#94a3b8')
                        _prec=str(_pr.get('RECORD','')).strip()
                        _pcol=_pcfp_cols[_pi%2]
                        _pcol.markdown(
                            f"<div style='{_pbg}{_pbl}border:1px solid #1e293b;border-radius:8px;"
                            f"padding:6px 10px;margin-bottom:4px;display:flex;align-items:center;justify-content:space-between;gap:8px;'>"
                            f"<div style='display:flex;align-items:center;gap:6px;'>"
                            f"<span style='font-family:Bebas Neue,sans-serif;font-size:1rem;color:{_pseed_c};min-width:22px;'>#{_pseed}</span>"
                            f"{_plh}"
                            f"<span style='font-weight:800;color:{'#f1f5f9' if _pis_user else '#64748b'};font-family:Barlow Condensed,sans-serif;font-size:.88rem;'>{html.escape(_ptm)}</span>"
                            f"<span style='font-size:.62rem;color:#475569;'>{html.escape(_prec)}</span>"
                            f"</div>"
                            f"<div style='text-align:right;'>"
                            f"<span style='font-size:.68rem;color:#475569;'>CFP #{_pcfp_rk}</span>"
                            f"<span style='font-size:.68rem;color:#60a5fa;margin-left:6px;'>FPI {_pfpi_s}</span>"
                            f"</div></div>",
                            unsafe_allow_html=True
                        )
                    st.caption(f"Projected field from Wk {_pcfp_lw} CFP rankings + FPI. Seeds 1-4 = first-round byes.")
            else:
                st.info("No CFP rankings data available for projection.")
        except Exception as _pe:
            st.caption(f"CFP projection unavailable: {_pe}")

        st.markdown("---")
        render_cfp_bracket()

    with _rm_tabs[1]:
        st.header("📐 FPI, MS+ & Metrics")
        _met_tabs=st.tabs(["📈 FPI & MS+","🎮 Game Control","⚡ Speed Freaks","🧬 Natty DNA","💥 Explosive Index","🔍 Beatdown Reality","🧠 Talent Development","📊 Dynasty Analytics"])

        with _met_tabs[0]:
            st.caption("Power ratings, schedule-adjusted projections, and résumé metrics.")
            try:
                _fpi_df,_msp_df=get_ratings_and_ms_plus(year=CURRENT_YEAR,week_cap=CURRENT_WEEK_NUMBER)
                if not _msp_df.empty:
                    _power_table(_msp_df,"fpi_msp","#fbbf24","FPI and MS+ combined -- sorted by FPI by default.",has_msp=True)
                elif not _fpi_df.empty:
                    _power_table(_fpi_df,"fpi_only","#fbbf24","FPI power ratings.",has_msp=False)
                else:
                    st.info("No ratings data. Push schedule data and run COMPUTE_RATINGS.bat.")
            except Exception as e:
                st.caption(f"FPI/MS+ unavailable: {e}")

        with _met_tabs[1]:
            st.caption("Who actually dominated their games, not just won them.")
            def _gc_acc2(s):
                s=float(s) if s else 0
                if s>=82: return "#22c55e"
                if s>=72: return "#4ade80"
                if s>=60: return "#84cc16"
                if s>=48: return "#facc15"
                if s>=35: return "#fb923c"
                return "#ef4444"
            def _gc_badge2(s):
                s=float(s) if s else 0
                if s>=82: return "TOTAL CONTROL","#22c55e"
                if s>=72: return "COMMANDING","#4ade80"
                if s>=60: return "SOLID CONTROL","#84cc16"
                if s>=48: return "FRAGILE","#facc15"
                if s>=35: return "SURVIVING","#fb923c"
                return "OUTPLAYED","#ef4444"
            try:
                _gc_sum=pd.DataFrame(); _gc_games2=pd.DataFrame(); _gc_trend2=pd.DataFrame()
                for _pth in ['FPI/game_control_summary_v3.csv','game_control_summary_v3.csv']:
                    if os.path.exists(_pth): _gc_sum=pd.read_csv(_pth); break
                for _pth2 in ['FPI/game_control_by_game_v3.csv','game_control_by_game_v3.csv']:
                    if os.path.exists(_pth2): _gc_games2=pd.read_csv(_pth2); break
                for _pth3 in ['FPI/game_control_trend_v3.csv','game_control_trend_v3.csv']:
                    if os.path.exists(_pth3): _gc_trend2=pd.read_csv(_pth3); break
                if _gc_sum.empty:
                    st.info("Push game_control_summary_v3.csv (run COMPUTE_RATINGS.bat) to enable Game Control.")
                    st.caption("Game Control is pre-computed by dynasty_metrics_pipeline.py.")
                else:
                    for _gdf in [_gc_sum,_gc_games2,_gc_trend2]:
                        for _c in ("TEAM","USER"):
                            if _c in _gdf.columns: _gdf[_c]=_gdf[_c].astype(str).str.strip()
                        if "YEAR" in _gdf.columns: _gdf["YEAR"]=pd.to_numeric(_gdf["YEAR"],errors="coerce")
                    _gc_yr_opts_top=sorted(_gc_games2["YEAR"].dropna().unique().astype(int),reverse=True) if not _gc_games2.empty and "YEAR" in _gc_games2.columns else [CURRENT_YEAR]
                    _gc_top_yr=st.selectbox("Season",_gc_yr_opts_top,index=0,key="gc_top_yr")
                    _gc_sum["AVG_GAME_CONTROL"]=pd.to_numeric(_gc_sum["AVG_GAME_CONTROL"],errors="coerce").fillna(0)
                    # Build per-year table from by-game CSV (summary has no YEAR col)
                    _gc_bg_yr=_gc_games2[_gc_games2["YEAR"].fillna(-1).astype(int)==_gc_top_yr].copy() if not _gc_games2.empty and "YEAR" in _gc_games2.columns else pd.DataFrame()
                    if not _gc_bg_yr.empty and "game_control_score" in _gc_bg_yr.columns:
                        _gc_bg_yr["game_control_score"]=pd.to_numeric(_gc_bg_yr["game_control_score"],errors="coerce")
                        _gc_bg_yr["_w"]=(_gc_bg_yr["RESULT"].str.upper()=="W").astype(int)
                        _gc_bg_yr["_l"]=(_gc_bg_yr["RESULT"].str.upper()=="L").astype(int)
                        _gc_agg=_gc_bg_yr.groupby(["USER","TEAM"]).agg(
                            RECORD_WINS=("_w","sum"),RECORD_LOSSES=("_l","sum"),
                            AVG_GAME_CONTROL=("game_control_score","mean"),
                            BEST_GAME_CONTROL=("game_control_score","max"),
                            WORST_GAME_CONTROL=("game_control_score","min"),
                        ).reset_index()
                        _gc_agg["AVG_GAME_CONTROL"]=_gc_agg["AVG_GAME_CONTROL"].round(1)
                        _gc_sumf=_gc_agg.copy()
                    else:
                        _gc_sumf=_gc_sum.copy()
                    _gc_ranked=_gc_sumf.sort_values("AVG_GAME_CONTROL",ascending=False).reset_index(drop=True)
                    _gc_ranked["RANK"]=range(1,len(_gc_ranked)+1)
                    # Summary leaderboard
                    for _,_gr2 in _gc_ranked.iterrows():
                        _t2=str(_gr2["TEAM"]); _u2=str(_gr2["USER"])
                        _a2=float(_gr2.get("AVG_GAME_CONTROL",0)); _w2=int(_gr2.get("RECORD_WINS",0) or 0); _l2=int(_gr2.get("RECORD_LOSSES",0) or 0)
                        _badge2,_acc2=_gc_badge2(_a2)
                        _logo2=image_file_to_data_uri(get_logo_source(_t2))
                        _lh2=f"<img src='{_logo2}' style='width:36px;height:36px;object-fit:contain;'/>" if _logo2 else ""
                        tc2=get_team_primary_color(_t2)
                        st.markdown(
                            f"<div style='background:linear-gradient(90deg,{tc2}18 0%,#0f172a 40%);"
                            f"border-left:4px solid {_acc2};border-radius:10px;padding:10px 14px;margin-bottom:6px;"
                            f"display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;'>"
                            f"<div style='display:flex;align-items:center;gap:8px;'>"
                            f"<span style='color:#475569;font-family:Bebas Neue,sans-serif;'>#{int(_gr2['RANK'])}</span>"
                            f"{_lh2}"
                            f"<div><div style='font-weight:900;color:{tc2};font-family:Barlow Condensed,sans-serif;font-size:.9rem;'>{html.escape(_t2)}</div>"
                            f"<div style='font-size:.65rem;color:#64748b;'>{_w2}-{_l2} · {html.escape(_u2)}</div></div></div>"
                            f"<div style='text-align:right;'>"
                            f"<div style='font-size:.72rem;color:{_acc2};font-weight:900;letter-spacing:.04em;'>{_badge2}</div>"
                            f"<div style='font-family:Bebas Neue,sans-serif;font-size:1.4rem;color:{_acc2};'>{_a2:.1f}</div>"
                            f"</div></div>",
                            unsafe_allow_html=True
                        )
                    # Bar chart overview
                    _gc_bar2=go.Figure()
                    _gc_bs=_gc_ranked.sort_values("AVG_GAME_CONTROL",ascending=True)
                    _gc_bar2.add_trace(go.Bar(
                        y=[f"{r['TEAM']} ({r['USER']})" for _,r in _gc_bs.iterrows()],
                        x=_gc_bs["AVG_GAME_CONTROL"], orientation='h',
                        marker_color=[_gc_acc2(v) for v in _gc_bs["AVG_GAME_CONTROL"]],
                        text=[f"{float(v):.1f}" for v in _gc_bs["AVG_GAME_CONTROL"]], textposition='outside'))
                    _gc_bar2.update_layout(height=max(180,50*len(_gc_bs)),
                        margin=dict(l=10,r=40,t=10,b=10),
                        paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#cbd5e1'),showlegend=False,
                        xaxis=dict(range=[0,100],gridcolor='rgba(255,255,255,.06)'),
                        yaxis=dict(gridcolor='rgba(255,255,255,.03)'))
                    st.plotly_chart(_gc_bar2,use_container_width=True,config={'displayModeBar':False,'staticPlot':True})
                    # Team deep dive
                    st.subheader("🔍 By-Game Deep Dive")
                    _gc_sel_opts=[f"{r['USER']} • {r['TEAM']}" for _,r in _gc_ranked.iterrows() if str(r['TEAM']) in ALL_USER_TEAMS]
                    if _gc_sel_opts:
                        _gc_games2_f=_gc_games2[_gc_games2['YEAR'].fillna(-1).astype(int)==_gc_top_yr] if not _gc_games2.empty and 'YEAR' in _gc_games2.columns else _gc_games2
                    _gc_trend2_f=_gc_trend2[_gc_trend2['YEAR'].fillna(-1).astype(int)==_gc_top_yr] if not _gc_trend2.empty and 'YEAR' in _gc_trend2.columns else _gc_trend2
                    _gc_picked=st.selectbox("Select team",_gc_sel_opts,key="gc_team_sel2")
                    _gc_pu=_gc_picked.split(" • ")[0]; _gc_pt=_gc_picked.split(" • ")[1]
                    _gc_tg2=_gc_games2_f[(_gc_games2_f["USER"]==_gc_pu)&(_gc_games2_f["TEAM"]==_gc_pt)].copy() if not _gc_games2_f.empty else pd.DataFrame()
                    _gc_tt2=_gc_trend2_f[(_gc_trend2_f["USER"]==_gc_pu)&(_gc_trend2_f["TEAM"]==_gc_pt)].copy() if not _gc_trend2_f.empty else pd.DataFrame()
                    # Trend line
                    if not _gc_tt2.empty and "game_control_score" in _gc_tt2.columns:
                            _gc_tt2=_gc_tt2.sort_values(["YEAR","WEEK"]).copy()
                            _gc_tt2["wlbl"]="W"+_gc_tt2["WEEK"].astype(str)
                            _gcfig2=go.Figure()
                            _gcfig2.add_trace(go.Scatter(
                                x=_gc_tt2["wlbl"],y=_gc_tt2["game_control_score"],mode='lines+markers',
                                line=dict(color='#94a3b8',width=2),
                                marker=dict(size=11,color=[_gc_acc2(v) for v in _gc_tt2["game_control_score"]],line=dict(color='#0f172a',width=2)),
                                hovertemplate='<b>%{x}</b><br>GC: %{y:.1f}<extra></extra>'))
                            for _yval,_clr in [(82,"#22c55e"),(72,"#4ade80"),(60,"#84cc16"),(48,"#facc15")]:
                                _gcfig2.add_hline(y=_yval,line_dash="dot",line_color=_clr,opacity=.3)
                            _gcfig2.update_layout(height=260,margin=dict(l=24,r=16,t=10,b=20),
                                paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
                                font=dict(color='#cbd5e1'),showlegend=False,
                                xaxis=dict(title="Week",gridcolor='rgba(255,255,255,.06)'),
                                yaxis=dict(title="GC Score",gridcolor='rgba(255,255,255,.06)',range=[0,100]))
                            st.plotly_chart(_gcfig2,use_container_width=True,config={'displayModeBar':False,'staticPlot':True})
                    # Game cards
                    if not _gc_tg2.empty:
                            _gc_tg2=_gc_tg2.sort_values(["YEAR","WEEK"],ascending=[False,False])
                            for _,_gg2 in _gc_tg2.iterrows():
                                _wk2=int(float(_gg2.get("WEEK",0) or 0)); _opp2=str(_gg2.get("OPPONENT","?"))
                                _ts2=int(float(_gg2.get("TEAM_SCORE",0) or 0)); _os2=int(float(_gg2.get("OPP_SCORE",0) or 0))
                                _res2=str(_gg2.get("RESULT","?")); _score2=float(_gg2.get("game_control_score",50) or 50)
                                _acc3=_gc_acc2(_score2)
                                _pills2=""
                                for _flag,_flbl,_fclr in [("close_escape","CLOSE ESCAPE","#f59e0b"),("false_blowout","FALSE BLOWOUT","#a78bfa"),("stealth_dominance","STEALTH DOM","#38bdf8"),("got_robbed_flag","GOT ROBBED","#f87171")]:
                                    if str(_gg2.get(_flag,"")).upper() in("TRUE","1","YES"):
                                        _pills2+=f"<span style='display:inline-block;font-size:.65rem;font-weight:900;padding:2px 7px;border-radius:999px;margin-right:4px;background:{_fclr}22;color:{_fclr};border:1px solid {_fclr}55;'>{_flbl}</span>"
                                _opp_l2=image_file_to_data_uri(get_logo_source(_opp2))
                                _opp_img2=f"<img src='{_opp_l2}' style='width:18px;height:18px;object-fit:contain;vertical-align:middle;margin-right:4px;'/>" if _opp_l2 else ""
                                st.markdown(
                                    f"<div style='background:linear-gradient(90deg,{_acc3}12 0%,#0a1628 28%);"
                                    f"border-left:4px solid {_acc3};border-radius:10px;padding:10px 14px;margin-bottom:6px;'>"
                                    f"<div style='display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;'>"
                                    f"<div style='display:flex;align-items:center;gap:6px;font-weight:800;color:#f8fafc;'>"
                                    f"<span style='font-family:Bebas Neue,sans-serif;font-size:.85rem;color:#475569;'>WK {_wk2}</span>"
                                    f"{_opp_img2}<span>{html.escape(_opp2)}</span></div>"
                                    f"<div style='display:flex;align-items:center;gap:10px;'>"
                                    f"<span style='font-weight:900;color:{"#4ade80" if _res2.upper()=="W" else "#f87171"};'>{_res2} {_ts2}--{_os2}</span>"
                                    f"<span style='font-family:Bebas Neue,sans-serif;font-size:1.2rem;color:{_acc3};font-weight:900;'>GC {_score2:.1f}</span>"
                                    f"</div></div>"
                                    +( f"<div style='margin-top:6px;'>{_pills2}</div>" if _pills2 else "")
                                    +f"</div>",
                                    unsafe_allow_html=True
                                )
                    else:
                            st.info("No by-game data for this team yet. Push game_control_by_game_v3.csv.")
            except Exception as e:
                st.caption(f"Game Control unavailable: {e}")

        with _met_tabs[2]:
            st.caption("Team speed profiles -- live from all 136 teams.")
            _sf_df=build_speed_freaks_live(CURRENT_YEAR)
            if not _sf_df.empty:
                render_speed_freaks_table(_sf_df)
                # Key
                st.markdown("""
<div style='background:#06090f;border:1px solid #1e293b;border-radius:8px;padding:10px 14px;margin-top:8px;font-size:.68rem;'>
  <div style='font-weight:800;color:#f8fafc;margin-bottom:6px;'>Speed Freaks Key</div>
  <div style='display:flex;flex-wrap:wrap;gap:8px;color:#64748b;'>
    <span><span style='color:#38bdf8;font-weight:700;'>90+ SPD</span> -- Players rated 90+ speed</span>
    <span><span style='color:#60a5fa;font-weight:700;'>Cheat</span> -- Quad 90 (SPD+ACC+AGI+COD all ≥90)</span>
    <span><span style='color:#f97316;font-weight:700;'>Monster</span> -- Elite front-7 athlete</span>
    <span><span style='color:#22c55e;font-weight:700;'>Q-Hog</span> -- Quick OL (AGI≥85, STR≥90)</span>
    <span><span style='color:#fbbf24;font-weight:700;'>Gen</span> -- Generational speed (96+ SPD or ACC)</span>
    <span><span style='color:#94a3b8;font-weight:700;'>MPH</span> -- Composite speed score</span>
  </div>
</div>""", unsafe_allow_html=True)
            else:
                st.info(f"No roster data found. Push cfb_136_top30_rosters_{CURRENT_YEAR}.csv to enable Speed Freaks.")

        with _met_tabs[3]:
            render_natty_dna()

        with _met_tabs[4]:
            st.caption("Offensive explosion rating — drives, explosiveness, and big-play ability by game.")
            def _ei_acc(s):
                s=float(s) if s else 0
                if s>=95: return "#fbbf24"
                if s>=80: return "#4ade80"
                if s>=60: return "#60a5fa"
                if s>=40: return "#f97316"
                return "#f87171"
            try:
                _ei_sum=pd.DataFrame(); _ei_g=pd.DataFrame(); _ei_t=pd.DataFrame()
                for _p in ['FPI/explosive_index_summary.csv','explosive_index_summary.csv']:
                    if __import__('os').path.exists(_p): _ei_sum=__import__('pandas').read_csv(_p); break
                for _p in ['FPI/explosive_index_by_game.csv','explosive_index_by_game.csv']:
                    if __import__('os').path.exists(_p): _ei_g=__import__('pandas').read_csv(_p); break
                for _p in ['FPI/explosive_index_trend.csv','explosive_index_trend.csv']:
                    if __import__('os').path.exists(_p): _ei_t=__import__('pandas').read_csv(_p); break
                if _ei_sum.empty:
                    st.info("Push explosive_index_summary.csv to enable this tab.")
                else:
                    _ei_yr_avail=sorted(_ei_g['YEAR'].dropna().unique().astype(int),reverse=True) if not _ei_g.empty and 'YEAR' in _ei_g.columns else [CURRENT_YEAR]
                    _ei_sum_yr=st.selectbox('Season',_ei_yr_avail,index=0,key='ei_sum_yr')
                    _ei_sum_f=_ei_sum.copy()  # summary is all-time, games filtered
                    for _df in [_ei_sum,_ei_g,_ei_t]:
                        for _c in ('USER','TEAM'): 
                            if _c in _df.columns: _df[_c]=_df[_c].astype(str).str.strip()
                    _ei_sum['AVG_EXPLOSIVE_INDEX']=pd.to_numeric(_ei_sum.get('AVG_EXPLOSIVE_INDEX',0),errors='coerce').fillna(0)
                    # Filter by selected year if YEAR column present
                    _ei_bg_yr=_ei_g[_ei_g["YEAR"].fillna(-1).astype(int)==_ei_sum_yr].copy() if not _ei_g.empty and "YEAR" in _ei_g.columns else pd.DataFrame()
                    if not _ei_bg_yr.empty and "off_explosive_index" in _ei_bg_yr.columns:
                        _ei_bg_yr["_w"]=(_ei_bg_yr["RESULT"].str.upper()=="W").astype(int)
                        _ei_bg_yr["_l"]=(_ei_bg_yr["RESULT"].str.upper()=="L").astype(int)
                        for _efc in ("off_explosive_index","def_steel_curtain_index","quick_strike_flag","aerial_nuke_flag","ground_blast_flag","sputtering_offense_flag"):
                            if _efc in _ei_bg_yr.columns: _ei_bg_yr[_efc]=pd.to_numeric(_ei_bg_yr[_efc],errors="coerce").fillna(0)
                        _ei_agg=_ei_bg_yr.groupby(["USER","TEAM"]).agg(
                            RECORD_WINS=("_w","sum"),
                            RECORD_LOSSES=("_l","sum"),
                            AVG_EXPLOSIVE_INDEX=("off_explosive_index","mean"),
                        ).reset_index()
                        for _efc,_efcn in [("def_steel_curtain_index","AVG_STEEL_CURTAIN_INDEX"),("quick_strike_flag","QUICK_STRIKES"),("aerial_nuke_flag","AERIAL_NUKES"),("ground_blast_flag","GROUND_BLASTS"),("sputtering_offense_flag","SPUTTERING_GAMES")]:
                            if _efc in _ei_bg_yr.columns:
                                _fs=_ei_bg_yr.groupby(["USER","TEAM"])[_efc].agg("mean" if "index" in _efc else "sum").reset_index().rename(columns={_efc:_efcn})
                                _ei_agg=_ei_agg.merge(_fs,on=["USER","TEAM"],how="left")
                        _ei_agg["AVG_EXPLOSIVE_INDEX"]=_ei_agg["AVG_EXPLOSIVE_INDEX"].round(1)
                        _ei_style=_ei_sum[["USER","TEAM","OFF_STYLE_LABEL","DEF_STYLE_LABEL"]].copy() if all(c in _ei_sum.columns for c in ["OFF_STYLE_LABEL","DEF_STYLE_LABEL"]) else pd.DataFrame()
                        if not _ei_style.empty: _ei_agg=_ei_agg.merge(_ei_style,on=["USER","TEAM"],how="left")
                        _ei_sum_filt=_ei_agg
                    else:
                        _ei_sum_filt=_ei_sum.copy()
                    _ei_ranked=_ei_sum_filt.sort_values("AVG_EXPLOSIVE_INDEX",ascending=False).reset_index(drop=True)
                    _ei_ranked['RANK']=range(1,len(_ei_ranked)+1)
                    # Leaderboard
                    for _,_er in _ei_ranked.iterrows():
                        _t3=str(_er['TEAM']); _u3=str(_er['USER'])
                        _off=float(_er.get('AVG_EXPLOSIVE_INDEX',0)); _def=float(_er.get('AVG_STEEL_CURTAIN_INDEX',0))
                        _w3=int(_er.get('RECORD_WINS',0) or 0); _l3=int(_er.get('RECORD_LOSSES',0) or 0)
                        _qs=int(_er.get('QUICK_STRIKES',0) or 0); _an=int(_er.get('AERIAL_NUKES',0) or 0)
                        _gb=int(_er.get('GROUND_BLASTS',0) or 0); _sp=int(_er.get('SPUTTERING_GAMES',0) or 0)
                        _os=str(_er.get('OFF_STYLE_LABEL','')); _ds=str(_er.get('DEF_STYLE_LABEL',''))
                        _off_c=_ei_acc(_off); _def_c=_ei_acc(_def); tc3=get_team_primary_color(_t3)
                        _lg3=get_school_logo_src(_t3)
                        _lh3=f"<img src='{_lg3}' style='width:32px;height:32px;object-fit:contain;'/>" if _lg3 else ""
                        st.markdown(
                            f"<div style='background:linear-gradient(90deg,{tc3}15 0%,#0f172a 40%);"
                            f"border-left:4px solid {_off_c};border-radius:10px;padding:10px 14px;margin-bottom:6px;'>"
                            f"<div style='display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;'>"
                            f"<div style='display:flex;align-items:center;gap:8px;'>"
                            f"<span style='color:#475569;font-family:Bebas Neue,sans-serif;'>#{int(_er['RANK'])}</span>"
                            f"{_lh3}<div>"
                            f"<div style='font-weight:900;color:{tc3};font-family:Barlow Condensed,sans-serif;'>{html.escape(_t3)}</div>"
                            f"<div style='font-size:.65rem;color:#64748b;'>{_w3}-{_l3} · {html.escape(_u3)} · {html.escape(_os)}</div>"
                            f"</div></div>"
                            f"<div style='text-align:right;'>"
                            f"<div style='font-size:.62rem;color:#94a3b8;'>OFF <span style='color:{_off_c};font-weight:900;font-size:.85rem;'>{_off:.1f}</span>"
                            f"  DEF <span style='color:{_def_c};font-weight:900;font-size:.85rem;'>{_def:.1f}</span></div>"
                            f"<div style='font-size:.6rem;color:#475569;margin-top:2px;'>QS:{_qs} Nuke:{_an} GB:{_gb} Sputter:{_sp}</div>"
                            f"</div></div></div>",
                            unsafe_allow_html=True
                        )
                    # Deep dive
                    st.subheader("🔍 By-Game")
                    _ei_yr_opts=sorted(_ei_g['YEAR'].dropna().unique().astype(int),reverse=True) if not _ei_g.empty and 'YEAR' in _ei_g.columns else [CURRENT_YEAR]
                    _ei_yr_sel=st.selectbox("Season",_ei_yr_opts,index=0,key="ei_yr_sel")
                    _ei_g_f=_ei_g[_ei_g['YEAR'].fillna(-1).astype(int)==_ei_yr_sel].copy() if not _ei_g.empty and 'YEAR' in _ei_g.columns else _ei_g.copy()
                    _ei_teams=[f"{r['USER']} • {r['TEAM']}" for _,r in _ei_ranked.iterrows() if r['TEAM'] in ALL_USER_TEAMS]
                    if _ei_teams:
                        _ei_pick=st.selectbox("Team",_ei_teams,key="ei_team_pick")

                        _ei_pu2,_ei_pt2=_ei_pick.split(" • ",1)
                        _ei_g_sel=_ei_g[_ei_g['YEAR'].fillna(-1).astype(int)==_ei_sum_yr].copy() if not _ei_g.empty and 'YEAR' in _ei_g.columns else _ei_g.copy()
                        _ei_tg=_ei_g_sel[(_ei_g_sel['USER']==_ei_pu2)&(_ei_g_sel['TEAM']==_ei_pt2)].sort_values(['YEAR','WEEK'],ascending=[False,False])
                        for _,_eg in _ei_tg.iterrows():
                            _ewk=int(float(_eg.get('WEEK',0) or 0))
                            _eopp=str(_eg.get('OPPONENT','?')); _eres=str(_eg.get('RESULT','?'))
                            _ets=int(float(_eg.get('TEAM_SCORE',0) or 0)); _eos=int(float(_eg.get('OPP_SCORE',0) or 0))
                            _eoff=float(_eg.get('off_explosive_index',50) or 50)
                            _edef=float(_eg.get('def_steel_curtain_index',50) or 50)
                            _eolbl=str(_eg.get('off_explosive_label',''))
                            _erc="#4ade80" if _eres.upper()=="W" else "#f87171"
                            _eol=image_file_to_data_uri(get_logo_source(_eopp))
                            _eolh=f"<img src='{_eol}' style='width:18px;height:18px;object-fit:contain;vertical-align:middle;margin-right:4px;'/>" if _eol else ""
                            _eofc=_ei_acc(_eoff); _edfc=_ei_acc(_edef)
                            st.markdown(
                                f"<div style='background:linear-gradient(90deg,{_eofc}10 0%,#0a1628 28%);"
                                f"border-left:4px solid {_eofc};border-radius:8px;padding:9px 12px;margin-bottom:5px;'>"
                                f"<div style='display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;'>"
                                f"<div style='display:flex;align-items:center;gap:6px;font-size:.82rem;color:#f8fafc;font-weight:800;'>"
                                f"<span style='font-family:Bebas Neue,sans-serif;font-size:.8rem;color:#475569;'>WK {_ewk}</span>"
                                f"{_eolh}{html.escape(_eopp)}</div>"
                                f"<div style='display:flex;align-items:center;gap:10px;'>"
                                f"<span style='color:{_erc};font-weight:900;'>{_eres} {_ets}--{_eos}</span>"
                                f"<span style='font-size:.7rem;color:{_eofc};font-weight:700;'>OFF {_eoff:.1f}</span>"
                                f"<span style='font-size:.7rem;color:{_edfc};font-weight:700;'>DEF {_edef:.1f}</span>"
                                f"</div></div>"
                                f"<div style='font-size:.62rem;color:#64748b;margin-top:3px;'>{html.escape(_eolbl)}</div>"
                                f"</div>",
                                unsafe_allow_html=True
                            )
            except Exception as _ei_err:
                st.caption(f"Explosive Index unavailable: {_ei_err}")

        with _met_tabs[5]:
            st.caption("Beatdown Reality Check — how dominant were the wins actually? How bad were the losses really?")
            try:
                _brc_sum=pd.DataFrame(); _brc_g=pd.DataFrame()
                for _p in ['FPI/beatdown_reality_check_summary.csv','beatdown_reality_check_summary.csv']:
                    if __import__('os').path.exists(_p): _brc_sum=__import__('pandas').read_csv(_p); break
                for _p in ['FPI/beatdown_reality_check_by_game.csv','beatdown_reality_check_by_game.csv']:
                    if __import__('os').path.exists(_p): _brc_g=__import__('pandas').read_csv(_p); break
                if _brc_sum.empty:
                    st.info("Push beatdown_reality_check_summary.csv to enable this tab.")
                else:
                    _brc_yr_avail2=sorted(_brc_g['YEAR'].dropna().unique().astype(int),reverse=True) if not _brc_g.empty and 'YEAR' in _brc_g.columns else [CURRENT_YEAR]
                    _brc_sum_yr=st.selectbox('Season',_brc_yr_avail2,index=0,key='brc_sum_yr')
                    for _df in [_brc_sum,_brc_g]:
                        for _c in ('USER','TEAM'):
                            if _c in _df.columns: _df[_c]=_df[_c].astype(str).str.strip()
                    _brc_sum['AVG_BEATDOWN_REALITY_SCORE']=pd.to_numeric(_brc_sum.get('AVG_BEATDOWN_REALITY_SCORE',0),errors='coerce').fillna(0)
                    _brc_bg_yr=_brc_g[_brc_g["YEAR"].fillna(-1).astype(int)==_brc_sum_yr].copy() if not _brc_g.empty and "YEAR" in _brc_g.columns else pd.DataFrame()
                    if not _brc_bg_yr.empty and "beatdown_reality_score" in _brc_bg_yr.columns:
                        _brc_bg_yr["beatdown_reality_score"]=pd.to_numeric(_brc_bg_yr["beatdown_reality_score"],errors="coerce")
                        _brc_bg_yr["_w"]=(_brc_bg_yr["RESULT"].str.upper()=="W").astype(int)
                        _brc_bg_yr["_l"]=(_brc_bg_yr["RESULT"].str.upper()=="L").astype(int)
                        _brc_agg_d={"_w":"sum","_l":"sum","beatdown_reality_score":"mean"}
                        for _bf in ("win_was_shakier_than_score_flag","we_should_have_won_bigger_flag","got_worked_flag"):
                            if _bf in _brc_bg_yr.columns: _brc_bg_yr[_bf]=pd.to_numeric(_brc_bg_yr[_bf],errors="coerce").fillna(0); _brc_agg_d[_bf]="sum"
                        _brc_agg=_brc_bg_yr.groupby(["USER","TEAM"]).agg(**{
                            "RECORD_WINS":pd.NamedAgg("_w","sum"),
                            "RECORD_LOSSES":pd.NamedAgg("_l","sum"),
                            "AVG_BEATDOWN_REALITY_SCORE":pd.NamedAgg("beatdown_reality_score","mean"),
                            **({k.replace("win_was_shakier_than_score_flag","SHAKY_WINS").replace("we_should_have_won_bigger_flag","SHOULD_HAVE_WON_BIGGER_GAMES").replace("got_worked_flag","GOT_WORKED_GAMES"):pd.NamedAgg(column=k,aggfunc="sum") for k in ("win_was_shakier_than_score_flag","we_should_have_won_bigger_flag","got_worked_flag") if k in _brc_bg_yr.columns})
                        }).reset_index()
                        _brc_agg["AVG_BEATDOWN_REALITY_SCORE"]=_brc_agg["AVG_BEATDOWN_REALITY_SCORE"].round(1)
                        _brc_style=_brc_sum[["USER","TEAM","BRC_PROFILE_LABEL"]].copy() if "BRC_PROFILE_LABEL" in _brc_sum.columns else pd.DataFrame()
                        if not _brc_style.empty: _brc_agg=_brc_agg.merge(_brc_style,on=["USER","TEAM"],how="left")
                        _brc_sum_filt=_brc_agg
                    else:
                        _brc_sum_filt=_brc_sum.copy()
                    _brc_ranked=_brc_sum_filt.sort_values("AVG_BEATDOWN_REALITY_SCORE",ascending=False).reset_index(drop=True)
                    _brc_ranked['RANK']=range(1,len(_brc_ranked)+1)
                    def _brc_c(s):
                        s=float(s) if s else 0
                        if s>=85: return "#4ade80"
                        if s>=70: return "#fbbf24"
                        if s>=50: return "#f97316"
                        return "#f87171"
                    for _,_br in _brc_ranked.iterrows():
                        _bt=str(_br['TEAM']); _bu=str(_br['USER'])
                        _ba=float(_br.get('AVG_BEATDOWN_REALITY_SCORE',0))
                        _bw=int(_br.get('RECORD_WINS',0) or 0); _bl=int(_br.get('RECORD_LOSSES',0) or 0)
                        _bp=str(_br.get('BRC_PROFILE_LABEL','')); _bac=_brc_c(_ba); tc4=get_team_primary_color(_bt)
                        _lg4=get_school_logo_src(_bt)
                        _lh4=f"<img src='{_lg4}' style='width:32px;height:32px;object-fit:contain;'/>" if _lg4 else ""
                        _sh_w=int(_br.get('SHAKY_WINS',0) or 0); _bw2=int(_br.get('SHOULD_HAVE_WON_BIGGER_GAMES',0) or 0)
                        _gw=int(_br.get('GOT_WORKED_GAMES',0) or 0)
                        st.markdown(
                            f"<div style='background:linear-gradient(90deg,{tc4}15 0%,#0f172a 40%);"
                            f"border-left:4px solid {_bac};border-radius:10px;padding:10px 14px;margin-bottom:6px;'>"
                            f"<div style='display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;'>"
                            f"<div style='display:flex;align-items:center;gap:8px;'>"
                            f"<span style='color:#475569;font-family:Bebas Neue,sans-serif;'>#{int(_br['RANK'])}</span>"
                            f"{_lh4}<div>"
                            f"<div style='font-weight:900;color:{tc4};font-family:Barlow Condensed,sans-serif;'>{html.escape(_bt)}</div>"
                            f"<div style='font-size:.65rem;color:#64748b;'>{_bw}-{_bl} · {html.escape(_bu)} · {html.escape(_bp)}</div>"
                            f"</div></div>"
                            f"<div style='text-align:right;'>"
                            f"<div style='font-family:Bebas Neue,sans-serif;font-size:1.4rem;color:{_bac};'>{_ba:.1f}</div>"
                            f"<div style='font-size:.6rem;color:#475569;'>Shaky W:{_sh_w} Could've Won Bigger:{_bw2} Got Worked:{_gw}</div>"
                            f"</div></div></div>",
                            unsafe_allow_html=True
                        )
                    # By-game
                    st.subheader("🔍 By-Game")
                    _brc_yr_opts=sorted(_brc_g['YEAR'].dropna().unique().astype(int),reverse=True) if not _brc_g.empty and 'YEAR' in _brc_g.columns else [CURRENT_YEAR]
                    _brc_yr_sel=st.selectbox("Season",_brc_yr_opts,index=0,key="brc_yr_sel")
                    _brc_g_f=_brc_g[_brc_g['YEAR'].fillna(-1).astype(int)==_brc_yr_sel].copy() if not _brc_g.empty and 'YEAR' in _brc_g.columns else _brc_g.copy()
                    _brc_teams=[f"{r['USER']} • {r['TEAM']}" for _,r in _brc_ranked.iterrows() if r['TEAM'] in ALL_USER_TEAMS]
                    if _brc_teams:
                        _brc_pick=st.selectbox("Team",_brc_teams,key="brc_team_pick")
                        _brc_pu,_brc_pt=_brc_pick.split(" • ",1)
                        _brc_g_sel2=_brc_g[_brc_g['YEAR'].fillna(-1).astype(int)==_brc_sum_yr].copy() if not _brc_g.empty and 'YEAR' in _brc_g.columns else _brc_g.copy()
                        _brc_tg=_brc_g_sel2[(_brc_g_sel2['USER']==_brc_pu)&(_brc_g_sel2['TEAM']==_brc_pt)].sort_values(['YEAR','WEEK'],ascending=[False,False])
                        for _,_bg in _brc_tg.iterrows():
                            _bgwk=int(float(_bg.get('WEEK',0) or 0))
                            _bgopp=str(_bg.get('OPPONENT','?')); _bgres=str(_bg.get('RESULT','?'))
                            _bgts=int(float(_bg.get('TEAM_SCORE',0) or 0)); _bgos=int(float(_bg.get('OPP_SCORE',0) or 0))
                            _bgsc=float(_bg.get('beatdown_reality_score',_bg.get('AVG_BEATDOWN_REALITY_SCORE',50)) if 'beatdown_reality_score' in _bg.index else 50)
                            _bgrc="#4ade80" if _bgres.upper()=="W" else "#f87171"
                            _bgc=_brc_c(_bgsc)
                            _bgol=image_file_to_data_uri(get_logo_source(_bgopp))
                            _bgolh=f"<img src='{_bgol}' style='width:18px;height:18px;object-fit:contain;vertical-align:middle;margin-right:4px;'/>" if _bgol else ""
                            st.markdown(
                                f"<div style='background:linear-gradient(90deg,{_bgc}10 0%,#0a1628 28%);"
                                f"border-left:4px solid {_bgc};border-radius:8px;padding:9px 12px;margin-bottom:5px;'>"
                                f"<div style='display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;'>"
                                f"<div style='display:flex;align-items:center;gap:6px;font-size:.82rem;color:#f8fafc;font-weight:800;'>"
                                f"<span style='font-family:Bebas Neue,sans-serif;font-size:.8rem;color:#475569;'>WK {_bgwk}</span>"
                                f"{_bgolh}{html.escape(_bgopp)}</div>"
                                f"<div style='display:flex;align-items:center;gap:10px;'>"
                                f"<span style='color:{_bgrc};font-weight:900;'>{_bgres} {_bgts}--{_bgos}</span>"
                                f"<span style='font-family:Bebas Neue,sans-serif;font-size:1.1rem;color:{_bgc};font-weight:900;'>BRC {_bgsc:.1f}</span>"
                                f"</div></div></div>",
                                unsafe_allow_html=True
                            )
            except Exception as _brc_err:
                st.caption(f"Beatdown Reality Check unavailable: {_brc_err}")

        with _met_tabs[6]:
            st.header("🧠 Talent Development")
            st.caption("Year-over-year player rating improvements. Compare a player's OVR, SPD, ACC, AGI, COD across seasons.")
            try:
                import glob as _tg
                # Build year list: per-year CSVs (2043+) + legacy years from cfb26_rosters_full.csv
                _td_peryear=sorted([int(f.split('_')[-1].replace('.csv','')) for f in _tg.glob('cfb_136_top30_rosters_*.csv')],reverse=True)
                _td_legacy_yrs=[]
                if os.path.exists('cfb26_rosters_full.csv'):
                    try:
                        _leg=pd.read_csv('cfb26_rosters_full.csv')
                        _leg.columns=[str(c).strip() for c in _leg.columns]
                        _yr_lc=next((c for c in _leg.columns if c.upper() in ('YEAR','SEASON')),None)
                        if _yr_lc: _td_legacy_yrs=sorted(_leg[_yr_lc].dropna().astype(int).unique().tolist())
                    except: pass
                _td_years=sorted(list(set(_td_peryear+_td_legacy_yrs)),reverse=True)
                def _load_roster_for_year(yr):
                    """Load roster for year — per-year CSV first, fall back to cfb26 legacy."""
                    _f=f'cfb_136_top30_rosters_{yr}.csv'
                    if os.path.exists(_f):
                        _r=pd.read_csv(_f); _r.columns=[str(c).strip() for c in _r.columns]
                        if 'YEAR' in _r.columns:
                            _r['YEAR']=pd.to_numeric(_r['YEAR'],errors='coerce')
                            _r=_r[_r['YEAR'].fillna(-1).astype(int)==yr]
                        return _r
                    if os.path.exists('cfb26_rosters_full.csv'):
                        _r=pd.read_csv('cfb26_rosters_full.csv'); _r.columns=[str(c).strip() for c in _r.columns]
                        _yr_lc=next((c for c in _r.columns if c.upper() in ('YEAR','SEASON')),None)
                        if _yr_lc: return _r[pd.to_numeric(_r[_yr_lc],errors='coerce').fillna(-1).astype(int)==yr]
                    return pd.DataFrame()
                if len(_td_years)<2:
                    st.info("Need at least 2 seasons of roster data to show development.")
                else:
                    _td_c1,_td_c2=st.columns(2)
                    with _td_c1: _td_yr_new=st.selectbox("Current Season",_td_years,index=0,key="td_yr_new")
                    with _td_c2:
                        _td_yr_old_opts=[y for y in _td_years if y<_td_yr_new]
                        _td_yr_old=st.selectbox("Prior Season",_td_yr_old_opts,index=0,key="td_yr_old") if _td_yr_old_opts else None
                    if _td_yr_old:
                        _ros_new=_load_roster_for_year(_td_yr_new)
                        _ros_old=_load_roster_for_year(_td_yr_old)
                        for _rdf in [_ros_new,_ros_old]:
                            _rdf.columns=[str(c).strip() for c in _rdf.columns]
                            for _old_c,_new_c in [('PLAYER','NAME'),('POS','POS')]:
                                if _old_c in _rdf.columns and _new_c not in _rdf.columns: _rdf.rename(columns={_old_c:_new_c},inplace=True)
                            _tc=next((c for c in _rdf.columns if c.upper()=='TEAM'),'TEAM')
                            _nc=next((c for c in _rdf.columns if c.upper() in ('NAME','PLAYER')),'NAME')
                            if _tc!='TEAM': _rdf.rename(columns={_tc:'TEAM'},inplace=True)
                            if _nc!='NAME': _rdf.rename(columns={_nc:'NAME'},inplace=True)
                            for _ac in ('OVR','SPD','ACC','AGI','COD'):
                                if _ac in _rdf.columns: _rdf[_ac]=pd.to_numeric(_rdf[_ac],errors='coerce').fillna(0)
                        _ros_new_u=_ros_new[_ros_new['TEAM'].isin(ALL_USER_TEAMS)].copy()
                        _ros_old_u=_ros_old[_ros_old['TEAM'].isin(ALL_USER_TEAMS)].copy()
                        _merge_cols=[c for c in ('OVR','SPD','ACC','AGI','COD') if c in _ros_old_u.columns]
                        _merged=_ros_new_u.merge(_ros_old_u[['NAME','TEAM']+_merge_cols],on=['NAME','TEAM'],suffixes=('','_old'),how='inner')
                        for _ac in ('OVR','SPD','ACC','AGI','COD'):
                            if f'{_ac}_old' in _merged.columns:
                                _merged[f'd{_ac}']=(_merged[_ac]-_merged[f'{_ac}_old']).round(1)
                        if _merged.empty:
                            st.info("No matching players between seasons.")
                        else:
                            _merged=_merged[_merged['dOVR'].notna()].copy()
                            st.subheader(f"🏆 Biggest Movers: {_td_yr_old} → {_td_yr_new}")
                            _imp_cols=['OVR','SPD','ACC','AGI','COD']
                            _imp_labels={'OVR':'Overall','SPD':'Speed','ACC':'Accel','AGI':'Agility','COD':'COD'}
                            _imp_colors={'OVR':'#fbbf24','SPD':'#38bdf8','ACC':'#4ade80','AGI':'#a78bfa','COD':'#f97316'}
                            _card_cols=st.columns(len(_imp_cols))
                            for _idx,_at in enumerate(_imp_cols):
                                _dc=f'd{_at}'
                                if _dc not in _merged.columns: continue
                                _best=_merged[_merged[_dc]>0].nlargest(1,_dc)
                                if _best.empty: continue
                                _bp=_best.iloc[0]; _btm=str(_bp['TEAM']); _ic=_imp_colors[_at]
                                _blg=get_school_logo_src(_btm)
                                _blh=f"<img src='{_blg}' style='width:20px;height:20px;object-fit:contain;'/>" if _blg else ''
                                _bnm=str(_bp.get('NAME','?')); _bpo=str(_bp.get('POS','?'))
                                _bdelta=float(_bp[_dc]); _bnew=int(_bp.get(_at,0)); _bold=int(_bp.get(f'{_at}_old',0))
                                _card_cols[_idx].markdown(
                                    f"<div style='background:linear-gradient(135deg,{_ic}18 0%,#06090f 60%);border:1px solid {_ic}40;"
                                    f"border-radius:12px;padding:10px 12px;text-align:center;'>"
                                    f"<div style='font-size:.58rem;color:{_ic};font-weight:700;letter-spacing:.06em;text-transform:uppercase;margin-bottom:4px;'>TOP {_imp_labels[_at]} ↑</div>"
                                    f"<div style='margin-bottom:3px;'>{_blh}</div>"
                                    f"<div style='font-weight:900;color:#f1f5f9;font-family:Barlow Condensed,sans-serif;font-size:.85rem;'>{html.escape(_bnm)}</div>"
                                    f"<div style='font-size:.58rem;color:#64748b;margin-bottom:4px;'>{html.escape(_bpo)} · {html.escape(_btm)}</div>"
                                    f"<div style='font-family:Bebas Neue,sans-serif;font-size:1.4rem;color:{_ic};line-height:1;'>+{_bdelta:.0f}</div>"
                                    f"<div style='font-size:.55rem;color:#475569;'>{_bold} → {_bnew}</div></div>",
                                    unsafe_allow_html=True)
                            st.markdown("---")
                            # ── Top 10 OVR Gains — FPI-style leaderboard ─────────────
                            st.subheader(f"📈 Top 10 OVR Gains: {_td_yr_old} → {_td_yr_new}")
                            _top10=_merged.nlargest(10,'dOVR').copy()
                            _top10_html=""
                            for _ti,(_,_tr) in enumerate(_top10.iterrows()):
                                _tnm=str(_tr.get('NAME','?')); _tpo=str(_tr.get('POS','?')); _ttm=str(_tr.get('TEAM','?'))
                                _tdov=float(_tr.get('dOVR',0)); _tnew=int(_tr.get('OVR',0)); _told=int(_tr.get('OVR_old',0))
                                _tpc=get_team_primary_color(_ttm); _tlg=get_school_logo_src(_ttm)
                                _tlh=f"<img src='{_tlg}' style='width:20px;height:20px;object-fit:contain;vertical-align:middle;'/>" if _tlg else ""
                                _trk_c='#fbbf24' if _ti==0 else ('#94a3b8' if _ti==1 else ('#cd7f32' if _ti==2 else '#475569'))
                                _top10_html+=(f"<tr style='border-bottom:1px solid #0f172a;background:{_tpc}12'>"
                                    f"<td style='padding:5px 8px;text-align:center;font-family:Bebas Neue,sans-serif;font-size:.95rem;color:{_trk_c};'>#{_ti+1}</td>"
                                    f"<td style='padding:5px 8px;white-space:nowrap;'>{_tlh} <span style='font-weight:800;color:#f1f5f9;font-family:Barlow Condensed,sans-serif;font-size:.88rem;'>{html.escape(_tnm)}</span></td>"
                                    f"<td style='padding:5px 8px;text-align:center;'><span style='background:{_tpc}33;color:{_tpc};border-radius:3px;padding:1px 6px;font-size:.62rem;font-weight:700;'>{_tpo}</span></td>"
                                    f"<td style='padding:5px 8px;text-align:center;color:#64748b;font-size:.75rem;'>{html.escape(_ttm[:12])}</td>"
                                    f"<td style='padding:5px 8px;text-align:center;color:#94a3b8;font-size:.75rem;'>{_told}</td>"
                                    f"<td style='padding:5px 8px;text-align:center;font-family:Bebas Neue,sans-serif;font-size:.95rem;color:#4ade80;'>+{_tdov:.0f}</td>"
                                    f"<td style='padding:5px 8px;text-align:center;color:#f1f5f9;font-weight:700;font-size:.82rem;'>{_tnew}</td>"
                                    f"</tr>")
                            st.markdown(
                                "<div style='overflow-x:auto;border:1px solid #1e293b;border-radius:10px;background:#0a1220;'>"
                                "<table style='width:100%;border-collapse:collapse;font-size:.82rem;'>"
                                "<thead><tr style='background:#06090f;'>"
                                "<th style='padding:6px 8px;color:#475569;font-size:.58rem;'>#</th>"
                                "<th style='padding:6px 8px;color:#94a3b8;font-size:.58rem;text-align:left;'>Player</th>"
                                "<th style='padding:6px 8px;color:#475569;font-size:.58rem;'>Pos</th>"
                                "<th style='padding:6px 8px;color:#475569;font-size:.58rem;'>Team</th>"
                                "<th style='padding:6px 8px;color:#64748b;font-size:.58rem;'>Was</th>"
                                "<th style='padding:6px 8px;color:#4ade80;font-size:.58rem;'>Δ OVR</th>"
                                "<th style='padding:6px 8px;color:#f1f5f9;font-size:.58rem;'>Now</th>"
                                f"</tr></thead><tbody>{_top10_html}</tbody></table></div>",
                                unsafe_allow_html=True
                            )
                            st.markdown("---")
                            # ── Coach Developer Rankings — EI-style cards ─────────────
                            st.subheader("🏅 Coach Talent Developer Rankings")
                            _coach_avgs=[]
                            for _cuser,_cteam in USER_TEAMS.items():
                                _tm=_merged[_merged['TEAM']==_cteam]
                                if not _tm.empty and 'dOVR' in _tm.columns:
                                    _coach_avgs.append({'user':_cuser,'team':_cteam,'avg_imp':round(_tm['dOVR'].mean(),2),'improved':int((_tm['dOVR']>0).sum()),'total':len(_tm)})
                            if _coach_avgs:
                                _coach_avgs.sort(key=lambda x:-x['avg_imp'])
                                _dev_medals={0:'🥇',1:'🥈',2:'🥉'}
                                for _di,_da in enumerate(_coach_avgs):
                                    _du=_da['user']; _dt=_da['team']
                                    _dc=get_team_primary_color(_dt)
                                    _dlg=get_school_logo_src(_dt)
                                    _dlh=f"<img src='{_dlg}' style='width:28px;height:28px;object-fit:contain;'/>" if _dlg else ""
                                    _bar_w=max(5,min(100,int((_da['avg_imp']+5)*8)))
                                    _medal=_dev_medals.get(_di,f"#{_di+1}")
                                    st.markdown(
                                        f"<div style='background:linear-gradient(90deg,{_dc}22 0%,#06090f 40%);border:1px solid {_dc}44;"
                                        f"border-left:4px solid {_dc};border-radius:10px;padding:10px 16px;margin-bottom:6px;'>"
                                        f"<div style='display:flex;align-items:center;gap:10px;'>"
                                        f"<span style='font-family:Bebas Neue,sans-serif;font-size:1.3rem;color:#fbbf24;min-width:28px;'>{_medal}</span>"
                                        f"{_dlh}"
                                        f"<div style='flex:1;'>"
                                        f"<div style='display:flex;align-items:baseline;gap:6px;'><span style='font-weight:900;color:{_dc};font-family:Barlow Condensed,sans-serif;font-size:.95rem;'>{html.escape(_dt)}</span>"
                                        f"<span style='font-size:.65rem;color:#64748b;'>{html.escape(_du)}</span></div>"
                                        f"<div style='background:#1e293b;border-radius:4px;height:6px;margin-top:4px;overflow:hidden;'>"
                                        f"<div style='background:{_dc};width:{_bar_w}%;height:100%;border-radius:4px;'></div></div>"
                                        f"</div>"
                                        f"<div style='text-align:right;'><div style='font-family:Bebas Neue,sans-serif;font-size:1.8rem;color:{"#4ade80" if _da["avg_imp"]>0 else "#f87171"};line-height:1;'>{_da['avg_imp']:+.2f}</div>"
                                        f"<div style='font-size:.55rem;color:#475569;'>AVG Δ OVR</div>"
                                        f"<div style='font-size:.6rem;color:#64748b;'>{_da['improved']}/{_da['total']} improved</div></div>"
                                        f"</div></div>",
                                        unsafe_allow_html=True
                                    )
                            st.markdown("---")
                            st.subheader("🌟 Top 10 Career OVR Gains")
                            _all_ros=[]
                            for _yr in sorted(_td_years):
                                try:
                                    _rr=_load_roster_for_year(_yr)
                                    if _rr.empty: continue
                                    _tc2=next((c for c in _rr.columns if c.upper()=='TEAM'),'TEAM')
                                    _nc2=next((c for c in _rr.columns if c.upper() in ('NAME','PLAYER')),'NAME')
                                    if _tc2!='TEAM': _rr.rename(columns={_tc2:'TEAM'},inplace=True)
                                    if _nc2!='NAME': _rr.rename(columns={_nc2:'NAME'},inplace=True)
                                    _rr['OVR']=pd.to_numeric(_rr.get('OVR',0),errors='coerce').fillna(0)
                                    _rr['_yr']=_yr; _all_ros.append(_rr[['NAME','TEAM','OVR','_yr']])
                                except: pass
                            if _all_ros:
                                _adf=pd.concat(_all_ros,ignore_index=True)[lambda d:d['TEAM'].isin(ALL_USER_TEAMS)]
                                _first=_adf.groupby(['NAME','TEAM'])['OVR'].first().reset_index().rename(columns={'OVR':'Start'})
                                _last=_adf.groupby(['NAME','TEAM'])['OVR'].last().reset_index().rename(columns={'OVR':'Current'})
                                _car=_first.merge(_last,on=['NAME','TEAM'])
                                _car['Career Δ']=(_car['Current']-_car['Start']).round(1)
                                _car10=_car[_car['Career Δ']>0].nlargest(10,'Career Δ')[['NAME','TEAM','Start','Current','Career Δ']]
                                _car10.columns=['Player','Team','Start OVR','Current OVR','Career Δ']
                                _car_html=""
                                for _ci,(_,_cr) in enumerate(_car10.reset_index(drop=True).iterrows()):
                                    _cpc=get_team_primary_color(str(_cr['Team'])); _clg=get_school_logo_src(str(_cr['Team']))
                                    _clh=f"<img src='{_clg}' style='width:18px;height:18px;object-fit:contain;vertical-align:middle;'/>" if _clg else ""
                                    _car_html+=(f"<tr style='border-bottom:1px solid #0f172a;background:{_cpc}10;'>"
                                        f"<td style='padding:5px 8px;text-align:center;color:#fbbf24;font-family:Bebas Neue,sans-serif;'>#{_ci+1}</td>"
                                        f"<td style='padding:5px 8px;'>{_clh} <span style='font-weight:800;color:#f1f5f9;font-family:Barlow Condensed,sans-serif;font-size:.85rem;'>{html.escape(str(_cr['Player']))}</span></td>"
                                        f"<td style='padding:5px 8px;text-align:center;color:#64748b;font-size:.72rem;'>{html.escape(str(_cr['Team'])[:12])}</td>"
                                        f"<td style='padding:5px 8px;text-align:center;color:#94a3b8;font-size:.72rem;'>{int(_cr['Start OVR'])}</td>"
                                        f"<td style='padding:5px 8px;text-align:center;color:#f1f5f9;font-weight:700;font-size:.78rem;'>{int(_cr['Current OVR'])}</td>"
                                        f"<td style='padding:5px 8px;text-align:center;font-family:Bebas Neue,sans-serif;font-size:.95rem;color:#4ade80;'>+{float(_cr['Career Δ']):.0f}</td>"
                                        f"</tr>")
                                st.markdown(
                                    "<div style='overflow-x:auto;border:1px solid #1e293b;border-radius:10px;background:#0a1220;'>"
                                    "<table style='width:100%;border-collapse:collapse;'><thead><tr style='background:#06090f;'>"
                                    "<th style='padding:6px 8px;color:#475569;font-size:.58rem;'>#</th>"
                                    "<th style='padding:6px 8px;color:#94a3b8;font-size:.58rem;text-align:left;'>Player</th>"
                                    "<th style='padding:6px 8px;color:#475569;font-size:.58rem;'>Team</th>"
                                    "<th style='padding:6px 8px;color:#64748b;font-size:.58rem;'>Start</th>"
                                    "<th style='padding:6px 8px;color:#f1f5f9;font-size:.58rem;'>Now</th>"
                                    "<th style='padding:6px 8px;color:#4ade80;font-size:.58rem;'>Career Δ</th>"
                                    f"</tr></thead><tbody>{_car_html}</tbody></table></div>",
                                    unsafe_allow_html=True)
            except Exception as _tde:
                st.caption(f"Talent Development unavailable: {_tde}")

        with _met_tabs[7]:
            st.header("📊 Dynasty Analytics")
            st.caption("Signature stats from Game Control, Explosive Index, and Beatdown Reality.")
            try:
                _da_gc=pd.DataFrame(); _da_ei=pd.DataFrame(); _da_brc=pd.DataFrame()
                for _p in ['FPI/game_control_by_game_v3.csv','game_control_by_game_v3.csv']:
                    if os.path.exists(_p): _da_gc=pd.read_csv(_p); break
                for _p in ['FPI/explosive_index_by_game.csv','explosive_index_by_game.csv']:
                    if os.path.exists(_p): _da_ei=pd.read_csv(_p); break
                for _p in ['FPI/beatdown_reality_check_by_game.csv','beatdown_reality_check_by_game.csv']:
                    if os.path.exists(_p): _da_brc=pd.read_csv(_p); break
                for _df3 in [_da_gc,_da_ei,_da_brc]:
                    if not _df3.empty:
                        for _c3 in ('USER','TEAM','RESULT'):
                            if _c3 in _df3.columns: _df3[_c3]=_df3[_c3].astype(str).str.strip()
                _da_yr_sel=st.selectbox("Season",[CURRENT_YEAR,CURRENT_YEAR-1],format_func=lambda y:str(y),key="da_yr_sel")
                for _dfc in [_da_gc,_da_ei,_da_brc]:
                    if not _dfc.empty and 'YEAR' in _dfc.columns: _dfc['YEAR']=pd.to_numeric(_dfc['YEAR'],errors='coerce')
                _gc_yr=_da_gc[_da_gc['YEAR'].fillna(-1).astype(int)==_da_yr_sel] if not _da_gc.empty else pd.DataFrame()
                _ei_yr=_da_ei[_da_ei['YEAR'].fillna(-1).astype(int)==_da_yr_sel] if not _da_ei.empty else pd.DataFrame()
                _brc_yr=_da_brc[_da_brc['YEAR'].fillna(-1).astype(int)==_da_yr_sel] if not _da_brc.empty else pd.DataFrame()
                for _dfn in [_gc_yr,_ei_yr,_brc_yr]:
                    for _num_col in ('game_control_score','off_explosive_index','beatdown_reality_score','aerial_nuke_flag','win_was_shakier_than_score_flag','got_worked_flag','quick_strike_flag'):
                        if _num_col in _dfn.columns: _dfn[_num_col]=pd.to_numeric(_dfn[_num_col],errors='coerce').fillna(0)
                _da_metrics=[]
                if not _gc_yr.empty and 'game_control_score' in _gc_yr.columns:
                    _dom=_gc_yr[(_gc_yr['game_control_score']>=80)&(_gc_yr['RESULT']=='W')]
                    if not _dom.empty:
                        _dom_cnt=_dom.groupby('USER').size(); _dt=_dom_cnt.idxmax()
                        _da_metrics.append(('🔥 Most Dominant Wins',f"{_dt}: {int(_dom_cnt[_dt])} dominant W (GC≥80)","game_control_score ≥ 80",'#f97316'))
                    _gc_std=_gc_yr.groupby('USER')['game_control_score'].std().dropna()
                    if not _gc_std.empty:
                        _ct=_gc_std.idxmin()
                        _da_metrics.append(('🎯 Most Consistent',f"{_ct} (σ={_gc_std[_ct]:.1f})","Lowest game control variance",'#4ade80'))
                if not _ei_yr.empty and 'off_explosive_index' in _ei_yr.columns:
                    _ea=_ei_yr.groupby('USER')['off_explosive_index'].mean().dropna()
                    if not _ea.empty:
                        _et=_ea.idxmax()
                        _da_metrics.append(('💥 Most Explosive',f"{_et}: {_ea[_et]:.1f} avg EI","Highest avg explosive index",'#fbbf24'))
                    if 'aerial_nuke_flag' in _ei_yr.columns:
                        _nk=_ei_yr.groupby('USER')['aerial_nuke_flag'].sum()
                        if _nk.max()>0:
                            _nt=_nk.idxmax()
                            _da_metrics.append(('🚀 Air Raid King',f"{_nt}: {int(_nk[_nt])} nuke games","Most aerial nuke flag games",'#38bdf8'))
                if not _brc_yr.empty and 'win_was_shakier_than_score_flag' in _brc_yr.columns:
                    _sw=_brc_yr[_brc_yr['RESULT']=='W'].groupby('USER')['win_was_shakier_than_score_flag'].sum()
                    if not _sw.empty and _sw.max()>0:
                        _st2=_sw.idxmax()
                        _da_metrics.append(('😅 Luckiest Winner',f"{_st2}: {int(_sw[_st2])} shaky wins","Won but shouldn't have by that much",'#a78bfa'))
                if not _brc_yr.empty and 'got_worked_flag' in _brc_yr.columns:
                    _wk=_brc_yr.groupby('USER')['got_worked_flag'].sum()
                    if not _wk.empty and _wk.max()>0:
                        _wt=_wk.idxmax()
                        _da_metrics.append(('💀 Most Demolished',f"{_wt}: got worked {int(_wk[_wt])}x","Most got_worked_flag games",'#ef4444'))
                if _da_metrics:
                    for _mi in range(0,len(_da_metrics),3):
                        _row_m=_da_metrics[_mi:_mi+3]
                        _mcc=st.columns(max(1,len(_row_m)))
                        for _mj,(_mtit,_mval,_mdsc,_mc_c) in enumerate(_row_m):
                            _mcc[_mj].markdown(
                                f"<div style='background:linear-gradient(135deg,{_mc_c}18 0%,#06090f 60%);border:1px solid {_mc_c}40;border-radius:12px;padding:12px 14px;margin-bottom:8px;'>"
                                f"<div style='font-size:.6rem;color:{_mc_c};font-weight:700;letter-spacing:.06em;text-transform:uppercase;margin-bottom:5px;'>{html.escape(_mtit)}</div>"
                                f"<div style='font-weight:900;color:#f1f5f9;font-family:Barlow Condensed,sans-serif;font-size:.98rem;margin-bottom:2px;'>{html.escape(_mval)}</div>"
                                f"<div style='font-size:.58rem;color:#475569;font-style:italic;'>{html.escape(_mdsc)}</div></div>",
                                unsafe_allow_html=True)
                st.markdown("---")
                st.subheader("🕐 Quarter-by-Quarter Scoring")
                st.caption("Average points scored per quarter and 4th-quarter scoring (comeback/closer ability).")
                try:
                    _gs_q=pd.read_csv('game_summaries.csv') if os.path.exists('game_summaries.csv') else pd.DataFrame()
                    if not _gs_q.empty:
                        _gs_q['YEAR']=pd.to_numeric(_gs_q['YEAR'],errors='coerce')
                        _gs_q=_gs_q[_gs_q['YEAR'].fillna(-1).astype(int)==_da_yr_sel].copy()
                        for _qc in ('VIS_Q1','VIS_Q2','VIS_Q3','VIS_Q4','HOME_Q1','HOME_Q2','HOME_Q3','HOME_Q4','VIS_FINAL','HOME_FINAL'):
                            if _qc in _gs_q.columns: _gs_q[_qc]=pd.to_numeric(_gs_q[_qc],errors='coerce')
                        # Build per-user Q rows
                        _q_rows=[]
                        for _,_qr in _gs_q.iterrows():
                            _vu=str(_qr.get('VIS_USER','')).strip(); _hu=str(_qr.get('HOME_USER','')).strip()
                            if _vu and _vu!='nan' and _vu in USER_TEAMS:
                                _q_rows.append({'user':_vu,'Q1':_qr.get('VIS_Q1'),'Q2':_qr.get('VIS_Q2'),'Q3':_qr.get('VIS_Q3'),'Q4':_qr.get('VIS_Q4')})
                            if _hu and _hu!='nan' and _hu in USER_TEAMS:
                                _q_rows.append({'user':_hu,'Q1':_qr.get('HOME_Q1'),'Q2':_qr.get('HOME_Q2'),'Q3':_qr.get('HOME_Q3'),'Q4':_qr.get('HOME_Q4')})
                        if _q_rows:
                            _qdf=pd.DataFrame(_q_rows)
                            for _qc in ('Q1','Q2','Q3','Q4'): _qdf[_qc]=pd.to_numeric(_qdf[_qc],errors='coerce')
                            _q_avg=_qdf.groupby('user')[['Q1','Q2','Q3','Q4']].mean().round(1)
                            _q_avg['Total/G']=_q_avg.sum(axis=1).round(1)
                            _q_avg=_q_avg.sort_values('Total/G',ascending=False)
                            # Render as FPI-style table
                            _q_html=""
                            for _qi,(_qu,_qrow) in enumerate(_q_avg.iterrows()):
                                _qteam=USER_TEAMS.get(_qu,'')
                                _qpc=get_team_primary_color(_qteam)
                                _qlg=get_school_logo_src(_qteam)
                                _qlh=f"<img src='{_qlg}' style='width:20px;height:20px;object-fit:contain;vertical-align:middle;'/>" if _qlg else ""
                                # Best/worst Q highlighting
                                _qs=[_qrow['Q1'],_qrow['Q2'],_qrow['Q3'],_qrow['Q4']]
                                _best_q=_qs.index(max(_qs)); _worst_q=_qs.index(min(_qs))
                                def _qc_fmt(qi,val):
                                    c='#4ade80' if qi==_best_q else ('#f87171' if qi==_worst_q else '#94a3b8')
                                    return f"<td style='padding:5px 8px;text-align:center;font-family:Bebas Neue,sans-serif;font-size:.92rem;color:{c};'>{val:.1f}</td>"
                                _q_html+=(f"<tr style='border-bottom:1px solid #0f172a;background:{_qpc}12;'>"
                                    f"<td style='padding:5px 8px;text-align:center;color:#475569;font-family:Bebas Neue,sans-serif;'>#{_qi+1}</td>"
                                    f"<td style='padding:5px 8px;white-space:nowrap;'>{_qlh} <span style='font-weight:800;color:{_qpc};font-family:Barlow Condensed,sans-serif;font-size:.88rem;'>{html.escape(_qu)}</span></td>"
                                    +_qc_fmt(0,_qrow['Q1'])+_qc_fmt(1,_qrow['Q2'])+_qc_fmt(2,_qrow['Q3'])+_qc_fmt(3,_qrow['Q4'])
                                    +f"<td style='padding:5px 8px;text-align:center;color:#fbbf24;font-weight:900;font-size:.88rem;'>{_qrow['Total/G']:.1f}</td>"
                                    f"</tr>")
                            st.markdown(
                                "<div style='overflow-x:auto;border:1px solid #1e293b;border-radius:10px;background:#0a1220;'>"
                                "<table style='width:100%;border-collapse:collapse;'><thead><tr style='background:#06090f;'>"
                                "<th style='padding:6px 8px;color:#475569;font-size:.6rem;'>#</th>"
                                "<th style='padding:6px 8px;color:#94a3b8;font-size:.6rem;text-align:left;'>Coach</th>"
                                "<th style='padding:6px 8px;color:#60a5fa;font-size:.6rem;'>Q1</th>"
                                "<th style='padding:6px 8px;color:#4ade80;font-size:.6rem;'>Q2</th>"
                                "<th style='padding:6px 8px;color:#f97316;font-size:.6rem;'>Q3</th>"
                                "<th style='padding:6px 8px;color:#f87171;font-size:.6rem;'>Q4</th>"
                                "<th style='padding:6px 8px;color:#fbbf24;font-size:.6rem;'>Pts/G</th>"
                                f"</tr></thead><tbody>{_q_html}</tbody></table></div>",
                                unsafe_allow_html=True)
                            st.caption("🟢 Best quarter avg per coach · 🔴 Worst quarter avg · Best Q4 = strongest closer")
                except Exception as _qe:
                    st.caption(f"Q scoring unavailable: {_qe}")
                st.markdown("---")
                st.subheader(f"📋 {_da_yr_sel} Full Breakdown")
                _stat_rows=[]
                for _du in USER_TEAMS:
                    _row={'Coach':_du}
                    if not _gc_yr.empty and 'game_control_score' in _gc_yr.columns:
                        _ug=_gc_yr[_gc_yr['USER']==_du]
                        _row['Avg GC']=f"{_ug['game_control_score'].mean():.1f}" if not _ug.empty else '--'
                        _row['Dom Wins']=int((_ug['game_control_score']>=80).sum()) if not _ug.empty else 0
                    if not _ei_yr.empty and 'off_explosive_index' in _ei_yr.columns:
                        _ue=_ei_yr[_ei_yr['USER']==_du]
                        _row['Avg EI']=f"{_ue['off_explosive_index'].mean():.1f}" if not _ue.empty else '--'
                        _row['Nukes']=int(_ue['aerial_nuke_flag'].sum()) if not _ue.empty and 'aerial_nuke_flag' in _ue.columns else 0
                    if not _brc_yr.empty and 'beatdown_reality_score' in _brc_yr.columns:
                        _ub=_brc_yr[_brc_yr['USER']==_du]
                        _row['Avg BRC']=f"{_ub['beatdown_reality_score'].mean():.1f}" if not _ub.empty else '--'
                        _row['Shaky W']=int(_ub['win_was_shakier_than_score_flag'].sum()) if not _ub.empty and 'win_was_shakier_than_score_flag' in _ub.columns else 0
                    _stat_rows.append(_row)
                if _stat_rows:
                    st.dataframe(pd.DataFrame(_stat_rows).set_index('Coach'),use_container_width=True)
                # ── Game Summaries Box Score Section ─────────────────────────────
                st.markdown("---")
                st.subheader("🎮 Box Score Theater")
                st.caption("Game-by-game stats from game_summaries.csv. Select any matchup to see the full box score.")
                try:
                    _gs=pd.read_csv('game_summaries.csv') if os.path.exists('game_summaries.csv') else pd.DataFrame()
                    if _gs.empty:
                        st.info("Push game_summaries.csv to the repo to enable Box Score Theater.")
                    else:
                        _gs.columns=[str(c).strip() for c in _gs.columns]
                        _gs['YEAR']=pd.to_numeric(_gs['YEAR'],errors='coerce')
                        _gs['WEEK']=pd.to_numeric(_gs['WEEK'],errors='coerce')
                        _gs_yr=_gs[_gs['YEAR'].fillna(-1).astype(int)==_da_yr_sel].copy()
                        for _nc2 in ('VIS_FINAL','HOME_FINAL','VIS_TOTAL_OFFENSE','HOME_TOTAL_OFFENSE','VIS_RUSH_YDS','HOME_RUSH_YDS','VIS_PASS_YDS','HOME_PASS_YDS','VIS_TURNOVERS','HOME_TURNOVERS','VIS_3RD_CONV','VIS_3RD_ATT','HOME_3RD_CONV','HOME_3RD_ATT','HOME_RUSH_TD','VIS_RUSH_TD','VIS_PASS_TD','HOME_PASS_TD'):
                            if _nc2 in _gs_yr.columns: _gs_yr[_nc2]=pd.to_numeric(_gs_yr[_nc2],errors='coerce')
                        if _gs_yr.empty:
                            st.info(f"No game summaries for {_da_yr_sel}.")
                        else:
                            # User-team games only
                            _gs_user=_gs_yr[(_gs_yr['VIS_USER'].astype(str).str.strip().isin(USER_TEAMS.keys()))|
                                             (_gs_yr['HOME_USER'].astype(str).str.strip().isin(USER_TEAMS.keys()))].copy()
                            _gs_user['_label']=_gs_user.apply(lambda r:
                                f"Wk {int(r['WEEK'])} · {str(r['VISITOR']).strip()} {int(r['VIS_FINAL']) if pd.notna(r['VIS_FINAL']) else '?'} @ "
                                f"{str(r['HOME']).strip()} {int(r['HOME_FINAL']) if pd.notna(r['HOME_FINAL']) else '?'}",axis=1)
                            _gs_sel=st.selectbox("Select Game",_gs_user['_label'].tolist(),key="gs_box_sel")
                            _gs_row=_gs_user[_gs_user['_label']==_gs_sel].iloc[0]
                            # Render box score card
                            _vis=str(_gs_row['VISITOR']).strip(); _hom=str(_gs_row['HOME']).strip()
                            _vf=int(_gs_row['VIS_FINAL']) if pd.notna(_gs_row['VIS_FINAL']) else 0
                            _hf=int(_gs_row['HOME_FINAL']) if pd.notna(_gs_row['HOME_FINAL']) else 0
                            _vc=get_team_primary_color(_vis); _hc=get_team_primary_color(_hom)
                            _vl=get_school_logo_src(_vis); _hl=get_school_logo_src(_hom)
                            _vlh=f"<img src='{_vl}' style='width:32px;height:32px;object-fit:contain;'/>" if _vl else ""
                            _hlh=f"<img src='{_hl}' style='width:32px;height:32px;object-fit:contain;'/>" if _hl else ""
                            _wc2='#4ade80' if _vf>_hf else '#f87171'
                            _hc2='#4ade80' if _hf>_vf else '#f87171'
                            _note=str(_gs_row.get('NOTES','')).strip()
                            # Score header
                            st.markdown(
                                f"<div style='background:linear-gradient(135deg,{_vc}12 0%,#06090f 50%,{_hc}12 100%);"
                                f"border:1px solid #1e293b;border-radius:14px;padding:16px 20px;margin-bottom:10px;'>"
                                f"<div style='display:flex;align-items:center;justify-content:space-between;gap:12px;'>"
                                f"<div style='flex:1;display:flex;align-items:center;gap:8px;'>{_vlh}<div>"
                                f"<div style='font-weight:900;color:{_vc};font-family:Barlow Condensed,sans-serif;font-size:1rem;'>{html.escape(_vis)}</div>"
                                f"<div style='font-size:.62rem;color:#64748b;'>Away</div></div></div>"
                                f"<div style='text-align:center;'><div style='display:flex;align-items:center;gap:8px;'>"
                                f"<span style='font-family:Bebas Neue,sans-serif;font-size:2.5rem;color:{_wc2};line-height:1;'>{_vf}</span>"
                                f"<span style='color:#334155;font-size:1.5rem;'>-</span>"
                                f"<span style='font-family:Bebas Neue,sans-serif;font-size:2.5rem;color:{_hc2};line-height:1;'>{_hf}</span></div>"
                                f"<div style='font-size:.55rem;color:#475569;letter-spacing:.08em;'>FINAL · Wk {int(_gs_row['WEEK'])}</div></div>"
                                f"<div style='flex:1;display:flex;align-items:center;gap:8px;justify-content:flex-end;'><div style='text-align:right;'>"
                                f"<div style='font-weight:900;color:{_hc};font-family:Barlow Condensed,sans-serif;font-size:1rem;'>{html.escape(_hom)}</div>"
                                f"<div style='font-size:.62rem;color:#64748b;'>Home</div></div>{_hlh}</div></div>"
                                +(f"<div style='margin-top:8px;font-size:.72rem;color:#94a3b8;font-style:italic;border-top:1px solid #1e293b;padding-top:8px;'>{html.escape(_note[:120])}</div>" if _note and _note!='nan' else "")
                                +f"</div>",unsafe_allow_html=True)
                            # Q-by-Q scores
                            _q_cols=st.columns(5)
                            for _qi,_ql in enumerate(['Q1','Q2','Q3','Q4','FINAL']):
                                _vq=_gs_row.get(f'VIS_{_ql}' if _ql!='FINAL' else 'VIS_FINAL',None)
                                _hq=_gs_row.get(f'HOME_{_ql}' if _ql!='FINAL' else 'HOME_FINAL',None)
                                _vqs=f"{int(float(_vq))}" if pd.notna(_vq) and str(_vq)!='nan' else "-"
                                _hqs=f"{int(float(_hq))}" if pd.notna(_hq) and str(_hq)!='nan' else "-"
                                _q_cols[_qi].markdown(f"<div style='text-align:center;background:#0a1220;border-radius:8px;padding:6px 4px;'>"
                                    f"<div style='font-size:.58rem;color:#475569;letter-spacing:.08em;'>{_ql}</div>"
                                    f"<div style='font-family:Bebas Neue,sans-serif;font-size:1.1rem;color:{_wc2};'>{_vqs}</div>"
                                    f"<div style='font-family:Bebas Neue,sans-serif;font-size:1.1rem;color:{_hc2};'>{_hqs}</div>"
                                    f"</div>",unsafe_allow_html=True)
                            st.markdown("---")
                            # Full stat grid
                            _stat_pairs=[
                                ("Total Yards","VIS_TOTAL_OFFENSE","HOME_TOTAL_OFFENSE"),
                                ("Rush Yards","VIS_RUSH_YDS","HOME_RUSH_YDS"),
                                ("Pass Yards","VIS_PASS_YDS","HOME_PASS_YDS"),
                                ("Rush TDs","VIS_RUSH_TD","HOME_RUSH_TD"),
                                ("Pass TDs","VIS_PASS_TD","HOME_PASS_TD"),
                                ("1st Downs","VIS_FIRST_DOWNS","HOME_FIRST_DOWNS"),
                                ("3rd Down","VIS_3RD_CONV","HOME_3RD_CONV"),
                                ("Turnovers","VIS_TURNOVERS","HOME_TURNOVERS"),
                                ("Penalties","VIS_PENALTIES","HOME_PENALTIES"),
                                ("TOP (min)","VIS_TOP","HOME_TOP"),
                            ]
                            _gs_rows_html=""
                            for _sn,_vc2,_hc2n in _stat_pairs:
                                _vv=_gs_row.get(_vc2); _hv=_gs_row.get(_hc2n)
                                def _fmt_stat(v,nm):
                                    if not pd.notna(v) or str(v)=='nan': return "--"
                                    if nm=="TOP (min)": return str(v).split(":")[0]+":"+str(v).split(":")[1] if ":" in str(v) else str(v)
                                    try: return str(int(float(v)))
                                    except: return str(v)
                                _vvs=_fmt_stat(_vv,_sn); _hvs=_fmt_stat(_hv,_sn)
                                try:
                                    if _sn=="TOP (min)":
                                        _vm=int(str(_vv).split(":")[0]) if ":" in str(_vv) else float(_vv)
                                        _hm=int(str(_hv).split(":")[0]) if ":" in str(_hv) else float(_hv)
                                        _better_vis=_vm>_hm
                                    elif _sn in ('Turnovers','Penalties'): _better_vis=float(_vv)<float(_hv)
                                    else: _better_vis=float(_vv)>float(_hv)
                                    _vis_fc='#4ade80' if _better_vis else '#94a3b8'; _hom_fc='#4ade80' if not _better_vis else '#94a3b8'
                                except: _vis_fc='#94a3b8'; _hom_fc='#94a3b8'
                                _gs_rows_html+=(f"<tr style='border-bottom:1px solid #0f172a;'>"
                                    f"<td style='padding:5px 10px;text-align:right;font-weight:700;color:{_vis_fc};font-size:.85rem;'>{_vvs}</td>"
                                    f"<td style='padding:5px 10px;text-align:center;color:#475569;font-size:.72rem;'>{html.escape(_sn)}</td>"
                                    f"<td style='padding:5px 10px;text-align:left;font-weight:700;color:{_hom_fc};font-size:.85rem;'>{_hvs}</td>"
                                    f"</tr>")
                            st.markdown(
                                f"<table style='width:100%;border-collapse:collapse;background:#06090f;border-radius:10px;overflow:hidden;'>"
                                f"<thead><tr><th style='padding:6px 10px;text-align:right;color:{_vc};font-size:.75rem;'>{html.escape(_vis)}</th>"
                                f"<th style='padding:6px 10px;text-align:center;color:#334155;font-size:.65rem;'>STAT</th>"
                                f"<th style='padding:6px 10px;text-align:left;color:{_hc};font-size:.75rem;'>{html.escape(_hom)}</th></tr></thead>"
                                f"<tbody>{_gs_rows_html}</tbody></table>",
                                unsafe_allow_html=True)
                except Exception as _gse:
                    st.caption(f"Box Score Theater unavailable: {_gse}")
            except Exception as _dae:
                st.caption(f"Dynasty Analytics unavailable: {_dae}")

# ══════════════════════════════════════════════════════════════════════
# TAB 2 -- ROSTER ATTRITION
# ══════════════════════════════════════════════════════════════════════
with tabs[2]:
    render_roster_attrition_tab()

# ══════════════════════════════════════════════════════════════════════
# COMPATIBILITY SHIMS for Season Recap / User Legacies
# (These sections were built against the original load_data schema)
# ══════════════════════════════════════════════════════════════════════

# Build `years` from scores
years = sorted(pd.to_numeric(scores.get('YEAR', pd.Series(dtype=float)), errors='coerce').dropna().astype(int).unique(), reverse=True)

# Build `meta` column lookup dict
_yr_col  = smart_col(scores, ['YEAR','Year'])
_vt_col  = smart_col(scores, ['Visitor'])
_vs_col  = smart_col(scores, ['Vis Score','V_Pts'])
_ht_col  = smart_col(scores, ['Home'])
_hs_col  = smart_col(scores, ['Home Score','H_Pts'])
_h_yr_col   = smart_col(heisman, ['Year','YEAR']) if heisman is not None and not heisman.empty else 'Year'
_h_pl_col   = smart_col(heisman, ['Player','Winner','NAME']) if heisman is not None and not heisman.empty else 'Player'
_h_sch_col  = smart_col(heisman, ['School','Team','TEAM']) if heisman is not None and not heisman.empty else 'Team'
_h_usr_col  = smart_col(heisman, ['User','USER']) if heisman is not None and not heisman.empty else 'User'
_c_yr_col   = smart_col(coty, ['Year','YEAR']) if coty is not None and not coty.empty else 'Year'
_c_co_col   = smart_col(coty, ['Coach','Winner','Name']) if coty is not None and not coty.empty else 'Coach'
_c_sch_col  = smart_col(coty, ['School','Team']) if coty is not None and not coty.empty else 'Team'
_c_usr_col  = smart_col(coty, ['User','USER']) if coty is not None and not coty.empty else 'User'

meta = {
    'yr': _yr_col, 'vt': _vt_col, 'vs': _vs_col, 'ht': _ht_col, 'hs': _hs_col,
    'h_yr': _h_yr_col, 'h_player': _h_pl_col, 'h_school': _h_sch_col, 'h_user': _h_usr_col,
    'c_yr': _c_yr_col, 'c_coach': _c_co_col, 'c_school': _c_sch_col, 'c_user': _c_usr_col,
}

# r_2041 alias
r_2041 = model_2041.copy() if model_2041 is not None and not model_2041.empty else pd.DataFrame()
ratings = r_2041.copy()
rec = pd.DataFrame()  # recruiting -- load if needed
try: rec = pd.read_csv('recruiting_class_history_all.csv')
except: pass

# _safe_col helper needed by Season Recap
def _safe_col(df, col, default=0):
    if col not in df.columns:
        return pd.Series([default]*len(df), index=df.index, dtype=float)
    val = df[col]
    if isinstance(val, pd.DataFrame): val = val.iloc[:,0]
    return pd.to_numeric(val, errors='coerce').fillna(default)

# load_team_ratings shim
def load_team_ratings(year=None):
    target_year = int(year) if year else CURRENT_YEAR
    _yr_file = f'team_ratings_{target_year}.csv'
    if os.path.exists(_yr_file):
        try:
            tr = pd.read_csv(_yr_file)
            result = {}
            for _, row in tr.iterrows():
                k = str(row.get('TEAM','')).strip().lower()
                if not k: continue
                result[k] = {'OVR': row.get('OVR', row.get('OVERALL',82)), 'OFF': row.get('OFF', row.get('OFFENSE',82)), 'DEF': row.get('DEF', row.get('DEFENSE',82))}
            if result: return result
        except: pass
    try:
        _legacy = pd.read_csv('TeamRatingsHistory.csv')
        _legacy['YEAR'] = pd.to_numeric(_legacy['YEAR'], errors='coerce')
        _yr = _legacy[_legacy['YEAR'].fillna(-1).astype(int)==target_year]
        if _yr.empty: _yr = _legacy[_legacy['YEAR']==_legacy['YEAR'].max()]
        result = {}
        for _, row in _yr.iterrows():
            k = str(row.get('TEAM','')).strip().lower()
            if k: result[k] = {'OVR': row.get('OVR', row.get('OVERALL',82)), 'OFF': row.get('OFF', row.get('OFFENSE',82)), 'DEF': row.get('DEF', row.get('DEFENSE',82))}
        return result
    except: return {}

# estimate_game_line shim
def estimate_game_line(team, opp, model_df, rank_map):
    try:
        _oc = next((c for c in ('Power Index','FPI','OVERALL','RATING') if c in model_df.columns), None)
        _tc = next((c for c in ('TEAM','Team') if c in model_df.columns), 'TEAM')
        if _oc:
            _pi = dict(zip(model_df[_tc].astype(str).str.strip(), pd.to_numeric(model_df[_oc], errors='coerce').fillna(0)))
            diff = _pi.get(team, 0) - _pi.get(opp, 0)
            fav = team if diff > 0 else opp
            return f"{fav} -{abs(diff)*3.5:.0f}", team == fav
    except: pass
    return "EVEN", True

def get_team_record_display(team, model_df, rankings_df):
    try:
        _sched = load_scores_master(CURRENT_YEAR)
        if _sched.empty: return ""
        _fin = _sched[_sched['Status'].astype(str).str.upper()=='FINAL']
        _fin['Vis Score'] = pd.to_numeric(_fin.get('Vis Score'), errors='coerce')
        _fin['Home Score'] = pd.to_numeric(_fin.get('Home Score'), errors='coerce')
        _fin = _fin.dropna(subset=['Vis Score','Home Score'])
        w = len(_fin[(_fin['Visitor'].astype(str).str.strip()==team)&(_fin['Vis Score']>_fin['Home Score'])]) + \
            len(_fin[(_fin['Home'].astype(str).str.strip()==team)&(_fin['Home Score']>_fin['Vis Score'])])
        l_games = len(_fin[(_fin['Visitor'].astype(str).str.strip()==team)|(_fin['Home'].astype(str).str.strip()==team)]) - w
        return f"{w}-{l_games}"
    except: return ""

# ══════════════════════════════════════════════════════════════════════
# TAB 3 -- SEASON RECAP
# ══════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.header("📺 Season Recap")
    _recap_default = (CURRENT_YEAR - 1) if CURRENT_WEEK_NUMBER < 13 else CURRENT_YEAR
    _recap_default = _recap_default if _recap_default in years else (years[-1] if years else CURRENT_YEAR)
    _recap_default_idx = years.index(_recap_default) if _recap_default in years else max(0, len(years)-1)
    sel_year = int(st.selectbox("Select Season", years, index=_recap_default_idx, key="season_year"))
    y_data = scores[scores[meta['yr']].astype(int) == sel_year].copy()

    # 1. DATA LOADING & STAT ENGINE
    try:
        # Load ratings for the SELECTED season year, not current model year
        _yr_ratings_map = load_team_ratings(year=sel_year)
        _ratings = {str(k).strip(): int(float(v.get('OVR', v.get('OVERALL', 0)) or 0))
                    for k, v in _yr_ratings_map.items()} if _yr_ratings_map else {}
        # Fallback: if no historical ratings for that year, try model_2041
        if not _ratings:
            ovr_col = next((c for c in model_2041.columns if 'OVR' in str(c).upper() or 'OVERALL' in str(c).upper()), None)
            team_col = next((c for c in model_2041.columns if 'TEAM' in str(c).upper()), 'TEAM')
            _ratings = dict(zip(_safe_col(model_2041, team_col, '').astype(str).str.strip(), _safe_col(model_2041, ovr_col, 0))) if ovr_col else {}
        
        heisman_all = pd.read_csv('Heisman_Finalists.csv')
        heisman_all = heisman_all[heisman_all['YEAR'].astype(int) == sel_year].copy()
    except:
        _ratings = {}; heisman_all = pd.DataFrame()

    def format_heisman_stats(row):
        """Builds a position-specific stat line from CSV columns."""
        pos = str(row.get('POS', '')).upper()
        parts = []
        
        def _fmt(val, label):
            if pd.notnull(val) and val != 0:
                # Format as int if possible
                return f"{int(val)} {label}"
            return None

        if pos == 'QB':
            parts += [f"{_fmt(row.get('PASS_YDS'), 'Yds')}", f"{_fmt(row.get('PASS_TD'), 'TD')}", f"{_fmt(row.get('PASS_INT'), 'Int')}"]
            r_yds = _fmt(row.get('RUSH_YDS'), 'Rush Yds')
            if r_yds: parts.append(r_yds)
        elif pos in ['HB', 'RB']:
            parts += [f"{_fmt(row.get('RUSH_YDS'), 'Yds')}", f"{_fmt(row.get('RUSH_TD'), 'TD')}", f"{_fmt(row.get('REC_YDS'), 'Rec Yds')}"]
        elif pos in ['WR', 'TE']:
            parts += [f"{_fmt(row.get('CATCHES'), 'Rec')}", f"{_fmt(row.get('REC_YDS'), 'Yds')}", f"{_fmt(row.get('REC_TD'), 'TD')}"]
        
        # Filter out Nones and join
        valid_parts = [p for p in parts if p and 'None' not in p]
        return " | ".join(valid_parts) if valid_parts else "Stats Pending"

    # 2. HELPER FUNCTIONS
    def _award_logo_tag(team, size=48):
        uri = image_file_to_data_uri(get_logo_source(team)) if team else None
        return f"<img src='{uri}' style='width:{size}px;height:{size}px;object-fit:contain;'/>" if uri else "🏈"

    def _award_card(accent, logo_tag, badge, line1, line2, line3='', stats=''):
        stat_div = f"<div style='margin-top:8px; padding-top:6px; border-top:1px solid {accent}33; font-size:0.7rem; color:#f1f5f9; font-family:monospace; font-weight:600;'>{html.escape(stats)}</div>" if stats else ""
        return (
            f"<div style='background:linear-gradient(135deg,{accent}22,#0f172a); border:1px solid {accent}55; border-radius:12px; padding:14px 16px; display:flex; align-items:center; gap:12px;'>"
            f"{logo_tag}<div style='min-width:0;'><div style='font-size:0.6rem; color:#94a3b8; letter-spacing:.08em; font-weight:700; margin-bottom:3px;'>{badge}</div>"
            f"<div style='font-weight:900; color:{accent}; font-size:0.92rem; line-height:1.25; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{html.escape(line1)}</div>"
            f"<div style='font-size:0.72rem; color:#94a3b8; margin-top:1px;'>{html.escape(line2)}</div>{line3 if line3 else ''}{stat_div}</div></div>"
        )

    # 3. AWARDS LOGIC
    award_champ = "TBD"; champ_team = ""; path_to_title = []
    try:
        _b_results = pd.read_csv('CFPbracketresults.csv')
        _ncg = _b_results[(_b_results['YEAR'].astype(int) == sel_year) & (_b_results['ROUND'].str.strip() == 'NCG') & (_b_results['COMPLETED'] == 1)]
        if not _ncg.empty:
            award_champ = str(_ncg.iloc[0]['WINNER']).strip()
            champ_team = award_champ
            _my_wins = _b_results[(_b_results['YEAR'].astype(int) == sel_year) & (_b_results['WINNER'].str.strip() == champ_team) & (_b_results['COMPLETED'] == 1)]
            _rd_order = {'R1': 1, 'QF': 2, 'SF': 3, 'NCG': 4}
            _my_wins = _my_wins.copy(); _my_wins['_rd_sort'] = _my_wins['ROUND'].str.strip().map(_rd_order); _my_wins = _my_wins.sort_values('_rd_sort')
            for _, _wg in _my_wins.iterrows():
                _is_t1 = str(_wg['TEAM1']).strip() == champ_team
                _opp = str(_wg['TEAM2']).strip() if _is_t1 else str(_wg['TEAM1']).strip()
                _my_s, _opp_s = (int(_wg['TEAM1_SCORE']), int(_wg['TEAM2_SCORE'])) if _is_t1 else (int(_wg['TEAM2_SCORE']), int(_wg['TEAM1_SCORE']))
                path_to_title.append(f"{str(_wg['ROUND']).strip()}: def. {_opp} ({_my_s}-{_opp_s})")
    except: pass

    # Heisman Banner
    if not heisman_all.empty:
        _winner_row = heisman_all[heisman_all['FINISH'].astype(int) == 1].iloc[0]
        he_p = f"{str(_winner_row['NAME'])} ({str(_winner_row.get('POS', '--'))})"
        he_t, he_u = str(_winner_row['TEAM']), str(_winner_row.get('USER', ''))
        he_stats = format_heisman_stats(_winner_row)
    else: he_p, he_t, he_u, he_stats = "TBD", "", "", ""

    coty_row = coty[coty[meta['c_yr']].astype(int) == sel_year]
    co_c = str(coty_row.iloc[0][meta['c_coach']]) if not coty_row.empty else "TBD"
    co_t = str(coty_row.iloc[0][meta['c_school']]) if not coty_row.empty else ""

    # 4. RENDER BANNER
    _c_col, _h_col, _ct_col = [get_team_primary_color(t) if t else '#fbbf24' for t in [champ_team, he_t, co_t]]
    path_html = "".join([f"<div style='font-size:0.62rem; color:#94a3b8; line-height:1.2; margin-top:1px;'>• {p}</div>" for p in path_to_title])
    if path_html: path_html = f"<div style='margin-top:8px; border-top:1px solid {_c_col}33; padding-top:6px;'>{path_html}</div>"

    awards_html = (
        "<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:10px; margin-bottom:16px;'>"
        + _award_card(_c_col, _award_logo_tag(champ_team, 52), "🏆 NATIONAL CHAMPION", award_champ, "", line3=path_html)
        + _award_card(_h_col, _award_logo_tag(he_t, 52), "🏅 HEISMAN WINNER", he_p, f"{he_t} ({he_u})", stats=he_stats)
        + _award_card(_ct_col, _award_logo_tag(co_t, 52), "🎓 COACH OF THE YEAR", co_c, f"{co_t}")
        + "</div>"
    )
    st.markdown(awards_html, unsafe_allow_html=True)

    # 5. USER BATTLES (Upset Detection) -- user vs user ONLY
    if not y_data.empty:
        _known_users = set(str(u).strip().title() for u in USER_TEAMS.keys())
        user_games = y_data[
            (y_data['V_User_Final'].astype(str).str.strip().str.title().isin(_known_users)) &
            (y_data['H_User_Final'].astype(str).str.strip().str.title().isin(_known_users)) &
            (y_data['V_User_Final'] != y_data['H_User_Final'])
        ].copy()
        if not user_games.empty:
            st.markdown(f"#### ⚔️ User Battles of {sel_year}")
            for _, _g in user_games.iterrows():
                vt, ht = str(_g['Visitor_Final']).strip(), str(_g['Home_Final']).strip()
                v_ovr = _ratings.get(vt.lower(), _ratings.get(vt, 0))
                h_ovr = _ratings.get(ht.lower(), _ratings.get(ht, 0))
                is_upset = (int(_g['V_Pts']) > int(_g['H_Pts']) and v_ovr < h_ovr - 2) or (int(_g['H_Pts']) > int(_g['V_Pts']) and h_ovr < v_ovr - 2)
                badge = f"<span style='background:#ef4444;color:white;font-size:0.6rem;padding:2px 6px;border-radius:4px;margin-left:8px;font-weight:900;'>🔥 UPSET (+{abs(v_ovr-h_ovr)})</span>" if is_upset else ""
                st.markdown(f"<div style='display:flex;align-items:center;gap:8px;padding:8px 10px;background:#0a1628;border-radius:8px;border:1px solid #1e293b;margin-bottom:5px;'>"
                            f"<div style='display:flex;align-items:center;gap:6px;flex:1;'>{_award_logo_tag(vt, 28)}<div><div style='color:{get_team_primary_color(vt)};font-size:0.8rem;font-weight:800;'>{html.escape(vt)}</div><div style='font-size:0.62rem;color:#475569;'>{int(v_ovr)} OVR</div></div></div>"
                            f"<div style='text-align:center;min-width:110px;'><div style='font-weight:900;font-size:1.1rem;color:#f1f5f9;'>{int(_g['V_Pts'])} &ndash; {int(_g['H_Pts'])}</div>{badge}</div>"
                            f"<div style='display:flex;align-items:center;gap:6px;flex:1;justify-content:flex-end;'><div style='text-align:right;'><div style='color:{get_team_primary_color(ht)};font-size:0.8rem;font-weight:800;'>{html.escape(ht)}</div><div style='font-size:0.62rem;color:#475569;'>{int(h_ovr)} OVR</div></div>{_award_logo_tag(ht, 28)}</div></div>", unsafe_allow_html=True)

    # 6. HEISMAN LEADERBOARD (Vertical Stack with Custom Stats)
    if not heisman_all.empty:
        st.markdown("#### 🏆 Heisman Voting Results")
        leaderboard = heisman_all.sort_values('FINISH')
        
        for idx, _f in leaderboard.head(5).reset_index(drop=True).iterrows():
            _ft = str(_f['TEAM']).strip()
            _f_color = get_team_primary_color(_ft)
            _finish = int(_f['FINISH'])
            _stats = format_heisman_stats(_f)
            
            _bg = "#1e293b" if _finish == 1 else "#0f172a"
            _bw = "6px" if _finish == 1 else "4px"
            stat_html = f"<div style='margin-top:8px; padding-top:6px; border-top:1px solid {_f_color}33; font-size:0.75rem; color:#cbd5e1; font-family:monospace; font-weight:600;'>📊 {_stats}</div>" if _stats else ""

            st.markdown(f"""
            <div style='background:{_bg}; border:1px solid #1e293b; border-left:{_bw} solid {_f_color}; border-radius:10px; padding:14px 18px; display:flex; align-items:center; gap:12px; margin-bottom:8px;'>
              <div style='flex-shrink:0; background:#0a1628; padding:4px; border-radius:6px;'>{_award_logo_tag(_ft, size=34)}</div>
              <div style='flex:1; min-width:0;'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                  <div style='font-weight:900; font-size:1.05rem; color:white;'>{html.escape(str(_f['NAME']))} {"👑" if _finish == 1 else ""}</div>
                  <div style='font-weight:800; color:{_f_color if _finish == 1 else "#94a3b8"}; font-size:0.95rem;'>#{_finish}</div>
                </div>
                <div style='font-size:0.75rem; color:#94a3b8; margin-top:2px;'>{html.escape(_ft)} • {str(_f.get('POS','--'))} • {str(_f.get('USER','CPU'))}</div>
                {stat_html}
              </div>
            </div>""", unsafe_allow_html=True)

# --- ALL-AMERICANS ---
    st.markdown("---")
    st.subheader(f"🏅 {sel_year} All-Americans")

    try:
        aa_df = pd.read_csv("all_americans.csv")
    except Exception:
        aa_df = pd.DataFrame(columns=["Year", "TeamType", "Pos", "Player", "School", "Class"])

    for col in ["Year", "TeamType", "Pos", "Player", "School", "Class"]:
        if col not in aa_df.columns:
            aa_df[col] = pd.NA

    aa_df["Year"] = pd.to_numeric(aa_df["Year"], errors="coerce")
    aa_df["TeamType"] = (
        aa_df["TeamType"]
        .astype(str)
        .str.strip()
        .replace({
            "First Team": "1st Team",
            "Second Team": "2nd Team",
            "Freshman Team": "Freshman"
        })
    )
    aa_df["Pos"] = aa_df["Pos"].astype(str).str.strip()
    aa_df["Player"] = aa_df["Player"].astype(str).str.strip()
    aa_df["School"] = aa_df["School"].astype(str).str.strip()
    aa_df["Class"] = aa_df["Class"].astype(str).str.strip()

    user_team_map = USER_TEAMS if 'USER_TEAMS' in globals() else {}
    team_to_user = {str(team).strip(): str(user).strip() for user, team in user_team_map.items()}
    user_team_set = set(team_to_user.keys())

    def get_school_logo_src(team_name):
        try:
            logo_path = get_logo_source(team_name)
            if logo_path:
                uri = image_file_to_data_uri(logo_path)
                if uri:
                    return uri
        except Exception:
            pass
        return None

    def prep_aa_table(df_in):
        if df_in.empty:
            return df_in

        out = df_in.copy()
        out.insert(0, "Logo", out["School"].map(get_school_logo_src))
        out["User"] = out["School"].map(lambda x: team_to_user.get(str(x).strip(), ""))
        return out

    recap_year = sel_year
    aa_year_df = aa_df[aa_df["Year"] == recap_year].copy()

    if aa_year_df.empty:
        st.caption("No All-Americans logged for this season yet.")
    else:
        aa_tabs = st.tabs(["🥇 1st Team", "🥈 2nd Team", "🌟 Freshman"])

        with aa_tabs[0]:
            first_df = prep_aa_table(aa_year_df[aa_year_df["TeamType"] == "1st Team"].copy())
            if first_df.empty:
                st.caption("No 1st Team rows found.")
            else:
                st.dataframe(
                    first_df[["Logo", "Pos", "Player", "School", "Class", "User"]],
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Logo": st.column_config.ImageColumn(""),
                        "Pos": st.column_config.TextColumn("Pos", width="small"),
                        "Player": st.column_config.TextColumn("Player", width="medium"),
                        "School": st.column_config.TextColumn("School", width="medium"),
                        "Class": st.column_config.TextColumn("Class", width="small"),
                        "User": st.column_config.TextColumn("User", width="small"),
                    }
                )

        with aa_tabs[1]:
            second_df = prep_aa_table(aa_year_df[aa_year_df["TeamType"] == "2nd Team"].copy())
            if second_df.empty:
                st.caption("No 2nd Team rows found.")
            else:
                st.dataframe(
                    second_df[["Logo", "Pos", "Player", "School", "Class", "User"]],
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Logo": st.column_config.ImageColumn(""),
                        "Pos": st.column_config.TextColumn("Pos", width="small"),
                        "Player": st.column_config.TextColumn("Player", width="medium"),
                        "School": st.column_config.TextColumn("School", width="medium"),
                        "Class": st.column_config.TextColumn("Class", width="small"),
                        "User": st.column_config.TextColumn("User", width="small"),
                    }
                )

        with aa_tabs[2]:
            fresh_df = prep_aa_table(aa_year_df[aa_year_df["TeamType"] == "Freshman"].copy())
            if fresh_df.empty:
                st.caption("No Freshman rows found.")
            else:
                st.dataframe(
                    fresh_df[["Logo", "Pos", "Player", "School", "Class", "User"]],
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "Logo": st.column_config.ImageColumn(""),
                        "Pos": st.column_config.TextColumn("Pos", width="small"),
                        "Player": st.column_config.TextColumn("Player", width="medium"),
                        "School": st.column_config.TextColumn("School", width="medium"),
                        "Class": st.column_config.TextColumn("Class", width="small"),
                        "User": st.column_config.TextColumn("User", width="small"),
                    }
                )

    # --- HIGHEST RATED GAMES ---
    st.markdown("---")
    st.subheader(f"📺 Highest Rated Games of {sel_year}")
    st.caption("Viewership formula based on matchup stakes, rankings, rivalry, margin, and game context.")

    try:
        _rc_scores_df = load_scores_master(sel_year)
        _rc_scores_df["YEAR"] = pd.to_numeric(_rc_scores_df["YEAR"], errors="coerce")
        _rc_scores_df["Week"] = pd.to_numeric(_rc_scores_df["Week"], errors="coerce")
        _rc_scores_df["Vis Score"] = pd.to_numeric(_rc_scores_df["Vis Score"], errors="coerce")
        _rc_scores_df["Home Score"] = pd.to_numeric(_rc_scores_df["Home Score"], errors="coerce")
        _rc_scores_df["Visitor Rank"] = pd.to_numeric(_rc_scores_df["Visitor Rank"], errors="coerce")
        _rc_scores_df["Home Rank"] = pd.to_numeric(_rc_scores_df["Home Rank"], errors="coerce")

        # Use CFP ranking snapshots if available
        _GLOBAL_WEEK_RANK_LOOKUP = {}
        try:
            _cfp_h2=pd.read_csv('cfp_rankings_history.csv')
            for _,_rr in _cfp_h2.iterrows():
                _rteam=str(_rr.get('TEAM','')).strip().lower()
                _ryr=int(_rr.get('YEAR',0) or 0)
                _rwk=int(_rr.get('WEEK',0) or 0)
                _rrk=int(_rr.get('RANK',99) or 99)
                _GLOBAL_WEEK_RANK_LOOKUP[(_rteam,_ryr,_rwk)]=_rrk
        except: pass
        if _GLOBAL_WEEK_RANK_LOOKUP:
            _rc_scores_df["Visitor Rank Snapshot"] = _rc_scores_df.apply(
                lambda r: get_rank_at_week(r.get("Visitor",""), r.get("Week",0), r.get("YEAR", sel_year)), axis=1)
            _rc_scores_df["Home Rank Snapshot"] = _rc_scores_df.apply(
                lambda r: get_rank_at_week(r.get("Home",""), r.get("Week",0), r.get("YEAR", sel_year)), axis=1)
        else:
            _rc_scores_df["Visitor Rank Snapshot"] = _rc_scores_df["Visitor Rank"]
            _rc_scores_df["Home Rank Snapshot"] = _rc_scores_df["Home Rank"]

        _rc_cy = _rc_scores_df[
            (_rc_scores_df["YEAR"] == sel_year) &
            (_rc_scores_df["Status"].astype(str).str.upper() == "FINAL")
        ].dropna(subset=["Vis Score","Home Score"]).copy()

        _rc_cy["Vis_User"] = _rc_cy["Vis_User"].astype(str).str.strip().str.title()
        _rc_cy["Home_User"] = _rc_cy["Home_User"].astype(str).str.strip().str.title()

        _rc_tv_rows = []
        for _, _rrow in _rc_cy.iterrows():
            try:
                _vs = float(_rrow["Vis Score"]); _hs = float(_rrow["Home Score"])
                _vr = float(_rrow["Visitor Rank Snapshot"]) if not pd.isna(_rrow.get("Visitor Rank Snapshot")) else 99
                _hr = float(_rrow["Home Rank Snapshot"]) if not pd.isna(_rrow.get("Home Rank Snapshot")) else 99
                _margin = abs(_vs - _hs); _total = _vs + _hs
                _vu = str(_rrow.get("Vis_User","")).strip(); _hu = str(_rrow.get("Home_User","")).strip()
                _is_user = (_vu in USER_TEAMS) or (_hu in USER_TEAMS)
                _is_h2h  = (_vu in USER_TEAMS) and (_hu in USER_TEAMS)
                _wk = float(_rrow.get("Week",0) or 0)
                _is_playoff   = _wk >= 16
                _is_conf_champ = str(_rrow.get("Conf Title","0")).strip() in ("1","Yes","yes")
                _is_natty      = str(_rrow.get("Natty Game","0")).strip().upper() in ("1","YES")
                _top_rank = min(_vr,_hr); _both = _vr<=25 and _hr<=25
                _base = 2.0
                if _top_rank<=5:   _base+=6.5
                elif _top_rank<=10: _base+=4.5
                elif _top_rank<=15: _base+=2.8
                elif _top_rank<=25: _base+=1.5
                if _both: _base+=2.5
                if _margin<=3: _base+=3.5
                elif _margin<=7: _base+=2.0
                elif _margin<=14: _base+=0.8
                if _is_user: _base+=1.5
                if _is_h2h:  _base+=2.0
                if _is_conf_champ: _base+=2.0
                if _is_playoff:    _base+=3.0
                if _is_natty:      _base+=5.0
                if _total>=80: _base+=1.5
                elif _total>=60: _base+=0.8
                _rc_tv_rows.append({
                    "rating": round(_base, 2),
                    "Visitor": str(_rrow.get("Visitor","")), "Home": str(_rrow.get("Home","")),
                    "Vis Score": int(_vs), "Home Score": int(_hs),
                    "Visitor Rank": int(_vr) if _vr<99 else None,
                    "Home Rank": int(_hr) if _hr<99 else None,
                    "Week": int(_wk), "Vis_User": _vu, "Home_User": _hu,
                    "Conf Title": _rrow.get("Conf Title",0),
                    "Natty Game": _rrow.get("Natty Game",0),
                })
            except Exception:
                pass

        if _rc_tv_rows:
            _rc_top = sorted(_rc_tv_rows, key=lambda x: x["rating"], reverse=True)[:10]
            for _ri, _rg in enumerate(_rc_top, 1):
                _rvis = _rg["Visitor"]; _rhom = _rg["Home"]
                _rvs  = _rg["Vis Score"]; _rhs = _rg["Home Score"]
                _rvr  = f"#{_rg['Visitor Rank']} " if _rg["Visitor Rank"] else ""
                _rhr  = f"#{_rg['Home Rank']} " if _rg["Home Rank"] else ""
                _winner = _rvis if _rvs > _rhs else _rhom
                _rvu  = _rg["Vis_User"]; _rhu  = _rg["Home_User"]
                _rv_color = get_team_primary_color(_rvis) if _rvu in USER_TEAMS else "#94a3b8"
                _rh_color = get_team_primary_color(_rhom) if _rhu in USER_TEAMS else "#94a3b8"
                _r_rating = _rg["rating"]
                _wk_lbl = "Conf Champ" if str(_rg.get("Conf Title","0")) in ("1","1.0") else \
                          ("Natty" if str(_rg.get("Natty Game","0")) in ("1","1.0") else f"Wk {_rg['Week']}")
                _ri_col = "#fbbf24" if _ri==1 else ("#9ca3af" if _ri==2 else ("#b45309" if _ri==3 else "#475569"))
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:10px;padding:8px 12px;"
                    f"background:linear-gradient(90deg,#0d1117 0%,#080d14 100%);"
                    f"border-left:3px solid {_ri_col};border-radius:6px;margin-bottom:4px;'>"
                    f"<span style='font-family:Bebas Neue,sans-serif;font-size:1.3rem;color:{_ri_col};"
                    f"min-width:28px;text-align:center;'>{_ri}</span>"
                    f"<div style='flex:1;min-width:0;'>"
                    f"<div style='font-size:0.85rem;font-weight:800;color:#f1f5f9;'>"
                    f"<span style='color:{_rv_color};'>{html.escape(_rvr+_rvis)}</span>"
                    f"<span style='color:#475569;font-weight:400;'> vs </span>"
                    f"<span style='color:{_rh_color};'>{html.escape(_rhr+_rhom)}</span>"
                    f"</div>"
                    f"<div style='font-size:0.72rem;color:#64748b;'>{_wk_lbl}</div>"
                    f"</div>"
                    f"<span style='font-family:Barlow Condensed,sans-serif;font-weight:900;"
                    f"font-size:1.1rem;color:#f1f5f9;'>"
                    f"{'<span style=\"color:#4ade80;\">' if _rvs>_rhs else ''}{_rvs}"
                    f"{'</span>' if _rvs>_rhs else ''}"
                    f"<span style='color:#475569;'> - </span>"
                    f"{'<span style=\"color:#4ade80;\">' if _rhs>_rvs else ''}{_rhs}"
                    f"{'</span>' if _rhs>_rvs else ''}</span>"
                    f"<span style='font-size:0.78rem;color:#fbbf24;font-weight:700;margin-left:8px;'>"
                    f"📺 {_r_rating:.1f}M</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
        else:
            st.caption(f"No completed games found for {sel_year}.")
    except Exception as _rc_tv_err:
        st.caption(f"Could not load game ratings: {_rc_tv_err}")

    # --- TEAM OVERVIEW ---




# ══════════════════════════════════════════════════════════════════════
# TAB 4 -- USER LEGACIES (H2H Matrix, ISPN Classics, GOAT Rankings)
# Dynasty YouTube dropped.
# ══════════════════════════════════════════════════════════════════════
with tabs[4]:
    _ul_tabs = st.tabs(["⚔️ H2H Matrix", "🎬 ISPN Classics", "🐐 GOAT Rankings"])

    # --- H2H MATRIX ---
with _ul_tabs[0]:
        st.header("⚔️ Head-to-Head Matrix")
        st.caption("All-time user vs. user records. Net Edge = wins minus losses. Rivalry Score weights game count and balance.")

        # ── FULL GRID -- one card per matchup cell ─────────────────────────────────
        st.subheader("📊 All-Time H2H Grid")

        # Build sorted user list with current team info for logo + color
        _h2h_user_info = {}
        for _, _mr in model_2041.iterrows():
            _h2h_user_info[str(_mr['USER'])] = {
                'team': str(_mr['TEAM']),
                'color': get_team_primary_color(str(_mr['TEAM'])),
                'logo_uri': image_file_to_data_uri(get_logo_source(str(_mr['TEAM']))),
            }

        _h2h_users = sorted(all_users)

        # Header row -- opponent logos
        _header_cells = "<td style='padding:6px;'></td>"
        for _opp in _h2h_users:
            _opp_info = _h2h_user_info.get(_opp, {})
            _opp_tc   = _opp_info.get('color', '#6b7280')
            _opp_lu   = _opp_info.get('logo_uri', '')
            _logo_tag  = (f"<img src='{_opp_lu}' style='width:28px;height:28px;"
                          f"object-fit:contain;'/>" if _opp_lu else "🏈")
            _header_cells += (
                f"<td style='text-align:center;padding:6px;'>"
                f"<div style='display:flex;flex-direction:column;align-items:center;gap:2px;'>"
                f"{_logo_tag}"
                f"<span style='font-size:0.6rem;color:{_opp_tc};font-weight:700;white-space:nowrap;'>"
                f"{html.escape(_opp)}</span></div></td>"
            )

        # Data rows
        _data_rows = ""
        for _usr in _h2h_users:
            _usr_info = _h2h_user_info.get(_usr, {})
            _usr_tc   = _usr_info.get('color', '#6b7280')
            _usr_lu   = _usr_info.get('logo_uri', '')
            _usr_logo = (f"<img src='{_usr_lu}' style='width:28px;height:28px;"
                         f"object-fit:contain;'/>" if _usr_lu else "🏈")

            _row_cells = (
                f"<td style='padding:6px 8px;white-space:nowrap;border-right:1px solid #1e293b;'>"
                f"<div style='display:flex;align-items:center;gap:6px;'>"
                f"{_usr_logo}"
                f"<span style='font-size:0.72rem;font-weight:700;color:{_usr_tc};'>"
                f"{html.escape(_usr)}</span></div></td>"
            )

            _usr_h2h_row = h2h_df[h2h_df['User'] == _usr]

            for _opp in _h2h_users:
                if _usr == _opp:
                    _row_cells += (
                        "<td style='text-align:center;padding:6px;"
                        "background:#1e293b;'>"
                        "<span style='color:#374151;font-size:1rem;'>&#8212;</span></td>"
                    )
                    continue
                try:
                    _rec = _usr_h2h_row[_opp].iloc[0] if not _usr_h2h_row.empty else "0-0"
                    _net = int(h2h_heat.loc[_usr, _opp])
                    _parts = str(_rec).split('-')
                    _w = int(_parts[0]) if len(_parts) == 2 else 0
                    _l = int(_parts[1]) if len(_parts) == 2 else 0
                except Exception:
                    _rec, _w, _l, _net = "0-0", 0, 0, 0
                _cell_bg = ("#0d2b0d" if _net > 0 else
                            "#2b0d0d" if _net < 0 else "#111827")
                _rec_color = ("#22c55e" if _net > 0 else
                              "#f87171" if _net < 0 else "#94a3b8")
                _net_str = (f"+{_net}" if _net > 0 else
                            str(_net) if _net < 0 else "Even")
                _row_cells += (
                    f"<td style='text-align:center;padding:6px 8px;"
                    f"background:{_cell_bg};'>"
                    f"<div style='font-weight:900;font-size:0.82rem;color:{_rec_color};'>"
                    f"{html.escape(str(_rec))}</div>"
                    f"<div style='font-size:0.58rem;color:#475569;'>{_net_str}</div>"
                    f"</td>"
                )
            _data_rows += f"<tr style='border-bottom:1px solid #0f172a;'>{_row_cells}</tr>"

        st.markdown(
            f"<div style='overflow-x:auto;border:1px solid #1e293b;"
            f"border-radius:12px;background:#0f172a;'>"
            f"<table style='width:100%;border-collapse:collapse;font-size:13px;'>"
            f"<thead><tr style='background:#111827;'>{_header_cells}</tr></thead>"
            f"<tbody>{_data_rows}</tbody></table></div>",
            unsafe_allow_html=True
        )

        # ── AVERAGE MARGIN OF VICTORY MATRIX ─────────────────────────────────────
        st.markdown("---")
        st.subheader("📐 Average Margin of Victory")
        st.caption("Average point differential when these two coaches face off. Positive = row coach wins by that margin on average.")
        try:
            _all_scores=load_scores_master(multi_year=True)
            _all_scores.columns=[str(c).strip() for c in _all_scores.columns]
            _vu_c=next((c for c in _all_scores.columns if 'vis' in c.lower() and 'user' in c.lower()),None)
            _hu_c=next((c for c in _all_scores.columns if 'home' in c.lower() and 'user' in c.lower()),None)
            _vs_c=next((c for c in _all_scores.columns if c in ('Vis Score','Vis_Score','V_Pts')),None)
            _hs_c=next((c for c in _all_scores.columns if c in ('Home Score','Home_Score','H_Pts')),None)
            if _vu_c and _hu_c and _vs_c and _hs_c:
                _all_scores['_vu']=_all_scores[_vu_c].astype(str).str.strip().str.title()
                _all_scores['_hu']=_all_scores[_hu_c].astype(str).str.strip().str.title()
                _all_scores['_vs']=pd.to_numeric(_all_scores[_vs_c],errors='coerce')
                _all_scores['_hs']=pd.to_numeric(_all_scores[_hs_c],errors='coerce')
                _g=_all_scores[(_all_scores['_vu'].isin(_h2h_users))&(_all_scores['_hu'].isin(_h2h_users))].dropna(subset=['_vs','_hs'])
                # Build avg margin grid
                _mar_header="<td style='padding:6px;'></td>"
                for _opp2 in _h2h_users:
                    _opp_inf2=_h2h_user_info.get(_opp2,{})
                    _opp_lu2=_opp_inf2.get('logo_uri','')
                    _opp_tc2=_opp_inf2.get('color','#6b7280')
                    _lg2=f"<img src='{_opp_lu2}' style='width:24px;height:24px;object-fit:contain;'/>" if _opp_lu2 else '🏈'
                    _mar_header+=f"<td style='text-align:center;padding:5px;'><div style='display:flex;flex-direction:column;align-items:center;gap:1px;'>{_lg2}<span style='font-size:.55rem;color:{_opp_tc2};font-weight:700;'>{html.escape(_opp2)}</span></div></td>"
                _mar_rows=''
                for _usr2 in _h2h_users:
                    _ui2=_h2h_user_info.get(_usr2,{}); _ul2=_ui2.get('logo_uri',''); _uc2=_ui2.get('color','#6b7280')
                    _ul_img=f"<img src='{_ul2}' style='width:24px;height:24px;object-fit:contain;'/>" if _ul2 else '🏈'
                    _row='<td style="padding:5px 8px;border-right:1px solid #1e293b;">'
                    _row+=f"<div style='display:flex;align-items:center;gap:5px;'>{_ul_img}<span style='font-size:.68rem;font-weight:700;color:{_uc2};'>{html.escape(_usr2)}</span></div></td>"
                    for _opp2 in _h2h_users:
                        if _usr2==_opp2:
                            _row+="<td style='text-align:center;padding:5px;background:#1e293b;'><span style='color:#374151;'>—</span></td>"
                            continue
                        # As visitor
                        _gv=_g[(_g['_vu']==_usr2)&(_g['_hu']==_opp2)]
                        _margins_v=(_gv['_vs']-_gv['_hs']).tolist()
                        # As home
                        _gh=_g[(_g['_hu']==_usr2)&(_g['_vu']==_opp2)]
                        _margins_h=(_gh['_hs']-_gh['_vs']).tolist()
                        _all_m=_margins_v+_margins_h
                        if _all_m:
                            _avg_m=sum(_all_m)/len(_all_m)
                            _mc='#4ade80' if _avg_m>0 else ('#f87171' if _avg_m<0 else '#94a3b8')
                            _ms=f"+{_avg_m:.1f}" if _avg_m>0 else f"{_avg_m:.1f}"
                            _nbg='#0d2b0d' if _avg_m>0 else ('#2b0d0d' if _avg_m<0 else '#111827')
                            _row+=f"<td style='text-align:center;padding:5px;background:{_nbg};'><span style='font-weight:900;font-size:.82rem;color:{_mc};'>{_ms}</span></td>"
                        else:
                            _row+="<td style='text-align:center;padding:5px;'><span style='color:#334155;font-size:.7rem;'>—</span></td>"
                    _mar_rows+=f"<tr style='border-bottom:1px solid #0f172a;'>{_row}</tr>"
                st.markdown(
                    f"<div style='overflow-x:auto;border:1px solid #1e293b;border-radius:12px;background:#0f172a;'>"
                    f"<table style='width:100%;border-collapse:collapse;font-size:13px;'>"
                    f"<thead><tr style='background:#111827;'>{_mar_header}</tr></thead>"
                    f"<tbody>{_mar_rows}</tbody></table></div>",
                    unsafe_allow_html=True
                )
            else:
                st.info("Not enough score data to build margin matrix.")
        except Exception as _me:
            st.caption(f"Margin matrix unavailable: {_me}")

        # ── RIVALRY METER ───────────────────────────────────────────────────────────

with _ul_tabs[1]:
    st.header("🎬 ISPN Classics")
    st.caption("The most iconic games in dynasty history — ranked by closeness, stakes, and upset factor.")
    try:
        _cl_scores=load_scores_master(multi_year=True)
        _cl_ratings=model_2041.copy() if model_2041 is not None and not model_2041.empty else pd.DataFrame()
        _classics=build_ispn_classics(_cl_scores,_cl_ratings)
        # Supplement with CFP bracket results
        try:
            _cfp_bkt=pd.read_csv('CFPbracketresults.csv')
            _cfp_bkt.columns=[str(c).strip() for c in _cfp_bkt.columns]
            if not _cfp_bkt.empty and 'YEAR' in _cfp_bkt.columns:
                _cfp_bkt['YEAR']=pd.to_numeric(_cfp_bkt['YEAR'],errors='coerce')
                # Build classic rows from bracket results if they have scores
                _sc1=next((c for c in _cfp_bkt.columns if 'SCORE' in c.upper() and ('1' in c or 'TEAM1' in c.upper() or 'VIS' in c.upper())),None)
                _sc2=next((c for c in _cfp_bkt.columns if 'SCORE' in c.upper() and ('2' in c or 'TEAM2' in c.upper() or 'HOME' in c.upper())),None)
                _t1c=next((c for c in _cfp_bkt.columns if c.upper()=='TEAM1'),None)
                _t2c=next((c for c in _cfp_bkt.columns if c.upper()=='TEAM2'),None)
                if _t1c and _t2c and _sc1 and _sc2 and not _classics.empty:
                    _existing_keys=set(zip(_classics['Visitor'],_classics['Home'],_classics['Year']))
                    _bkt_rows=[]
                    for _,_br in _cfp_bkt.dropna(subset=[_sc1,_sc2]).iterrows():
                        _t1=str(_br.get(_t1c,'')).strip(); _t2=str(_br.get(_t2c,'')).strip()
                        _s1=int(float(_br.get(_sc1,0) or 0)); _s2=int(float(_br.get(_sc2,0) or 0))
                        _byr=int(_br.get('YEAR',CURRENT_YEAR) or CURRENT_YEAR)
                        _rnd=str(_br.get('ROUND','CFP')).strip()
                        if _s1<=0 and _s2<=0: continue
                        if (_t1,_t2,_byr) in _existing_keys or (_t2,_t1,_byr) in _existing_keys: continue
                        _mg=abs(_s1-_s2)
                        _gw={'NCG':20,'SF':12,'QF':8,'R1':4}.get(_rnd,6)
                        _cs=max(0,35-_mg)+_gw
                        _bkt_rows.append({'Year':_byr,'Visitor':_t1,'VisPts':_s1,'HomePts':_s2,'Home':_t2,
                            'VisUser':'','HomeUser':'','Margin':_mg,'Winner':_t1 if _s1>_s2 else _t2,
                            'Loser':_t2 if _s1>_s2 else _t1,'WinnerUser':'','LoserUser':'',
                            'WinnerPts':max(_s1,_s2),'LoserPts':min(_s1,_s2),
                            'WinnerOVR':80,'LoserOVR':80,'OVR_Diff':0,'IsUpset':False,
                            'GameType':f'CFP {_rnd}','ClassicScore':_cs})
                    if _bkt_rows:
                        _classics=pd.concat([_classics,pd.DataFrame(_bkt_rows)],ignore_index=True).sort_values('ClassicScore',ascending=False).reset_index(drop=True)
        except: pass
        if _classics.empty:
            st.info("No classic games found yet. Keep playing!")
        else:
            def _utag3(u):
                if u and u.upper() not in ('CPU','','NAN'):
                    _tc3=get_team_primary_color(USER_TEAMS.get(u,''))
                    return f"<span style='background:{_tc3}22;color:{_tc3};font-size:.58rem;font-weight:700;padding:1px 5px;border-radius:3px;margin-left:3px;'>{html.escape(u.upper())}</span>"
                return ""
            medals_cl={0:"🥇",1:"🥈",2:"🥉"}
            for i,(_,row) in enumerate(_classics.head(15).iterrows()):
                # Use correct column names from build_ispn_classics output
                vis=str(row.get('Visitor','')).strip()
                hom=str(row.get('Home','')).strip()
                vs=int(row.get('VisPts',row.get('Vis Score',0)) or 0)
                hs=int(row.get('HomePts',row.get('Home Score',0)) or 0)
                yr=int(row.get('Year',row.get('YEAR',CURRENT_YEAR)) or CURRENT_YEAR)
                gtype=str(row.get('GameType',''))
                # Week from source data
                _wk_raw=row.get('Week',row.get('WEEK',0))
                wk=int(float(_wk_raw)) if _wk_raw and str(_wk_raw) not in ('','nan') else 0
                vu=str(row.get('VisUser',row.get('Vis_User',''))).strip()
                hu=str(row.get('HomeUser',row.get('Home_User',''))).strip()
                margin=abs(vs-hs)
                is_upset=bool(row.get('IsUpset',False))
                vc=get_team_primary_color(vis); hc2=get_team_primary_color(hom)
                vl=image_file_to_data_uri(get_logo_source(vis))
                hl2=image_file_to_data_uri(get_logo_source(hom))
                vl_h=f"<img src='{vl}' style='width:32px;height:32px;object-fit:contain;'/>" if vl else "🏈"
                hl_h=f"<img src='{hl2}' style='width:32px;height:32px;object-fit:contain;'/>" if hl2 else "🏈"
                medal=medals_cl.get(i,f"#{i+1}")
                # Badge: game type overrides generic labels
                if 'National' in gtype or 'NCG' in gtype: badge_lbl="🏆 NATTY"; badge_c="#fbbf24"
                elif 'CFP' in gtype or 'Playoff' in gtype: badge_lbl="🏟️ CFP"; badge_c="#22d3ee"
                elif 'Conf' in gtype: badge_lbl="🎖️ CONF"; badge_c="#a78bfa"
                elif margin<=7: badge_lbl="💀 THRILLER"; badge_c="#f43f5e"
                elif is_upset: badge_lbl="🚨 UPSET"; badge_c="#f97316"
                else: badge_lbl="🎬 CLASSIC"; badge_c="#60a5fa"
                # Readable game label
                if gtype and gtype not in ('Regular Season',''):
                    wk_lbl=f"{gtype} · {yr}"
                elif wk>0:
                    wk_lbl=f"Wk {wk}, {yr}"
                else:
                    wk_lbl=str(yr)
                # Score display with winner bold
                vs_bold="font-weight:900;color:#f1f5f9;" if vs>=hs else "color:#64748b;"
                hs_bold="font-weight:900;color:#f1f5f9;" if hs>=vs else "color:#64748b;"
                st.markdown(
                    f"<div style='background:linear-gradient(135deg,rgba(15,23,42,.98),rgba(8,15,28,.98));"
                    f"border:1px solid #1e293b;border-radius:12px;padding:12px 14px;margin-bottom:8px;'>"
                    f"<div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;'>"
                    f"<div style='display:flex;align-items:center;gap:8px;'>"
                    f"<span style='font-family:Bebas Neue,sans-serif;font-size:1.3rem;color:#fbbf24;'>{medal}</span>"
                    f"<span style='background:{badge_c}22;color:{badge_c};font-size:.62rem;font-weight:900;"
                    f"padding:3px 8px;border-radius:5px;font-family:Barlow Condensed,sans-serif;"
                    f"letter-spacing:.08em;'>{badge_lbl}</span>"
                    f"<span style='font-size:.65rem;color:#475569;'>{html.escape(wk_lbl)}</span>"
                    f"</div>"
                    f"<span style='font-size:.6rem;color:#334155;'>Classic Score: {float(row.get('ClassicScore',0)):.0f}</span>"
                    f"</div>"
                    f"<div style='display:flex;align-items:center;justify-content:space-between;gap:8px;'>"
                    f"<div style='display:flex;align-items:center;gap:8px;flex:1;min-width:0;'>"
                    f"{vl_h}<div><div style='font-size:.82rem;font-weight:800;color:{vc};'>{html.escape(vis)}{_utag3(vu)}</div>"
                    f"<div style='font-size:.6rem;color:#475569;'>Away</div></div></div>"
                    f"<div style='text-align:center;flex-shrink:0;padding:0 8px;'>"
                    f"<div style='display:flex;align-items:center;gap:4px;'>"
                    f"<span style='{vs_bold}font-family:Bebas Neue,sans-serif;font-size:1.5rem;line-height:1;'>{vs}</span>"
                    f"<span style='color:#334155;font-size:1rem;'>-</span>"
                    f"<span style='{hs_bold}font-family:Bebas Neue,sans-serif;font-size:1.5rem;line-height:1;'>{hs}</span>"
                    f"</div>"
                    f"<div style='font-size:.55rem;color:#334155;text-transform:uppercase;letter-spacing:.06em;'>FINAL</div>"
                    f"</div>"
                    f"<div style='display:flex;align-items:center;gap:8px;flex:1;min-width:0;justify-content:flex-end;'>"
                    f"<div style='text-align:right;'><div style='font-size:.82rem;font-weight:800;color:{hc2};'>{html.escape(hom)}{_utag3(hu)}</div>"
                    f"<div style='font-size:.6rem;color:#475569;'>Home</div></div>{hl_h}</div></div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
    except Exception as e:
        st.caption(f"ISPN Classics unavailable: {e}")

with _ul_tabs[2]:
    st.header("🐐 GOAT Rankings")
    st.caption("All-time dynasty GOAT scores. Titles × 200 + Natty apps × 80 + CFP wins × 40 + Conf titles × 25 + 1st rounders × 12 + NFL picks × 4.")
    try:
        if stats_df is None or stats_df.empty:
            st.info("No dynasty history yet.")
        else:
            _goat_df=stats_df.sort_values('GOAT Score',ascending=False).reset_index(drop=True)
            _goat_df.insert(0,'Rank',range(1,len(_goat_df)+1))
            medals_g={1:"🥇",2:"🥈",3:"🥉"}
            for _,gr in _goat_df.iterrows():
                user_g=str(gr['User']); team_g=USER_TEAMS.get(user_g,'')
                tc_g=get_team_primary_color(team_g); lg=get_school_logo_src(team_g)
                lh_g=f"<img src='{lg}' style='width:32px;height:32px;object-fit:contain;'/>" if lg else ""
                rk_g=int(gr['Rank'])
                medal_g=medals_g.get(rk_g,f"#{rk_g}")
                natties=int(gr.get('Natties',0)); apps=int(gr.get('Natty Apps',0))
                cfpw=int(gr.get('CFP Wins',0)); conft=int(gr.get('Conf Titles',0))
                drafted=int(gr.get('Drafted',0)); rnd1=int(gr.get('1st Rounders',0))
                goat=int(gr.get('GOAT Score',0)); rec=str(gr.get('Career Record',''))
                st.markdown(
                    f"<div style='background:linear-gradient(90deg,{tc_g}18 0%,#0f172a 40%);"
                    f"border:1px solid {tc_g}44;border-left:4px solid {tc_g};"
                    f"border-radius:12px;padding:12px 16px;margin-bottom:8px;'>"
                    f"<div style='display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;'>"
                    f"<div style='display:flex;align-items:center;gap:10px;'>"
                    f"<span style='font-family:Bebas Neue,sans-serif;font-size:1.4rem;color:#fbbf24;'>{medal_g}</span>"
                    f"{lh_g}"
                    f"<div>"
                    f"<div style='font-weight:900;color:{tc_g};font-size:.95rem;font-family:Barlow Condensed,sans-serif;'>{html.escape(team_g)}</div>"
                    f"<div style='font-size:.68rem;color:#64748b;'>{html.escape(user_g)} · {rec}</div>"
                    f"</div></div>"
                    f"<div style='text-align:right;'>"
                    f"<div style='font-family:Bebas Neue,sans-serif;font-size:1.8rem;color:#fbbf24;line-height:1;'>{goat:,}</div>"
                    f"<div style='font-size:.55rem;color:#475569;text-transform:uppercase;letter-spacing:.05em;'>GOAT Score</div>"
                    f"</div></div>"
                    f"<div style='margin-top:6px;display:flex;gap:8px;flex-wrap:wrap;font-size:.65rem;'>"
                    +("".join([
                        f"<span style='background:{tc_g}22;color:{tc_g};border-radius:4px;padding:1px 7px;font-weight:700;'>{natties}🏆</span>" if natties else "",
                        f"<span style='color:#94a3b8;'>Natty Apps: {apps}</span>" if apps else "",
                        f"<span style='color:#94a3b8;'>CFP Wins: {cfpw}</span>" if cfpw else "",
                        f"<span style='color:#94a3b8;'>Conf: {conft}</span>" if conft else "",
                        f"<span style='color:#94a3b8;'>NFL: {drafted} ({rnd1} Rd1)</span>" if drafted else "",
                    ]))
                    +f"</div></div>",
                    unsafe_allow_html=True
                )
    except Exception as e:
        st.caption(f"GOAT Rankings unavailable: {e}")


# --- SEASON RECAP ---


# ══════════════════════════════════════════════════════════════════════
# TAB 5 -- ROSTER MATCHUP
# ══════════════════════════════════════════════════════════════════════
with tabs[5]:
    _rm_tabs2 = st.tabs(["🎯 Roster Matchup"])
    render_roster_matchup_tab()

    # --- SIDEBAR CONTENT ---
    with st.sidebar:
        st.markdown("---")
        st.markdown("""
            <div style="background: linear-gradient(135deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.02) 100%); padding: 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); border-top: 4px solid #10B981; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 20px;">
                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                    <div style="font-size: 1.5rem; margin-right: 10px;">📱</div>
                    <h4 style="margin: 0; color: #FFFFFF; font-size: 1.1rem;">Install Mobile App</h4>
                </div>
                <p style="font-size: 0.85rem; color: #BBBBBB; margin: 0 0 12px 0; line-height: 1.4;">Add this dynasty hub directly to your phone's home screen for fullscreen, one-tap access.</p>
                <div style="background-color: rgba(239, 68, 68, 0.15); border-left: 3px solid #EF4444; padding: 8px; margin-bottom: 12px; font-size: 0.8rem; color: #DDDDDD;">
                    <b>Note:</b> If opening from Discord or Messages, tap the menu and select <b>"Open in Safari/Chrome"</b> first!
                </div>
                <div style="margin-bottom: 10px;">
                    <strong style="color: #FFFFFF; font-size: 0.85rem;">🍎 iOS (Safari)</strong>
                    <ol style="font-size: 0.8rem; color: #DDDDDD; padding-left: 20px; margin: 3px 0 0 0;">
                        <li>Tap the <b>Share</b> icon at the bottom.</li>
                        <li>Scroll down and tap <b>Add to Home Screen</b>.</li>
                    </ol>
                </div>
                <div>
                    <strong style="color: #FFFFFF; font-size: 0.85rem;">🤖 Android (Chrome)</strong>
                    <ol style="font-size: 0.8rem; color: #DDDDDD; padding-left: 20px; margin: 3px 0 0 0;">
                        <li>Tap the <b>Three Dots</b> menu at the top right.</li>
                        <li>Tap <b>Open Streamlit</b>, <b>Install App</b>, or <b>Add to Home Screen</b>.</li>
                    </ol>
                </div>
            </div>
        """, unsafe_allow_html=True)

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.markdown("---")

    st.sidebar.markdown(
        "<p style='font-size:11px;font-weight:500;color:#64748b;text-transform:uppercase;"
        "letter-spacing:.05em;margin-bottom:6px;'>Commissioner Tools</p>",
        unsafe_allow_html=True,
    )

    if st.sidebar.button("📊 Sync Derived Stats", use_container_width=True,
                         help="Auto-updates CFP wins/losses, natty counts & appearances in UserDraftPicks.csv and coach_records.csv"):
        with st.sidebar:
            with st.spinner("Syncing…"):
                _ok, _msgs = sync_derived_stats()
            for _m in _msgs:
                if _m.startswith("✅"):
                    st.success(_m, icon=None)
                elif _m.startswith("⚠️"):
                    st.warning(_m, icon=None)
                else:
                    st.error(_m, icon=None)
            if _ok:
                st.cache_data.clear()
# ── NIL BOARD (Tab 13) ────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🏈 ISPN Dynasty")
    _ncaa_l = image_file_to_data_uri(get_logo_source('NCAA') or '')
    if _ncaa_l: st.markdown(f"<div style='text-align:center;'><img src='{_ncaa_l}' style='width:64px;object-fit:contain;'/></div>", unsafe_allow_html=True)
    st.markdown(f"**Season:** {CURRENT_YEAR} · **Week:** {CURRENT_WEEK_NUMBER}")
    st.markdown(f"**Status:** {'🏝️ Offseason' if IS_OFFSEASON else ('🏟️ Bowl Season' if IS_BOWL_WEEK else '🏈 Regular Season')}")
    st.markdown("---")
    st.markdown("**User Teams**")
    for user, team in USER_TEAMS.items():
        _uc = get_team_primary_color(team)
        _ul = get_school_logo_src(team)
        _ul_h = f"<img src='{_ul}' style='width:16px;height:16px;object-fit:contain;vertical-align:middle;margin-right:4px;'/>" if _ul else ""
        st.markdown(f"<span style='font-size:.8rem;'>{_ul_h}<span style='color:{_uc};font-weight:700;'>{team}</span> <span style='color:#475569;'>({user})</span></span>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("**Quick Links**")
    st.markdown("""
- 📱 Add to home screen for fullscreen  
- 🔄 Refresh to reload live data  
- 💾 Commish: push CSVs after score saves
""")
    st.markdown("---")
    st.caption("ISPN College Football Gameday v2")
    st.caption(f"Dynasty Year {CURRENT_YEAR} · Built with ❤️ for the Island CFB League")
