# AI Job Search & Application Intelligence Platform

> A production-grade, open-source AI-powered job search and application tracking system built with **Python (FastAPI)** and a planned **Next.js 14** dashboard. Works for any domain (Data Engineering, AI/ML, Backend, Frontend, DevOps, etc.) via a Naukri-style dynamic preference matrix.

---

## 📑 Table of Contents

1. [What This Project Does](#-what-this-project-does)
2. [How the System Works (Architecture)](#-how-the-system-works-architecture)
3. [Installation & Local Setup](#-installation--local-setup)
4. [Optional Installations](#-optional-installations)
5. [Files You Should Edit for Customization](#-files-you-should-edit-for-customization)
6. [Step-by-Step Usage: From Install to Applying for Jobs](#-step-by-step-usage-from-install-to-applying-for-jobs)
7. [API Reference (curl examples)](#-api-reference-curl-examples)
8. [Configuration Reference](#-configuration-reference)
9. [Troubleshooting](#-troubleshooting)
10. [Project Structure](#-project-structure)
11. [Development Timeline](#-development-timeline)
12. [License](#-license)

---

## 🎯 What This Project Does

A complete end-to-end job search automation platform that:

| Stage | What it does |
|------|--------------|
| **🔍 Discovery** | Pulls jobs from Greenhouse, Lever, Ashby ATS APIs + accepts any URL or raw text |
| **🧹 Normalization** | Strips UTMs, standardizes titles, normalizes company names |
| **🔁 Deduplication** | 5-tier check: source+ID → URL → company+title → text Jaccard → embedding similarity |
| **🎯 Matching** | 4-stage explainable filter: hard rules → BM25 lexical → cosine vectors → LLM scoring |
| **📝 Tailoring** | Rewrites your resume for each job, **without ever inventing facts** (Diff Guard) |
| **📊 Tracking** | Kanban-style application CRM with full timeline (Discovered → Applied → Offer) |
| **💡 Answer Bank** | Saves your verified answers to common application questions |

**Key Promise:** The resume tailor uses an LLM but enforces a hard rule — *every claim must be traceable to your uploaded master resume or profile facts*. No fabricated metrics, no made-up employers.

---

## 🏗️ How the System Works (Architecture)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    JOB PIPELINE (End-to-End)                             │
└──────────────────────────────────────────────────────────────────────────┘

 [Greenhouse / Lever / Ashby]    [Any URL / Raw Text]
         │                              │
         └──────────────┬───────────────┘
                        ▼
              ┌─────────────────────┐
              │  1. NORMALIZATION   │  ← strip UTMs, normalize title/company
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │ 2. 5-TIER DEDUPE    │  ← source+ID, URL, company+title, Jaccard, embed
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │ 3. HARD FILTERS     │  ← location, salary, excluded keywords
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │ 4. LEXICAL (BM25)   │  ← keyword overlap with your skills
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │ 5. VECTOR (Cosine)  │  ← semantic similarity via embeddings
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │ 6. LLM EXPLAINER    │  ← Claude 3.5: pros / gaps / score breakdown
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │ 7. RESUME TAILOR    │  ← Claude 3.5 reorders + rephrases (NO fabrication)
              │    + DIFF GUARD     │     every bullet traceable to your facts
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │ 8. APPLICATION CRM  │  ← Kanban: DISCOVERED → APPLIED → OFFER
              └─────────────────────┘
```

---

## 🚀 Installation & Local Setup

### Prerequisites (Required)

| Tool | Version | Check command |
|------|---------|---------------|
| **Python** | 3.11+ (3.13.1 tested) | `python --version` |
| **Git** | Any recent | `git --version` |
| **pip** | Bundled with Python | `pip --version` |

> You do **not** need Docker, PostgreSQL, or Node.js for the backend to work. The system uses SQLite by default and runs zero-config.

### Step 1: Clone the Repository

```bash
git clone https://github.com/jayantorion/pythonmagic.git
cd pythonmagic
```

### Step 2: Create a Virtual Environment

**Windows (PowerShell / CMD):**
```cmd
cd backend
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs 11 packages (~50 MB):
- `fastapi`, `uvicorn` — web framework
- `pydantic`, `pydantic-settings` — validation & config
- `sqlalchemy`, `aiosqlite`, `asyncpg` — database
- `anthropic` — Claude 3.5 AI
- `httpx`, `beautifulsoup4` — HTTP + HTML parsing
- `pymupdf`, `python-docx` — resume PDF/DOCX parsing
- `numpy` — embeddings

### Step 4: Set Up Environment File

```bash
# From the project root (not inside backend/)
cp .env.example .env
```

> The `.env` file is auto-created from `.env.example` if you use the `run.py` launcher instead.

### Step 5: Start the Backend

**Option A — Using the launcher (recommended):**
```bash
# From project root
python run.py
```

**Option B — Direct uvicorn:**
```bash
# From inside backend/ with venv activated
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8765
INFO:     Application startup complete.
2026-09-04 XX:XX:XX,XXX [INFO] job_assistant: Database initialized. Engine: SQLite
```

### Step 6: Verify It Works

In a **new terminal**:
```bash
curl http://127.0.0.1:8765/health
# → {"status":"healthy"}

# Or run the bundled verification script
python simple_verify.py
```

Open the **interactive API docs** in your browser:
```
http://127.0.0.1:8765/docs
```

🎉 **You're up and running.** A default candidate profile ("Alex Data Engineer") is auto-created on first launch with 4 seed facts. You can replace it with your own data (see [Step 2 below](#step-2-customize-your-candidate-profile)).

---

## ⚙️ Optional Installations

These are **not required** to run the system. Install only what you need.

### 🟡 Optional: Anthropic Claude API Key (for AI features)

Without this key, the system uses a **deterministic offline heuristic** for matching and resume tailoring. The system works, but match scores and tailored resumes are less nuanced.

```bash
# Edit .env
ANTHROPIC_API_KEY=sk-ant-api03-...your-key-here
```

Get a key: [https://console.anthropic.com/](https://console.anthropic.com/)

**Free fallback behaviour:** All LLM features (job analysis, match explanation, resume tailoring, answer drafting, cover letter) automatically fall back to keyword-based heuristics when no key is set or if the API call fails.

### 🟡 Optional: OpenAI Embeddings (for semantic dedup)

By default the system uses a **local deterministic embedding** (hash-projected, offline, no cost). For better semantic deduplication, set:

```bash
# Edit .env
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-...your-openai-key
```

### 🟡 Optional: PostgreSQL + pgvector (for production / cloud)

By default the system uses **SQLite** — zero-config, works out of the box. For cloud deployment or when you need true vector similarity at scale:

```bash
# 1. Start PostgreSQL via Docker
docker compose up -d

# 2. Edit .env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/job_agent

# 3. Restart the backend — tables are auto-created
```

The system **auto-detects** which engine you're using via the URL prefix (`sqlite` vs `postgresql+asyncpg`).

### 🟡 Optional: Adzuna API (for additional job source)

Get a free key at [https://developer.adzuna.com/](https://developer.adzuna.com/) and add to `.env`:
```bash
ADZUNA_APP_ID=your-app-id
ADZUNA_APP_KEY=your-app-key
ADZUNA_COUNTRY=in
```

### 🔴 Optional: Next.js 14 Frontend (planned, not yet shipped)

The README is structured to support a Next.js 14 + shadcn/ui dashboard, but the frontend is not implemented yet. For now, use the **Swagger UI at `/docs`** to interact with all APIs visually.

---

## 📝 Files You Should Edit for Customization

Here's a map of **what to edit** for common customizations:

### 🟢 To customize your candidate profile (most common edit)

**File: [backend/app/api/v1/candidate.py](backend/app/api/v1/candidate.py)** — `get_or_create_default_profile()` function (lines 30-114)

This is the **seed data** the first time the app runs. Change:
- `full_name`, `email`, `phone`, `location` — your contact info
- `domain` — your target job domain (`Data Engineering`, `AI/ML`, `Backend`, etc.)
- `target_roles` — list of roles you're targeting
- `experience_years`, `experience_level` — your seniority
- `tech_stack_priorities` — must-have / preferred / nice-to-have skills
- `preferences` — work modes, locations, salary, excluded keywords/companies
- `career_summary` — short bio for the resume
- The `default_facts` list (lines 73-110) — your verified skills/experience bullets

> After the first run, the profile is **already in the database**, so editing the seed code does NOT change existing data. Use the API to update (see Step 2 below) or delete `backend/data/job_agent.db` to re-seed.

### 🟢 To customize hard filters / matching rules

**File: [backend/app/services/matching/hard_filters.py](backend/app/services/matching/hard_filters.py)**

Defines which jobs are filtered out before any AI scoring. Useful when you want to add domain-specific keywords or blacklist companies.

### 🟢 To customize the AI prompts (match / tailor)

**File: [backend/app/services/ai/claude.py](backend/app/services/ai/claude.py)**

Contains the system prompts for:
- `analyze_job_description()` — extracts structured requirements
- `evaluate_candidate_match()` — produces the match score
- `tailor_resume_ast()` — rewrites the resume
- `draft_answer_for_question()` — drafts application answers

### 🟢 To customize the local embedding algorithm

**File: [backend/app/services/ai/embedding.py](backend/app/services/ai/embedding.py)**

The `_generate_local_embedding()` function (lines 41-57) is the offline fallback. Adjust `dim` for different vector sizes.

### 🟡 To add a new job source

Create a new file in `backend/app/services/discovery/`, e.g. `my_ats.py`:
```python
from app.services.discovery.base import JobSource
class MyATS(JobSource):
    async def fetch_jobs(self, ...): ...
```
Then register it in `backend/app/api/v1/jobs.py` and `backend/app/api/v1/discover.py`.

### 🟡 To switch the default port

Edit [run.py](run.py) line 65 (`"--port", "8765"`) and the matching line in your `.env` if needed.

### 🟡 To change the database location

By default SQLite is at `backend/data/job_agent.db`. Change `DATA_DIR` in [backend/app/core/config.py](backend/app/core/config.py) line 9.

---

## 📖 Step-by-Step Usage: From Install to Applying for Jobs

This is the full **end-to-end workflow** the platform supports.

### Step 1: Start the backend

```bash
python run.py
# or: cd backend && python -m uvicorn app.main:app --reload
```

Verify: `curl http://127.0.0.1:8765/health` → `{"status":"healthy"}`

### Step 2: Customize your candidate profile

Edit the seed data in `backend/app/api/v1/candidate.py` (lines 30-114), then **delete the existing DB**:
```bash
rm backend/data/job_agent.db
# Restart the server — fresh profile is seeded
```

OR update via API:
```bash
curl -X PUT http://127.0.0.1:8765/api/v1/candidate/profile \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Your Name",
    "domain": "Data Engineering",
    "experience_years": 4,
    "tech_stack_priorities": {
      "must_have": ["Python", "SQL", "Spark"],
      "preferred": ["dbt", "Snowflake"],
      "nice_to_have": ["Kubernetes"]
    },
    "preferences": {
      "work_modes": ["remote"],
      "salary_expectation": {"min_amount": 2500000, "currency": "INR", "period": "annual"},
      "excluded_keywords": ["PHP", "WordPress"]
    }
  }'
```

### Step 3: Upload your master resume (PDF or DOCX)

```bash
curl -X POST http://127.0.0.1:8765/api/v1/candidate/resume/upload \
  -F "file=@/path/to/your/resume.pdf" \
  -F "is_master=true"
```

The parser extracts:
- Contact info
- Skills by category
- Work experience with bullet points
- Education
- Projects
- Certifications

…and **stores atomic facts** in the database. These facts become the "ground truth" for the Diff Guard.

### Step 4: Discover jobs (3 ways)

**Option A — Pull from ATS feeds (Greenhouse, Lever, Ashby):**
```bash
curl -X POST "http://127.0.0.1:8765/api/v1/jobs/discover?query=Data+Engineer&limit=20"
```

**Option B — Paste a single job URL (works for Naukri, LinkedIn, Indeed, etc.):**
```bash
curl -X POST http://127.0.0.1:8765/api/v1/jobs/ingest \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.linkedin.com/jobs/view/1234567"}'
```

**Option C — Paste raw job description text:**
```bash
curl -X POST http://127.0.0.1:8765/api/v1/jobs/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "Senior Data Engineer at Acme Corp\nLocation: Bangalore\nWe are looking for...",
    "company_name": "Acme Corp",
    "title": "Senior Data Engineer"
  }'
```

Each ingested job goes through the full pipeline: normalize → 5-tier dedupe → hard filters → match scoring.

### Step 5: Browse ranked jobs

```bash
# All jobs, ranked by match score
curl "http://127.0.0.1:8765/api/v1/jobs?limit=20"

# Only remote jobs
curl "http://127.0.0.1:8765/api/v1/jobs?remote_only=true"

# Only jobs with match score >= 80
curl "http://127.0.0.1:8765/api/v1/jobs?min_score=80"

# Search by keyword
curl "http://127.0.0.1:8765/api/v1/jobs?query=spark"
```

Each job returns:
- `match.overall_score` (0-100)
- `match.recommendation` (`EXCELLENT` / `STRONG` / `CONSIDER` / `WEAK` / `SKIP`)
- `match.pros` (bullet list)
- `match.gaps` (bullet list)
- `match.dealbreakers` (if any)

### Step 6: Get full match explanation for a job

```bash
curl "http://127.0.0.1:8765/api/v1/jobs/{job_id}"
```

Returns the structured breakdown: skills matched, skills missing, experience fit, seniority fit, domain fit.

### Step 7: Tailor your resume for a specific job

```bash
curl -X POST http://127.0.0.1:8765/api/v1/resume/tailor \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "uuid-of-target-job",
    "variant_type": "targeted"
  }'
```

Returns:
- `tailored_ast` — the modified resume structure
- `diff_provenance` — which facts were used / which bullets were rephrased
- `ats_score` — keyword density + structure quality (0-100)
- `id` — save this to download the HTML later

The Diff Guard **blocks** any tailoring that tries to add skills, companies, or metrics not in your master resume.

### Step 8: Download the tailored HTML resume

```bash
curl "http://127.0.0.1:8765/api/v1/resume/{version_id}/download" -o tailored_resume.html
```

Open the HTML in any browser → print to PDF (Ctrl+P → Save as PDF).

### Step 9: Move job to "Apply" status in the CRM

```bash
curl -X PATCH http://127.0.0.1:8765/api/v1/applications/{application_id} \
  -H "Content-Type: application/json" \
  -d '{
    "status": "APPLIED",
    "notes": "Submitted via company career portal, ref: ABC-123"
  }'
```

### Step 10: Track your entire pipeline

```bash
# All applications, grouped by status
curl http://127.0.0.1:8765/api/v1/applications

# Stats overview
curl http://127.0.0.1:8765/api/v1/applications/stats
```

Returns counts per lifecycle stage: `DISCOVERED`, `SHORTLISTED`, `READY_TO_APPLY`, `APPLIED`, `INTERVIEWING`, `OFFER`, `REJECTED`, `WITHDRAWN`.

### Step 11: Save answers to common application questions

When you answer a screening question, save the verified answer so the platform can auto-draft it next time:

```bash
curl -X POST http://127.0.0.1:8765/api/v1/candidate/answers \
  -H "Content-Type: application/json" \
  -d '{
    "question_text": "Why do you want to work at our company?",
    "verified_answer": "Your real, verified answer here.",
    "category": "motivation"
  }'
```

When you encounter the same question again:
```bash
curl -X POST "http://127.0.0.1:8765/api/v1/candidate/answers/draft?question=Why+do+you+want+to+work+at+our+company"
# Returns: { "answer": "Your real, verified answer here.", "source": "verified_answer_bank" }
```

If the question is new, the AI drafts a response **grounded only in your verified facts** (no fabrication).

### Step 12: Update the CRM as you progress

```bash
# Got an interview?
curl -X PATCH http://127.0.0.1:8765/api/v1/applications/{id} \
  -d '{"status": "INTERVIEWING", "notes": "Phone screen scheduled for 2026-09-10"}'

# Got an offer?
curl -X PATCH http://127.0.0.1:8765/api/v1/applications/{id} \
  -d '{"status": "OFFER", "notes": "Offer: 28LPA + 50k RSUs"}'

# Rejected?
curl -X PATCH http://127.0.0.1:8765/api/v1/applications/{id} \
  -d '{"status": "REJECTED", "notes": "Position closed"}
```

Every status change is logged as a timeline event in the application's history.

---

## 🔌 API Reference (curl examples)

All endpoints are under `http://127.0.0.1:8765/api/v1/`. Interactive docs: `/docs`.

### Candidate

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/candidate/profile` | Get your profile |
| `PUT` | `/candidate/profile` | Update your profile |
| `GET` | `/candidate/facts` | List verified facts |
| `POST` | `/candidate/facts` | Add a new fact |
| `GET` | `/candidate/answers` | List saved answers |
| `POST` | `/candidate/answers` | Save a verified answer |
| `POST` | `/candidate/answers/draft?question=...` | Draft a new answer (AI or saved) |
| `POST` | `/candidate/resume/upload` | Upload master resume (multipart) |
| `GET` | `/candidate/resume/master` | Get master resume record |

### Jobs

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/jobs/discover?query=...&limit=20` | Trigger discovery from ATS feeds |
| `POST` | `/jobs/ingest` | Ingest single job (URL or text) |
| `GET` | `/jobs` | List jobs (filters: `query`, `min_score`, `remote_only`, `status`, `limit`, `offset`) |
| `GET` | `/jobs/{id}` | Job detail with full match breakdown |

### Resume

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/resume/tailor` | Generate tailored resume AST + diff |
| `GET` | `/resume/{version_id}/download` | Download as HTML |

### Applications

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/applications` | List all (filter: `status_filter=APPLIED`) |
| `GET` | `/applications/{id}` | Single app + timeline events |
| `PATCH` | `/applications/{id}` | Update status, notes, follow-up date |
| `GET` | `/applications/stats` | Aggregate counts by status |

---

## 🔧 Configuration Reference

All configuration is in `.env` (auto-created from `.env.example` on first run).

### Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/job_agent.db` | SQLAlchemy URL. Switch to `postgresql+asyncpg://...` for production. |

### AI

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | empty | Get from [console.anthropic.com](https://console.anthropic.com/). Falls back to heuristics if unset. |
| `ANTHROPIC_MODEL` | `claude-3-5-sonnet-20241022` | For complex tasks (match evaluation, resume tailoring) |
| `ANTHROPIC_FAST_MODEL` | `claude-3-5-haiku-20241022` | For cheaper/faster tasks (job analysis, Q&A drafts) |
| `EMBEDDING_PROVIDER` | `local` | `local` (offline) or `openai` |
| `OPENAI_API_KEY` | empty | Required only if `EMBEDDING_PROVIDER=openai` |

### Job Sources (Optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `ADZUNA_APP_ID` | empty | Optional aggregator feed |
| `ADZUNA_APP_KEY` | empty | Optional aggregator feed |
| `ADZUNA_COUNTRY` | `in` | ISO country code |

### Web

| Variable | Default | Description |
|----------|---------|-------------|
| `API_V1_STR` | `/api/v1` | URL prefix for all API routes |
| `CORS_ORIGINS` | `["http://localhost:3000", ...]` | Allowed origins for browser frontend |
| `APP_TITLE` | `AI Job Search & Application Intelligence Platform` | Shown in OpenAPI docs |
| `PORT` | `8765` (set via uvicorn arg) | Server port |

---

## 🩺 Troubleshooting

### `ModuleNotFoundError: No module named 'X'`
```bash
pip install -r requirements.txt
# Or for a specific package:
pip install X
```

### Port 8765 already in use
Edit [run.py](run.py) line 65 to a different port, or kill the conflicting process:
```cmd
netstat -ano | findstr :8765
taskkill /PID <pid> /F
```

### Database locked (Windows)
```cmd
# Find the process holding the SQLite file
tasklist | findstr python
taskkill /PID <pid> /F
```

### Unicode / encoding errors on Windows
The verification scripts auto-force UTF-8. If you write your own scripts, add at the top:
```python
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
```

### LLM features are returning generic / heuristic results
- Make sure `ANTHROPIC_API_KEY` is set in `.env`
- Restart the server after editing `.env`
- Check the log output for `Error calling Claude for ...` messages

### Want a clean slate?
```bash
# Stop the server, then:
rm backend/data/job_agent.db
# Restart — fresh database with default profile
```

---

## 🗂️ Project Structure

```
AIMODELTEST/
├── backend/                        # Python FastAPI application
│   ├── app/
│   │   ├── api/v1/                # REST endpoints (candidate, jobs, resume, applications)
│   │   ├── core/                  # config.py, database.py, logging.py
│   │   ├── models/                # SQLAlchemy ORM (candidate, job, match, resume, application)
│   │   ├── schemas/               # Pydantic request/response shapes
│   │   └── services/
│   │       ├── ai/                # Claude provider, embeddings
│   │       ├── discovery/         # Greenhouse, Lever, Ashby, universal URL parser
│   │       ├── matching/          # hard_filters, lexical_ranker, vector_matcher, explainer
│   │       ├── normalization/     # canonicalizer, deduplicator (5-tier)
│   │       └── resume/            # parser, tailor, diff_guard, pdf_generator
│   ├── data/                       # SQLite database (gitignored)
│   ├── storage/                    # Uploaded resumes & generated HTML (gitignored)
│   └── requirements.txt            # 11 dependencies, ~50 MB
├── .env.example                    # Template (copy to .env)
├── .gitignore                      # Excludes __pycache__, data/, storage/, .env
├── docker-compose.yml              # PostgreSQL+pgvector for production
├── init-postgres.sh                # Initializes pgvector extension
├── run.py                          # Local launcher (handles venv, .env, port)
├── simple_verify.py                # 5-step smoke test
├── verify_system.py                # 7-step full system test
├── LINEAGE.md                      # LOCAL ONLY — full file map & data flow
└── README.md                       # This file
```

See [LINEAGE.md](LINEAGE.md) for a detailed file-by-file breakdown (local only, not pushed to git).

---

## 📅 Development Timeline

This project was developed over a 2-week period (Aug 21 - Sep 4, 2026).

### Week 1: Foundation & Core Architecture (Aug 21-27)
- **Aug 21**: Project initialization — FastAPI + dual-mode DB engine
- **Aug 22-23**: Database models, Pydantic schemas, core config
- **Aug 24**: Anthropic Claude integration + embedding services
- **Aug 25**: Core API endpoints (candidate, jobs, applications)
- **Aug 26-27**: Job matching engine + resume tailoring system

### Week 2: Features & Polish (Aug 28 - Sep 4)
- **Aug 28-29**: Deduplication engine + normalization
- **Aug 30**: Documentation (README, LINEAGE, scripts)
- **Aug 31 - Sep 1**: Testing + system verification
- **Sep 2**: Docker setup, environment configuration
- **Sep 3**: Final config (.gitignore, packaging)
- **Sep 4**: Production-ready release

**Total**: 14 days, ~4,740 LOC across 53 source files.

### Development Milestones

✅ **Week 1 (Aug 21-27)**
- Milestone 1: Project Scaffold & Dual-Mode DB Engine
- Milestone 2: Candidate Profile & Dynamic Preferences
- Milestone 3: Universal Job Discovery & 5-Tier Deduplication
- Milestone 4: Multi-Stage Domain Matching & Explainable Scoring

✅ **Week 2 (Aug 28 - Sep 4)**
- Milestone 5: Zero-Fabrication Resume Tailoring & Diff Guard
- Milestone 6: Application CRM & Timeline Logger
- Milestone 7: Next.js 14 Dashboard UI (frontend structure planned)
- Milestone 8: Packaging, Launchers, Testing & Full Documentation

---

## 📄 License

MIT

## 🙏 Acknowledgments

Built with [FastAPI](https://fastapi.tiangolo.com/), [SQLAlchemy 2.0](https://www.sqlalchemy.org/), [Pydantic v2](https://docs.pydantic.dev/), and [Anthropic Claude 3.5](https://www.anthropic.com/).
