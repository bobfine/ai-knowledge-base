# AI Development Guide 2025

## Overview
A comprehensive web-based guide that organizes and summarizes information from 613 AI-related emails. The guide covers the latest AI development tools, techniques, and best practices from September 2024 through January 2026.

## Project Structure
```
/
├── app.py                      # Flask web application
├── parse_mbox.py               # Email parser script
├── generate_summaries.py       # AI summary generator
├── add_mbox.py                 # INCREMENTAL UPDATE - add new mbox files
├── setup_new_guide.py          # Fresh start setup script
├── parsed_emails.json          # Extracted email data (541 emails)
├── processed_mbox_files.json   # Tracks which mbox files processed
├── PRD.md                      # Full technical documentation
├── templates/
│   └── index.html              # Main guide template
└── attached_assets/
    └── *.mbox                  # Source email file(s)
```

## Key Features
- **613 emails analyzed** across 16 topic categories
- **1351 resource links** extracted
- **AI-generated summaries** - each email has a 2-3 sentence summary
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
1. AI Coding IDEs (136 emails) - Cursor, Claude Code, etc.
2. AI Agents (118 emails) - Agentic development
3. Claude & Anthropic (107 emails)
4. AI Visual Tools (83 emails)
5. Google & Gemini (81 emails)
6. Prompt Engineering (81 emails)
7. OpenAI & GPT (80 emails)
8. LLM & Models (75 emails)
9. Learning Resources (62 emails)
10. No-Code/Low-Code AI Builders (52 emails)
11. AI for Business (52 emails)
12. Physical AI & Robotics (28 emails)
13. MCP (Model Context Protocol) (25 emails)
14. Vibe Coding (25 emails)
15. AI Hardware & Compute (24 emails)
16. General AI (175 emails) - Uncategorized

## Adding New Emails (Incremental Update)

To EXPAND your knowledge base with new emails:

1. **Export new emails** to .mbox format
2. **Add the new mbox file** to `attached_assets/` (keep existing files)
3. **Run incremental update**:
   ```bash
   python add_mbox.py
   ```
   This will:
   - Preserve all existing emails
   - Parse only the new mbox file
   - Skip duplicates automatically
   - Generate AI summaries for new emails only
   - Update the database

4. **Restart the app** to see updated content

**Cost:** ~$0.15-0.20 per 500 new emails

**Search:** No reindexing needed - client-side search automatically includes new emails

## Starting Fresh (New Guide)

To create a completely new guide:

1. **Fork this project** in Replit
2. **Delete** `parsed_emails.json` and `processed_mbox_files.json`
3. **Add your mbox file** to `attached_assets/`
4. **Run**: `python setup_new_guide.py`

## Recent Changes
- **Jan 2026**: Added incremental update workflow (add_mbox.py)
- **Jan 2026**: Added AI-generated summaries and boolean search
- **Jan 2026**: Initial creation - parsed mbox file and built comprehensive guide
