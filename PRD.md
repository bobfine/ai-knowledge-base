# Email Guide Application - Product Requirements Document

## 1. Project Overview

### Purpose
A web-based application that transforms email newsletters (in .mbox format) into an organized, searchable knowledge base with AI-generated summaries.

### Key Value Proposition
- Automatically parses and categorizes emails by topic
- Extracts all external links for easy reference
- Generates concise AI summaries for each email
- Provides boolean keyword search across all content
- Delivers a clean, responsive web interface

---

## 2. Technical Architecture

### Tech Stack
| Component | Technology |
|-----------|------------|
| Backend | Python 3.11 + Flask |
| Frontend | HTML + Tailwind CSS (CDN) |
| AI Integration | OpenAI GPT-4.1-mini via Replit AI Integrations |
| Data Storage | JSON file (parsed_emails.json) |
| Hosting | Replit (port 5000) |

### Architecture Diagram
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  .mbox file     │────▶│  parse_mbox.py   │────▶│ parsed_emails   │
│  (input)        │     │  (parser)        │     │ .json           │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                        ┌──────────────────┐              │
                        │ generate_        │◀─────────────┘
                        │ summaries.py     │──────┐
                        └──────────────────┘      │
                               │                  │
                               ▼                  ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │  OpenAI API      │     │ parsed_emails   │
                        │  (GPT-4.1-mini)  │     │ .json (updated) │
                        └──────────────────┘     └────────┬────────┘
                                                          │
                        ┌──────────────────┐              │
                        │  app.py          │◀─────────────┘
                        │  (Flask server)  │
                        └────────┬─────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │  index.html      │
                        │  (Tailwind UI)   │
                        └──────────────────┘
```

---

## 3. Core Features

### 3.1 Email Parsing
**File:** `parse_mbox.py`

**Functionality:**
- Reads standard .mbox email files
- Extracts: subject, date, sender, body content
- Handles both plain text and HTML emails (strips HTML tags)
- Deduplicates extracted content

**Acceptance Criteria:**
- Running script produces JSON with all emails
- Each email has subject, date, from, content, links, categories fields

### 3.2 Automatic Categorization
**File:** `parse_mbox.py` (function: `categorize_email`)

**Default Categories:**
```python
categories = {
    'AI Coding IDEs': ['cursor', 'windsurf', 'claude code', 'vscode', 'copilot'],
    'AI Agents': ['agent', 'agentic', 'mcp', 'autonomous'],
    'Claude & Anthropic': ['claude', 'anthropic', 'sonnet', 'opus', 'haiku'],
    'OpenAI & GPT': ['openai', 'gpt', 'chatgpt', 'o1', 'o3'],
    'Google & Gemini': ['google', 'gemini', 'bard', 'deepmind'],
    'Prompt Engineering': ['prompt', 'prompting', 'chain of thought', 'few-shot'],
    'AI Visual Tools': ['image', 'video', 'midjourney', 'dalle', 'stable diffusion'],
    'No-Code/Low-Code Builders': ['lovable', 'bolt', 'replit', 'no-code', 'low-code'],
    'Learning Resources': ['course', 'tutorial', 'learn', 'masterclass', 'workshop'],
    # ... add more as needed
}
```

**Customization:** Edit the `categories` dictionary to match your email topics.

### 3.3 Link Extraction
**File:** `parse_mbox.py`

**Functionality:**
- Regex extracts all HTTP/HTTPS URLs from email body
- Filters out URLs shorter than 10 characters
- Removes trailing punctuation
- Stores as array in each email object

### 3.4 AI-Generated Summaries
**File:** `generate_summaries.py`

**Functionality:**
- Reads parsed_emails.json
- For each email without a summary, calls OpenAI API
- Generates 2-3 sentence summary based on:
  - Email subject and content
  - URL patterns (infers context from domains/paths)
- Saves progress every 10 emails (crash-safe)

**Model:** GPT-4.1-mini (cost-effective, good quality)

**Prompt Template:**
```
Based on the following email, write a concise 2-3 sentence summary 
that captures the main topic and key takeaways. If there are external 
links, infer their content from the URL patterns and how they're 
referenced in the email.
```

### 3.5 Boolean Keyword Search
**File:** `templates/index.html` (JavaScript)

**Supported Operators:**
| Operator | Example | Behavior |
|----------|---------|----------|
| AND | `cursor AND agent` | Both terms must appear |
| OR | `openai OR claude` | Either term matches |
| NOT | `gpt NOT beta` | Exclude term |
| Combined | `cursor AND agent OR claude` | Complex queries |

**Search Scope:** Subject, content, and URLs

### 3.6 Expandable Category Sections
**File:** `templates/index.html`

**Behavior:**
- Categories displayed as collapsible accordions
- Default state: collapsed
- Click header to expand/collapse
- Shows email count per category
- Sorted by email count (descending)

### 3.7 Responsive Web Design
**Framework:** Tailwind CSS (CDN)

**Breakpoints:**
- Mobile: < 640px (single column)
- Tablet: 640px - 1024px (two columns)
- Desktop: > 1024px (full layout with sidebar)

---

## 4. Data Model

### Email Object Schema
```json
{
  "subject": "string - email subject line",
  "date": "string - RFC822 date format",
  "from": "string - sender email/name",
  "content": "string - plain text body (HTML stripped)",
  "links": ["array", "of", "extracted", "URLs"],
  "categories": ["array", "of", "matched", "categories"],
  "summary": "string - AI-generated 2-3 sentence summary"
}
```

### Example Entry
```json
{
  "subject": "Claude Code Best Practices from Anthropic",
  "date": "Mon, 15 Jan 2026 09:30:00 -0800",
  "from": "newsletter@example.com",
  "content": "Today we explore the new CLAUDE.md configuration...",
  "links": [
    "https://anthropic.com/engineering/claude-code-best-practices",
    "https://github.com/anthropics/claude-code"
  ],
  "categories": ["Claude & Anthropic", "AI Coding IDEs"],
  "summary": "Anthropic released official best practices for Claude Code, including the CLAUDE.md configuration file for persistent project context. Key recommendations include using the What/Why/How framework and extended thinking keywords for complex tasks."
}
```

---

## 5. File Structure

```
project-root/
├── app.py                    # Flask web server
├── parse_mbox.py             # Email parser script
├── generate_summaries.py     # AI summary generator
├── setup_new_guide.py        # Automated setup script
├── parsed_emails.json        # Generated email data
├── templates/
│   └── index.html            # Main UI template
├── attached_assets/
│   └── *.mbox                # Input email file(s)
├── replit.md                 # Project documentation
├── PRD.md                    # This document
├── pyproject.toml            # Python dependencies
└── .replit                   # Replit configuration
```

---

## 6. Setup Process

### Option A: Automated Setup
```bash
python setup_new_guide.py
```

**Script Actions:**
1. Finds .mbox files in `attached_assets/`
2. Prompts for guide title
3. Optionally deletes existing data
4. Runs email parser
5. Generates AI summaries
6. Updates page title
7. Displays completion message

### Option B: Manual Setup
```bash
# 1. Parse emails
python parse_mbox.py

# 2. Generate summaries
python generate_summaries.py

# 3. Start server
python app.py
```

---

## 7. Customization Points

### 7.1 Categories/Topics
**File:** `parse_mbox.py`

Modify the `categorize_email()` function to change topic keywords:
```python
def categorize_email(subject, content):
    categories = {
        'Your Topic 1': ['keyword1', 'keyword2'],
        'Your Topic 2': ['keyword3', 'keyword4'],
        # Add your categories here
    }
```

### 7.2 Page Title & Branding
**File:** `templates/index.html`

Update these elements:
- `<title>` tag (line ~6)
- `<h1>` header text (line ~61)
- Description paragraph
- Footer text

### 7.3 Summary Prompt
**File:** `generate_summaries.py`

Modify the prompt in `generate_summary()` function to change summary style.

### 7.4 Visual Styling
**File:** `templates/index.html`

- Gradient colors: `.gradient-bg` class
- Card styles: `.category-card`, `.email-card`
- Accent colors: Change Tailwind color classes (indigo, purple, etc.)

---

## 8. Deployment Configuration

### Development
```bash
python app.py
# Runs on http://0.0.0.0:5000
```

### Production (Replit)
**Deployment Type:** Autoscale

**Run Command:**
```bash
python app.py
```

**Required Environment Variables:**
- `AI_INTEGRATIONS_OPENAI_API_KEY` (auto-set by Replit integration)
- `AI_INTEGRATIONS_OPENAI_BASE_URL` (auto-set by Replit integration)

---

## 9. Dependencies

### Python Packages
```
flask
openai
```

### Install Command
```bash
pip install flask openai
```

Or via Replit's package manager.

---

## 10. Creating a New Guide from Scratch

### Step-by-Step Instructions

1. **Create new Replit project**
   - Choose Python template
   - Name your project

2. **Install dependencies**
   ```bash
   pip install flask openai
   ```

3. **Set up OpenAI integration**
   - Search for "OpenAI" in Replit integrations
   - Add the Python OpenAI AI Integration

4. **Create file structure**
   - Create `templates/` folder
   - Create `attached_assets/` folder

5. **Copy core files**
   - `app.py` - Flask server
   - `parse_mbox.py` - Email parser
   - `generate_summaries.py` - Summary generator
   - `templates/index.html` - UI template
   - `setup_new_guide.py` - Setup automation

6. **Add your .mbox file**
   - Place in `attached_assets/` folder

7. **Customize categories** (optional)
   - Edit `parse_mbox.py` with your topic keywords

8. **Run setup**
   ```bash
   python setup_new_guide.py
   ```

9. **Start the app**
   ```bash
   python app.py
   ```

10. **Publish** (optional)
    - Configure deployment settings
    - Click Publish for public URL

---

## 11. Maintenance

### Adding New Emails
1. Export new emails to .mbox format
2. Replace or append to existing .mbox file
3. Delete `parsed_emails.json`
4. Run `python setup_new_guide.py`

### Regenerating Summaries
```bash
# Delete summaries from JSON or delete the file
python generate_summaries.py
```

### Updating Categories
1. Edit keywords in `parse_mbox.py`
2. Delete `parsed_emails.json`
3. Re-run parser

---

*Document Version: 1.0*
*Last Updated: January 2026*
