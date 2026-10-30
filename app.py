import os
import secrets
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='.', static_url_path='')

# --- DB config: Postgres on Railway, SQLite fallback ---
database_url = os.environ.get('DATABASE_URL', '').strip()
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///projecttrack.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'hzc-projects-secret')

db = SQLAlchemy(app)

# --- Model ---
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='viewer')  # ROOT / admin / manager / viewer
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    token = db.Column(db.String(128), nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None
        }

def init_db():
    with app.app_context():
        db.create_all()
        # default users
        defaults = [
            ("ROOT User", "root@hzcprojects.com", "root123", "ROOT"),
            ("Admin User", "admin@hzcprojects.com", "admin123", "admin"),
            ("Viewer User", "viewer@hzcprojects.com", "viewer123", "viewer"),
        ]
        for name, email, pwd, role in defaults:
            if not User.query.filter_by(email=email).first():
                u = User(
                    name=name,
                    email=email,
                    password_hash=generate_password_hash(pwd),
                    role=role,
                    is_active=True
                )
                db.session.add(u)
        db.session.commit()

init_db()

# --- Helpers ---
def get_user_from_token(req):
    auth = req.headers.get('Authorization','')
    token = None
    if auth.startswith('Bearer '):
        token = auth.split(' ',1)[1].strip()
    else:
        token = req.headers.get('X-Auth-Token') or req.args.get('token')
        if not token:
            data = {}
            try:
                data = req.get_json(silent=True) or {}
            except:
                data = {}
            token = data.get('token')
    if not token:
        return None
    user = User.query.filter_by(token=token).first()
    if not user or not user.token_expiry or user.token_expiry < datetime.utcnow():
        return None
    return user

# --- Routes: pages ---
@app.route('/')
def root():
    return send_from_directory('.', 'login.html')

@app.route('/login.html')
def login_page():
    return send_from_directory('.', 'login.html')

@app.route('/index.html')
def index_page():
    return send_from_directory('.', 'index.html')

@app.route('/projecttrack.css')
def css():
    return send_from_directory('.', 'projecttrack.css')

@app.route('/health')
def health():
    db_type = 'postgres' if database_url else 'sqlite'
    count = 0
    try:
        count = User.query.count()
    except:
        pass
    return jsonify({"status":"ok", "db": db_type, "users": count, "database_url_present": bool(database_url)})

# --- API: Auth ---
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    name = data.get('name','').strip()
    email = data.get('email','').strip().lower()
    password = data.get('password','')
    role = data.get('role','viewer').strip().lower()
    if role not in ['root','admin','manager','viewer']:
        role = 'viewer'
    # keep ROOT uppercase internally for display but store lower except ROOT
    if role == 'root':
        role = 'ROOT'
    if not name or not email or not password:
        return jsonify({"error":"name, email, password required"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error":"Email already exists"}), 409
    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
        role=role,
        is_active=True
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"message":"User created", "user": user.to_dict()}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email','').strip().lower()
    password = data.get('password','')
    if not email or not password:
        return jsonify({"error":"email and password required"}), 400
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error":"Invalid credentials"}), 401
    if not user.is_active:
        return jsonify({"error":"Account disabled"}), 403
    token = secrets.token_urlsafe(32)
    user.token = token
    user.token_expiry = datetime.utcnow() + timedelta(days=7)
    user.last_login = datetime.utcnow()
    db.session.commit()
    return jsonify({"message":"Login ok", "token": token, "user": user.to_dict()})

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    user = get_user_from_token(request)
    if user:
        user.token = None
        user.token_expiry = None
        db.session.commit()
    return jsonify({"message":"Logged out"})

@app.route('/api/users', methods=['GET'])
def list_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([u.to_dict() for u in users])

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    requester = get_user_from_token(request)
    if not requester:
        # allow if no token but check role from header? For Users DB tab to work without strict auth, allow but log
        # Strict version: require admin/ROOT token
        auth_header = request.headers.get('Authorization','')
        if not auth_header:
            return jsonify({"error":"Auth token required"}), 401
        return jsonify({"error":"Invalid or expired token"}), 401
    if requester.role.lower() not in ['root','admin'] and requester.role != 'ROOT':
        return jsonify({"error":"Admin or ROOT only"}), 403
    if requester.id == user_id:
        return jsonify({"error":"Cannot delete self"}), 400
    target = User.query.get(user_id)
    if not target:
        return jsonify({"error":"User not found"}), 404
    if target.role == 'ROOT' and requester.role != 'ROOT':
        return jsonify({"error":"Only ROOT can delete ROOT user"}), 403
    db.session.delete(target)
    db.session.commit()
    return jsonify({"message":"User deleted"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
