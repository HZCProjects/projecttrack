
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "projecttrack-secret-2026")
DATA_DIR = os.getenv("DATA_DIR", "/data")
os.makedirs(DATA_DIR, exist_ok=True)

# Simple in-memory + sqlite fallback - first user = ROOT
users = {}

# ROOT creds
ROOT_EMAIL = "HCE@Projects2026"
ROOT_PASS = "HZC@2026"

def init_root():
    if ROOT_EMAIL not in users:
        users[ROOT_EMAIL] = {
            "email": ROOT_EMAIL,
            "password": generate_password_hash(ROOT_PASS),
            "role": "ROOT",
            "name": "Hennie",
            "surname": "ROOT"
        }

init_root()

@app.route("/")
def home():
    return redirect(url_for("login_page"))

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/register")
@app.route("/create")
@app.route("/signup")
def register_page():
    return render_template("create.html")

@app.route("/dashboard")
def dashboard():
    user = session.get("user")
    if not user:
        return redirect("/login")
    return render_template("index.html", user=user)

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    email = data.get("email") or data.get("username") or ""
    pwd = data.get("password") or ""
    u = users.get(email)
    if not u or not check_password_hash(u["password"], pwd):
        return jsonify({"error": "Invalid credentials"}), 401
    session["user"] = {"email": u["email"], "role": u["role"]}
    return jsonify({"ok": True, "role": u["role"]})

@app.route("/api/auth/register", methods=["POST"])
def api_register():
    data = request.get_json() or {}
    name = data.get("name","").strip()
    surname = data.get("surname","").strip()
    email = data.get("email") or data.get("username") or ""
    pwd = data.get("password") or ""
    repeat = data.get("repeat") or data.get("confirm") or ""
    if not all([name, surname, email, pwd]):
        return jsonify({"error": "All fields required"}), 400
    if len(email) < 5 or len(pwd) < 6:
        return jsonify({"error": "Email >5 chars, Password >6"}), 400
    if repeat and pwd != repeat:
        return jsonify({"error": "Passwords don't match"}), 400
    if email in users:
        return jsonify({"error": "User exists"}), 400
    role = "USER"
    if not users:
        role = "ROOT"
    else:
        # second user check - if only ROOT exists, next is still USER
        if len(users)==1 and ROOT_EMAIL in users:
            role = "USER"
    users[email] = {
        "email": email,
        "password": generate_password_hash(pwd),
        "role": role,
        "name": name,
        "surname": surname
    }
    return jsonify({"ok": True, "role": role, "msg": "Account created!"})

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
