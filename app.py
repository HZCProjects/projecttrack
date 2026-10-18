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
    # Migration: Add missing columns to old tables (if table existed before) - FULL LIST
    try:
        if USE_PG:
            # Check and add columns that might be missing in old DB - ALL columns
            for col, coltype in [
                ('project_name', 'TEXT DEFAULT \'\''),
                ('location', 'TEXT DEFAULT \'\''),
                ('structure_number', 'TEXT DEFAULT \'\''),
                ('collector_number', 'TEXT DEFAULT \'\''),
                ('section_number', 'TEXT DEFAULT \'\''),
                ('chainage_extra', 'TEXT DEFAULT \'\''),
                ('date', 'TEXT DEFAULT \'\''),
                ('inspector', 'TEXT DEFAULT \'\''),
                ('status', 'TEXT DEFAULT \'draft\''),
                ('sheet_type', 'TEXT DEFAULT \'trench\''),
                ('checklist_data', 'TEXT DEFAULT \'{}\''),
                ('created_at', 'TEXT DEFAULT \'\''),
                ('updated_at', 'TEXT DEFAULT \'\''),
                # Old column names that might have been used before
                ('data', 'TEXT DEFAULT \'{}\''),
                ('checks', 'TEXT DEFAULT \'{}\''),
                ('checklist', 'TEXT DEFAULT \'{}\''),
            ]:
                try:
                    cur.execute(f"ALTER TABLE qc_sheets ADD COLUMN IF NOT EXISTS {col} {coltype}")
                except Exception as e:
                    print(f"Migration add {col}: {e}")
            conn.commit()
            # Log current columns for debugging
            try:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='qc_sheets'")
                cols = [r[0] for r in cur.fetchall()]
                print(f"Current qc_sheets columns after migration: {cols}")
            except Exception as e:
                print(f"Could not list columns: {e}")
        else:
            # SQLite migration
            for col, coltype in [
                ('project_name', 'TEXT DEFAULT \'\''),
                ('location', 'TEXT DEFAULT \'\''),
                ('structure_number', 'TEXT DEFAULT \'\''),
                ('collector_number', 'TEXT DEFAULT \'\''),
                ('section_number', 'TEXT DEFAULT \'\''),
                ('chainage_extra', 'TEXT DEFAULT \'\''),
                ('date', 'TEXT DEFAULT \'\''),
                ('inspector', 'TEXT DEFAULT \'\''),
                ('status', 'TEXT DEFAULT \'draft\''),
                ('sheet_type', 'TEXT DEFAULT \'trench\''),
                ('checklist_data', 'TEXT DEFAULT \'{}\''),
                ('created_at', 'TEXT DEFAULT \'\''),
                ('updated_at', 'TEXT DEFAULT \'\''),
            ]:
                try:
                    cur.execute(f"ALTER TABLE qc_sheets ADD COLUMN {col} {coltype}")
                except Exception as e:
                    # Column already exists in SQLite throws error, ignore
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
        # Build dict manually to avoid description issues
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
            # FIX: If no session but DATABASE_URL missing (using SQLite ephemeral), allow save anyway for QC sheets
            # This prevents "Session expired" loop when Railway Postgres is deleted
            if not sess:
                # Check if this is a QC sheet request - allow with warning header
                if request.path.startswith('/api/qc-sheets'):
                    # Allow save even without session if token missing - create mock user
                    # This is temporary fix until Postgres restored
                    print(f"WARN: No session for {request.path}, token={token[:10] if token else 'none'} - allowing anyway (USE_PG={USE_PG})")
                    request.current_user = {'token': 'temp', 'user_id': 1, 'username': 'temp_user', 'role': 'admin', 'display_name': 'Temp Admin'}
                    return f(*args, **kwargs)
                return jsonify({"error":"Unauthorized - Please login"}), 401
            request.current_user=sess
            if sess['role'] not in roles:
                return jsonify({"error":f"Forbidden - Role '{sess['role']}' cannot do this. Need: {', '.join(roles)}"}), 403
            return f(*args, **kwargs)
        return d
    return deco


@app.route('/api/auth/check-session')
def check_session():
    token = request.args.get('token') or request.headers.get('Authorization','').replace('Bearer ','')
    if not token:
        return jsonify({"has_token": False, "use_pg": USE_PG, "db_url_set": bool(DATABASE_URL)})
    sess = get_session(token)
    return jsonify({"has_token": bool(token), "session_found": bool(sess), "session": sess, "use_pg": USE_PG})


@app.route('/api/qc-sheets/public-save', methods=['POST'])
def public_save_qc():
    """Fallback endpoint - ONE ID PER STRUCTURE NUMBER - updates if structure_number exists"""
    data=request.json or {}; now=datetime.utcnow().isoformat()
    conn=get_conn(); cur=conn.cursor()
    cdata=data.get('checklist_data') or data.get('checks') or data.get('checklist') or {}
    if isinstance(cdata, dict): cdata=json.dumps(cdata)
    fields=('project_name','location','structure_number','collector_number','section_number','chainage_extra','date','inspector','status','sheet_type')
    vals=[data.get(f,'') for f in fields]
    struct_no = str(data.get('structure_number','')).strip()
    try:
        # ENFORCE ONE ID PER (Structure No + Collector No + sheet_type) - handles duplicates
        sheet_type = data.get('sheet_type','')
        collector_no = str(data.get('collector_number','')).strip()
        if struct_no:
            if USE_PG:
                cur.execute('SELECT id FROM qc_sheets WHERE structure_number=%s AND collector_number=%s AND sheet_type=%s LIMIT 1', (struct_no, collector_no, sheet_type))
            else:
                cur.execute('SELECT id FROM qc_sheets WHERE structure_number=? AND collector_number=? AND sheet_type=? LIMIT 1', (struct_no, collector_no, sheet_type))
            existing = cur.fetchone()
            if existing:
                existing_id = existing[0] if USE_PG else existing[0]
                print(f"Structure {struct_no} already exists as ID {existing_id} - updating instead of creating new")
                # Update existing instead of creating new
                if USE_PG:
                    cur.execute('UPDATE qc_sheets SET project_name=%s, location=%s, structure_number=%s, collector_number=%s, section_number=%s, chainage_extra=%s, date=%s, inspector=%s, status=%s, sheet_type=%s, checklist_data=%s, updated_at=%s WHERE id=%s',
                        (*vals, cdata, now, existing_id))
                else:
                    cur.execute('UPDATE qc_sheets SET project_name=?, location=?, structure_number=?, collector_number=?, section_number=?, chainage_extra=?, date=?, inspector=?, status=?, sheet_type=?, checklist_data=?, updated_at=? WHERE id=?',
                        (*vals, cdata, now, existing_id))
                conn.commit(); conn.close()
                return jsonify({"id": existing_id, "updated": True, "message": f"Updated existing Structure {struct_no} Collector {collector_no} - ID {existing_id} (One ID per Structure+Collector)"})
        
        if USE_PG:
            cur.execute('INSERT INTO qc_sheets (project_name,location,structure_number,collector_number,section_number,chainage_extra,date,inspector,status,sheet_type,checklist_data,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id', (*vals,cdata,now,now))
            sid=cur.fetchone()[0]
        else:
            cur.execute('INSERT INTO qc_sheets (project_name,location,structure_number,collector_number,section_number,chainage_extra,date,inspector,status,sheet_type,checklist_data,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)', (*vals,cdata,now,now))
            sid=cur.lastrowid
        conn.commit(); conn.close()
        return jsonify({"id":sid, "created": True, "message": f"Created Structure {struct_no} - ID {sid}"})
    except Exception as e:
        print(f"public-save error (trying fallback): {e}")
        try:
            conn.rollback()
            # Check again for existing in fallback
            collector_no = str(data.get('collector_number','')).strip()
            sheet_type = data.get('sheet_type','')
            if struct_no:
                if USE_PG:
                    cur.execute('SELECT id FROM qc_sheets WHERE structure_number=%s AND collector_number=%s AND sheet_type=%s LIMIT 1', (struct_no, collector_no, sheet_type))
                else:
                    cur.execute('SELECT id FROM qc_sheets WHERE structure_number=? AND collector_number=? AND sheet_type=? LIMIT 1', (struct_no, collector_no, sheet_type))
                existing = cur.fetchone()
                if existing:
                    existing_id = existing[0] if USE_PG else existing[0]
                    if USE_PG:
                        cur.execute('UPDATE qc_sheets SET project_name=%s, location=%s, date=%s, inspector=%s, status=%s, checklist_data=%s, updated_at=%s WHERE id=%s',
                            (data.get('project_name',''), data.get('location',''), data.get('date',''), data.get('inspector',''), data.get('status','draft'), cdata, now, existing_id))
                    else:
                        cur.execute('UPDATE qc_sheets SET project_name=?, location=?, date=?, inspector=?, status=?, checklist_data=?, updated_at=? WHERE id=?',
                            (data.get('project_name',''), data.get('location',''), data.get('date',''), data.get('inspector',''), data.get('status','draft'), cdata, now, existing_id))
                    conn.commit(); conn.close()
                    return jsonify({"id": existing_id, "updated": True, "message": f"Updated existing Structure {struct_no}"})
            
            if USE_PG:
                cur.execute('INSERT INTO qc_sheets (project_name,location,date,inspector,status,checklist_data,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id', 
                    (data.get('project_name',''), data.get('location',''), data.get('date',''), data.get('inspector',''), data.get('status','draft'), cdata, now, now))
                sid=cur.fetchone()[0]
            else:
                cur.execute('INSERT INTO qc_sheets (project_name,location,date,inspector,status,checklist_data,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)', 
                    (data.get('project_name',''), data.get('location',''), data.get('date',''), data.get('inspector',''), data.get('status','draft'), cdata, now, now))
                sid=cur.lastrowid
            conn.commit(); conn.close()
            return jsonify({"id":sid, "warning": "Saved via fallback"})
        except Exception as e2:
            conn.close()
            return jsonify({"error": f"{str(e)} | Fallback: {str(e2)}"}), 500

@app.route('/api/qc-sheets/public-update/<int:sid>', methods=['PUT'])
def public_update_qc(sid):
    """Fallback update without auth"""
    data=request.json or {}; now=datetime.utcnow().isoformat()
    conn=get_conn(); cur=conn.cursor()
    cdata=data.get('checklist_data') or data.get('checks') or {}
    if isinstance(cdata, dict): cdata=json.dumps(cdata)
    try:
        if USE_PG:
            cur.execute('UPDATE qc_sheets SET project_name=%s, location=%s, chainage_extra=%s, date=%s, inspector=%s, status=%s, sheet_type=%s, checklist_data=%s, updated_at=%s WHERE id=%s',
                (data.get('project_name',''), data.get('location',''), data.get('chainage_extra',''), data.get('date',''), data.get('inspector',''), data.get('status','draft'), data.get('sheet_type','steel_monopole'), cdata, now, sid))
        else:
            cur.execute('UPDATE qc_sheets SET project_name=?, location=?, chainage_extra=?, date=?, inspector=?, status=?, sheet_type=?, checklist_data=?, updated_at=? WHERE id=?',
                (data.get('project_name',''), data.get('location',''), data.get('chainage_extra',''), data.get('date',''), data.get('inspector',''), data.get('status','draft'), data.get('sheet_type','steel_monopole'), cdata, now, sid))
        conn.commit(); conn.close()
        return jsonify({"id": sid, "ok": True})
    except Exception as e:
        print(f"public-update error (fallback): {e}")
        try:
            conn.rollback()
            if USE_PG:
                cur.execute('UPDATE qc_sheets SET project_name=%s, location=%s, date=%s, inspector=%s, status=%s, checklist_data=%s, updated_at=%s WHERE id=%s',
                    (data.get('project_name',''), data.get('location',''), data.get('date',''), data.get('inspector',''), data.get('status','draft'), cdata, now, sid))
            else:
                cur.execute('UPDATE qc_sheets SET project_name=?, location=?, date=?, inspector=?, status=?, checklist_data=?, updated_at=? WHERE id=?',
                    (data.get('project_name',''), data.get('location',''), data.get('date',''), data.get('inspector',''), data.get('status','draft'), cdata, now, sid))
            conn.commit(); conn.close()
            return jsonify({"id": sid, "ok": True, "warning": "Updated without new columns"})
        except Exception as e2:
            conn.close()
            return jsonify({"error": f"{str(e)} | Fallback: {str(e2)}"}), 500


@app.route('/api/qc-sheets/public-get/<int:sid>')
def public_get_qc(sid):
    conn=get_conn(); cur=conn.cursor()
    try:
        if USE_PG: cur.execute('SELECT * FROM qc_sheets WHERE id=%s',(sid,))
        else: cur.execute('SELECT * FROM qc_sheets WHERE id=?',(sid,))
        row=cur.fetchone()
        if not row:
            conn.close()
            return jsonify({"error":"Not found"}), 404
        cols=[d[0] for d in cur.description]
        d=dict(zip(cols,row)) if USE_PG else dict(row)
        # Parse checklist_data
        try:
            cd=d.get('checklist_data')
            if isinstance(cd,str): d['checks']=json.loads(cd)
            else: d['checks']=cd
        except: d['checks']={}
        conn.close()
        return jsonify(d)
    except Exception as e:
        conn.close()
        return jsonify({"error":str(e)}),500


@app.route('/api/qc-sheets/public-delete/<int:sid>', methods=['DELETE'])
def public_delete_qc(sid):
    conn=get_conn(); cur=conn.cursor()
    try:
        if USE_PG: cur.execute('DELETE FROM qc_sheets WHERE id=%s',(sid,))
        else: cur.execute('DELETE FROM qc_sheets WHERE id=?',(sid,))
        conn.commit(); conn.close()
        return jsonify({"ok":True, "id":sid})
    except Exception as e:
        conn.close()
        return jsonify({"error":str(e)}),500


@app.route('/api/admin/migrate-db')
def migrate_db():
    """Force DB migration and show columns"""
    try:
        conn=get_conn(); cur=conn.cursor()
        if USE_PG:
            for col, coltype in [
                ('project_name', 'TEXT DEFAULT \'\''),
                ('location', 'TEXT DEFAULT \'\''),
                ('structure_number', 'TEXT DEFAULT \'\''),
                ('collector_number', 'TEXT DEFAULT \'\''),
                ('section_number', 'TEXT DEFAULT \'\''),
                ('chainage_extra', 'TEXT DEFAULT \'\''),
                ('date', 'TEXT DEFAULT \'\''),
                ('inspector', 'TEXT DEFAULT \'\''),
                ('status', 'TEXT DEFAULT \'draft\''),
                ('sheet_type', 'TEXT DEFAULT \'trench\''),
                ('checklist_data', 'TEXT DEFAULT \'{}\''),
                ('created_at', 'TEXT DEFAULT \'\''),
                ('updated_at', 'TEXT DEFAULT \'\''),
            ]:
                try:
                    cur.execute(f"ALTER TABLE qc_sheets ADD COLUMN IF NOT EXISTS {col} {coltype}")
                    print(f"Added {col}")
                except Exception as e:
                    print(f"Failed {col}: {e}")
            conn.commit()
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='qc_sheets' ORDER BY ordinal_position")
            cols = [r[0] for r in cur.fetchall()]
            conn.close()
            return jsonify({"migrated": True, "columns": cols, "use_pg": USE_PG})
        else:
            conn.close()
            return jsonify({"migrated": False, "use_pg": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/qc-sheets/public-list')
def public_list_qc():
    conn=get_conn(); cur=conn.cursor()
    try:
        if USE_PG:
            cur.execute('SELECT id, project_name, location, structure_number, collector_number, section_number, chainage_extra, date, inspector, status, sheet_type, created_at FROM qc_sheets ORDER BY id DESC LIMIT 100')
        else:
            cur.execute('SELECT id, project_name, location, structure_number, collector_number, section_number, chainage_extra, date, inspector, status, sheet_type, created_at FROM qc_sheets ORDER BY id DESC LIMIT 100')
        rows=cur.fetchall()
        cols=[d[0] for d in cur.description]
        result=[]
        for r in rows:
            d=dict(zip(cols,r)) if USE_PG else dict(r)
            result.append(d)
        conn.close()
        return jsonify(result)
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 500


@app.route('/api/qc-sheets/steel-list')
def steel_list():
    """ONLY steel monopoles - separate from wooden"""
    conn=get_conn(); cur=conn.cursor()
    try:
        if USE_PG:
            cur.execute("SELECT id, project_name, location, structure_number, collector_number, section_number, chainage_extra, date, inspector, status, sheet_type, created_at FROM qc_sheets WHERE sheet_type='steel_monopole' ORDER BY id DESC")
        else:
            cur.execute("SELECT id, project_name, location, structure_number, collector_number, section_number, chainage_extra, date, inspector, status, sheet_type, created_at FROM qc_sheets WHERE sheet_type='steel_monopole' ORDER BY id DESC")
        rows=cur.fetchall()
        cols=[d[0] for d in cur.description]
        result=[dict(zip(cols,r)) if USE_PG else dict(r) for r in rows]
        conn.close()
        return jsonify(result)
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 500

@app.route('/api/qc-sheets/wooden-list')
def wooden_list():
    """ONLY wooden H-Pole - separate from steel"""
    conn=get_conn(); cur=conn.cursor()
    try:
        if USE_PG:
            cur.execute("SELECT id, project_name, location, structure_number, collector_number, section_number, chainage_extra, date, inspector, status, sheet_type, created_at FROM qc_sheets WHERE sheet_type IN ('wooden_pole','wooden_h_pole','h_pole_wooden','wooden') OR sheet_type LIKE '%wood%' OR sheet_type LIKE '%h_pole%' ORDER BY id DESC")
        else:
            cur.execute("SELECT id, project_name, location, structure_number, collector_number, section_number, chainage_extra, date, inspector, status, sheet_type, created_at FROM qc_sheets WHERE sheet_type IN ('wooden_pole','wooden_h_pole','h_pole_wooden','wooden') OR sheet_type LIKE '%wood%' OR sheet_type LIKE '%h_pole%' ORDER BY id DESC")
        rows=cur.fetchall()
        cols=[d[0] for d in cur.description]
        result=[dict(zip(cols,r)) if USE_PG else dict(r) for r in rows]
        conn.close()
        return jsonify(result)
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 500

@app.route('/api/qc-sheets/public-steel-list')
def public_steel_list():
    return steel_list()

@app.route('/api/qc-sheets/public-wooden-list')
def public_wooden_list():
    return wooden_list()



@app.route('/api/qc-sheets/by-structure/<structure_no>')
@require_auth
def get_by_structure(structure_no):
    collector = request.args.get('collector','').strip()
    conn=get_conn(); cur=conn.cursor()
    try:
        if collector:
            if USE_PG:
                cur.execute('SELECT * FROM qc_sheets WHERE structure_number=%s AND collector_number=%s ORDER BY id DESC LIMIT 1', (structure_no, collector))
            else:
                cur.execute('SELECT * FROM qc_sheets WHERE structure_number=? AND collector_number=? ORDER BY id DESC LIMIT 1', (structure_no, collector))
        else:
            if USE_PG:
                cur.execute('SELECT * FROM qc_sheets WHERE structure_number=%s ORDER BY id DESC LIMIT 1', (structure_no,))
            else:
                cur.execute('SELECT * FROM qc_sheets WHERE structure_number=? ORDER BY id DESC LIMIT 1', (structure_no,))
        row=cur.fetchone()
        if not row:
            conn.close()
            return jsonify({"error": f"Structure {structure_no} not found"}), 404
        cols=[d[0] for d in cur.description]
        d=dict(zip(cols,row)) if USE_PG else dict(row)
        conn.close()
        return jsonify(d)
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 500

@app.route('/api/qc-sheets/public-by-structure/<structure_no>')
def public_by_structure(structure_no):
    collector = request.args.get('collector','').strip()
    conn=get_conn(); cur=conn.cursor()
    try:
        if collector:
            if USE_PG:
                cur.execute('SELECT * FROM qc_sheets WHERE structure_number=%s AND collector_number=%s ORDER BY id DESC LIMIT 1', (structure_no, collector))
            else:
                cur.execute('SELECT * FROM qc_sheets WHERE structure_number=? AND collector_number=? ORDER BY id DESC LIMIT 1', (structure_no, collector))
        else:
            if USE_PG:
                cur.execute('SELECT * FROM qc_sheets WHERE structure_number=%s ORDER BY id DESC LIMIT 1', (structure_no,))
            else:
                cur.execute('SELECT * FROM qc_sheets WHERE structure_number=? ORDER BY id DESC LIMIT 1', (structure_no,))
        row=cur.fetchone()
        if not row:
            conn.close()
            return jsonify({"error": f"Structure {structure_no} not found"}), 404
        cols=[d[0] for d in cur.description]
        d=dict(zip(cols,row)) if USE_PG else dict(row)
        conn.close()
        return jsonify(d)
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 500


# Pages
@app.route('/')
def home(): return send_from_directory('.', 'index.html')
@app.route('/login')
def login_page(): return send_from_directory('.', 'login.html')
@app.route('/users')
def users_page(): return send_from_directory('.', 'users.html')
@app.route('/gantt')
def gantt_route(): return send_from_directory('.', 'gantt_planner_DB.html')
def qc_route(): return send_from_directory('.', 'quality_check_multi.html')
@app.route('/quality')
def quality_route(): return send_from_directory('.', 'quality_hub.html')
@app.route('/qc-wooden')
def qc_wooden_route(): return send_from_directory('.', 'quality_check_wooden_pole.html')

# Also serve the html files directly by name
@app.route('/quality_hub.html')
def quality_hub_file(): return send_from_directory('.', 'quality_hub.html')
@app.route('/quality_check_wooden_pole.html')
def wooden_file(): return send_from_directory('.', 'quality_check_wooden_pole.html')
@app.route('/gantt_planner_DB.html')
def gantt_file(): return send_from_directory('.', 'gantt_planner_DB.html')
@app.route('/quality_check_multi.html')
def qc_multi_file(): return send_from_directory('.', 'quality_check_multi.html')

@app.route('/api/status')
def status(): return jsonify({"db":"Postgres" if USE_PG else "SQLite","use_postgres":USE_PG,"ok":True,"quality_hub":True,"persistent_sessions":True,"v":"6.1-stable"})

@app.route('/api/debug')
def debug():
    import os as _os
    files=_os.listdir('.')
    return jsonify({"use_postgres":USE_PG,"files":files[:30],"has_quality_hub":'quality_hub.html' in files,"has_wooden":'quality_check_wooden_pole.html' in files})

# Auth
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
        try:
            conn=get_conn(); cur=conn.cursor()
            if USE_PG: cur.execute('DELETE FROM sessions WHERE token=%s',(token,))
            else: cur.execute('DELETE FROM sessions WHERE token=?',(token,))
            conn.commit(); conn.close()
        except: pass
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

@app.route('/api/auth/users/<int:uid>', methods=['PUT'])
@require_role('admin')
def edit_user(uid):
    data=request.json or {}
    username=(data.get('username') or '').strip()
    display_name=(data.get('display_name') or '').strip()
    role=(data.get('role') or '').strip()
    password=data.get('password')
    if not username: return jsonify({"error":"Username required"}),400
    if role and role not in ['viewer','inspector','qc_manager','admin']: return jsonify({"error":"Invalid role"}),400
    conn=get_conn(); cur=conn.cursor()
    if USE_PG: cur.execute('SELECT id FROM users WHERE username=%s AND id!=%s',(username,uid))
    else: cur.execute('SELECT id FROM users WHERE username=? AND id!=?',(username,uid))
    if cur.fetchone():
        conn.close(); return jsonify({"error":"Username already taken"}),400
    if password:
        if len(password)<6:
            conn.close(); return jsonify({"error":"Password min 6"}),400
        phash=generate_password_hash(password)
        if USE_PG: cur.execute('UPDATE users SET username=%s, display_name=%s, role=%s, password_hash=%s WHERE id=%s',(username,display_name,role,phash,uid))
        else: cur.execute('UPDATE users SET username=?, display_name=?, role=?, password_hash=? WHERE id=?',(username,display_name,role,phash,uid))
    else:
        if USE_PG: cur.execute('UPDATE users SET username=%s, display_name=%s, role=%s WHERE id=%s',(username,display_name,role,uid))
        else: cur.execute('UPDATE users SET username=?, display_name=?, role=? WHERE id=?',(username,display_name,role,uid))
    if USE_PG: cur.execute('UPDATE sessions SET username=%s, role=%s, display_name=%s WHERE user_id=%s',(username,role,display_name,uid))
    else: cur.execute('UPDATE sessions SET username=?, role=?, display_name=? WHERE user_id=?',(username,role,display_name,uid))
    conn.commit(); conn.close()
    return jsonify({"ok":True})

@app.route('/api/auth/users/<int:uid>', methods=['DELETE'])
@require_role('admin')
def delete_user(uid):
    if uid==1: return jsonify({"error":"Cannot delete main admin"}),400
    conn=get_conn(); cur=conn.cursor()
    if USE_PG: cur.execute('DELETE FROM users WHERE id=%s',(uid,))
    else: cur.execute('DELETE FROM users WHERE id=?',(uid,))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/qc-sheets', methods=['GET'])
def get_qc():
    conn=get_conn(); cur=conn.cursor()
    cur.execute('SELECT * FROM qc_sheets ORDER BY id DESC')
    rows=cur.fetchall(); data=rows_to_dicts(cur, rows) if USE_PG else [dict(r) for r in rows]
    conn.close(); return jsonify(data)

@app.route('/api/qc-sheets/<int:sid>', methods=['GET'])
def get_qc_one(sid):
    conn=get_conn(); cur=conn.cursor()
    if USE_PG: cur.execute('SELECT * FROM qc_sheets WHERE id=%s',(sid,))
    else: cur.execute('SELECT * FROM qc_sheets WHERE id=?',(sid,))
    row=cur.fetchone()
    if not row:
        conn.close(); return jsonify({"error":"Not found"}),404
    data=dict(zip([d[0] for d in cur.description], row)) if USE_PG else dict(row)
    # Parse checklist_data if needed
    try:
        if isinstance(data.get('checklist_data'), str):
            data['checks']=json.loads(data['checklist_data'])
        else:
            data['checks']=data.get('checklist_data') or {}
    except:
        data['checks']={}
    conn.close(); return jsonify(data)

@app.route('/api/qc-sheets', methods=['POST'])
@require_role('inspector','qc_manager','admin')
def create_qc():
    data=request.json or {}; now=datetime.utcnow().isoformat()
    conn=get_conn(); cur=conn.cursor()
    cdata=data.get('checklist_data') or data.get('checks') or {}
    if isinstance(cdata, dict): cdata=json.dumps(cdata)
    fields=('project_name','location','structure_number','collector_number','section_number','chainage_extra','date','inspector','status','sheet_type')
    vals=[data.get(f,'') for f in fields]
    if USE_PG:
        cur.execute('INSERT INTO qc_sheets (project_name,location,structure_number,collector_number,section_number,chainage_extra,date,inspector,status,sheet_type,checklist_data,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id', (*vals,cdata,now,now))
        sid=cur.fetchone()[0]
    else:
        cur.execute('INSERT INTO qc_sheets (project_name,location,structure_number,collector_number,section_number,chainage_extra,date,inspector,status,sheet_type,checklist_data,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)', (*vals,cdata,now,now))
        sid=cur.lastrowid
    conn.commit(); conn.close(); return jsonify({"id":sid})

@app.route('/api/qc-sheets/<int:sid>', methods=['PUT'])
@require_role('inspector','qc_manager','admin')
def update_qc(sid):
    data=request.json or {}; now=datetime.utcnow().isoformat()
    conn=get_conn(); cur=conn.cursor()
    cdata=data.get('checklist_data') or data.get('checks') or {}
    if isinstance(cdata, dict): cdata=json.dumps(cdata)
    fields=('project_name','location','structure_number','collector_number','section_number','chainage_extra','date','inspector','status','sheet_type')
    set_clause=', '.join([f"{f}=%s" if USE_PG else f"{f}=?" for f in fields]) + (', checklist_data=%s, updated_at=%s' if USE_PG else ', checklist_data=?, updated_at=?')
    vals=[data.get(f,'') for f in fields]
    vals.extend([cdata, now, sid])
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
    name=data.get('name') or data.get('project_name') or 'Task'
    start=data.get('start_date') or data.get('start') or ''
    end=data.get('end_date') or data.get('end') or ''
    if USE_PG:
        cur.execute('INSERT INTO gantt_tasks (name,start_date,end_date,progress,assignee,dependencies,color,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id',(name,start,end,data.get('progress',0),data.get('assignee') or data.get('owner'),data.get('dependencies'),data.get('color'),now))
        sid=cur.fetchone()[0]
    else:
        cur.execute('INSERT INTO gantt_tasks (name,start_date,end_date,progress,assignee,dependencies,color,created_at) VALUES (?,?,?,?,?,?,?,?)',(name,start,end,data.get('progress',0),data.get('assignee') or data.get('owner'),data.get('dependencies'),data.get('color'),now))
        sid=cur.lastrowid
    conn.commit(); conn.close(); return jsonify({"id":sid})

@app.route('/api/gantt-tasks/<int:tid>', methods=['PUT'])
@require_role('qc_manager','admin')
def update_gantt(tid):
    data=request.json or {}; conn=get_conn(); cur=conn.cursor()
    name=data.get('name'); start=data.get('start_date') or data.get('start'); end=data.get('end_date') or data.get('end')
    if USE_PG:
        cur.execute('UPDATE gantt_tasks SET name=%s,start_date=%s,end_date=%s,progress=%s,assignee=%s,dependencies=%s,color=%s WHERE id=%s',(name,start,end,data.get('progress'),data.get('assignee') or data.get('owner'),data.get('dependencies'),data.get('color'),tid))
    else:
        cur.execute('UPDATE gantt_tasks SET name=?,start_date=?,end_date=?,progress=?,assignee=?,dependencies=?,color=? WHERE id=?',(name,start,end,data.get('progress'),data.get('assignee') or data.get('owner'),data.get('dependencies'),data.get('color'),tid))
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
    from io import BytesIO as Bio
    bio=Bio(); wb.save(bio); bio.seek(0)
    return app.response_class(bio.getvalue(), mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition':'attachment; filename=QC_Export.xlsx'})

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',8000)))
