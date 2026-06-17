# Onboarding — Organizing Life Services AI

Welcome. This repo runs SEO automation, content generation, and analytics for **organizinglifeservices.com**. Read this top-to-bottom before touching code.

## What this system does

A FastAPI backend + small dashboard that:
- Pulls data from Google Search Console, GA4, Google Ads, Google Business Profile, and Shopify
- Runs SEO audits, content generation, and lifecycle workflows against organizinglifeservices.com
- Pushes meta tags, schema markup, blog posts, and internal links to the Shopify storefront
- Persists time-series data in Postgres for trend analysis

Architecture details: [docs/architecture.md](architecture.md).

## Repo layout

```
app/                FastAPI backend (routes/, services/, agents/, skills/)
dashboard/          React/Vite frontend
data/               One-shot scripts for SEO operations + audit outputs
docs/               Architecture, runbooks, SEO audits, design docs
infra/              Postgres + backup configuration
scripts/            Setup helpers (OAuth token generators, etc.)
workflows/n8n/      Versioned n8n workflows
credentials/        Service-account JSON (gitignored)
```

## First-time setup

1. **Clone:**
   ```bash
   git clone <repo-url>
   cd organizing-life-services-ai
   ```

2. **Copy env template:**
   ```bash
   cp .env.example .env
   ```
   Then ask the project owner for the actual values. Required at minimum:
   - `SHOPIFY_*` (storefront API access)
   - `GA4_PROPERTY_ID`, `SEARCH_CONSOLE_SITE_URL`
   - Postgres connection strings

3. **Get credentials:**
   - Place `google-service-account.json` in `credentials/` (ask the owner)
   - The service-account email is `ols-operations@ols-marketing-agent.iam.gserviceaccount.com` — it already has GA4 + GSC + Sheets access (see [`/memories/repo/google_apis_status.md`](../memories/repo/google_apis_status.md))

4. **Start the stack:**
   ```bash
   ./rebuild.command
   ```
   This runs `docker-compose up -d --force-recreate` and waits for health checks. The API will be at http://localhost:8000 and the dashboard at http://localhost:5173.
   For Mac mini server deployment, use [`docs/deployment.md`](deployment.md)
   and [`docs/mac-mini-implementation-guide.md`](mac-mini-implementation-guide.md)
   instead of the laptop rebuild helper.

5. **Set up the audit venv** (for one-shot SEO scripts that don't run in the container):
   ```bash
   python3 -m venv .venv-audit
   source .venv-audit/bin/activate
   pip install -r requirements.txt
   ```

## Key gotchas (from `/memories/repo/google_apis_status.md`)

- `docker-compose restart api` does **not** reload `.env` — use `docker-compose up -d --force-recreate api` instead.
- If you change env vars before Postgres first-init, wipe the volume: `docker volume rm organizing-life-services-ai_postgres_data`.
- Google Ads dev token requires an MCC account; standalone accounts cannot access API Center.
- GBP disallows service accounts for some operations but the Performance API works with SA auth.

## Where to look for things

| You want to... | Look at... |
|---|---|
| Understand the architecture | [docs/architecture.md](architecture.md) |
| Read past SEO audits | [docs/seo-audits/](seo-audits/) |
| See what's changed on the site | [docs/seo-audits/CHANGELOG.md](seo-audits/CHANGELOG.md) |
| Run an SEO audit / push meta / deploy schema | [docs/runbooks/](runbooks/) |
| Add a new API integration | [docs/google_ads_api_design_doc.md](google_ads_api_design_doc.md) is the template |
| Understand which Google APIs are live | [`/memories/repo/google_apis_status.md`](../memories/repo/google_apis_status.md) |
| Add agents / skills | [docs/agents.md](agents.md), `app/skills/` |
| Understand private AI conversation backups | [conversations/README.md](../conversations/README.md) |

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for commit conventions and PR process.

## Who to ask

- **Project owner:** Robert Porter
- **Live site:** https://organizinglifeservices.com
- **GCP project:** `ols-marketing-agent` (project number `330992031618`)
- **GA4 property:** `396184354`
- **Shopify spreadsheet:** `1nFx6g0g1ICsl9qaKM1OsReeMOP25jCx5aZyQOjbpk1A`
