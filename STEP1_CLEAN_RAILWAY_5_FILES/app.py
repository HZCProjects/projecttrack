import os
from flask import Flask, send_from_directory, jsonify

app = Flask(__name__)

# STEP 1 - Clean Base - Only dashboard, no QC, no Map, no Datalogs - No mojis
# Routes for Step 1
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/index.html')
def index_file():
    return send_from_directory('.', 'index.html')

@app.route('/projecttrack.css')
def css():
    return send_from_directory('.', 'projecttrack.css')

@app.route('/health')
def health():
    return jsonify({"status": "ok", "step": "STEP 1 - Dashboard Base", "mojis": "none", "sidebar": "yes", "colors": "#383C40 + #B2B2B2", "version": "step1_clean"})

@app.route('/api/health')
def api_health():
    return jsonify({"status": "ok", "step": 1, "message": "Step 1 clean base - dashboard only"})

# Future steps will add routes here
# Step 2: /quality
# Step 3: /qc-wooden
# Step 4: /qc-multi
# Step 5: /qc-conductor
# Step 6: /datalogs, /structures, /map
# Step 7: /users, /kanban, /gantt

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
