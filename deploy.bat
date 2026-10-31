@echo off
echo === PROJECTTRACK - VERSION FILE PERMANENT ===
if exist VERSION (set /p VERSION=<VERSION) else (set VERSION=33)
echo VERSION %VERSION% - Choose: Test Local First or Deploy to Fly Direct
echo.

if not exist ".git" (
  echo .git missing - restoring...
  git init
  git branch -M main
  git remote add origin https://github.com/HZCProjects/projecttrack.git 2>nul
  git remote set-url origin https://github.com/HZCProjects/projecttrack.git
)

echo 1. Backup to GitHub https://github.com/HZCProjects/projecttrack.git ...
git add -A --force
git commit -m "VERSION %VERSION% - Keep me signed in + local test option - %date% %time% - direct fly + backup github"
git push origin main

echo 2. Deploy DIRECT to Fly https://projecttrack.fly.dev ...
fly deploy --remote-only -a projecttrack

echo 3. Lock machine 8d9231ae37d0e8 restart always (never stopped)...
fly machine update 8d9231ae37d0e8 --restart always -a projecttrack --yes
fly machine start 8d9231ae37d0e8 -a projecttrack

echo.
echo === DONE VERSION %VERSION% ===
fly status -a projecttrack
curl.exe https://projecttrack.fly.dev/health
pause