@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 medbot_x.py
) else (
    python medbot_x.py
)
if not %errorlevel%==0 (
    echo.
    echo The game did not start. Install Python 3 from python.org, then try again.
    pause
)
