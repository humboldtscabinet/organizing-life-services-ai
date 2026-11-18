# Worked example: designing and refining one task

This is the design history behind Task 01 (and the enqueue-filter work it
mirrors). It shows how the *prompt and the grader* changed after a first agent
attempt — the point being that most of the safety in this repo comes from the
rubric, not the model.

## v1 prompt (too open-ended)

> We keep getting junk frozen-meta rewrite tasks in the dashboard. Add a filter
> that stops the bad ones from showing up.

### What went wrong on the first attempt

The agent produced a plausible-looking change that failed review on three
counts:

1. **It moved the decision into the wrong layer.** The filter was added inside
   the Apply dispatcher, so a "bad" task could still be *created*, and the
   rejection only happened when the operator clicked Apply. That both cluttered
   the queue (the thing we wanted to fix) and put new logic on the high-stakes
   write path.
2. **"Bad" was undefined, so it over-rejected.** With no rubric, the agent
   dropped any rewrite whose title differed a lot from the live title —
   including legitimate CTR rewrites, which is the whole value of the feature.
3. **No test pinned the boundary.** The PR had one happy-path test and no case
   proving a *good* rewrite still survived, so the regression was invisible.

The first two are guardrail problems; the third is why they slipped through.

## What we changed

### Prompt v2 (constrained + testable)

> Stop enqueueing low-value `shopify.apply_frozen_meta` tasks **at creation
> time** (a pure predicate — no Apply, gate, or `action_kind` changes). Reject a
> draft when it: is essentially the raw GSC query; drops the live page's city or
> core service term; targets a rank hole (avg position ≥ 15 — a ranking job, not
> a snippet job); duplicates a URL that already has an open frozen-meta task; or
> is truncated / keyword-stuffed / names a competitor. A real CTR snippet job on
> an existing URL that keeps the city + service **must still enqueue**.

The changes that mattered:

- **Named the layer:** "at creation time … no Apply/gate/`action_kind`
  changes." This is the difference between fixing the queue and growing the
  write surface.
- **Turned "bad" into an enumerated list** with a concrete threshold
  (`RANK_HOLE_POSITION = 15.0`) instead of a vibe.
- **Added an explicit negative requirement** — the good rewrite must survive —
  so the grader has a both-sides boundary.

### Grader v2 (executable + human)

- Executable: `tests/test_task_enqueue_filters.py` must contain a rejecting case
  *and* a surviving-good-rewrite case, plus dedupe-by-URL; and
  `tests/test_agent_eval_guardrails.py` must still pass to prove the gate and
  allowlist were untouched.
- Human: the filter is a pure, side-effect-free predicate; no new `action_kind`;
  CHANGELOG updated.

## Final result

The shipped work (`app/services/task_enqueue_filters.py`,
`frozen_meta_rejection_reason` / `should_skip_low_lead_near_me`, wired into task
*creation* in `dashboard_service.py` and `content_scheduler.py`) matches prompt
v2 exactly, and its tests encode both sides of every boundary. See the
"Enqueue-time task filters" entry in [`../CHANGELOG.md`](../CHANGELOG.md).

## The transferable lesson

When an agent task touches guardrails, the prompt must name **(a)** the layer
the change belongs in, **(b)** the exact reject/keep boundary, and **(c)** a
must-not-regress positive case — and the grader must make all three executable.
Vague prompts don't just produce worse code; they produce code that quietly
relocates risk.
