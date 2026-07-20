@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    python -m venv .venv
)

call .venv\Scripts\activate.bat
pip install -q -r requirements.txt
python main.py
