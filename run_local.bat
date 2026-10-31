@echo off
echo === LOCAL TEST - BEFORE FLY DEPLOY ===
echo Installing requirements...
pip install -r requirements.txt

echo.
echo Starting local server at http://127.0.0.1:5000
echo Test:
echo - Sign Up: http://127.0.0.1:5000/create - check Keep me signed in until logout
echo - Login: Root / HZC@2026
echo - User Management: http://127.0.0.1:5000/users - Edit field active, Logout (root) shows selected username
echo - Last name + password auto-fill (cleared by browser cache)
echo.
echo Press Ctrl+C to stop local test, then run .\deploy.bat to deploy to Fly
echo.
python app.py
pause