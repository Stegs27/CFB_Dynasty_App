#!/usr/bin/env python3
from __future__ import annotations
import re, sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
import pandas as pd
from PIL import Image, ImageOps
try:
    import pytesseract
except Exception:
    pytesseract = None

TESSERACT_CMD = r""
YEAR = 2041
SCREENSHOT_DIR = Path("weekly_screens")
OUT_DIR = Path("weekly_out")
OCR_TEXT_DIR = OUT_DIR / "ocr_text"
TEAM_RATINGS_PATH = Path("TeamRatingsHistory.csv")
CPU_MASTER_PATH = Path("CPUscores_MASTER.csv")
USER_V_USER_PATH = Path("scores.csv")
IMAGE_EXTS = {".png",".jpg",".jpeg",".webp"}

TEAM_ALIAS_MAP = {
    "sjsu":"San Jose State","san jose st":"San Jose State","usf":"USF","south florida":"USF",
    "florida st":"Florida State","fsu":"Florida State","ohio st":"Ohio State","penn st":"Penn State",
    "app st":"Appalachian State","app st.":"Appalachian State",
}
OCR_TEXT_REPLACEMENTS = {
    "0klah0ma":"Oklahoma","0hio State":"Ohio State","Penn St":"Penn State",
    "San Jose St":"San Jose State","So Carolina":"South Carolina","App St":"Appalachian State",
    "Ga Tech":"Georgia Tech","Ga Southern":"Georgia Southern",
}

@dataclass
class ParsedGame:
    year:int; week:int; visitor:str; home:str; vis_score:Optional[int]; home_score:Optional[int]
    vis_user:str; home_user:str; visitor_rank:Optional[int]; home_rank:Optional[int]
    visitor_record:Optional[str]; home_record:Optional[str]; status:str; source:str
    reg_season:int=1; conf_title:int=0; bowl:int=0; natty_game:int=0; cfp:str=""

def fail(msg:str)->None:
    print(f"[ERROR] {msg}"); sys.exit(1)

def ensure_dirs():
    OUT_DIR.mkdir(exist_ok=True); OCR_TEXT_DIR.mkdir(exist_ok=True)

def norm_team(name:str)->str:
    n = re.sub(r"\s+"," ",str(name).strip())
    return TEAM_ALIAS_MAP.get(n.lower(), n)

def split_record(record)->Tuple[Optional[int],Optional[int]]:
    try:
        a,b = str(record).split("-",1); return int(a), int(b)
    except Exception:
        return None, None

def find_groups(folder:Path)->Dict[str,List[Path]]:
    groups={}
    if not folder.exists(): fail(f"Missing screenshot folder: {folder}")
    for p in folder.iterdir():
        if not p.is_file() or p.suffix.lower() not in IMAGE_EXTS: continue
        if "cfp" in p.stem.lower(): continue
        stem = re.sub(r"[_\-]+"," ",p.stem)
        stem = re.sub(r"\b[12]\b$","",stem).strip()
        team = norm_team(stem)
        groups.setdefault(team, []).append(p)
    for k in groups: groups[k] = sorted(groups[k], key=lambda x:x.name)
    return groups

def find_cfp_images(folder:Path)->List[Path]:
    return sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS and "cfp" in p.stem.lower()], key=lambda x:x.name)

def stitch(paths:List[Path])->Image.Image:
    ims=[Image.open(p).convert("RGB") for p in paths]
    w=max(i.width for i in ims); h=sum(i.height for i in ims)
    canvas=Image.new("RGB",(w,h),"white")
    y=0
    for im in ims:
        canvas.paste(im,(0,y)); y+=im.height
    return canvas

def preprocess(img:Image.Image)->Image.Image:
    g=ImageOps.grayscale(img)
    return g.point(lambda x: 0 if x < 175 else 255, mode="1")

def ocr(img:Image.Image)->str:
    if pytesseract is None: fail("Install pytesseract first: pip install pytesseract")
    if TESSERACT_CMD: pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    return pytesseract.image_to_string(img, config="--psm 6")

def clean_text(text:str)->str:
    t=text
    for bad,good in OCR_TEXT_REPLACEMENTS.items(): t=t.replace(bad,good)
    t=t.replace("—","-").replace("–","-")
    return re.sub(r"[ \t]+"," ",t)

def extract_header_record(text:str)->Optional[str]:
    for ln in [x.strip() for x in text.splitlines() if x.strip()][:25]:
        m=re.findall(r"\b(\d{1,2}-\d{1,2})\b", ln)
        if m: return m[0]
    return None

def extract_combined_record(text:str)->Optional[str]:
    m=re.search(r"Combined Opponent Record[:\s]+(\d{1,3}-\d{1,3})", text, re.I)
    return m.group(1) if m else None

def extract_rank_prefix(text:str)->Tuple[Optional[int],str]:
    m=re.match(r"^\s*#?(\d{1,2})\s+(.+)$", text)
    return (int(m.group(1)), m.group(2).strip()) if m else (None, text.strip())

def extract_record(text:str)->Optional[str]:
    m=re.search(r"\b(\d{1,2}-\d{1,2})\b", text)
    return m.group(1) if m else None

def parse_result_token(text:str)->Tuple[str,Optional[int],Optional[int]]:
    t=text.strip().upper()
    if "BYE" in t: return "BYE",None,None
    if re.search(r"\b\d{1,2}:\d{2}\s*(AM|PM)\b", t): return "SCHEDULED",None,None
    m=re.search(r"\b([WL])\s*(\d{1,3})-(\d{1,3})\b", t)
    if m: return "FINAL", int(m.group(2)), int(m.group(3))
    return "UNKNOWN",None,None

def likely_week(line:str)->Optional[int]:
    m=re.search(r"\bW(?:EEK)?\s*(\d{1,2})\b", line.upper())
    if m: return int(m.group(1))
    m=re.fullmatch(r"\s*(\d{1,2})\s*", line)
    if m:
        n=int(m.group(1))
        if 1 <= n <= 16: return n
    return None

def load_team_user_map(path:Path)->Dict[str,str]:
    df=pd.read_csv(path)
    cols={c.lower().strip():c for c in df.columns}
    if "team" not in cols or "user" not in cols: fail("TeamRatingsHistory.csv needs TEAM and USER")
    if "year" in cols:
        df[cols["year"]] = pd.to_numeric(df[cols["year"]], errors="coerce")
        latest=df[cols["year"]].dropna().max()
        if pd.notna(latest): df=df[df[cols["year"]]==latest].copy()
    return {norm_team(r[cols["team"]]): str(r[cols["user"]]).strip().title() for _,r in df.iterrows() if str(r[cols["team"]]).strip()}

def parse_schedule(team:str, text:str, team_user_map:Dict[str,str], source:str):
    lines=[ln.strip() for ln in text.splitlines() if ln.strip()]
    rows=[]; i=0
    team_user=team_user_map.get(team, "CPU")
    team_record=extract_header_record(text)
    combined=extract_combined_record(text)
    while i < len(lines):
        wk=likely_week(lines[i])
        if wk is None: i+=1; continue
        opp_line = lines[i+1] if i+1 < len(lines) else ""
        res_line = lines[i+2] if i+2 < len(lines) else ""
        rec_line = lines[i+3] if i+3 < len(lines) else ""
        if not opp_line: i+=1; continue
        opp_rank, opp_raw = extract_rank_prefix(opp_line)
        away=False; up=opp_raw.upper()
        if up.startswith("@ "): away=True; opp=opp_raw[2:].strip()
        elif up.startswith("AT "): away=True; opp=opp_raw[3:].strip()
        elif up.startswith("VS "): opp=opp_raw[3:].strip()
        else: opp=opp_raw.strip()
        opp=norm_team(opp)
        status, team_score, opp_score = parse_result_token(res_line)
        opp_record = extract_record(rec_line)
        if status == "BYE": i+=4; continue
        if away:
            visitor, home = team, opp
            vis_user, home_user = team_user, team_user_map.get(opp, "CPU")
            visitor_rank, home_rank = None, opp_rank
            visitor_record, home_record = team_record, opp_record
            vis_score, home_score = (team_score, opp_score) if status=="FINAL" else (None,None)
        else:
            visitor, home = opp, team
            vis_user, home_user = team_user_map.get(opp, "CPU"), team_user
            visitor_rank, home_rank = opp_rank, None
            visitor_record, home_record = opp_record, team_record
            vis_score, home_score = (opp_score, team_score) if status=="FINAL" else (None,None)
        rows.append(ParsedGame(YEAR,wk,visitor,home,vis_score,home_score,vis_user,home_user,visitor_rank,home_rank,visitor_record,home_record,"SCHEDULED" if status!="FINAL" else "FINAL",source))
        i+=4
    return rows, team_record, combined

def rows_to_df(rows:List[ParsedGame])->pd.DataFrame:
    return pd.DataFrame([{
        "YEAR":r.year,"Week":r.week,"Visitor":r.visitor,"Home":r.home,"Vis Score":r.vis_score,"Home Score":r.home_score,
        "CFP":r.cfp,"Vis_User":r.vis_user,"Home_User":r.home_user,"Visitor Rank":r.visitor_rank,"Home Rank":r.home_rank,
        "Visitor Record":r.visitor_record,"Home Record":r.home_record,"Reg Season":r.reg_season,"Conf Title":r.conf_title,
        "Bowl":r.bowl,"Natty Game":r.natty_game,"Status":r.status,"Source":r.source
    } for r in rows])

def update_cpu_master(new_rows_df:pd.DataFrame)->pd.DataFrame:
    existing = pd.read_csv(CPU_MASTER_PATH) if CPU_MASTER_PATH.exists() else pd.DataFrame(columns=new_rows_df.columns)
    merged = pd.concat([existing,new_rows_df], ignore_index=True)
    merged = merged.drop_duplicates(subset=["YEAR","Week","Visitor","Home"], keep="last").sort_values(["YEAR","Week","Home","Visitor"]).reset_index(drop=True)
    merged.to_csv(CPU_MASTER_PATH, index=False)
    return merged

def update_scores(cpu_df:pd.DataFrame)->pd.DataFrame:
    uv = cpu_df[(cpu_df["Status"]=="FINAL")&(cpu_df["Vis_User"].fillna("CPU")!="CPU")&(cpu_df["Home_User"].fillna("CPU")!="CPU")].copy()
    out = pd.DataFrame({
        "YEAR":uv["YEAR"],"Visitor":uv["Visitor"],"Home":uv["Home"],"Vis Score":uv["Vis Score"],"Home Score":uv["Home Score"],
        "CFP":uv.get("CFP",""),"Vis_User":uv["Vis_User"],"Home_User":uv["Home_User"],"Reg Season":uv.get("Reg Season",1),
        "Conf Title":uv.get("Conf Title",0),"Bowl":uv.get("Bowl",0),"Natty Game":uv.get("Natty Game",0)
    })
    if USER_V_USER_PATH.exists():
        existing=pd.read_csv(USER_V_USER_PATH)
        out=pd.concat([existing,out], ignore_index=True)
        out=out.drop_duplicates(subset=["YEAR","Visitor","Home","Vis Score","Home Score"], keep="last").sort_values(["YEAR","Visitor","Home"]).reset_index(drop=True)
    out.to_csv(USER_V_USER_PATH, index=False)
    return out

def detect_current_week(cpu_df:pd.DataFrame)->Optional[int]:
    scheds = pd.to_numeric(cpu_df.loc[cpu_df["Status"]=="SCHEDULED","Week"], errors="coerce").dropna()
    finals = pd.to_numeric(cpu_df.loc[cpu_df["Status"]=="FINAL","Week"], errors="coerce").dropna()
    if not scheds.empty: return int(scheds.min())
    if not finals.empty: return int(finals.max())
    return None

def parse_cfp_rankings(text:str)->pd.DataFrame:
    rows=[]; seen=set()
    for ln in [x.strip() for x in text.splitlines() if x.strip()]:
        m=re.match(r"^\#?(\d{1,2})\s+([A-Za-z0-9&\.\-\' ]+)$", ln)
        if not m: continue
        rank=int(m.group(1)); team=norm_team(m.group(2).strip())
        if 1 <= rank <= 25:
            key=(rank,team)
            if key not in seen:
                seen.add(key); rows.append({"Current CFP Ranking":rank,"Team":team})
    return pd.DataFrame(rows).sort_values("Current CFP Ranking").reset_index(drop=True) if rows else pd.DataFrame(columns=["Current CFP Ranking","Team"])

def update_team_ratings(cpu_df:pd.DataFrame, team_user_map:Dict[str,str], header_summary:Dict[str,Dict[str,Optional[str]]], cfp_df:pd.DataFrame)->pd.DataFrame:
    trh=pd.read_csv(TEAM_RATINGS_PATH)
    cols={c.lower().strip():c for c in trh.columns}
    if "team" not in cols or "user" not in cols: fail("TeamRatingsHistory.csv needs TEAM and USER")
    team_col,user_col = cols["team"], cols["user"]
    year_col = cols.get("year")
    for c in ["Combined Opponent Wins","Combined Opponent Losses","Current Record Wins","Current Record Losses","Current CFP Ranking"]:
        if c not in trh.columns: trh[c]=pd.NA
    if year_col: trh[year_col]=pd.to_numeric(trh[year_col], errors="coerce")
    cfp_map={norm_team(r["Team"]): int(r["Current CFP Ranking"]) for _,r in cfp_df.iterrows()} if not cfp_df.empty else {}
    cur = cpu_df[pd.to_numeric(cpu_df["YEAR"], errors="coerce")==YEAR].copy()
    for idx,row in trh.iterrows():
        if year_col and pd.notna(row[year_col]) and int(row[year_col]) != YEAR: continue
        team=norm_team(row[team_col]); user=str(row[user_col]).strip().title()
        if team_user_map.get(team) != user: continue
        team_games=cur[(cur["Visitor"]==team)|(cur["Home"]==team)].copy()
        if team_games.empty: continue
        hrec=header_summary.get(team,{}).get("team_record")
        hcomb=header_summary.get(team,{}).get("combined_opp_record")
        if hrec:
            cw,cl = split_record(hrec)
        else:
            cw=cl=0
            for _,g in team_games.iterrows():
                if str(g["Status"]).upper() != "FINAL": continue
                try: vs=float(g["Vis Score"]); hs=float(g["Home Score"])
                except Exception: continue
                if g["Visitor"]==team:
                    cw += int(vs>hs); cl += int(vs<hs)
                else:
                    cw += int(hs>vs); cl += int(hs<vs)
        if hcomb:
            ow,ol = split_record(hcomb)
        else:
            ow=ol=0
            for _,g in team_games.iterrows():
                opp_rec = g["Home Record"] if g["Visitor"]==team else g["Visitor Record"]
                a,b = split_record(opp_rec); ow += a or 0; ol += b or 0
        trh.at[idx,"Current Record Wins"]=cw
        trh.at[idx,"Current Record Losses"]=cl
        trh.at[idx,"Combined Opponent Wins"]=ow
        trh.at[idx,"Combined Opponent Losses"]=ol
        trh.at[idx,"Current CFP Ranking"]=cfp_map.get(team,"NR")
    trh.to_csv(TEAM_RATINGS_PATH, index=False)
    return trh

def build_current_week_games(cpu_df:pd.DataFrame, week:Optional[int])->pd.DataFrame:
    if week is None: return pd.DataFrame()
    df=cpu_df[pd.to_numeric(cpu_df["Week"], errors="coerce")==week].copy()
    if df.empty: return df
    df["User_vs_User"]=(df["Vis_User"].fillna("CPU")!="CPU")&(df["Home_User"].fillna("CPU")!="CPU")
    return df.sort_values(["Home","Visitor"]).reset_index(drop=True)

def build_user_matchups(current_week_df:pd.DataFrame)->pd.DataFrame:
    if current_week_df.empty: return pd.DataFrame()
    df=current_week_df[current_week_df["User_vs_User"]==True].copy()
    cols=["YEAR","Week","Visitor","Home","Vis_User","Home_User","Visitor Rank","Home Rank","Visitor Record","Home Record","Status"]
    return df[cols].reset_index(drop=True) if not df.empty else pd.DataFrame(columns=cols)

def compute_series(scores_df:pd.DataFrame)->pd.DataFrame:
    recs={}
    if scores_df.empty: return pd.DataFrame(columns=["User A","User B","A Wins","B Wins","Series"])
    for _,r in scores_df.iterrows():
        a=str(r["Vis_User"]).title(); b=str(r["Home_User"]).title()
        if a.lower()=="cpu" or b.lower()=="cpu": continue
        key=tuple(sorted([a,b])); rec=recs.setdefault(key,{key[0]:0,key[1]:0})
        try: vs=float(r["Vis Score"]); hs=float(r["Home Score"])
        except Exception: continue
        winner = a if vs>hs else b if hs>vs else None
        if winner: rec[winner]+=1
    rows=[]
    for (u1,u2),rec in sorted(recs.items()):
        rows.append({"User A":u1,"User B":u2,"A Wins":rec[u1],"B Wins":rec[u2],"Series":f"{u1} {rec[u1]} - {rec[u2]} {u2}"})
    return pd.DataFrame(rows)

def main():
    ensure_dirs()
    team_user_map=load_team_user_map(TEAM_RATINGS_PATH)
    groups=find_groups(SCREENSHOT_DIR)
    if not groups: fail(f"No team schedule screenshots found in {SCREENSHOT_DIR}")
    all_rows=[]; header_summary={}
    for team,paths in groups.items():
        img=preprocess(stitch(paths[:2]))
        text=clean_text(ocr(img))
        (OCR_TEXT_DIR / f"{re.sub(r'[^A-Za-z0-9]+','_',team)}.txt").write_text(text, encoding="utf-8")
        team_rows, team_record, combined_record = parse_schedule(team,text,team_user_map,", ".join(p.name for p in paths))
        header_summary[team]={"team_record":team_record,"combined_opp_record":combined_record}
        all_rows.extend(team_rows)
    parsed_df=rows_to_df(all_rows)
    parsed_df.to_csv(OUT_DIR/"parsed_rows.csv", index=False)
    cfp_images=find_cfp_images(SCREENSHOT_DIR)
    cfp_df=pd.DataFrame(columns=["Current CFP Ranking","Team"])
    if cfp_images:
        cfp_text=clean_text(ocr(preprocess(stitch(cfp_images[:2]))))
        (OCR_TEXT_DIR/"CFP_rankings.txt").write_text(cfp_text, encoding="utf-8")
        cfp_df=parse_cfp_rankings(cfp_text)
    cfp_df.to_csv(OUT_DIR/"cfp_rankings_parsed.csv", index=False)
    cpu_df=update_cpu_master(parsed_df)
    scores_df=update_scores(cpu_df)
    trh_df=update_team_ratings(cpu_df, team_user_map, header_summary, cfp_df)
    current_week=detect_current_week(cpu_df)
    current_week_df=build_current_week_games(cpu_df, current_week)
    current_week_df.to_csv(OUT_DIR/"current_week_games.csv", index=False)
    user_matchups_df=build_user_matchups(current_week_df)
    user_matchups_df.to_csv(OUT_DIR/"user_matchups.csv", index=False)
    series_df=compute_series(scores_df)
    series_df.to_csv(OUT_DIR/"series_records.csv", index=False)
    summary = "\n".join([
        f"Teams parsed: {len(groups)}",
        f"Parsed schedule rows: {len(parsed_df)}",
        f"CPU master rows: {len(cpu_df)}",
        f"User-v-user rows in scores.csv: {len(scores_df)}",
        f"TeamRatingsHistory rows: {len(trh_df)}",
        f"Detected current week: {current_week}",
        f"Current week game rows: {len(current_week_df)}",
        f"Current week user-v-user rows: {len(user_matchups_df)}",
        f"Series records tracked: {len(series_df)}",
        f"CFP rankings parsed: {len(cfp_df)}",
    ])
    (OUT_DIR/"summary.txt").write_text(summary, encoding="utf-8")
    print(summary)

if __name__ == "__main__":
    main()
