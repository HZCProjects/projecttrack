# LOCAL TEST BEFORE FLY DEPLOY

VERSION 33 - Keep me signed in until logout - Final with local test

Why test locally first:
- Faster than fly deploy --remote-only (30 sec vs 3 min)
- Check User Management edit active, Logout shows selected username
- Check Sign Up saves last name + password auto-fill
- Check Keep me signed in checkbox
- Check login Root/root/HCE@Projects2026 case-insensitive

How to test locally:

1. Double-click run_local.bat
   or PowerShell: .\run_local.ps1

2. Browser opens:
   http://127.0.0.1:5000

3. Test steps:
   a) /create - Sign Up:
      - Fill Name, Surname (e.g. Hennie), Username, Password
      - Check "Keep me signed in until logout"
      - Check "I accept Terms"
      - SIGN UP
      - Should auto-fill next time + stay signed in

   b) /login:
      - Email or Username: Root (or root or HCE@Projects2026)
      - Password: HZC@2026
      - Check "Keep me signed in until logout"
      - SIGN IN -> goes to /users

   c) /users - User Management:
      - Left: Add User form with Role Permissions
      - Right: All Users table
      - Click Edit on any user -> left form becomes active with black border + banner "Editing: username"
      - Top bar: Logout (Display Name) | role - when editing, shows selected username
      - Edit field active test

   d) Check database:
      - File projecttrack.db created in folder
      - Close browser, reopen http://127.0.0.1:5000/users - should still be logged in if Keep me signed in checked
      - Click Logout -> should require login again

4. If local test OK, deploy to Fly:
   .\deploy.bat
   -> git push backup to GitHub + fly deploy direct to https://projecttrack.fly.dev + restart always

Database note:
- Locally: uses ./projecttrack.db
- On Fly: uses /data/projecttrack.db (volume vol_vjy257w7yod8wnpv)
