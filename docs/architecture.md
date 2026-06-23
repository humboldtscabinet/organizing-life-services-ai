# Architecture Overview

Organizing Life Services AI is a localhost-first SEO operations system. The
Mac mini runs the production-style stack; the iMac/laptop clone is the
development workspace.

## Runtime Layers

1. **Access boundary** — API, dashboard, and n8n bind to localhost on the Mac
   mini. Use SSH forwarding or a deliberately chosen tunnel/VPN before exposing
   any UI beyond the machine.
2. **FastAPI** — authenticated routes, validation, Shopify/Google workflows,
   high-stakes gates, and database persistence.
3. **Postgres** — structured SEO, dashboard, lifecycle, and LLM audit data.
4. **React dashboard** — local operator console for metrics and task review.
5. **n8n** — optional automation runner for scheduled workflows.
6. **Ollama/Gemma** — local clerk model for low-risk local work.
7. **Cloud LLMs** — executive drafting and independent judiciary review for
   higher-risk content and decisions.

## Data Flow

1. Pull GSC, GA4, Shopify, Ads, and GBP data where credentials/access exist.
2. Store normalized records in Postgres.
3. Generate dashboard tasks and audit reports from measured gaps.
4. Human reviews recommended changes.
5. High-stakes routes require `human_confirmed=true` and
   `judge_verdict=PASS` before customer-facing writes.
6. Follow-up SEO audits measure impact after a clean comparison window.

## Current Boundaries

- Postgres is not published to the host network in server compose.
- Public/business writes are guarded by `app/safety.py`.
- Legacy direct-write scripts under `data/` are guarded by
  `data/_mutation_guard.py` and should be treated as historical/manual tools.
- The broad "agent government" layer is not production behavior yet; current
  agent-like behavior is the LLM router plus explicit route gates.

See also:

- [deployment.md](deployment.md)
- [agents.md](agents.md)
- [runbooks/data-mutation-scripts.md](runbooks/data-mutation-scripts.md)
