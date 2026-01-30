"""
Learning curriculum service for AI Knowledge Base.
Generates personalized learning paths based on categories.
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_connection


def get_category_based_curriculum():
    """
    Generate curriculum modules based on actual email categories.
    Creates learning paths from the 27 granular categories.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Get all categories with at least 3 emails
        cursor.execute('''
            SELECT category, COUNT(*) as count 
            FROM email_categories 
            GROUP BY category 
            HAVING count >= 3
            ORDER BY count DESC
        ''')
        categories = cursor.fetchall()
        
        curriculum = []
        order = 1
        
        # Define module descriptions and estimated hours for each category
        category_meta = {
            'Claude & Anthropic': ('Master Claude AI, Claude Code, and Anthropic products for development and productivity.', 5),
            'OpenAI & GPT': ('Deep dive into ChatGPT, GPT-4, and the OpenAI ecosystem.', 5),
            'Google & Gemini': ('Explore Google\'s AI tools including Gemini, NotebookLM, and AI Studio.', 4),
            'AI Agents': ('Build and understand autonomous AI agents and agentic workflows.', 6),
            'AI for Business': ('Apply AI to business productivity, workflows, and enterprise use cases.', 5),
            'Tool Announcements': ('Stay current with the latest AI tool launches and updates.', 3),
            'AI News & Industry': ('Understand AI industry trends, funding, and market dynamics.', 3),
            'Prompt Engineering': ('Master the art and science of writing effective AI prompts.', 5),
            'Learning Resources': ('Curated learning materials and educational content about AI.', 4),
            'Developer Resources': ('API tutorials, documentation, and developer guides.', 4),
            'AI Visual Tools': ('Image generation, video AI, and visual creative tools.', 4),
            'AI Research & Reports': ('Academic papers, benchmarks, and industry research.', 4),
            'No-Code/Low-Code': ('Build AI applications without traditional coding using Bolt, Lovable, v0.', 4),
            'AI Coding IDEs': ('AI-powered code editors and development environments.', 4),
            'Physical AI & Robotics': ('Robots, embodied AI, and physical world applications.', 3),
            'AI Automation': ('Workflow automation with AI using n8n, Zapier, and similar tools.', 4),
            'Vibe Coding': ('Natural language coding - describe what you want, AI builds it.', 4),
            'Cursor': ('Master the Cursor IDE for AI-assisted development.', 3),
            'MCP & Tool Integration': ('Model Context Protocol and tool integrations.', 3),
            'LLM & Models': ('Understand large language models, architectures, and training.', 5),
            'Replit': ('Build and deploy with Replit Agent and the Replit platform.', 3),
            'AI Safety & Ethics': ('AI alignment, interpretability, and responsible AI.', 3),
            'AI Audio & Music': ('Voice synthesis, music generation, and audio AI.', 3),
            'RAG & Embeddings': ('Retrieval-augmented generation and vector databases.', 4),
            'Perplexity': ('Master Perplexity AI for research and search.', 2),
            'Windsurf': ('Windsurf/Codeium for AI-assisted coding.', 2),
            'DeepSeek': ('Understanding DeepSeek models and capabilities.', 2),
        }
        
        for cat_row in categories:
            category = cat_row['category']
            count = cat_row['count']
            
            if category in category_meta:
                description, hours = category_meta[category]
            else:
                description = f'Learn about {category} through curated email content.'
                hours = 3
            
            # Calculate lessons (1 per 8-10 emails, min 2, max 8)
            lesson_count = max(2, min(8, count // 10 + 2))
            
            curriculum.append({
                'order': order,
                'title': category,
                'description': description,
                'category': category,  # Link to actual category
                'estimated_hours': hours,
                'target_lessons': lesson_count
            })
            order += 1
        
        return curriculum


def initialize_curriculum():
    """Initialize the category-based curriculum in the database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Clear existing curriculum to regenerate
        cursor.execute('DELETE FROM lesson_sources')
        cursor.execute('DELETE FROM quiz_questions')
        cursor.execute('DELETE FROM user_progress')
        cursor.execute('DELETE FROM lessons')
        cursor.execute('DELETE FROM modules')
        conn.commit()
        
        # Get category-based curriculum
        curriculum = get_category_based_curriculum()
        
        for module in curriculum:
            cursor.execute('''
                INSERT INTO modules (title, description, order_index, estimated_hours, topics_json)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                module['title'],
                module['description'],
                module['order'],
                module['estimated_hours'],
                str([module['category']])
            ))
            module_id = cursor.lastrowid
            
            # Create lessons from emails in this category
            create_lessons_for_category(cursor, module_id, module['category'], module['target_lessons'])
        
        conn.commit()
        print(f"✅ Initialized {len(curriculum)} curriculum modules from categories")
        return len(curriculum)


def create_lessons_for_category(cursor, module_id, category, max_lessons):
    """Create lessons from emails in a specific category."""
    
    # Get emails in this category
    cursor.execute('''
        SELECT e.id, e.subject, e.summary, e.date_parsed
        FROM emails e
        JOIN email_categories ec ON e.id = ec.email_id
        WHERE ec.category = ?
        GROUP BY e.id
        ORDER BY e.date_parsed DESC
        LIMIT ?
    ''', (category, max_lessons))
    
    emails = cursor.fetchall()
    
    for idx, email in enumerate(emails):
        # Create a rich lesson title
        title = email['subject'][:80] if email['subject'] else f"Lesson {idx + 1}: {category}"
        
        # Use summary as lesson content (enriched data is fetched at runtime)
        content = email['summary'] if email['summary'] else f"Learn about {category} concepts and applications."
        
        cursor.execute('''
            INSERT INTO lessons (module_id, title, content, order_index)
            VALUES (?, ?, ?, ?)
        ''', (module_id, title, content, idx + 1))
        
        lesson_id = cursor.lastrowid
        
        # Link source email
        cursor.execute('''
            INSERT OR IGNORE INTO lesson_sources (lesson_id, email_id)
            VALUES (?, ?)
        ''', (lesson_id, email['id']))


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
    parser.add_argument('--show', action='store_true', help='Show curriculum')
    args = parser.parse_args()
    
    if args.init:
        initialize_curriculum()
    
    print("\n=== Curriculum ===")
    for module in get_curriculum():
        print(f"  {module['order']}. {module['title']} ({module['lesson_count']} lessons)")
    
    print("\n=== Progress ===")
    progress = get_user_progress_summary()
    print(f"  Completed: {progress['completed_lessons']}/{progress['total_lessons']} lessons ({progress['completion_percent']}%)")
