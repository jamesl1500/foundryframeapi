# Site Audit Platform API

FastAPI backend for [audit.foundryframe.com](https://audit.foundryframe.com). Leads submit
a website URL, the API audits it (SEO/performance/accessibility/security heuristics),
sends the findings to Claude for a plain-English summary + package recommendation, and
persists the lead + audit in Postgres.

## Stack

- FastAPI + SQLAlchemy (async, `asyncpg`) + Alembic
- httpx + BeautifulSoup for the site auditor
- Google Lighthouse (via the PageSpeed Insights API) for performance/accessibility/SEO/best-practices scores + Core Web Vitals
- Anthropic Claude for the AI recommendation layer
- Deployed to AWS

## Local setup

```bash
cp .env.example .env   # fill in ANTHROPIC_API_KEY, JWT_SECRET, etc.
docker compose up -d db  # from repo root, starts Postgres
uv sync
uv run alembic upgrade head
uv run api               # or: uv run uvicorn api.main:app --reload
```

PageSpeed Insights works without an API key at a low rate limit; set `PAGESPEED_API_KEY`
in `.env` for production use.

API docs available at `http://localhost:8000/docs`.

## Project layout

```
src/api/
  ai/              Claude integration (services/claude_service.py)
  api/v1/routes/   HTTP routes (health, audits, leads)
  core/            settings, DB engine/session
  models/          SQLAlchemy models (Lead, Audit)
  schemas/         Pydantic request/response models
  services/        business logic (site auditor, lead upsert)
migrations/        Alembic migrations
```

## Key endpoints

- `POST /api/v1/audits` — submit `{ url, email, name?, company?, phone? }`, runs the audit
  synchronously, returns the persisted `Audit` (score, findings, AI summary + recommendation).
- `GET /api/v1/audits/{id}` — fetch a previously run audit.
- `GET /api/v1/leads` — list captured leads.

## Migrations

```bash
uv run alembic revision --autogenerate -m "message"
uv run alembic upgrade head
```

## Tests / lint

```bash
uv run pytest
uv run ruff check .
uv run mypy .
```

## Deployment

See [docs/DEPLOYMENT.md](../../docs/DEPLOYMENT.md) for the AWS (ECR + ECS Fargate + RDS) setup.
