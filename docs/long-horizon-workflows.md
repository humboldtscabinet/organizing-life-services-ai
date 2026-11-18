# Long-horizon workflows

Most real work in this system is not a single edit — it is a multi-step workflow
that an agent (or an agent + operator) has to carry across several subsystems
without dropping a guardrail. This page describes two such workflows end to end
and says explicitly what **"done correctly"** means, so the finish line is a
checklist and not a feeling.

These two are the backbone of the whole stack: the **gated Apply flow** (how any
customer-facing change actually ships) and the **independent judiciary check**
(how a high-stakes change earns the right to ship).

---

## Workflow A — Gated Apply: from signal to a live change

A measured SEO signal becomes a live Shopify/content/GTM change only by walking
this path. No step may be skipped or merged into another.

1. **Measure.** Ingest real GSC/GA4/Shopify/Ads/GBP data (read-only). Nothing
   here writes anything customer-facing.
2. **Generate an opportunity.** A pure, side-effect-free predicate turns the
   data into a candidate (e.g. a page-1 low-CTR snippet rewrite). Junk filters
   (`app/services/task_enqueue_filters.py`) drop low-value rows *before* they are
   created.
3. **Create a `DashboardTask` row.** n8n/cron may do this. The row carries a
   frozen `action_payload` and an allowlisted `action_kind` — or none, in which
   case it is advisory only. Creating a row changes nothing live.
4. **Draft + judge.** For copy changes, the executive model drafts and the
   **independent judiciary** reviews (Workflow B). The verdict is recorded.
5. **Human approves.** The operator reviews the task in the dashboard and
   clicks Apply. This is the only thing that may call
   `POST /api/dashboard/tasks/{id}/apply` — never automation.
6. **Dispatch through the allowlist.** `apply_task` (`task_apply_service.py`)
   looks up the `action_kind` in `ALLOWLIST`, refuses never-apply / deferred /
   unknown kinds, enforces `assert_high_stakes_gate` (both signals required),
   then calls the registered handler with the frozen payload. The LLM never
   invents the verb.
7. **Execute + audit.** The handler performs the write; the task moves
   `pending → approved → executing → completed` (or `failed`), and a
   `WorkflowLog` row records the outcome either way.
8. **Measure impact.** After a clean comparison window, confirm the change did
   what the opportunity predicted.

### Done correctly looks like

- The change went live **only** after a human click, with a recorded
  `judge_verdict=PASS` where the verb is non-deterministic.
- The applied payload is exactly the frozen one from step 3 — no LLM-chosen verb
  or late-bound parameters.
- A refused or un-approved task made **no** live change and left the queue and
  the site untouched.
- There is a `WorkflowLog` row for the attempt (success *or* failure), so the
  action is auditable after the fact.
- No `/products/*` or utility-collection write happened, regardless of flags.

### Done incorrectly looks like (any one of these fails the workflow)

- Apply reachable from n8n/cron, or the gate satisfied by a default/auto-set
  flag.
- A new `action_kind` dispatched that wasn't a reviewed `ALLOWLIST` entry.
- Opportunity generation that wrote to the DB or called a provider instead of
  staying a pure predicate.

The invariants for this workflow are pinned by
[`../tests/test_task_apply.py`](../tests/test_task_apply.py),
[`../tests/test_high_stakes_routes.py`](../tests/test_high_stakes_routes.py),
and [`../tests/test_agent_eval_guardrails.py`](../tests/test_agent_eval_guardrails.py).

---

## Workflow B — The independent judiciary check

A high-stakes copy change must be reviewed by a model that is deliberately
*different* from the one that wrote it, before a human is ever asked to confirm.

1. **Executive drafts.** Claude (Anthropic) produces the content draft or SEO
   change from first-party evidence.
2. **Route to an independent judge.** `route_llm` sends the review to the
   judiciary role, which resolves to **xAI/Grok when `XAI_API_KEY` is set** —
   a different provider/family than the executive — and otherwise falls back to
   Anthropic. The point is independence, not a second opinion from the same
   model.
3. **Judge returns a verdict.** `PASS` or not. A timeout, an error, or an empty
   body must **never** resolve to `PASS`.
4. **Record the audit row.** The call is logged (success or error) with the
   verdict, so the review is reconstructable.
5. **Gate on both signals.** `assert_high_stakes_gate` lets the write proceed
   only if `judge_verdict=="PASS"` **and** `human_approved` is true. "No verdict"
   and "FAIL" both keep the gate closed.
6. **Human confirms.** Only now does the operator's click take effect
   (re-joining Workflow A at step 5).

### Done correctly looks like

- The judge that reviewed the draft was a different provider family than the
  drafter whenever `XAI_API_KEY` is configured.
- Every judiciary call left an audit row — including failures.
- A non-PASS or missing verdict blocked the write; it was never laundered into
  an implicit approval.
- The human confirmation was still required on top of the `PASS`.

### Done incorrectly looks like

- A provider timeout treated as "no objection" and allowed through.
- The judiciary silently retried against the executive's own family, collapsing
  the independence.
- `judge_verdict=PASS` alone (no human click) permitted a write.

The fail-closed behavior and verdict integrity are pinned by
[`../tests/test_llm_router.py`](../tests/test_llm_router.py) and
[`../tests/test_agent_eval_guardrails.py`](../tests/test_agent_eval_guardrails.py);
the policy is in [`agents.md`](agents.md) and
[`mac-mini-agent-server-plan.md`](mac-mini-agent-server-plan.md).

---

For the rubric used to review changes to these workflows, see
[`agent-evaluation.md`](agent-evaluation.md). For hands-on example tasks and
their graders, see [`../evals/`](../evals/).
