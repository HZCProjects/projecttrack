import os, secrets, traceback
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='static', template_folder='templates')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'projecttrack.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_PATH
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
    def init_db():
        try:
            db.create_all()
            defaults=[("ROOT","Admin","root@hzcprojects.com","root123","ROOT"),("Admin","User","admin@hzcprojects.com","admin123","admin"),("Viewer","User","viewer@hzcprojects.com","viewer123","viewer")]
            for name,surname,email,pwd,role in defaults:
                if not User.query.filter_by(email=email).first():
                    u=User(name=name,surname=surname,email=email,password_hash=generate_password_hash(pwd),role=role)
                    db.session.add(u)
            db.session.commit()
            print(f"DB OK users {User.query.count()}", flush=True)
        except Exception as e:
            print(f"DB init failed {e}", flush=True)
            traceback.print_exc()
    try:
        with app.app_context():
            init_db()
    except Exception as e:
        print(f"init failed {e}", flush=True)
except Exception as e:
    print(f"Import error {e}", flush=True)
    traceback.print_exc()
    db=None; User=None
    def generate_password_hash(p): return p
    def check_password_hash(a,b): return False

def get_user_by_token(t):
    if not t or db is None: return None
    try:
        u=User.query.filter_by(token=t).first()
        if not u: return None
        if u.token_expiry and u.token_expiry < datetime.utcnow(): return None
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
    try: c=User.query.count() if db else 0
    except: c=0
    return jsonify({"status":"ok","db":"sqlite","users":c})

@app.route('/api/auth/register', methods=['POST'])
def register():
    if db is None: return jsonify({"error":"DB not ready"}),500
    d=request.get_json() or {}
    name=d.get('name','').strip(); surname=d.get('surname','').strip(); email=d.get('email','').strip().lower(); pwd=d.get('password',''); role=d.get('role','viewer')
    if len(name)<1 or len(email)<6 or len(pwd)<7: return jsonify({"error":"Check fields length"}),400
    if User.query.filter_by(email=email).first(): return jsonify({"error":"Email exists"}),400
    u=User(name=name,surname=surname,email=email,password_hash=generate_password_hash(pwd),role=role)
    db.session.add(u); db.session.commit()
    return jsonify({"message":"Created","user":{"id":u.id}}),201

@app.route('/api/auth/login', methods=['POST'])
def login():
    if db is None: return jsonify({"error":"DB not ready"}),500
    d=request.get_json() or {}
    email=d.get('email','').strip().lower(); pwd=d.get('password','')
    u=User.query.filter_by(email=email).first()
    if not u or not check_password_hash(u.password_hash,pwd): return jsonify({"error":"Invalid credentials"}),401
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
    return jsonify([{"id":x.id,"name":x.name,"surname":x.surname or "", "email":x.email,"role":x.role} for x in users])

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
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',8080)))