"""
Unit tests for pure helpers in data/deep_seo_audit.py.

That file isn't an importable package, so we load it by path. We only touch
side-effect-free helpers (math + formatting + GSC totals), never the network
or API entry points.
"""

import importlib.util
from pathlib import Path

import pytest

_AUDIT_PATH = Path(__file__).resolve().parent.parent / "data" / "deep_seo_audit.py"


@pytest.fixture(scope="module")
def audit():
    spec = importlib.util.spec_from_file_location("deep_seo_audit", _AUDIT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_pct_change_basic(audit):
    assert audit.pct_change(110, 100) == pytest.approx(10.0)
    assert audit.pct_change(90, 100) == pytest.approx(-10.0)


def test_pct_change_guards_zero(audit):
    assert audit.pct_change(5, 0) is None
    assert audit.pct_change(5, None) is None


def test_fmt_int(audit):
    assert audit.fmt_int(15981) == "15,981"
    assert audit.fmt_int("n/a") == "n/a"


def test_fmt_pct(audit):
    assert audit.fmt_pct(None) == "n/a"
    assert audit.fmt_pct(-14.1) == "-14.1%"
    assert audit.fmt_pct(7.0) == "+7.0%"


def test_gsc_totals_weighted_position(audit):
    rows = [
        {"clicks": 10, "impressions": 100, "position": 2.0},
        {"clicks": 0, "impressions": 900, "position": 20.0},
    ]
    t = audit.gsc_totals(rows)
    assert t["clicks"] == 10
    assert t["impressions"] == 1000
    # impression-weighted position leans toward the high-impression row
    assert t["avg_position_weighted"] == pytest.approx((2 * 100 + 20 * 900) / 1000)
    # raw mean is the simple average of the two positions
    assert t["avg_position_unweighted"] == pytest.approx(11.0)
    assert t["ctr"] == pytest.approx(10 / 1000)


def test_gsc_totals_empty(audit):
    t = audit.gsc_totals([])
    assert t["clicks"] == 0
    assert t["impressions"] == 0
    assert t["avg_position_weighted"] == 0.0
