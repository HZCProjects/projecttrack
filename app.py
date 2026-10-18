
import os, json, sqlite3, secrets
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

try:
    import psycopg2
    HAS_PG = True
except:
    HAS_PG = False

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)
DATABASE_URL = os.environ.get('DATABASE_URL')
USE_PG = bool(DATABASE_URL and HAS_PG)

def get_conn():
    if USE_PG:
        return psycopg2.connect(DATABASE_URL)
    else:
        conn = sqlite3.connect('projecttrack.db')
        conn.row_factory = sqlite3.Row
        return conn

def rows_to_dicts(cur, rows):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in rows]

def init_db():
    conn = get_conn(); cur = conn.cursor()
    if USE_PG:
        cur.execute("""CREATE TABLE IF NOT EXISTS qc_sheets (
            id SERIAL PRIMARY KEY, project_name TEXT, location TEXT,
            structure_number TEXT DEFAULT '', collector_number TEXT DEFAULT '',
            section_number TEXT DEFAULT '', chainage_extra TEXT DEFAULT '',
            date TEXT, inspector TEXT, status TEXT DEFAULT 'draft',
            sheet_type TEXT DEFAULT 'trench', checklist_data TEXT, created_at TEXT, updated_at TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS gantt_tasks (
            id SERIAL PRIMARY KEY, name TEXT, start_date TEXT, end_date TEXT,
            progress INTEGER DEFAULT 0, assignee TEXT, dependencies TEXT, color TEXT, created_at TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, role TEXT DEFAULT 'viewer',
            display_name TEXT DEFAULT '', created_at TEXT, last_login TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY, user_id INTEGER, username TEXT, role TEXT,
            display_name TEXT, created_at TEXT)""")
    else:
        cur.execute("""CREATE TABLE IF NOT EXISTS qc_sheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT, project_name TEXT, location TEXT,
            structure_number TEXT DEFAULT '', collector_number TEXT DEFAULT '',
            section_number TEXT DEFAULT '', chainage_extra TEXT DEFAULT '',
            date TEXT, inspector TEXT, status TEXT DEFAULT 'draft',
            sheet_type TEXT DEFAULT 'trench', checklist_data TEXT, created_at TEXT, updated_at TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS gantt_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, start_date TEXT, end_date TEXT,
            progress INTEGER DEFAULT 0, assignee TEXT, dependencies TEXT, color TEXT, created_at TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, role TEXT DEFAULT 'viewer',
            display_name TEXT DEFAULT '', created_at TEXT, last_login TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY, user_id INTEGER, username TEXT, role TEXT,
            display_name TEXT, created_at TEXT)""")
    try:
        if USE_PG:
            for col, coltype in [
                ('project_name', "TEXT DEFAULT ''"),
                ('location', "TEXT DEFAULT ''"),
                ('structure_number', "TEXT DEFAULT ''"),
                ('collector_number', "TEXT DEFAULT ''"),
                ('section_number', "TEXT DEFAULT ''"),
                ('chainage_extra', "TEXT DEFAULT ''"),
                ('date', "TEXT DEFAULT ''"),
                ('inspector', "TEXT DEFAULT ''"),
                ('status', "TEXT DEFAULT 'draft'"),
                ('sheet_type', "TEXT DEFAULT 'trench'"),
                ('checklist_data', "TEXT DEFAULT '{}'"),
                ('created_at', "TEXT DEFAULT ''"),
                ('updated_at', "TEXT DEFAULT ''"),
            ]:
                try:
                    cur.execute(f"ALTER TABLE qc_sheets ADD COLUMN IF NOT EXISTS {col} {coltype}")
                except Exception as e:
                    print(f"Migration add {col}: {e}")
            conn.commit()
        else:
            for col, coltype in [
                ('project_name', "TEXT DEFAULT ''"),
                ('location', "TEXT DEFAULT ''"),
                ('structure_number', "TEXT DEFAULT ''"),
                ('collector_number', "TEXT DEFAULT ''"),
                ('section_number', "TEXT DEFAULT ''"),
                ('chainage_extra', "TEXT DEFAULT ''"),
                ('date', "TEXT DEFAULT ''"),
                ('inspector', "TEXT DEFAULT ''"),
                ('status', "TEXT DEFAULT 'draft'"),
                ('sheet_type', "TEXT DEFAULT 'trench'"),
                ('checklist_data', "TEXT DEFAULT '{}'"),
                ('created_at', "TEXT DEFAULT ''"),
                ('updated_at', "TEXT DEFAULT ''"),
            ]:
                try:
                    cur.execute(f"ALTER TABLE qc_sheets ADD COLUMN {col} {coltype}")
                except:
                    pass
            conn.commit()
    except Exception as e:
        print(f"Migration error: {e}")
        try: conn.commit()
        except: pass
    conn.close()

def init_users():
    conn = get_conn(); cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM users')
    cnt = cur.fetchone()[0]
    if cnt == 0:
        now = datetime.utcnow().isoformat()
        defaults = [
            ('admin', generate_password_hash('HZC2026!'), 'admin', 'System Admin'),
            ('qc_lead', generate_password_hash('QC2026!'), 'qc_manager', 'QC Lead'),
            ('inspector', generate_password_hash('Inspect2026!'), 'inspector', 'Site Inspector'),
            ('viewer', generate_password_hash('Viewer123'), 'viewer', 'Guest Viewer'),
        ]
        for u,p,r,dname in defaults:
            if USE_PG:
                cur.execute('INSERT INTO users (username,password_hash,role,display_name,created_at) VALUES (%s,%s,%s,%s,%s)', (u,p,r,dname,now))
            else:
                cur.execute('INSERT INTO users (username,password_hash,role,display_name,created_at) VALUES (?,?,?,?,?)', (u,p,r,dname,now))
        conn.commit()
    conn.close()

init_db()
init_users()

def get_session(token):
    if not token: return None
    try:
        conn=get_conn(); cur=conn.cursor()
        if USE_PG:
            cur.execute('SELECT token, user_id, username, role, display_name FROM sessions WHERE token=%s',(token,))
        else:
            cur.execute('SELECT token, user_id, username, role, display_name FROM sessions WHERE token=?',(token,))
        row=cur.fetchone()
        if not row:
            conn.close()
            return None
        if USE_PG:
            result = {'token': row[0], 'user_id': row[1], 'username': row[2], 'role': row[3], 'display_name': row[4]}
        else:
            result = dict(row) if hasattr(row, 'keys') else {'token': row[0], 'user_id': row[1], 'username': row[2], 'role': row[3], 'display_name': row[4]}
        conn.close()
        return result
    except Exception as e:
        try: conn.close()
        except: pass
        print(f"get_session error: {e}")
        return None

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization','')
        token = auth.replace('Bearer ','') if auth.startswith('Bearer ') else ''
        if not token:
            token = request.cookies.get('session_token','')
        sess = get_session(token)
        if not sess:
            return jsonify({'error': 'Unauthorized'}), 401
        request.user = sess
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__
    return decorated

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if '..' in path: return 'Not found', 404
    try:
        return send_from_directory('.', path)
    except:
        return send_from_directory('.', 'index.html')

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username','').strip()
    password = data.get('password','')
    if not username or not password:
        return jsonify({'error': 'Missing credentials'}), 400
    conn=get_conn(); cur=conn.cursor()
    if USE_PG:
        cur.execute('SELECT id, username, password_hash, role, display_name FROM users WHERE username=%s',(username,))
    else:
        cur.execute('SELECT id, username, password_hash, role, display_name FROM users WHERE username=?',(username,))
    row=cur.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Invalid credentials'}), 401
    if USE_PG:
        uid, uname, phash, role, dname = row
    else:
        uid = row['id'] if hasattr(row, 'keys') else row[0]
        uname = row['username'] if hasattr(row, 'keys') else row[1]
        phash = row['password_hash'] if hasattr(row, 'keys') else row[2]
        role = row['role'] if hasattr(row, 'keys') else row[3]
        dname = row['display_name'] if hasattr(row, 'keys') else row[4]
    if not check_password_hash(phash, password):
        conn.close()
        return jsonify({'error': 'Invalid credentials'}), 401
    token = secrets.token_urlsafe(32)
    now = datetime.utcnow().isoformat()
    if USE_PG:
        cur.execute('INSERT INTO sessions (token, user_id, username, role, display_name, created_at) VALUES (%s,%s,%s,%s,%s,%s)', (token, uid, uname, role, dname, now))
        cur.execute('UPDATE users SET last_login=%s WHERE id=%s',(now, uid))
    else:
        cur.execute('INSERT INTO sessions (token, user_id, username, role, display_name, created_at) VALUES (?,?,?,?,?,?)', (token, uid, uname, role, dname, now))
        cur.execute('UPDATE users SET last_login=? WHERE id=?',(now, uid))
    conn.commit(); conn.close()
    return jsonify({'token': token, 'user': {'id': uid, 'username': uname, 'role': role, 'display_name': dname}})

@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    auth = request.headers.get('Authorization','')
    token = auth.replace('Bearer ','') if auth.startswith('Bearer ') else ''
    if token:
        conn=get_conn(); cur=conn.cursor()
        if USE_PG:
            cur.execute('DELETE FROM sessions WHERE token=%s',(token,))
        else:
            cur.execute('DELETE FROM sessions WHERE token=?',(token,))
        conn.commit(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def me():
    return jsonify(request.user)

@app.route('/api/users', methods=['GET'])
@require_auth
def list_users():
    if request.user['role'] not in ('admin', 'qc_manager'):
        return jsonify({'error': 'Forbidden'}), 403
    conn=get_conn(); cur=conn.cursor()
    cur.execute('SELECT id, username, role, display_name, created_at, last_login FROM users ORDER BY id')
    rows=cur.fetchall()
    cols=[d[0] for d in cur.description]
    data=[dict(zip(cols, r)) for r in rows]
    conn.close()
    return jsonify(data)

@app.route('/api/qc-sheets', methods=['GET'])
@require_auth
def list_sheets():
    conn=get_conn(); cur=conn.cursor()
    cur.execute('SELECT * FROM qc_sheets ORDER BY id DESC')
    rows=cur.fetchall()
    if not rows:
        conn.close()
        return jsonify([])
    cols=[d[0] for d in cur.description]
    data=[]
    for r in rows:
        d=dict(zip(cols, r))
        # Ensure checklist_data is parsed if string
        if isinstance(d.get('checklist_data'), str):
            try: d['checklist_data']=json.loads(d['checklist_data'])
            except: pass
        data.append(d)
    conn.close()
    return jsonify(data)

@app.route('/api/qc-sheets', methods=['POST'])
@require_auth
def create_sheet():
    data=request.get_json() or {}
    now=datetime.utcnow().isoformat()
    checklist=json.dumps(data.get('checklist_data',{}))
    conn=get_conn(); cur=conn.cursor()
    if USE_PG:
        cur.execute("""INSERT INTO qc_sheets (project_name, location, structure_number, collector_number, section_number, chainage_extra, date, inspector, status, sheet_type, checklist_data, created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (data.get('project_name',''), data.get('location',''), data.get('structure_number',''), data.get('collector_number',''), data.get('section_number',''), data.get('chainage_extra',''), data.get('date',''), data.get('inspector',''), data.get('status','draft'), data.get('sheet_type','trench'), checklist, now, now))
        nid=cur.fetchone()[0]
    else:
        cur.execute("""INSERT INTO qc_sheets (project_name, location, structure_number, collector_number, section_number, chainage_extra, date, inspector, status, sheet_type, checklist_data, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (data.get('project_name',''), data.get('location',''), data.get('structure_number',''), data.get('collector_number',''), data.get('section_number',''), data.get('chainage_extra',''), data.get('date',''), data.get('inspector',''), data.get('status','draft'), data.get('sheet_type','trench'), checklist, now, now))
        nid=cur.lastrowid
    conn.commit(); conn.close()
    return jsonify({'id': nid})

@app.route('/api/gantt-tasks', methods=['GET'])
@require_auth
def list_gantt():
    conn=get_conn(); cur=conn.cursor()
    cur.execute('SELECT * FROM gantt_tasks ORDER BY id')
    rows=cur.fetchall()
    cols=[d[0] for d in cur.description] if rows else []
    data=[dict(zip(cols, r)) for r in rows]
    conn.close()
    return jsonify(data)

@app.route('/api/gantt-tasks', methods=['POST'])
@require_auth
def create_gantt():
    data=request.get_json() or {}
    now=datetime.utcnow().isoformat()
    conn=get_conn(); cur=conn.cursor()
    if USE_PG:
        cur.execute("""INSERT INTO gantt_tasks (name, start_date, end_date, progress, assignee, dependencies, color, created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (data.get('name',''), data.get('start_date',''), data.get('end_date',''), data.get('progress',0), data.get('assignee',''), json.dumps(data.get('dependencies',[])), data.get('color',''), now))
        nid=cur.fetchone()[0]
    else:
        cur.execute("""INSERT INTO gantt_tasks (name, start_date, end_date, progress, assignee, dependencies, color, created_at)
            VALUES (?,?,?,?,?,?,?,?)""",
            (data.get('name',''), data.get('start_date',''), data.get('end_date',''), data.get('progress',0), data.get('assignee',''), json.dumps(data.get('dependencies',[])), data.get('color',''), now))
        nid=cur.lastrowid
    conn.commit(); conn.close()
    return jsonify({'id': nid})

@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({
        'db': 'Postgres' if USE_PG else 'SQLite',
        'has_postgres': HAS_PG,
        'database_url_set': bool(DATABASE_URL),
        'time': datetime.utcnow().isoformat()
    })

# === SAFE CHECKPOINT v101 - Clean, no indent errors ===
import json as _cp_json
import os as _cp_os
from datetime import datetime as _cp_dt

CHECKPOINT_FILE = 'checkpoints.jsonl'
DEPLOY_COUNT_FILE = '.deploy_count'
CHECKPOINT_EVERY = 5

def _get_deploy_count():
    try:
        if _cp_os.path.exists(DEPLOY_COUNT_FILE):
            with open(DEPLOY_COUNT_FILE, 'r') as f:
                return int(f.read().strip() or '0')
    except:
        pass
    return 0

def _inc_deploy_count():
    c = _get_deploy_count() + 1
    try:
        with open(DEPLOY_COUNT_FILE, 'w') as f:
            f.write(str(c))
    except:
        pass
    return c

def save_checkpoint_summary(action='deploy', details=None):
    count = _inc_deploy_count()
    summary = {
        'timestamp': _cp_dt.utcnow().isoformat() + 'Z',
        'deploy_no': count,
        'action': action,
        'details': details or {},
        'db_type': 'postgres' if USE_PG else 'sqlite'
    }
    try:
        with open(CHECKPOINT_FILE, 'a') as f:
            f.write(_cp_json.dumps(summary) + '\n')
    except:
        pass
    is_cp = (count % CHECKPOINT_EVERY == 0)
    return count, is_cp

@app.route('/api/checkpoints', methods=['GET'])
def list_checkpoints():
    if not _cp_os.path.exists(CHECKPOINT_FILE):
        return jsonify([])
    out = []
    try:
        with open(CHECKPOINT_FILE, 'r') as f:
            for line in f:
                if line.strip():
                    out.append(_cp_json.loads(line))
    except:
        pass
    return jsonify(out[-50:])

@app.route('/api/checkpoints/save', methods=['POST'])
def manual_checkpoint():
    data = request.get_json(silent=True) or {}
    c, is_cp = save_checkpoint_summary(action=data.get('action','manual'), details=data)
    return jsonify({'deploy_no': c, 'is_checkpoint': is_cp, 'every': CHECKPOINT_EVERY})

@app.route('/api/checkpoints/count', methods=['GET'])
def get_count():
    cnt = _get_deploy_count()
    nxt = CHECKPOINT_EVERY - (cnt % CHECKPOINT_EVERY) if cnt % CHECKPOINT_EVERY != 0 else 0
    return jsonify({'count': cnt, 'next_checkpoint_in': nxt})

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',8000)))
