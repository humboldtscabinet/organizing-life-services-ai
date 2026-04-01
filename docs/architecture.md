# Architecture Overview

See MASTER_PLAN_V2.1 for full details.

## Layers
1. **No reverse proxy yet** — laptop-only development
2. **FastAPI** — webhooks, validation, business logic, DB persistence
3. **Postgres** — structured business data
4. **n8n** — business automations
5. **Skills / prompt files** — version-controlled SOPs
6. **Agent layer (CrewAI)** — future only
