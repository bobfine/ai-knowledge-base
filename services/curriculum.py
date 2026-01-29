"""
Learning curriculum service for AI Knowledge Base.
Generates personalized learning paths and content.
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_connection


# Default curriculum modules for learning about AI
DEFAULT_CURRICULUM = [
    {
        'order': 1,
        'title': 'Introduction to AI & LLMs',
        'description': 'Understanding the fundamentals of AI, machine learning, and large language models.',
        'topics': ['AI basics', 'Machine Learning', 'LLM', 'GPT', 'Claude'],
        'estimated_hours': 4
    },
    {
        'order': 2,
        'title': 'AI Coding Assistants',
        'description': 'Learn to use AI-powered coding tools like Cursor, Claude Code, and GitHub Copilot.',
        'topics': ['Cursor', 'Claude Code', 'GitHub Copilot', 'Windsurf', 'AI Coding IDEs'],
        'estimated_hours': 6
    },
    {
        'order': 3,
        'title': 'Prompt Engineering',
        'description': 'Master the art of writing effective prompts for AI systems.',
        'topics': ['Prompt Engineering', 'Chain of Thought', 'Few-shot Learning'],
        'estimated_hours': 5
    },
    {
        'order': 4,
        'title': 'AI Agents & Automation',
        'description': 'Understanding and building AI agents for task automation.',
        'topics': ['AI Agents', 'Agentic AI', 'MCP', 'Automation'],
        'estimated_hours': 6
    },
    {
        'order': 5,
        'title': 'No-Code AI Development',
        'description': 'Building applications with AI without traditional coding.',
        'topics': ['Vibe Coding', 'Lovable', 'Bolt', 'v0', 'Replit'],
        'estimated_hours': 4
    },
    {
        'order': 6,
        'title': 'RAG & Knowledge Systems',
        'description': 'Building AI systems that integrate with your own data.',
        'topics': ['RAG', 'Embeddings', 'Vector Database', 'Knowledge Graph'],
        'estimated_hours': 5
    }
]


def initialize_curriculum():
    """Initialize the default curriculum in the database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Check if modules exist
        cursor.execute('SELECT COUNT(*) FROM modules')
        count = cursor.fetchone()[0]
        
        if count > 0:
            print(f"Curriculum already initialized ({count} modules)")
            return count
        
        # Insert default modules
        for module in DEFAULT_CURRICULUM:
            cursor.execute('''
                INSERT INTO modules (title, description, order_index, estimated_hours, topics_json)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                module['title'],
                module['description'],
                module['order'],
                module['estimated_hours'],
                str(module['topics'])
            ))
            module_id = cursor.lastrowid
            
            # Create lessons from related emails
            create_lessons_for_module(cursor, module_id, module['topics'])
        
        conn.commit()
        print(f"✅ Initialized {len(DEFAULT_CURRICULUM)} curriculum modules")
        return len(DEFAULT_CURRICULUM)


def create_lessons_for_module(cursor, module_id, topics):
    """Create lessons from emails matching module topics."""
    # Get emails matching any of the topics
    lessons_created = 0
    
    for topic in topics[:3]:  # Limit to 3 lessons per module initially
        # Find emails related to this topic
        search_term = f'%{topic}%'
        cursor.execute('''
            SELECT e.id, e.subject, e.summary, e.date_parsed
            FROM emails e
            WHERE e.subject LIKE ? OR e.summary LIKE ?
            ORDER BY e.date_parsed DESC
            LIMIT 1
        ''', (search_term, search_term))
        
        email = cursor.fetchone()
        if email:
            cursor.execute('''
                INSERT INTO lessons (module_id, title, content, order_index)
                VALUES (?, ?, ?, ?)
            ''', (
                module_id,
                f"Understanding {topic}",
                email['summary'] or f"Learn about {topic} and its applications in AI.",
                lessons_created + 1
            ))
            lesson_id = cursor.lastrowid
            
            # Link the source email
            cursor.execute('''
                INSERT OR IGNORE INTO lesson_sources (lesson_id, email_id)
                VALUES (?, ?)
            ''', (lesson_id, email['id']))
            
            lessons_created += 1
    
    return lessons_created


def get_curriculum():
    """Get all modules with lesson counts."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT m.*, 
                   (SELECT COUNT(*) FROM lessons l WHERE l.module_id = m.id) as lesson_count
            FROM modules m
            ORDER BY m.order_index
        ''')
        
        modules = []
        for row in cursor.fetchall():
            modules.append({
                'id': row['id'],
                'title': row['title'],
                'description': row['description'],
                'order': row['order_index'],
                'estimated_hours': row['estimated_hours'],
                'lesson_count': row['lesson_count']
            })
        
        return modules


def get_module_details(module_id):
    """Get detailed module information including lessons."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM modules WHERE id = ?', (module_id,))
        module = cursor.fetchone()
        if not module:
            return None
        
        # Get lessons
        cursor.execute('''
            SELECT * FROM lessons WHERE module_id = ? ORDER BY order_index
        ''', (module_id,))
        
        lessons = [dict(row) for row in cursor.fetchall()]
        
        # Get user progress for each lesson
        cursor.execute('''
            SELECT lesson_id, status, completed_at
            FROM user_progress
            WHERE module_id = ?
        ''', (module_id,))
        
        progress = {row['lesson_id']: row for row in cursor.fetchall()}
        
        for lesson in lessons:
            lesson['progress'] = progress.get(lesson['id'], {
                'status': 'not_started',
                'completed_at': None
            })
        
        return {
            'id': module['id'],
            'title': module['title'],
            'description': module['description'],
            'estimated_hours': module['estimated_hours'],
            'lessons': lessons
        }


def mark_lesson_complete(lesson_id, score=None):
    """Mark a lesson as complete and record progress."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Get module_id for the lesson
        cursor.execute('SELECT module_id FROM lessons WHERE id = ?', (lesson_id,))
        lesson = cursor.fetchone()
        if not lesson:
            return False
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_progress (lesson_id, module_id, status, score, completed_at)
            VALUES (?, ?, 'completed', ?, ?)
        ''', (lesson_id, lesson['module_id'], score, datetime.now().isoformat()))
        
        conn.commit()
        return True


def get_user_progress_summary():
    """Get overall learning progress summary."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Total lessons
        cursor.execute('SELECT COUNT(*) FROM lessons')
        total_lessons = cursor.fetchone()[0]
        
        # Completed lessons
        cursor.execute("SELECT COUNT(*) FROM user_progress WHERE status = 'completed'")
        completed = cursor.fetchone()[0]
        
        # Total modules
        cursor.execute('SELECT COUNT(*) FROM modules')
        total_modules = cursor.fetchone()[0]
        
        # Completed modules (all lessons done)
        cursor.execute('''
            SELECT COUNT(DISTINCT m.id)
            FROM modules m
            WHERE NOT EXISTS (
                SELECT 1 FROM lessons l
                WHERE l.module_id = m.id
                AND NOT EXISTS (
                    SELECT 1 FROM user_progress up
                    WHERE up.lesson_id = l.id AND up.status = 'completed'
                )
            ) AND EXISTS (SELECT 1 FROM lessons WHERE module_id = m.id)
        ''')
        completed_modules = cursor.fetchone()[0]
        
        # Average score
        cursor.execute('SELECT AVG(score) FROM user_progress WHERE score IS NOT NULL')
        avg_score = cursor.fetchone()[0] or 0
        
        return {
            'total_lessons': total_lessons,
            'completed_lessons': completed,
            'completion_percent': round(completed / total_lessons * 100, 1) if total_lessons > 0 else 0,
            'total_modules': total_modules,
            'completed_modules': completed_modules,
            'average_score': round(avg_score, 1)
        }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--init', action='store_true', help='Initialize curriculum')
    args = parser.parse_args()
    
    if args.init:
        initialize_curriculum()
    
    print("\n=== Curriculum ===")
    for module in get_curriculum():
        print(f"  {module['order']}. {module['title']} ({module['lesson_count']} lessons)")
    
    print("\n=== Progress ===")
    progress = get_user_progress_summary()
    print(f"  Completed: {progress['completed_lessons']}/{progress['total_lessons']} lessons ({progress['completion_percent']}%)")
