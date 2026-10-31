@echo off
echo === DIRECT TO FLY + BACKUP TO GITHUB - VERSION 29 ===
echo Checking .git...

if not exist ".git" (
  echo .git missing - restoring...
  git init
  git branch -M main
  git remote add origin https://github.com/HZCProjects/projecttrack.git 2>nul
  git remote set-url origin https://github.com/HZCProjects/projecttrack.git
)

echo 1. Backing up to GitHub https://github.com/HZCProjects/projecttrack.git ...
git add -A --force
git commit -m "VERSION 29 - %date% %time% - direct fly + backup github" 2>nul
git push origin main

echo 2. Deploying DIRECT to Fly primary...
fly deploy --remote-only -a projecttrack

echo 3. Locking machine to never stop again...
fly machine update 8d9231ae37d0e8 --restart always -a projecttrack --yes
fly machine start 8d9231ae37d0e8 -a projecttrack

echo === DONE ===
fly status -a projecttrack
curl.exe https://projecttrack.fly.dev/health
pause