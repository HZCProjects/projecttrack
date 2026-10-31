from pathlib import Path
import sqlite3, os
from flask import Flask, render_template, request, redirect, session, g

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "projecttrack-secret-2026-HZC")

DATA_DIR = Path("/data")
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE = str(DATA_DIR / "projecttrack.db")
except Exception:
    DATABASE = "projecttrack.db"

ROOT_EMAIL = "HCE@Projects2026"
ROOT_PASS = "HZC@2026"

def get_db():
    db = getattr(g, "_db", None)
    if db is None:
        db = g._db = sqlite3.connect(DATABASE, check_same_thread=False)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    try:
        db = get_db()
        cur = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if cur.fetchone():
            cols = [r["name"] for r in db.execute("PRAGMA table_info(users)")]
            if "password" not in cols or "email" not in cols:
                db.execute("DROP TABLE users")
                db.commit()
        db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, surname TEXT, email TEXT UNIQUE, password TEXT, is_root INTEGER DEFAULT 0)")
        db.commit()
        cur = db.execute("SELECT COUNT(*) as c FROM users")
        if cur.fetchone()["c"] == 0:
            db.execute("INSERT INTO users (name,surname,email,password,is_root) VALUES (?,?,?,?,1)", ("ROOT","ROOT", ROOT_EMAIL, ROOT_PASS))
            db.commit()
            print(f"ROOT created {ROOT_EMAIL}")
    except Exception as e:
        print(f"init_db error {e}")

@app.before_request
def before():
    init_db()

@app.teardown_appcontext
def close_db(exc):
    db = getattr(g, "_db", None)
    if db:
        try:
            db.close()
        except:
            pass

@app.route("/")
def index():
    return redirect("/login")

@app.route("/login", methods=["GET","POST"])
def login():
    msg=""
    if request.method=="POST":
        email=request.form.get("email","").strip()
        pwd=request.form.get("password","").strip()
        try:
            db=get_db()
            cur=db.execute("SELECT * FROM users WHERE email=? AND password=?",(email,pwd))
            u=cur.fetchone()
            if u:
                session["user"]=u["email"]
                return redirect("/dashboard")
            msg="Invalid Username / Password"
        except Exception as e:
            msg=str(e)
    return render_template("login.html", msg=msg)

@app.route("/register", methods=["GET","POST"])
@app.route("/create", methods=["GET","POST"])
@app.route("/signup", methods=["GET","POST"])
def register():
    msg=""
    if request.method=="POST":
        name=request.form.get("name","").strip()
        surname=request.form.get("surname","").strip()
        email=request.form.get("email","").strip()
        pwd=request.form.get("password","").strip()
        repeat=request.form.get("repeat","").strip()
        if not name or not surname or not email or not pwd:
            msg="*All Fields Must Be Completed"
        elif repeat and pwd!=repeat:
            msg="Passwords do not match"
        else:
            try:
                db=get_db()
                is_root=1 if email==ROOT_EMAIL else 0
                db.execute("INSERT INTO users (name,surname,email,password,is_root) VALUES (?,?,?,?,?)",(name,surname,email,pwd,is_root))
                db.commit()
                return redirect("/login")
            except Exception as e:
                msg="Username / Email exists"
    return render_template("create.html", msg=msg)

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    user = session["user"]
    html = f"<div style='font-family:Arial;padding:30px;'><h2>Welcome {user}</h2><p><a href='/logout'>Logout</a></p>"
    html += "<p>VERSION 28 Clean Locked - ALL FIXES: Volume /data/projecttrack.db | Fly jnb 512MB | Machine 8d9231ae37d0e8 restart always | Volume vol_vjy257w7yod8wnpv 1GB</p>"
    html += "<p>Primary: https://projecttrack.fly.dev - ok | Model: DIRECT TO FLY + BACKUP TO GITHUB - no Queued, never stopped again</p></div>"
    return html

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/forgot")
def forgot():
    return '<div style="font-family:Arial;padding:20px;"><h3>Forgot Username / Password?</h3><p>Contact ROOT HCE@Projects2026</p><a href="/login">Back</a></div>'

@app.route("/terms")
def terms():
    return '<div style="font-family:Arial;padding:20px;"><h3>Terms&Conditions - ProjectTrack SaaS</h3><p>VERSION 28 ALL FIXES</p><a href="/login">Back</a></div>'

@app.route("/health")
def health():
    return "ok", 200