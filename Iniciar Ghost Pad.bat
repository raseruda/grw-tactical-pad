@echo off
setlocal
cd /d "%~dp0"
title Ghost Tactical Pad — Wildlands

tasklist /FI "IMAGENAME eq GRW.exe" 2>nul | find /I "GRW.exe" >nul
if %ERRORLEVEL%==0 (
    echo GRW.exe detected running. Opening Ghost Tactical Pad window on http://127.0.0.1:8766 ...
    if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" (
        start "" "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" --app=http://127.0.0.1:8766 --new-window
        exit /b 0
    )
    if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" (
        start "" "%ProgramFiles%\Google\Chrome\Application\chrome.exe" --app=http://127.0.0.1:8766 --new-window
        exit /b 0
    )
    start "" http://127.0.0.1:8766
    exit /b 0
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
    python "%~dp0launcher.py" %*
    exit /b %ERRORLEVEL%
)

echo Ghost Recon Wildlands (GRW.exe) is not running and standalone Python is not installed.
echo Start the game normally to auto-launch Ghost Tactical Pad on Monitor 2.
pause
