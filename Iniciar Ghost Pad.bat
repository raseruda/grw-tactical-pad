@echo off
setlocal
cd /d "%~dp0"
title Ghost Tactical Pad — Wildlands

if exist "%~dp0GhostTacticalPad.exe" (
    start "" "%~dp0GhostTacticalPad.exe" %*
    exit /b 0
)
if exist "%~dp0..\GhostTacticalPad.exe" (
    start "" "%~dp0..\GhostTacticalPad.exe" %*
    exit /b 0
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
    python "%~dp0launcher.py" %*
    exit /b %ERRORLEVEL%
)

echo GhostTacticalPad.exe nao encontrado e Python nao esta instalado neste PC.
echo Execute pelo GhostTacticalPad.exe ou abra o Ghost Recon Wildlands normalmente.
pause
