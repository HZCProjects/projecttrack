
import os
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

app = Flask(__name__, static_folder='static', template_folder='templates')

# DUAL DB: Postgres (psycopg3 for Python 3.15) + SQLite fallback
db_url = os.environ.get('DATABASE_URL','').strip()
if db_url:
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://','postgresql://',1)
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://','postgresql+psycopg://',1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///projecttrack.db'



app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY','projecttrack-secret-2026')

db = SQLAlchemy(app)

class User(db.Model):
    __tablename__='users'
    id=db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String(120), nullable=False)
    surname=db.Column(db.String(120))
    email=db.Column(db.String(200), unique=True, nullable=False)
    password_hash=db.Column(db.String(300), nullable=False)
    role=db.Column(db.String(20), default='USER')
    is_active=db.Column(db.Boolean, default=True)
    created_at=db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_login=db.Column(db.DateTime)
    token=db.Column(db.String(500))
    token_expiry=db.Column(db.DateTime)

with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        # Rebuild if old schema
        try:
            db.drop_all()
            db.create_all()
        except:
            app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///projecttrack.db'
            db.create_all()

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
@app.route('/create')
@app.route('/signup')
def register_page():
    return render_template('create.html')

@app.route('/dashboard')
@app.route('/index.html')
def dashboard():
    return render_template('index.html')

@app.route('/api/auth/register', methods=['POST'])
def register():
    data=request.get_json() or {}
    name=data.get('name','').strip()
    surname=data.get('surname','').strip()
    email=(data.get('email') or '').strip().lower()
    pwd=data.get('password','')
    repeat=data.get('repeatPassword','') or data.get('repeat','')
    if not all([name,surname,email,pwd,repeat]):
        return jsonify({'error':'All fields required'}),400
    if len(email)<6:
        return jsonify({'error':'Login Name must be more than 5 Characters'}),400
    if len(pwd)<7:
        return jsonify({'error':'Password must be more than 6 Characters'}),400
    if pwd!=repeat:
        return jsonify({'error':'Passwords do not match'}),400
    if User.query.filter_by(email=email).first():
        return jsonify({'error':'User already exists'}),400
    is_first = User.query.count()==0
    role='ROOT' if is_first else 'USER'
    u=User(name=name,surname=surname,email=email,password_hash=generate_password_hash(pwd),role=role)
    db.session.add(u)
    db.session.commit()
    return jsonify({'ok':True,'role':role})

@app.route('/api/auth/login', methods=['POST'])
def login():
    data=request.get_json() or {}
    email=(data.get('email') or data.get('login') or '').strip().lower()
    pwd=data.get('password','')
    if not email or not pwd:
        return jsonify({'error':'Email and password required'}),400
    u=User.query.filter_by(email=email).first()
    if not u or not check_password_hash(u.password_hash,pwd):
        return jsonify({'error':'Invalid credentials'}),401
    if not u.is_active:
        return jsonify({'error':'User inactive'}),403
    u.last_login=datetime.datetime.utcnow()
    db.session.commit()
    return jsonify({'ok':True,'email':u.email,'role':u.role,'name':u.name})

@app.route('/api/health')
def health():
    try:
        c=User.query.count()
        return jsonify({'status':'ok','users':c})
    except Exception as e:
        return jsonify({'status':'error','error':str(e)}),500

if __name__=='__main__':
    port=int(os.environ.get('PORT',5000))
    app.run(host='0.0.0.0',port=port)
