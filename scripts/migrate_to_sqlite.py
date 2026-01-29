#!/usr/bin/env python3
"""
Migration script to convert parsed_emails.json to SQLite database.
Preserves all existing data and creates normalized tables.
"""

import json
import os
import sys
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_database, get_connection, get_db_path


def parse_email_date(date_str):
    """Parse email date string to datetime, with fallback."""
    if not date_str:
        return None
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        # Try common date formats
        formats = [
            '%a, %d %b %Y %H:%M:%S %z',
            '%Y-%m-%d %H:%M:%S',
            '%d %b %Y %H:%M:%S',
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return None


def extract_domain(url):
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower().replace('www.', '')
    except Exception:
        return None


def migrate_emails():
    """Migrate all emails from JSON to SQLite."""
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'parsed_emails.json')
    
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found!")
        return False
    
    print(f"Loading emails from {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        emails = json.load(f)
    
    print(f"Found {len(emails)} emails to migrate")
    
    # Initialize database
    init_database()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Check if already migrated
        cursor.execute('SELECT COUNT(*) FROM emails')
        existing_count = cursor.fetchone()[0]
        
        if existing_count > 0:
            print(f"Database already contains {existing_count} emails.")
            response = input("Do you want to clear and re-migrate? (y/N): ")
            if response.lower() != 'y':
                print("Migration cancelled.")
                return False
            
            # Clear all tables
            print("Clearing existing data...")
            cursor.execute('DELETE FROM email_links')
            cursor.execute('DELETE FROM email_categories')
            cursor.execute('DELETE FROM emails')
            conn.commit()
        
        print("Migrating emails...")
        migrated = 0
        links_count = 0
        categories_count = 0
        
        for i, email in enumerate(emails):
            # Parse date
            date_parsed = parse_email_date(email.get('date', ''))
            
            # Insert email
            cursor.execute('''
                INSERT INTO emails (subject, content, date, date_parsed, sender, summary, original_categories)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                email.get('subject', ''),
                email.get('content', ''),
                email.get('date', ''),
                date_parsed.isoformat() if date_parsed else None,
                email.get('from', ''),
                email.get('summary', ''),
                json.dumps(email.get('categories', []))
            ))
            
            email_id = cursor.lastrowid
            
            # Insert links
            for link in email.get('links', []):
                domain = extract_domain(link)
                cursor.execute('''
                    INSERT INTO email_links (email_id, url, domain)
                    VALUES (?, ?, ?)
                ''', (email_id, link, domain))
                links_count += 1
            
            # Insert categories
            for category in email.get('categories', []):
                cursor.execute('''
                    INSERT OR IGNORE INTO email_categories (email_id, category)
                    VALUES (?, ?)
                ''', (email_id, category))
                categories_count += 1
            
            migrated += 1
            
            # Progress update
            if (i + 1) % 1000 == 0:
                print(f"  Progress: {i + 1}/{len(emails)} emails migrated...")
                conn.commit()  # Commit in batches
        
        conn.commit()
        
        print(f"\n✅ Migration complete!")
        print(f"   - Emails: {migrated}")
        print(f"   - Links: {links_count}")
        print(f"   - Category assignments: {categories_count}")
        
        # Print category summary
        cursor.execute('''
            SELECT category, COUNT(*) as count 
            FROM email_categories 
            GROUP BY category 
            ORDER BY count DESC
            LIMIT 10
        ''')
        print(f"\nTop 10 categories:")
        for row in cursor.fetchall():
            print(f"   - {row['category']}: {row['count']}")
        
        # Print date range
        cursor.execute('SELECT MIN(date_parsed), MAX(date_parsed) FROM emails WHERE date_parsed IS NOT NULL')
        date_range = cursor.fetchone()
        if date_range[0] and date_range[1]:
            print(f"\nDate range: {date_range[0][:10]} to {date_range[1][:10]}")
    
    return True


def build_trend_snapshots():
    """Build trend snapshots for analytics."""
    print("\nBuilding trend snapshots...")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Clear existing snapshots
        cursor.execute('DELETE FROM trend_snapshots')
        
        # Build daily snapshots by category
        cursor.execute('''
            INSERT INTO trend_snapshots (date, category, email_count)
            SELECT 
                DATE(e.date_parsed) as date,
                ec.category,
                COUNT(*) as email_count
            FROM emails e
            JOIN email_categories ec ON e.id = ec.email_id
            WHERE e.date_parsed IS NOT NULL
            GROUP BY DATE(e.date_parsed), ec.category
        ''')
        
        conn.commit()
        
        cursor.execute('SELECT COUNT(*) FROM trend_snapshots')
        count = cursor.fetchone()[0]
        print(f"   Created {count} trend snapshots")


if __name__ == '__main__':
    print("=" * 60)
    print("AI Knowledge Base - JSON to SQLite Migration")
    print("=" * 60)
    
    if migrate_emails():
        build_trend_snapshots()
        print(f"\n✅ Database ready at: {get_db_path()}")
    else:
        print("\n❌ Migration failed or was cancelled.")
