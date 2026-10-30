import os, secrets, traceback
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='static', template_folder='templates')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_TYPE = 'SQLITE'
DB_ERROR = None

# Try Postgres first if DATABASE_URL exists, else SQLite
db_url = os.environ.get('DATABASE_URL','').strip()
if db_url:
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://','postgresql://',1)
    # Test if we can use it, but we will try to connect later
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    DB_TYPE = 'POSTGRES'
    print(f"Trying POSTGRES env...", flush=True)
else:
    DB_PATH = os.path.join(BASE_DIR, 'projecttrack.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_PATH
    DB_TYPE = 'SQLITE'
    print(f"Using SQLITE {DB_PATH}", flush=True)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import SQLAlchemy
try:
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

    def ensure_defaults():
        global DB_TYPE, DB_ERROR
        try:
            db.create_all()
            defaults=[("ROOT","Admin","root@hzcprojects.com","root123","ROOT"),("Admin","User","admin@hzcprojects.com","admin123","admin"),("Viewer","User","viewer@hzcprojects.com","viewer123","viewer")]
            added=0
            for n,s,e,p,r in defaults:
                if not User.query.filter_by(email=e).first():
                    db.session.add(User(name=n,surname=s,email=e,password_hash=generate_password_hash(p),role=r))
                    added+=1
            if added:
                db.session.commit()
            cnt = User.query.count()
            print(f"DB {DB_TYPE} OK users={cnt}", flush=True)
            return cnt
        except Exception as e:
            DB_ERROR = str(e)[:500]
            print(f"DB {DB_TYPE} FAILED: {e}", flush=True)
            traceback.print_exc()
            # FALLBACK TO SQLITE if postgres fails
            if DB_TYPE == 'POSTGRES':
                print("Falling back to SQLITE...", flush=True)
                try:
                    # Switch to SQLite
                    DB_PATH = os.path.join(BASE_DIR, 'projecttrack.db')
                    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_PATH
                    # Need to re-init? We'll create new engine by removing old and creating tables with sqlite
                    # For fallback, we create tables using sqlite file directly
                    # Since db already bound, we can try again with sqlite uri via new app context trick
                    # Simplest: use sqlite connection for ensure
                    from sqlalchemy import create_engine
                    from sqlalchemy.orm import scoped_session, sessionmaker
                    # Fallback manual: just create sqlite tables via same db object by disposing
                    db.engine.dispose()
                    # Update to sqlite uri and try again
                    db.session.remove()
                    # Reconfigure - need new engine, easiest is to create all with sqlite uri
                    # We'll just switch global and try again in same try block
                    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_PATH
                    # Recreate engine
                    db.create_all()
                    added=0
                    for n,s,e,p,r in defaults:
                        if not User.query.filter_by(email=e).first():
                            db.session.add(User(name=n,surname=s,email=e,password_hash=generate_password_hash(p),role=r))
                            added+=1
                    if added:
                        db.session.commit()
                    DB_TYPE = 'SQLITE (fallback from POSTGRES)'
                    cnt = User.query.count()
                    print(f"Fallback SQLITE OK users={cnt}", flush=True)
                    return cnt
                except Exception as e2:
                    print(f"Fallback also failed: {e2}", flush=True)
                    traceback.print_exc()
                    return 0
            return 0

    with app.app_context():
        ensure_defaults()

except Exception as e:
    print(f"CRITICAL IMPORT FAIL: {e}", flush=True)
    traceback.print_exc()
    DB_TYPE = f'ERROR: {e}'[:100]
    DB_ERROR = str(e)
    db = None
    User = None
    def ensure_defaults(): return 0
    def generate_password_hash(p): return p
    def check_password_hash(a,b): return False

def get_user_by_token(t):
    if not t or db is None: return None
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
        if db is not None:
            with app.app_context():
                ensure_defaults()
        c = User.query.count() if db and User else 0
    except Exception as e:
        c = 0
        DB_ERROR_LOCAL = str(e)
    return jsonify({"status":"ok","db":DB_TYPE.lower(),"db_type":DB_TYPE,"users":c,"env_has_db":bool(os.environ.get('DATABASE_URL')),"error":str(DB_ERROR)[:500] if DB_ERROR else None})

@app.route('/api/auth/register', methods=['POST'])
def register():
    if db is None: return jsonify({"error":"DB not ready"}),500
    d=request.get_json() or {}
    name=d.get('name','').strip(); surname=d.get('surname','').strip(); email=d.get('email','').strip().lower(); pwd=d.get('password','')
    if len(name)<1: return jsonify({"error":"Name required"}),400
    if len(email)<6: return jsonify({"error":"Email must be >5 chars"}),400
    if len(pwd)<7: return jsonify({"error":"Password must be >6 chars"}),400
    if User.query.filter_by(email=email).first(): return jsonify({"error":"Email exists"}),400
    u=User(name=name,surname=surname,email=email,password_hash=generate_password_hash(pwd),role=d.get('role','viewer'))
    db.session.add(u); db.session.commit()
    return jsonify({"message":"Created","user":{"id":u.id}}),201

@app.route('/api/auth/login', methods=['POST'])
def login():
    if db is None: return jsonify({"error":"DB not ready"}),500
    d=request.get_json() or {}
    email=d.get('email','').strip().lower(); pwd=d.get('password','')
    u=User.query.filter_by(email=email).first()
    if not u or not check_password_hash(u.password_hash,pwd): return jsonify({"error":"Invalid credentials"}),401
    token=secrets.token_urlsafe(32); u.token=token; u.token_expiry=datetime.utcnow()+timedelta(days=7); u.last_login=datetime.utcnow(); db.session.commit()
    return jsonify({"token":token,"user":{"id":u.id,"name":u.name,"email":u.email,"role":u.role}})

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    t=request.headers.get('Authorization','').replace('Bearer ','').strip()
    try:
        if db: 
            u=User.query.filter_by(token=t).first()
            if u: u.token=None; u.token_expiry=None; db.session.commit()
    except: pass
    return jsonify({"message":"ok"})

@app.route('/api/users', methods=['GET'])
def list_users():
    if db is None: return jsonify([])
    try:
        users=User.query.order_by(User.id).all()
        return jsonify([{"id":x.id,"name":x.name,"surname":x.surname or "", "email":x.email,"role":x.role} for x in users])
    except: return jsonify([])

@app.route('/api/users/<int:uid>', methods=['DELETE'])
def del_user(uid):
    if db is None: return jsonify({"error":"No DB"}),500
    t=request.headers.get('Authorization','').replace('Bearer ','').strip()
    caller=get_user_by_token(t)
    if not caller: return jsonify({"error":"Login as ROOT/admin first"}),401
    if caller.role not in ['ROOT','admin']: return jsonify({"error":"Forbidden"}),403
    u=db.session.get(User, uid)
    if not u: return jsonify({"error":"Not found"}),404
    db.session.delete(u); db.session.commit()
    return jsonify({"message":"Deleted"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',8080)))