
import os, json, sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS

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

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    if USE_PG:
        cur.execute('''CREATE TABLE IF NOT EXISTS qc_sheets (
            id SERIAL PRIMARY KEY,
            project_name TEXT,
            location TEXT,
            structure_number TEXT DEFAULT '',
            collector_number TEXT DEFAULT '',
            section_number TEXT DEFAULT '',
            chainage_extra TEXT DEFAULT '',
            date TEXT,
            inspector TEXT,
            status TEXT DEFAULT 'draft',
            checks_json TEXT,
            created_at TEXT,
            updated_at TEXT
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS gantt_tasks (
            id SERIAL PRIMARY KEY,
            name TEXT,
            start_date TEXT,
            end_date TEXT,
            progress INTEGER,
            color TEXT,
            owner TEXT,
            created_at TEXT,
            updated_at TEXT
        )''')
        for col in ['structure_number','collector_number','section_number','chainage_extra']:
            try:
                cur.execute(f"ALTER TABLE qc_sheets ADD COLUMN {col} TEXT DEFAULT ''")
            except:
                pass
    else:
        cur.execute('''CREATE TABLE IF NOT EXISTS qc_sheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT,
            location TEXT,
            structure_number TEXT DEFAULT '',
            collector_number TEXT DEFAULT '',
            section_number TEXT DEFAULT '',
            chainage_extra TEXT DEFAULT '',
            date TEXT,
            inspector TEXT,
            status TEXT DEFAULT 'draft',
            checks_json TEXT,
            created_at TEXT,
            updated_at TEXT
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS gantt_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            start_date TEXT,
            end_date TEXT,
            progress INTEGER,
            color TEXT,
            owner TEXT,
            created_at TEXT,
            updated_at TEXT
        )''')
    conn.commit()
    cur.execute('SELECT COUNT(*) FROM gantt_tasks')
    count = cur.fetchone()[0]
    if count == 0:
        defaults = [
            ("Project Initiation & Contract","2026-01-06","2026-01-16",100,"#3b82f6","PMO"),
            ("Site Survey & Soil Test","2026-01-13","2026-01-28",100,"#8b5cf6","Engineering"),
            ("Powerline Route Design","2026-01-20","2026-02-10",85,"#8b5cf6","Design"),
            ("Material Procurement - Poles & Cables","2026-02-02","2026-02-28",60,"#f59e0b","Procurement"),
            ("Foundation & Pole Erection","2026-02-18","2026-03-20",40,"#10b981","Construction"),
            ("Conductor Stringing","2026-03-10","2026-04-05",15,"#10b981","Construction"),
            ("Transformer Installation","2026-03-25","2026-04-15",0,"#10b981","Electrical"),
            ("Testing & Commissioning","2026-04-10","2026-04-25",0,"#ef4444","QA"),
            ("Client Handover & Documentation","2026-04-22","2026-04-30",0,"#0f172a","PMO"),
        ]
        now = datetime.utcnow().isoformat()
        for d in defaults:
            if USE_PG:
                cur.execute('INSERT INTO gantt_tasks (name,start_date,end_date,progress,color,owner,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)', (*d, now, now))
            else:
                cur.execute('INSERT INTO gantt_tasks (name,start_date,end_date,progress,color,owner,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)', (*d, now, now))
        conn.commit()
    conn.close()

init_db()

# ========= AUTH SYSTEM =========
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

def init_auth():
    conn = get_conn(); cur = conn.cursor()
    if USE_PG:
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'viewer',
            display_name TEXT DEFAULT '',
            created_at TEXT,
            last_login TEXT
        )""")
    else:
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'viewer',
            display_name TEXT DEFAULT '',
            created_at TEXT,
            last_login TEXT
        )""")
    conn.commit()
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

init_auth()

@app.route('/login')
def login_page():
    return send_from_directory('.', 'login.html')

@app.route('/users')
def users_page():
    return send_from_directory('.', 'users.html')

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    data = request.json
    username = data.get('username','').strip()
    password = data.get('password','')
    conn = get_conn(); cur = conn.cursor()
    if USE_PG:
        cur.execute('SELECT * FROM users WHERE username=%s', (username,))
    else:
        cur.execute('SELECT * FROM users WHERE username=?', (username,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({"error":"Invalid username or password"}), 401
    # Convert row to dict
    if USE_PG:
        cols = [desc[0] for desc in cur.description]
        user = dict(zip(cols, row))
    else:
        user = dict(row)
    if not check_password_hash(user['password_hash'], password):
        conn.close()
        return jsonify({"error":"Invalid username or password"}), 401
    now = datetime.utcnow().isoformat()
    if USE_PG:
        cur.execute('UPDATE users SET last_login=%s WHERE id=%s', (now, user['id']))
    else:
        cur.execute('UPDATE users SET last_login=? WHERE id=?', (now, user['id']))
    conn.commit(); conn.close()
    token = secrets.token_hex(16)
    return jsonify({"id": user['id'],"username": user['username'],"role": user['role'],"display_name": user['display_name'],"token": token,"login_at": now})

@app.route('/api/auth/users', methods=['GET'])
def list_users():
    conn = get_conn(); cur = conn.cursor()
    cur.execute('SELECT id, username, role, display_name, created_at, last_login FROM users ORDER BY id')
    rows = cur.fetchall()
    data = rows_to_dicts(cur, rows) if USE_PG else [dict(r) for r in rows]
    conn.close()
    return jsonify(data)

@app.route('/api/auth/users', methods=['POST'])
@require_role('admin')
def create_user():
    data = request.json
    username = data.get('username','').strip()
    password = data.get('password','')
    role = data.get('role','viewer')
    display_name = data.get('display_name','')
    if not username or not password:
        return jsonify({"error":"Username and password required"}), 400
    if len(password) < 6:
        return jsonify({"error":"Password must be at least 6 chars"}), 400
    conn = get_conn(); cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    try:
        if USE_PG:
            cur.execute('INSERT INTO users (username,password_hash,role,display_name,created_at) VALUES (%s,%s,%s,%s,%s) RETURNING id',(username, generate_password_hash(password), role, display_name, now))
            sid = cur.fetchone()[0]
        else:
            cur.execute('INSERT INTO users (username,password_hash,role,display_name,created_at) VALUES (?,?,?,?,?)',(username, generate_password_hash(password), role, display_name, now))
            sid = cur.lastrowid
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({"error": f"Username exists or error: {e}"}), 400
    conn.close()
    return jsonify({"id": sid})

@app.route('/api/auth/users/<int:uid>', methods=['DELETE'])
@require_role('admin')
def delete_user(uid):
    if uid == 1:
        return jsonify({"error":"Cannot delete main admin"}), 400
    conn = get_conn(); cur = conn.cursor()
    if USE_PG:
        cur.execute('DELETE FROM users WHERE id=%s', (uid,))
    else:
        cur.execute('DELETE FROM users WHERE id=?', (uid,))
    conn.commit(); conn.close()
    return jsonify({"ok": True})
# ========= END AUTH =========


@app.route('/')
def index(): return send_from_directory('.', 'index.html')

@app.route('/gantt')
def gantt_page(): return send_from_directory('.', 'gantt_planner_DB.html')

@app.route('/qc')
def qc_page(): return send_from_directory('.', 'quality_check_multi.html')

@app.route('/quality_check_multi.html')
def qc_multi(): return send_from_directory('.', 'quality_check_multi.html')

@app.route('/gantt_planner_DB.html')
def gantt_db(): return send_from_directory('.', 'gantt_planner_DB.html')

@app.route('/api/debug')
def debug():
    import os
    files = os.listdir('.')
    return jsonify({"cwd": os.getcwd(), "exists_gantt": os.path.exists('gantt_planner_DB.html'), "exists_qc": os.path.exists('quality_check_multi.html'), "files": files})

def rows_to_dicts(cur, rows):
    if USE_PG:
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, r)) for r in rows]
    else:
        return [dict(r) for r in rows]

@app.route('/api/qc-sheets', methods=['GET'])
def list_qc():
    conn = get_conn(); cur = conn.cursor()
    cur.execute('SELECT * FROM qc_sheets ORDER BY updated_at DESC')
    rows = cur.fetchall()
    data = rows_to_dicts(cur, rows)
    conn.close()
    for r in data:
        try: r['checks'] = json.loads(r['checks_json'] or '{}')
        except: r['checks'] = {}
    return jsonify(data)

@app.route('/api/qc-sheets', methods=['POST'])
@require_role('inspector','qc_manager','admin')
def create_qc():
    d = request.json
    conn = get_conn(); cur = conn.cursor(); now = datetime.utcnow().isoformat()
    if USE_PG:
        cur.execute('INSERT INTO qc_sheets (project_name,location,structure_number,collector_number,section_number,chainage_extra,date,inspector,status,checks_json,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id',
                    (d.get('project_name',''), d.get('location',''), d.get('structure_number',''), d.get('collector_number',''), d.get('section_number',''), d.get('chainage_extra',''), d.get('date',''), d.get('inspector','HZC QC Team'), d.get('status','draft'), json.dumps(d.get('checks',{})), now, now))
        sid = cur.fetchone()[0]
    else:
        cur.execute('INSERT INTO qc_sheets (project_name,location,structure_number,collector_number,section_number,chainage_extra,date,inspector,status,checks_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                    (d.get('project_name',''), d.get('location',''), d.get('structure_number',''), d.get('collector_number',''), d.get('section_number',''), d.get('chainage_extra',''), d.get('date',''), d.get('inspector','HZC QC Team'), d.get('status','draft'), json.dumps(d.get('checks',{})), now, now))
        sid = cur.lastrowid
    conn.commit(); conn.close()
    return jsonify({"id": sid})

@app.route('/api/qc-sheets/<int:sid>', methods=['GET'])
def get_qc(sid):
    conn = get_conn(); cur = conn.cursor()
    if USE_PG: cur.execute('SELECT * FROM qc_sheets WHERE id=%s', (sid,))
    else: cur.execute('SELECT * FROM qc_sheets WHERE id=?', (sid,))
    r = cur.fetchone()
    if not r: 
        conn.close(); return jsonify({"error":"not found"}), 404
    data = rows_to_dicts(cur, [r])[0] if USE_PG else dict(r)
    try: data['checks'] = json.loads(data['checks_json'] or '{}')
    except: data['checks'] = {}
    conn.close()
    return jsonify(data)

@app.route('/api/qc-sheets/<int:sid>', methods=['PUT'])
@require_role('inspector','qc_manager','admin')
def update_qc(sid):
    d = request.json; now = datetime.utcnow().isoformat()
    conn = get_conn(); cur = conn.cursor()
    if USE_PG:
        cur.execute('UPDATE qc_sheets SET project_name=%s, location=%s, structure_number=%s, collector_number=%s, section_number=%s, chainage_extra=%s, date=%s, inspector=%s, status=%s, checks_json=%s, updated_at=%s WHERE id=%s',
                    (d.get('project_name'), d.get('location'), d.get('structure_number',''), d.get('collector_number',''), d.get('section_number',''), d.get('chainage_extra',''), d.get('date'), d.get('inspector'), d.get('status'), json.dumps(d.get('checks',{})), now, sid))
    else:
        cur.execute('UPDATE qc_sheets SET project_name=?, location=?, structure_number=?, collector_number=?, section_number=?, chainage_extra=?, date=?, inspector=?, status=?, checks_json=?, updated_at=? WHERE id=?',
                    (d.get('project_name'), d.get('location'), d.get('structure_number',''), d.get('collector_number',''), d.get('section_number',''), d.get('chainage_extra',''), d.get('date'), d.get('inspector'), d.get('status'), json.dumps(d.get('checks',{})), now, sid))
    conn.commit(); conn.close()
    return jsonify({"ok":True})

@app.route('/api/qc-sheets/<int:sid>', methods=['DELETE'])
@require_role('qc_manager','admin')
def delete_qc(sid):
    conn=get_conn(); cur=conn.cursor()
    if USE_PG: cur.execute('DELETE FROM qc_sheets WHERE id=%s',(sid,))
    else: cur.execute('DELETE FROM qc_sheets WHERE id=?',(sid,))
    conn.commit(); conn.close()
    return jsonify({"ok":True})

@app.route('/api/gantt-tasks', methods=['GET'])
def list_gantt():
    conn=get_conn(); cur=conn.cursor()
    cur.execute('SELECT * FROM gantt_tasks ORDER BY start_date ASC')
    rows=cur.fetchall()
    data=rows_to_dicts(cur, rows)
    conn.close()
    return jsonify(data)

@app.route('/api/gantt-tasks', methods=['POST'])
@require_role('qc_manager','admin')
def create_gantt():
    d=request.json; now=datetime.utcnow().isoformat()
    conn=get_conn(); cur=conn.cursor()
    if USE_PG:
        cur.execute('INSERT INTO gantt_tasks (name,start_date,end_date,progress,color,owner,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id',
                    (d['name'], d['start'], d['end'], d.get('progress',0), d.get('color','#3b82f6'), d.get('owner','HZC'), now, now))
        sid=cur.fetchone()[0]
    else:
        cur.execute('INSERT INTO gantt_tasks (name,start_date,end_date,progress,color,owner,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)',
                    (d['name'], d['start'], d['end'], d.get('progress',0), d.get('color','#3b82f6'), d.get('owner','HZC'), now, now))
        sid=cur.lastrowid
    conn.commit(); conn.close()
    return jsonify({"id":sid})

@app.route('/api/gantt-tasks/<int:tid>', methods=['PUT'])
@require_role('qc_manager','admin')
def update_gantt(tid):
    d=request.json; now=datetime.utcnow().isoformat()
    conn=get_conn(); cur=conn.cursor()
    if USE_PG:
        cur.execute('UPDATE gantt_tasks SET name=%s, start_date=%s, end_date=%s, progress=%s, color=%s, owner=%s, updated_at=%s WHERE id=%s',
                    (d['name'], d['start'], d['end'], d.get('progress',0), d.get('color'), d.get('owner'), now, tid))
    else:
        cur.execute('UPDATE gantt_tasks SET name=?, start_date=?, end_date=?, progress=?, color=?, owner=?, updated_at=? WHERE id=?',
                    (d['name'], d['start'], d['end'], d.get('progress',0), d.get('color'), d.get('owner'), now, tid))
    conn.commit(); conn.close()
    return jsonify({"ok":True})

@app.route('/api/gantt-tasks/<int:tid>', methods=['DELETE'])
@require_role('qc_manager','admin')
def delete_gantt(tid):
    conn=get_conn(); cur=conn.cursor()
    if USE_PG: cur.execute('DELETE FROM gantt_tasks WHERE id=%s',(tid,))
    else: cur.execute('DELETE FROM gantt_tasks WHERE id=?',(tid,))
    conn.commit(); conn.close()
    return jsonify({"ok":True})

@app.route('/api/export/excel')
def export_excel():
    from openpyxl import Workbook
    from io import BytesIO
    conn=get_conn(); cur=conn.cursor()
    cur.execute('SELECT * FROM qc_sheets ORDER BY updated_at DESC')
    rows=cur.fetchall()
    sheets=rows_to_dicts(cur, rows) if USE_PG else [dict(r) for r in rows]
    conn.close()
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "QC Sheets Summary"
    ws1.append(["ID","Project Name","Location","Structure No","Collector No","Section No","Date","Inspector","Status","Checked","Pass","Fail","Score %","Created At","Updated At"])
    ws2 = wb.create_sheet("Checks Detail")
    ws2.append(["Sheet ID","Project","Location","Structure","Collector","Section","Check Section","Check #","Checkpoint","Depth Selected","Status","Remark"])
    check_names = [
        ["Foundation & Excavation","Excavation depth","Shuttering alignment","Reinforcement","Concrete mix & slump","Curing 7 days","Backfilling"],
        ["Pole Erection","Pole type/height","Verticality ≤1°","Alignment","Bolt torque","Danger plate","Anti-climbing"],
        ["Conductor Stringing","ACSR type","Sag & tension","Jumper connections","Earth continuity","Insulator cleaning","Clearance ≥2.5m"],
        ["Earthing","Earth resistance <10Ω","Electrode depth 3m","GI size 25x3mm","Lightning arrester","Bonding","Pit marking"],
        ["Transformer","Rating 100/200kVA","Oil level & BDV","Bushing tightness","Cable termination","Fuse/MCB","Neutral <5Ω"],
        ["Testing","IR >50MΩ","Continuity","Polarity","Load test","Safety clearance","As-built docs"],
    ]
    for s in sheets:
        try: checks = json.loads(s.get('checks_json') or '{}')
        except: checks = {}
        passed = sum(1 for v in checks.values() if isinstance(v,dict) and v.get('status')=='pass')
        failed = sum(1 for v in checks.values() if isinstance(v,dict) and v.get('status')=='fail')
        checked = sum(1 for v in checks.values() if isinstance(v,dict) and v.get('status'))
        score = round(passed/checked*100) if checked else 0
        ws1.append([s['id'], s['project_name'], s.get('location',''), s.get('structure_number',''), s.get('collector_number',''), s.get('section_number',''), s['date'], s['inspector'], s['status'], checked, passed, failed, score, s['created_at'], s['updated_at']])
        for si, sec in enumerate(check_names):
            sec_title = sec[0]
            for ii, cp in enumerate(sec[1:]):
                key = f"{si}_{ii}"
                v = checks.get(key, {})
                if isinstance(v,dict):
                    depth = v.get('depth','') if si==0 and ii==0 else ''
                    ws2.append([s['id'], s['project_name'], s.get('location',''), s.get('structure_number',''), s.get('collector_number',''), s.get('section_number',''), sec_title, ii+1, cp, depth, v.get('status',''), v.get('remark','')])
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return Response(bio.getvalue(), mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition':'attachment; filename=ProjectTrack_QC_Sheets.xlsx'})

@app.route('/api/status')
def status():
    return jsonify({"use_postgres": USE_PG, "has_pg_driver": HAS_PG, "db": "Postgres" if USE_PG else "SQLite", "time": datetime.utcnow().isoformat()})

@app.route('/<path:path>')
def serve_static(path):
    # Fallback: if file exists serve it, else index
    import os
    if os.path.exists(path):
        return send_from_directory('.', path)
    return send_from_directory('.', 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 4002))
    app.run(host='0.0.0.0', port=port)


# ========= ROLE PROTECTION =========
from functools import wraps

# In-memory token store: token -> user dict
TOKEN_STORE = {}

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization','')
        token = None
        if auth.startswith('Bearer '):
            token = auth[7:]
        else:
            # fallback: allow X-Token or ?token= for compatibility
            token = request.headers.get('X-Token') or request.args.get('token')
        if not token or token not in TOKEN_STORE:
            return jsonify({"error":"Unauthorized - Please login"}), 401
        request.current_user = TOKEN_STORE[token]
        return f(*args, **kwargs)
    return decorated

def require_role(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth = request.headers.get('Authorization','')
            token = auth[7:] if auth.startswith('Bearer ') else (request.headers.get('X-Token') or request.args.get('token'))
            if not token or token not in TOKEN_STORE:
                return jsonify({"error":"Unauthorized - Please login"}), 401
            user = TOKEN_STORE[token]
            request.current_user = user
            if user['role'] not in allowed_roles:
                return jsonify({"error": f"Forbidden - Role '{user['role']}' cannot perform this. Required: {', '.join(allowed_roles)}"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

# Patch login to store token
original_login = auth_login
# We need to override auth_login to store token
@app.route('/api/auth/login', methods=['POST'])
def auth_login_with_token():
    data = request.json
    username = data.get('username','').strip()
    password = data.get('password','')
    conn = get_conn(); cur = conn.cursor()
    if USE_PG:
        cur.execute('SELECT * FROM users WHERE username=%s', (username,))
    else:
        cur.execute('SELECT * FROM users WHERE username=?', (username,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({"error":"Invalid username or password"}), 401
    if USE_PG:
        cols = [desc[0] for desc in cur.description]
        user = dict(zip(cols, row))
    else:
        user = dict(row)
    if not check_password_hash(user['password_hash'], password):
        conn.close()
        return jsonify({"error":"Invalid username or password"}), 401
    now = datetime.utcnow().isoformat()
    if USE_PG:
        cur.execute('UPDATE users SET last_login=%s WHERE id=%s', (now, user['id']))
    else:
        cur.execute('UPDATE users SET last_login=? WHERE id=?', (now, user['id']))
    conn.commit(); conn.close()
    token = secrets.token_hex(24)
    user_info = {"id": user['id'],"username": user['username'],"role": user['role'],"display_name": user['display_name'],"token": token,"login_at": now}
    TOKEN_STORE[token] = user_info
    return jsonify(user_info)

@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    auth = request.headers.get('Authorization','')
    token = auth[7:] if auth.startswith('Bearer ') else (request.headers.get('X-Token') or request.json.get('token') if request.json else None)
    if token in TOKEN_STORE:
        del TOKEN_STORE[token]
    return jsonify({"ok":True})

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def auth_me():
    return jsonify(request.current_user)
# ========= END ROLE PROTECTION =========

