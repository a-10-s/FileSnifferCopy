import sqlite3
import json
from pathlib import Path
from config import DB_PATH, DEFAULT_SETTINGS

def get_db_connection():
    """Return a sqlite3 connection with foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initialize the SQLite database schema if not already present."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Settings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)

    # 2. Jobs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        source TEXT NOT NULL,
        destination TEXT NOT NULL,
        schedule_type TEXT NOT NULL, -- 'manual', 'hourly', 'daily'
        schedule_value TEXT,         -- For hourly: interval in hours; For daily: 'HH:MM'
        convert_enabled INTEGER NOT NULL DEFAULT 0, -- 0 or 1
        convert_extensions TEXT DEFAULT 'exr',     -- Comma-separated list e.g. 'exr,dpx'
        target_compression TEXT DEFAULT 'dwab',
        active INTEGER NOT NULL DEFAULT 1,         -- 0 or 1
        last_run TEXT,
        prune_enabled INTEGER NOT NULL DEFAULT 0,
        prune_threshold_gb REAL DEFAULT 20.0,
        proxy_enabled INTEGER NOT NULL DEFAULT 0,
        proxy_fps INTEGER DEFAULT 24,
        sync_mode TEXT DEFAULT 'mirror'
    );
    """)

    # Check for missing columns in jobs (for migration of existing databases)
    cursor.execute("PRAGMA table_info(jobs);")
    columns = [col['name'] for col in cursor.fetchall()]
    if 'prune_enabled' not in columns:
        cursor.execute("ALTER TABLE jobs ADD COLUMN prune_enabled INTEGER NOT NULL DEFAULT 0;")
    if 'prune_threshold_gb' not in columns:
        cursor.execute("ALTER TABLE jobs ADD COLUMN prune_threshold_gb REAL DEFAULT 20.0;")
    if 'proxy_enabled' not in columns:
        cursor.execute("ALTER TABLE jobs ADD COLUMN proxy_enabled INTEGER NOT NULL DEFAULT 0;")
    if 'proxy_fps' not in columns:
        cursor.execute("ALTER TABLE jobs ADD COLUMN proxy_fps INTEGER DEFAULT 24;")
    if 'sync_mode' not in columns:
        cursor.execute("ALTER TABLE jobs ADD COLUMN sync_mode TEXT DEFAULT 'mirror';")


    # 3. Sync State Table (keeps track of what has been successfully transferred)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sync_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        relative_path TEXT NOT NULL,
        file_size INTEGER NOT NULL,
        mtime REAL NOT NULL,
        status TEXT NOT NULL,        -- 'synced', 'failed', 'pruned'
        last_sync TEXT,
        FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE,
        UNIQUE(job_id, relative_path)
    );
    """)

    # 4. Sync History Table (for dashboard reports and space saving computations)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sync_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER,
        file_name TEXT NOT NULL,
        status TEXT NOT NULL,        -- 'success', 'failed', 'warning'
        bytes_transferred INTEGER NOT NULL,
        bytes_saved INTEGER NOT NULL DEFAULT 0,
        error_message TEXT,
        timestamp TEXT DEFAULT (datetime('now', 'localtime'))
    );
    """)

    # Insert default settings if they don't exist
    for key, val in DEFAULT_SETTINGS.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, str(val)))

    conn.commit()
    conn.close()

# --- Helper functions for Settings ---

def get_setting(key, default=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        val = row["value"]
        # Try to convert to int or float if numeric
        try:
            if "." in val:
                return float(val)
            return int(val)
        except ValueError:
            return val
    return default

def set_setting(key, value):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

# --- Helper functions for Jobs ---

def get_all_jobs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs")
    rows = cursor.fetchall()
    jobs = [dict(r) for r in rows]
    conn.close()
    return jobs

def get_job(job_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_job(name, source, destination, schedule_type, schedule_value, convert_enabled, convert_extensions, target_compression, prune_enabled=0, prune_threshold_gb=20.0, proxy_enabled=0, proxy_fps=24, sync_mode='mirror'):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO jobs (name, source, destination, schedule_type, schedule_value, convert_enabled, convert_extensions, target_compression, prune_enabled, prune_threshold_gb, proxy_enabled, proxy_fps, sync_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, source, destination, schedule_type, schedule_value, convert_enabled, convert_extensions, target_compression, prune_enabled, prune_threshold_gb, proxy_enabled, proxy_fps, sync_mode))
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return job_id

def update_job(job_id, name, source, destination, schedule_type, schedule_value, convert_enabled, convert_extensions, target_compression, active, prune_enabled=0, prune_threshold_gb=20.0, proxy_enabled=0, proxy_fps=24, sync_mode='mirror'):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE jobs
        SET name = ?, source = ?, destination = ?, schedule_type = ?, schedule_value = ?, 
            convert_enabled = ?, convert_extensions = ?, target_compression = ?, active = ?,
            prune_enabled = ?, prune_threshold_gb = ?, proxy_enabled = ?, proxy_fps = ?, sync_mode = ?
        WHERE id = ?
    """, (name, source, destination, schedule_type, schedule_value, convert_enabled, convert_extensions, target_compression, active, prune_enabled, prune_threshold_gb, proxy_enabled, proxy_fps, sync_mode, job_id))
    conn.commit()
    conn.close()

def delete_job(job_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()

def update_job_last_run(job_id, timestamp_str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET last_run = ? WHERE id = ?", (timestamp_str, job_id))
    conn.commit()
    conn.close()

# --- Helper functions for Sync State & History ---

def get_sync_state(job_id, relative_path):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sync_state WHERE job_id = ? AND relative_path = ?", (job_id, relative_path))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def set_sync_state(job_id, relative_path, file_size, mtime, status, last_sync):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO sync_state (job_id, relative_path, file_size, mtime, status, last_sync)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (job_id, relative_path, file_size, mtime, status, last_sync))
    conn.commit()
    conn.close()

def add_history_entry(job_id, file_name, status, bytes_transferred, bytes_saved, error_message=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sync_history (job_id, file_name, status, bytes_transferred, bytes_saved, error_message)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (job_id, file_name, status, bytes_transferred, bytes_saved, error_message))
    conn.commit()
    conn.close()

def get_history(limit=100):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT h.*, j.name as job_name 
        FROM sync_history h
        LEFT JOIN jobs j ON h.job_id = j.id
        ORDER BY h.id DESC LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    history = [dict(r) for r in rows]
    conn.close()
    return history

def get_total_savings():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(bytes_saved) as total FROM sync_history WHERE status = 'success'")
    row = cursor.fetchone()
    conn.close()
    return row["total"] if row and row["total"] else 0

def clear_history():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sync_history")
    conn.commit()
    conn.close()

# Initialize DB when loaded
init_db()
