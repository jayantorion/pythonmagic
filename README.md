# AI Job Search & Application Intelligence Platform

A Intelligence Platform

A production-grade AI-powered job search and application tracking system built with Python (FastAPI) and Next.js 14.

## Overview

This platform automates the entire job search lifecycle:
- **Discovery**: Scrapes jobs from ATS APIs (Greenhouse, Lever, Ashby) and universal URL ingestion
- **Matching**: Multi-stage explainable scoring (hard filters → lexical → vector → LLM)
- **Tailoring**: Zero-fabrication resume customization with Diff Guard verification
- **Tracking**: Complete application CRM with timeline logging
- **Learning**: Outcome-based preference refinement

## Features

- **Dual-mode Storage**: SQLite (local default) ↔️ PostgreSQL + pgvector (production)
- **Naukri-style Preferences**: Dynamic preference matrix for any domain
- **Universal Parser**: Extract jobs from any URL or raw text
- **5-Tier Deduplication**: Source+ID, URL, Company+Title, Text Jaccard, Embeddings
- **Explainable Matching**: Human-readable pros/cons/gaps with scoring breakdown
- **Zero-Fabrication Resume**: Never invents facts; Diff Guard ensures truthfulness
- **Application Tracking**: Kanban-style lifecycle (Discovered → Applied → Interview → Offer)
- **Extensible Design**: Modular architecture for easy feature addition

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Anthropic API key (optional for heuristic mode)
python -m uvicorn app.main:app --reload
```

### Frontend Setup (Coming Soon)
```bash
# cd frontend
# npm install
# npm run dev
```

## Architecture

```
Job Discovery → Normalization → Deduplication → Hard Filters → 
Lexical Ranking → Vector Similarity → LLM Matching → Resume Tailoring → Application CRM
```

## API Endpoints

- `POST /api/v1/jobs/discover` - Trigger job discovery
- `GET /api/v1/jobs` - List discovered jobs with filtering
- `POST /api/v1/jobs/ingest` - Ingest single job from URL/text
- `GET /api/v1/jobs/{id}` - Get job details with match explanation
- `POST /api/v1/resume/tailor` - Generate tailored resume
- `GET /api/v1/applications` - Application CRM
- `GET /api/v1/candidate/profile` - Candidate preferences & facts

## Configuration

See `.env.example` for all options:
- `DATABASE_URL`: SQLite (default) or PostgreSQL connection string
- `ANTHROPIC_API_KEY`: For LLM-powered features (heuristic fallback available)
- `EMBEDDING_PROVIDER`: `local` (default) or `openai`

## Development Milestones

✅ Milestone 1: Project Scaffold & Dual-Mode DB Engine  
✅ Milestone 2: Candidate Profile & Dynamic Preferences  
✅ Milestone 3: Universal Job Discovery & 5-Tier Deduplication  
✅ Milestone 4: Multi-Stage Domain Matching & Explainable Scoring  
✅ Milestone 5: Zero-Fabrication Resume Tailoring & Diff Guard  
✅ Milestone 6: Application CRM & Timeline Logger  
✅ Milestone 7: Next.js 14 Dashboard UI (Implemented)  
✅ Milestone 8: Packaging, Launchers & Documentation (Completed)

## License

MIT

## Acknowledgments

Built with FastAPI, SQLAlchemy 2.0, Pydantic v2, and Anthropic Claude.