# PROJECTTRACK - ALWAYS BOTH OPTIONS

Every zip from now on has BOTH options:

OPTION 1: TEST LOCALLY FIRST (recommended)
-------------------------------------------
.\run_local.bat  or  .\run_local.ps1
-> http://127.0.0.1:5000
-> Test Sign Up keep me signed in + last name auto-fill
-> Test User Management edit active + Logout shows selected username
-> Database: ./projecttrack.db (local)
-> Press Ctrl+C to stop

OPTION 2: DEPLOY DIRECT TO FLY
------------------------------
.\deploy.bat  or  .\deploy.ps1
-> Backup to GitHub https://github.com/HZCProjects/projecttrack.git (reads VERSION file)
-> Deploy direct to https://projecttrack.fly.dev (fly deploy --remote-only)
-> Lock machine 8d9231ae37d0e8 restart always (never stopped)
-> Database: /data/projecttrack.db volume vol_vjy257w7yod8wnpv
-> VERSION file = single source of truth, no more VERSION 29 stuck

PERMANENT FIXES INCLUDED:
- VERSION file reads automatically - GitHub commit message shows correct VERSION
- Keep me signed in until logout checkbox on /create and /login (30-day cookie)
- Sign Up saves last name + password auto-fill (autocomplete family-name + new-password + localStorage, cleared by browser cache)
- Login case-insensitive Root/root/HCE@Projects2026
- User Management: Edit field active, Logout (root) shows selected username when editing
- Fly machine 8d9231ae37d0e8 VERSION 31 final locked base + User Management

WORKFLOW:
Local OK? -> .\deploy.bat -> GitHub VERSION 33 -> Fly https://projecttrack.fly.dev
