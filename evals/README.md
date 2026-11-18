# Agent evaluation tasks

This directory holds a small, public set of **hand-crafted example tasks** that
look like the real work agents (Cursor Cloud Agents / Grok Bots) do in this
repo. They exist to make our evaluation standards concrete: each task pairs a
prompt an agent would receive with a grader/rubric a reviewer uses to decide
whether the result is actually correct and safe.

These are not a benchmark harness or a training set. They are worked examples of
the kind of multi-step, guardrail-sensitive change this codebase requires, so
that the bar is visible instead of living only in reviewers' heads.

## How the tasks are structured

Each file in [`tasks/`](tasks/) has three sections:

1. **Prompt** — what the agent is asked to do, phrased the way the request
   actually arrives (an issue, a Slack message, a follow-up).
2. **Grader / rubric** — how we decide it was done correctly: a checklist, the
   exact test command that must pass, and the expected observable outcomes.
3. **Why it's realistic** — a note on which real problem this mirrors and why it
   is genuinely multi-step (it touches more than one subsystem, or it has a
   "looks done but isn't" failure mode).

## The tasks

| Task | Mirrors | Core risk being graded |
|---|---|---|
| [01 — Add a gated SEO opportunity type](tasks/01-add-gated-seo-opportunity-type.md) | the enqueue-time filters + frozen-meta work | new opportunity logic that must **not** touch the gate/Apply |
| [02 — Wire a new data source without breaking the gate](tasks/02-wire-new-data-source.md) | the GSC/GA4/Ads ingest services | read-only ingest that stays localhost-only and gate-neutral |
| [03 — Fix a failure mode in the LLM router](tasks/03-fix-llm-router-failure-mode.md) | `llm_router.py` audit logging & fail-closed routing | an error path that must fail safe and stay auditable |
| [04 — Register a new allowlisted Apply verb](tasks/04-register-allowlisted-apply-verb.md) | the `ALLOWLIST` / `task_apply_service` dispatcher | the one deliberately-reviewed way to add a write verb |

See [`example-iteration.md`](example-iteration.md) for a worked example of
designing and refining one of these prompts (and its grader) after a first
agent attempt went wrong.

## Running the graders

The high-stakes graders are **executable**: they are the focused invariant tests
in [`../tests/test_agent_eval_guardrails.py`](../tests/test_agent_eval_guardrails.py)
plus the existing gate/router/apply suites. The convenience runner maps a task
to the tests that grade it:

```bash
# Grade everything the example tasks care about:
evals/grade.sh

# Grade one task by number:
evals/grade.sh 04
```

A task's "code" grade is these tests passing; the rest of the rubric
(side-effect risk, scope, docs) is a human checklist, because that is how this
repo is actually reviewed. The full standard lives in
[`../docs/agent-evaluation.md`](../docs/agent-evaluation.md).
