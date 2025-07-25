import os
import sqlite3
from datetime import datetime
from threading import Lock
from time import sleep

from flask import Flask, render_template, request, jsonify, abort
from flask_socketio import SocketIO

import board
import adafruit_dht

# — Configuration —
BASE_DIR = os.path.dirname(__file__)
DATABASE = os.path.join(BASE_DIR, 'peerconnect.db')
SECRET_KEY = os.environ.get('FLASK_SECRET', 'dev-key')

# DHT11 on BCM4 (physical pin 7)
DHT_DEVICE = adafruit_dht.DHT11(board.D4)

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins="*")

# Shared cache + lock
temp_lock = Lock()
last_temp = None

def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('''
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
        rows = conn.execute(
            "SELECT id,kiosk_id,category,content,timestamp "
            "FROM posts WHERE status='approved' ORDER BY timestamp DESC"
        ).fetchall()
        cats = conn.execute(
            "SELECT DISTINCT category FROM posts WHERE status='approved'"
        ).fetchall()
    posts      = [dict(zip(['id','kiosk_id','category','content','timestamp'],r)) for r in rows]
    categories = [c[0] for c in cats]
    return render_template('index.html', posts=posts, categories=categories)

@app.route('/api/posts', methods=['POST'])
def add_post():
    data     = request.get_json() or {}
    kiosk_id = data.get('kiosk_id','unknown')
    cat      = data.get('category','uncategorized')
    cont     = data.get('content','')
    ts       = datetime.utcnow().isoformat()
    with sqlite3.connect(DATABASE) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO posts (kiosk_id,category,content,timestamp) VALUES (?,?,?,?)",
            (kiosk_id,cat,cont,ts)
        )
        post_id = cur.lastrowid
    post = dict(id=post_id, kiosk_id=kiosk_id,
                category=cat,   content=cont,
                timestamp=ts,   status='approved')
    socketio.emit('new_post', post)
    return jsonify(post), 201

@app.route('/api/temperature')
def get_temperature():
    with temp_lock:
        t = last_temp
    if t is None:
        return jsonify({'temperature': None}), 503
    return jsonify({'temperature': t})

@socketio.on('connect')
def on_connect():
    app.logger.info("Client connected")

def temperature_updater():
    global last_temp
    while True:
        try:
            t = DHT_DEVICE.temperature
            if t is not None:
                with temp_lock:
                    last_temp = round(t,1)
            else:
                app.logger.warning("DHT returned None")
        except Exception as e:
            app.logger.warning("DHT read failed: %s", e)
        sleep(10)

if __name__ == '__main__':
    init_db()
    socketio.start_background_task(temperature_updater)
    socketio.run(app, host='192.168.1.7', port=5000, debug=True)
