# AI Event Agent (2026)

Production-oriented event intelligence platform for AI/ML/Cloud/GPU topics.

## What this project does
- Runs a scheduled web intelligence pipeline for India-focused tech events.
- Extracts events, speakers, topics, and source links using Nemotron (OpenAI-compatible vLLM endpoint).
- Enriches speakers with best-effort public web metadata:
  - LinkedIn URL and public bio snippet
  - Wikipedia URL (if found)
  - previous-talk references (if found)
- Generates a shared daily PDF report.
- Serves a role-based API for dashboard + admin controls.

## Runtime model
- Primary model: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16`
- Endpoint style: OpenAI-compatible REST (`/v1/...`)
- Current endpoint convention:
  - `LLM_INFERENCE_URL=http://101.53.140.68:8000/v1`

## Roles and auth
- `user`: read events/speakers/reports + chat
- `super_admin`: user capabilities + query CRUD + schedule edits + manual run actions
- Auth: JWT (`HS256`) with 24-hour session

## API surface (v2)
### Auth
- `POST /api/auth/login`
- `GET /api/auth/me`

### User
- `GET /api/status`
- `GET /api/events`
- `GET /api/events/{id}`
- `GET /api/speakers`
- `GET /api/reports`
- `GET /api/reports/{report_id}/download`
- `POST /api/chat` (supports optional `report_id` context)

### Super admin
- `GET /api/admin/queries`
- `POST /api/admin/queries`
- `PUT /api/admin/queries/{query_id}`
- `DELETE /api/admin/queries/{query_id}`
- `GET /api/admin/schedule`
- `PUT /api/admin/schedule`
- `POST /api/admin/run-now`
- `POST /api/admin/reports/generate-now`

## Scheduling defaults
- Timezone: `Asia/Kolkata`
- Daily scrape: `00:00`
- Daily report generation: `12:00`

Schedule is persisted in DB and can be edited by super admin APIs.

## Tech stack
- FastAPI + SQLAlchemy + SQLite
- CrewAI orchestration + deterministic scrape layer
- DuckDuckGo search + Crawl4AI scraping
- APScheduler for in-app scheduling
- PyJWT for auth
- fpdf2/PyMuPDF fallback for PDF generation

## Project layout
```text
.
├── main.py
├── auth.py
├── config.py
├── crew.py
├── scraper.py
├── requirements.txt
├── agents/
├── db/
├── services/
├── tools/
└── backend/                # local runtime artifacts (ignored)
    ├── .env
    ├── events.db
    ├── reports/
    └── venv/
```

## Environment variables
Create runtime `.env` (kept local/ignored):

```env
LLM_INFERENCE_URL=http://101.53.140.68:8000/v1
LLM_API_KEY=none
LLM_MODEL=nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16

DATABASE_URL=sqlite:///./events.db

JWT_SECRET=replace-with-strong-random-secret
JWT_EXPIRE_HOURS=24
NORMAL_USER_USERNAME=user
NORMAL_USER_PASSWORD=user
SUPER_ADMIN_USERNAME=super_admin
SUPER_ADMIN_PASSWORD=super_admin

APP_TIMEZONE=Asia/Kolkata
DEFAULT_SCRAPE_TIME=00:00
DEFAULT_REPORT_TIME=12:00
REPORTS_DIR=./reports

MAX_TOKENS_PER_PAGE=8000
DDGS_RETRY_COUNT=3
DDGS_BASE_DELAY=2
MAX_SPEAKERS_PER_EVENT=5
SPEAKER_SEARCH_TIMEOUT=10

LOG_LEVEL=INFO
```

## Local run
From project root (use your venv python):

```bash
uvicorn main:app --host 0.0.0.0 --port 8010 --reload
```

## VM run (tmux)
Recommended split:
- backend API: `8010`
- frontend: `3010`
- model server: `8000`

### Inbound rules guidance
- Open `3010` if frontend is directly exposed.
- Open `8010` only if direct API access is needed externally.
- If using reverse proxy (recommended), keep backend private and expose only domain ports.

## Domain target
Planned public domain: `scout.docustory.in`.

## Notes
- This repo intentionally ignores local secrets/runtime artifacts (`.env`, DB, reports, venv).
- `docs/` and `.claude/` are local-only by current workflow preferences.
