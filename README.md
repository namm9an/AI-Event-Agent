# AI Event Agent

Scout-grade event intelligence for E2E Networks' marketing and events team. Automatically discovers AI/ML/Cloud/GPU events across India, identifies speakers with enriched metadata, generates daily PDF reports, and serves everything through a role-based dashboard.

---

## What it does

- **Scrapes** AI/ML/Cloud events daily via DuckDuckGo + Crawl4AI (no browser required)
- **Enriches** each event with speaker details: LinkedIn, Wikipedia, topic links, previous talks
- **Generates** a daily PDF report at 12:00 IST, downloadable from the dashboard
- **Serves** a REST API with JWT auth — read-only users and super admins
- **Runs** a modern Next.js dashboard with event table, speaker details, report downloads, and a chat assistant

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Daily Pipeline (00:00 IST)               │
│                                                                  │
│  DuckDuckGo Search → Crawl4AI Scrape → Direct LLM Calls        │
│       (Python)             (Python)        (Nemotron 30B)       │
│                                                                  │
│  Step 1: Enrichment  — extract event metadata from raw markdown │
│  Step 2: Speakers    — identify speakers + LinkedIn/Wikipedia    │
│  Step 3: Formatter   — validate, deduplicate, normalize JSON     │
│                                    │                             │
│                              SQLite DB                           │
└─────────────────────────────────────────────────────────────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     │       FastAPI (port 8010)    │
                     │       JWT Auth (HS256)        │
                     └──────────────┬──────────────┘
                                    │
                     ┌──────────────┴──────────────┐
                     │    Next.js Dashboard (3010)  │
                     │    Reports · Chat · Admin    │
                     └─────────────────────────────┘
```

**LLM**: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` served via vLLM on A100 80GB
**Key design choice**: Direct `ChatOpenAI` calls instead of CrewAI ReAct loops — avoids parsing failures from Nemotron's `<think>...</think>` output format.

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI + SQLAlchemy + SQLite |
| LLM | Nemotron 30B via OpenAI-compatible vLLM endpoint |
| Scraping | DuckDuckGo (`ddgs`) + Crawl4AI |
| Scheduling | APScheduler (in-process cron) |
| Auth | PyJWT (HS256, 24h sessions) |
| Reports | fpdf2 (PyMuPDF fallback) |
| Frontend | Next.js 14 + Tailwind CSS |

---

## Project Structure

```
.
├── main.py              # FastAPI server — all API endpoints
├── auth.py              # JWT auth, role guards
├── config.py            # Env config, LLM client factory
├── crew.py              # Hybrid pipeline: scrape → LLM → DB
├── scraper.py           # DuckDuckGo search + Crawl4AI scrape
├── requirements.txt
├── db/
│   ├── database.py      # Engine, session, migrations, seeding
│   └── models.py        # Event, Speaker, ScrapeRun, SearchQuery, Report, AppSetting
├── services/
│   ├── report_service.py     # PDF generation
│   ├── scheduler_service.py  # APScheduler wrapper
│   └── settings_service.py   # DB-backed key-value settings
├── frontend/            # Next.js 14 dashboard
│   ├── app/
│   ├── components/
│   └── lib/
└── reports/             # Generated daily PDFs (runtime)
```

---

## Quickstart (Local)

### Prerequisites

- Python 3.11+
- Node.js 18+
- vLLM endpoint running Nemotron (or any OpenAI-compatible model)

### Backend

```bash
# 1. Clone and enter project
git clone https://github.com/namm9an/AI-Event-Agent
cd AI-Event-Agent

# 2. Create virtualenv and install
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Copy and fill env
cp .env.example .env
# Edit .env — set LLM_INFERENCE_URL, JWT_SECRET at minimum

# 4. Start backend
uvicorn main:app --host 0.0.0.0 --port 8010 --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev   # starts on port 3010
```

Open `http://localhost:3010` — login with `user / user` (read-only) or `super_admin / super_admin` (admin).

---

## Environment Variables

Create a `.env` file in the project root:

```env
# LLM endpoint (OpenAI-compatible)
LLM_INFERENCE_URL=http://101.53.140.68:8000/v1
LLM_API_KEY=none
LLM_MODEL=nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16

# Database
DATABASE_URL=sqlite:///./events.db

# Auth — change JWT_SECRET in production
JWT_SECRET=replace-with-a-strong-random-secret
JWT_EXPIRE_HOURS=24
NORMAL_USER_USERNAME=user
NORMAL_USER_PASSWORD=user
SUPER_ADMIN_USERNAME=super_admin
SUPER_ADMIN_PASSWORD=super_admin

# Scheduler
APP_TIMEZONE=Asia/Kolkata
DEFAULT_SCRAPE_TIME=00:00
DEFAULT_REPORT_TIME=12:00
REPORTS_DIR=./reports
REPORT_FONT_PATH=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf

# Scraping
MAX_TOKENS_PER_PAGE=6000
DDGS_RETRY_COUNT=3
DDGS_BASE_DELAY=2
MAX_SPEAKERS_PER_EVENT=5

# Logging
LOG_LEVEL=INFO
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8010
```

---

## API Reference

### Auth

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/login` | — | Get JWT token |
| GET | `/api/auth/me` | User | Token info |

**Login request:**
```json
{ "username": "user", "password": "user" }
```

### User Endpoints (any authenticated user)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | Server status, last run metrics |
| GET | `/api/events` | List events (filter by status, city, category, search) |
| GET | `/api/events/{id}` | Single event with speakers |
| GET | `/api/speakers` | List all speakers |
| GET | `/api/reports` | List generated reports |
| GET | `/api/reports/{id}/download` | Download PDF report |
| POST | `/api/chat` | Chat with event assistant (supports `report_id` context) |

### Admin Endpoints (super_admin only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/queries` | List search queries |
| POST | `/api/admin/queries` | Add search query |
| PUT | `/api/admin/queries/{id}` | Update query |
| DELETE | `/api/admin/queries/{id}` | Delete query |
| GET | `/api/admin/schedule` | Get current schedule |
| PUT | `/api/admin/schedule` | Update scrape/report times |
| POST | `/api/admin/run-now` | Trigger scrape immediately |
| POST | `/api/admin/reports/generate-now` | Trigger report immediately |

---

## Dashboard Features

| Page | Role | Features |
|------|------|---------|
| `/` | Public | Landing + auto-redirect if logged in |
| `/login` | Public | JWT login form |
| `/dashboard` | User | Events table, speaker details, report sidebar, chat |
| `/settings` | super_admin | Query manager, schedule editor, manual run buttons |

---

## Scheduling

Schedules are persisted in the DB and editable via the admin API:

| Job | Default (IST) | Description |
|-----|--------------|-------------|
| Scrape | 00:00 | Full pipeline — search, scrape, extract |
| Report | 12:00 | Generate PDF from today's events |

Changes take effect immediately without restart.

---

## Roles

| Role | Credentials | Access |
|------|------------|--------|
| `user` | `user / user` | Events, speakers, reports, chat |
| `super_admin` | `super_admin / super_admin` | Everything + query/schedule/run management |

---

## VM Deployment (scout.docustory.in)

```bash
# SSH into VM
ssh root@205.147.102.105

# Pull latest
cd /path/to/AI-Event-Agent
git pull origin main

# Restart backend in tmux
tmux new-session -d -s backend "source venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8010"

# Restart frontend in tmux
tmux new-session -d -s frontend "cd frontend && npm run build && npm start -- -p 3010"

# Model server already running on port 8000 (Nemotron via vLLM)
```

**NGINX config** — proxy `scout.docustory.in` → `localhost:3010`, `/api/*` → `localhost:8010`.

---

## Data Model

### Event
`id, name, description, date_text, location, city, status, category[], url, organizer, event_type, registration_url, image_url, scraped_at, last_scraped_at`

### Speaker
`id, event_id, name, designation, company, talk_title, talk_summary, linkedin_url, linkedin_bio, topic_links[], topic_category, previous_talks[], wikipedia_url`

### Report
`id, report_date, file_name, file_path, status, summary_json, raw_text, created_at`

### SearchQuery (admin-editable)
`id, query, topic, is_active, priority, created_at`

---

## Notes

- `.env`, `events.db`, `reports/`, and `venv/` are gitignored — never commit secrets
- The pipeline uses direct LLM calls (not CrewAI ReAct) to handle Nemotron's thinking-token output
- Speaker enrichment is best-effort — never fabricates data, uses empty strings for missing fields
- Duplicate detection uses exact URL match + fuzzy name+date matching (85% threshold)
