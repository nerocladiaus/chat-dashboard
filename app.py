from flask import Flask, render_template, request, jsonify, abort
from flask_socketio import SocketIO
import sqlite3
from datetime import datetime
import os

BASE_DIR = os.path.dirname(__file__)
DATABASE = os.path.join(BASE_DIR, 'peerconnect.db')
SECRET_KEY = 'your-secret-key'

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')
app.config['SECRET_KEY'] = SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins="*")

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
                status TEXT DEFAULT 'approved'
            )
        ''')

@app.route('/')
def index():
    with sqlite3.connect(DATABASE) as conn:
        # fetch all approved posts
        rows = conn.execute(
            "SELECT id, kiosk_id, category, content, timestamp "
            "FROM posts WHERE status='approved' ORDER BY timestamp DESC"
        ).fetchall()
        # fetch the distinct categories
        cats = conn.execute(
            "SELECT DISTINCT category FROM posts WHERE status='approved'"
        ).fetchall()

    posts = [dict(zip(
        ['id','kiosk_id','category','content','timestamp'], r
    )) for r in rows]

    # flatten category tuples → ['Academic Help', 'Lost & Found', ...]
    categories = [c[0] for c in cats]

    return render_template('index.html',
                           posts=posts,
                           categories=categories)

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    with sqlite3.connect(DATABASE) as conn:
        row = conn.execute(
            "SELECT id,kiosk_id,category,content,timestamp,status "
            "FROM posts WHERE id=?", (post_id,)
        ).fetchone()
    if not row or row[5] != 'approved':
        abort(404)
    post = dict(zip(
        ['id','kiosk_id','category','content','timestamp','status'], row
    ))
    return render_template('post_detail.html', post=post)

@app.route('/api/posts', methods=['GET'])
def get_posts():
    with sqlite3.connect(DATABASE) as conn:
        rows = conn.execute(
            "SELECT id,kiosk_id,category,content,timestamp,status "
            "FROM posts ORDER BY id DESC"
        ).fetchall()
    posts = [dict(zip(
        ['id','kiosk_id','category','content','timestamp','status'], r
    )) for r in rows]
    return jsonify(posts)

@app.route('/api/posts', methods=['POST'])
def add_post():
    data = request.get_json() or {}
    kiosk_id = data.get('kiosk_id','unknown')
    category = data.get('category','uncategorized')
    content  = data.get('content','')
    ts = datetime.utcnow().isoformat()
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO posts (kiosk_id,category,content,timestamp) "
            "VALUES (?,?,?,?)",
            (kiosk_id, category, content, ts)
        )
        post_id = c.lastrowid

    post = {
      'id': post_id,
      'kiosk_id': kiosk_id,
      'category': category,
      'content': content,
      'timestamp': ts,
      'status': 'approved'
    }

    # broadcast new post
    socketio.emit('new_post', post)
    return jsonify(post), 201

@socketio.on('connect')
def on_connect():
    print('Client connected')

if __name__ == '__main__':
    init_db()
    # only listen on your Pi’s own LAN IP
    socketio.run(app, host='127.0.0.1', port=5000)
