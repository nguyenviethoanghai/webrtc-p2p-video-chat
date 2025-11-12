from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3
import os
import uuid
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import json
import hashlib
import threading
import time

# Sửa đường dẫn templates để tìm thư mục templates từ root project
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
template_dir = os.path.join(project_root, 'templates')
upload_dir = os.path.join(project_root, 'uploads')

app = Flask(__name__, template_folder=template_dir)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = upload_dir
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Tối ưu SocketIO cho hosting miễn phí
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode='threading',
    ping_interval=25,  # Giảm ping interval
    ping_timeout=20,   # Giảm timeout
    logger=False,      # Tắt debug log để tăng performance
    engineio_logger=False
)

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

def ensure_db_exists():
    """Ensure database exists and is initialized"""
    try:
        # Check if database file exists
        if not os.path.exists(DATABASE_PATH):
            print(f"🔧 Database doesn't exist, creating: {DATABASE_PATH}")
        
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
        print("✅ Database tables ensured")
        return True
    except Exception as e:
        print(f"❌ Database initialization error: {str(e)}")
        return False

def init_db():
    """Initialize database tables"""
    return ensure_db_exists()

# Initialize database on startup
print("🔍 Initializing database...")
init_db()
print("✅ Database ready")

# Connection pool để tối ưu database - Move this BEFORE usage
db_lock = threading.Lock()

def get_db_connection():
    """Get database connection with optimization"""
    conn = sqlite3.connect(DATABASE_PATH, 
                          check_same_thread=False,
                          timeout=10,  # Timeout cho connection
                          isolation_level=None)  # Autocommit mode
    conn.row_factory = sqlite3.Row  # Enable dict-like access
    return conn

# Message queue để handle tin nhắn khi disconnect
pending_messages = {}
message_lock = threading.Lock()

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
        # Ensure database exists
        if not ensure_db_exists():
            return jsonify({'error': 'Database initialization failed'}), 500
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        # Tối ưu database operation
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                password_hash = hash_password(password)
                cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', 
                              (username, password_hash))
                user_id = cursor.lastrowid
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
        # Ensure database exists
        if not ensure_db_exists():
            return jsonify({'error': 'Database initialization failed'}), 500
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        # Tối ưu database operation
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('SELECT id, username, password_hash FROM users WHERE username = ?', 
                              (username,))
                user = cursor.fetchone()
                
                if user and verify_password(password, user['password_hash']):
                    print(f"✅ User logged in: {username} (ID: {user['id']})")
                    return jsonify({'user_id': user['id'], 'username': user['username']})
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
        # Ensure database exists
        if not ensure_db_exists():
            return jsonify({'error': 'Database initialization failed'}), 500
            
        # Use optimized connection
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, username FROM users')
            users_data = cursor.fetchall()
            conn.close()
        
        users = []
        for user_data in users_data:
            user_id = user_data['id']
            username = user_data['username']
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
        # Ensure database exists
        if not ensure_db_exists():
            return jsonify({'error': 'Database initialization failed'}), 500
            
        # Tối ưu query với limit để giảm tải
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT m.id, m.sender_id, m.receiver_id, m.content, m.message_type, 
                       m.file_path, m.created_at, u.username
                FROM messages m
                JOIN users u ON m.sender_id = u.id
                WHERE (m.sender_id = ? AND m.receiver_id = ?) 
                   OR (m.sender_id = ? AND m.receiver_id = ?)
                ORDER BY m.created_at DESC
                LIMIT ? OFFSET ?
            ''', (user1_id, user2_id, user2_id, user1_id, limit, offset))
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'id': row['id'],
                    'sender_id': row['sender_id'],
                    'receiver_id': row['receiver_id'],
                    'content': row['content'],
                    'message_type': row['message_type'],
                    'file_path': row['file_path'],
                    'created_at': row['created_at'],
                    'sender_name': row['username']
                })
            
            conn.close()
            # Reverse để có thứ tự từ cũ đến mới
            return jsonify(list(reversed(messages)))
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

def deliver_pending_messages(user_id):
    """Deliver pending messages when user comes online"""
    with message_lock:
        if user_id in pending_messages:
            messages_to_deliver = pending_messages[user_id].copy()
            del pending_messages[user_id]
            print(f"Delivering {len(messages_to_deliver)} pending messages to user {user_id}")
            
            for message in messages_to_deliver:
                if user_id in connected_users:
                    emit('new_message', message, room=connected_users[user_id])

# Socket.IO events
@socketio.on('ping')
def handle_ping():
    emit('pong')

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')
    emit('connected', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')
    # Remove user from connected_users and update last seen
    for user_id, sid in list(connected_users.items()):
        if sid == request.sid:
            del connected_users[user_id]
            user_last_seen[user_id] = datetime.now().isoformat()
            
            # Deliver pending messages if any
            deliver_pending_messages(user_id)
            
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
    
    print(f"User {user_id} joined with sid {request.sid}")
    
    # Deliver any pending messages
    deliver_pending_messages(user_id)
    
    # Broadcast user online status
    emit('user_status_changed', {
        'user_id': user_id, 
        'status': 'online',
        'last_seen': user_last_seen[user_id]
    }, broadcast=True)

@socketio.on('send_message')
def handle_message(data):
    try:
        # Ensure database exists
        if not ensure_db_exists():
            emit('error', {'message': 'Database not available'})
            return
            
        sender_id = data['sender_id']
        receiver_id = data['receiver_id']
        content = data['content']
        message_type = data.get('message_type', 'text')
        file_path = data.get('file_path')
        client_message_id = data.get('client_message_id')  # For client-side tracking
        
        # Immediately acknowledge receipt
        emit('message_received', {'client_message_id': client_message_id})
        
        # Save to database with optimization
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO messages (sender_id, receiver_id, content, message_type, file_path)
                VALUES (?, ?, ?, ?, ?)
            ''', (sender_id, receiver_id, content, message_type, file_path))
            message_id = cursor.lastrowid
            
            # Get sender name
            cursor.execute('SELECT username FROM users WHERE id = ?', (sender_id,))
            sender_result = cursor.fetchone()
            sender_name = sender_result['username'] if sender_result else f'User {sender_id}'
            
            conn.close()
        
        message_data = {
            'id': message_id,
            'sender_id': sender_id,
            'receiver_id': receiver_id,
            'content': content,
            'message_type': message_type,
            'file_path': file_path,
            'sender_name': sender_name,
            'created_at': datetime.now().isoformat(),
            'client_message_id': client_message_id
        }
        
        # Send to receiver if online, otherwise store as pending
        if receiver_id in connected_users:
            emit('new_message', message_data, room=connected_users[receiver_id])
            print(f"Message delivered to online user {receiver_id}")
        else:
            # Store as pending message
            with message_lock:
                if receiver_id not in pending_messages:
                    pending_messages[receiver_id] = []
                pending_messages[receiver_id].append(message_data)
            print(f"Message stored as pending for offline user {receiver_id}")
        
        # Confirm delivery to sender
        emit('message_delivered', {
            'message_id': message_id,
            'client_message_id': client_message_id,
            'delivered_at': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Send message error: {str(e)}")
        emit('error', {
            'message': 'Failed to send message',
            'client_message_id': data.get('client_message_id')
        })

# Message status tracking
@socketio.on('message_read')
def handle_message_read(data):
    """Handle when a message is read"""
    message_id = data.get('message_id')
    reader_id = data.get('user_id')
    
    # Broadcast read status to sender if online
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT sender_id FROM messages WHERE id = ?', (message_id,))
            result = cursor.fetchone()
            
            if result and result['sender_id'] in connected_users:
                emit('message_read_status', {
                    'message_id': message_id,
                    'read_by': reader_id,
                    'read_at': datetime.now().isoformat()
                }, room=connected_users[result['sender_id']])
            
            conn.close()
    except Exception as e:
        print(f"❌ Message read error: {str(e)}")

# Connection recovery
@socketio.on('recover_connection')
def handle_recover_connection(data):
    """Handle connection recovery"""
    user_id = data['user_id']
    last_message_id = data.get('last_message_id', 0)
    
    # Rejoin user
    connected_users[user_id] = request.sid
    user_last_seen[user_id] = datetime.now().isoformat()
    
    # Send any missed messages
    try:
        with db_lock:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT m.id, m.sender_id, m.receiver_id, m.content, m.message_type, 
                       m.file_path, m.created_at, u.username
                FROM messages m
                JOIN users u ON m.sender_id = u.id
                WHERE m.receiver_id = ? AND m.id > ?
                ORDER BY m.created_at ASC
                LIMIT 20
            ''', (user_id, last_message_id))
            
            missed_messages = []
            for row in cursor.fetchall():
                missed_messages.append({
                    'id': row['id'],
                    'sender_id': row['sender_id'],
                    'receiver_id': row['receiver_id'],
                    'content': row['content'],
                    'message_type': row['message_type'],
                    'file_path': row['file_path'],
                    'created_at': row['created_at'],
                    'sender_name': row['username']
                })
            
            conn.close()
            
            if missed_messages:
                emit('missed_messages', {'messages': missed_messages})
                
    except Exception as e:
        print(f"❌ Recovery error: {str(e)}")
    
    # Deliver pending messages
    deliver_pending_messages(user_id)

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
    print("🚀 Starting optimized chat app...")
    init_db()
    
    # Get port from environment (Render provides PORT env var)
    port = int(os.environ.get('PORT', 5001))
    
    # Run with optimized settings for free hosting
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=port, 
        debug=False,
        use_reloader=False,
        log_output=False  # Reduce logging overhead
    )
