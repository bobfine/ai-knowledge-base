"""
Tool tracking service for AI Knowledge Base.
Extracts and tracks mentions of AI tools, products, and platforms.
"""

import os
import sys
import re
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_connection


# Tool/Product dictionary with variations and categories
TOOLS_DICTIONARY = {
    # AI Coding IDEs & Assistants
    'Claude Code': {
        'patterns': [r'\bclaude\s*code\b', r'\bclaudecode\b'],
        'category': 'AI Coding IDE',
        'company': 'Anthropic'
    },
    'Cursor': {
        'patterns': [r'\bcursor\b(?!\s*position)', r'\bcursor\.ai\b', r'\bcursor\s+ai\b'],
        'category': 'AI Coding IDE',
        'company': 'Cursor Inc'
    },
    'Windsurf': {
        'patterns': [r'\bwindsurf\b', r'\bcodeium\b'],
        'category': 'AI Coding IDE',
        'company': 'Codeium'
    },
    'GitHub Copilot': {
        'patterns': [r'\bcopilot\b', r'\bgithub\s*copilot\b'],
        'category': 'AI Coding IDE',
        'company': 'GitHub/Microsoft'
    },
    'Devin': {
        'patterns': [r'\bdevin\b'],
        'category': 'AI Coding Agent',
        'company': 'Cognition'
    },
    
    # No-Code/Low-Code Builders
    'Lovable': {
        'patterns': [r'\blovable\b', r'\blovable\.dev\b'],
        'category': 'No-Code Builder',
        'company': 'Lovable'
    },
    'Bolt': {
        'patterns': [r'\bbolt\s*new\b', r'\bbolt\.new\b'],
        'category': 'No-Code Builder',
        'company': 'StackBlitz'
    },
    'Replit': {
        'patterns': [r'\breplit\b'],
        'category': 'No-Code Builder',
        'company': 'Replit'
    },
    'v0': {
        'patterns': [r'\bv0\b', r'\bv0\.dev\b'],
        'category': 'No-Code Builder',
        'company': 'Vercel'
    },
    
    # LLM Models & Providers
    'Claude': {
        'patterns': [r'\bclaude\b(?!\s*code)'],
        'category': 'LLM',
        'company': 'Anthropic'
    },
    'GPT-4': {
        'patterns': [r'\bgpt-?4\b', r'\bgpt4\b'],
        'category': 'LLM',
        'company': 'OpenAI'
    },
    'GPT-4o': {
        'patterns': [r'\bgpt-?4o\b', r'\bo1\b', r'\bo3\b'],
        'category': 'LLM',
        'company': 'OpenAI'
    },
    'ChatGPT': {
        'patterns': [r'\bchatgpt\b'],
        'category': 'LLM',
        'company': 'OpenAI'
    },
    'Gemini': {
        'patterns': [r'\bgemini\b'],
        'category': 'LLM',
        'company': 'Google'
    },
    'DeepSeek': {
        'patterns': [r'\bdeepseek\b'],
        'category': 'LLM',
        'company': 'DeepSeek'
    },
    'Qwen': {
        'patterns': [r'\bqwen\b'],
        'category': 'LLM',
        'company': 'Alibaba'
    },
    
    # AI Platforms & Tools
    'MCP': {
        'patterns': [r'\bmcp\b', r'\bmodel\s*context\s*protocol\b'],
        'category': 'Protocol',
        'company': 'Anthropic'
    },
    'Perplexity': {
        'patterns': [r'\bperplexity\b'],
        'category': 'AI Search',
        'company': 'Perplexity AI'
    },
    'NotebookLM': {
        'patterns': [r'\bnotebooklm\b', r'\bnotebook\s*lm\b'],
        'category': 'AI Notes',
        'company': 'Google'
    },
    'Midjourney': {
        'patterns': [r'\bmidjourney\b'],
        'category': 'AI Image',
        'company': 'Midjourney'
    },
    'DALL-E': {
        'patterns': [r'\bdall-?e\b', r'\bdalle\b'],
        'category': 'AI Image',
        'company': 'OpenAI'
    },
    'Stable Diffusion': {
        'patterns': [r'\bstable\s*diffusion\b'],
        'category': 'AI Image',
        'company': 'Stability AI'
    },
    
    # Companies (broader matching)
    'Anthropic': {
        'patterns': [r'\banthropic\b'],
        'category': 'Company',
        'company': 'Anthropic'
    },
    'OpenAI': {
        'patterns': [r'\bopenai\b'],
        'category': 'Company',
        'company': 'OpenAI'
    },
    'Google': {
        'patterns': [r'\bgoogle\b(?!\s*search)'],
        'category': 'Company',
        'company': 'Google'
    },
    
    # Concepts & Techniques
    'Vibe Coding': {
        'patterns': [r'\bvibe\s*coding\b', r'\bvibe-coding\b', r'\bvibecoding\b'],
        'category': 'Concept',
        'company': None
    },
    'RAG': {
        'patterns': [r'\brag\b(?!\w)', r'\bretrieval\s*augmented\b'],
        'category': 'Technique',
        'company': None
    },
    'Prompt Engineering': {
        'patterns': [r'\bprompt\s*engineering\b'],
        'category': 'Technique',
        'company': None
    },
}


def extract_tool_mentions(text):
    """Extract mentions of known tools from text."""
    text_lower = text.lower()
    mentions = []
    
    for tool_name, tool_info in TOOLS_DICTIONARY.items():
        for pattern in tool_info['patterns']:
            if re.search(pattern, text_lower, re.IGNORECASE):
                mentions.append({
                    'name': tool_name,
                    'category': tool_info['category'],
                    'company': tool_info['company']
                })
                break  # Only count once per tool
    
    return mentions


def populate_tools_table():
    """Scan all emails and populate the tools table with mentions."""
    print("Scanning emails for tool mentions...")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Clear existing tool data
        cursor.execute('DELETE FROM tool_mentions')
        cursor.execute('DELETE FROM tools')
        
        # Get all emails
        cursor.execute('SELECT id, subject, content, date_parsed FROM emails')
        emails = cursor.fetchall()
        
        tool_stats = defaultdict(lambda: {
            'first_mention': None,
            'last_mention': None,
            'count': 0,
            'email_ids': []
        })
        
        for email in emails:
            text = f"{email['subject'] or ''} {email['content'] or ''}"
            mentions = extract_tool_mentions(text)
            date_parsed = email['date_parsed']
            
            for mention in mentions:
                tool_name = mention['name']
                tool_stats[tool_name]['count'] += 1
                tool_stats[tool_name]['email_ids'].append(email['id'])
                tool_stats[tool_name]['category'] = mention['category']
                tool_stats[tool_name]['company'] = mention['company']
                
                if date_parsed:
                    if tool_stats[tool_name]['first_mention'] is None or date_parsed < tool_stats[tool_name]['first_mention']:
                        tool_stats[tool_name]['first_mention'] = date_parsed
                    if tool_stats[tool_name]['last_mention'] is None or date_parsed > tool_stats[tool_name]['last_mention']:
                        tool_stats[tool_name]['last_mention'] = date_parsed
        
        # Insert tools
        for tool_name, stats in tool_stats.items():
            cursor.execute('''
                INSERT INTO tools (name, normalized_name, category, first_mention, last_mention, mention_count)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                tool_name,
                tool_name.lower().replace(' ', '_'),
                stats['category'],
                stats['first_mention'],
                stats['last_mention'],
                stats['count']
            ))
            tool_id = cursor.lastrowid
            
            # Insert tool mentions
            for email_id in stats['email_ids']:
                cursor.execute('''
                    INSERT OR IGNORE INTO tool_mentions (email_id, tool_id)
                    VALUES (?, ?)
                ''', (email_id, tool_id))
        
        conn.commit()
        
        print(f"   Found {len(tool_stats)} unique tools")
        print(f"   Total mentions: {sum(s['count'] for s in tool_stats.values())}")
        
        return len(tool_stats)


def get_tool_rankings(limit=20):
    """Get tools ranked by mention count."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT name, category, mention_count, first_mention, last_mention
            FROM tools
            ORDER BY mention_count DESC
            LIMIT ?
        ''', (limit,))
        
        return [
            {
                'name': row['name'],
                'category': row['category'],
                'mentions': row['mention_count'],
                'first_seen': row['first_mention'][:10] if row['first_mention'] else None,
                'last_seen': row['last_mention'][:10] if row['last_mention'] else None
            }
            for row in cursor.fetchall()
        ]


def get_tool_comparison():
    """Get tool comparison matrix data for the dashboard."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Get tools with recent activity
        cursor.execute('''
            SELECT 
                t.name, 
                t.category,
                t.mention_count,
                t.last_mention,
                t.avg_sentiment
            FROM tools t
            ORDER BY t.mention_count DESC
            LIMIT 15
        ''')
        
        tools = []
        for row in cursor.fetchall():
            # Calculate "heat" based on recency and mentions
            tools.append({
                'name': row['name'],
                'category': row['category'],
                'mentions': row['mention_count'],
                'last_activity': row['last_mention'][:10] if row['last_mention'] else 'Unknown',
                'sentiment': row['avg_sentiment'] or 0,
                'sentiment_label': 'positive' if (row['avg_sentiment'] or 0) >= 0 else 'negative'
            })
        
        return tools


def get_tools_by_category():
    """Get tools grouped by category."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT category, name, mention_count
            FROM tools
            ORDER BY category, mention_count DESC
        ''')
        
        categories = defaultdict(list)
        for row in cursor.fetchall():
            categories[row['category']].append({
                'name': row['name'],
                'mentions': row['mention_count']
            })
        
        return dict(categories)


def get_tool_details(tool_name):
    """Get detailed information about a specific tool."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM tools WHERE name = ?', (tool_name,))
        tool = cursor.fetchone()
        if not tool:
            return None
        
        # Get related emails
        cursor.execute('''
            SELECT e.id, e.subject, e.summary, e.date_parsed
            FROM emails e
            JOIN tool_mentions tm ON e.id = tm.email_id
            JOIN tools t ON tm.tool_id = t.id
            WHERE t.name = ?
            ORDER BY e.date_parsed DESC
            LIMIT 20
        ''', (tool_name,))
        
        emails = [
            {
                'id': row['id'],
                'subject': row['subject'],
                'summary': row['summary'],
                'date': row['date_parsed'][:10] if row['date_parsed'] else None
            }
            for row in cursor.fetchall()
        ]
        
        return {
            'name': tool['name'],
            'category': tool['category'],
            'mentions': tool['mention_count'],
            'first_seen': tool['first_mention'][:10] if tool['first_mention'] else None,
            'last_seen': tool['last_mention'][:10] if tool['last_mention'] else None,
            'emails': emails
        }


if __name__ == '__main__':
    # Populate tools table
    populate_tools_table()
    
    print("\n=== Tool Rankings ===")
    for tool in get_tool_rankings(15):
        print(f"  {tool['name']}: {tool['mentions']} mentions ({tool['category']})")
    
    print("\n=== Tools by Category ===")
    for category, tools in get_tools_by_category().items():
        tool_names = ', '.join(t['name'] for t in tools[:3])
        print(f"  {category}: {tool_names}")
