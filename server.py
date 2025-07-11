import os
import sqlite3
from flask import Flask, render_template, request, jsonify, g
from flask_socketio import SocketIO, join_room

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["DATABASE"] = os.path.join(app.root_path, "chat.db")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "devkey")

socketio = SocketIO(app, cors_allowed_origins="*")

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"], detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def teardown(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.execute(
        "CREATE TABLE IF NOT EXISTS chats ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  name TEXT NOT NULL"
        ");"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS messages ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  chat_id INTEGER NOT NULL,"
        "  user TEXT NOT NULL,"
        "  text TEXT NOT NULL,"
        "  ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"  
        "  FOREIGN KEY(chat_id) REFERENCES chats(id)"
        ");"
    )
    db.commit()

# initialize DB once
def setup():
    with app.app_context():
        init_db()
setup()

# Socket.IO: handle room joins
@socketio.on('join')
def handle_join(data):
    room = f"chat_{data['chat_id']}"
    join_room(room)

# Routes
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/chat/<int:chat_id>')
def chat_page(chat_id):
    return render_template('chat.html', chat_id=chat_id)

# API: list/create chats
@app.route('/api/chats', methods=['GET','POST'])
def api_chats():
    db = get_db()
    if request.method == 'POST':
        name = request.json.get('name','').strip()
        if not name:
            return jsonify(error='Chat name required'),400
        cur = db.execute('INSERT INTO chats(name) VALUES(?)', (name,))
        db.commit()
        return jsonify(id=cur.lastrowid, name=name),201
    rows = db.execute('SELECT id,name FROM chats').fetchall()
    return jsonify([dict(r) for r in rows])

# API: list & post messages per chat
@app.route('/api/chats/<int:chat_id>/messages', methods=['GET','POST'])
def api_messages(chat_id):
    db = get_db()
    if request.method == 'POST':
        data = request.get_json()
        user, text = data.get('user','').strip(), data.get('text','').strip()
        if not user or not text:
            return jsonify(error='Both user and text are required'),400
        cur = db.execute(
            'INSERT INTO messages(chat_id,user,text) VALUES(?,?,?)',
            (chat_id,user,text)
        )
        db.commit()
        msg = {'id':cur.lastrowid,'chat_id':chat_id,'user':user,'text':text,'ts':None}
        room = f"chat_{chat_id}"
        socketio.emit('new_message', msg, room=room)
        return jsonify(msg),201
    rows = db.execute(
        'SELECT id, user, text, ts FROM messages WHERE chat_id=? ORDER BY ts',
        (chat_id,)
    ).fetchall()
    return jsonify([dict(r) for r in rows])

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)