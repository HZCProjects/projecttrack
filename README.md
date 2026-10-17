# ProjectTrack v11 - FINAL FIX
- Fixed get_session bug (close after building dict)
- Fixed Save to Database - absolute /api paths
- Fixed Steel Monopole file - removed duplicate getSteelGPS inside saveCurrent()
- Quality Hub headings visibility fixed (dark bold)
- GPS Coordinates + Get Current GPS button
- Score 14.4px 20% bigger
- Simple homepage (no Master Dashboard)
- Postgres sessions persistent

## Default logins:
- admin / HZC2026! (admin)
- qc_lead / QC2026! (qc_manager)
- inspector / Inspect2026! (inspector)
- viewer / Viewer123 (viewer)

## Railway Deploy:
1. Upload all files to GitHub
2. Railway -> Variables -> Ensure DATABASE_URL exists (postgresql://...)
3. If missing: Add Postgres: New -> Database -> PostgreSQL
4. Redeploy
5. Login -> Save should work

## Files:
- app.py (main backend)
- index.html (simple homepage)
- quality_hub.html
- quality_check_multi.html (Steel Monopoles - FIXED SAVE)
- quality_check_wooden_pole.html (H-Pole Wooden)
- gantt_planner_DB.html
- users.html, login.html
