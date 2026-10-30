# STEP 1c - User Account Database First - Real DB

## Database - users table
- id PK, name, email unique, password_hash, role (ROOT/admin/manager/viewer), is_active, created_at, last_login, token, token_expiry
- Password hashed with werkzeug
- Auto creates default users: root@hzcprojects.com/root123 (ROOT), admin@hzcprojects.com/admin123, viewer@hzcprojects.com/viewer123

## Files
- app.py - Flask + SQLAlchemy + PostgreSQL/SQLite auto, /api/auth/register, /api/auth/login, /api/users
- login.html - 3 tabs: Sign in, Create Account (DB), Users DB list + delete
- index.html - Dashboard checks token, shows user
- requirements.txt - Flask, Flask-SQLAlchemy, SQLAlchemy, psycopg2-binary, gunicorn
- Procfile

## Railway Setup
1. Add PostgreSQL plugin in Railway (or use SQLite fallback projecttrack.db)
2. DATABASE_URL auto set by Railway
3. Deploy - tables auto create, default users auto created
4. Login with root@hzcprojects.com / root123

## API
POST /api/auth/register {name,email,password,role}
POST /api/auth/login {email,password} -> token + user
GET /api/users -> list
DELETE /api/users/:id -> delete (admin/ROOT only)
GET /health -> DB status
