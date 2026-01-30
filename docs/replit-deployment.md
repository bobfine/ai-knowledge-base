# Replit Deployment Guide

Step-by-step guide to deploy the AI Knowledge Base to Replit.

---

## Prerequisites

1. Replit account (free tier works)
2. GitHub repository with your code (already done: `bobfine/ai-knowledge-base`)
3. OpenAI API key

---

## Step 1: Import from GitHub

1. Go to [replit.com](https://replit.com)
2. Click **"Create Repl"**
3. Select **"Import from GitHub"**
4. Paste your repo URL: `https://github.com/bobfine/ai-knowledge-base`
5. Click **"Import from GitHub"**

Replit will auto-detect Python and create the project.

---

## Step 2: Configure Environment

### Add Secrets (Environment Variables)

1. Click the **"Secrets"** tab (🔒 lock icon in left sidebar)
2. Add the following secret:

| Key | Value |
|-----|-------|
| `OPENAI_API_KEY` | `sk-proj-...your-key...` |

### Verify `.replit` File

Replit should auto-create this. If not, create `.replit`:

```toml
run = "python3 app.py"
modules = ["python-3.11"]

[nix]
channel = "stable-24_05"

[deployment]
run = ["sh", "-c", "python3 app.py"]
deploymentTarget = "cloudrun"

[[ports]]
localPort = 8080
externalPort = 80
```

---

## Step 3: Install Dependencies

Replit auto-installs from `requirements.txt`. Verify it exists:

```
flask>=2.0
openai>=1.0
numpy
python-dateutil
```

If missing packages, click **"Shell"** and run:
```bash
pip install flask openai numpy python-dateutil
```

---

## Step 4: Upload Database

Your SQLite database needs to be uploaded:

1. Click **"Files"** tab in Replit
2. Navigate to `data/` folder (create if missing)
3. Upload `knowledge.db` from your local machine

**Alternative:** Run migration on Replit:
```bash
python3 scripts/migrate_to_sqlite.py
```

---

## Step 5: Run the App

1. Click the green **"Run"** button
2. Replit will start Flask on port 8080
3. A preview window opens with your app

---

## Step 6: Deploy to Production

1. Click **"Deploy"** button (top right)
2. Choose **"Reserved VM"** or **"Autoscale"**
3. Configure:
   - **Name:** ai-knowledge-base
   - **Run command:** `python3 app.py`
4. Click **"Deploy"**

You'll get a public URL like: `https://ai-knowledge-base.yourname.repl.co`

---

## Files to Include

Make sure these are in your repo:

```
├── app.py                    # Main Flask app
├── database.py               # Database connection
├── requirements.txt          # Python dependencies
├── data/
│   ├── knowledge.db          # SQLite database
│   └── emails.json           # Backup data
├── services/
│   ├── analytics.py
│   ├── briefings.py
│   ├── curriculum.py
│   ├── embeddings.py
│   └── link_enricher.py
├── routes/
│   ├── api.py
│   └── learning.py
├── templates/
│   ├── dashboard.html
│   ├── index.html
│   ├── learn.html
│   ├── search.html
│   └── tools.html
└── static/                   # CSS/JS assets
```

---

## Files to Exclude (Optional)

Add to `.gitignore` if not already:

```
attached_assets/              # Raw mbox files (large)
*.mbox
enrichment.log
__pycache__/
.env
```

---

## Post-Deployment Checklist

- [ ] App loads at Replit URL
- [ ] Dashboard shows stats and categories
- [ ] Search works (semantic + keyword)
- [ ] Learning modules load
- [ ] AI Briefing generates (requires OPENAI_API_KEY secret)

---

## Updating After Deployment

To push updates:

1. Commit changes locally:
   ```bash
   git add -A && git commit -m "Update" && git push
   ```

2. In Replit, click **"Git"** tab → **"Pull"**

3. Click **"Redeploy"** if using Deployments

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No module named X" | Run `pip install X` in Shell |
| Database not found | Upload `data/knowledge.db` or run migration |
| API key error | Add `OPENAI_API_KEY` to Secrets |
| Port conflict | Ensure app runs on port 8080 |
| Static files 404 | Check `static/` folder exists |
