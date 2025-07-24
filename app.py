import os
import shutil
import subprocess
import threading
import uuid
from flask import Flask, request, render_template, send_from_directory, jsonify, session
from flask_session import Session

app = Flask(__name__)

# --- Config ---
app.secret_key = 'supersecretkey'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

ROOT_DIR = 'downloads'
LOG_DIR = 'logs'

os.makedirs(ROOT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

def run_lncrawl(novel_url, user_id):
    user_dir = os.path.join(ROOT_DIR, user_id)
    epub_dir = os.path.join(user_dir, 'epub')
    log_file = os.path.join(LOG_DIR, f'{user_id}.log')

    if os.path.exists(epub_dir):
        shutil.rmtree(epub_dir)
    os.makedirs(epub_dir, exist_ok=True)

    with open(log_file, 'w') as f:
        f.write("\U0001F4E5 Starting download...\n")

    cmd = [
        'lncrawl',
        '-s', novel_url,
        '-o', user_dir,
        '--format', 'epub',
        '--suppress',
        '--close-directly'
    ]

    with open(log_file, 'a') as log:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            log.write(line)
            log.flush()

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())

    user_id = session['user_id']
    epub_dir = os.path.join(ROOT_DIR, user_id, 'epub')
    epub_files = []

    if os.path.exists(epub_dir):
        epub_files = sorted([f for f in os.listdir(epub_dir) if f.endswith('.epub')])

    if request.method == 'POST':
        novel_url = request.form.get('novel_url', '').strip()
        if not novel_url.startswith("http"):
            return render_template('index.html', submitted=False, message="❌ Invalid URL!", epub_files=epub_files)

        threading.Thread(target=run_lncrawl, args=(novel_url, user_id)).start()
        return render_template('index.html', submitted=True, epub_files=epub_files)

    return render_template('index.html', submitted=False, epub_files=epub_files)

@app.route('/progress')
def progress():
    user_id = session.get('user_id')
    log_file = os.path.join(LOG_DIR, f'{user_id}.log')

    if os.path.exists(log_file):
        with open(log_file) as f:
            return jsonify({'log': ''.join(f.readlines()[-30:])})
    return jsonify({'log': ''})

@app.route('/list-epubs')
def list_epubs():
    user_id = session.get('user_id')
    epub_dir = os.path.join(ROOT_DIR, user_id, 'epub')
    if os.path.exists(epub_dir):
        epub_files = sorted([f"{user_id}/epub/{f}" for f in os.listdir(epub_dir) if f.endswith('.epub')])
        return jsonify({'files': epub_files})
    return jsonify({'files': []})

@app.route('/downloads/<user_id>/epub/<filename>')
def serve_epub(user_id, filename):
    epub_dir = os.path.join(ROOT_DIR, user_id, 'epub')
    return send_from_directory(epub_dir, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)

