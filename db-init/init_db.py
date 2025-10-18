#!/usr/bin/env python3
import sqlite3
import os
import sys

def init_database():
    db_path = os.getenv('DB_PATH', '/app/db/rss.sqlite')
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable WAL mode for better concurrent access
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=10000")
    cursor.execute("PRAGMA temp_store=MEMORY")
    
    
    # Create logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            service TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create tagging_items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tagging_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            path TEXT NOT NULL,
            folder TEXT,
            status TEXT DEFAULT 'waiting',
            size INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create conversion_tracking table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversion_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_name TEXT NOT NULL,
            total_files INTEGER DEFAULT 0,
            converted_files INTEGER DEFAULT 0,
            current_file TEXT,
            status TEXT DEFAULT 'pending',
            progress_percentage REAL DEFAULT 0.0,
            estimated_eta_seconds INTEGER,
            merge_folder_path TEXT,
            temp_folder_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create conversion_jobs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversion_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ygg_torrent_id INTEGER,
            book_name TEXT NOT NULL,
            source_path TEXT NOT NULL,
            backup_path TEXT,
            status TEXT DEFAULT 'pending',
            attempts INTEGER DEFAULT 0,
            max_attempts INTEGER DEFAULT 3,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tagging_items_status ON tagging_items(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tagging_items_created_at ON tagging_items(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversion_tracking_status ON conversion_tracking(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversion_tracking_created_at ON conversion_tracking(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversion_jobs_status ON conversion_jobs(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversion_jobs_created_at ON conversion_jobs(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversion_jobs_book_name ON conversion_jobs(book_name)')
    
    conn.commit()
    conn.close()
    
    print(f"Database initialized at {db_path}")

if __name__ == "__main__":
    init_database()
