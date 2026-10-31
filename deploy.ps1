$version = "33"
if (Test-Path "VERSION") { $version = (Get-Content VERSION -Raw).Trim() }
Write-Host "=== VERSION $version - PROJECTTRACK ===" -ForegroundColor Cyan
if (-not (Test-Path ".git")) {
  git init; git branch -M main
  git remote add origin https://github.com/HZCProjects/projecttrack.git 2>$null
  git remote set-url origin https://github.com/HZCProjects/projecttrack.git
}
Write-Host "1. Backup to GitHub..." -ForegroundColor Yellow
git add -A --force
git commit -m "VERSION $version - Keep me signed in + local test - $(Get-Date -Format 'yyyy-MM-dd HH:mm') - direct fly + backup github"
git push origin main
Write-Host "2. Deploy DIRECT to Fly..." -ForegroundColor Yellow
fly deploy --remote-only -a projecttrack
Write-Host "3. Lock restart always..." -ForegroundColor Yellow
fly machine update 8d9231ae37d0e8 --restart always -a projecttrack --yes
fly machine start 8d9231ae37d0e8 -a projecttrack
Write-Host "=== DONE VERSION $version ===" -ForegroundColor Green
fly status -a projecttrack