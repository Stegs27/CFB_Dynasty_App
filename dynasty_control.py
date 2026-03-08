#!/usr/bin/env python3
from __future__ import annotations

import os
import platform
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext

ROOT = Path(__file__).resolve().parent
REFRESH_SCRIPT = ROOT / "dynasty_refresh.py"
VIDEO_SCRIPT = ROOT / "dynasty_video_refresh.py"
APP_SCRIPT = ROOT / "dynasty_app.py"
WEEKLY_SCREENS = ROOT / "weekly_screens"
VIDEO_INBOX = ROOT / "weekly_videos"
WEEKLY_OUT = ROOT / "weekly_out"
SUMMARY_FILE = WEEKLY_OUT / "summary.txt"

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

class DynastyControlApp:
    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.master.title("CFB Dynasty Control Center")
        self.master.geometry("980x700")
        self.master.minsize(820, 560)

        self.status_var = tk.StringVar(value="Ready.")
        self.refresh_running = False

        self._build_ui()
        self.refresh_summary()

    def _build_ui(self) -> None:
        top = tk.Frame(self.master, padx=14, pady=12)
        top.pack(fill="x")

        tk.Label(
            top,
            text="CFB Dynasty Control Center",
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            top,
            text="Drop screenshots or a weekly video, update dynasty data, then launch the app.",
            font=("Segoe UI", 10),
            fg="#555555",
            anchor="w",
        ).pack(fill="x", pady=(4, 10))

        btns = tk.Frame(top)
        btns.pack(fill="x", pady=(4, 8))

        self.btn_open_screens = tk.Button(btns, text="Open weekly_screens", width=20, command=self.open_weekly_screens)
        self.btn_open_screens.grid(row=0, column=0, padx=(0, 8), pady=4)

        self.btn_open_videos = tk.Button(btns, text="Open weekly_videos", width=20, command=self.open_weekly_videos)
        self.btn_open_videos.grid(row=0, column=1, padx=(0, 8), pady=4)

        self.btn_refresh = tk.Button(btns, text="Update from Screenshots", width=22, command=self.run_refresh)
        self.btn_refresh.grid(row=0, column=2, padx=(0, 8), pady=4)

        self.btn_video = tk.Button(btns, text="Update from Weekly Video", width=22, command=self.run_video_refresh)
        self.btn_video.grid(row=0, column=3, padx=(0, 8), pady=4)

        self.btn_launch = tk.Button(btns, text="Launch Streamlit App", width=20, command=self.launch_streamlit)
        self.btn_launch.grid(row=1, column=0, padx=(0, 8), pady=4)

        self.btn_clear_screens = tk.Button(btns, text="Clear weekly_screens", width=20, command=self.clear_screenshots)
        self.btn_clear_screens.grid(row=1, column=1, padx=(0, 8), pady=4)

        self.btn_clear_videos = tk.Button(btns, text="Clear weekly_videos", width=20, command=self.clear_videos)
        self.btn_clear_videos.grid(row=1, column=2, padx=(0, 8), pady=4)

        self.btn_reload = tk.Button(btns, text="Reload Summary", width=18, command=self.refresh_summary)
        self.btn_reload.grid(row=1, column=3, pady=4)

        info = tk.Frame(self.master, padx=14, pady=0)
        info.pack(fill="x")

        tk.Label(
            info,
            justify="left",
            anchor="w",
            font=("Consolas", 10),
            text=(
                f"Root: {ROOT}\n"
                f"dynasty_refresh.py: {'FOUND' if REFRESH_SCRIPT.exists() else 'MISSING'}  |  "
                f"dynasty_video_refresh.py: {'FOUND' if VIDEO_SCRIPT.exists() else 'MISSING'}  |  "
                f"dynasty_app.py: {'FOUND' if APP_SCRIPT.exists() else 'MISSING'}"
            ),
        ).pack(fill="x", pady=(0, 10))

        summary_wrap = tk.Frame(self.master, padx=14, pady=8)
        summary_wrap.pack(fill="both", expand=True)

        tk.Label(
            summary_wrap,
            text="Latest Refresh Summary",
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        self.summary = scrolledtext.ScrolledText(
            summary_wrap,
            wrap="word",
            font=("Consolas", 10),
            height=24,
            state="disabled",
        )
        self.summary.pack(fill="both", expand=True)

        status_bar = tk.Frame(self.master, bd=1, relief="sunken")
        status_bar.pack(fill="x", side="bottom")

        tk.Label(
            status_bar,
            textvariable=self.status_var,
            anchor="w",
            padx=8,
            pady=5,
        ).pack(fill="x")

    def set_status(self, text: str) -> None:
        self.status_var.set(text)
        self.master.update_idletasks()

    def append_summary(self, text: str) -> None:
        self.summary.configure(state="normal")
        self.summary.insert("end", text)
        self.summary.see("end")
        self.summary.configure(state="disabled")

    def set_summary_text(self, text: str) -> None:
        self.summary.configure(state="normal")
        self.summary.delete("1.0", "end")
        self.summary.insert("1.0", text)
        self.summary.configure(state="disabled")

    def refresh_summary(self) -> None:
        if SUMMARY_FILE.exists():
            try:
                text = SUMMARY_FILE.read_text(encoding="utf-8", errors="replace")
            except Exception as exc:
                text = f"Could not read summary file:\n{exc}"
        else:
            text = (
                "No weekly_out/summary.txt found yet.\n\n"
                "Suggested workflow:\n"
                "1) Put screenshots in weekly_screens or one video in weekly_videos\n"
                "2) Click an update button\n"
                "3) Review summary here\n"
                "4) Launch Streamlit App\n"
            )
        self.set_summary_text(text)
        self.set_status("Summary loaded.")

    def _open_folder(self, folder: Path, label: str) -> None:
        folder.mkdir(exist_ok=True)
        try:
            system = platform.system()
            if system == "Windows":
                os.startfile(str(folder))  # type: ignore[attr-defined]
            elif system == "Darwin":
                subprocess.Popen(["open", str(folder)], cwd=ROOT)
            else:
                subprocess.Popen(["xdg-open", str(folder)], cwd=ROOT)
            self.set_status(f"Opened {label}.")
        except Exception as exc:
            messagebox.showerror("Open Folder Failed", str(exc))
            self.set_status(f"Failed to open {label}.")

    def open_weekly_screens(self) -> None:
        self._open_folder(WEEKLY_SCREENS, "weekly_screens")

    def open_weekly_videos(self) -> None:
        self._open_folder(VIDEO_INBOX, "weekly_videos")

    def _disable_buttons(self) -> None:
        for btn in [
            self.btn_open_screens, self.btn_open_videos, self.btn_refresh, self.btn_video,
            self.btn_launch, self.btn_clear_screens, self.btn_clear_videos, self.btn_reload
        ]:
            btn.configure(state="disabled")

    def _enable_buttons(self) -> None:
        for btn in [
            self.btn_open_screens, self.btn_open_videos, self.btn_refresh, self.btn_video,
            self.btn_launch, self.btn_clear_screens, self.btn_clear_videos, self.btn_reload
        ]:
            btn.configure(state="normal")

    def _run_command_background(self, cmd, label: str) -> None:
        def worker() -> None:
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                output = proc.stdout.strip()
                self.master.after(0, lambda: self._command_finished(label, proc.returncode, output))
            except Exception as exc:
                self.master.after(0, lambda: self._command_finished(label, 1, str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _command_finished(self, label: str, returncode: int, output: str) -> None:
        self.refresh_running = False
        self._enable_buttons()

        header = f"\n\n--- {label} finished (exit code {returncode}) ---\n"
        self.append_summary(header + (output or "[no output]") + "\n")
        self.refresh_summary()

        if returncode == 0:
            self.set_status(f"{label} completed successfully.")
        else:
            self.set_status(f"{label} failed.")
            messagebox.showerror(f"{label} Failed", output or f"{label} exited with code {returncode}")

    def run_refresh(self) -> None:
        if self.refresh_running:
            return
        if not REFRESH_SCRIPT.exists():
            messagebox.showerror("Missing File", "dynasty_refresh.py not found.")
            return
        WEEKLY_SCREENS.mkdir(exist_ok=True)
        self.refresh_running = True
        self._disable_buttons()
        self.set_status("Running dynasty_refresh.py...")
        self._run_command_background([sys.executable, str(REFRESH_SCRIPT)], "Dynasty Refresh")

    def run_video_refresh(self) -> None:
        if self.refresh_running:
            return
        missing = []
        if not VIDEO_SCRIPT.exists():
            missing.append("dynasty_video_refresh.py")
        if not REFRESH_SCRIPT.exists():
            missing.append("dynasty_refresh.py")
        if missing:
            messagebox.showerror("Missing Files", "Missing required items:\n- " + "\n- ".join(missing))
            return

        VIDEO_INBOX.mkdir(exist_ok=True)
        has_video = any(p.is_file() for p in VIDEO_INBOX.iterdir())
        if not has_video:
            messagebox.showerror("No Video Found", "Put one weekly video in weekly_videos first.")
            return

        self.refresh_running = True
        self._disable_buttons()
        self.set_status("Running dynasty_video_refresh.py...")
        self._run_command_background([sys.executable, str(VIDEO_SCRIPT)], "Dynasty Video Refresh")

    def launch_streamlit(self) -> None:
        if not APP_SCRIPT.exists():
            messagebox.showerror("Missing File", "dynasty_app.py not found.")
            return
        try:
            subprocess.Popen(
                ["streamlit", "run", str(APP_SCRIPT)],
                cwd=ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.set_status("Launched Streamlit app.")
        except FileNotFoundError:
            messagebox.showerror("Streamlit Not Found", "Install it with:\npip install streamlit")
            self.set_status("Failed to launch Streamlit.")
        except Exception as exc:
            messagebox.showerror("Launch Failed", str(exc))
            self.set_status("Failed to launch Streamlit.")

    def _clear_folder_by_exts(self, folder: Path, exts) -> int:
        if not folder.exists():
            return 0
        deleted = 0
        for p in folder.iterdir():
            if p.is_file() and p.suffix.lower() in exts:
                try:
                    p.unlink()
                    deleted += 1
                except Exception:
                    pass
        return deleted

    def clear_screenshots(self) -> None:
        WEEKLY_SCREENS.mkdir(exist_ok=True)
        confirm = messagebox.askyesno("Clear weekly_screens", "Delete all image files in weekly_screens?")
        if not confirm:
            return
        deleted = self._clear_folder_by_exts(WEEKLY_SCREENS, IMAGE_EXTS)
        self.set_status(f"Cleared {deleted} screenshot file(s).")
        messagebox.showinfo("Cleared", f"Deleted {deleted} screenshot file(s).")

    def clear_videos(self) -> None:
        VIDEO_INBOX.mkdir(exist_ok=True)
        confirm = messagebox.askyesno("Clear weekly_videos", "Delete all video files in weekly_videos?")
        if not confirm:
            return
        deleted = self._clear_folder_by_exts(VIDEO_INBOX, {".mp4", ".mov", ".mkv", ".avi", ".webm"})
        self.set_status(f"Cleared {deleted} video file(s).")
        messagebox.showinfo("Cleared", f"Deleted {deleted} video file(s).")


def main() -> None:
    root = tk.Tk()
    DynastyControlApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
