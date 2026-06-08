"""
Unit tests for the URL Inspection summariser.

`summarize()` is the pure aggregation step that turns raw per-URL inspection
dicts into report counts + a "needs attention" list. No network needed.
"""

from app.services import gsc_url_inspection as ui


def test_summarize_all_indexed_no_problems():
    results = [
        {"url": "https://x/a", "verdict": "PASS",
         "coverage_state": "Submitted and indexed", "canonical_mismatch": False},
        {"url": "https://x/b", "verdict": "PASS",
         "coverage_state": "Submitted and indexed", "canonical_mismatch": False},
    ]
    s = ui.summarize(results)
    assert s["inspected"] == 2
    assert s["errors"] == 0
    assert s["verdict_counts"] == {"PASS": 2}
    assert s["problems"] == []


def test_summarize_flags_not_indexed():
    # Real not-indexed URLs come back with a non-PASS verdict (the substring
    # "indexed" is present in "not indexed", so coverage alone won't flag it).
    results = [
        {"url": "https://x/a", "verdict": "NEUTRAL",
         "coverage_state": "Crawled - currently not indexed", "canonical_mismatch": False},
    ]
    s = ui.summarize(results)
    assert len(s["problems"]) == 1
    assert s["problems"][0]["url"] == "https://x/a"


def test_summarize_flags_canonical_mismatch():
    results = [
        {"url": "https://x/a", "verdict": "PASS",
         "coverage_state": "Submitted and indexed", "canonical_mismatch": True},
    ]
    s = ui.summarize(results)
    assert len(s["problems"]) == 1


def test_summarize_counts_errors():
    results = [
        {"url": "https://x/a", "error": "quota exceeded"},
        {"url": "https://x/b", "verdict": "PASS",
         "coverage_state": "Submitted and indexed", "canonical_mismatch": False},
    ]
    s = ui.summarize(results)
    assert s["errors"] == 1
    assert any(p.get("error") for p in s["problems"])
    assert s["verdict_counts"] == {"PASS": 1}
