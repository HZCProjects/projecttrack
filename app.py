import os, secrets, traceback
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='static', template_folder='templates')

# Use simple file path in current dir, not instance_path - avoids permission crash on Railway
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'projecttrack.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_PATH
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Lazy import SQLAlchemy to catch errors
try:
    from flask_sqlalchemy import SQLAlchemy
    from werkzeug.security import generate_password_hash, check_password_hash
    db = SQLAlchemy(app)
    
    class User(db.Model):
        __tablename__='users'
        id=db.Column(db.Integer, primary_key=True)
        name=db.Column(db.String(120), nullable=False)
        email=db.Column(db.String(120), unique=True, nullable=False)
        password_hash=db.Column(db.String(255), nullable=False)
        role=db.Column(db.String(20), default='viewer')
        is_active=db.Column(db.Boolean, default=True)
        created_at=db.Column(db.DateTime, default=datetime.utcnow)
        last_login=db.Column(db.DateTime, nullable=True)
        token=db.Column(db.String(255), nullable=True)
        token_expiry=db.Column(db.DateTime, nullable=True)

    def init_db():
        try:
            db.create_all()
            defaults=[("ROOT","root@hzcprojects.com","root123","ROOT"),("Admin","admin@hzcprojects.com","admin123","admin"),("Viewer","viewer@hzcprojects.com","viewer123","viewer")]
            for name,email,pwd,role in defaults:
                if not User.query.filter_by(email=email).first():
                    u=User(name=name,email=email,password_hash=generate_password_hash(pwd),role=role)
                    db.session.add(u)
            db.session.commit()
            print(f"DB OK at {DB_PATH} - users {User.query.count()}", flush=True)
        except Exception as e:
            print(f"DB init failed: {e}", flush=True)
            traceback.print_exc()

    # Init inside try so import never crashes
    try:
        with app.app_context():
            init_db()
    except Exception as e:
        print(f"App context init failed: {e}", flush=True)

except Exception as e:
    print(f"Critical import error: {e}", flush=True)
    traceback.print_exc()
    # Fallback - create minimal app without DB to avoid CRASHED
    db = None
    User = None
    def generate_password_hash(p): return p
    def check_password_hash(a,b): return False

def get_user_by_token(t):
    if not t or db is None: return None
    try:
        u=User.query.filter_by(token=t).first()
        if not u: return None
        if u.token_expiry and u.token_expiry < datetime.utcnow(): return None
        return u
    except:
        return None

@app.route('/')
def root(): return send_from_directory('templates','login.html')
@app.route('/index.html')
def idx(): return send_from_directory('templates','index.html')
@app.route('/login.html')
def log(): return send_from_directory('templates','login.html')
@app.route('/static/<path:path>')
def sf(path): return send_from_directory('static', path)
@app.route('/projecttrack.css')
def css_file(): return send_from_directory('static','projecttrack.css')
@app.route('/health')
def health():
    try: c=User.query.count() if db else 0
    except: c=0
    return jsonify({"status":"ok","step":"STEP2_CRASH_FIX","db":"sqlite","users":c, "db_path": DB_PATH})

@app.route('/api/auth/register', methods=['POST'])
def register():
    if db is None: return jsonify({"error":"DB not ready"}),500
    d=request.get_json() or {}
    name=d.get('name','').strip(); email=d.get('email','').strip().lower(); pwd=d.get('password',''); role=d.get('role','viewer')
    if not name or not email or not pwd: return jsonify({"error":"Required"}),400
    if User.query.filter_by(email=email).first(): return jsonify({"error":"Exists"}),400
    u=User(name=name,email=email,password_hash=generate_password_hash(pwd),role=role)
    db.session.add(u); db.session.commit()
    return jsonify({"message":"Created","user":{"id":u.id}}),201

@app.route('/api/auth/login', methods=['POST'])
def login():
    if db is None: return jsonify({"error":"DB not ready"}),500
    d=request.get_json() or {}
    email=d.get('email','').strip().lower(); pwd=d.get('password','')
    u=User.query.filter_by(email=email).first()
    if not u or not check_password_hash(u.password_hash,pwd): return jsonify({"error":"Invalid"}),401
    token=secrets.token_urlsafe(32)
    u.token=token; u.token_expiry=datetime.utcnow()+timedelta(days=7); u.last_login=datetime.utcnow()
    db.session.commit()
    return jsonify({"token":token,"user":{"id":u.id,"name":u.name,"email":u.email,"role":u.role}})

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    if db is None: return jsonify({"message":"ok"})
    t=request.headers.get('Authorization','').replace('Bearer ','').strip()
    u=User.query.filter_by(token=t).first()
    if u: u.token=None; u.token_expiry=None; db.session.commit()
    return jsonify({"message":"ok"})

@app.route('/api/users', methods=['GET'])
def list_users():
    if db is None: return jsonify([])
    users=User.query.order_by(User.id).all()
    return jsonify([{"id":x.id,"name":x.name,"email":x.email,"role":x.role} for x in users])

@app.route('/api/users/<int:uid>', methods=['DELETE'])
def del_user(uid):
    if db is None: return jsonify({"error":"No DB"}),500
    t=request.headers.get('Authorization','').replace('Bearer ','').strip()
    caller=get_user_by_token(t)
    if not caller: return jsonify({"error":"Unauthorized"}),401
    if caller.role not in ['ROOT','admin']: return jsonify({"error":"Forbidden"}),403
    u=db.session.get(User, uid)
    if not u: return jsonify({"error":"Not found"}),404
    db.session.delete(u); db.session.commit()
    return jsonify({"message":"Deleted"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT',8080))
    print(f"Starting on 0.0.0.0:{port}", flush=True)
    app.run(host='0.0.0.0', port=port)