import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

class DatabaseViewer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("💬 Chat Database Viewer")
        self.root.geometry("800x600")
        
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        
        # Users tab
        users_frame = ttk.Frame(notebook)
        notebook.add(users_frame, text="👥 Users")
        
        # Messages tab  
        messages_frame = ttk.Frame(notebook)
        notebook.add(messages_frame, text="💬 Messages")
        
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.setup_users_tab(users_frame)
        self.setup_messages_tab(messages_frame)
        
        # Refresh button
        refresh_btn = tk.Button(self.root, text="🔄 Refresh", command=self.refresh_data)
        refresh_btn.pack(pady=5)
        
        self.refresh_data()
    
    def setup_users_tab(self, frame):
        # Users treeview
        self.users_tree = ttk.Treeview(frame, columns=('ID', 'Username', 'Created'), show='headings')
        self.users_tree.heading('ID', text='ID')
        self.users_tree.heading('Username', text='Username')
        self.users_tree.heading('Created', text='Created At')
        
        users_scroll = ttk.Scrollbar(frame, orient='vertical', command=self.users_tree.yview)
        self.users_tree.configure(yscrollcommand=users_scroll.set)
        
        self.users_tree.pack(side='left', fill='both', expand=True)
        users_scroll.pack(side='right', fill='y')
    
    def setup_messages_tab(self, frame):
        # Messages treeview
        self.messages_tree = ttk.Treeview(frame, columns=('ID', 'From', 'To', 'Content', 'Type', 'Time'), show='headings')
        self.messages_tree.heading('ID', text='ID')
        self.messages_tree.heading('From', text='From')
        self.messages_tree.heading('To', text='To')
        self.messages_tree.heading('Content', text='Content')
        self.messages_tree.heading('Type', text='Type')
        self.messages_tree.heading('Time', text='Time')
        
        messages_scroll = ttk.Scrollbar(frame, orient='vertical', command=self.messages_tree.yview)
        self.messages_tree.configure(yscrollcommand=messages_scroll.set)
        
        self.messages_tree.pack(side='left', fill='both', expand=True)
        messages_scroll.pack(side='right', fill='y')
    
    def refresh_data(self):
        try:
            conn = sqlite3.connect('messenger.db')
            cursor = conn.cursor()
            
            # Load users
            self.users_tree.delete(*self.users_tree.get_children())
            cursor.execute("SELECT id, username, created_at FROM users")
            for row in cursor.fetchall():
                self.users_tree.insert('', 'end', values=row)
            
            # Load messages
            self.messages_tree.delete(*self.messages_tree.get_children())
            cursor.execute("""
                SELECT m.id, u1.username, u2.username, m.content, m.message_type, m.created_at
                FROM messages m
                JOIN users u1 ON m.sender_id = u1.id
                JOIN users u2 ON m.receiver_id = u2.id
                ORDER BY m.created_at DESC
                LIMIT 50
            """)
            for row in cursor.fetchall():
                content = row[3][:50] + "..." if len(row[3]) > 50 else row[3]
                self.messages_tree.insert('', 'end', values=(row[0], row[1], row[2], content, row[4], row[5]))
            
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Database error: {e}")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = DatabaseViewer()
    app.run()
