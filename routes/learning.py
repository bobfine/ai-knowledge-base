"""
Learning API routes for AI Knowledge Base.
Provides REST endpoints for the learning assistant.
"""

from flask import Blueprint, jsonify, request

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.curriculum import (
    get_curriculum,
    get_module_details,
    mark_lesson_complete,
    get_user_progress_summary,
    initialize_curriculum
)
from services.quiz import (
    get_quiz_for_lesson,
    grade_quiz,
    generate_quiz_llm,
    store_quiz_questions
)

learning_bp = Blueprint('learning', __name__, url_prefix='/api/learn')


@learning_bp.route('/curriculum')
def api_curriculum():
    """Get the full curriculum with progress."""
    modules = get_curriculum()
    progress = get_user_progress_summary()
    
    return jsonify({
        'modules': modules,
        'progress': progress
    })


@learning_bp.route('/modules/<int:module_id>')
def api_module(module_id):
    """Get details for a specific module."""
    module = get_module_details(module_id)
    if module:
        return jsonify(module)
    return jsonify({'error': 'Module not found'}), 404


@learning_bp.route('/lessons/<int:lesson_id>/complete', methods=['POST'])
def api_complete_lesson(lesson_id):
    """Mark a lesson as complete."""
    data = request.get_json() or {}
    score = data.get('score')
    
    success = mark_lesson_complete(lesson_id, score)
    if success:
        return jsonify({'success': True})
    return jsonify({'error': 'Lesson not found'}), 404


@learning_bp.route('/lessons/<int:lesson_id>')
def api_lesson_detail(lesson_id):
    """Get full lesson details including content and related emails."""
    from database import get_connection
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Get lesson info
        cursor.execute('''
            SELECT l.id, l.title, l.content, l.email_id, l.module_id,
                   m.title as module_title
            FROM lessons l
            JOIN modules m ON l.module_id = m.id
            WHERE l.id = ?
        ''', (lesson_id,))
        lesson = cursor.fetchone()
        
        if not lesson:
            return jsonify({'error': 'Lesson not found'}), 404
        
        # Get the source email for this lesson
        cursor.execute('''
            SELECT id, subject, content, summary, date
            FROM emails WHERE id = ?
        ''', (lesson['email_id'],))
        source_email = cursor.fetchone()
        
        # Get related emails by searching for similar topics
        related = []
        if source_email:
            keywords = lesson['title'].split()[:3]
            for keyword in keywords:
                cursor.execute('''
                    SELECT id, subject, summary, date FROM emails
                    WHERE (subject LIKE ? OR content LIKE ?)
                    AND id != ?
                    LIMIT 3
                ''', (f'%{keyword}%', f'%{keyword}%', lesson['email_id']))
                for row in cursor.fetchall():
                    if row['id'] not in [r['id'] for r in related]:
                        related.append(dict(row))
            related = related[:5]  # Limit to 5 related
        
        return jsonify({
            'id': lesson['id'],
            'title': lesson['title'],
            'content': lesson['content'],
            'module_title': lesson['module_title'],
            'source_email': dict(source_email) if source_email else None,
            'related_reading': related
        })


@learning_bp.route('/lessons/<int:lesson_id>/quiz')
def api_get_quiz(lesson_id):
    """Get quiz for a lesson."""
    questions = get_quiz_for_lesson(lesson_id)
    
    if not questions:
        # Generate quiz on demand if none exists
        from database import get_connection
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT title, content FROM lessons WHERE id = ?', (lesson_id,))
            lesson = cursor.fetchone()
            
            if lesson:
                questions = generate_quiz_llm(
                    lesson['title'],
                    lesson['content'] or f"Learning about {lesson['title']}"
                )
                store_quiz_questions(lesson_id, questions)
                questions = get_quiz_for_lesson(lesson_id)
    
    # Remove correct answers from response (client shouldn't know answers)
    safe_questions = [
        {
            'id': q['id'],
            'question': q['question'],
            'options': q['options']
        }
        for q in questions
    ]
    
    return jsonify({
        'lesson_id': lesson_id,
        'questions': safe_questions
    })


@learning_bp.route('/lessons/<int:lesson_id>/quiz/submit', methods=['POST'])
def api_submit_quiz(lesson_id):
    """Submit quiz answers for grading."""
    data = request.get_json()
    if not data or 'answers' not in data:
        return jsonify({'error': 'Answers required'}), 400
    
    result = grade_quiz(lesson_id, data['answers'])
    
    # If passed, mark lesson complete with score
    if result.get('passed'):
        mark_lesson_complete(lesson_id, result['score'])
    
    return jsonify(result)


@learning_bp.route('/progress')
def api_progress():
    """Get overall learning progress."""
    return jsonify(get_user_progress_summary())


@learning_bp.route('/init', methods=['POST'])
def api_init_curriculum():
    """Initialize the curriculum (usually done on first run)."""
    count = initialize_curriculum()
    return jsonify({'modules_created': count})
