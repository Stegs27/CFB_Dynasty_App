@echo off
cd /d "%~dp0"

echo =========================================
echo   DYNASTY ONE-UPLOAD VIDEO AUTOMATION
echo =========================================
echo.

if not exist "weekly_videos" mkdir "weekly_videos"
if not exist "weekly_screens" mkdir "weekly_screens"
if not exist "weekly_out" mkdir "weekly_out"

if not exist "dynasty_video_refresh.py" (
    echo ERROR: dynasty_video_refresh.py not found.
    pause
    exit /b 1
)

if not exist "dynasty_refresh.py" (
    echo ERROR: dynasty_refresh.py not found.
    pause
    exit /b 1
)

set HAS_VIDEO=
for %%F in ("weekly_videos\*.mp4" "weekly_videos\*.mov" "weekly_videos\*.mkv" "weekly_videos\*.avi" "weekly_videos\*.webm") do (
    if exist "%%~F" set HAS_VIDEO=1
)

if not defined HAS_VIDEO (
    echo ERROR: No video found in weekly_videos.
    echo Put one weekly dynasty video in that folder and run again.
    pause
    exit /b 1
)

echo Found weekly video.
echo Running single-upload automation...
python dynasty_video_refresh.py

if errorlevel 1 (
    echo.
    echo =========================================
    echo Automation failed.
    echo Check the error above and weekly_out\video_import_summary.txt
    echo =========================================
    pause
    exit /b 1
)

echo.
echo =========================================
echo Automation complete.
echo weekly_out now contains OCR review CSVs.
echo weekly_screens now contains auto-generated screenshots.
echo dynasty_refresh.py already ran.
echo =========================================
echo.

choice /M "Launch Streamlit app now"
if errorlevel 2 goto done
if errorlevel 1 goto launchapp

:launchapp
streamlit run dynasty_app.py
goto done

:done
pause
