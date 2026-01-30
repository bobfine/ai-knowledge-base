#!/usr/bin/env python3
"""
Re-categorize emails using GPT-4o for more granular classification.
"""

import os
import sys
import json
import sqlite3
import time
from openai import OpenAI

# Category definitions
CATEGORIES = {
    # Tier 1: Vendor/Product
    "Claude & Anthropic": "Claude, Claude Code, Anthropic products",
    "OpenAI & GPT": "ChatGPT, GPT-4, GPT-4o, o1, o3, OpenAI products",
    "Google & Gemini": "Gemini, NotebookLM, Google AI products",
    "DeepSeek": "DeepSeek R1, V3, and related content",
    "Cursor": "Cursor IDE features and tips",
    "Windsurf": "Windsurf/Codeium IDE content",
    "Replit": "Replit Agent and platform",
    "Perplexity": "Perplexity AI search and products",
    
    # Tier 2: Technology
    "MCP & Tool Integration": "Model Context Protocol, tool integrations",
    "AI Agents": "Autonomous agents, agentic workflows",
    "Vibe Coding": "Natural language coding, describe-to-build",
    "RAG & Embeddings": "Retrieval, vector DBs, embeddings",
    "Prompt Engineering": "Prompts, templates, system prompts",
    "AI Coding IDEs": "Code editors, IDE features (general)",
    "No-Code/Low-Code": "Visual builders, Bolt, Lovable, v0",
    "LLM & Models": "Model releases, architecture, training",
    
    # Tier 3: Application
    "AI Visual Tools": "Image/video generation, design tools",
    "AI Audio & Music": "Voice, music, audio generation",
    "Physical AI & Robotics": "Robots, embodied AI, hardware",
    "AI for Business": "Enterprise, productivity, workflows",
    "AI Automation": "Workflows, n8n, automations",
    
    # Tier 4: Content Type
    "AI News & Industry": "Funding, acquisitions, market trends",
    "AI Research & Reports": "Papers, studies, benchmarks",
    "Developer Resources": "Tutorials, APIs, documentation",
    "Learning Resources": "Courses, educational content",
    "Tool Announcements": "New releases, product launches",
    "AI Safety & Ethics": "Alignment, interpretability, safety",
}

CATEGORY_LIST = list(CATEGORIES.keys())

def get_db_connection():
    """Get database connection."""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'knowledge.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_email_data(conn, email_id):
    """Get email data with tool mentions and link info."""
    cur = conn.cursor()
    
    # Get email
    cur.execute("SELECT id, subject, summary, original_categories FROM emails WHERE id = ?", (email_id,))
    email = dict(cur.fetchone())
    
    # Get tool mentions
    cur.execute("""
        SELECT t.name FROM tool_mentions tm 
        JOIN tools t ON tm.tool_id = t.id 
        WHERE tm.email_id = ?
    """, (email_id,))
    email['tools'] = [row['name'] for row in cur.fetchall()]
    
    # Get link domains/titles
    cur.execute("""
        SELECT domain, title FROM email_links 
        WHERE email_id = ? AND title IS NOT NULL
        LIMIT 5
    """, (email_id,))
    email['links'] = [{'domain': row['domain'], 'title': row['title'][:100] if row['title'] else ''} for row in cur.fetchall()]
    
    return email

def classify_email(client, email):
    """Use GPT-4o to classify an email."""
    
    prompt = f"""Classify this AI-related email into categories.

EMAIL:
Subject: {email['subject']}
Summary: {email['summary']}
Tools mentioned: {', '.join(email['tools']) if email['tools'] else 'None'}
Link domains: {', '.join([l['domain'] for l in email['links']]) if email['links'] else 'None'}

AVAILABLE CATEGORIES:
{chr(10).join([f"- {cat}: {desc}" for cat, desc in CATEGORIES.items()])}

RULES:
1. Pick exactly 1 PRIMARY category (the best fit)
2. Pick 0-2 SECONDARY categories (if clearly relevant)
3. Prefer vendor-specific categories when appropriate (e.g., "Claude & Anthropic" over "AI Agents" if about Claude)
4. Use "Tool Announcements" for new product launches
5. Use "AI News & Industry" for funding/acquisition news

Return JSON only:
{{"primary": "Category Name", "secondary": ["Cat1", "Cat2"], "confidence": 0.95}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=150,
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        print(f"  Error classifying email {email['id']}: {e}")
        return {"primary": "General AI", "secondary": [], "confidence": 0.0}

def update_email_categories(conn, email_id, primary, secondary):
    """Update email categories in database."""
    cur = conn.cursor()
    
    # Update original_categories with new primary + secondary
    all_cats = [primary] + secondary
    cur.execute("UPDATE emails SET original_categories = ? WHERE id = ?", 
                (json.dumps(all_cats), email_id))
    
    # Clear old category assignments
    cur.execute("DELETE FROM email_categories WHERE email_id = ?", (email_id,))
    
    # Insert new category assignments
    for cat in all_cats:
        cur.execute("INSERT INTO email_categories (email_id, category) VALUES (?, ?)",
                    (email_id, cat))
    
    conn.commit()

def main():
    # Check for API key
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        sys.exit(1)
    
    client = OpenAI(api_key=api_key)
    conn = get_db_connection()
    
    # Get all email IDs
    cur = conn.cursor()
    cur.execute("SELECT id FROM emails ORDER BY id")
    email_ids = [row['id'] for row in cur.fetchall()]
    
    total = len(email_ids)
    print(f"Re-categorizing {total} emails...")
    
    stats = {"processed": 0, "errors": 0}
    category_counts = {}
    
    for i, email_id in enumerate(email_ids):
        email = get_email_data(conn, email_id)
        result = classify_email(client, email)
        
        primary = result.get('primary', 'General AI')
        secondary = result.get('secondary', [])[:2]  # Max 2 secondary
        confidence = result.get('confidence', 0.0)
        
        # Validate categories
        if primary not in CATEGORY_LIST:
            primary = 'General AI'
        secondary = [s for s in secondary if s in CATEGORY_LIST and s != primary]
        
        update_email_categories(conn, email_id, primary, secondary)
        
        # Track stats
        stats["processed"] += 1
        category_counts[primary] = category_counts.get(primary, 0) + 1
        
        # Progress
        if (i + 1) % 50 == 0 or i == total - 1:
            print(f"  Processed {i + 1}/{total} emails...")
        
        # Rate limiting
        time.sleep(0.1)
    
    conn.close()
    
    print(f"\n✅ Re-categorization complete!")
    print(f"   Processed: {stats['processed']}")
    print(f"\nCategory distribution:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"   {cat}: {count}")

if __name__ == "__main__":
    main()
