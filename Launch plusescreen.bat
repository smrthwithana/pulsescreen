@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating local Python environment...
    py -3.11 -m venv .venv >nul 2>nul
    if errorlevel 1 python -m venv .venv
    if errorlevel 1 (
        echo Could not create .venv. Install Python 3.11+ and try again.
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" -c "import pygame, sounddevice, numpy, spotipy, dotenv" >nul 2>nul
if errorlevel 1 (
    echo Installing plusescreen dependencies...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Dependency installation failed.
        pause
        exit /b 1
    )
)

if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "main.py"
) else (
    start "" ".venv\Scripts\python.exe" "main.py"
)

endlocal
