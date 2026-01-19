<#
.SYNOPSIS
    Manage Docker volumes for AMALIA persistence

.DESCRIPTION
    This script helps manage Docker volumes for persistent data storage:
    - Agent configurations
    - Application data (models, sessions, MCP servers)
    - Logs
    
.EXAMPLE
    .\manage-volumes.ps1 -Action backup
    .\manage-volumes.ps1 -Action restore
    .\manage-volumes.ps1 -Action list
    .\manage-volumes.ps1 -Action clean
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("backup", "restore", "list", "clean", "inspect")]
    [string]$Action,
    
    [Parameter(Mandatory=$false)]
    [string]$BackupPath = ".\volume-backups"
)

$ErrorActionPreference = "Stop"

# Volume names
$volumes = @(
    "amalia_redis_data",
    "amalia_agent_configs",
    "amalia_app_data",
    "amalia_app_logs"
)

function Show-Volumes {
    Write-Host "`n=== Docker Volumes ===" -ForegroundColor Cyan
    foreach ($vol in $volumes) {
        $exists = docker volume inspect $vol 2>$null
        if ($LASTEXITCODE -eq 0) {
            $info = $exists | ConvertFrom-Json
            $mountpoint = $info.Mountpoint
            Write-Host "✓ $vol" -ForegroundColor Green
            Write-Host "  Location: $mountpoint" -ForegroundColor Gray
        } else {
            Write-Host "✗ $vol (not created)" -ForegroundColor Yellow
        }
    }
    Write-Host ""
}

function Backup-Volumes {
    Write-Host "`n=== Backing up volumes ===" -ForegroundColor Cyan
    
    # Create backup directory
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupDir = Join-Path $BackupPath $timestamp
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    
    foreach ($vol in $volumes) {
        Write-Host "Backing up $vol..." -ForegroundColor Yellow
        
        $backupFile = Join-Path $backupDir "$vol.tar"
        
        # Create a temporary container to access the volume
        docker run --rm `
            -v "${vol}:/volume" `
            -v "${backupDir}:/backup" `
            busybox `
            tar -czf "/backup/$vol.tar.gz" -C /volume .
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Backed up $vol" -ForegroundColor Green
        } else {
            Write-Host "✗ Failed to backup $vol" -ForegroundColor Red
        }
    }
    
    Write-Host "`nBackup completed: $backupDir" -ForegroundColor Green
}

function Restore-Volumes {
    Write-Host "`n=== Restoring volumes ===" -ForegroundColor Cyan
    
    # Find latest backup
    $latestBackup = Get-ChildItem -Path $BackupPath -Directory | 
        Sort-Object Name -Descending | 
        Select-Object -First 1
    
    if (-not $latestBackup) {
        Write-Host "✗ No backups found in $BackupPath" -ForegroundColor Red
        return
    }
    
    Write-Host "Restoring from: $($latestBackup.FullName)" -ForegroundColor Yellow
    
    foreach ($vol in $volumes) {
        $backupFile = Join-Path $latestBackup.FullName "$vol.tar.gz"
        
        if (Test-Path $backupFile) {
            Write-Host "Restoring $vol..." -ForegroundColor Yellow
            
            # Ensure volume exists
            docker volume create $vol | Out-Null
            
            # Restore from backup
            docker run --rm `
                -v "${vol}:/volume" `
                -v "$($latestBackup.FullName):/backup" `
                busybox `
                tar -xzf "/backup/$vol.tar.gz" -C /volume
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ Restored $vol" -ForegroundColor Green
            } else {
                Write-Host "✗ Failed to restore $vol" -ForegroundColor Red
            }
        } else {
            Write-Host "⊘ Skipping $vol (no backup found)" -ForegroundColor Gray
        }
    }
    
    Write-Host "`nRestore completed" -ForegroundColor Green
}

function Clean-Volumes {
    Write-Host "`n=== Cleaning volumes ===" -ForegroundColor Cyan
    Write-Host "WARNING: This will delete all persistent data!" -ForegroundColor Red
    $confirm = Read-Host "Type 'DELETE' to confirm"
    
    if ($confirm -ne "DELETE") {
        Write-Host "Cancelled" -ForegroundColor Yellow
        return
    }
    
    # Stop containers first
    Write-Host "Stopping containers..." -ForegroundColor Yellow
    docker compose down
    
    foreach ($vol in $volumes) {
        Write-Host "Removing $vol..." -ForegroundColor Yellow
        docker volume rm $vol 2>$null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Removed $vol" -ForegroundColor Green
        } else {
            Write-Host "⊘ $vol not found" -ForegroundColor Gray
        }
    }
    
    Write-Host "`nVolumes cleaned" -ForegroundColor Green
}

function Inspect-Volumes {
    Write-Host "`n=== Inspecting volumes ===" -ForegroundColor Cyan
    
    foreach ($vol in $volumes) {
        Write-Host "`n--- $vol ---" -ForegroundColor Yellow
        docker volume inspect $vol 2>$null | ConvertFrom-Json | ConvertTo-Json -Depth 10
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Volume not found" -ForegroundColor Gray
        }
    }
}

# Execute action
switch ($Action) {
    "list" { Show-Volumes }
    "backup" { Backup-Volumes }
    "restore" { Restore-Volumes }
    "clean" { Clean-Volumes }
    "inspect" { Inspect-Volumes }
}
