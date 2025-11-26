# Agentic AutoML Platform - Run Script
# This script starts both backend and frontend in separate terminals

Write-Host "Starting Agentic AutoML Platform..." -ForegroundColor Cyan
Write-Host ""

# Get the current directory
$rootDir = Get-Location

# Start backend in new window
Write-Host "Starting backend server..." -ForegroundColor Yellow
$backendCommand = "Set-Location '$rootDir\backend'; & '.\venv\Scripts\Activate.ps1'; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCommand

Start-Sleep -Seconds 2

# Start frontend in new window
Write-Host "Starting frontend server..." -ForegroundColor Yellow
$frontendCommand = "Set-Location '$rootDir\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCommand

Write-Host ""
Write-Host "OK Both servers starting..." -ForegroundColor Green
Write-Host ""
Write-Host "Backend: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C in each terminal window to stop the servers" -ForegroundColor Yellow
