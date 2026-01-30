---
description: Import a new .mbox file into the knowledge base and run enrichment
---

# Import New Mbox Workflow

This workflow imports a new .mbox file, processes it into the database, generates embeddings, enriches links, categorizes emails, and refreshes the learning curriculum.

## Prerequisites

1. Place your new `.mbox` file in: `attached_assets/`
2. Ensure the app server is not running (or it will auto-reload)
3. Set your OpenAI API key: `export OPENAI_API_KEY="your-key"`

## Steps

### Step 1: Parse & Import the Mbox File

Run the incremental update script to parse emails and generate AI summaries:

```bash
cd "/Users/robertfine/AI Database Assessment v012826/ai-knowledge-base"
python3 add_mbox.py
```

This will:
- Parse all new .mbox files in `attached_assets/`
- Deduplicate against existing emails
- Generate AI summaries for new emails
- Update `parsed_emails.json`

### Step 2: Migrate to SQLite Database

Sync the parsed emails to the SQLite database:

// turbo
```bash
cd "/Users/robertfine/AI Database Assessment v012826/ai-knowledge-base"
echo "y" | python3 scripts/migrate_to_sqlite.py
```

### Step 3: Generate Embeddings for Semantic Search

Generate vector embeddings for the new emails:

// turbo
```bash
cd "/Users/robertfine/AI Database Assessment v012826/ai-knowledge-base"
python3 -c "from services.embeddings import generate_all_embeddings; generate_all_embeddings()"
```

This only processes emails that don't have embeddings yet.

### Step 4: Enrich Links

Fetch metadata for new links (titles, descriptions):

// turbo
```bash
cd "/Users/robertfine/AI Database Assessment v012826/ai-knowledge-base"
python3 services/link_enricher.py --enrich 500
```

Adjust the limit as needed. At 1 req/sec, 500 links takes ~8 minutes.

### Step 5: Categorize New Emails

Classify emails into 27 granular categories using GPT-4o:

// turbo
```bash
cd "/Users/robertfine/AI Database Assessment v012826/ai-knowledge-base"
python3 scripts/recategorize_emails.py
```

This assigns primary + secondary categories to each email.

### Step 6: Refresh Learning Curriculum

Update the learning modules with new content:

// turbo
```bash
cd "/Users/robertfine/AI Database Assessment v012826/ai-knowledge-base"
python3 -c "from services.curriculum import initialize_curriculum; initialize_curriculum()"
```

This regenerates all 26 learning modules based on categories.

### Step 7: Restart the Server

// turbo
```bash
cd "/Users/robertfine/AI Database Assessment v012826/ai-knowledge-base"
pkill -f "python.*app" 2>/dev/null; sleep 2
python3 app.py &
```

## Verification

Check the stats after import:

```bash
cd "/Users/robertfine/AI Database Assessment v012826/ai-knowledge-base"

# Check database stats
python3 -c "from database import get_email_count; print(f'Total emails: {get_email_count()}')"

# Check embedding coverage
python3 -c "from services.embeddings import get_embedding_stats; import json; print(json.dumps(get_embedding_stats(), indent=2))"

# Check link enrichment progress
python3 services/link_enricher.py --stats

# Check learning modules
python3 -c "from services.curriculum import get_curriculum; print(f'Learning modules: {len(get_curriculum())}')"
```

## Quick One-Liner (After Mbox is Placed)

For a quick import without prompts (non-interactive):

```bash
cd "/Users/robertfine/AI Database Assessment v012826/ai-knowledge-base" && \
python3 add_mbox.py && \
echo "y" | python3 scripts/migrate_to_sqlite.py && \
python3 -c "from services.embeddings import generate_all_embeddings; generate_all_embeddings()" && \
python3 services/link_enricher.py --enrich 500 && \
python3 scripts/recategorize_emails.py && \
python3 -c "from services.curriculum import initialize_curriculum; initialize_curriculum()" && \
echo "✅ Import complete! Restart server with: python3 app.py"
```

## What Gets Updated

| Component | Updated |
|-----------|---------|
| 📧 Emails | New emails added to database |
| 🔗 Links | Link metadata enriched |
| 📂 Categories | All emails classified into 27 categories |
| 🔥 What's Hot | Auto-updated (queries live data) |
| 🛠️ Top Tools | Auto-updated (queries live data) |
| 📚 Learning | 26 modules regenerated with new lessons |
| 🔍 Search | Embeddings generated for semantic search |
