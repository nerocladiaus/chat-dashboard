# app.py
import os
import time
import sqlite3
import atexit
from datetime import datetime

from flask import (
    Flask, render_template, request,
    jsonify, abort, make_response,
    redirect, url_for
)
from flask_socketio import SocketIO

import board
import adafruit_dht

# — Configuration —
BASE_DIR = os.path.dirname(__file__)
DATABASE = os.path.join(BASE_DIR, 'peerconnect.db')
SECRET_KEY = 'your-secret-key'

# DHT sensor on BCM4 / physical pin 7
DHT_PIN    = board.D4
DHT_DEVICE = adafruit_dht.DHT11(DHT_PIN)

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')
app.config['SECRET_KEY'] = SECRET_KEY

socketio = SocketIO(app, cors_allowed_origins="*")

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin']  = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return response

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        # existing posts table
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
        # new comments table
        c.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER,
                user TEXT,
                comment TEXT,
                timestamp TEXT,
                FOREIGN KEY(post_id) REFERENCES posts(id)
            )
        ''')
        conn.commit()

@app.route('/')
def index():
    with sqlite3.connect(DATABASE) as conn:
        rows = conn.execute(
            "SELECT id, kiosk_id, category, content, timestamp "
            "FROM posts WHERE status='approved' ORDER BY timestamp DESC"
        ).fetchall()
        cats = conn.execute(
            "SELECT DISTINCT category FROM posts WHERE status='approved'"
        ).fetchall()

    posts = [dict(zip(['id','kiosk_id','category','content','timestamp'], r))
             for r in rows]
    categories = [c[0] for c in cats]
    return render_template('index.html',
                           posts=posts,
                           categories=categories)


@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
def post_detail(post_id):
    with sqlite3.connect(DATABASE) as conn:
        # Handle new comment submission
        if request.method == 'POST':
            user = request.form.get('user', 'Anonymous').strip() or 'Anonymous'
            comment_text = request.form['comment'].strip()
            ts = datetime.utcnow().isoformat()
            conn.execute(
                "INSERT INTO comments (post_id,user,comment,timestamp) "
                "VALUES (?,?,?,?)",
                (post_id, user, comment_text, ts)
            )
            conn.commit()
            return redirect(url_for('post_detail', post_id=post_id))

        # Fetch the post
        row = conn.execute(
            "SELECT id,kiosk_id,category,content,timestamp,status "
            "FROM posts WHERE id=?", (post_id,)
        ).fetchone()
        if not row or row[5] != 'approved':
            abort(404)
        post = dict(zip(
            ['id','kiosk_id','category','content','timestamp','status'], row
        ))

        # Fetch comments for this post
        comment_rows = conn.execute(
            "SELECT user,comment,timestamp "
            "FROM comments WHERE post_id=? ORDER BY timestamp DESC",
            (post_id,)
        ).fetchall()
    comments = [
        dict(zip(['user','comment','timestamp'], cr))
        for cr in comment_rows
    ]

    return render_template('post_detail.html',
                           post=post,
                           comments=comments)


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
    kiosk_id = data.get('kiosk_id', 'unknown')
    category = data.get('category', 'uncategorized')
    content  = data.get('content', '')
    ts       = datetime.utcnow().isoformat()

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
    socketio.emit('new_post', post)
    return jsonify(post), 201


@app.route('/api/temperature', methods=['GET', 'OPTIONS'])
def get_temperature():
    if request.method == 'OPTIONS':
        return make_response(('', 204))

    for _ in range(3):
        try:
            t = DHT_DEVICE.temperature
            break
        except RuntimeError:
            time.sleep(1)
    else:
        return jsonify({'temperature': None}), 503

    return jsonify({'temperature': t}), 200


@socketio.on('connect')
def on_connect():
    print('Client connected')


@atexit.register
def cleanup_sensor():
    try:
        DHT_DEVICE.exit()
    except Exception:
        pass


if __name__ == '__main__':
    init_db()
    socketio.run(app, host='192.168.1.7', port=5000)
