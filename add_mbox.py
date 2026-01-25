#!/usr/bin/env python3
"""
Incremental Update Script - Add new mbox files to existing knowledge base.

This script PRESERVES all existing data and ADDS new emails from a new mbox file.
It handles deduplication, generates summaries only for new emails, and updates statistics.

Usage:
1. Place your new .mbox file in attached_assets/
2. Run: python add_mbox.py

The script will:
- Load existing parsed_emails.json (if any)
- Parse the new mbox file
- Deduplicate emails (by subject + date)
- Generate AI summaries for NEW emails only
- Merge with existing data
- Update the JSON file
"""

import os
import sys
import json
import glob
import time
import hashlib
from datetime import datetime
from collections import defaultdict

from parse_mbox import parse_mbox_file, categorize_email
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY"),
    base_url=os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
)

def generate_email_hash(email):
    """Create a unique hash for deduplication based on subject + date."""
    key = f"{email.get('subject', '')}{email.get('date', '')}".lower().strip()
    return hashlib.md5(key.encode()).hexdigest()

def load_existing_emails():
    """Load existing parsed emails, return empty list if none exist."""
    if os.path.exists('parsed_emails.json'):
        with open('parsed_emails.json', 'r', encoding='utf-8') as f:
            emails = json.load(f)
            print(f"Loaded {len(emails)} existing emails")
            return emails
    print("No existing emails found - starting fresh")
    return []

def get_existing_hashes(emails):
    """Get set of hashes for all existing emails."""
    return {generate_email_hash(e) for e in emails}

def generate_summary(email):
    """Generate AI summary for a single email."""
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
                {"role": "system", "content": "You are a helpful assistant that summarizes email newsletters. Be concise and informative."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating summary: {e}")
        return None

def find_new_mbox_files(processed_files_path='processed_mbox_files.json'):
    """Find mbox files that haven't been processed yet."""
    mbox_files = glob.glob('attached_assets/*.mbox')
    
    processed = set()
    if os.path.exists(processed_files_path):
        with open(processed_files_path, 'r') as f:
            processed = set(json.load(f))
    
    new_files = [f for f in mbox_files if f not in processed]
    return new_files, processed

def mark_file_processed(filepath, processed_files_path='processed_mbox_files.json'):
    """Mark an mbox file as processed."""
    processed = set()
    if os.path.exists(processed_files_path):
        with open(processed_files_path, 'r') as f:
            processed = set(json.load(f))
    
    processed.add(filepath)
    
    with open(processed_files_path, 'w') as f:
        json.dump(list(processed), f, indent=2)

def print_statistics(emails):
    """Print summary statistics."""
    categories_count = defaultdict(int)
    all_links = []
    
    for email in emails:
        for cat in email.get('categories', ['General AI']):
            categories_count[cat] += 1
        all_links.extend(email.get('links', []))
    
    print("\n" + "=" * 50)
    print("UPDATED STATISTICS")
    print("=" * 50)
    print(f"\nTotal emails: {len(emails)}")
    print(f"Total links: {len(all_links)}")
    print(f"Unique links: {len(set(all_links))}")
    print(f"Categories: {len(categories_count)}")
    
    print("\nEmails by category:")
    for cat, count in sorted(categories_count.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

def main():
    print("=" * 60)
    print("INCREMENTAL UPDATE - Add New Emails to Knowledge Base")
    print("=" * 60)
    
    existing_emails = load_existing_emails()
    existing_hashes = get_existing_hashes(existing_emails)
    
    new_files, processed = find_new_mbox_files()
    
    if not new_files:
        all_mbox = glob.glob('attached_assets/*.mbox')
        if not all_mbox:
            print("\nNo mbox files found in attached_assets/")
            return
        
        print(f"\nAll {len(all_mbox)} mbox file(s) have already been processed:")
        for f in all_mbox:
            status = "(processed)" if f in processed else "(new)"
            print(f"  - {f} {status}")
        
        print("\nOptions:")
        print("1. Add a new mbox file to attached_assets/")
        print("2. To reprocess a file, delete processed_mbox_files.json")
        return
    
    print(f"\nFound {len(new_files)} new mbox file(s) to process:")
    for i, f in enumerate(new_files, 1):
        print(f"  {i}. {f}")
    
    if len(new_files) == 1:
        selected = new_files[0]
    else:
        choice = input("\nEnter number to process (or 'all' for all files): ").strip()
        if choice.lower() == 'all':
            selected = new_files
        else:
            idx = int(choice) - 1 if choice else 0
            selected = [new_files[idx]]
    
    if isinstance(selected, str):
        selected = [selected]
    
    total_new = 0
    total_duplicates = 0
    
    for mbox_file in selected:
        print(f"\n{'=' * 50}")
        print(f"Processing: {mbox_file}")
        print("=" * 50)
        
        print("\nStep 1: Parsing emails...")
        new_emails = parse_mbox_file(mbox_file)
        print(f"  Found {len(new_emails)} emails in file")
        
        print("\nStep 2: Checking for duplicates...")
        unique_new = []
        for email in new_emails:
            email_hash = generate_email_hash(email)
            if email_hash not in existing_hashes:
                unique_new.append(email)
                existing_hashes.add(email_hash)
            else:
                total_duplicates += 1
        
        print(f"  New unique emails: {len(unique_new)}")
        print(f"  Duplicates skipped: {len(new_emails) - len(unique_new)}")
        
        if unique_new:
            print("\nStep 3: Generating AI summaries for new emails...")
            for i, email in enumerate(unique_new):
                summary = generate_summary(email)
                if summary:
                    email['summary'] = summary
                else:
                    email['summary'] = ''
                
                if (i + 1) % 10 == 0 or i == len(unique_new) - 1:
                    print(f"  Progress: {i + 1}/{len(unique_new)}")
                
                time.sleep(0.1)
            
            existing_emails.extend(unique_new)
            total_new += len(unique_new)
        
        mark_file_processed(mbox_file)
        print(f"\nMarked {mbox_file} as processed")
    
    print("\n" + "=" * 50)
    print("Step 4: Saving updated database...")
    print("=" * 50)
    
    with open('parsed_emails.json', 'w', encoding='utf-8') as f:
        json.dump(existing_emails, f, indent=2, ensure_ascii=False)
    
    print(f"  Saved {len(existing_emails)} total emails")
    
    print_statistics(existing_emails)
    
    # Update the last modified date
    today = datetime.now().strftime('%B %d, %Y')
    with open('last_updated.txt', 'w') as f:
        f.write(today)
    print(f"\n  Updated 'Last Updated' date to: {today}")
    
    print("\n" + "=" * 50)
    print("INCREMENTAL UPDATE COMPLETE!")
    print("=" * 50)
    print(f"\n  New emails added: {total_new}")
    print(f"  Duplicates skipped: {total_duplicates}")
    print(f"  Total emails now: {len(existing_emails)}")
    print("\nRestart the web app to see updated content.")
    print("The search will automatically include all new emails.")

if __name__ == '__main__':
    main()
