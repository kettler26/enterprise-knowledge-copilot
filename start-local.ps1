# Start API + static UI (no Node required). Browser: http://127.0.0.1:8000/ui/
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\apps\api
Write-Host "Starting SaaS Copilot API on http://127.0.0.1:8000"
Write-Host "Open UI: http://127.0.0.1:8000/ui/  (or http://127.0.0.1:8000/ -> redirect)"
Write-Host "Stop with Ctrl+C. If port 8000 is busy, close the old terminal or change the port below."
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
