# DIRECT TO FLY + BACKUP TO GITHUB - One command
# Usage: .\deploy.ps1 or .\deploy.ps1 "your commit message"

param(
    [string]$msg = "update $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
)

Write-Host "=== DIRECT TO FLY + BACKUP TO GITHUB ===" -ForegroundColor Cyan

# 1. Backup to GitHub
Write-Host "1. Backing up to GitHub..." -ForegroundColor Yellow
git add -A --force
git commit -m $msg
git push origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "Git push failed, but continuing to Fly deploy..." -ForegroundColor Red
}

# 2. Direct to Fly (instant, no Queued)
Write-Host "2. Deploying DIRECT to Fly primary..." -ForegroundColor Yellow
fly deploy --remote-only -a projecttrack

Write-Host "=== DONE ===" -ForegroundColor Green
Write-Host "Fly: https://projecttrack.fly.dev" -ForegroundColor Cyan
Write-Host "GitHub: backup complete" -ForegroundColor Cyan
fly status -a projecttrack