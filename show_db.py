import sqlite3
import os

def show_tables(limit_messages=10):
    """Display database tables in a nice format"""
    if not os.path.exists('messenger.db'):
        print("❌ Database not found! Run the server first.")
        return
    
    conn = sqlite3.connect('messenger.db')
    cursor = conn.cursor()
    
    print("📊 USERS TABLE")
    print("-" * 60)
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    print(f"Total users: {user_count}")
    
    cursor.execute("SELECT id, username, created_at FROM users")
    users = cursor.fetchall()
    
    if users:
        print(f"\n{'ID':<5} {'Username':<20} {'Created At':<25}")
        print("-" * 60)
        for user in users:
            print(f"{user[0]:<5} {user[1]:<20} {str(user[2]):<25}")
    else:
        print("No users found")
    
    print("\n💬 MESSAGES TABLE")
    print("-" * 80)
    cursor.execute("SELECT COUNT(*) FROM messages")
    msg_count = cursor.fetchone()[0]
    print(f"Total messages: {msg_count}")
    
    if limit_messages == 0:
        print("Showing ALL messages:")
        limit_clause = ""
    else:
        print(f"Showing {limit_messages} most recent messages:")
        limit_clause = f"LIMIT {limit_messages}"
    
    cursor.execute(f"""
        SELECT m.id, u1.username as sender, u2.username as receiver, 
               m.content, m.message_type, m.created_at
        FROM messages m
        JOIN users u1 ON m.sender_id = u1.id
        JOIN users u2 ON m.receiver_id = u2.id
        ORDER BY m.created_at DESC
        {limit_clause}
    """)
    messages = cursor.fetchall()
    
    if messages:
        print(f"\n{'ID':<5} {'From':<15} {'To':<15} {'Content':<30} {'Type':<10} {'Time':<20}")
        print("-" * 80)
        for msg in messages:
            content = msg[3][:30] + "..." if len(str(msg[3])) > 30 else str(msg[3])
            print(f"{msg[0]:<5} {msg[1]:<15} {msg[2]:<15} {content:<30} {msg[4]:<10} {str(msg[5]):<20}")
    else:
        print("No messages found")
    
    conn.close()

def show_all_tables():
    """Show complete database"""
    show_tables(limit_messages=0)

def show_recent_tables():
    """Show only recent messages"""
    show_tables(limit_messages=10)

def interactive_menu():
    """Interactive menu for viewing database"""
    while True:
        print("\n📊 DATABASE VIEWER")
        print("=" * 30)
        print("1. Show recent (10 messages)")
        print("2. Show ALL messages")
        print("3. Show only users")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            show_recent_tables()
        elif choice == '2':
            show_all_tables()
        elif choice == '3':
            show_users_only()
        elif choice == '4':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice!")
        
        input("\nPress Enter to continue...")

def show_users_only():
    """Show only users table"""
    if not os.path.exists('messenger.db'):
        print("❌ Database not found!")
        return
    
    conn = sqlite3.connect('messenger.db')
    cursor = conn.cursor()
    
    print("👥 USERS TABLE (COMPLETE)")
    print("-" * 60)
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    print(f"Total users: {user_count}")
    
    cursor.execute("SELECT id, username, created_at FROM users ORDER BY id")
    users = cursor.fetchall()
    
    if users:
        print(f"\n{'ID':<5} {'Username':<20} {'Created At':<25}")
        print("-" * 60)
        for user in users:
            print(f"{user[0]:<5} {user[1]:<20} {str(user[2]):<25}")
    else:
        print("No users found")
    
    conn.close()

if __name__ == "__main__":
    # Default behavior - show recent
    if len(os.sys.argv) > 1:
        if os.sys.argv[1] == "--all":
            show_all_tables()
        elif os.sys.argv[1] == "--users":
            show_users_only()
        elif os.sys.argv[1] == "--menu":
            interactive_menu()
        else:
            print("Usage:")
            print("  python show_db.py           # Show recent messages")
            print("  python show_db.py --all     # Show ALL messages")
            print("  python show_db.py --users   # Show only users")
            print("  python show_db.py --menu    # Interactive menu")
    else:
        interactive_menu()
