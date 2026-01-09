# AI Development Guide 2025

## Overview
A comprehensive web-based guide that organizes and summarizes information from 541 AI-related emails. The guide covers the latest AI development tools, techniques, and best practices from September 2024 through January 2026.

## Project Structure
```
/
├── app.py                 # Flask web application
├── parse_mbox.py          # Email parser script
├── parsed_emails.json     # Extracted email data (541 emails)
├── templates/
│   └── index.html         # Main guide template
└── attached_assets/
    └── AI_*.mbox          # Source email file
```

## Key Features
- **541 emails analyzed** across 16 topic categories
- **1253 resource links** extracted
- **Boolean keyword search** - supports AND, OR, NOT operators
- Interactive navigation with smooth scrolling
- Organized by topics: Claude/Anthropic, OpenAI, Cursor, Vibe Coding, etc.
- Best practices and prompt engineering techniques
- Learning resource links

## Tech Stack
- Python 3.11
- Flask (web framework)
- Tailwind CSS (styling via CDN)

## Running the Application
```bash
python app.py
```
Server runs on port 5000.

## Categories Covered
1. AI Coding IDEs (119 emails) - Cursor, Claude Code, etc.
2. AI Agents (104 emails) - Agentic development
3. Claude & Anthropic (86 emails)
4. AI Visual Tools (78 emails)
5. OpenAI & GPT (71 emails)
6. Prompt Engineering (71 emails)
7. Google & Gemini (69 emails)
8. Learning Resources (60 emails)
9. No-Code/Low-Code Builders (49 emails)
10. And more...

## Recent Changes
- **Jan 2026**: Initial creation - parsed mbox file and built comprehensive guide
