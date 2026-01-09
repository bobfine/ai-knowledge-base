#!/usr/bin/env python3
"""
Setup script for creating a new email guide from an mbox file.

Usage:
1. Place your .mbox file in the attached_assets/ folder
2. Run: python setup_new_guide.py

The script will:
- Find your mbox file
- Parse all emails and extract content/links
- Generate AI summaries for each email
- Update the guide with your content
"""

import os
import sys
import json
import glob

def find_mbox_files():
    mbox_files = glob.glob('attached_assets/*.mbox')
    return mbox_files

def update_guide_title(title):
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.replace('AI Development Guide 2025', title)
    
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Updated guide title to: {title}")

def main():
    print("=" * 50)
    print("Email Guide Setup Script")
    print("=" * 50)
    
    mbox_files = find_mbox_files()
    
    if not mbox_files:
        print("\nNo .mbox files found in attached_assets/")
        print("Please add your mbox file to that folder and run again.")
        return
    
    print(f"\nFound {len(mbox_files)} mbox file(s):")
    for i, f in enumerate(mbox_files, 1):
        print(f"  {i}. {f}")
    
    if len(mbox_files) == 1:
        selected = mbox_files[0]
    else:
        choice = input("\nEnter number to select (or press Enter for first): ").strip()
        idx = int(choice) - 1 if choice else 0
        selected = mbox_files[idx]
    
    print(f"\nUsing: {selected}")
    
    title = input("\nEnter the guide title (e.g., 'OpenHMD Guide January 2026'): ").strip()
    if not title:
        title = "Email Guide"
    
    if os.path.exists('parsed_emails.json'):
        confirm = input("\nExisting parsed_emails.json found. Delete and start fresh? (y/n): ").strip().lower()
        if confirm == 'y':
            os.remove('parsed_emails.json')
            print("Deleted old data.")
    
    print("\n" + "=" * 50)
    print("Step 1: Parsing emails...")
    print("=" * 50)
    
    with open('parse_mbox.py', 'r', encoding='utf-8') as f:
        parser_code = f.read()
    
    old_path = None
    for line in parser_code.split('\n'):
        if 'attached_assets/' in line and '.mbox' in line:
            import re
            match = re.search(r"'(attached_assets/[^']+\.mbox)'", line)
            if match:
                old_path = match.group(1)
                break
    
    if old_path and old_path != selected:
        parser_code = parser_code.replace(old_path, selected)
        with open('parse_mbox.py', 'w', encoding='utf-8') as f:
            f.write(parser_code)
        print(f"Updated parser to use: {selected}")
    
    os.system('python parse_mbox.py')
    
    print("\n" + "=" * 50)
    print("Step 2: Generating AI summaries...")
    print("=" * 50)
    os.system('python generate_summaries.py')
    
    print("\n" + "=" * 50)
    print("Step 3: Updating guide title...")
    print("=" * 50)
    update_guide_title(title)
    
    print("\n" + "=" * 50)
    print("COMPLETE!")
    print("=" * 50)
    print("\nYour guide is ready. Restart the app to see your new content.")
    print("Run: python app.py")

if __name__ == '__main__':
    main()
