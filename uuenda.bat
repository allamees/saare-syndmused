@echo off
rem Kogub sündmused kõigist allikatest uuesti (app\events.json)
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv (
  echo Esimene käivitus: paigaldan vajalikud teegid...
  python -m venv .venv
  .venv\Scripts\python.exe -m pip install -q -r requirements.txt
)
set PYTHONIOENCODING=utf-8
.venv\Scripts\python.exe -m scraper.run
pause
