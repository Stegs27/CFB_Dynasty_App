"""
prep_cpu_draft_pool.py
======================
Computes the three derived columns for cpu_draft_pool.csv:
  - PosBucket      : position group from raw Pos
  - DraftValueScore: weighted OVR + athleticism + AWR + position bonus
  - DraftRank      : rank within each DraftYear by DraftValueScore desc
  - DraftRound     : ceil(DraftRank / 32), capped at 7

Usage:
  python prep_cpu_draft_pool.py                        # reads + writes cpu_draft_pool.csv in-place
  python prep_cpu_draft_pool.py input.csv output.csv   # custom paths
  python prep_cpu_draft_pool.py --year 2043            # only recompute rows for that year
"""

import sys
import math
import hashlib
import pandas as pd
import numpy as np
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
INPUT_FILE  = 'cpu_draft_pool.csv'
OUTPUT_FILE = 'cpu_draft_pool.csv'
FILTER_YEAR = None   # set via --year arg or leave None to process all years

# ── Position bucket map ────────────────────────────────────────────────────────
POS_BUCKET = {
    'QB':   'QB',
    'HB':   'RB',  'RB': 'RB', 'FB': 'RB',
    'WR':   'WR',
    'TE':   'TE',
    'LT':   'OL',  'LG': 'OL', 'C': 'OL', 'RG': 'OL', 'RT': 'OL',
    'LEDG': 'EDGE','REDG': 'EDGE',
    'DT':   'IDL',
    'MIKE': 'LB',  'WILL': 'LB', 'SAM': 'LB',
    'CB':   'CB',
    'FS':   'S',   'SS': 'S',
    'K':    'K',
    'P':    'P',
}

# ── Position bonus (reverse-engineered from 2042 draft class) ─────────────────
POS_BONUS = {
    'CB':   8.97,
    'WR':   8.81,
    'QB':   8.36,
    'EDGE': 8.31,
    'OL':   6.71,
    'IDL':  6.26,
    'S':    5.93,
    'RB':   4.80,
    'LB':   3.53,
    'TE':   1.90,
    'P':    1.56,
    'K':    1.46,
}

def compute_pos_bucket(pos):
    return POS_BUCKET.get(str(pos).strip().upper(), 'OL')

def compute_draft_value_score(row):
    ovr    = float(row.get('OVR',  0) or 0)
    spd    = float(row.get('SPD',  75) or 75)
    acc    = float(row.get('ACC',  75) or 75)
    agi    = float(row.get('AGI',  75) or 75)
    cod    = float(row.get('COD',  75) or 75)
    awr    = float(row.get('AWR',  75) or 75)
    bucket = str(row.get('PosBucket', 'OL')).strip()

    athl_avg  = (spd + acc + agi + cod) / 4.0
    pos_bonus = POS_BONUS.get(bucket, 5.0)

    score = ovr * 0.80 + athl_avg * 0.12 + awr * 0.10 + pos_bonus
    return round(score, 2)

def process_year_group(df_year):
    """Compute all derived columns for a single DraftYear group."""
    df = df_year.copy()

    # PosBucket
    df['PosBucket'] = df['Pos'].apply(compute_pos_bucket)

    # DraftValueScore
    df['DraftValueScore'] = df.apply(compute_draft_value_score, axis=1)

    # DraftRank — sort desc by DraftValueScore, break ties by OVR then name
    df = df.sort_values(
        ['DraftValueScore', 'OVR', 'Player'],
        ascending=[False, False, True]
    ).reset_index(drop=True)
    df['DraftRank'] = df.index + 1

    # DraftRound — ceil(rank/32) capped at 7
    df['DraftRound'] = df['DraftRank'].apply(lambda r: min(math.ceil(r / 32), 7))

    return df

def main():
    global INPUT_FILE, OUTPUT_FILE, FILTER_YEAR

    args = sys.argv[1:]
    year_flag = None

    # Parse --year XXXX
    if '--year' in args:
        yi = args.index('--year')
        year_flag = int(args[yi + 1])
        args = args[:yi] + args[yi+2:]

    if len(args) >= 1: INPUT_FILE  = args[0]
    if len(args) >= 2: OUTPUT_FILE = args[1]
    if year_flag:      FILTER_YEAR = year_flag

    print(f"Reading:  {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE)

    required = ['DraftYear', 'Player', 'CollegeTeam', 'Pos', 'Class', 'OVR']
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"❌ Missing required columns: {missing}")
        sys.exit(1)

    # Numeric coercion
    for col in ['OVR', 'SPD', 'ACC', 'AGI', 'COD', 'STR', 'AWR']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0

    df['DraftYear'] = pd.to_numeric(df['DraftYear'], errors='coerce')

    # Process: either one year or all
    years_to_process = [int(FILTER_YEAR)] if FILTER_YEAR else sorted(df['DraftYear'].dropna().astype(int).unique())

    processed_parts = []
    unchanged_parts = []

    for yr in df['DraftYear'].dropna().astype(int).unique():
        chunk = df[df['DraftYear'].fillna(-1).astype(int) == yr].copy()
        if yr in years_to_process:
            processed_parts.append(process_year_group(chunk))
            print(f"  ✅ Processed {yr}: {len(chunk)} players")
        else:
            unchanged_parts.append(chunk)

    result = pd.concat(processed_parts + unchanged_parts, ignore_index=True)

    # Preserve column order — put derived cols right after raw attrs
    base_cols = ['DraftYear', 'DraftRank', 'Player', 'CollegeTeam', 'Pos', 'PosBucket',
                 'Class', 'OVR', 'SPD', 'ACC', 'AGI', 'COD', 'STR', 'AWR',
                 'DraftValueScore', 'DraftRound']
    extra_cols = [c for c in result.columns if c not in base_cols]
    final_cols = [c for c in base_cols if c in result.columns] + extra_cols
    result = result[final_cols]

    result.to_csv(OUTPUT_FILE, index=False)
    print(f"\n✅ Written: {OUTPUT_FILE}  ({len(result)} total rows across {len(years_to_process)} year(s) processed)")
    print(f"\nColumn order: {list(result.columns)}")

    # Quick sanity check on processed years
    for yr in years_to_process:
        chunk = result[result['DraftYear'].astype(int) == yr]
        if not chunk.empty:
            r1 = chunk[chunk['DraftRound'] == 1]
            print(f"\n  {yr} — {len(chunk)} players, {len(r1)} Round 1 picks")
            print(f"  Top 5: {', '.join(chunk.head(5)['Player'].tolist())}")

if __name__ == '__main__':
    main()
