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
        cur.execute('''CREATE TABLE IF NOT EXISTS qc_sheets (
            id SERIAL PRIMARY KEY, project_name TEXT, location TEXT,
            structure_number TEXT DEFAULT '', collector_number TEXT DEFAULT '',
            section_number TEXT DEFAULT '', chainage_extra TEXT DEFAULT '',
            date TEXT, inspector TEXT, status TEXT DEFAULT 'draft',
            sheet_type TEXT DEFAULT 'trench', checklist_data TEXT, created_at TEXT, updated_at TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS gantt_tasks (
            id SERIAL PRIMARY KEY, name TEXT, start_date TEXT, end_date TEXT,
            progress INTEGER DEFAULT 0, assignee TEXT, dependencies TEXT, color TEXT, created_at TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, role TEXT DEFAULT 'viewer',
            display_name TEXT DEFAULT '', created_at TEXT, last_login TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY, user_id INTEGER, username TEXT, role TEXT,
            display_name TEXT, created_at TEXT)''')
    else:
        cur.execute('''CREATE TABLE IF NOT EXISTS qc_sheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT, project_name TEXT, location TEXT,
            structure_number TEXT DEFAULT '', collector_number TEXT DEFAULT '',
            section_number TEXT DEFAULT '', chainage_extra TEXT DEFAULT '',
            date TEXT, inspector TEXT, status TEXT DEFAULT 'draft',
            sheet_type TEXT DEFAULT 'trench', checklist_data TEXT, created_at TEXT, updated_at TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS gantt_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, start_date TEXT, end_date TEXT,
            progress INTEGER DEFAULT 0, assignee TEXT, dependencies TEXT, color TEXT, created_at TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, role TEXT DEFAULT 'viewer',
            display_name TEXT DEFAULT '', created_at TEXT, last_login TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY, user_id INTEGER, username TEXT, role TEXT,
            display_name TEXT, created_at TEXT)''')
    conn.commit(); conn.close()

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

# ---- Auth helpers with persistent sessions ----
def get_session(token):
    if not token: return None
    conn=get_conn(); cur=conn.cursor()
    if USE_PG: cur.execute('SELECT * FROM sessions WHERE token=%s',(token,))
    else: cur.execute('SELECT * FROM sessions WHERE token=?',(token,))
    row=cur.fetchone()
    conn.close()
    if not row: return None
    return dict(zip([d[0] for d in cur.description], row)) if USE_PG else dict(row)

def require_auth(f):
    @wraps(f)
    def d(*args, **kwargs):
        auth=request.headers.get('Authorization','')
        token=auth[7:] if auth.startswith('Bearer ') else (request.headers.get('X-Token') or request.args.get('token'))
        sess=get_session(token)
        if not sess: return jsonify({"error":"Unauthorized - Please login again"}), 401
        request.current_user=sess
        return f(*args, **kwargs)
    return d

def require_role(*roles):
    def deco(f):
        @wraps(f)
        def d(*args, **kwargs):
            auth=request.headers.get('Authorization','')
            token=auth[7:] if auth.startswith('Bearer ') else (request.headers.get('X-Token') or request.args.get('token'))
            sess=get_session(token)
            if not sess: return jsonify({"error":"Unauthorized - Please login"}), 401
            request.current_user=sess
            if sess['role'] not in roles:
                return jsonify({"error":f"Forbidden - Role '{sess['role']}' cannot do this. Need: {', '.join(roles)}"}), 403
            return f(*args, **kwargs)
        return d
    return deco

@app.route('/')
def home(): return send_from_directory('.', 'index.html')
@app.route('/login')
def login_page(): return send_from_directory('.', 'login.html')
@app.route('/users')
def users_page(): return send_from_directory('.', 'users.html')
@app.route('/gantt')
def gantt_route(): return send_from_directory('.', 'gantt_planner_DB.html')
@app.route('/qc')
def qc_route(): return send_from_directory('.', 'quality_check_multi.html')

@app.route('/api/status')
def status(): return jsonify({"db":"Postgres" if USE_PG else "SQLite","use_postgres":USE_PG,"ok":True,"persistent_sessions":True})

@app.route('/api/debug')
def debug():
    import os as _os
    return jsonify({"use_postgres":USE_PG,"files":_os.listdir('.')[:20]})

@app.route('/api/auth/login', methods=['POST'])
def login():
    data=request.json or {}
    username=(data.get('username') or '').strip()
    password=data.get('password') or ''
    conn=get_conn(); cur=conn.cursor()
    if USE_PG: cur.execute('SELECT * FROM users WHERE username=%s',(username,))
    else: cur.execute('SELECT * FROM users WHERE username=?',(username,))
    row=cur.fetchone()
    if not row:
        conn.close(); return jsonify({"error":"Invalid username or password"}), 401
    user=dict(zip([d[0] for d in cur.description], row)) if USE_PG else dict(row)
    if not check_password_hash(user['password_hash'], password):
        conn.close(); return jsonify({"error":"Invalid username or password"}), 401
    now=datetime.utcnow().isoformat()
    if USE_PG: cur.execute('UPDATE users SET last_login=%s WHERE id=%s',(now,user['id']))
    else: cur.execute('UPDATE users SET last_login=? WHERE id=?',(now,user['id']))
    token=secrets.token_hex(24)
    if USE_PG:
        cur.execute('INSERT INTO sessions (token,user_id,username,role,display_name,created_at) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (token) DO NOTHING',(token,user['id'],user['username'],user['role'],user['display_name'],now))
    else:
        cur.execute('INSERT OR REPLACE INTO sessions (token,user_id,username,role,display_name,created_at) VALUES (?,?,?,?,?,?)',(token,user['id'],user['username'],user['role'],user['display_name'],now))
    conn.commit(); conn.close()
    return jsonify({"id":user['id'],"username":user['username'],"role":user['role'],"display_name":user['display_name'],"token":token,"login_at":now})

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    auth=request.headers.get('Authorization','')
    token=auth[7:] if auth.startswith('Bearer ') else (request.headers.get('X-Token') or (request.json or {}).get('token'))
    if token:
        conn=get_conn(); cur=conn.cursor()
        if USE_PG: cur.execute('DELETE FROM sessions WHERE token=%s',(token,))
        else: cur.execute('DELETE FROM sessions WHERE token=?',(token,))
        conn.commit(); conn.close()
    return jsonify({"ok":True})

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def me(): return jsonify(request.current_user)

@app.route('/api/auth/users', methods=['GET'])
def list_users():
    conn=get_conn(); cur=conn.cursor()
    cur.execute('SELECT id, username, role, display_name, created_at, last_login FROM users ORDER BY id')
    rows=cur.fetchall(); data=rows_to_dicts(cur, rows) if USE_PG else [dict(r) for r in rows]
    conn.close(); return jsonify(data)

@app.route('/api/auth/users', methods=['POST'])
@require_role('admin')
def create_user():
    data=request.json or {}
    username=(data.get('username') or '').strip()
    password=data.get('password') or ''
    role=data.get('role') or 'viewer'
    display_name=data.get('display_name') or ''
    if not username or not password: return jsonify({"error":"Username and password required"}),400
    if len(password)<6: return jsonify({"error":"Password min 6"}),400
    conn=get_conn(); cur=conn.cursor(); now=datetime.utcnow().isoformat()
    try:
        if USE_PG:
            cur.execute('INSERT INTO users (username,password_hash,role,display_name,created_at) VALUES (%s,%s,%s,%s,%s) RETURNING id',(username,generate_password_hash(password),role,display_name,now))
            sid=cur.fetchone()[0]
        else:
            cur.execute('INSERT INTO users (username,password_hash,role,display_name,created_at) VALUES (?,?,?,?,?)',(username,generate_password_hash(password),role,display_name,now))
            sid=cur.lastrowid
        conn.commit()
    except Exception as e:
        conn.close(); return jsonify({"error":f"Username exists: {e}"}),400
    conn.close(); return jsonify({"id":sid})

@app.route('/api/auth/users/<int:uid>', methods=['DELETE'])
@require_role('admin')
def delete_user(uid):
    if uid==1: return jsonify({"error":"Cannot delete main admin"}),400
    conn=get_conn(); cur=conn.cursor()
    if USE_PG: cur.execute('DELETE FROM users WHERE id=%s',(uid,))
    else: cur.execute('DELETE FROM users WHERE id=?',(uid,))

@app.route('/api/auth/users/<int:uid>', methods=['PUT'])
@require_role('admin')
def edit_user(uid):
    data=request.json or {}
    username=(data.get('username') or '').strip()
    display_name=(data.get('display_name') or '').strip()
    role=(data.get('role') or '').strip()
    password=data.get('password')
    if not username:
        return jsonify({"error":"Username required"}),400
    if role and role not in ['viewer','inspector','qc_manager','admin']:
        return jsonify({"error":"Invalid role"}),400
    conn=get_conn(); cur=conn.cursor()
    # Check if username taken by other user
    if USE_PG:
        cur.execute('SELECT id FROM users WHERE username=%s AND id!=%s',(username,uid))
    else:
        cur.execute('SELECT id FROM users WHERE username=? AND id!=?',(username,uid))
    if cur.fetchone():
        conn.close(); return jsonify({"error":"Username already taken"}),400
    # Build update
    if password:
        if len(password)<6:
            conn.close(); return jsonify({"error":"Password min 6 chars"}),400
        phash=generate_password_hash(password)
        if USE_PG:
            cur.execute('UPDATE users SET username=%s, display_name=%s, role=%s, password_hash=%s WHERE id=%s',(username,display_name,role,phash,uid))
        else:
            cur.execute('UPDATE users SET username=?, display_name=?, role=?, password_hash=? WHERE id=?',(username,display_name,role,phash,uid))
    else:
        if USE_PG:
            cur.execute('UPDATE users SET username=%s, display_name=%s, role=%s WHERE id=%s',(username,display_name,role,uid))
        else:
            cur.execute('UPDATE users SET username=?, display_name=?, role=? WHERE id=?',(username,display_name,role,uid))
    # Also update sessions for this user to reflect new role/name
    if USE_PG:
        cur.execute('UPDATE sessions SET username=%s, role=%s, display_name=%s WHERE user_id=%s',(username,role,display_name,uid))
    else:
        cur.execute('UPDATE sessions SET username=?, role=?, display_name=? WHERE user_id=?',(username,role,display_name,uid))
    conn.commit(); conn.close()
    return jsonify({"ok":True})


# QC
@app.route('/api/qc-sheets', methods=['GET'])
def get_qc():
    conn=get_conn(); cur=conn.cursor()
    cur.execute('SELECT * FROM qc_sheets ORDER BY id DESC')
    rows=cur.fetchall(); data=rows_to_dicts(cur, rows) if USE_PG else [dict(r) for r in rows]
    conn.close(); return jsonify(data)

@app.route('/api/qc-sheets', methods=['POST'])
@require_role('inspector','qc_manager','admin')
def create_qc():
    data=request.json or {}; now=datetime.utcnow().isoformat()
    conn=get_conn(); cur=conn.cursor()
    fields=('project_name','location','structure_number','collector_number','section_number','chainage_extra','date','inspector','status','sheet_type','checklist_data')
    vals=[data.get(f,'') if f!='checklist_data' else json.dumps(data.get(f,{})) for f in fields]
    if USE_PG:
        cur.execute('INSERT INTO qc_sheets (project_name,location,structure_number,collector_number,section_number,chainage_extra,date,inspector,status,sheet_type,checklist_data,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id', (*vals,now,now))
        sid=cur.fetchone()[0]
    else:
        cur.execute('INSERT INTO qc_sheets (project_name,location,structure_number,collector_number,section_number,chainage_extra,date,inspector,status,sheet_type,checklist_data,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)', (*vals,now,now))
        sid=cur.lastrowid
    conn.commit(); conn.close(); return jsonify({"id":sid})

@app.route('/api/qc-sheets/<int:sid>', methods=['PUT'])
@require_role('inspector','qc_manager','admin')
def update_qc(sid):
    data=request.json or {}; now=datetime.utcnow().isoformat()
    conn=get_conn(); cur=conn.cursor()
    fields=('project_name','location','structure_number','collector_number','section_number','chainage_extra','date','inspector','status','sheet_type','checklist_data')
    set_clause=', '.join([f"{f}=%s" if USE_PG else f"{f}=?" for f in fields])+', updated_at=%s' if USE_PG else ', updated_at=?'
    vals=[data.get(f,'') if f!='checklist_data' else json.dumps(data.get(f,{})) for f in fields]
    vals.append(now); vals.append(sid)
    if USE_PG: cur.execute(f'UPDATE qc_sheets SET {set_clause} WHERE id=%s', vals)
    else: cur.execute(f'UPDATE qc_sheets SET {set_clause} WHERE id=?', vals)
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/qc-sheets/<int:sid>', methods=['DELETE'])
@require_role('qc_manager','admin')
def delete_qc(sid):
    conn=get_conn(); cur=conn.cursor()
    if USE_PG: cur.execute('DELETE FROM qc_sheets WHERE id=%s',(sid,))
    else: cur.execute('DELETE FROM qc_sheets WHERE id=?',(sid,))
    conn.commit(); conn.close(); return jsonify({"ok":True})

# Gantt
@app.route('/api/gantt-tasks', methods=['GET'])
def get_gantt():
    conn=get_conn(); cur=conn.cursor()
    cur.execute('SELECT * FROM gantt_tasks ORDER BY id')
    rows=cur.fetchall(); data=rows_to_dicts(cur, rows) if USE_PG else [dict(r) for r in rows]
    conn.close(); return jsonify(data)

@app.route('/api/gantt-tasks', methods=['POST'])
@require_role('qc_manager','admin')
def create_gantt():
    data=request.json or {}; now=datetime.utcnow().isoformat()
    conn=get_conn(); cur=conn.cursor()
    if USE_PG:
        cur.execute('INSERT INTO gantt_tasks (name,start_date,end_date,progress,assignee,dependencies,color,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id',(data.get('name'),data.get('start_date'),data.get('end_date'),data.get('progress',0),data.get('assignee'),data.get('dependencies'),data.get('color'),now))
        sid=cur.fetchone()[0]
    else:
        cur.execute('INSERT INTO gantt_tasks (name,start_date,end_date,progress,assignee,dependencies,color,created_at) VALUES (?,?,?,?,?,?,?,?)',(data.get('name'),data.get('start_date'),data.get('end_date'),data.get('progress',0),data.get('assignee'),data.get('dependencies'),data.get('color'),now))
        sid=cur.lastrowid
    conn.commit(); conn.close(); return jsonify({"id":sid})

@app.route('/api/gantt-tasks/<int:tid>', methods=['PUT'])
@require_role('qc_manager','admin')
def update_gantt(tid):
    data=request.json or {}; conn=get_conn(); cur=conn.cursor()
    if USE_PG:
        cur.execute('UPDATE gantt_tasks SET name=%s,start_date=%s,end_date=%s,progress=%s,assignee=%s,dependencies=%s,color=%s WHERE id=%s',(data.get('name'),data.get('start_date'),data.get('end_date'),data.get('progress'),data.get('assignee'),data.get('dependencies'),data.get('color'),tid))
    else:
        cur.execute('UPDATE gantt_tasks SET name=?,start_date=?,end_date=?,progress=?,assignee=?,dependencies=?,color=? WHERE id=?',(data.get('name'),data.get('start_date'),data.get('end_date'),data.get('progress'),data.get('assignee'),data.get('dependencies'),data.get('color'),tid))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/gantt-tasks/<int:tid>', methods=['DELETE'])
@require_role('qc_manager','admin')
def delete_gantt(tid):
    conn=get_conn(); cur=conn.cursor()
    if USE_PG: cur.execute('DELETE FROM gantt_tasks WHERE id=%s',(tid,))
    else: cur.execute('DELETE FROM gantt_tasks WHERE id=?',(tid,))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/export/excel')
def export_excel():
    try:
        from openpyxl import Workbook
        from io import BytesIO
    except:
        return jsonify({"error":"openpyxl not installed"}),500
    conn=get_conn(); cur=conn.cursor()
    cur.execute('SELECT * FROM qc_sheets')
    rows=cur.fetchall(); data=rows_to_dicts(cur, rows) if USE_PG else [dict(r) for r in rows]
    conn.close()
    wb=Workbook(); ws=wb.active; ws.title="QC Sheets"
    ws.append(["ID","Project","Location","Structure","Collector","Section","Chainage","Date","Inspector","Status","Type"])
    for r in data:
        ws.append([r.get('id'),r.get('project_name'),r.get('location'),r.get('structure_number'),r.get('collector_number'),r.get('section_number'),r.get('chainage_extra'),r.get('date'),r.get('inspector'),r.get('status'),r.get('sheet_type')])
    bio=BytesIO(); wb.save(bio); bio.seek(0)
    return app.response_class(bio.getvalue(), mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition':'attachment; filename=QC_Export.xlsx'})

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',8000)))
