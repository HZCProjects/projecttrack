Write-Host "=== LOCAL TEST - BEFORE FLY DEPLOY ===" -ForegroundColor Cyan
Write-Host "Installing requirements..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host ""
Write-Host "Starting local server at http://127.0.0.1:5000" -ForegroundColor Green
Write-Host "Test:" -ForegroundColor Yellow
Write-Host "- Sign Up: http://127.0.0.1:5000/create - check Keep me signed in until logout"
Write-Host "- Login: Root / HZC@2026"
Write-Host "- User Management: http://127.0.0.1:5000/users"
Write-Host "- Edit field active, Logout shows selected username"
Write-Host "- Last name + password auto-fill"
Write-Host ""
Write-Host "Press Ctrl+C to stop, then .\deploy.bat to deploy to Fly" -ForegroundColor Cyan
Write-Host ""

python app.py