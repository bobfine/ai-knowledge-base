import json
import os
import time
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY"),
    base_url=os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
)

def generate_summary(email):
    subject = email.get('subject', '')
    content = email.get('content', '')[:2000]
    links = email.get('links', [])
    links_text = '\n'.join(links[:10]) if links else 'No external links'
    
    prompt = f"""Based on the following email, write a concise 2-3 sentence summary that captures the main topic and key takeaways. If there are external links, infer their content from the URL patterns and how they're referenced in the email.

Subject: {subject}

Content:
{content}

External Links:
{links_text}

Write a helpful summary (2-3 sentences):"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes AI development newsletter emails. Be concise and informative."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating summary: {e}")
        return None

def main():
    with open('parsed_emails.json', 'r', encoding='utf-8') as f:
        emails = json.load(f)
    
    print(f"Generating summaries for {len(emails)} emails...")
    
    processed = 0
    failed = 0
    
    for i, email in enumerate(emails):
        if email.get('summary'):
            processed += 1
            continue
            
        summary = generate_summary(email)
        if summary:
            email['summary'] = summary
            processed += 1
        else:
            email['summary'] = ''
            failed += 1
        
        if (i + 1) % 10 == 0:
            print(f"Progress: {i + 1}/{len(emails)} ({processed} successful, {failed} failed)")
            with open('parsed_emails.json', 'w', encoding='utf-8') as f:
                json.dump(emails, f, indent=2, ensure_ascii=False)
        
        time.sleep(0.1)
    
    with open('parsed_emails.json', 'w', encoding='utf-8') as f:
        json.dump(emails, f, indent=2, ensure_ascii=False)
    
    print(f"\nComplete! Generated {processed} summaries ({failed} failed)")

if __name__ == '__main__':
    main()
