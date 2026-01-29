"""
Entity extraction service for AI Knowledge Base.
Uses LLM to extract entities (tools, companies, concepts, people) from emails.
"""

import os
import sys
import json
import re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_connection


# Known entity patterns for quick extraction (no API needed)
KNOWN_ENTITIES = {
    # AI Tools & Products
    'Claude Code': 'tool',
    'Cursor': 'tool',
    'Windsurf': 'tool',
    'GitHub Copilot': 'tool',
    'Devin': 'tool',
    'Lovable': 'tool',
    'Bolt': 'tool',
    'v0': 'tool',
    'Replit': 'tool',
    'ChatGPT': 'tool',
    'GPT-4': 'tool',
    'GPT-4o': 'tool',
    'Claude': 'tool',
    'Gemini': 'tool',
    'Perplexity': 'tool',
    'NotebookLM': 'tool',
    'Midjourney': 'tool',
    'DALL-E': 'tool',
    'Stable Diffusion': 'tool',
    'DeepSeek': 'tool',
    'Qwen': 'tool',
    
    # Companies
    'Anthropic': 'company',
    'OpenAI': 'company',
    'Google': 'company',
    'Microsoft': 'company',
    'Meta': 'company',
    'Amazon': 'company',
    'Apple': 'company',
    'NVIDIA': 'company',
    'Cognition': 'company',
    'Codeium': 'company',
    'Vercel': 'company',
    'StackBlitz': 'company',
    
    # Concepts
    'Vibe Coding': 'concept',
    'MCP': 'concept',
    'RAG': 'concept',
    'Prompt Engineering': 'concept',
    'Fine-tuning': 'concept',
    'Embeddings': 'concept',
    'Vector Database': 'concept',
    'AI Agents': 'concept',
    'Agentic AI': 'concept',
    'Chain of Thought': 'concept',
    'Few-shot Learning': 'concept',
    'Context Window': 'concept',
}


def extract_entities_pattern(text):
    """Extract entities using pattern matching (no API needed)."""
    text_lower = text.lower()
    found = []
    
    for entity_name, entity_type in KNOWN_ENTITIES.items():
        pattern = re.escape(entity_name.lower())
        if re.search(r'\b' + pattern + r'\b', text_lower):
            found.append({
                'name': entity_name,
                'type': entity_type,
                'extraction_method': 'pattern'
            })
    
    return found


def extract_entities_llm(text, openai_client=None):
    """Extract entities using LLM for more nuanced extraction."""
    if openai_client is None:
        try:
            from openai import OpenAI
            api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('AI_INTEGRATIONS_OPENAI_API_KEY')
            if not api_key:
                return extract_entities_pattern(text)  # Fallback
            openai_client = OpenAI(api_key=api_key)
        except Exception as e:
            print(f"OpenAI client error: {e}")
            return extract_entities_pattern(text)
    
    prompt = f"""Extract named entities from the following text about AI technology.

Categories:
- tool: AI products, software, apps, models (e.g., Claude, Cursor, GPT-4)
- company: Organizations (e.g., Anthropic, OpenAI, Google)
- concept: Technical concepts, methodologies (e.g., RAG, embeddings, fine-tuning)
- person: Named individuals mentioned

Return JSON array only, no other text:
[{{"name": "entity name", "type": "category"}}]

Text:
{text[:2000]}
"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an entity extraction assistant. Return only valid JSON arrays."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0
        )
        
        content = response.choices[0].message.content.strip()
        # Clean up response
        if content.startswith('```'):
            content = content.split('\n', 1)[1].rsplit('```', 1)[0]
        
        entities = json.loads(content)
        for e in entities:
            e['extraction_method'] = 'llm'
        return entities
        
    except Exception as e:
        print(f"LLM extraction error: {e}")
        return extract_entities_pattern(text)


def populate_entities_table(use_llm=False, batch_size=50):
    """Extract entities from all emails and populate the database."""
    print(f"Extracting entities (LLM: {use_llm})...")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Clear existing entity data
        cursor.execute('DELETE FROM email_entities')
        cursor.execute('DELETE FROM entities')
        conn.commit()
        
        # Get all emails
        cursor.execute('SELECT id, subject, content, date_parsed FROM emails')
        emails = cursor.fetchall()
        
        entity_stats = {}  # name -> {type, first_seen, last_seen, count, email_ids}
        
        openai_client = None
        if use_llm:
            try:
                from openai import OpenAI
                api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('AI_INTEGRATIONS_OPENAI_API_KEY')
                if api_key:
                    openai_client = OpenAI(api_key=api_key)
            except Exception as e:
                print(f"Could not initialize OpenAI: {e}")
        
        for i, email in enumerate(emails):
            text = f"{email['subject'] or ''}\n{email['content'] or ''}"
            
            if use_llm and openai_client and (i < batch_size):  # Limit LLM calls
                entities = extract_entities_llm(text, openai_client)
            else:
                entities = extract_entities_pattern(text)
            
            date_parsed = email['date_parsed']
            
            for entity in entities:
                name = entity['name']
                if name not in entity_stats:
                    entity_stats[name] = {
                        'type': entity['type'],
                        'first_seen': date_parsed,
                        'last_seen': date_parsed,
                        'count': 0,
                        'email_ids': []
                    }
                
                entity_stats[name]['count'] += 1
                entity_stats[name]['email_ids'].append(email['id'])
                
                if date_parsed:
                    if entity_stats[name]['first_seen'] is None or date_parsed < entity_stats[name]['first_seen']:
                        entity_stats[name]['first_seen'] = date_parsed
                    if entity_stats[name]['last_seen'] is None or date_parsed > entity_stats[name]['last_seen']:
                        entity_stats[name]['last_seen'] = date_parsed
            
            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1}/{len(emails)} emails...")
        
        # Insert entities
        for name, stats in entity_stats.items():
            cursor.execute('''
                INSERT INTO entities (name, type, first_seen, last_seen, mention_count)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                name,
                stats['type'],
                stats['first_seen'],
                stats['last_seen'],
                stats['count']
            ))
            entity_id = cursor.lastrowid
            
            # Insert email-entity mappings
            for email_id in stats['email_ids']:
                cursor.execute('''
                    INSERT OR IGNORE INTO email_entities (email_id, entity_id)
                    VALUES (?, ?)
                ''', (email_id, entity_id))
        
        conn.commit()
        
        print(f"\n✅ Entity extraction complete!")
        print(f"   - Unique entities: {len(entity_stats)}")
        print(f"   - Total mentions: {sum(s['count'] for s in entity_stats.values())}")
        
        # Print by type
        type_counts = {}
        for stats in entity_stats.values():
            t = stats['type']
            type_counts[t] = type_counts.get(t, 0) + 1
        print(f"   - By type: {type_counts}")
        
        return len(entity_stats)


def get_entity_list(entity_type=None, limit=50):
    """Get list of entities, optionally filtered by type."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if entity_type:
            cursor.execute('''
                SELECT * FROM entities 
                WHERE type = ? 
                ORDER BY mention_count DESC 
                LIMIT ?
            ''', (entity_type, limit))
        else:
            cursor.execute('''
                SELECT * FROM entities 
                ORDER BY mention_count DESC 
                LIMIT ?
            ''', (limit,))
        
        return [dict(row) for row in cursor.fetchall()]


def get_entity_details(entity_name):
    """Get detailed information about an entity."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM entities WHERE name = ?', (entity_name,))
        entity = cursor.fetchone()
        if not entity:
            return None
        
        # Get related emails
        cursor.execute('''
            SELECT e.id, e.subject, e.summary, e.date_parsed
            FROM emails e
            JOIN email_entities ee ON e.id = ee.email_id
            WHERE ee.entity_id = ?
            ORDER BY e.date_parsed DESC
            LIMIT 20
        ''', (entity['id'],))
        
        emails = [dict(row) for row in cursor.fetchall()]
        
        # Get co-occurring entities
        cursor.execute('''
            SELECT e2.name, e2.type, COUNT(*) as co_occurrences
            FROM email_entities ee1
            JOIN email_entities ee2 ON ee1.email_id = ee2.email_id
            JOIN entities e2 ON ee2.entity_id = e2.id
            WHERE ee1.entity_id = ? AND ee2.entity_id != ?
            GROUP BY e2.id
            ORDER BY co_occurrences DESC
            LIMIT 10
        ''', (entity['id'], entity['id']))
        
        related = [dict(row) for row in cursor.fetchall()]
        
        return {
            'name': entity['name'],
            'type': entity['type'],
            'mention_count': entity['mention_count'],
            'first_seen': entity['first_seen'],
            'last_seen': entity['last_seen'],
            'emails': emails,
            'related_entities': related
        }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--llm', action='store_true', help='Use LLM for extraction')
    args = parser.parse_args()
    
    populate_entities_table(use_llm=args.llm)
    
    print("\n=== Top Entities ===")
    for entity in get_entity_list(limit=15):
        print(f"  {entity['name']} ({entity['type']}): {entity['mention_count']} mentions")
