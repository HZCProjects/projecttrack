import os, secrets, traceback
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='static', template_folder='templates')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

db_url = os.environ.get('DATABASE_URL','').strip()
if db_url:
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://','postgresql+psycopg2://',1)
    elif db_url.startswith('postgresql://') and '+psycopg2' not in db_url:
        db_url = db_url.replace('postgresql://','postgresql+psycopg2://',1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    DB_TYPE = 'POSTGRES'
else:
    DB_PATH = os.path.join(BASE_DIR, 'projecttrack.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
    DB_TYPE = 'SQLITE'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__='users'
    id=db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String(120), nullable=False)
    surname=db.Column(db.String(120), nullable=True)
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
        cnt = User.query.count()
        print(f"DB {DB_TYPE} init OK users={cnt}", flush=True)
        return cnt
    except Exception as e:
        msg=str(e).lower()
        print(f"init_db error {e} - will rebuild table", flush=True)
        traceback.print_exc()
        try: db.session.rollback()
        except: pass
        # If column missing or table mismatch, drop and recreate
        if 'undefinedcolumn' in msg or 'does not exist' in msg or 'no such column' in msg or 'name' in msg:
            try:
                print("Dropping and recreating users table...", flush=True)
                db.drop_all()
                db.create_all()
                cnt = User.query.count()
                print(f"Rebuilt OK users={cnt}", flush=True)
                return cnt
            except Exception as e2:
                print(f"rebuild failed {e2}", flush=True)
                traceback.print_exc()
                try: db.session.rollback()
                except: pass
        return 0

with app.app_context():
    init_db()

def get_user_by_token(t):
    if not t: return None
    try:
        u=User.query.filter_by(token=t).first()
        if not u or (u.token_expiry and u.token_expiry < datetime.utcnow()): return None
        return u
    except: return None

@app.route('/')
def root(): return send_from_directory('templates','login.html')
@app.route('/index.html')
def idx(): return send_from_directory('templates','index.html')
@app.route('/login.html')
def log(): return send_from_directory('templates','login.html')
@app.route('/static/<path:p>')
def sf(p): return send_from_directory('static', p)

@app.route('/health')
def health():
    try:
        c = User.query.count()
    except Exception as e:
        print(f"health error {e} - init", flush=True)
        with app.app_context():
            c = init_db()
    return jsonify({"status":"ok","db":DB_TYPE.lower(),"db_type":DB_TYPE,"users":c,"env_has_db":bool(os.environ.get('DATABASE_URL'))})

@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        try:
            # Try count to detect missing column
            User.query.count()
        except Exception as ce:
            print(f"Detected schema issue in register: {ce} - rebuilding", flush=True)
            try: db.session.rollback()
            except: pass
            db.drop_all()
            db.create_all()

        d=request.get_json() or {}
        name=d.get('name','').strip()
        surname=d.get('surname','').strip()
        email=d.get('email','').strip().lower()
        pwd=d.get('password','')
        print(f"REGISTER name={name} surname={surname} email={email} pwdLen={len(pwd)}", flush=True)
        if len(name)<1: return jsonify({"error":"Name required"}),400
        if len(email)<6: return jsonify({"error":"Email must be >5 chars"}),400
        if len(pwd)<7: return jsonify({"error":"Password must be >6 chars"}),400
        if User.query.filter_by(email=email).first():
            return jsonify({"error":"Email exists - try Log In"}),400
        
        is_first = User.query.count() == 0
        role = 'ROOT' if is_first else d.get('role','viewer')
        
        u=User(name=name,surname=surname,email=email,password_hash=generate_password_hash(pwd),role=role)
        db.session.add(u)
        db.session.commit()
        print(f"Created {email} as {role} id={u.id}", flush=True)
        return jsonify({"message":"Created as "+role,"user":{"id":u.id,"role":role}}),201
    except Exception as e:
        print(f"REGISTER FAILED: {e}", flush=True)
        traceback.print_exc()
        try: db.session.rollback()
        except: pass
        return jsonify({"error":f"Server error: {str(e)[:400]}"}),500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        d=request.get_json() or {}
        email=d.get('email','').strip().lower(); pwd=d.get('password','')
        print(f"LOGIN attempt {email}", flush=True)
        u=User.query.filter_by(email=email).first()
        if not u or not check_password_hash(u.password_hash,pwd):
            return jsonify({"error":"Invalid credentials"}),401
        token=secrets.token_urlsafe(32)
        u.token=token; u.token_expiry=datetime.utcnow()+timedelta(days=7); u.last_login=datetime.utcnow()
        db.session.commit()
        return jsonify({"token":token,"user":{"id":u.id,"name":u.name,"email":u.email,"role":u.role}})
    except Exception as e:
        print(f"LOGIN FAILED {e}", flush=True)
        traceback.print_exc()
        return jsonify({"error":f"Login error: {str(e)[:400]}"}),500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    t=request.headers.get('Authorization','').replace('Bearer ','').strip()
    try:
        u=User.query.filter_by(token=t).first()
        if u: u.token=None; u.token_expiry=None; db.session.commit()
    except: pass
    return jsonify({"message":"ok"})

@app.route('/api/users', methods=['GET'])
def list_users():
    try:
        users=User.query.order_by(User.id).all()
        return jsonify([{"id":x.id,"name":x.name,"surname":x.surname or "", "email":x.email,"role":x.role} for x in users])
    except Exception as e:
        print(f"list_users fail {e}", flush=True)
        return jsonify([])

@app.route('/api/users/<int:uid>', methods=['DELETE'])
def del_user(uid):
    t=request.headers.get('Authorization','').replace('Bearer ','').strip()
    caller=get_user_by_token(t)
    if not caller: return jsonify({"error":"Login as ROOT first"}),401
    if caller.role not in ['ROOT','admin']: return jsonify({"error":"Forbidden - need ROOT"}),403
    u=db.session.get(User, uid)
    if not u: return jsonify({"error":"Not found"}),404
    if u.id==caller.id: return jsonify({"error":"Cannot delete yourself"}),400
    db.session.delete(u); db.session.commit()
    return jsonify({"message":"Deleted"})

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',8080)))