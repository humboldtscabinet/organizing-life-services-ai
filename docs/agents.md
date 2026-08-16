# Agents And Model Roles

The repo is not a free-running multi-agent system yet. Keep it that way until
the SEO/data workflows are boring, measured, and safe.

Current agent behavior lives in:

- `app/services/llm_router.py` — model selection and audit logging
- `app/safety.py` — high-stakes write gates
- guarded FastAPI routes — human confirmation before public writes

## Role Policy

Use model roles by task risk, not by hype:

| Role | Default model/provider | Use for | Must not do |
|---|---|---|---|
| Clerk | Local Gemma via Ollama | low-risk classification, summaries, draft outlines, local context checks | publish, mutate Shopify, change ads/budgets, or decide final approval |
| Executive | Claude/ChatGPT-class cloud model | content drafts, strategic analysis, synthesis across SEO evidence | bypass human review or fabricate first-party claims |
| Judiciary | Independent cloud judge | high-stakes review, contradiction checks, publish safety | rewrite content silently or approve without evidence |

High-stakes writes require both:

```text
human_confirmed=true
judge_verdict=PASS
```

This applies before Shopify/content/lifecycle writes, bulk alt-text pushes, ads
budget changes, and any future operation that changes customer-facing state.

## Service-Only Shopify Rule

OLS sells services, not merchandise. Shopify products (credit-card fees,
processing fees, etc.) and utility collections are internal-only.

Agents **must not**:

- Call product SEO write endpoints or “optimize” `/products/*` for search
- Generate ads creatives, landing pages, or blogs that treat fee products as goods
- Create dashboard SEO tasks for `/products/*` or utility collections
- Suggest indexing `/collections/all` or `/collections/fees-products`

Agents **may** work on service pages, service-area pages, the homepage, and
blog articles. Product SEO writes are policy-blocked in the API even if a human
confirmation flag is present.

## SEO Operating Principle

Agents should improve the measurement loop, not replace it:

1. Pull GSC, GA4, Shopify, Ads, and GBP data where available.
2. Generate opportunities from real impressions, clicks, CTR, rank, revenue, or
   conversion evidence.
3. Draft changes with first-party local business facts.
4. Judge the draft independently.
5. Require human approval before public writes.
6. Measure impact after a clean comparison window.

## Never-list

Do **not** add:

- CrewAI or free-running multi-agent loops
- Ads budget / bid / keyword mutate agents (`ads.budget_bid_keyword`)
- GBP writes (`gbp.write`, `gbp.*`)
- Indexing API
- LLM-invented GTM tags (`gtm.create_arbitrary`)

Allowlisted Apply verbs live in `app/services/task_apply_service.py`. n8n and
cron may create `DashboardTask` rows. Only a human-confirmed dashboard click
may call `POST /api/dashboard/tasks/{id}/apply`.

## Deferred Work

CrewAI or a broader "agent government" can come later, but it should be added
only when it removes real operational burden. Do not build new autonomous agents
until the following are stable:

- GBP data access and local SEO metrics
- route failures returning real HTTP failures
- backup/offsite recovery
- one maintained path for recurring Shopify mutations
- documented weekly SEO audit ownership
