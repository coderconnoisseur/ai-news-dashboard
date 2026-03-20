# AI News Aggregation & Broadcasting Dashboard

> Built for Culinda · v1.1 · FastAPI · React · PostgreSQL · Claude AI

A production-ready dashboard that automatically ingests AI/ML news from 20+ sources, deduplicates stories, enriches them with Claude-generated summaries and images, and lets you broadcast curated favorites to Email, LinkedIn, and WhatsApp in three clicks.

---

## Table of contents

- [Features](#features)
- [Architecture](#architecture)
- [Database schema](#database-schema)
- [Quick start](#quick-start)
- [Local development](#local-development)
- [Configuration reference](#configuration-reference)
- [API reference](#api-reference)
- [AI pipeline](#ai-pipeline)
- [News sources](#news-sources)
- [Deployment](#deployment)
- [Tech stack](#tech-stack)

---

## Features

| Area | What it does |
|---|---|
| **News feed** | 20+ sources, auto-refreshed every 15 min, sortable by date / impact / source |
| **AI/ML filter** | Keyword whitelist (50 terms) strips off-topic content from mixed sources |
| **Ad detection** | Pattern matching drops promotional posts before they reach the DB |
| **Deduplication** | Jaccard similarity (configurable threshold, default 0.85) marks near-duplicate stories |
| **Image enrichment** | Fetches `og:image` / `twitter:image` for articles missing thumbnails |
| **Title polishing** | Regex stage strips date/category prefixes; Claude Haiku rewrites messy academic titles |
| **AI summaries** | Claude Opus generates 2–3 sentence summaries per article |
| **Impact scoring** | Claude Haiku rates each story 0–10 for importance |
| **Favorites** | Star any article; persisted in Postgres with full history |
| **Broadcast** | Real SMTP email; simulated LinkedIn post and WhatsApp message with AI-generated copy |
| **Search & filters** | Keyword search, date range, source filter, include/exclude duplicates |
| **Sources admin** | Add / toggle / delete sources from the UI without restarting |
| **Broadcast history** | Full log of every send with platform, status, and generated content |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                       External Sources (20+)                         │
│  RSS feeds: OpenAI · Google AI · HuggingFace · TechCrunch · arXiv   │
│  Scrapers:  Anthropic · DeepMind · Meta AI                           │
│  Community: Reddit r/ML · r/LocalLLaMA · Hacker News                 │
└─────────────────────────────┬────────────────────────────────────────┘
                              │  RSS / HTTP
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Fetcher Worker  (APScheduler · 15 min)            │
│  1. Fetch sources (feedparser / HTML scraper)                        │
│  2. AI/ML keyword filter + ad detection                              │
│  3. Stage-1 title clean (regex strips date/category prefixes)        │
│  4. Save to DB (SHA-256 hash dedup on insert)                        │
│  5. Jaccard dedup pass                                               │
│  6. Image enrichment (og:image fetch)                                │
│  7. Title enrichment (Claude Haiku for messy titles)                 │
└─────────────────────────────┬────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        PostgreSQL Database                           │
│   sources · news_items · favorites · broadcast_logs · users          │
└───────────┬──────────────────────────────────────────────────────────┘
            │
            ├─────────────────────────────────────────────┐
            ▼                                             ▼
┌─────────────────────────┐               ┌──────────────────────────┐
│   FastAPI Backend        │               │   Claude AI Services     │
│   /api/news/*            │◀─────────────▶│   Summarization (Opus)   │
│   /api/favorites/*       │               │   Impact score (Haiku)   │
│   /api/broadcast/*       │               │   LinkedIn post (Opus)   │
│   /api/sources/*         │               │   Newsletter (Opus)      │
└──────────┬───────────────┘               └──────────────────────────┘
           │  REST JSON
           ▼
┌──────────────────────────────────────────────────────────────────────┐
│             React + Vite + Tailwind  (nginx · :3000)                 │
│   Feed  ·  Favorites  ·  Broadcast  ·  Sources admin                │
└──────────────────────────────┬───────────────────────────────────────┘
                               │  User broadcasts
                               ▼
               ┌───────────────────────────────┐
               │      Broadcast Services        │
               │  Email       (real SMTP)       │
               │  LinkedIn    (AI copy, sim.)   │
               │  WhatsApp    (AI copy, sim.)   │
               │  Newsletter  (HTML generated)  │
               └───────────────────────────────┘
```

---

## Database schema

```sql
sources (
  id, name, url,
  type            -- rss | scraper | api | youtube | reddit
  active, fetch_interval_minutes, last_fetched_at, created_at
)

news_items (
  id, source_id,
  title,          -- Text; polished by title_service
  summary,        -- raw extracted text
  ai_summary,     -- Claude-generated 2-3 sentence summary
  url, author, image_url, published_at, fetched_at,
  tags[],
  is_duplicate, duplicate_of_id,
  content_hash,   -- SHA-256(title+url) for fast dedup
  similarity_score,
  impact_score    -- 0-10, Claude Haiku
)

favorites      (id, user_id, news_item_id, created_at)

broadcast_logs (
  id, favorite_id,
  platform        -- email | linkedin | whatsapp | blog | newsletter
  status          -- pending | success | failed | simulated
  payload, error_message, timestamp
)

users          (id, name, email, role, created_at)
```

---

## Quick start

**Prerequisites:** Docker · Docker Compose · Anthropic API key

```bash
# 1. Clone and configure
git clone <repo-url>
cd ai-news-dashboard
cp .env.example .env
# open .env — set ANTHROPIC_API_KEY at minimum

# 2. Launch
docker compose up --build
```

Wait ~30 s for Postgres to initialise and the first fetch to complete.

| Service | URL |
|---|---|
| Dashboard | http://localhost:3000 |
| API (Swagger) | http://localhost:8000/api/docs |
| Postgres | localhost:5432 |

```bash
# Smoke tests
curl http://localhost:8000/api/health
curl -X POST http://localhost:8000/api/news/refresh
curl "http://localhost:8000/api/news/feed?page=1&page_size=20"
```

---

## Local development

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# ensure DATABASE_URL in .env points to a running Postgres
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev     # → http://localhost:5173
```

> When running locally without Docker, change the proxy target in `vite.config.js` from `http://backend:8000` to `http://localhost:8000`.

---

## Configuration reference

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@db:5432/ainews` | Postgres connection |
| `ANTHROPIC_API_KEY` | — | **Required** for all AI features |
| `FETCH_INTERVAL_MINUTES` | `15` | Background fetch cadence |
| `DEDUP_SIMILARITY_THRESHOLD` | `0.85` | Jaccard threshold (0–1; higher = stricter) |
| `MAX_NEWS_AGE_DAYS` | `7` | Feed hides items older than this |
| `SMTP_HOST / PORT / USER / PASSWORD` | — | Real email (leave blank → simulation) |
| `LINKEDIN_ACCESS_TOKEN` | — | LinkedIn API (blank → simulation) |
| `WHATSAPP_API_KEY / PHONE_ID` | — | WhatsApp Business API (blank → simulation) |

---

## API reference

### News
| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/news/feed` | `page`, `page_size`, `sort_by`, `search`, `source_id`, `days_back` |
| `GET` | `/api/news/{id}` | Single item |
| `POST` | `/api/news/refresh` | Triggers background fetch |
| `GET` | `/api/news/stats/summary` | Dedup stats, source counts |

### Favorites
| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/favorites/` | All favorites with news data |
| `POST` | `/api/favorites/{id}` | Star an item |
| `DELETE` | `/api/favorites/{id}` | Unstar |

### Broadcast
| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/broadcast/` | `{ favorite_ids, platform, recipient_email? }` |
| `GET` | `/api/broadcast/logs` | Broadcast history |

### Sources
| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/sources/` | List |
| `POST` | `/api/sources/` | Add |
| `PATCH` | `/api/sources/{id}/toggle` | Enable / disable |
| `DELETE` | `/api/sources/{id}` | Remove |
| `POST` | `/api/sources/seed` | Re-seed defaults (upsert) |

Full docs: **http://localhost:8000/api/docs**

---

## AI pipeline

All Claude calls are non-blocking — ingestion never waits on the API.

| Feature | Model | When |
|---|---|---|
| Title clean (regex) | — | At parse time, every item |
| Title polish | `claude-haiku-4-5` | Background, items matching messy-title heuristic |
| Image enrichment | — | Background, items with no `image_url` |
| Article summary | `claude-opus-4-5` | On-demand when feed is viewed |
| Impact score | `claude-haiku-4-5` | Background, after save |
| LinkedIn post | `claude-opus-4-5` | On broadcast action |
| Newsletter HTML | `claude-opus-4-5` | On broadcast action |
| Email body | rule-based | On broadcast action (zero LLM cost) |

---

## News sources

### AI-lab blogs (no keyword filter)
OpenAI · Google AI · Anthropic · DeepMind · Meta AI · Hugging Face · Microsoft AI · The Batch (deeplearning.ai)

### Tech media (AI keyword filter applied)
TechCrunch AI · VentureBeat AI · The Verge AI · Wired AI · MIT Technology Review

### Research
arXiv cs.AI · arXiv cs.LG · arXiv cs.CL · PapersWithCode

### Community
Hacker News (≥5 pts, LLM keyword) · Reddit r/MachineLearning · Reddit r/LocalLLaMA

---

## Deployment

### Docker Compose
```bash
docker compose up --build -d
```

### Render.com
1. Create a PostgreSQL instance → set `DATABASE_URL`
2. Web Service from `./backend/Dockerfile`
3. Static Site from `./frontend` (`npm run build`, publish `dist/`)

### Fly.io
```bash
fly postgres create --name ainews-db
fly launch --dockerfile backend/Dockerfile  --name ainews-backend
fly launch --dockerfile frontend/Dockerfile --name ainews-frontend
fly secrets set ANTHROPIC_API_KEY=sk-ant-...
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18 · Vite · Tailwind CSS · react-router-dom · lucide-react |
| Backend | FastAPI · SQLAlchemy 2 · APScheduler · Pydantic v2 |
| Database | PostgreSQL 16 |
| Ingestion | feedparser · httpx · BeautifulSoup4 |
| AI | Anthropic Claude (opus-4-5, haiku-4-5) |
| Serving | nginx · uvicorn |
| Containers | Docker · Docker Compose |

---

## Project structure

```
ai-news-dashboard/
├── docker-compose.yml
├── .env.example
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py               # FastAPI app, lifespan, CORS
│       ├── config.py             # Settings via pydantic-settings
│       ├── database.py           # Engine + auto-migration on startup
│       ├── models/               # source, news_item, favorite, broadcast_log, user
│       ├── schemas/              # Pydantic request/response models
│       ├── routers/              # news, favorites, broadcast, sources
│       ├── services/
│       │   ├── ingestion.py      # RSS + scraper, relevance + ad filter
│       │   ├── dedup.py          # Jaccard similarity dedup
│       │   ├── image_service.py  # og:image enrichment
│       │   ├── title_service.py  # Regex + Claude Haiku title polish
│       │   ├── ai_service.py     # Summarize, score, caption, newsletter
│       │   └── broadcast_service.py
│       └── workers/
│           └── fetcher.py        # 7-step APScheduler pipeline
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    └── src/
        ├── api/                  # axios client for all endpoints
        ├── hooks/                # useFeed, useFavorites
        ├── components/           # Layout, NewsCard, BroadcastModal
        └── pages/                # Feed, Favorites, Broadcast, Sources
```
