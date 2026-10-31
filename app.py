
import os
from pathlib import Path
import sqlite3
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
        # check existing table schema
        cur = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        table_exists = cur.fetchone() is not None
        if table_exists:
            # check columns
            cols = [r["name"] for r in db.execute("PRAGMA table_info(users)")]
            if "password" not in cols or "is_root" not in cols:
                print(f"OLD schema found {cols} -> dropping and recreating")
                db.execute("DROP TABLE IF EXISTS users")
                db.commit()
                table_exists = False

        if not table_exists:
            db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT, is_root INTEGER DEFAULT 0)")
            db.commit()

        # ensure ROOT exists
        cur = db.execute("SELECT COUNT(*) as c FROM users")
        if cur.fetchone()["c"] == 0:
            db.execute("INSERT INTO users (email,password,is_root) VALUES (?,?,1)", (ROOT_EMAIL, ROOT_PASS))
            db.commit()
            print(f"ROOT created {ROOT_EMAIL}")
    except Exception as e:
        print(f"init_db error: {e}")
        import traceback; traceback.print_exc()

@app.before_request
def before():
    init_db()

@app.teardown_appcontext
def close_db(exc):
    db = getattr(g, "_db", None)
    if db is not None:
        try:
            db.close()
        except:
            pass

@app.route("/")
def index():
    if "user" in session:
        return redirect("/dashboard")
    return redirect("/login")

@app.route("/register", methods=["GET","POST"])
@app.route("/create", methods=["GET","POST"])
def create():
    msg=""
    if request.method=="POST":
        email=request.form.get("email","").strip()
        pwd=request.form.get("password","").strip()
        if not email or not pwd:
            msg="Fill all fields"
        else:
            try:
                db=get_db()
                db.execute("INSERT INTO users (email,password,is_root) VALUES (?,?,0)",(email,pwd))
                db.commit()
                return redirect("/login")
            except sqlite3.IntegrityError:
                msg="Email exists"
            except Exception as e:
                msg=f"Error: {e}"
    return render_template("create.html", msg=msg)

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
            else:
                msg="Invalid login"
        except Exception as e:
            msg=f"DB error: {e}"
    return render_template("login.html", msg=msg)

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return f'<h2 style="font-family:Arial;padding:20px;">Welcome {session["user"]}<br><a href="/logout">Logout</a><br><br>Fly OK: https://projecttrack.fly.dev<br>Machine: jnb<br>DB: {DATABASE}</h2>'

@app.route("/forgot")
def forgot():
    return '<h3>Reset - contact ROOT HCE@Projects2026</h3><a href="/login">Back</a>'

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/health")
def health():
    return "ok", 200
