import os
from flask import Flask, jsonify, send_from_directory
app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/')
def root(): return send_from_directory('templates', 'login.html')
@app.route('/index.html')
def index_page(): return send_from_directory('templates', 'index.html')
@app.route('/login.html')
def login_page(): return send_from_directory('templates', 'login.html')
@app.route('/static/<path:path>')
def static_files(path): return send_from_directory('static', path)
@app.route('/projecttrack.css')
def css_root(): return send_from_directory('static', 'projecttrack.css')
@app.route('/health')
def health(): return jsonify({"status":"ok","step":"STEP1_FIXED","db":"none"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)