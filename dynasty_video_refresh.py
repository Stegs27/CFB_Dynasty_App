#!/usr/bin/env python3
from __future__ import annotations

"""
dynasty_video_refresh.py

Single-upload weekly video importer for the dynasty workflow.

Workflow
--------
1) Put one weekly video into weekly_videos/
2) Run this script (or the matching .bat file)
3) The script:
   - samples frames from the video
   - OCRs headers and full frames
   - detects likely team schedule / CFP / recruiting / conference standings screens
   - exports the best screenshots into weekly_screens/
   - writes review CSVs into weekly_out/
   - runs dynasty_refresh.py automatically

Result
------
Your normal screenshot-based pipeline still does the final CSV updates, but now the
screenshots are generated from one video automatically, so you do not have to capture
and sort screenshots by hand anymore.

Important
---------
This is a one-upload automated workflow, not a mathematical guarantee of perfect OCR.
Video quality, pause time, and menu clarity still matter.
"""

import csv
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2
from PIL import Image

try:
    import pytesseract
except Exception:
    pytesseract = None
else:
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

ROOT = Path(__file__).resolve().parent
VIDEO_INBOX = ROOT / "weekly_videos"
WEEKLY_SCREENS = ROOT / "weekly_screens"
WEEKLY_OUT = ROOT / "weekly_out"
FRAME_DEBUG = WEEKLY_OUT / "video_frames_debug"
REFRESH_SCRIPT = ROOT / "dynasty_refresh.py"
SUMMARY_FILE = WEEKLY_OUT / "video_import_summary.txt"

SCHEDULE_CSV = WEEKLY_OUT / "video_schedule_candidates.csv"
CFP_CSV = WEEKLY_OUT / "cfp_rankings_candidates.csv"
RECRUITING_CSV = WEEKLY_OUT / "recruiting_candidates.csv"
STANDINGS_CSV = WEEKLY_OUT / "conference_standings_candidates.csv"

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}

TEAM_ALIASES = {
    "florida st": "Florida State",
    "fsu": "Florida State",
    "florida state": "Florida State",
    "florida": "Florida",
    "south florida": "USF",
    "usf": "USF",
    "san jose st": "San Jose State",
    "san jose state": "San Jose State",
    "sjsu": "San Jose State",
    "bowling green": "Bowling Green",
    "texas tech": "Texas Tech",
    "oklahoma st": "Oklahoma State",
    "oklahoma state": "Oklahoma State",
    "ok state": "Oklahoma State",
    "app state": "Appalachian State",
    "app st": "Appalachian State",
    "appalachian state": "Appalachian State",
    "nc state": "NC State",
    "penn state": "Penn State",
    "south carolina": "South Carolina",
    "texas a&m": "Texas A&M",
    "georgia tech": "Georgia Tech",
    "san diego state": "San Diego State",
    "lsu": "LSU",
    "rapid city": "Rapid City",
    "panama city": "Panama City",
    "hammond": "Hammond",
    "alabaster": "Alabaster",
    "death valley": "Death Valley",
    "gate city": "Gate City",
}

OCR_TEXT_REPLACEMENTS = {
    "0klah0ma": "Oklahoma",
    "0klahoma": "Oklahoma",
    "0hio State": "Ohio State",
    "Penn St": "Penn State",
    "San Jose St": "San Jose State",
    "So Carolina": "South Carolina",
    "App St.": "Appalachian State",
    "App St": "Appalachian State",
    "Ga Tech": "Georgia Tech",
    "Ga Southern": "Georgia Southern",
    "WEEKI": "WEEK 1",
    "WEEk": "WEEK",
    "CFP TOPZS": "CFP TOP 25",
    "TOPZS": "TOP 25",
}

def fail(msg: str, exit_code: int = 1) -> None:
    print(msg)
    WEEKLY_OUT.mkdir(exist_ok=True)
    SUMMARY_FILE.write_text(msg, encoding="utf-8")
    sys.exit(exit_code)

def variance_of_laplacian(img_bgr) -> float:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())

def clean_text(text: str) -> str:
    out = text
    for bad, good in OCR_TEXT_REPLACEMENTS.items():
        out = out.replace(bad, good)
    out = out.replace("—", "-").replace("–", "-")
    out = re.sub(r"[ \t]+", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out

def ocr_text(img: Image.Image) -> str:
    if pytesseract is None:
        fail("pytesseract is not installed. Run: pip install pytesseract")
    try:
        return clean_text(pytesseract.image_to_string(img, config="--psm 6"))
    except Exception as exc:
        fail(f"OCR failed: {exc}")
        return ""

def choose_video() -> Path:
    VIDEO_INBOX.mkdir(exist_ok=True)
    videos = [p for p in VIDEO_INBOX.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS]
    if not videos:
        fail("No video found in weekly_videos.")
    videos = sorted(videos, key=lambda p: p.stat().st_mtime, reverse=True)
    return videos[0]

def normalize_team(text: str) -> str:
    s = re.sub(r"\s+", " ", text.strip())
    return TEAM_ALIASES.get(s.lower(), s)

def detect_week(text: str):
    m = re.search(r"\bW(?:EEK)?\s*(\d{1,2})\b", text.upper())
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None

def extract_record_tokens(text: str):
    return re.findall(r"\b\d{1,2}-\d{1,2}\b", text)

def extract_score_tokens(text: str):
    return re.findall(r"\b\d{1,3}-\d{1,3}\b", text)

def classify_frame(text: str):
    t = text.lower()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    joined = " ".join(lines[:8]).lower()

    if ("cfp" in t and ("rank" in t or "top 25" in t)) or ("cfp top 25" in t):
        return ("cfp", "CFP_rankings")

    if "recruit" in t and ("rank" in t or "class" in t or "national" in t):
        return ("recruiting", "recruiting_rankings")

    if ("standings" in t or "conference" in t) and any(k in t for k in ["w-l", "conf", "overall", "division", "rank"]):
        label = "conference_standings"
        if lines:
            first = re.sub(r"[^A-Za-z0-9&' .-]", "", lines[0]).strip()
            if first:
                label = first.replace(" ", "_")
        return ("conference_standings", label)

    for alias, team in TEAM_ALIASES.items():
        if alias in joined:
            return ("schedule", team)

    if "week" in t and any(k in t for k in ["bye", "combined opponent record", "w-l", "final", "opp w-l"]):
        if lines:
            guess = re.sub(r"[^A-Za-z0-9&' .-]", "", lines[0]).strip()
            if len(guess) >= 3:
                return ("schedule", normalize_team(guess))

    return (None, None)

def extract_candidates(video_path: Path, sample_every_seconds: float = 0.75):
    WEEKLY_OUT.mkdir(exist_ok=True)
    FRAME_DEBUG.mkdir(exist_ok=True)
    WEEKLY_SCREENS.mkdir(exist_ok=True)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        fail(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = frame_count / fps if fps else 0.0
    step = max(1, int(fps * sample_every_seconds))

    groups = defaultdict(list)
    sampled = 0

    for idx in range(0, frame_count, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue

        sampled += 1
        sharpness = variance_of_laplacian(frame)
        h, w = frame.shape[:2]

        header_crop = frame[0:int(h * 0.30), 0:w]
        middle_crop = frame[int(h * 0.20):int(h * 0.85), 0:w]

        header_pil = Image.fromarray(cv2.cvtColor(header_crop, cv2.COLOR_BGR2RGB))
        middle_pil = Image.fromarray(cv2.cvtColor(middle_crop, cv2.COLOR_BGR2RGB))
        full_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        header_text = ocr_text(header_pil)
        middle_text = ocr_text(middle_pil)
        full_text = ocr_text(full_pil)
        combined_text = "\n".join([header_text, middle_text, full_text])

        kind, label = classify_frame(combined_text)
        if not kind:
            continue

        safe_label = re.sub(r"[^A-Za-z0-9]+", "_", label or kind).strip("_") or kind
        debug_path = FRAME_DEBUG / f"{kind}_{safe_label}_{idx}.png"
        cv2.imwrite(str(debug_path), frame)

        groups[(kind, label)].append({
            "idx": idx,
            "sharpness": sharpness,
            "path": debug_path,
            "header_text": header_text,
            "middle_text": middle_text,
            "full_text": full_text,
            "week": detect_week(combined_text),
            "records_found": ", ".join(extract_record_tokens(combined_text)[:12]),
            "scores_found": ", ".join(extract_score_tokens(combined_text)[:12]),
        })

    cap.release()
    return duration, sampled, groups

def export_best_frames(groups):
    exported = []
    for (kind, label), items in groups.items():
        items = sorted(items, key=lambda x: x["sharpness"], reverse=True)
        safe_label = re.sub(r"[^A-Za-z0-9]+", "_", label or kind).strip("_") or kind

        if kind == "schedule":
            for i, item in enumerate(items[:2], start=1):
                out = WEEKLY_SCREENS / f"{safe_label}_{i}.png"
                shutil.copyfile(item["path"], out)
                exported.append(out)
        elif kind in {"cfp", "recruiting"}:
            out = WEEKLY_SCREENS / f"{safe_label}.png"
            shutil.copyfile(items[0]["path"], out)
            exported.append(out)
    return exported

def write_candidate_csv(path: Path, rows):
    fields = [
        "screen_label", "frame_index", "sharpness", "frame_path", "week_detected",
        "records_found", "scores_found", "header_text", "middle_text", "full_text"
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def export_review_csvs(groups):
    buckets = {
        "schedule": [],
        "cfp": [],
        "recruiting": [],
        "conference_standings": [],
    }

    for (kind, label), items in groups.items():
        items = sorted(items, key=lambda x: x["sharpness"], reverse=True)
        for item in items[:3]:
            buckets[kind].append({
                "screen_label": label,
                "frame_index": item["idx"],
                "sharpness": round(item["sharpness"], 2),
                "frame_path": str(item["path"].relative_to(ROOT)),
                "week_detected": item["week"] if item["week"] is not None else "",
                "records_found": item["records_found"],
                "scores_found": item["scores_found"],
                "header_text": item["header_text"].replace("\n", " | "),
                "middle_text": item["middle_text"].replace("\n", " | "),
                "full_text": item["full_text"].replace("\n", " | "),
            })

    write_candidate_csv(SCHEDULE_CSV, buckets["schedule"])
    write_candidate_csv(CFP_CSV, buckets["cfp"])
    write_candidate_csv(RECRUITING_CSV, buckets["recruiting"])
    write_candidate_csv(STANDINGS_CSV, buckets["conference_standings"])

    return {k: len(v) for k, v in buckets.items()}

def detect_likely_current_week(groups):
    weeks = []
    for (kind, _), items in groups.items():
        if kind != "schedule":
            continue
        for item in items:
            if item["week"] is not None:
                weeks.append(item["week"])
    if not weeks:
        return None
    return Counter(weeks).most_common(1)[0][0]

def run_refresh():
    if not REFRESH_SCRIPT.exists():
        fail("dynasty_refresh.py not found.")
    proc = subprocess.run(
        [sys.executable, str(REFRESH_SCRIPT)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout

def main():
    video = choose_video()
    print(f"Using video: {video.name}")

    duration, sampled, groups = extract_candidates(video, sample_every_seconds=0.75)
    exported = export_best_frames(groups)
    csv_counts = export_review_csvs(groups)
    likely_week = detect_likely_current_week(groups)
    refresh_code, refresh_output = run_refresh()

    lines = []
    lines.append(f"Video used: {video.name}")
    lines.append(f"Duration (seconds): {duration:.1f}")
    lines.append(f"Frames sampled: {sampled}")
    lines.append(f"Groups found: {len(groups)}")
    lines.append(f"Likely current week: {likely_week if likely_week is not None else 'unknown'}")
    lines.append(f"Frames exported to weekly_screens: {len(exported)}")
    lines.append(f"Schedule candidate rows: {csv_counts['schedule']}")
    lines.append(f"CFP candidate rows: {csv_counts['cfp']}")
    lines.append(f"Recruiting candidate rows: {csv_counts['recruiting']}")
    lines.append(f"Conference standings candidate rows: {csv_counts['conference_standings']}")
    lines.append("")
    for (kind, label), items in sorted(groups.items()):
        lines.append(f"{kind}: {label} -> {len(items)} candidate frame(s)")
    lines.append("")
    lines.append(f"dynasty_refresh.py exit code: {refresh_code}")
    lines.append("")
    lines.append("dynasty_refresh.py output:")
    lines.append((refresh_output or "[no output]").strip())

    SUMMARY_FILE.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))

    if refresh_code != 0:
        sys.exit(refresh_code)

if __name__ == "__main__":
    main()
