# AGENTS.md

Rules for **Cursor Cloud Agents and Grok Bots that change this codebase**.
Organizing Life Services (OLS) is a gated SEO + business-ops stack (FastAPI,
Postgres, React dashboard, Google, Shopify). It is deliberately **not** a
free-running multi-agent system, and it must stay that way until the SEO/data
workflows are boring, measured, and safe.

If you are operating OLS *through* Grok Bot seats (running endpoints, audits,
Seedance, ops), read [`docs/grok-bot.md`](docs/grok-bot.md). If you are
*editing this repository*, this file is the contract.

## Where to look before you change anything

- [`docs/agents.md`](docs/agents.md) — the policy: model roles, the never-list,
  and the service-only Shopify rule. This is authoritative.
- [`app/safety.py`](app/safety.py) — the FastAPI-facing high-stakes gate.
- [`app/services/llm_router.py`](app/services/llm_router.py) — model/provider
  selection, audit logging, and `assert_high_stakes_gate`.
- [`app/services/task_apply_service.py`](app/services/task_apply_service.py) —
  the allowlisted Apply dispatcher (`ALLOWLIST`, `NEVER_APPLY_KINDS`).
- [`docs/grok-bot.md`](docs/grok-bot.md) — Grok Bot operating contract / seats.
- [`docs/architecture.md`](docs/architecture.md) — system overview.

## Hard rules (do not violate)

1. **Honor the gate.** High-stakes writes require `human_confirmed=true` **and**
   `judge_verdict=PASS`. Do not loosen, bypass, auto-set, or route around either
   flag. The gate lives in `assert_high_stakes_gate` and `app/safety.py`; keep
   it fail-closed.
2. **Do not invent Apply verbs.** Writes are limited to the registered
   `action_kind`s in `task_apply_service.ALLOWLIST`. Adding a new kind is a
   deliberate, reviewed change — never something inferred from a task row or an
   LLM suggestion.
3. **Never-apply list is permanent:** `ads.budget_bid_keyword`, `gbp.write`,
   `gbp.*`, `gtm.create_arbitrary`. Do not register, implement, or "temporarily"
   enable any of them.
4. **Do not build an agent framework.** No CrewAI, no free-running multi-agent
   loops, no n8n replacement / workflow builder. Keep `app/agents/` and
   `app/skills/*` as the empty placeholders they are — do not fill them with
   runtime agent loops or skill frameworks.
5. **Keep the access boundary.** Postgres/API/dashboard/n8n/Ollama stay
   localhost / Tailscale only. Never commit `.env` or
   `credentials/`. Never expose services to the LAN or public internet in a
   change.
6. **Service-only Shopify rule.** No product SEO writes (`/products/*`), no
   optimizing utility/fee collections, no indexing `/collections/all` or
   `/collections/fees-products`. See `docs/agents.md`.
7. **n8n/cron may only create `DashboardTask` rows.** Only a human dashboard
   click may call `POST /api/dashboard/tasks/{id}/apply`. Do not wire automation
   to Apply.

## How to work

- Work on a branch and land changes via **PR review**. No direct-to-production
  edits.
- **Keep changes small and reviewable.** Prefer the smallest change that
  satisfies the request; document trade-offs in the PR.
- **Run the tests that cover what you touched**, especially the router/apply
  path:

  ```bash
  python3 -m pytest tests/test_llm_router.py tests/test_task_apply.py \
      tests/test_high_stakes_routes.py tests/test_gtm_write_control.py
  ```

- If a requested change fights existing settings, tests, or policy, **stop and
  document why** in the PR instead of forcing it through.
- **Stay quiet if nothing changed.** Do not open PRs, create tasks, or ping when
  there is no material diff.
- Do **not** merge unrelated `automation/*` snapshot/audit PRs, and do not
  rewrite or dump the contents of `conversations/`.

## Model roles (summary — full policy in `docs/agents.md`)

| Role | Provider | Use for |
|---|---|---|
| Clerk | Local Gemma via Ollama | low-risk classification, summaries, drafts |
| Executive | Anthropic (Claude) | content drafts, synthesis, analysis |
| Judiciary | xAI/Grok when `XAI_API_KEY` is set, else Anthropic | independent high-stakes review |

The judiciary is intentionally an **independent** reviewer: when `XAI_API_KEY`
is present it routes to xAI/Grok so the judge is a different provider/family
than the Anthropic executive (see `docs/mac-mini-agent-server-plan.md`). A judge
`PASS` is necessary but never sufficient — a human confirmation is still
required for every high-stakes write.
