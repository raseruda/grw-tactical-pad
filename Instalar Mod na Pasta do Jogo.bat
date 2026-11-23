@echo off
setlocal
set "WILDLANDS_DIR=C:\Program Files (x86)\Steam\steamapps\common\Wildlands"
if not exist "%WILDLANDS_DIR%\GRW.exe" (
    echo GRW.exe not found at %WILDLANDS_DIR%
    pause
    exit /b 1
)
echo Building Ghost Tactical Pad release...
python "%~dp0mod_native\build_proxy.py" --no-zip
if errorlevel 1 exit /b 1

echo Installing winmm.dll and GhostPad\ into %WILDLANDS_DIR% ...
copy /Y "%~dp0mod_release\winmm.dll" "%WILDLANDS_DIR%\winmm.dll" >nul
xcopy /E /I /Y "%~dp0mod_release\GhostPad" "%WILDLANDS_DIR%\GhostPad" >nul
echo Done! Launch Ghost Recon Wildlands normally.
pause
