@echo off
echo === DIRECT TO FLY + BACKUP TO GITHUB ===
echo 1. Backing up to GitHub...
git add -A --force
git commit -m "direct fly %date% %time%"
git push origin main
echo 2. Deploying DIRECT to Fly...
fly deploy --remote-only -a projecttrack
echo === DONE ===
fly status -a projecttrack
pause