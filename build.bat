@echo off
REM Build a standalone sprint_recap.exe for Windows.
REM Requires: Python 3.10+ installed on this machine (only for building).
REM The resulting exe in dist\ has no Python dependency.

setlocal

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: python not found on PATH. Install Python 3.10+ to build.
    pause
    exit /b 1
)

echo --- Creating temporary build venv ---
python -m venv build_venv
call build_venv\Scripts\activate.bat

echo --- Installing dependencies ---
pip install -r requirements.txt pyinstaller

echo --- Building exe ---
pyinstaller ^
    --onefile ^
    --windowed ^
    --name sprint_recap ^
    --clean ^
    sprint_recap.py

echo --- Done ---
echo Exe is at: dist\sprint_recap.exe
echo Copy it next to your .pptx template in OneDrive.

call build_venv\Scripts\deactivate.bat
pause
