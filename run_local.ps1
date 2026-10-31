Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "PROJECTTRACK - LOCAL TEST BEFORE FLY" -ForegroundColor Cyan
Write-Host "VERSION 33 - Keep me signed in until logout" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "Option 1: Test Locally First (recommended) = this script"
Write-Host "Option 2: Deploy Direct to Fly = .\deploy.bat"
Write-Host ""
Write-Host "Installing requirements..." -ForegroundColor Yellow
pip install -r requirements.txt
Write-Host ""
Write-Host "Starting LOCAL server at http://127.0.0.1:5000" -ForegroundColor Green
Write-Host "TEST:"
Write-Host "- /create : Keep me signed in + Surname auto-fill"
Write-Host "- /login : Root / HZC@2026 + Keep me signed in"
Write-Host "- /users : Edit active, Logout shows selected"
Write-Host ""
Write-Host "Press Ctrl+C to stop, then .\deploy.bat to deploy to Fly" -ForegroundColor Cyan
python app.py