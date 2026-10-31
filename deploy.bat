@echo off
echo === PERMANENT VERSIONING - READS VERSION FILE ===
if exist VERSION (
  set /p VERSION=<VERSION
) else (
  set VERSION=32
)
echo VERSION 33 - Keep me signed in

if not exist ".git" (
  echo .git missing - restoring...
  git init
  git branch -M main
  git remote add origin https://github.com/HZCProjects/projecttrack.git 2>nul
  git remote set-url origin https://github.com/HZCProjects/projecttrack.git
)

echo 1. Backing up to GitHub...
git add -A --force
git commit -m "VERSION 33 - Keep me signed in - User Management - Root displays selected username - %date% %time% - direct fly + backup github"
git push origin main

echo 2. Deploying DIRECT to Fly...
fly deploy --remote-only -a projecttrack

echo 3. Locking restart always...
fly machine update 8d9231ae37d0e8 --restart always -a projecttrack --yes
fly machine start 8d9231ae37d0e8 -a projecttrack

echo === DONE VERSION 33 - Keep me signed in ===
fly status -a projecttrack
curl.exe https://projecttrack.fly.dev/health
pause