# Mbox Import Pipeline Documentation

This document explains each process in the mbox import workflow.

---

## Pipeline Overview

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  1. Parse    │ → │ 2. Migrate   │ → │ 3. Embeddings│ → │ 4. Enrich    │
│  Mbox File   │   │ to SQLite    │   │ for Search   │   │ Links        │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
                                                                ↓
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  7. Restart  │ ← │ 6. Refresh   │ ← │ 5. Categorize│ ← │              │
│  Server      │   │ Curriculum   │   │ with GPT-4o  │   │              │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
```

---

## Step 1: Parse Mbox File

**Script:** `add_mbox.py`

**What it does:**
- Reads all `.mbox` files from `attached_assets/` directory
- Parses email headers (subject, date, sender)
- Extracts email body content
- Deduplicates against existing emails (by message ID)
- Generates AI summaries using GPT-4o
- Extracts URLs/links from email content
- Identifies tool mentions (Claude, Cursor, etc.)
- Outputs to `parsed_emails.json`

**Output:** `parsed_emails.json` with new emails added

---

## Step 2: Migrate to SQLite Database

**Script:** `scripts/migrate_to_sqlite.py`

**What it does:**
- Reads `parsed_emails.json`
- Syncs data to SQLite database (`data/knowledge.db`)
- Creates/updates records in:
  - `emails` table
  - `email_links` table
  - `tool_mentions` table
  - `email_categories` table

**Database Tables:**
| Table | Purpose |
|-------|---------|
| `emails` | Core email data (subject, content, summary, date) |
| `email_links` | URLs extracted from emails |
| `email_categories` | Category assignments per email |
| `tool_mentions` | Tools mentioned in each email |
| `tools` | Tool reference data (name, category) |

---

## Step 3: Generate Embeddings

**Script:** `services/embeddings.py`

**What it does:**
- Uses OpenAI's `text-embedding-3-small` model
- Generates 1536-dimensional vector for each email
- Combines subject + summary + categories for embedding
- Stores embeddings in `emails.embedding` column (as JSON)
- Only processes emails without existing embeddings

**Purpose:** Enables semantic search - find emails by meaning, not just keywords.

---

## Step 4: Enrich Links

**Script:** `services/link_enricher.py`

**What it does:**
- Fetches each URL's webpage
- Extracts metadata:
  - Page title
  - Meta description
  - Domain name
- Rate-limited to 1 request/second
- Updates `email_links` table with enriched data

**Purpose:** Makes links browsable with titles instead of raw URLs.

---

## Step 5: Categorize Emails

**Script:** `scripts/recategorize_emails.py`

**What it does:**
- Uses GPT-4o-mini for classification
- Assigns each email to one of 27 categories:

| Tier | Categories |
|------|------------|
| **Vendor** | Claude & Anthropic, OpenAI & GPT, Google & Gemini, DeepSeek, Cursor, Windsurf, Replit, Perplexity |
| **Technology** | MCP & Tool Integration, AI Agents, Vibe Coding, RAG & Embeddings, Prompt Engineering, AI Coding IDEs, No-Code/Low-Code, LLM & Models |
| **Application** | AI Visual Tools, AI Audio & Music, Physical AI & Robotics, AI for Business, AI Automation |
| **Content** | AI News & Industry, AI Research & Reports, Developer Resources, Learning Resources, Tool Announcements, AI Safety & Ethics |

- Assigns 1 primary + up to 2 secondary categories
- Updates `email_categories` and `emails.original_categories`

---

## Step 6: Refresh Curriculum

**Script:** `services/curriculum.py`

**What it does:**
- Creates learning modules from categories
- Each category becomes a learning module
- Lessons are created from emails in each category
- Links source emails to lessons via `lesson_sources` table
- Generates 26 modules with 138+ lessons total

**Database Tables:**
| Table | Purpose |
|-------|---------|
| `modules` | Learning modules (title, description) |
| `lessons` | Individual lessons linked to modules |
| `lesson_sources` | Links lessons to source emails |
| `user_progress` | Tracks completed lessons |
| `quiz_questions` | Quiz questions for each lesson |

---

## Step 7: Restart Server

**Command:** `python3 app.py`

**What it does:**
- Starts Flask development server on port 8080
- Loads all routes (dashboard, browse, search, learn)
- Initializes database connection pool

---

## Auto-Updated Components

These components don't need explicit refresh - they query live data:

| Component | Data Source | Updated When |
|-----------|-------------|--------------|
| **What's Hot** | `get_whats_hot()` - last 7 days of emails | On page load |
| **Top Tools** | `get_tool_rankings()` - all tool mentions | On page load |
| **AI Briefing** | `generate_briefing_content()` - aggregates all data | On button click |
| **Categories** | `get_all_categories_alphabetical()` - all categories | On page load |
| **Trend Chart** | `get_topic_timeline()` - 30-day trends | On page load |

---

## Quick Reference

### One-Liner Command
```bash
cd "/Users/robertfine/AI Database Assessment v012826/ai-knowledge-base" && \
python3 add_mbox.py && \
echo "y" | python3 scripts/migrate_to_sqlite.py && \
python3 -c "from services.embeddings import generate_all_embeddings; generate_all_embeddings()" && \
python3 services/link_enricher.py --enrich 500 && \
python3 scripts/recategorize_emails.py && \
python3 -c "from services.curriculum import initialize_curriculum; initialize_curriculum()"
```

### Environment Variables
```bash
export OPENAI_API_KEY="sk-..."  # Required for embeddings, categorization, briefings
```

### Database Location
```
data/knowledge.db
```

### Logs
```
enrichment.log  # Link enrichment progress
```
