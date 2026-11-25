@echo off
rem Käivitab rakenduse sinu arvutis ja avab selle brauseris: http://localhost:8765
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv
  .venv\Scripts\python.exe -m pip install -q -r requirements.txt
)
start "" http://localhost:8765
echo Rakendus töötab aadressil http://localhost:8765  (sulgemiseks sulge see aken)
.venv\Scripts\python.exe -m http.server 8765 --directory app
