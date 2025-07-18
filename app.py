from flask import Flask, render_template, request, jsonify, abort
from flask_socketio import SocketIO
import sqlite3
from datetime import datetime
import os

# — Configuration —
DATABASE = os.path.join(os.path.dirname(__file__), 'peerconnect.db')
SECRET_KEY = 'your-secret-key'

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins="*")

# — Database init —
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kiosk_id TEXT,
                category TEXT,
                content TEXT,
                timestamp TEXT,
                status TEXT DEFAULT 'pending'
            )
        ''')
        # Other tables omitted for brevity—reuse previous definitions

# — Routes —
@app.route('/')
def index():
    with sqlite3.connect(DATABASE) as conn:
        rows = conn.execute(
            "SELECT id, kiosk_id, category, content, timestamp, status FROM posts WHERE status='approved' ORDER BY timestamp DESC"
        ).fetchall()
    posts = [dict(zip(['id','kiosk_id','category','content','timestamp','status'], r)) for r in rows]
    return render_template('index.html', posts=posts)

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    with sqlite3.connect(DATABASE) as conn:
        row = conn.execute(
            "SELECT id, kiosk_id, category, content, timestamp, status FROM posts WHERE id=?",
            (post_id,)
        ).fetchone()
    if not row or row[5] != 'approved':
        abort(404)
    post = dict(zip(['id','kiosk_id','category','content','timestamp','status'], row))
    return render_template('post_detail.html', post=post)

# Include existing API endpoints and SocketIO handlers here...
# — Main entrypoint —
if __name__ == '__main__':
    init_db()
    socketio.run(app, host='0.0.0.0', port=5000)