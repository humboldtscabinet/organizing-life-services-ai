#!/usr/bin/env bash
# Grade the evals/ example tasks by running the focused tests that act as their
# executable rubric. With no argument, runs the full high-stakes grader set.
# With a task number (01-04), runs only the tests that grade that task.
#
#   evals/grade.sh        # all high-stakes graders
#   evals/grade.sh 04     # just the allowlisted-Apply-verb grader
#
# This is the "code" half of each task's rubric. The human checklist half lives
# in the task file and in docs/agent-evaluation.md.
set -euo pipefail

cd "$(dirname "$0")/.."

# The invariant rubric that every high-stakes task is graded against.
RUBRIC="tests/test_agent_eval_guardrails.py"

case "${1:-all}" in
  all)
    exec python3 -m pytest -q \
      "$RUBRIC" \
      tests/test_llm_router.py \
      tests/test_task_apply.py \
      tests/test_high_stakes_routes.py \
      tests/test_gtm_write_control.py \
      tests/test_task_enqueue_filters.py
    ;;
  01)
    # New opportunity logic must not touch the gate/Apply: enqueue filters +
    # the invariant that the allowlist stays gated and never-apply stays intact.
    exec python3 -m pytest -q "$RUBRIC" tests/test_task_enqueue_filters.py
    ;;
  02)
    # New data source: ingest services + the gate invariants stay untouched.
    exec python3 -m pytest -q "$RUBRIC" tests/test_gsc_service.py tests/test_data_freshness.py
    ;;
  03)
    # LLM router failure modes: routing, audit logging, fail-closed gate.
    exec python3 -m pytest -q "$RUBRIC" tests/test_llm_router.py tests/test_llm_status.py
    ;;
  04)
    # New allowlisted Apply verb: dispatcher + gate wiring invariants.
    exec python3 -m pytest -q "$RUBRIC" tests/test_task_apply.py tests/test_high_stakes_routes.py
    ;;
  *)
    echo "Unknown task: ${1}. Use one of: all, 01, 02, 03, 04" >&2
    exit 2
    ;;
esac
