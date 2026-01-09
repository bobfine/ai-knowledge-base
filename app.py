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
            categories[cat].append(email)
    
    sorted_categories = dict(sorted(categories.items(), key=lambda x: -len(x[1])))
    
    return render_template('index.html', 
                          emails=emails, 
                          categories=sorted_categories,
                          total_emails=len(emails),
                          total_links=sum(len(e.get('links', [])) for e in emails))

@app.route('/api/emails')
def api_emails():
    with open('parsed_emails.json', 'r', encoding='utf-8') as f:
        emails = json.load(f)
    return jsonify(emails)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
