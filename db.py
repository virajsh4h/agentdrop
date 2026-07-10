import sqlite3
import os

DB_NAME = "agentdrop.db"

def get_db():
    db_name = os.environ.get("TESTING_DB", DB_NAME)
    conn = sqlite3.connect(db_name, timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS drops (
        id TEXT PRIMARY KEY,
        ciphertext TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        status TEXT NOT NULL, -- 'active', 'used', 'revoked', 'expired'
        revoke_token TEXT NOT NULL,
        failed_attempts INTEGER DEFAULT 0
    )
    """)
    
    # Migration for existing databases
    try:
        cursor.execute("ALTER TABLE drops ADD COLUMN failed_attempts INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass # Column already exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS receipts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        drop_id TEXT NOT NULL,
        action TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (drop_id) REFERENCES drops (id)
    )
    """)
    conn.commit()
    conn.close()

init_db()
