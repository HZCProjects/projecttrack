
import os
from pathlib import Path
import sqlite3
from flask import Flask, render_template, request, redirect, session, g

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "projecttrack-secret-2026-HZC")

# ALWAYS use /data when mounted, else local
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
        try:
            db = g._db = sqlite3.connect(DATABASE, check_same_thread=False)
            db.row_factory = sqlite3.Row
        except Exception as e:
            print(f"DB connect error {e}")
            db = g._db = sqlite3.connect(":memory:", check_same_thread=False)
            db.row_factory = sqlite3.Row
    return db

def init_db():
    try:
        db = get_db()
        db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT, is_root INTEGER DEFAULT 0)")
        db.commit()
        cur = db.execute("SELECT COUNT(*) as c FROM users")
        count = cur.fetchone()["c"]
        if count == 0:
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
    return f'<h2 style="font-family:Arial;padding:20px;">Welcome {session["user"]}<br><a href="/logout">Logout</a><br><br>Fly primary OK: https://projecttrack.fly.dev<br>Volume: {DATABASE}</h2>'

@app.route("/forgot")
def forgot():
    return '<h3>Reset - contact ROOT HCE@Projects2026</h3><a href="/login">Back to login</a>'

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# health check for Fly
@app.route("/health")
def health():
    return "ok", 200
