# Task 03 — Fix a failure mode in the LLM router

## Prompt

> When the judiciary provider (xAI/Grok) times out or returns a non-JSON body,
> we need to be certain that failure can never be laundered into an approval.
> Harden and lock down the judiciary failure path so that:
>
> - A provider error is still recorded in the audit log (with the error) and
>   then surfaced to the caller — never swallowed into a silent gap. (The router
>   already writes an error audit row today; the task is to keep that guaranteed
>   and pin it with a test.)
> - A failed or empty judiciary response **never** resolves to a passing
>   verdict. Downstream, "no verdict" and "FAIL" must both keep the high-stakes
>   gate closed.
> - Don't change which provider serves which role, and don't add a retry that
>   silently swaps the judiciary to the executive's family.

## Grader / rubric

**Executable (`evals/grade.sh 03`)**

- [ ] `tests/test_llm_router.py` passes, including a **new** test that simulates
      a judiciary provider raising / returning a non-PASS body and asserts:
      (a) an audit row is written with the error (preserving today's behavior),
      and (b) the returned/resolved verdict is not `"PASS"`.
- [ ] `tests/test_agent_eval_guardrails.py::TestGateFailsClosed` passes — a
      `None` or non-`"PASS"` verdict still raises `HighRiskGateError`.

**Human checklist**

- [ ] The fix is in the **error path** only; the happy-path routing
      (`_default_role_for` / `_provider_for`) is unchanged, so clerk→Ollama,
      executive→Claude, judiciary→Grok-when-`XAI_API_KEY` still holds.
- [ ] No `except: pass` / swallowed exception. The error is logged and recorded,
      not hidden.
- [ ] The judiciary stays an **independent** provider — the fix does not add a
      fallback that routes the judge to the same family as the executive (that
      would defeat the independent-review design in
      `docs/mac-mini-agent-server-plan.md`).
- [ ] `assert_high_stakes_gate` is untouched; its fail-closed contract is relied
      on, not re-implemented.

**Expected outcome:** provider failures are auditable and fail safe; a human
confirmation is still required and a non-PASS verdict can never be laundered
into an approval.

## Why it's realistic

The router already writes an audit row on both success and error and exposes
`assert_high_stakes_gate` as a separate fail-closed check (see
`app/services/llm_router.py`). This task is multi-step because the real risk
isn't the crash — it's the *quiet* degradation where a timeout becomes an
implicit "no objection." The grader pins the two invariants that protect
against that: audit completeness and verdict integrity.
