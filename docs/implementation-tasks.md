# AI Knowledge Base - Implementation Tasks

## Phase 1: Research Dashboard (Weeks 1-2)

### 1.1 Database Migration
- [ ] Create SQLite database schema (`data/knowledge.db`)
- [ ] Write migration script `scripts/migrate_to_sqlite.py`
- [ ] Migrate 11,700 emails from JSON to SQLite
- [ ] Add indexes for date, sender, categories
- [ ] **TEST**: Verify row count matches JSON, query performance < 100ms

### 1.2 Analytics Engine
- [ ] Create `services/analytics.py`
- [ ] Implement topic clustering (group similar emails)
- [ ] Implement trend detection (rising/falling topics by week)
- [ ] Implement tool mention extraction (Claude, Cursor, etc.)
- [ ] Add sentiment scoring (positive/negative/neutral)
- [ ] **TEST**: Verify clustering produces coherent groups, trends match manual analysis

### 1.3 AI Briefing Generator
- [ ] Create `services/briefings.py`
- [ ] Implement on-demand briefing generation
- [ ] Create briefing prompt template (hot topics, trends, takeaways)
- [ ] Add source email references to briefings
- [ ] Cache generated briefings in DB
- [ ] **TEST**: Generate briefing, verify relevance and accuracy

### 1.4 Tool Tracking Service
- [ ] Create `services/tools.py`
- [ ] Build tool/product name dictionary (50+ tools)
- [ ] Implement mention counting with date tracking
- [ ] Calculate sentiment per tool
- [ ] Track first/last mention dates
- [ ] **TEST**: Verify Claude Code has ~890 mentions, correct dates

### 1.5 Dashboard API Routes
- [ ] Create `routes/dashboard.py`
- [ ] `GET /api/briefing` - Generate/return briefing
- [ ] `GET /api/trends` - Topic trends over time
- [ ] `GET /api/tools` - Tool comparison matrix
- [ ] `GET /api/stats` - Overall statistics
- [ ] **TEST**: All endpoints return valid JSON, < 500ms response

### 1.6 Dashboard UI
- [ ] Create `templates/dashboard.html`
- [ ] Add executive briefing card (with generate button)
- [ ] Add trend charts (Chart.js line/bar charts)
- [ ] Add tool comparison matrix table
- [ ] Add "What's Hot" section
- [ ] Add date range filters
- [ ] Style with Tailwind CSS
- [ ] **TEST**: UI renders correctly, charts populate, filters work

### 1.7 Phase 1 Integration Testing
- [ ] End-to-end test: Load page → Generate briefing → View trends
- [ ] Performance test: Page load < 2s with all data
- [ ] Mobile responsiveness check

---

## Phase 2: Knowledge Graph + Semantic Search (Weeks 3-4)

### 2.1 Entity Extraction Pipeline
- [ ] Create `services/entities.py`
- [ ] Build entity extraction prompt for LLM
- [ ] Extract entities from all emails (batch processing)
- [ ] Store in `entities` and `email_entities` tables
- [ ] Create entity type taxonomy (tool, company, concept, person)
- [ ] **TEST**: Spot-check 20 emails for extraction accuracy > 85%

### 2.2 Vector Embeddings
- [ ] Create `services/embeddings.py`
- [ ] Set up OpenAI text-embedding-3-small integration
- [ ] Generate embeddings for all emails (batch with progress)
- [ ] Store embeddings in SQLite (BLOB or sqlite-vss)
- [ ] Implement similarity search function
- [ ] **TEST**: "Claude prompt tips" returns Claude-related emails

### 2.3 Relationship Mapping
- [ ] Design relationship types (integrates_with, competes_with, etc.)
- [ ] Create relationship extraction prompt
- [ ] Build `entity_relationships` table
- [ ] Calculate relationship strength scores
- [ ] **TEST**: Claude Code → MCP relationship exists, strength > 0.5

### 2.4 Semantic Search API
- [ ] Create `routes/search.py`
- [ ] `POST /api/search` - Semantic search with query
- [ ] Implement hybrid search (semantic + keyword)
- [ ] Add AI synthesis of search results
- [ ] Return sources with relevance scores
- [ ] **TEST**: Natural language queries return relevant results

### 2.5 Knowledge Graph Visualization
- [ ] Create `templates/graph.html`
- [ ] Implement D3.js force-directed graph
- [ ] Add node click → entity detail panel
- [ ] Add zoom/pan controls
- [ ] Filter by entity type
- [ ] **TEST**: Graph renders with 100+ nodes, interactions smooth

### 2.6 Entity Detail Pages
- [ ] Create `templates/entity.html`
- [ ] Show entity name, type, description
- [ ] Show all emails mentioning entity
- [ ] Show related entities
- [ ] Show sentiment over time
- [ ] **TEST**: Entity page loads for "Claude Code" with correct data

### 2.7 Search UI
- [ ] Create `templates/search.html`
- [ ] Add semantic search bar
- [ ] Add AI answer panel
- [ ] Add source email cards
- [ ] Add "Related Topics" suggestions
- [ ] **TEST**: Search flow works end-to-end

### 2.8 Phase 2 Integration Testing
- [ ] Search → Click result → View entity → Explore graph
- [ ] Verify graph relationships match extracted data
- [ ] Performance: Search returns in < 2s

---

## Phase 3: AI Learning Assistant (Weeks 5-7)

### 3.1 Curriculum Generation
- [ ] Create `services/curriculum.py`
- [ ] Design module/lesson structure schema
- [ ] Create curriculum generation prompt
- [ ] Generate 5-7 learning modules from email corpus
- [ ] Extract lesson content from source emails
- [ ] Store in `modules` and `lessons` tables
- [ ] **TEST**: Curriculum covers major topics, lessons have content

### 3.2 Quiz Generation
- [ ] Create `services/quiz.py`
- [ ] Design quiz question schema
- [ ] Create quiz generation prompt (from lesson content)
- [ ] Generate 3-5 questions per lesson
- [ ] Store questions with correct answers
- [ ] **TEST**: Quiz questions are relevant, answers are correct

### 3.3 Progress Tracking (Single User)
- [ ] Create `user_progress` table (no auth, single user)
- [ ] Track lesson completions with timestamps
- [ ] Track quiz scores
- [ ] Calculate overall progress percentage
- [ ] Store in localStorage + SQLite
- [ ] **TEST**: Progress persists across sessions

### 3.4 Learning Dashboard UI
- [ ] Create `templates/learning/home.html`
- [ ] Show current progress overview
- [ ] Show next recommended lesson
- [ ] Show learning streak (days active)
- [ ] Add skill radar chart
- [ ] **TEST**: Dashboard reflects actual progress

### 3.5 Module & Lesson UI
- [ ] Create `templates/learning/module.html`
- [ ] Create `templates/learning/lesson.html`
- [ ] Show lesson content with formatting
- [ ] Show source emails for each lesson
- [ ] Add "Mark Complete" button
- [ ] Add navigation (prev/next lesson)
- [ ] **TEST**: Can navigate through entire curriculum

### 3.6 Quiz Interface
- [ ] Create `templates/learning/quiz.html`
- [ ] Show questions one at a time
- [ ] Provide immediate feedback on answers
- [ ] Show final score with explanations
- [ ] Update progress on completion
- [ ] **TEST**: Complete quiz, verify score saved

### 3.7 Gamification (Simple)
- [ ] Add progress bars for each module
- [ ] Add "lessons completed" counter
- [ ] Add completion celebration animation
- [ ] Track learning streak
- [ ] **TEST**: Visual feedback works correctly

### 3.8 Phase 3 Integration Testing
- [ ] Full learning flow: Dashboard → Module → Lesson → Quiz → Progress update
- [ ] Verify progress persists after refresh
- [ ] Test all modules have content

---

## Final Integration & Polish

### 4.1 Navigation & UX
- [ ] Create unified navigation bar
- [ ] Add links between all sections (Dashboard, Search, Graph, Learn)
- [ ] Ensure consistent styling across all pages
- [ ] Add loading states for AI operations
- [ ] **TEST**: Navigate between all sections smoothly

### 4.2 Performance Optimization
- [ ] Add database query caching
- [ ] Lazy load graph visualization
- [ ] Paginate email lists
- [ ] Compress static assets
- [ ] **TEST**: All pages load < 2s, no memory leaks

### 4.3 Error Handling
- [ ] Add error handling for OpenAI API calls
- [ ] Add fallbacks for failed operations
- [ ] Add user-friendly error messages
- [ ] **TEST**: Simulate API failure, verify graceful degradation

### 4.4 Documentation
- [ ] Update README.md with new features
- [ ] Add setup instructions for Replit
- [ ] Document API endpoints
- [ ] Add environment variable list
- [ ] **TEST**: Fresh setup from README works

### 4.5 Deployment Prep
- [ ] Verify Replit compatibility
- [ ] Test with Replit environment variables
- [ ] Create .replit run configuration
- [ ] Final smoke test on Replit
- [ ] **TEST**: Deploy to Replit successfully
