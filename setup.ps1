# Agentic AutoML Platform - Setup Script
# This script sets up the development environment

Write-Host "Agentic AutoML Platform Setup" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "Checking Python version..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "OK $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}

# Check Node.js version
Write-Host "Checking Node.js version..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    Write-Host "OK Node.js $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Node.js not found. Please install Node.js 18+" -ForegroundColor Red
    exit 1
}

# Create directories
Write-Host ""
Write-Host "Creating required directories..." -ForegroundColor Yellow
$directories = @(
    "data\uploads",
    "logs"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        Write-Host "OK Created $dir" -ForegroundColor Green
    } else {
        Write-Host "OK $dir already exists" -ForegroundColor Green
    }
}

# Setup backend
Write-Host ""
Write-Host "Setting up backend..." -ForegroundColor Yellow
Push-Location backend

# Create virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    Write-Host "OK Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment and install dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
$activateScript = Join-Path (Get-Location) ".venv\Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    & $activateScript
    pip install -r requirements.txt --quiet
    Write-Host "OK Python dependencies installed" -ForegroundColor Green
} else {
    Write-Host "WARNING: Could not find activation script, installing globally..." -ForegroundColor Yellow
    python -m pip install -r requirements.txt --quiet
    Write-Host "OK Python dependencies installed" -ForegroundColor Green
}

Pop-Location

# Setup frontend
Write-Host ""
Write-Host "Setting up frontend..." -ForegroundColor Yellow
Push-Location frontend

if (-not (Test-Path "node_modules")) {
    Write-Host "Installing Node.js dependencies..." -ForegroundColor Yellow
    npm install --silent
    Write-Host "OK Node.js dependencies installed" -ForegroundColor Green
} else {
    Write-Host "OK Node.js dependencies already installed" -ForegroundColor Green
}

Pop-Location

# Create .env file if it does not exist
Write-Host ""
Write-Host "Checking environment configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "OK Created .env file (please update with your API keys)" -ForegroundColor Green
} else {
    Write-Host "OK .env file already exists" -ForegroundColor Green
}

# Summary
Write-Host ""
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "Setup completed successfully!" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Edit .env file and add your API keys" -ForegroundColor White
Write-Host "2. Start the backend:"  -ForegroundColor White
Write-Host "   cd backend" -ForegroundColor Cyan
Write-Host "   .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "   uvicorn app.main:app --reload" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. In a new terminal, start the frontend:" -ForegroundColor White
Write-Host "   cd frontend" -ForegroundColor Cyan
Write-Host "   npm run dev" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. Open http://localhost:5173 in your browser" -ForegroundColor White
Write-Host ""
Write-Host "For more information, see QUICKSTART.md" -ForegroundColor Yellow
Write-Host ""
