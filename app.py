from flask import Flask, render_template, jsonify
import json

app = Flask(__name__)

@app.route('/')
def index():
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
                          emails_json=json.dumps(emails_for_search))

@app.route('/api/emails')
def api_emails():
    with open('parsed_emails.json', 'r', encoding='utf-8') as f:
        emails = json.load(f)
    return jsonify(emails)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
