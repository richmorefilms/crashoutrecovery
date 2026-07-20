$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& .\.venv\Scripts\Activate.ps1
pip install -q -r requirements.txt
Write-Host ""
Write-Host "  Crashout Recovery at http://127.0.0.1:8777" -ForegroundColor Green
Write-Host ""
python main.py
