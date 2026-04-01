# Organizing Life Services — AI Operations System

Self-hosted business operations system for Organizing Life Services.
Built on FastAPI + Postgres + n8n, with Google Sheets as the operator dashboard.

## Quick Start (Laptop Dev)

```bash
cp .env.example .env
# Fill in .env values
docker compose up -d --build
```

- **API**: http://localhost:8000
- **API docs**: http://localhost:8000/docs
- **n8n**: http://localhost:5678

## Architecture

See `docs/architecture.md` for the full system overview.

## Current Phase

**Phase 1 — SEO Integrations Foundation (Laptop Only)**
- Google Search Console
- Google Analytics 4
- Google Business Profile
- Google Ads
- Google Sheets operator dashboard
