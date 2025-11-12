import sqlite3
import os
from datetime import datetime

def view_database():
    """View all data in messenger.db"""
    db_path = 'messenger.db'
    
    print(f"🔍 Looking for database at: {os.path.abspath(db_path)}")
    print(f"📁 Current working directory: {os.getcwd()}")
    
    if not os.path.exists(db_path):
        print("❌ Database file NOT FOUND!")
        print("🔧 Solutions:")
        print("1. Run the server first: python source/server/app.py")
        print("2. Or create test database with option 3")
        input("\nPress Enter to continue...")
        return
    
    print(f"✅ Database file found! Size: {os.path.getsize(db_path)} bytes")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n" + "="*60)
        print("🗃️  MESSENGER DATABASE VIEWER")
        print("="*60)
        
        # Check SQLite version
        cursor.execute("SELECT sqlite_version()")
        version = cursor.fetchone()[0]
        print(f"📊 SQLite Version: {version}")
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        print(f"📋 Tables found: {table_names}")
        
        if not tables:
            print("\n⚠️  No tables found! Database is empty.")
            print("🔧 Run the server first to create tables.")
            input("\nPress Enter to continue...")
            return
        
        print("\n" + "-"*60)
        
        # View Users table
        if 'users' in table_names:
            print("👥 USERS TABLE:")
            print("-" * 30)
            try:
                cursor.execute("PRAGMA table_info(users)")
                columns_info = cursor.fetchall()
                columns = [col[1] for col in columns_info]
                print(f"Columns: {columns}")
                
                cursor.execute("SELECT COUNT(*) FROM users")
                count = cursor.fetchone()[0]
                print(f"Total users: {count}")
                
                if count > 0:
                    cursor.execute("SELECT * FROM users LIMIT 10")
                    users = cursor.fetchall()
                    print("\nUsers data:")
                    
                    for i, user in enumerate(users, 1):
                        print(f"  User {i}:")
                        print(f"    ID: {user[0]}")
                        print(f"    Username: {user[1]}")
                        if len(user) > 2 and user[2]:
                            print(f"    Password Hash: {user[2][:15]}...")
                        if len(user) > 3 and user[3]:
                            print(f"    Created: {user[3]}")
                        print()
                else:
                    print("  No users found")
                    
            except Exception as e:
                print(f"  ❌ Error reading users table: {e}")
        else:
            print("👥 USERS TABLE: Not found")
        
        print("\n" + "-"*30)
        
        # View Messages table
        if 'messages' in table_names:
            print("💬 MESSAGES TABLE:")
            print("-" * 30)
            try:
                cursor.execute("SELECT COUNT(*) FROM messages")
                count = cursor.fetchone()[0]
                print(f"Total messages: {count}")
                
                if count > 0:
                    cursor.execute("""
                        SELECT m.id, m.sender_id, m.receiver_id, m.content, 
                               m.message_type, m.file_path, m.created_at
                        FROM messages m
                        ORDER BY m.created_at DESC
                        LIMIT 5
                    """)
                    messages = cursor.fetchall()
                    print("\nRecent messages:")
                    
                    for i, msg in enumerate(messages, 1):
                        print(f"  Message {i}:")
                        print(f"    ID: {msg[0]}")
                        print(f"    From User ID: {msg[1]} → To User ID: {msg[2]}")
                        print(f"    Content: {msg[3][:50]}{'...' if len(str(msg[3])) > 50 else ''}")
                        print(f"    Type: {msg[4]}")
                        if msg[5]:
                            print(f"    File: {msg[5]}")
                        print(f"    Time: {msg[6]}")
                        print()
                else:
                    print("  No messages found")
                    
            except Exception as e:
                print(f"  ❌ Error reading messages table: {e}")
        else:
            print("💬 MESSAGES TABLE: Not found")
        
        conn.close()
        print("\n" + "="*60)
        
    except Exception as e:
        print(f"\n❌ Database connection error: {e}")
    
    input("\nPress Enter to continue...")

def create_test_database():
    """Create database with test data"""
    print("🔧 Creating test database...")
    
    try:
        conn = sqlite3.connect('messenger.db')
        cursor = conn.cursor()
        
        print("📋 Creating tables...")
        
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users (id),
                FOREIGN KEY (receiver_id) REFERENCES users (id)
            )
        ''')
        
        print("✅ Tables created!")
        
        # Create test users
        import hashlib
        
        def hash_password(password):
            return hashlib.sha256(password.encode()).hexdigest()
        
        test_users = [
            ('alice', '123456'),
            ('bob', '123456'),
            ('charlie', '123456'),
            ('test', 'password')
        ]
        
        print("👥 Creating test users...")
        for username, password in test_users:
            try:
                password_hash = hash_password(password)
                cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', 
                              (username, password_hash))
                print(f"  ✅ Created user: {username}")
            except sqlite3.IntegrityError:
                print(f"  ℹ️  User {username} already exists")
        
        # Create test messages
        print("💬 Creating test messages...")
        test_messages = [
            (1, 2, "Hello Bob! How are you?", "text"),
            (2, 1, "Hi Alice! I'm doing great!", "text"),
            (1, 3, "Hey Charlie, what's up?", "text"),
            (3, 1, "Hello Alice! Nice to meet you!", "text"),
            (2, 3, "Hi Charlie!", "text")
        ]
        
        for sender_id, receiver_id, content, msg_type in test_messages:
            try:
                cursor.execute('''
                    INSERT INTO messages (sender_id, receiver_id, content, message_type)
                    VALUES (?, ?, ?, ?)
                ''', (sender_id, receiver_id, content, msg_type))
            except Exception as e:
                print(f"  Warning: Could not create message: {e}")
        
        conn.commit()
        print("\n✅ Test database created successfully!")
        print("\n📝 Test accounts:")
        print("   Username: alice, Password: 123456")
        print("   Username: bob, Password: 123456") 
        print("   Username: charlie, Password: 123456")
        print("   Username: test, Password: password")
        
    except Exception as e:
        print(f"❌ Error creating database: {e}")
    finally:
        conn.close()
    
    input("\nPress Enter to continue...")

def clear_database():
    """Clear all data from database"""
    db_path = 'messenger.db'
    
    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        input("Press Enter to continue...")
        return
        
    print("⚠️  WARNING: This will delete ALL data!")
    choice = input("Type 'DELETE' to confirm: ")
    if choice != 'DELETE':
        print("Cancelled")
        input("Press Enter to continue...")
        return
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM messages")
        cursor.execute("DELETE FROM users")
        conn.commit()
        print("✅ Database cleared!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()
    
    input("Press Enter to continue...")

def check_database_file():
    """Check database file info"""
    db_path = 'messenger.db'
    abs_path = os.path.abspath(db_path)
    
    print("🔍 DATABASE FILE CHECK:")
    print("-" * 40)
    print(f"Path: {abs_path}")
    print(f"Exists: {os.path.exists(db_path)}")
    
    if os.path.exists(db_path):
        size = os.path.getsize(db_path)
        print(f"Size: {size:,} bytes")
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"Tables: {[t[0] for t in tables]}")
            conn.close()
        except Exception as e:
            print(f"Error reading: {e}")
    else:
        print("💡 Database doesn't exist yet.")
        print("   Run the server or option 3 to create it.")
    
    input("\nPress Enter to continue...")

def main_menu():
    """Main menu for database operations"""
    while True:
        # Clear screen (works on Windows)
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("🗃️  CHAT DATABASE MANAGER")
        print("="*40)
        print("1. 📊 View Database")
        print("2. 🗑️  Clear Database") 
        print("3. 🔧 Create Test Database")
        print("4. 🔍 Check Database File")
        print("5. 🚪 Exit")
        print("="*40)
        
        choice = input("Select option (1-5): ").strip()
        
        if choice == '1':
            view_database()
        elif choice == '2':
            clear_database()
        elif choice == '3':
            create_test_database()
        elif choice == '4':
            check_database_file()
        elif choice == '5':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice! Please enter 1-5")
            input("Press Enter to try again...")

if __name__ == "__main__":
    print("Starting Database Manager...")
    main_menu()
