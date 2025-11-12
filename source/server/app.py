from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3
import os
import uuid
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import json
import hashlib

# Sửa đường dẫn templates để tìm thư mục templates từ root project
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
template_dir = os.path.join(project_root, 'templates')
upload_dir = os.path.join(project_root, 'uploads')

app = Flask(__name__, template_folder=template_dir)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = upload_dir
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Debug paths
print(f"🔍 Project root: {project_root}")
print(f"📁 Template directory: {template_dir}")
print(f"📂 Upload directory: {upload_dir}")
print(f"📄 Template exists: {os.path.exists(template_dir)}")
print(f"📄 Index.html exists: {os.path.exists(os.path.join(template_dir, 'index.html'))}")
print(f"📂 Upload folder exists: {os.path.exists(upload_dir)}")

# Database initialization with password support
# Database path for Render
DATABASE_PATH = '/tmp/chat_app.db'

def init_db():
    """Initialize database tables"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER,
            content TEXT,
            message_type TEXT DEFAULT 'text',
            file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
print("🔍 Initializing database...")
init_db()
print("✅ Database ready")

# Sửa tất cả sqlite3.connect thành:
# conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, password_hash):
    """Verify password against hash"""
    return hash_password(password) == password_hash

# Connected users với thời gian last seen
connected_users = {}
user_last_seen = {}

# EMERGENCY TEST ROUTE
@app.route('/working')
def working():
    return "<h1>🎉 APP.PY WORKS!</h1><p>Original app is working!</p>"

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        return f"<h1>Template Error:</h1><p>{str(e)}</p><p>Template dir: {app.template_folder}</p>"

@app.route('/chat')
def chat():
    try:
        return render_template('chat.html')
    except Exception as e:
        return f"<h1>Chat Template Error:</h1><p>{str(e)}</p>"

@app.route('/api/register', methods=['POST'])
def register_user():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        conn = sqlite3.connect('messenger.db')
        cursor = conn.cursor()
        
        try:
            password_hash = hash_password(password)
            cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', 
                          (username, password_hash))
            user_id = cursor.lastrowid
            conn.commit()
            print(f"✅ User registered: {username} (ID: {user_id})")
            return jsonify({'user_id': user_id, 'username': username})
        except sqlite3.IntegrityError:
            return jsonify({'error': 'Username already exists'}), 400
        finally:
            conn.close()
            
    except Exception as e:
        print(f"❌ Register error: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/login', methods=['POST'])
def login_user():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        conn = sqlite3.connect('messenger.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT id, username, password_hash FROM users WHERE username = ?', 
                          (username,))
            user = cursor.fetchone()
            
            if user and verify_password(password, user[2]):
                print(f"✅ User logged in: {username} (ID: {user[0]})")
                return jsonify({'user_id': user[0], 'username': user[1]})
            else:
                return jsonify({'error': 'Invalid username or password'}), 401
        finally:
            conn.close()
            
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/users')
def get_users():
    try:
        conn = sqlite3.connect('messenger.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, username FROM users')
        users_data = cursor.fetchall()
        conn.close()
        
        users = []
        for user_data in users_data:
            user_id, username = user_data
            is_online = user_id in connected_users
            last_seen = user_last_seen.get(user_id, datetime.now().isoformat())
            
            users.append({
                'id': user_id,
                'username': username,
                'status': 'online' if is_online else 'offline',
                'last_seen': last_seen
            })
        
        return jsonify(users)
    except Exception as e:
        print(f"❌ Get users error: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/messages/<int:user1_id>/<int:user2_id>')
def get_messages(user1_id, user2_id):
    try:
        conn = sqlite3.connect('messenger.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT m.id, m.sender_id, m.receiver_id, m.content, m.message_type, 
                   m.file_path, m.created_at, u.username
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE (m.sender_id = ? AND m.receiver_id = ?) 
               OR (m.sender_id = ? AND m.receiver_id = ?)
            ORDER BY m.created_at ASC
        ''', (user1_id, user2_id, user2_id, user1_id))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                'id': row[0],
                'sender_id': row[1],
                'receiver_id': row[2],
                'content': row[3],
                'message_type': row[4],
                'file_path': row[5],
                'created_at': row[6],
                'sender_name': row[7]
            })
        
        conn.close()
        return jsonify(messages)
    except Exception as e:
        print(f"❌ Get messages error: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file:
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            print(f"📤 Uploading file: {filename}")
            print(f"💾 Saving to: {file_path}")
            
            try:
                file.save(file_path)
                print(f"✅ File saved successfully: {file_path}")
                print(f"📄 File exists after save: {os.path.exists(file_path)}")
                return jsonify({'file_path': unique_filename})
            except Exception as e:
                print(f"❌ Error saving file: {str(e)}")
                return jsonify({'error': f'Failed to save file: {str(e)}'}), 500
                
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    try:
        print(f"🔍 Requesting file: {filename}")
        print(f"📂 Upload folder: {app.config['UPLOAD_FOLDER']}")
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        print(f"📄 Full path: {file_path}")
        print(f"📄 File exists: {os.path.exists(file_path)}")
        
        if os.path.exists(file_path):
            return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
        else:
            print(f"❌ File not found: {file_path}")
            return "File not found", 404
    except Exception as e:
        print(f"❌ File serve error: {str(e)}")
        return f"Error: {str(e)}", 500

# Socket.IO events
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')
    # Remove user from connected_users and update last seen
    for user_id, sid in list(connected_users.items()):
        if sid == request.sid:
            del connected_users[user_id]
            user_last_seen[user_id] = datetime.now().isoformat()
            # Broadcast user offline status
            emit('user_status_changed', {
                'user_id': user_id, 
                'status': 'offline',
                'last_seen': user_last_seen[user_id]
            }, broadcast=True)
            break

@socketio.on('join')
def handle_join(data):
    user_id = data['user_id']
    connected_users[user_id] = request.sid
    user_last_seen[user_id] = datetime.now().isoformat()
    
    # Broadcast user online status
    emit('user_status_changed', {
        'user_id': user_id, 
        'status': 'online',
        'last_seen': user_last_seen[user_id]
    }, broadcast=True)

@socketio.on('send_message')
def handle_message(data):
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']
    content = data['content']
    message_type = data.get('message_type', 'text')
    file_path = data.get('file_path')
    
    # Save to database
    conn = sqlite3.connect('messenger.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO messages (sender_id, receiver_id, content, message_type, file_path)
        VALUES (?, ?, ?, ?, ?)
    ''', (sender_id, receiver_id, content, message_type, file_path))
    message_id = cursor.lastrowid
    
    # Get sender name
    cursor.execute('SELECT username FROM users WHERE id = ?', (sender_id,))
    sender_result = cursor.fetchone()
    sender_name = sender_result[0] if sender_result else f'User {sender_id}'
    
    conn.commit()
    conn.close()
    
    # Send to specific user if online
    if receiver_id in connected_users:
        emit('new_message', {
            'id': message_id,
            'sender_id': sender_id,
            'receiver_id': receiver_id,
            'content': content,
            'message_type': message_type,
            'file_path': file_path,
            'sender_name': sender_name,  # Add sender name
            'created_at': datetime.now().isoformat()
        }, room=connected_users[receiver_id])

# WebRTC signaling events
@socketio.on('offer')
def handle_offer(data):
    emit('offer', data, broadcast=True, include_self=False)

@socketio.on('answer')
def handle_answer(data):
    emit('answer', data, broadcast=True, include_self=False)

@socketio.on('ice-candidate')
def handle_candidate(data):
    emit('ice-candidate', data, broadcast=True, include_self=False)

@socketio.on('call_user')
def handle_call_user(data):
    receiver_id = data['receiver_id']
    if receiver_id in connected_users:
        emit('incoming_call', data, room=connected_users[receiver_id])

@socketio.on('call_accepted')
def handle_call_accepted(data):
    caller_id = data['caller_id']
    if caller_id in connected_users:
        emit('call_accepted', data, room=connected_users[caller_id])

@socketio.on('call_rejected')
def handle_call_rejected(data):
    caller_id = data['caller_id']
    if caller_id in connected_users:
        emit('call_rejected', data, room=connected_users[caller_id])

if __name__ == '__main__':
    print("🚀 Starting main chat app...")
    init_db()
    
    # Get port from environment (Render provides PORT env var)
    port = int(os.environ.get('PORT', 5001))
    
    # Run with gunicorn-compatible settings for production
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
