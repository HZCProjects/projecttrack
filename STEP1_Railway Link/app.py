import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def root():
    return """
<!DOCTYPE html><html><head><meta charset="UTF-8"><title>STEP1 ULTRA</title>
<style>body{font-family:Arial;background:#383C40;color:#fff;padding:40px} .card{background:#fff;color:#383C40;padding:24px;border-radius:10px;max-width:600px} a{color:#383C40}</style>
</head><body><div class="card"><h1>HZC Projects - STEP1 ULTRA - BUILD GREEN</h1><p>No Procfile, No nixpacks, No runtime - Auto detect</p><p><a href='/health'>/health</a> - should return ok</p><p id='out'></p></div>
<script>fetch('/health').then(r=>r.json()).then(j=>document.getElementById('out').innerText=JSON.stringify(j))</script>
</body></html>
"""

@app.route('/health')
def health():
    return jsonify({"status":"ok","step":"STEP1_ULTRA_BUILD_GREEN"})

# Railway injects PORT - Flask must listen on it
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)