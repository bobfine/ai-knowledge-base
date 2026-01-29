"""
Database module for AI Knowledge Base.
Handles SQLite connection, schema creation, and common queries.
"""

import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'knowledge.db')


def get_db_path():
    """Get the database path, ensuring the data directory exists."""
    db_dir = os.path.dirname(DATABASE_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    return DATABASE_PATH


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row  # Enable column access by name
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """Initialize the database with all required tables."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Core emails table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT,
                content TEXT,
                date TEXT,
                date_parsed DATETIME,
                sender TEXT,
                summary TEXT,
                sentiment REAL DEFAULT 0.0,
                embedding BLOB,
                original_categories TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Email links table (normalized from JSON array)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                domain TEXT,
                FOREIGN KEY (email_id) REFERENCES emails(id)
            )
        ''')
        
        # Email categories table (normalized from JSON array)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_categories (
                email_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                PRIMARY KEY (email_id, category),
                FOREIGN KEY (email_id) REFERENCES emails(id)
            )
        ''')
        
        # Entities extracted from emails
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL,
                description TEXT,
                first_seen DATETIME,
                last_seen DATETIME,
                mention_count INTEGER DEFAULT 0
            )
        ''')
        
        # Email-Entity junction table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_entities (
                email_id INTEGER NOT NULL,
                entity_id INTEGER NOT NULL,
                sentiment REAL DEFAULT 0.0,
                PRIMARY KEY (email_id, entity_id),
                FOREIGN KEY (email_id) REFERENCES emails(id),
                FOREIGN KEY (entity_id) REFERENCES entities(id)
            )
        ''')
        
        # Entity relationships
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entity_relationships (
                entity_a INTEGER NOT NULL,
                entity_b INTEGER NOT NULL,
                relationship TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                PRIMARY KEY (entity_a, entity_b, relationship),
                FOREIGN KEY (entity_a) REFERENCES entities(id),
                FOREIGN KEY (entity_b) REFERENCES entities(id)
            )
        ''')
        
        # Briefings (cached AI-generated summaries)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS briefings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                date_range_start DATETIME,
                date_range_end DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tool/Product tracking (derived from entities)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                normalized_name TEXT NOT NULL,
                category TEXT,
                first_mention DATETIME,
                last_mention DATETIME,
                mention_count INTEGER DEFAULT 0,
                avg_sentiment REAL DEFAULT 0.0
            )
        ''')
        
        # Tool mentions per email
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tool_mentions (
                email_id INTEGER NOT NULL,
                tool_id INTEGER NOT NULL,
                sentiment REAL DEFAULT 0.0,
                PRIMARY KEY (email_id, tool_id),
                FOREIGN KEY (email_id) REFERENCES emails(id),
                FOREIGN KEY (tool_id) REFERENCES tools(id)
            )
        ''')
        
        # Learning modules (Phase 3)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                order_index INTEGER DEFAULT 0,
                prerequisite_id INTEGER,
                FOREIGN KEY (prerequisite_id) REFERENCES modules(id)
            )
        ''')
        
        # Lessons within modules (Phase 3)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                order_index INTEGER DEFAULT 0,
                FOREIGN KEY (module_id) REFERENCES modules(id)
            )
        ''')
        
        # Lesson source emails (Phase 3)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lesson_sources (
                lesson_id INTEGER NOT NULL,
                email_id INTEGER NOT NULL,
                relevance REAL DEFAULT 1.0,
                PRIMARY KEY (lesson_id, email_id),
                FOREIGN KEY (lesson_id) REFERENCES lessons(id),
                FOREIGN KEY (email_id) REFERENCES emails(id)
            )
        ''')
        
        # Quiz questions (Phase 3)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quiz_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lesson_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                options TEXT NOT NULL,
                correct_answer INTEGER NOT NULL,
                explanation TEXT,
                FOREIGN KEY (lesson_id) REFERENCES lessons(id)
            )
        ''')
        
        # User progress (single user, Phase 3)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_progress (
                lesson_id INTEGER PRIMARY KEY,
                completed_at DATETIME,
                quiz_score REAL,
                FOREIGN KEY (lesson_id) REFERENCES lessons(id)
            )
        ''')
        
        # Trend snapshots for analytics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trend_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                category TEXT NOT NULL,
                email_count INTEGER DEFAULT 0,
                avg_sentiment REAL DEFAULT 0.0,
                UNIQUE(date, category)
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_emails_date ON emails(date_parsed)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_emails_sender ON emails(sender)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_links_domain ON email_links(domain)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_categories_category ON email_categories(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tools_name ON tools(normalized_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_trend_snapshots_date ON trend_snapshots(date)')
        
        conn.commit()
        print("Database initialized successfully!")


def get_email_count():
    """Get total number of emails in database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM emails')
        return cursor.fetchone()[0]


def get_all_categories():
    """Get all unique categories with counts."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT category, COUNT(*) as count 
            FROM email_categories 
            GROUP BY category 
            ORDER BY count DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]


def get_emails_by_category(category, limit=50, offset=0):
    """Get emails for a specific category."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.* 
            FROM emails e
            JOIN email_categories ec ON e.id = ec.email_id
            WHERE ec.category = ?
            ORDER BY e.date_parsed DESC
            LIMIT ? OFFSET ?
        ''', (category, limit, offset))
        return [dict(row) for row in cursor.fetchall()]


def search_emails(query, limit=50):
    """Basic keyword search across emails."""
    with get_connection() as conn:
        cursor = conn.cursor()
        search_term = f'%{query}%'
        cursor.execute('''
            SELECT * FROM emails 
            WHERE subject LIKE ? OR content LIKE ? OR summary LIKE ?
            ORDER BY date_parsed DESC
            LIMIT ?
        ''', (search_term, search_term, search_term, limit))
        return [dict(row) for row in cursor.fetchall()]


if __name__ == '__main__':
    init_database()
    print(f"Database created at: {get_db_path()}")
