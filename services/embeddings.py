"""
Embeddings service for AI Knowledge Base.
Generates and stores vector embeddings for semantic search.
"""

import os
import sys
import json
import struct
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_connection


def get_openai_client():
    """Get OpenAI client with appropriate API key."""
    try:
        from openai import OpenAI
        api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('AI_INTEGRATIONS_OPENAI_API_KEY')
        if not api_key:
            return None
        base_url = os.environ.get('AI_INTEGRATIONS_OPENAI_BASE_URL')
        if base_url:
            return OpenAI(api_key=api_key, base_url=base_url)
        return OpenAI(api_key=api_key)
    except Exception as e:
        print(f"Could not initialize OpenAI: {e}")
        return None


def embed_text(text, client=None):
    """Generate embedding for a single text."""
    if client is None:
        client = get_openai_client()
        if client is None:
            return None
    
    try:
        # Truncate text to fit model limits (8192 tokens ~ 30000 chars)
        text = text[:25000] if len(text) > 25000 else text
        
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Embedding error: {e}")
        return None


def embed_texts_batch(texts, client=None, batch_size=100):
    """Generate embeddings for multiple texts in batches."""
    if client is None:
        client = get_openai_client()
        if client is None:
            return [None] * len(texts)
    
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        # Truncate texts
        batch = [t[:25000] if len(t) > 25000 else t for t in batch]
        
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=batch
            )
            all_embeddings.extend([d.embedding for d in response.data])
        except Exception as e:
            print(f"Batch embedding error: {e}")
            all_embeddings.extend([None] * len(batch))
    
    return all_embeddings


def embedding_to_blob(embedding):
    """Convert embedding list to binary blob for SQLite storage."""
    if embedding is None:
        return None
    return struct.pack(f'{len(embedding)}f', *embedding)


def blob_to_embedding(blob):
    """Convert binary blob back to embedding list."""
    if blob is None:
        return None
    count = len(blob) // 4  # 4 bytes per float
    return list(struct.unpack(f'{count}f', blob))


def cosine_similarity(a, b):
    """Calculate cosine similarity between two embeddings."""
    if a is None or b is None:
        return 0.0
    
    dot_product = sum(x * y for x, y in zip(a, b))
    magnitude_a = sum(x * x for x in a) ** 0.5
    magnitude_b = sum(x * x for x in b) ** 0.5
    
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    
    return dot_product / (magnitude_a * magnitude_b)


def generate_all_embeddings(limit=None):
    """Generate embeddings for all emails that don't have them."""
    print("Generating embeddings for emails...")
    
    client = get_openai_client()
    if client is None:
        print("❌ No OpenAI API key available. Cannot generate embeddings.")
        return 0
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Get emails without embeddings
        if limit:
            cursor.execute('''
                SELECT id, subject, content, summary 
                FROM emails 
                WHERE embedding IS NULL
                LIMIT ?
            ''', (limit,))
        else:
            cursor.execute('''
                SELECT id, subject, content, summary 
                FROM emails 
                WHERE embedding IS NULL
            ''')
        
        emails = cursor.fetchall()
        
        if not emails:
            print("All emails already have embeddings.")
            return 0
        
        print(f"Processing {len(emails)} emails...")
        
        # Prepare texts for embedding
        texts = []
        for email in emails:
            # Combine subject + summary for embedding (more focused than full content)
            text = f"{email['subject'] or ''}\n\n{email['summary'] or email['content'][:500] or ''}"
            texts.append(text)
        
        # Generate embeddings in batches
        embeddings = embed_texts_batch(texts, client)
        
        # Store embeddings
        updated = 0
        for email, embedding in zip(emails, embeddings):
            if embedding:
                blob = embedding_to_blob(embedding)
                cursor.execute('''
                    UPDATE emails SET embedding = ? WHERE id = ?
                ''', (blob, email['id']))
                updated += 1
            
            if updated % 100 == 0 and updated > 0:
                print(f"  Progress: {updated}/{len(emails)} embeddings stored...")
                conn.commit()
        
        conn.commit()
        print(f"\n✅ Generated {updated} embeddings successfully!")
        return updated


def semantic_search(query, limit=10):
    """Search emails by semantic similarity to query."""
    client = get_openai_client()
    if client is None:
        print("No API key - falling back to keyword search")
        return keyword_search(query, limit)
    
    # Get query embedding
    query_embedding = embed_text(query, client)
    if query_embedding is None:
        return keyword_search(query, limit)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Get all emails with embeddings
        cursor.execute('''
            SELECT id, subject, summary, date_parsed, embedding
            FROM emails
            WHERE embedding IS NOT NULL
        ''')
        
        results = []
        for row in cursor.fetchall():
            embedding = blob_to_embedding(row['embedding'])
            similarity = cosine_similarity(query_embedding, embedding)
            
            results.append({
                'id': row['id'],
                'subject': row['subject'],
                'summary': row['summary'],
                'date': row['date_parsed'][:10] if row['date_parsed'] else None,
                'similarity': round(similarity, 4)
            })
        
        # Sort by similarity
        results.sort(key=lambda x: x['similarity'], reverse=True)
        results = results[:limit]
        
        # Fetch links for top results (with enriched data)
        for r in results:
            cursor.execute('''
                SELECT url, domain, title, description 
                FROM email_links WHERE email_id = ? LIMIT 5
            ''', (r['id'],))
            r['links'] = [{
                'url': row['url'],
                'domain': row['domain'],
                'title': row['title'],
                'description': row['description']
            } for row in cursor.fetchall()]
        
        return results


def keyword_search(query, limit=10):
    """Fallback keyword search when embeddings unavailable."""
    with get_connection() as conn:
        cursor = conn.cursor()
        search_term = f'%{query}%'
        
        cursor.execute('''
            SELECT id, subject, summary, date_parsed
            FROM emails
            WHERE subject LIKE ? OR content LIKE ? OR summary LIKE ?
            ORDER BY date_parsed DESC
            LIMIT ?
        ''', (search_term, search_term, search_term, limit))
        
        results = []
        for row in cursor.fetchall():
            r = {
                'id': row['id'],
                'subject': row['subject'],
                'summary': row['summary'],
                'date': row['date_parsed'][:10] if row['date_parsed'] else None,
                'similarity': None  # Keyword search doesn't have similarity
            }
            # Fetch links with enriched data
            cursor.execute('''
                SELECT url, domain, title, description 
                FROM email_links WHERE email_id = ? LIMIT 5
            ''', (row['id'],))
            r['links'] = [{
                'url': link['url'],
                'domain': link['domain'],
                'title': link['title'],
                'description': link['description']
            } for link in cursor.fetchall()]
            results.append(r)
        
        return results


def get_embedding_stats():
    """Get statistics about embeddings in the database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM emails')
        total = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM emails WHERE embedding IS NOT NULL')
        with_embeddings = cursor.fetchone()[0]
        
        return {
            'total_emails': total,
            'with_embeddings': with_embeddings,
            'without_embeddings': total - with_embeddings,
            'coverage_percent': round(with_embeddings / total * 100, 1) if total > 0 else 0
        }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--generate', action='store_true', help='Generate embeddings')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of emails')
    parser.add_argument('--search', type=str, help='Test semantic search')
    parser.add_argument('--stats', action='store_true', help='Show embedding stats')
    args = parser.parse_args()
    
    if args.stats:
        stats = get_embedding_stats()
        print(f"Embedding Stats:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
    
    if args.generate:
        generate_all_embeddings(limit=args.limit)
    
    if args.search:
        print(f"\nSearching for: {args.search}")
        results = semantic_search(args.search)
        for r in results[:5]:
            print(f"  [{r['similarity']:.3f}] {r['subject'][:60]}...")
