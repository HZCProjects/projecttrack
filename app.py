import os
from flask import Flask, send_from_directory, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets

app = Flask(__name__)

# Database config - Railway PostgreSQL or SQLite fallback
# Railway provides DATABASE_URL, else use sqlite
database_url = os.environ.get('DATABASE_URL', '')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///projecttrack.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'hzc-projects-secret-2026-clean')

db = SQLAlchemy(app)

# USER MODEL - Database First
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='viewer')  # admin, manager, viewer, ROOT
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    token = db.Column(db.String(128), nullable=True, index=True)
    token_expiry = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_token(self):
        self.token = secrets.token_urlsafe(32)
        self.token_expiry = datetime.utcnow() + timedelta(days=7)
        return self.token

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

# Create tables
with app.app_context():
    db.create_all()
    # Create default ROOT and Admin if not exists
    if not User.query.filter_by(email='root@hzcprojects.com').first():
        root = User(name='ROOT Super Admin', email='root@hzcprojects.com', role='ROOT')
        root.set_password('root123')
        db.session.add(root)
    if not User.query.filter_by(email='admin@hzcprojects.com').first():
        admin = User(name='Admin', email='admin@hzcprojects.com', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
    if not User.query.filter_by(email='viewer@hzcprojects.com').first():
        viewer = User(name='Viewer', email='viewer@hzcprojects.com', role='viewer')
        viewer.set_password('viewer123')
        db.session.add(viewer)
    db.session.commit()

# ROUTES - Static files
@app.route('/')
def root():
    return send_from_directory('.', 'login.html')

@app.route('/login')
@app.route('/login.html')
def login_page():
    return send_from_directory('.', 'login.html')

@app.route('/index.html')
@app.route('/dashboard')
def dashboard():
    return send_from_directory('.', 'index.html')

@app.route('/projecttrack.css')
def css():
    return send_from_directory('.', 'projecttrack.css')

# API - AUTH
@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.get_json() or {}
    name = data.get('name', '').strip() or 'User'
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    role = data.get('role', 'viewer').strip().lower()

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password min 6 chars"}), 400
    if role not in ['admin', 'manager', 'viewer', 'root']:
        role = 'viewer'
    if role == 'root':
        role = 'ROOT'  # Allow ROOT but will be checked

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "User already exists with this email"}), 400

    user = User(name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "User created", "user": user.to_dict()}), 201

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401
    if not user.is_active:
        return jsonify({"error": "Account disabled"}), 403

    token = user.generate_token()
    user.last_login = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "message": "Login successful",
        "token": token,
        "user": user.to_dict()
    })

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '').strip()
    if token:
        user = User.query.filter_by(token=token).first()
        if user:
            user.token = None
            user.token_expiry = None
            db.session.commit()
    return jsonify({"message": "Logged out"})

@app.route('/api/auth/me', methods=['GET'])
def api_me():
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '').strip()
    if not token:
        return jsonify({"error": "No token"}), 401
    user = User.query.filter_by(token=token).first()
    if not user or (user.token_expiry and user.token_expiry < datetime.utcnow()):
        return jsonify({"error": "Invalid or expired token"}), 401
    return jsonify({"user": user.to_dict()})

@app.route('/api/users', methods=['GET'])
def api_users():
    # List users - requires token, ROOT or admin can see all
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '').strip()
    if token:
        me = User.query.filter_by(token=token).first()
        if not me:
            return jsonify({"error": "Unauthorized"}), 401
    else:
        # Allow for now in Step 1c for demo, will lock in Step 2
        pass
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({"users": [u.to_dict() for u in users], "count": len(users)})

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def api_delete_user(user_id):
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '').strip()
    me = User.query.filter_by(token=token).first() if token else None
    if not me or me.role not in ['admin', 'ROOT']:
        return jsonify({"error": "Only Admin or ROOT can delete"}), 403
    if me.id == user_id:
        return jsonify({"error": "Cannot delete yourself"}), 400
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted"})

@app.route('/health')
def health():
    try:
        user_count = User.query.count()
    except:
        user_count = -1
    return jsonify({
        "status": "ok",
        "step": "STEP 1c - User Account Database First",
        "database": app.config['SQLALCHEMY_DATABASE_URI'].split('://')[0],
        "users": user_count,
        "login": "/login",
        "dashboard": "/index.html",
        "api": ["/api/auth/register", "/api/auth/login", "/api/users"],
        "mojis": "none",
        "version": "step1c_user_db_first"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
