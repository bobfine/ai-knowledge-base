"""
AI Briefing generator for AI Knowledge Base.
Generates on-demand AI-powered summaries of recent activity.
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_connection
from services.analytics import get_overall_stats, get_trending_topics, get_whats_hot, get_recent_emails
from services.tools import get_tool_rankings


def generate_briefing_content():
    """
    Generate a structured briefing without AI.
    This provides a fallback when API is not available.
    """
    stats = get_overall_stats()
    trending = get_trending_topics(days=7, limit=5)
    hot_topics = get_whats_hot(limit=5)
    top_tools = get_tool_rankings(limit=5)
    recent = get_recent_emails(limit=5)
    
    briefing = {
        'generated_at': datetime.now().isoformat(),
        'type': 'weekly',
        'stats_summary': f"Analyzing {stats['total_emails']} emails with {stats['total_links']} links across {stats['total_categories']} categories.",
        'date_range': f"{stats['date_range']['start']} to {stats['date_range']['end']}",
        
        'hot_topics': [
            {
                'topic': topic['category'],
                'count': topic['count'],
                'description': f"{topic['count']} emails this week"
            }
            for topic in hot_topics
        ],
        
        'trending': [
            {
                'topic': trend['category'],
                'growth': trend['growth_percent'],
                'trend_direction': trend['trend'],
                'description': f"{'+' if trend['growth_percent'] > 0 else ''}{trend['growth_percent']:.0f}% vs previous week"
            }
            for trend in trending
        ],
        
        'top_tools': [
            {
                'name': tool['name'],
                'mentions': tool['mentions'],
                'category': tool['category']
            }
            for tool in top_tools
        ],
        
        'recent_highlights': [
            {
                'subject': email['subject'],
                'summary': email['summary'][:150] + '...' if email['summary'] and len(email['summary']) > 150 else email['summary'],
                'date': email['date']
            }
            for email in recent
        ]
    }
    
    return briefing


def generate_ai_briefing(openai_client=None):
    """
    Generate an AI-enhanced briefing using GPT.
    Falls back to structured briefing if no API available.
    """
    # Get the structured data
    briefing_data = generate_briefing_content()
    
    if openai_client is None:
        # Try to get OpenAI client
        try:
            from openai import OpenAI
            openai_client = OpenAI(
                api_key=os.environ.get('AI_INTEGRATIONS_OPENAI_API_KEY') or os.environ.get('OPENAI_API_KEY'),
                base_url=os.environ.get('AI_INTEGRATIONS_OPENAI_BASE_URL')
            )
        except Exception:
            # Return structured briefing without AI enhancement
            briefing_data['ai_enhanced'] = False
            briefing_data['summary'] = _generate_summary_without_ai(briefing_data)
            return briefing_data
    
    # Build prompt for AI synthesis
    prompt = f"""You are an AI research analyst. Generate a brief, insightful executive summary based on this data from an AI knowledge base:

**Stats**: {briefing_data['stats_summary']}
**Date Range**: {briefing_data['date_range']}

**Hot Topics This Week**:
{chr(10).join(f"- {t['topic']}: {t['description']}" for t in briefing_data['hot_topics'])}

**Trending (vs Previous Week)**:
{chr(10).join(f"- {t['topic']}: {t['description']}" for t in briefing_data['trending'])}

**Top Tools Being Discussed**:
{chr(10).join(f"- {t['name']} ({t['category']}): {t['mentions']} mentions" for t in briefing_data['top_tools'])}

Write a 3-4 paragraph executive summary that:
1. Highlights the most important developments
2. Identifies key trends worth watching
3. Provides actionable insights for someone learning about AI
4. Uses a professional but engaging tone

Keep it concise and impactful."""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful AI research analyst providing weekly briefings on AI industry developments."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        briefing_data['ai_enhanced'] = True
        briefing_data['summary'] = response.choices[0].message.content
        
    except Exception as e:
        print(f"AI briefing generation failed: {e}")
        briefing_data['ai_enhanced'] = False
        briefing_data['summary'] = _generate_summary_without_ai(briefing_data)
    
    return briefing_data


def _generate_summary_without_ai(briefing_data):
    """Generate a summary without AI when API is unavailable."""
    hot = briefing_data['hot_topics']
    trending = briefing_data['trending']
    tools = briefing_data['top_tools']
    
    summary = f"""## Weekly AI Knowledge Briefing

### 🔥 What's Hot
The most active topics this week are **{hot[0]['topic'] if hot else 'General AI'}** ({hot[0]['count'] if hot else 0} emails) and **{hot[1]['topic'] if len(hot) > 1 else 'AI Coding'}** ({hot[1]['count'] if len(hot) > 1 else 0} emails).

### 📈 Trending Up
"""
    
    if trending:
        for t in trending[:3]:
            summary += f"- **{t['topic']}**: {t['description']}\n"
    
    summary += f"""
### 🛠️ Top Tools
The most discussed tools are **{tools[0]['name'] if tools else 'Claude'}** ({tools[0]['mentions'] if tools else 0} mentions), **{tools[1]['name'] if len(tools) > 1 else 'Cursor'}** ({tools[1]['mentions'] if len(tools) > 1 else 0} mentions), and **{tools[2]['name'] if len(tools) > 2 else 'GPT-4'}** ({tools[2]['mentions'] if len(tools) > 2 else 0} mentions).

### 💡 Key Takeaway
Stay focused on the trending topics and explore the top tools to stay current with AI developments.
"""
    
    return summary


def save_briefing(briefing_data):
    """Save a briefing to the database for caching."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO briefings (type, content, created_at)
            VALUES (?, ?, ?)
        ''', (
            briefing_data['type'],
            str(briefing_data),  # Store as string representation
            briefing_data['generated_at']
        ))
        conn.commit()
        return cursor.lastrowid


def get_latest_briefing():
    """Get the most recent briefing from cache."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM briefings
            ORDER BY created_at DESC
            LIMIT 1
        ''')
        row = cursor.fetchone()
        if row:
            return {
                'id': row['id'],
                'type': row['type'],
                'content': row['content'],
                'created_at': row['created_at']
            }
        return None


def format_briefing_html(briefing_data):
    """Format briefing data as HTML for display."""
    html = f"""
    <div class="briefing">
        <div class="briefing-header">
            <h2>📊 AI Knowledge Briefing</h2>
            <span class="date">Generated: {briefing_data['generated_at'][:16].replace('T', ' ')}</span>
            {'<span class="badge ai-enhanced">AI Enhanced</span>' if briefing_data.get('ai_enhanced') else '<span class="badge data-driven">Data-Driven</span>'}
        </div>
        
        <div class="summary">
            {briefing_data.get('summary', '').replace(chr(10), '<br>')}
        </div>
        
        <div class="sections">
            <div class="section hot-topics">
                <h3>🔥 Hot Topics</h3>
                <ul>
"""
    
    for topic in briefing_data.get('hot_topics', []):
        html += f"<li><strong>{topic['topic']}</strong>: {topic['description']}</li>\n"
    
    html += """
                </ul>
            </div>
            
            <div class="section trending">
                <h3>📈 Trending</h3>
                <ul>
"""
    
    for trend in briefing_data.get('trending', []):
        icon = '🚀' if trend['trend_direction'] == 'up' else ('📉' if trend['trend_direction'] == 'down' else '➡️')
        html += f"<li>{icon} <strong>{trend['topic']}</strong>: {trend['description']}</li>\n"
    
    html += """
                </ul>
            </div>
            
            <div class="section tools">
                <h3>🛠️ Top Tools</h3>
                <ul>
"""
    
    for tool in briefing_data.get('top_tools', []):
        html += f"<li><strong>{tool['name']}</strong> ({tool['category']}): {tool['mentions']} mentions</li>\n"
    
    html += """
                </ul>
            </div>
        </div>
    </div>
"""
    
    return html


if __name__ == '__main__':
    print("Generating briefing...")
    briefing = generate_briefing_content()
    
    print(f"\n{'='*60}")
    print("AI Knowledge Base Briefing")
    print(f"{'='*60}")
    print(f"\nGenerated: {briefing['generated_at']}")
    print(f"Stats: {briefing['stats_summary']}")
    
    print(f"\n🔥 Hot Topics:")
    for topic in briefing['hot_topics']:
        print(f"   - {topic['topic']}: {topic['description']}")
    
    print(f"\n📈 Trending:")
    for trend in briefing['trending']:
        print(f"   - {trend['topic']}: {trend['description']}")
    
    print(f"\n🛠️ Top Tools:")
    for tool in briefing['top_tools']:
        print(f"   - {tool['name']}: {tool['mentions']} mentions")
    
    print(f"\n📰 Recent Highlights:")
    for email in briefing['recent_highlights']:
        print(f"   - [{email['date']}] {email['subject'][:60]}...")
    
    # Try AI enhancement
    print(f"\n{'='*60}")
    print("Attempting AI-enhanced briefing...")
    print(f"{'='*60}")
    ai_briefing = generate_ai_briefing()
    print(f"\nAI Enhanced: {ai_briefing.get('ai_enhanced', False)}")
    print(f"\nSummary:\n{ai_briefing.get('summary', 'No summary generated')}")
