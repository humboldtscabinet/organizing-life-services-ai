# Organizing Life Services — AI Operations System

Self-hosted SEO and business-operations system for Organizing Life Services.
Built on FastAPI, Postgres, a React dashboard, n8n, Google integrations,
Shopify workflows, and a conservative local/cloud LLM router.

## Quick Start

```bash
cp .env.example .env
# Fill in .env values
docker compose up -d --build
```

- **API**: http://localhost:8000
- **API docs**: http://localhost:8000/docs
- **Dashboard**: http://localhost:3000
- **n8n**: http://localhost:5678

For the always-on Mac mini server, use:

```bash
infra/server/deploy_server.sh
```

See [docs/deployment.md](docs/deployment.md) for server deployment, backups,
local Ollama/Gemma verification, and post-reboot checks.

## Architecture

See `docs/architecture.md` for the full system overview.

## Current Operating Focus

1. Pull and store SEO/business data from GSC, GA4, Shopify, Google Ads, and GBP
   where access is available.
2. Generate evidence-based SEO opportunities from real performance data.
3. Draft changes with strict human and judge gates before public writes.
4. Measure impact through follow-up audits instead of trusting one-off changes.

The broader multi-agent layer is intentionally deferred until the core SEO
workflow is stable and measurable.
