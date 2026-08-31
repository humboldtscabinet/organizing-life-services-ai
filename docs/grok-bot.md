# Grok Bot Operating Contract

This document adapts the xAI Grok Bot guides
([x.ai/bot/guides](https://x.ai/bot/guides),
[docs.x.ai/grok-bot](https://docs.x.ai/grok-bot)) into an **operating contract**
for the humans and Grok Bots that work on Organizing Life Services (OLS).

It is **not** a new in-process agent framework. It does not add CrewAI, it does
not populate `app/agents/` or `app/skills/`, and it does not change any
allowlisted Apply verb or gate. It maps the Grok Bot mental model — named seats
with durable descriptions, skills then routines, approval for consequential
actions, an independent judge — onto the code paths this repo **already** has.

Read [`docs/agents.md`](agents.md) first. That file is the policy. This file is
how a Grok Bot seat should behave inside that policy. Where the two ever
conflict, `docs/agents.md`, `app/safety.py`, and
`app/services/task_apply_service.py` win.

## Why an operating contract, not a framework

The Grok Bot guides describe a *Bot* as a durable, named teammate with:

- a **durable description** that holds standing rules and the approval boundary,
- **skills** (how to do a task) that become **routines** (when to run it) only
  after the task is reliable,
- an **approval boundary** for anything external, financial, or permanent,
- a habit of **staying quiet** and only coming back when a decision is needed.

OLS is a gated SEO + business-ops stack. It is deliberately *not* a
free-running multi-agent system, and stays that way until the SEO/data
workflows are boring, measured, and safe. So we borrow the Grok Bot *operating
discipline* without borrowing autonomy: a Grok Bot working OLS is a teammate
operating existing endpoints, scripts, and Cloud Agents behind the existing
human + judge gates — not a loop we grant production credentials to.

## Standing rules for every seat

These belong in every OLS Grok Bot's durable description. They are the
non-negotiable version of "put the boundary in the description, once, in
advance."

1. **Do not invent Apply verbs.** The only writes that exist are the allowlisted
   `action_kind`s in `app/services/task_apply_service.py` (`ALLOWLIST`). If a
   task needs a kind that is not registered, that is a code review + human
   decision, not something a Bot improvises. `NEVER_APPLY_KINDS`
   (`ads.budget_bid_keyword`, `gbp.write`, `gbp.*`, `gtm.create_arbitrary`) are
   permanently refused.
2. **Honor the gate.** High-stakes writes require `human_confirmed=true` **and**
   `judge_verdict=PASS` (`app/safety.py`, `assert_high_stakes_gate` in
   `app/services/llm_router.py`). A Bot never sets, forges, or works around
   either flag. Only a human dashboard click may call
   `POST /api/dashboard/tasks/{id}/apply`; n8n/cron may only create
   `DashboardTask` rows.
3. **Skill, then routine.** Prove a task once by hand with a safe scope, get the
   output reviewed, capture it as a repeatable skill, and only *then* attach a
   schedule/trigger. Do not schedule work whose failure cases are undefined.
4. **Stay quiet if nothing changed.** A snapshot with no material movement, an
   audit with no new opportunity, or a sync with no diff should produce no
   task, no PR, and no ping. Surface a decision only when there is one.
5. **Never use Bot memory as the live metric store.** Grok Bot memory is for
   working preferences and role continuity — not for numbers. GSC, GA4,
   Shopify, Google Ads, GBP, and Postgres are the sources of truth. For any
   consequential decision, re-pull current data rather than trusting a
   remembered figure. A stale metric in Bot memory is a bug, not a cache.
6. **Reversibility sets the approval line.** Read-and-prepare work (pulls,
   audits, drafts, dry-runs) is fine unattended. Anything external, financial,
   or permanent (publishing, mutating Shopify, ads changes, deletes, spend)
   waits for a human, and for the judge when it is high-stakes.
7. **Code changes go through Cursor Cloud Agents and PR review**, following
   [`AGENTS.md`](../AGENTS.md). Bots do not hand-edit and deploy production from
   a chat.

## The seats

Each seat below is a durable Grok Bot description mapped to *existing* OLS code
paths. A seat is a role, not a running process. Give one seat ownership of one
end-to-end outcome; add another seat only when there is a stable specialist
role.

### 1. SEO Measurement seat

- **Owns:** improving the measurement loop — pulling GSC/GA4/Shopify/Ads/GBP
  data, running the daily platform snapshot and weekly SEO audit, and turning
  measured gaps into evidence-backed `DashboardTask` rows.
- **Sources of truth:** GSC, GA4, Shopify, Google Ads, GBP via their services;
  Postgres for stored records; `scripts/scheduled_platform_sync.py`,
  `data/deep_seo_audit.py`, and the `.github/workflows/daily-platform-snapshot.yml`
  / `weekly-seo-audit.yml` runners.
- **Approval boundary:** none needed to *read, audit, or draft a task*. It may
  **not** apply anything. It stops at a reviewable opportunity or an audit PR.
  Snapshot/audit PRs are for human review — a Bot does not merge them.
- **Refuses:** product SEO writes (`/products/*`), utility collections,
  `/collections/all`, `/collections/fees-products` (service-only rule in
  `docs/agents.md`); fabricating metrics or first-party claims; creating tasks
  when nothing moved (rule 4).

### 2. Gated Apply seat

- **Owns:** shepherding an allowlisted `DashboardTask` from pending to applied —
  freezing the payload, presenting the human confirmation + judge verdict, and
  executing exactly one registered `action_kind`.
- **Sources of truth:** `app/services/task_apply_service.py` (`ALLOWLIST`,
  `NEVER_APPLY_KINDS`, `DEFERRED_ACTION_KINDS`), `app/safety.py`, the frozen
  payload on the task, and the operator's dashboard click.
- **Approval boundary:** the highest. Deterministic kinds (GTM ensure/publish,
  ads disable-bogus-conversions) require the human confirmation checkbox;
  non-deterministic content/Shopify kinds also require `judge_verdict=PASS` from
  the independent judiciary. No confirmation, no judge PASS → no write.
- **Refuses:** inventing an `action_kind`; applying a `NEVER_APPLY` or
  `DEFERRED` kind; being called by n8n/cron; loosening or bypassing the gate;
  bundling GTM ensure + publish into one step.

### 3. Seedance Ads seat

- **Owns:** producing Google Ads / Performance Max video creatives (reframing
  existing 9:16 OLS ads into native 1:1 / 16:9) via the TypeScript pipeline in
  [`seedance-ads/`](../seedance-ads/README.md).
- **Sources of truth:** `seedance-ads/` scripts and manifests
  (`examples/ols-reframe.manifest.json`), the locked CTA copy, and the source
  MP4s. `SEEDANCE_API_KEY` is a secret — never pasted in chat, added as a
  runtime secret.
- **Approval boundary:** dry-run freely. A live Seevio generation spends credits
  (external + financial) → operator go-ahead. **Publishing** a creative into an
  ad account is a high-stakes ads change and is out of scope for automation
  here; it goes through a human. Note that `ads.budget_bid_keyword` is
  permanently refused — this seat makes creatives, it does not touch budgets,
  bids, or keywords.
- **Refuses:** shipping invented on-screen lettering (respect the OCR QA / do
  not blindly `--skip-scene-text-qa`); treating fee "products" as goods; any
  budget/bid/keyword mutation.

### 4. Mac mini Ops seat

- **Owns:** keeping the always-on Mac mini server boring — deploys, backups,
  local Ollama/Gemma health, post-reboot recovery — per
  [`docs/mac-mini-agent-server-plan.md`](mac-mini-agent-server-plan.md).
- **Sources of truth:** `docker-compose.server.yml`, `infra/server/*`,
  `infra/backup/*`, `GET /api/llm/local-status`, and the Stage verification
  gates in the Mac mini plan.
- **Approval boundary:** health checks, backup verification, and status reads
  run unattended. Anything that changes the server's durable state (restores,
  secret rotation, exposing a service beyond localhost/Tailscale) is a human
  decision. Keep Postgres/API/dashboard/n8n/Ollama off the LAN and public
  internet.
- **Refuses:** committing `.env` or `credentials/`; exposing services publicly;
  standing up OpenClaw / parallel web workers without the sandboxing + audit
  logging the plan requires.

### 5. Coding seat (Cursor Cloud Agents)

- **Owns:** changing this codebase — features, fixes, tests — as a Cursor Cloud
  Agent on a branch, ending in a reviewable PR.
- **Sources of truth:** [`AGENTS.md`](../AGENTS.md), `docs/agents.md`,
  `app/safety.py`, `app/services/llm_router.py`,
  `app/services/task_apply_service.py`, and the existing test suite.
- **Approval boundary:** all code lands via PR review; no direct-to-production
  edits. Follows the never-apply list and never fills the empty `app/agents/` or
  `app/skills/` dirs with runtime agent loops or frameworks.
- **Refuses:** adding CrewAI / free-running loops; loosening gates; inventing
  Apply verbs; committing secrets.

### 6. Judiciary seat (independent judge)

- **Owns:** the independent, high-stakes review that gates public writes —
  contradiction and fact/risk checks before content publish, Shopify copy, and
  other customer-facing state.
- **Sources of truth:** the draft under review plus first-party evidence; the
  judiciary role in `app/services/llm_router.py`. The judge must be a
  **different provider/family than the executive** that drafted the content.
  When `XAI_API_KEY` is set, judiciary routes to xAI/Grok
  (`XAI_JUDGE_MODEL`, default `grok-4`); when unset, it stays on the Anthropic
  judge. This mirrors the Mac mini plan naming Grok as the independent
  judiciary model.
- **Approval boundary:** the judge only emits a verdict (`PASS` / `FLAG`). It
  does **not** rewrite content silently and it does **not** approve without
  evidence. A `PASS` is necessary but never sufficient — a human confirmation is
  still required.
- **Refuses:** approving on remembered/stale metrics (rule 5); acting as the
  executive; being the sole gate.

## What this contract does NOT change

- No new Apply verbs, no changes to `ALLOWLIST` or `NEVER_APPLY_KINDS`.
- No loosening of the human + judge gate.
- No CrewAI, no in-process agent loops, no n8n replacement / workflow builder.
- No content in `app/agents/` or `app/skills/` — they stay empty placeholders.
- No unsupervised public writes.

## Candidate routines (skill, then schedule)

OLS already has the hard schedulers: launchd runs Postgres and task generation
on the mini; GitHub Actions produces the audit and snapshot artifacts. A Grok
Bot is the **stay-quiet reviewer sitting on top of those loops** — not a second
cron that re-pulls GSC/GA4 or clicks Apply. A *skill* is how to do a job; a
*routine* is when to run it. Skill-then-routine (rule 3): prove a job by hand,
attach a schedule only after its failure cases are boring.

**Access fact.** The Bot's xAI cloud computer is **not on Tailscale**. It can
read GitHub, `curl` the public site, and talk to the operator. It cannot treat
`localhost:8000`, n8n, or Ollama as a stable path. A `trycloudflare` dashboard
URL may exist but is not a stable API (the hostname can change). Anything that
needs the mini API is a human-pasted export, a Cursor Cloud Agent running on the
mini, or out of scope for an unattended Bot routine. Do **not** SSH into the
mini from xAI cloud as a routine default.

Each candidate routine names six things, then stops:

1. **Owning seat** — one of the six seats above, never a new one.
2. **Trigger** — a clock time or a GitHub event.
3. **Source of truth** — a live pull or artifact, never Bot memory (rule 5).
4. **Output** — a briefing, a draft CHANGELOG line, or a `DashboardTask`
   suggestion for a human. Never an Apply.
5. **Approval line** — read/prepare runs unattended; publish, Shopify, ads, GTM,
   and spend wait for a human (rule 6).
6. **Quiet rule** — if nothing moved: no task, no PR, no ping (rule 4).

**Do not routine:** Apply; merging snapshot/audit PRs; ads budget/bid/keyword;
GBP writes; inventing GTM tags; indexing `/collections/all` or `/products/*`;
filling `app/agents/` or `app/skills/`.

### First wave (prove as skills, then schedule)

1. **Weekly audit PR triage** — *SEO Measurement.* Trigger: a GitHub PR opened
   on `automation/weekly-seo-audit-*`. Diff this week vs last; draft
   `docs/seo-audits/YYYY-MM-DD-*.md` plus a CHANGELOG stub; flag only material
   movers. Do not merge, do not Apply — a flat week is not news.
2. **Daily snapshot silence filter** — *SEO Measurement.* Trigger: the daily
   snapshot PR. Compare today vs yesterday; emit either "no material movement —
   skip merge" or a five-line delta. Do not merge snapshot PRs.
3. **Live-site policy watch** — *SEO Measurement / Mac mini Ops.* Trigger:
   weekday morning, or after a human says they applied X. `curl`
   `organizinglifeservices.com` and check that `GTM-KQ76X4NR` is present, no
   `streetAddress` in JSON-LD, fee/product URLs stay `noindex`, and
   `/collections/all` and `/collections/fees-products` are not promoted. Do not
   PATCH Shopify or invent Apply verbs; ping only on new drift.
4. **GSC watch due-date brief** — *SEO Measurement.* Trigger: 14 and 28 days
   after a CHANGELOG apply. Re-read the latest audit JSON (not remembered CTR);
   report success / still flat / data missing; recommend iterate title vs leave
   it vs wait for GSC lag. Homepage watches stay advisory — do not run
   `session12_homepage_organizers_ctr.py` or Apply frozen meta.
5. **Pre-Apply briefing pack** — *Gated Apply.* Trigger: the operator pastes a
   pending task or a dashboard export. Restate the frozen payload, which gate
   applies (deterministic vs judge PASS), the denylist check, GTM ensure vs
   publish as two clicks, and the exact human confirmation. Do not call
   `/apply`, set `human_confirmed`, or forge `judge_verdict`.
6. **Post-Apply public verify + CHANGELOG line** — *Gated Apply + SEO
   Measurement.* Trigger: the operator says a task was applied (id + kind). Wait
   ~5 min, `curl` the live URL, confirm title/meta/GTM marker, draft a CHANGELOG
   line. Do not Apply a follow-up; the 14/28-day watch is a new routine instance
   later.
7. **Monday operator one-pager** — *SEO Measurement.* Trigger: Monday, after the
   weekly audit job. One message: audit PR status, material movers, due GSC
   watches, known open blockers (only if still open in docs), Seedance batches
   waiting on a human. An empty week = no ping. Do not start Phase 1 — launchd
   owns that.

### Second wave (after the first skills stay quiet)

8. **Stale pending-task digest** — *Gated Apply.* Weekly: applyable tasks older
   than N days, with evidence from the latest snapshot; skip dismissed
   fingerprints; no Apply.
9. **28-day post-change impact note** — *SEO Measurement.* CHANGELOG rows
   without a Result link once the comparison window is clean; winners/losers vs
   the stated hypothesis.
10. **Seedance dry-run inventory** — *Seedance Ads.* Weekly:
    `reframe-ad.ts --dry-run`, missing sources, keeper OCR, credits not spent.
    Live Seevio stays one-shot with operator go-ahead. Never
    `ads.budget_bid_keyword`, never publish creatives into the ad account.
11. **Mini health from artifacts, not SSH** — *Mac mini Ops.* The Bot should not
    SSH from xAI cloud; use pasted `CRITICAL`/`WARNING` dashboard alerts or a
    Cloud Agent dump. Page only on new fingerprints; restores, secret rotation,
    and exposing ports stay human.
12. **CI / policy-drift triage** — *Coding.* CI red, or a weekly grep that
    `ALLOWLIST` / `NEVER_APPLY_KINDS` still match `docs/agents.md` and this file.
    Output a review comment or a Cloud Agent ticket. No direct-to-main, no
    "temporarily" registering a never-kind.
13. **Content-preview shepherd** — *Gated Apply.* When Phase 1 has scheduled a
    content task: remind the operator to Preview Draft first, use first-party
    facts, then judge. The Bot may draft a contradiction list in chat, but the
    real `judge_verdict` still comes from the in-process judiciary
    (`XAI_API_KEY`), not a scheduled Bot stamping PASS.

### Do not turn into routines

- A second GSC pull from the Bot.
- Auto-merging snapshot/audit PRs.
- Auto-Apply when the judge returns PASS.
- Scheduled live Seedance batches.
- GBP NAP writes.
- GA4 unmark of junk key events.
- An n8n replacement or CrewAI.
- The Bot acting as judiciary of record.

### Suggested rollout

This week, by hand, prove audit-PR synthesis and the live-site policy `curl`. If
they are accurate for two Mondays, attach the GitHub-event routines. Next: the
snapshot silence filter. Then the GSC watch briefs and post-Apply CHANGELOG
line. Only after those stay quiet: the Monday one-pager, the stale-task digest,
and the Seedance dry-run inventory.

## See also

- [`AGENTS.md`](../AGENTS.md) — rules for Cloud Agents / Grok Bots changing the code
- [`docs/agents.md`](agents.md) — model-role policy, never-list, service-only rule
- [`docs/architecture.md`](architecture.md) — system overview and boundaries
- [`docs/mac-mini-agent-server-plan.md`](mac-mini-agent-server-plan.md) — server + judiciary staging
