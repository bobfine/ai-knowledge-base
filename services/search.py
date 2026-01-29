"""
Search service for AI Knowledge Base.
Combines semantic search with AI-powered answer synthesis.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_connection
from services.embeddings import semantic_search, keyword_search, get_openai_client


def hybrid_search(query, limit=10):
    """
    Perform hybrid search combining semantic and keyword matching.
    Returns results with both similarity scores and keyword matches.
    """
    # Try semantic search first
    semantic_results = semantic_search(query, limit=limit)
    
    # Also do keyword search
    keyword_results = keyword_search(query, limit=limit)
    
    # Merge results, prioritizing semantic if available
    seen_ids = set()
    merged = []
    
    for result in semantic_results:
        if result['id'] not in seen_ids:
            result['match_type'] = 'semantic'
            merged.append(result)
            seen_ids.add(result['id'])
    
    for result in keyword_results:
        if result['id'] not in seen_ids:
            result['match_type'] = 'keyword'
            result['similarity'] = 0.0  # No semantic score
            merged.append(result)
            seen_ids.add(result['id'])
    
    return merged[:limit]


def synthesize_answer(query, results, openai_client=None):
    """
    Use LLM to synthesize an answer from search results.
    Returns both the answer and source citations.
    """
    if not results:
        return {
            'answer': "I couldn't find any relevant information for that query.",
            'sources': [],
            'ai_generated': False
        }
    
    if openai_client is None:
        openai_client = get_openai_client()
    
    if openai_client is None:
        # Return formatted results without AI synthesis
        return {
            'answer': format_results_as_text(results[:5]),
            'sources': results[:5],
            'ai_generated': False
        }
    
    # Build context from results
    context = "\n\n".join([
        f"[Source {i+1}] {r['subject']}\n{r['summary'] or 'No summary available'}"
        for i, r in enumerate(results[:5])
    ])
    
    prompt = f"""Based on the following information from an AI knowledge base, answer the user's question.

User Question: {query}

Relevant Information:
{context}

Instructions:
1. Synthesize a helpful answer based on the sources
2. Be concise but comprehensive
3. Cite sources using [Source N] notation when referencing specific information
4. If the sources don't fully answer the question, acknowledge limitations

Answer:"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant answering questions about AI tools, techniques, and industry developments."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        return {
            'answer': response.choices[0].message.content,
            'sources': [
                {
                    'id': r['id'],
                    'subject': r['subject'],
                    'date': r['date'],
                    'similarity': r.get('similarity')
                }
                for r in results[:5]
            ],
            'ai_generated': True
        }
        
    except Exception as e:
        print(f"Synthesis error: {e}")
        return {
            'answer': format_results_as_text(results[:5]),
            'sources': results[:5],
            'ai_generated': False
        }


def format_results_as_text(results):
    """Format search results as readable text (fallback)."""
    if not results:
        return "No results found."
    
    lines = ["Here's what I found:\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"**{i}. {r['subject']}**")
        if r.get('summary'):
            lines.append(f"   {r['summary'][:200]}...")
        if r.get('date'):
            lines.append(f"   📅 {r['date']}")
        lines.append("")
    
    return "\n".join(lines)


def get_related_searches(query, limit=5):
    """Suggest related searches based on entities in query results."""
    results = semantic_search(query, limit=3)
    
    if not results:
        return []
    
    # Get entities from the result emails
    with get_connection() as conn:
        cursor = conn.cursor()
        email_ids = [r['id'] for r in results]
        placeholders = ','.join('?' * len(email_ids))
        
        cursor.execute(f'''
            SELECT DISTINCT e.name, e.type, e.mention_count
            FROM entities e
            JOIN email_entities ee ON e.id = ee.entity_id
            WHERE ee.email_id IN ({placeholders})
            ORDER BY e.mention_count DESC
            LIMIT ?
        ''', email_ids + [limit])
        
        return [
            {
                'suggestion': f"More about {row['name']}",
                'entity': row['name'],
                'type': row['type']
            }
            for row in cursor.fetchall()
        ]


def search_with_filters(query, filters=None, limit=10):
    """
    Search with optional filters for category, date range, entity.
    """
    base_results = hybrid_search(query, limit=limit * 2)  # Get more, then filter
    
    if not filters:
        return base_results[:limit]
    
    filtered = []
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        for result in base_results:
            include = True
            
            # Category filter
            if 'category' in filters:
                cursor.execute('''
                    SELECT 1 FROM email_categories 
                    WHERE email_id = ? AND category = ?
                ''', (result['id'], filters['category']))
                if not cursor.fetchone():
                    include = False
            
            # Date filter
            if include and 'date_from' in filters:
                cursor.execute('''
                    SELECT date_parsed FROM emails WHERE id = ?
                ''', (result['id'],))
                row = cursor.fetchone()
                if row and row['date_parsed'] and row['date_parsed'] < filters['date_from']:
                    include = False
            
            if include and 'date_to' in filters:
                cursor.execute('''
                    SELECT date_parsed FROM emails WHERE id = ?
                ''', (result['id'],))
                row = cursor.fetchone()
                if row and row['date_parsed'] and row['date_parsed'] > filters['date_to']:
                    include = False
            
            # Entity filter
            if include and 'entity' in filters:
                cursor.execute('''
                    SELECT 1 FROM email_entities ee
                    JOIN entities e ON ee.entity_id = e.id
                    WHERE ee.email_id = ? AND e.name = ?
                ''', (result['id'], filters['entity']))
                if not cursor.fetchone():
                    include = False
            
            if include:
                filtered.append(result)
                if len(filtered) >= limit:
                    break
    
    return filtered


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('query', nargs='?', help='Search query')
    parser.add_argument('--synthesize', action='store_true', help='Include AI synthesis')
    args = parser.parse_args()
    
    if args.query:
        print(f"Searching for: {args.query}\n")
        
        results = hybrid_search(args.query, limit=5)
        
        print("=== Search Results ===")
        for r in results:
            sim = f"[{r['similarity']:.3f}]" if r.get('similarity') else "[keyword]"
            print(f"{sim} {r['subject'][:60]}...")
        
        if args.synthesize:
            print("\n=== AI Synthesis ===")
            synthesis = synthesize_answer(args.query, results)
            print(synthesis['answer'])
    else:
        print("Usage: python search.py 'your query' [--synthesize]")
