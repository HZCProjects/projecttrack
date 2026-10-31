PERMANENT FIX FOR VERSION 29 ISSUE

Problem: deploy.bat had hardcoded "VERSION 29" in commit message, so GitHub always showed VERSION 29 even though code was VERSION 31 final locked.

Solution: VERSION file is single source of truth.

- VERSION file contains "32"
- deploy.bat does: set /p VERSION=<VERSION -> uses VERSION 32 in commit message automatically
- deploy.ps1 does: $version = Get-Content VERSION

To update version permanently:
1. Edit VERSION file: change 32 to 33
2. Run .\deploy.bat
3. GitHub will show VERSION 33 automatically - no need to edit deploy.bat

No more VERSION 29 stuck.
