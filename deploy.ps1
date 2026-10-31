# DIRECT TO FLY + BACKUP TO GITHUB - VERSION 29 - Auto restores .git if missing
param([string]$msg = "VERSION 29 - $(Get-Date -Format 'yyyy-MM-dd HH:mm')")

Write-Host "=== DIRECT TO FLY + BACKUP TO GITHUB ===" -ForegroundColor Cyan

if (-not (Test-Path ".git")) {
  Write-Host ".git missing - restoring..." -ForegroundColor Yellow
  git init
  git branch -M main
  git remote add origin https://github.com/HZCProjects/projecttrack.git 2>$null
  git remote set-url origin https://github.com/HZCProjects/projecttrack.git
}

Write-Host "1. Backing up to GitHub..." -ForegroundColor Yellow
git add -A --force
git commit -m $msg
git push origin main

Write-Host "2. Deploying DIRECT to Fly..." -ForegroundColor Yellow
fly deploy --remote-only -a projecttrack

Write-Host "3. Locking restart always - never stopped again..." -ForegroundColor Yellow
fly machine update 8d9231ae37d0e8 --restart always -a projecttrack --yes
fly machine start 8d9231ae37d0e8 -a projecttrack

Write-Host "=== DONE VERSION 29 started ===" -ForegroundColor Green
fly status -a projecttrack
curl.exe https://projecttrack.fly.dev/health