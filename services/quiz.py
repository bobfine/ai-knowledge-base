"""
Quiz generator service for AI Knowledge Base.
Generates quizzes from learning content to test knowledge.
"""

import os
import sys
import json
import random
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_connection


def get_openai_client():
    """Get OpenAI client if available."""
    try:
        from openai import OpenAI
        api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('AI_INTEGRATIONS_OPENAI_API_KEY')
        if not api_key:
            return None
        return OpenAI(api_key=api_key)
    except Exception:
        return None


def generate_quiz_llm(topic, lesson_content, num_questions=3):
    """Generate quiz questions using LLM."""
    client = get_openai_client()
    if not client:
        return generate_quiz_fallback(topic, num_questions)
    
    prompt = f"""Generate {num_questions} multiple choice quiz questions about "{topic}" based on this content:

{lesson_content[:2000]}

Return JSON array with this format:
[
  {{
    "question": "Question text?",
    "options": ["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4"],
    "correct_answer": "A",
    "explanation": "Brief explanation of correct answer"
  }}
]

Only return valid JSON, no other text."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a quiz generator. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        content = response.choices[0].message.content.strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1].rsplit('```', 1)[0]
        
        questions = json.loads(content)
        return questions
        
    except Exception as e:
        print(f"Quiz generation error: {e}")
        return generate_quiz_fallback(topic, num_questions)


def generate_quiz_fallback(topic, num_questions=3):
    """Generate basic fallback quiz questions when API unavailable."""
    templates = [
        {
            "question": f"What is {topic} primarily used for?",
            "options": ["A. Data storage", "B. AI-powered functionality", "C. Network management", "D. Hardware control"],
            "correct_answer": "B",
            "explanation": f"{topic} is an AI-related technology focused on intelligent automation and assistance."
        },
        {
            "question": f"Which category best describes {topic}?",
            "options": ["A. AI Tool", "B. Database System", "C. Operating System", "D. Networking Protocol"],
            "correct_answer": "A",
            "explanation": f"{topic} falls under AI tools and technologies."
        },
        {
            "question": f"What is a key benefit of using {topic}?",
            "options": ["A. Reduced electricity usage", "B. Increased productivity through AI assistance", "C. Better internet speed", "D. Improved printer quality"],
            "correct_answer": "B",
            "explanation": f"{topic} helps users be more productive by leveraging AI capabilities."
        }
    ]
    
    return templates[:num_questions]


def store_quiz_questions(lesson_id, questions):
    """Store generated quiz questions in the database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Clear existing questions for this lesson
        cursor.execute('DELETE FROM quiz_questions WHERE lesson_id = ?', (lesson_id,))
        
        for i, q in enumerate(questions):
            cursor.execute('''
                INSERT INTO quiz_questions (lesson_id, question_text, options_json, correct_answer, explanation, order_index)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                lesson_id,
                q['question'],
                json.dumps(q['options']),
                q['correct_answer'],
                q.get('explanation', ''),
                i + 1
            ))
        
        conn.commit()
        return len(questions)


def get_quiz_for_lesson(lesson_id):
    """Get quiz questions for a specific lesson."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM quiz_questions WHERE lesson_id = ? ORDER BY order_index
        ''', (lesson_id,))
        
        questions = []
        for row in cursor.fetchall():
            questions.append({
                'id': row['id'],
                'question': row['question_text'],
                'options': json.loads(row['options_json']),
                'correct_answer': row['correct_answer'],
                'explanation': row['explanation']
            })
        
        return questions


def grade_quiz(lesson_id, answers):
    """
    Grade a completed quiz.
    
    answers: dict of {question_id: user_answer}
    Returns: score and feedback
    """
    questions = get_quiz_for_lesson(lesson_id)
    
    if not questions:
        return {'error': 'No quiz found for this lesson'}
    
    correct = 0
    total = len(questions)
    feedback = []
    
    for q in questions:
        user_answer = answers.get(str(q['id']), '')
        is_correct = user_answer.upper() == q['correct_answer'].upper()
        
        if is_correct:
            correct += 1
        
        feedback.append({
            'question': q['question'],
            'your_answer': user_answer,
            'correct_answer': q['correct_answer'],
            'is_correct': is_correct,
            'explanation': q['explanation']
        })
    
    score = round((correct / total) * 100) if total > 0 else 0
    
    return {
        'score': score,
        'correct': correct,
        'total': total,
        'passed': score >= 70,
        'feedback': feedback
    }


def generate_all_quizzes(force=False):
    """Generate quizzes for all lessons that don't have them."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if force:
            cursor.execute('SELECT id, title, content FROM lessons')
        else:
            cursor.execute('''
                SELECT l.id, l.title, l.content
                FROM lessons l
                WHERE NOT EXISTS (
                    SELECT 1 FROM quiz_questions q WHERE q.lesson_id = l.id
                )
            ''')
        
        lessons = cursor.fetchall()
        
        for lesson in lessons:
            print(f"Generating quiz for: {lesson['title']}")
            questions = generate_quiz_llm(
                lesson['title'],
                lesson['content'] or f"Learning about {lesson['title']}",
                num_questions=3
            )
            store_quiz_questions(lesson['id'], questions)
        
        print(f"✅ Generated quizzes for {len(lessons)} lessons")
        return len(lessons)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--generate', action='store_true', help='Generate quizzes')
    parser.add_argument('--force', action='store_true', help='Regenerate all quizzes')
    args = parser.parse_args()
    
    if args.generate:
        generate_all_quizzes(force=args.force)
    else:
        # Show quiz stats
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM quiz_questions')
            count = cursor.fetchone()[0]
            print(f"Quiz questions in database: {count}")
