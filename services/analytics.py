"""
Analytics service for AI Knowledge Base.
Provides trend analysis, topic clustering, and statistical insights.
"""

import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_connection


def get_overall_stats():
    """Get overall statistics for the knowledge base."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Total emails
        cursor.execute('SELECT COUNT(*) FROM emails')
        total_emails = cursor.fetchone()[0]
        
        # Total links
        cursor.execute('SELECT COUNT(*) FROM email_links')
        total_links = cursor.fetchone()[0]
        
        # Unique domains
        cursor.execute('SELECT COUNT(DISTINCT domain) FROM email_links WHERE domain IS NOT NULL')
        unique_domains = cursor.fetchone()[0]
        
        # Total categories
        cursor.execute('SELECT COUNT(DISTINCT category) FROM email_categories')
        total_categories = cursor.fetchone()[0]
        
        # Date range
        cursor.execute('SELECT MIN(date_parsed), MAX(date_parsed) FROM emails WHERE date_parsed IS NOT NULL')
        date_range = cursor.fetchone()
        
        # Emails with summaries
        cursor.execute("SELECT COUNT(*) FROM emails WHERE summary IS NOT NULL AND summary != ''")
        emails_with_summaries = cursor.fetchone()[0]
        
        return {
            'total_emails': total_emails,
            'total_links': total_links,
            'unique_domains': unique_domains,
            'total_categories': total_categories,
            'date_range': {
                'start': date_range[0][:10] if date_range[0] else None,
                'end': date_range[1][:10] if date_range[1] else None
            },
            'emails_with_summaries': emails_with_summaries,
            'summary_coverage': round(emails_with_summaries / total_emails * 100, 1) if total_emails > 0 else 0
        }


def get_category_stats():
    """Get category breakdown with counts (sorted by count)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT category, COUNT(*) as count 
            FROM email_categories 
            GROUP BY category 
            ORDER BY count DESC
        ''')
        return [{'category': row['category'], 'count': row['count']} for row in cursor.fetchall()]


def get_all_categories_alphabetical():
    """Get all categories alphabetically with counts."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT category, COUNT(*) as count 
            FROM email_categories 
            GROUP BY category 
            ORDER BY category ASC
        ''')
        return [{'category': row['category'], 'count': row['count']} for row in cursor.fetchall()]


def get_trending_topics(days=7, limit=10):
    """
    Get topics that have increased in mentions recently.
    Compares recent period to previous period.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Get the most recent date in the database
        cursor.execute('SELECT MAX(date) FROM trend_snapshots')
        max_date_row = cursor.fetchone()
        if not max_date_row[0]:
            return []
        
        max_date = datetime.fromisoformat(max_date_row[0])
        recent_start = (max_date - timedelta(days=days)).isoformat()[:10]
        previous_start = (max_date - timedelta(days=days*2)).isoformat()[:10]
        previous_end = recent_start
        
        # Recent period counts
        cursor.execute('''
            SELECT category, SUM(email_count) as count 
            FROM trend_snapshots 
            WHERE date >= ?
            GROUP BY category
        ''', (recent_start,))
        recent = {row['category']: row['count'] for row in cursor.fetchall()}
        
        # Previous period counts
        cursor.execute('''
            SELECT category, SUM(email_count) as count 
            FROM trend_snapshots 
            WHERE date >= ? AND date < ?
            GROUP BY category
        ''', (previous_start, previous_end))
        previous = {row['category']: row['count'] for row in cursor.fetchall()}
        
        # Calculate growth
        trends = []
        for category, recent_count in recent.items():
            prev_count = previous.get(category, 0)
            if prev_count > 0:
                growth = ((recent_count - prev_count) / prev_count) * 100
            elif recent_count > 0:
                growth = 100  # New category
            else:
                growth = 0
            
            trends.append({
                'category': category,
                'recent_count': recent_count,
                'previous_count': prev_count,
                'growth_percent': round(growth, 1),
                'trend': 'up' if growth > 10 else ('down' if growth < -10 else 'stable')
            })
        
        # Sort by growth (descending)
        trends.sort(key=lambda x: x['growth_percent'], reverse=True)
        return trends[:limit]


def get_topic_timeline(days=30):
    """Get email counts by category over time for charting."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Get the most recent date
        cursor.execute('SELECT MAX(date) FROM trend_snapshots')
        max_date_row = cursor.fetchone()
        if not max_date_row[0]:
            return {'labels': [], 'datasets': []}
        
        max_date = datetime.fromisoformat(max_date_row[0])
        start_date = (max_date - timedelta(days=days)).isoformat()[:10]
        
        # Get top categories
        cursor.execute('''
            SELECT category, SUM(email_count) as total
            FROM trend_snapshots
            WHERE date >= ?
            GROUP BY category
            ORDER BY total DESC
            LIMIT 6
        ''', (start_date,))
        top_categories = [row['category'] for row in cursor.fetchall()]
        
        # Get weekly aggregated data for each category
        datasets = []
        colors = [
            'rgba(99, 102, 241, 0.8)',   # Indigo
            'rgba(168, 85, 247, 0.8)',   # Purple
            'rgba(236, 72, 153, 0.8)',   # Pink
            'rgba(59, 130, 246, 0.8)',   # Blue
            'rgba(34, 197, 94, 0.8)',    # Green
            'rgba(249, 115, 22, 0.8)',   # Orange
        ]
        
        for i, category in enumerate(top_categories):
            cursor.execute('''
                SELECT 
                    strftime('%Y-%W', date) as week,
                    SUM(email_count) as count
                FROM trend_snapshots
                WHERE category = ? AND date >= ?
                GROUP BY week
                ORDER BY week
            ''', (category, start_date))
            
            data = {row['week']: row['count'] for row in cursor.fetchall()}
            datasets.append({
                'label': category,
                'data': list(data.values()),
                'borderColor': colors[i % len(colors)],
                'backgroundColor': colors[i % len(colors)].replace('0.8', '0.2'),
                'tension': 0.3
            })
        
        # Get all weeks for labels
        cursor.execute('''
            SELECT DISTINCT strftime('%Y-%W', date) as week
            FROM trend_snapshots
            WHERE date >= ?
            ORDER BY week
        ''', (start_date,))
        labels = [row['week'] for row in cursor.fetchall()]
        
        return {
            'labels': labels,
            'datasets': datasets
        }


def get_whats_hot(limit=10):
    """Get the most discussed topics in the last 7 days."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Get the most recent date
        cursor.execute('SELECT MAX(date_parsed) FROM emails')
        max_date_row = cursor.fetchone()
        if not max_date_row[0]:
            return []
        
        max_date = datetime.fromisoformat(max_date_row[0])
        week_ago = (max_date - timedelta(days=7)).isoformat()
        
        cursor.execute('''
            SELECT 
                ec.category,
                COUNT(*) as count,
                MAX(e.date_parsed) as latest
            FROM emails e
            JOIN email_categories ec ON e.id = ec.email_id
            WHERE e.date_parsed >= ?
            GROUP BY ec.category
            ORDER BY count DESC
            LIMIT ?
        ''', (week_ago, limit))
        
        return [
            {
                'category': row['category'],
                'count': row['count'],
                'latest': row['latest'][:10] if row['latest'] else None
            }
            for row in cursor.fetchall()
        ]


def get_recent_emails(limit=10):
    """Get the most recent emails."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                e.id, e.subject, e.summary, e.date_parsed,
                GROUP_CONCAT(DISTINCT ec.category) as categories
            FROM emails e
            LEFT JOIN email_categories ec ON e.id = ec.email_id
            WHERE e.date_parsed IS NOT NULL
            GROUP BY e.id
            ORDER BY e.date_parsed DESC
            LIMIT ?
        ''', (limit,))
        
        return [
            {
                'id': row['id'],
                'subject': row['subject'][:100] + '...' if len(row['subject'] or '') > 100 else row['subject'],
                'summary': row['summary'],
                'date': row['date_parsed'][:10] if row['date_parsed'] else None,
                'categories': row['categories'].split(',') if row['categories'] else []
            }
            for row in cursor.fetchall()
        ]


def get_top_domains(limit=15):
    """Get top domains by link count."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT domain, COUNT(*) as count
            FROM email_links
            WHERE domain IS NOT NULL AND domain != ''
            GROUP BY domain
            ORDER BY count DESC
            LIMIT ?
        ''', (limit,))
        
        return [{'domain': row['domain'], 'count': row['count']} for row in cursor.fetchall()]


if __name__ == '__main__':
    # Test the analytics functions
    print("=== Overall Stats ===")
    stats = get_overall_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n=== Category Stats (Top 10) ===")
    for cat in get_category_stats()[:10]:
        print(f"  {cat['category']}: {cat['count']}")
    
    print("\n=== Trending Topics ===")
    for trend in get_trending_topics():
        print(f"  {trend['category']}: {trend['growth_percent']:+.1f}% ({trend['trend']})")
    
    print("\n=== What's Hot ===")
    for hot in get_whats_hot():
        print(f"  {hot['category']}: {hot['count']} (latest: {hot['latest']})")
    
    print("\n=== Top Domains ===")
    for domain in get_top_domains()[:10]:
        print(f"  {domain['domain']}: {domain['count']}")
