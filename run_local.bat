@echo off
echo ===========================================
echo PROJECTTRACK - LOCAL TEST BEFORE FLY
echo VERSION 33 - Keep me signed in until logout
echo ===========================================
echo Option 1: Test Locally First (recommended)
echo Option 2: Deploy Direct to Fly is .\deploy.bat
echo.
echo Installing requirements...
pip install -r requirements.txt
echo.
echo Starting LOCAL server at http://127.0.0.1:5000
echo.
echo TEST:
echo - /create : Keep me signed in checkbox + Surname + Password auto-fill
echo - /login  : Root / HZC@2026 case-insensitive + Keep me signed in
echo - /users  : Edit field active, Logout shows selected username
echo.
echo Press Ctrl+C to stop local test
echo When OK, run .\deploy.bat to deploy to Fly https://projecttrack.fly.dev
echo ===========================================
python app.py
pause