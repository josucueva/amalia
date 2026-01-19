<#
.SYNOPSIS
    Initialize Docker volumes with existing local data

.DESCRIPTION
    Copies existing data from local directories into Docker volumes.
    Useful for first-time setup or migrating from local development.

.EXAMPLE
    .\init-volumes.ps1
#>

$ErrorActionPreference = "Stop"

Write-Host "`n=== Initializing Docker Volumes ===" -ForegroundColor Cyan

# Ensure volumes exist
Write-Host "`nCreating volumes..." -ForegroundColor Yellow
docker volume create amalia_agent_configs | Out-Null
docker volume create amalia_app_data | Out-Null
docker volume create amalia_app_logs | Out-Null
docker volume create amalia_redis_data | Out-Null

Write-Host "✓ Volumes created" -ForegroundColor Green

# Copy agent configs if they exist locally
if (Test-Path ".\config\agents") {
    Write-Host "`nCopying agent configurations..." -ForegroundColor Yellow
    
    $agentFiles = Get-ChildItem -Path ".\config\agents\*.yaml" -ErrorAction SilentlyContinue
    
    if ($agentFiles) {
        # Create temporary container to copy files
        docker run --rm `
            -v "amalia_agent_configs:/volume" `
            -v "${PWD}\config\agents:/source" `
            busybox `
            sh -c "cp /source/*.yaml /volume/ 2>/dev/null || true"
        
        Write-Host "✓ Copied $($agentFiles.Count) agent config files" -ForegroundColor Green
    } else {
        Write-Host "⊘ No agent config files found in .\config\agents" -ForegroundColor Gray
    }
} else {
    Write-Host "⊘ .\config\agents directory not found" -ForegroundColor Gray
}

# Copy application data if it exists locally
if (Test-Path ".\data") {
    Write-Host "`nCopying application data..." -ForegroundColor Yellow
    
    $dataFiles = Get-ChildItem -Path ".\data" -File -ErrorAction SilentlyContinue
    
    if ($dataFiles) {
        # Copy JSON files
        docker run --rm `
            -v "amalia_app_data:/volume" `
            -v "${PWD}\data:/source" `
            busybox `
            sh -c "cp /source/*.json /volume/ 2>/dev/null || true"
        
        Write-Host "✓ Copied data files" -ForegroundColor Green
    }
    
    # Copy uploads directory if it exists
    if (Test-Path ".\data\uploads") {
        docker run --rm `
            -v "amalia_app_data:/volume" `
            -v "${PWD}\data\uploads:/source" `
            busybox `
            sh -c "mkdir -p /volume/uploads && cp -r /source/* /volume/uploads/ 2>/dev/null || true"
        
        Write-Host "✓ Copied uploads directory" -ForegroundColor Green
    }
} else {
    Write-Host "⊘ .\data directory not found" -ForegroundColor Gray
}

Write-Host "`n=== Volume Initialization Complete ===" -ForegroundColor Green
Write-Host "`nVolumes are ready to use. Start the application with:" -ForegroundColor Cyan
Write-Host "  docker compose up" -ForegroundColor White
Write-Host "`nTo view volume contents:" -ForegroundColor Cyan
Write-Host "  .\manage-volumes.ps1 -Action list" -ForegroundColor White
Write-Host ""
