$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
Write-Host "Running JS tone regression tests..." -ForegroundColor Cyan
node tests/tone/test_decision_flow_js.js
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "JS tests passed." -ForegroundColor Green
