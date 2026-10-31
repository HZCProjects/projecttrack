from pathlib import Path
import sqlite3, os
from datetime import datetime
from flask import Flask, render_template, request, redirect, session, g, jsonify

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
        # Create base table if not exists
        db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, surname TEXT, email TEXT UNIQUE, password TEXT, is_root INTEGER DEFAULT 0)")
        # Check columns
        cols = [r["name"] for r in db.execute("PRAGMA table_info(users)")]
        # Migrate old schema without password/email
        if "password" not in cols or "email" not in cols:
            db.execute("DROP TABLE users")
            db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, surname TEXT, email TEXT UNIQUE, password TEXT, is_root INTEGER DEFAULT 0)")
            cols = ["id","name","surname","email","password","is_root"]
        # Add new columns for Step3
        if "role" not in cols:
            db.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'viewer'")
        if "display_name" not in cols:
            db.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
        if "last_login" not in cols:
            db.execute("ALTER TABLE users ADD COLUMN last_login TEXT")
        if "username" not in cols:
            db.execute("ALTER TABLE users ADD COLUMN username TEXT")
        db.commit()
        # Ensure ROOT exists
        cur = db.execute("SELECT COUNT(*) as c FROM users")
        if cur.fetchone()["c"] == 0:
            db.execute("INSERT INTO users (name,surname,email,username,password,is_root,role,display_name) VALUES (?,?,?,?,?,?,?,?)", ("ROOT","ROOT", ROOT_EMAIL, "root", ROOT_PASS, 1, "root", "Root Super Admin"))
            db.commit()
            print(f"ROOT created {ROOT_EMAIL}")
        else:
            # Ensure root user has role root
            cur = db.execute("SELECT * FROM users WHERE email=?", (ROOT_EMAIL,))
            u = cur.fetchone()
            if u and u["role"] != "root":
                db.execute("UPDATE users SET role='root', is_root=1, username='root' WHERE email=?", (ROOT_EMAIL,))
                db.commit()
    except Exception as e:
        print(f"init_db error {e}")
        import traceback; traceback.print_exc()

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

def current_user():
    if "user" not in session:
        return None
    db = get_db()
    cur = db.execute("SELECT * FROM users WHERE email=? OR username=?", (session["user"], session["user"]))
    return cur.fetchone()

def is_root_user(u):
    return u and (u["role"] == "root" or u["is_root"] == 1)

def is_admin_user(u):
    return u and (u["role"] in ("root","admin") or u["is_root"]==1)

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
            cur=db.execute("SELECT * FROM users WHERE (email=? OR username=?) AND password=?",(email,email,pwd))
            u=cur.fetchone()
            if u:
                session["user"]=u["email"] or u["username"]
                # update last login
                now = datetime.now().strftime("%d %b %Y, %H:%M")
                db.execute("UPDATE users SET last_login=? WHERE id=?", (now, u["id"]))
                db.commit()
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
                role="root" if is_root else "viewer"
                db.execute("INSERT INTO users (name,surname,email,username,password,is_root,role,display_name) VALUES (?,?,?,?,?,?,?,?)",(name,surname,email,email,pwd,is_root,role,f"{name} {surname}"))
                db.commit()
                return redirect("/login")
            except Exception as e:
                msg="Username / Email exists"
    return render_template("create.html", msg=msg)

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    u = current_user()
    if not u:
        return redirect("/login")
    return redirect("/users")

@app.route("/users", methods=["GET","POST"])
def users():
    if "user" not in session:
        return redirect("/login")
    cur_u = current_user()
    if not cur_u or not is_admin_user(cur_u):
        return "<div style='font-family:Arial;padding:30px;'><h3>Access Denied - Admin/Root only</h3><a href='/login'>Login</a></div>", 403

    db = get_db()
    msg = ""
    edit_user = None

    # Handle Add User
    if request.method == "POST":
        action = request.form.get("action","add")
        if action == "add":
            username = request.form.get("username","").strip()
            display_name = request.form.get("display_name","").strip() or username
            password = request.form.get("password","").strip()
            role = request.form.get("role","viewer").strip()
            # Only Root can create other Root
            if role == "root" and not is_root_user(cur_u):
                msg = "Only Root can create other Root users"
            elif not username or not password:
                msg = "Username and Password required"
            else:
                try:
                    # name/surname split from display_name or username
                    name = display_name.split()[0] if display_name else username
                    surname = " ".join(display_name.split()[1:]) if len(display_name.split())>1 else ""
                    is_root = 1 if role=="root" else 0
                    db.execute("INSERT INTO users (name,surname,email,username,password,is_root,role,display_name,last_login) VALUES (?,?,?,?,?,?,?,?,?)",
                               (name, surname, username, username, password, is_root, role, display_name, "Never"))
                    db.commit()
                    msg = f"User {username} added"
                except Exception as e:
                    msg = f"Username exists: {username}"
        elif action == "edit":
            uid = request.form.get("id")
            username = request.form.get("username","").strip()
            display_name = request.form.get("display_name","").strip()
            password = request.form.get("password","").strip()
            role = request.form.get("role","viewer").strip()
            if role == "root" and not is_root_user(cur_u):
                msg = "Only Root can set Root role"
            else:
                try:
                    if password:
                        db.execute("UPDATE users SET username=?, display_name=?, password=?, role=?, is_root=?, email=? WHERE id=?", (username, display_name, password, role, 1 if role=="root" else 0, username, uid))
                    else:
                        db.execute("UPDATE users SET username=?, display_name=?, role=?, is_root=?, email=? WHERE id=?", (username, display_name, role, 1 if role=="root" else 0, username, uid))
                    db.commit()
                    msg = f"User {username} updated"
                except Exception as e:
                    msg = str(e)

    # Handle edit query
    edit_id = request.args.get("edit")
    if edit_id:
        cur = db.execute("SELECT * FROM users WHERE id=?", (edit_id,))
        edit_user = cur.fetchone()

    # Get all users
    cur = db.execute("SELECT * FROM users ORDER BY id ASC")
    all_users = cur.fetchall()

    return render_template("user_management.html", users=all_users, current=cur_u, edit_user=edit_user, msg=msg)

@app.route("/users/delete/<int:uid>")
def delete_user(uid):
    if "user" not in session:
        return redirect("/login")
    cur_u = current_user()
    if not cur_u or not is_admin_user(cur_u):
        return "Access Denied", 403
    # Admin cannot delete main user ID 1
    if uid == 1 and not is_root_user(cur_u):
        return "Admin cannot delete main user (ID 1)", 403
    db = get_db()
    # Prevent deleting self
    if cur_u["id"] == uid:
        return "Cannot delete yourself", 400
    db.execute("DELETE FROM users WHERE id=?", (uid,))
    db.commit()
    return redirect("/users")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/forgot")
def forgot():
    return '<div style="font-family:Arial;padding:20px;"><h3>Forgot Username / Password?</h3><p>Contact ROOT HCE@Projects2026</p><a href="/login">Back</a></div>'

@app.route("/terms")
def terms():
    return '<div style="font-family:Arial;padding:20px;"><h3>Terms&Conditions - ProjectTrack SaaS</h3><p>VERSION 32 User Management</p><a href="/login">Back</a></div>'

@app.route("/health")
def health():
    return "ok", 200