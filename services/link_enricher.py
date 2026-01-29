"""
Link Enrichment Service for AI Knowledge Base.
Fetches metadata from URLs to provide context in search results.
"""

import os
import sys
import re
import time
from datetime import datetime
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_connection

# Rate limiting
REQUESTS_PER_SECOND = 1
last_request_time = 0


def get_domain(url):
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower().replace('www.', '')
    except:
        return None


def is_social_link(url):
    """Check if URL is a social media link that needs special handling."""
    social_domains = ['twitter.com', 'x.com', 't.co', 'linkedin.com', 'facebook.com']
    domain = get_domain(url)
    return domain in social_domains if domain else False


def is_video_link(url):
    """Check if URL is a video platform."""
    video_domains = ['youtube.com', 'youtu.be', 'vimeo.com']
    domain = get_domain(url)
    return domain in video_domains if domain else False


def rate_limit():
    """Enforce rate limiting between requests."""
    global last_request_time
    elapsed = time.time() - last_request_time
    if elapsed < 1.0 / REQUESTS_PER_SECOND:
        time.sleep(1.0 / REQUESTS_PER_SECOND - elapsed)
    last_request_time = time.time()


def fetch_url_metadata(url, timeout=10):
    """
    Fetch metadata from a URL.
    Returns dict with title, description, content_excerpt, or None on failure.
    """
    import requests
    from bs4 import BeautifulSoup
    
    rate_limit()
    
    try:
        # Follow redirects (important for t.co links)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        
        # Get final URL after redirects
        final_url = response.url
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title = None
        if soup.title:
            title = soup.title.string
        if not title:
            og_title = soup.find('meta', property='og:title')
            if og_title:
                title = og_title.get('content')
        
        # Extract description
        description = None
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            description = meta_desc.get('content')
        if not description:
            og_desc = soup.find('meta', property='og:description')
            if og_desc:
                description = og_desc.get('content')
        
        # Extract content excerpt (first paragraph or article text)
        content_excerpt = None
        article = soup.find('article')
        if article:
            paragraphs = article.find_all('p')
            if paragraphs:
                content_excerpt = ' '.join(p.get_text().strip() for p in paragraphs[:2])
        if not content_excerpt:
            paragraphs = soup.find_all('p')
            for p in paragraphs[:5]:
                text = p.get_text().strip()
                if len(text) > 50:
                    content_excerpt = text[:500]
                    break
        
        return {
            'title': title[:255] if title else None,
            'description': description[:500] if description else None,
            'content_excerpt': content_excerpt[:500] if content_excerpt else None,
            'final_url': final_url,
            'status': 'success'
        }
        
    except requests.exceptions.Timeout:
        return {'status': 'failed', 'error': 'timeout'}
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else 0
        if status_code == 404:
            return {'status': 'failed', 'error': '404'}
        return {'status': 'failed', 'error': f'http_{status_code}'}
    except Exception as e:
        return {'status': 'failed', 'error': str(e)[:100]}


def extract_twitter_info(url):
    """Extract username and tweet ID from Twitter/X URLs."""
    patterns = [
        r'(?:twitter\.com|x\.com)/(\w+)/status/(\d+)',
        r'(?:twitter\.com|x\.com)/(\w+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            groups = match.groups()
            username = groups[0]
            tweet_id = groups[1] if len(groups) > 1 else None
            
            return {
                'title': f'@{username}' + (f' tweet #{tweet_id[-6:]}' if tweet_id else ''),
                'description': f'Twitter/X post by @{username}',
                'content_excerpt': None,
                'status': 'success'
            }
    
    return {'status': 'skipped', 'error': 'could not parse twitter url'}


def enrich_single_link(link_id, url):
    """Enrich a single link and update the database."""
    domain = get_domain(url)
    
    # Handle Twitter/X links specially
    if domain in ['twitter.com', 'x.com', 't.co']:
        # For t.co, we'd need to follow the redirect first
        if domain == 't.co':
            result = fetch_url_metadata(url)
            if result['status'] == 'success':
                # Now extract twitter info from final URL
                final_url = result.get('final_url', url)
                if 'twitter.com' in final_url or 'x.com' in final_url:
                    twitter_info = extract_twitter_info(final_url)
                    result.update(twitter_info)
        else:
            result = extract_twitter_info(url)
    else:
        result = fetch_url_metadata(url)
    
    # Update database
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE email_links 
            SET title = ?, description = ?, content_excerpt = ?, 
                fetch_status = ?, fetched_at = ?
            WHERE id = ?
        ''', (
            result.get('title'),
            result.get('description'),
            result.get('content_excerpt'),
            result.get('status', 'failed'),
            datetime.now().isoformat(),
            link_id
        ))
        conn.commit()
    
    return result


def enrich_pending_links(limit=100, category=None):
    """
    Enrich links that haven't been fetched yet.
    Optionally filter by email category.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if category:
            cursor.execute('''
                SELECT el.id, el.url 
                FROM email_links el
                JOIN email_categories ec ON el.email_id = ec.email_id
                WHERE (el.fetch_status = 'pending' OR el.fetch_status IS NULL)
                AND ec.category = ?
                LIMIT ?
            ''', (category, limit))
        else:
            cursor.execute('''
                SELECT id, url FROM email_links 
                WHERE fetch_status = 'pending' OR fetch_status IS NULL
                LIMIT ?
            ''', (limit,))
        
        links = cursor.fetchall()
    
    print(f"Found {len(links)} links to enrich")
    
    results = {'success': 0, 'failed': 0, 'skipped': 0}
    
    for i, link in enumerate(links):
        link_id, url = link['id'], link['url']
        
        print(f"[{i+1}/{len(links)}] {url[:60]}...", end=' ')
        
        result = enrich_single_link(link_id, url)
        status = result.get('status', 'failed')
        results[status] = results.get(status, 0) + 1
        
        if status == 'success':
            print(f"✓ {result.get('title', '')[:40]}")
        else:
            print(f"✗ {result.get('error', 'unknown')}")
    
    return results


def get_enrichment_stats():
    """Get statistics about link enrichment progress."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM email_links')
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM email_links WHERE fetch_status = 'success'")
        success = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM email_links WHERE fetch_status = 'failed'")
        failed = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM email_links WHERE fetch_status = 'pending' OR fetch_status IS NULL")
        pending = cursor.fetchone()[0]
        
        return {
            'total_links': total,
            'enriched': success,
            'failed': failed,
            'pending': pending,
            'coverage_percent': round(success / total * 100, 1) if total > 0 else 0
        }


def estimate_token_usage(num_links):
    """Estimate token usage for AI-based processing."""
    # Average content size per enriched link
    avg_title_chars = 60
    avg_description_chars = 150
    avg_excerpt_chars = 300
    
    chars_per_link = avg_title_chars + avg_description_chars + avg_excerpt_chars
    tokens_per_char = 0.25  # Rough estimate: 4 chars per token
    
    total_chars = chars_per_link * num_links
    total_tokens = int(total_chars * tokens_per_char)
    
    return {
        'estimated_tokens': total_tokens,
        'chars_per_link': chars_per_link,
        'total_chars': total_chars
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Link enrichment service')
    parser.add_argument('--enrich', type=int, help='Enrich N links')
    parser.add_argument('--category', type=str, help='Filter by category')
    parser.add_argument('--stats', action='store_true', help='Show enrichment stats')
    parser.add_argument('--test', type=str, help='Test single URL')
    args = parser.parse_args()
    
    if args.stats:
        stats = get_enrichment_stats()
        print("Link Enrichment Statistics:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
    
    if args.test:
        print(f"Testing URL: {args.test}")
        result = fetch_url_metadata(args.test)
        for k, v in result.items():
            print(f"  {k}: {v}")
    
    if args.enrich:
        results = enrich_pending_links(limit=args.enrich, category=args.category)
        print(f"\nEnrichment complete: {results}")
