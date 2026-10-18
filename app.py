from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3, os, json
from datetime import datetime

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)
DB = 'projecttrack.db'

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS qc_sheets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name TEXT,
        location TEXT,
        date TEXT,
        inspector TEXT,
        status TEXT DEFAULT 'draft',
        checks_json TEXT,
        created_at TEXT,
        updated_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS gantt_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, start TEXT, end TEXT, progress INTEGER, color TEXT, owner TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index(): return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(path): return send_from_directory('.', path)
    return send_from_directory('.', 'index.html')

# --- QC Sheets API ---
@app.route('/api/qc-sheets', methods=['GET'])
def list_qc():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM qc_sheets ORDER BY updated_at DESC')
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    # parse checks
    for r in rows:
        try: r['checks'] = json.loads(r['checks_json'] or '{}')
        except: r['checks'] = {}
    return jsonify(rows)

@app.route('/api/qc-sheets', methods=['POST'])
def create_qc():
    data = request.json
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    c.execute('INSERT INTO qc_sheets (project_name, location, date, inspector, status, checks_json, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)',
              (data.get('project_name',''), data.get('location',''), data.get('date',''), data.get('inspector','HZC QC Team'), data.get('status','draft'), json.dumps(data.get('checks',{})), now, now))
    conn.commit()
    sid = c.lastrowid
    conn.close()
    return jsonify({"id": sid, "message": "created"})

@app.route('/api/qc-sheets/<int:sid>', methods=['GET'])
def get_qc(sid):
    conn = sqlite3.connect(DB); conn.row_factory = sqlite3.Row; c=conn.cursor()
    c.execute('SELECT * FROM qc_sheets WHERE id=?', (sid,))
    r=c.fetchone(); conn.close()
    if not r: return jsonify({"error":"not found"}), 404
    d=dict(r)
    d['checks']=json.loads(d['checks_json'] or '{}')
    return jsonify(d)

@app.route('/api/qc-sheets/<int:sid>', methods=['PUT'])
def update_qc(sid):
    data = request.json
    conn = sqlite3.connect(DB); c=conn.cursor()
    now = datetime.utcnow().isoformat()
    c.execute('UPDATE qc_sheets SET project_name=?, location=?, date=?, inspector=?, status=?, checks_json=?, updated_at=? WHERE id=?',
              (data.get('project_name'), data.get('location'), data.get('date'), data.get('inspector'), data.get('status','draft'), json.dumps(data.get('checks',{})), now, sid))
    conn.commit(); conn.close()
    return jsonify({"message":"updated"})

@app.route('/api/qc-sheets/<int:sid>', methods=['DELETE'])
def delete_qc(sid):
    conn=sqlite3.connect(DB); c=conn.cursor(); c.execute('DELETE FROM qc_sheets WHERE id=?',(sid,)); conn.commit(); conn.close()
    return jsonify({"message":"deleted"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 4002))
    app.run(host='0.0.0.0', port=port)
