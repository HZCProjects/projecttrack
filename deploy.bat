@echo off
echo === VERSION 33 PERMANENT CLEAN - NO README ===
if exist VERSION (set /p VERSION=<VERSION) else (set VERSION=33)
echo VERSION %VERSION%

echo Cleaning README clutter permanently (so it never piles up)...
del /q README*.md LOCAL_TEST_README.md 2>nul
if exist ".git" (
  echo Removing README from git tracking...
  git rm --cached -r --quiet README*.md LOCAL_TEST_README.md 2>nul
)

if not exist ".git" (
  git init
  git branch -M main
  git remote add origin https://github.com/HZCProjects/projecttrack.git 2>nul
  git remote set-url origin https://github.com/HZCProjects/projecttrack.git
)

echo 1. Backup to GitHub https://github.com/HZCProjects/projecttrack.git ...
git add -A --force
git commit -m "VERSION %VERSION% - Permanent clean no README - Keep me signed in - %date% %time% - direct fly + backup github"
git push origin main

echo 2. Deploy DIRECT to Fly https://projecttrack.fly.dev ...
fly deploy --remote-only -a projecttrack

echo 3. Lock machine 8d9231ae37d0e8 restart always...
fly machine update 8d9231ae37d0e8 --restart always -a projecttrack --yes
fly machine start 8d9231ae37d0e8 -a projecttrack

echo === DONE VERSION %VERSION% - CLEAN NO README ===
fly status -a projecttrack
curl.exe https://projecttrack.fly.dev/health
pause