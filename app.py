"""
AI Knowledge Base - Enhanced Flask Application
Combines original email browser with new research dashboard features.
"""

from flask import Flask, render_template, jsonify, send_file
import json
import os
from datetime import datetime
from email.utils import parsedate_to_datetime

app = Flask(__name__)

# Import and register dashboard routes
from routes.dashboard import dashboard_bp
from routes.search import search_bp
from routes.learning import learning_bp
app.register_blueprint(dashboard_bp)
app.register_blueprint(search_bp)
app.register_blueprint(learning_bp)


def get_last_updated():
    """Get last updated date from metadata file or fallback to today."""
    if os.path.exists('last_updated.txt'):
        with open('last_updated.txt', 'r') as f:
            return f.read().strip()
    return datetime.now().strftime('%B %d, %Y')


def parse_date_safe(date_str):
    """Parse email date string, return epoch 0 if parsing fails."""
    try:
        return parsedate_to_datetime(date_str)
    except:
        from datetime import timezone
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


@app.route('/download/template')
def download_template():
    return send_file('email_guide_template.zip', as_attachment=True, download_name='email_guide_template.zip')


@app.route('/')
def index():
    """Main dashboard view - the new Research Dashboard."""
    from services.analytics import get_overall_stats, get_category_stats, get_whats_hot
    from services.tools import get_tool_rankings
    
    stats = get_overall_stats()
    categories = get_category_stats()[:10]
    hot_topics = get_whats_hot(limit=5)
    top_tools = get_tool_rankings(limit=8)
    
    return render_template('dashboard.html',
                          stats=stats,
                          categories=categories,
                          hot_topics=hot_topics,
                          top_tools=top_tools,
                          last_updated=get_last_updated())


@app.route('/search')
def search_page():
    """Semantic search page."""
    return render_template('search.html')


@app.route('/learn')
def learn_page():
    """AI Learning assistant page."""
    return render_template('learn.html')


@app.route('/tools')
def tools_page():
    """Tools directory page."""
    return render_template('tools.html')


@app.route('/browse')
def browse():
    """Original email browser view."""
    with open('parsed_emails.json', 'r', encoding='utf-8') as f:
        emails = json.load(f)
    
    categories = {}
    for email in emails:
        for cat in email.get('categories', ['General AI']):
            if cat not in categories:
                categories[cat] = []
            email_with_cat = email.copy()
            email_with_cat['category'] = cat
            categories[cat].append(email_with_cat)
    
    for cat in categories:
        categories[cat].sort(key=lambda e: parse_date_safe(e.get('date', '')), reverse=True)
    
    sorted_categories = dict(sorted(categories.items(), key=lambda x: -len(x[1])))
    
    emails_for_search = []
    for email in emails:
        email_copy = email.copy()
        email_copy['category'] = email.get('categories', ['General AI'])[0]
        emails_for_search.append(email_copy)
    
    return render_template('index.html', 
                          emails=emails, 
                          categories=sorted_categories,
                          total_emails=len(emails),
                          total_links=sum(len(e.get('links', [])) for e in emails),
                          emails_json=json.dumps(emails_for_search),
                          last_updated=get_last_updated())


@app.route('/api/emails')
def api_emails():
    with open('parsed_emails.json', 'r', encoding='utf-8') as f:
        emails = json.load(f)
    return jsonify(emails)


# Health check endpoint
@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})


if __name__ == '__main__':
    # Ensure database is initialized on startup
    from database import init_database, get_email_count
    init_database()
    
    # Check if data needs migration
    count = get_email_count()
    if count == 0:
        print("⚠️  Database is empty. Run 'python scripts/migrate_to_sqlite.py' to migrate data.")
    else:
        print(f"✅ Database contains {count} emails")
    
    app.run(host='0.0.0.0', port=8080, debug=True)
