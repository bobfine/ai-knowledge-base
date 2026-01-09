import mailbox
import re
import email
from email.header import decode_header
from collections import defaultdict
import json
from html import escape
import quopri

def decode_mime_header(header):
    """Decode MIME encoded header."""
    if not header:
        return ""
    decoded_parts = []
    for part, encoding in decode_header(header):
        if isinstance(part, bytes):
            try:
                decoded_parts.append(part.decode(encoding or 'utf-8', errors='replace'))
            except:
                decoded_parts.append(part.decode('utf-8', errors='replace'))
        else:
            decoded_parts.append(part)
    return ''.join(decoded_parts)

def strip_html_tags(html_content):
    """Remove HTML tags and decode entities."""
    clean = re.sub(r'<[^>]+>', ' ', html_content)
    clean = re.sub(r'&nbsp;', ' ', clean)
    clean = re.sub(r'&amp;', '&', clean)
    clean = re.sub(r'&lt;', '<', clean)
    clean = re.sub(r'&gt;', '>', clean)
    clean = re.sub(r'&quot;', '"', clean)
    clean = re.sub(r'&#39;', "'", clean)
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()

def extract_text_content(msg):
    """Extract text content from email message, with HTML fallback."""
    text_content = ""
    html_content = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            payload = part.get_payload(decode=True)
            if payload:
                charset = part.get_content_charset() or 'utf-8'
                try:
                    decoded = payload.decode(charset, errors='replace')
                except:
                    decoded = payload.decode('utf-8', errors='replace')
                
                if content_type == 'text/plain':
                    text_content += decoded
                elif content_type == 'text/html' and not text_content:
                    html_content = decoded
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            content_type = msg.get_content_type()
            charset = msg.get_content_charset() or 'utf-8'
            try:
                decoded = payload.decode(charset, errors='replace')
            except:
                decoded = payload.decode('utf-8', errors='replace')
            
            if content_type == 'text/plain':
                text_content = decoded
            elif content_type == 'text/html':
                html_content = decoded
    
    if not text_content and html_content:
        text_content = strip_html_tags(html_content)
    
    return text_content

def extract_links(text):
    """Extract URLs from text."""
    url_pattern = r'https?://[^\s<>"\')\]>]+'
    urls = re.findall(url_pattern, text)
    cleaned_urls = []
    for url in urls:
        url = url.rstrip('.,;:!?')
        if url and len(url) > 10:
            cleaned_urls.append(url)
    return list(set(cleaned_urls))

def categorize_email(subject, content):
    """Categorize email based on content."""
    text = (subject + " " + content).lower()
    
    categories = []
    
    if any(word in text for word in ['claude', 'anthropic', 'claude code']):
        categories.append('Claude & Anthropic')
    if any(word in text for word in ['openai', 'gpt', 'chatgpt', 'codex', 'o1', 'gpt-5']):
        categories.append('OpenAI & GPT')
    if any(word in text for word in ['gemini', 'google', 'deepmind']):
        categories.append('Google & Gemini')
    if any(word in text for word in ['cursor', 'vscode', 'ide', 'editor']):
        categories.append('AI Coding IDEs')
    if any(word in text for word in ['vibe coding', 'vibe-coding', 'vibecoding']):
        categories.append('Vibe Coding')
    if any(word in text for word in ['prompt', 'prompting', 'prompt engineering']):
        categories.append('Prompt Engineering')
    if any(word in text for word in ['agent', 'agents', 'agentic']):
        categories.append('AI Agents')
    if any(word in text for word in ['mcp', 'model context protocol']):
        categories.append('MCP (Model Context Protocol)')
    if any(word in text for word in ['replit', 'bolt', 'lovable', 'v0', 'builder']):
        categories.append('No-Code/Low-Code AI Builders')
    if any(word in text for word in ['robot', 'humanoid', 'physical ai']):
        categories.append('Physical AI & Robotics')
    if any(word in text for word in ['video', 'image', 'visual', 'design']):
        categories.append('AI Visual Tools')
    if any(word in text for word in ['course', 'tutorial', 'learn', 'training', 'masterclass']):
        categories.append('Learning Resources')
    if any(word in text for word in ['saas', 'startup', 'business', 'launch']):
        categories.append('AI for Business')
    if any(word in text for word in ['llm', 'model', 'parameter', 'fine-tuning']):
        categories.append('LLM & Models')
    if any(word in text for word in ['nvidia', 'hardware', 'compute']):
        categories.append('AI Hardware & Compute')
    
    if not categories:
        categories.append('General AI')
    
    return categories

def parse_mbox_file(filepath):
    """Parse mbox file and extract all emails."""
    emails = []
    
    mbox = mailbox.mbox(filepath)
    
    for message in mbox:
        try:
            subject = decode_mime_header(message.get('Subject', ''))
            date = message.get('Date', '')
            from_addr = decode_mime_header(message.get('From', ''))
            
            content = extract_text_content(message)
            
            content = content.split('-------------------------------------------------')[0].strip()
            
            links = extract_links(content)
            
            categories = categorize_email(subject, content)
            
            if subject or content.strip():
                emails.append({
                    'subject': subject,
                    'date': date,
                    'from': from_addr,
                    'content': content,
                    'links': links,
                    'categories': categories
                })
        except Exception as e:
            print(f"Error parsing message: {e}")
            continue
    
    return emails

if __name__ == "__main__":
    emails = parse_mbox_file("attached_assets/AI_1767978834302.mbox")
    
    with open('parsed_emails.json', 'w', encoding='utf-8') as f:
        json.dump(emails, f, ensure_ascii=False, indent=2)
    
    print(f"Parsed {len(emails)} emails")
    
    categories_count = defaultdict(int)
    all_links = []
    for email in emails:
        for cat in email['categories']:
            categories_count[cat] += 1
        all_links.extend(email['links'])
    
    print("\nCategories found:")
    for cat, count in sorted(categories_count.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    
    print(f"\nTotal unique links: {len(set(all_links))}")
