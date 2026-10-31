import os, sqlite3
from flask import Flask, render_template, request, redirect, session, g

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "projecttrack-secret-2026")
DATABASE = "/data/projecttrack.db" if os.path.exists("/data") else "projecttrack.db"

ROOT_EMAIL = "HCE@Projects2026"
ROOT_PASS = "HZC@2026"

def get_db():
    db = getattr(g, "_db", None)
    if db is None:
        os.makedirs(os.path.dirname(DATABASE) if "/" in DATABASE else ".", exist_ok=True)
        db = g._db = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT, is_root INTEGER DEFAULT 0)")
    db.commit()
    # ensure ROOT exists first
    cur = db.execute("SELECT * FROM users WHERE email=?", (ROOT_EMAIL,))
    if not cur.fetchone():
        db.execute("INSERT INTO users (email,password,is_root) VALUES (?,?,1)", (ROOT_EMAIL, ROOT_PASS))
        db.commit()

@app.before_request
def before():
    init_db()

@app.teardown_appcontext
def close_db(exc):
    db = getattr(g, "_db", None)
    if db is not None:
        db.close()

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
                is_root=1 if (email==ROOT_EMAIL and db.execute("SELECT COUNT(*) FROM users").fetchone()[0]==0) else 0
                # first user logic: if ROOT already exists, this is normal user
                # if email is ROOT and first = ROOT per your spec
                if email==ROOT_EMAIL:
                    is_root=1
                db.execute("INSERT INTO users (email,password,is_root) VALUES (?,?,?)",(email,pwd,is_root))
                db.commit()
                return redirect("/login")
            except sqlite3.IntegrityError:
                msg="Email exists"
    return render_template("create.html", msg=msg)

@app.route("/login", methods=["GET","POST"])
def login():
    msg=""
    if request.method=="POST":
        email=request.form.get("email","").strip()
        pwd=request.form.get("password","").strip()
        db=get_db()
        cur=db.execute("SELECT * FROM users WHERE email=? AND password=?",(email,pwd))
        u=cur.fetchone()
        if u:
            session["user"]=u["email"]
            return redirect("/dashboard")
        else:
            msg="Invalid login"
    return render_template("login.html", msg=msg)

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return f"<h2>Welcome {session['user']}</h2><p><a href='/logout'>Logout</a></p><p>Fly primary: https://projecttrack.fly.dev</p>"

@app.route("/forgot")
def forgot():
    return "<h3>Reset - contact ROOT HCE@Projects2026</h3><a href='/login'>Back</a>"

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__=="__main__":
    app.run(host="0.0.0.0", port=8080)