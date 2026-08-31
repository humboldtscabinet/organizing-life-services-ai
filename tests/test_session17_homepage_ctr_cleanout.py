"""Unit coverage for Session 17 homepage CTR (organizers + cleanout) patch.

These tests exercise the pure theme-string transforms only; no Shopify or
network calls are made. The mutation guard activates on import, which is fine.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def s17():
    return _load(
        "session17_homepage_ctr_cleanout",
        ROOT / "data" / "session17_homepage_ctr_cleanout.py",
    )


def _v1_meta_block(s17, *, title: str, description: str) -> str:
    return f"""
      {{%- comment -%}} {s17.HOMEPAGE_META_MARKER_V1}: title {{%- endcomment -%}}
      {{%- if template.name == 'index' -%}}
      {title}
      {{%- else -%}}
      {{{{ page_title }}}}
      {{%- endif -%}}
    </title>
    {{%- comment -%}} {s17.HOMEPAGE_META_MARKER_V1}: description {{%- endcomment -%}}
    {{%- if template.name == 'index' -%}}
    <meta name="description" content="{description}">
    {{%- elsif page_description -%}}
    <meta name="description" content="{{{{ page_description | escape }}}}">
    {{%- endif -%}}
"""


def _intlinks_block(s17, *, with_cleanout: bool) -> str:
    cleanout_line = (
        '<p style="margin:0;">Need a cleanout after the sale? See our '
        '<a href="/pages/estate-cleanout-services">estate cleanout services</a>.</p>'
        if with_cleanout
        else ""
    )
    return f"""
    {{%- if template.name == 'index' -%}}
    {{%- comment -%}} {s17.INTLINKS_MARKER}: organizer + service-area anchors {{%- endcomment -%}}
    <section class="ols-home-organizers-intlinks" aria-label="Estate sale organizer services">
      <h2>Estate Sale Organizers Serving Tampa Bay</h2>
      <p>Families hire our <a href="/pages/contact-us">estate sale organizers</a>.</p>
      {cleanout_line}
    </section>
    {{%- endif -%}}
"""


def _gtm_block(s17) -> str:
    return f"""
    {{%- comment -%}} {s17.GTM_MARKER} head {{%- endcomment -%}}
    <script>/* {s17.GTM_PUBLIC_ID} */</script>
"""


# --- Proposed copy contract ------------------------------------------------


def test_copy_lengths_and_dual_intent(s17):
    assert len(s17.HOMEPAGE_TITLE) <= 60
    assert 120 <= len(s17.HOMEPAGE_DESCRIPTION) <= 160
    # Both intents represented.
    assert "organizer" in s17.HOMEPAGE_TITLE.lower()
    assert "cleanout" in s17.HOMEPAGE_TITLE.lower()
    assert "organizer" in s17.HOMEPAGE_DESCRIPTION.lower()
    assert "cleanout" in s17.HOMEPAGE_DESCRIPTION.lower()
    # Region + approved phone preserved; no "near me" stuffing in the copy.
    assert "Tampa Bay" in s17.HOMEPAGE_DESCRIPTION
    assert "(727) 542-6028" in s17.HOMEPAGE_DESCRIPTION
    assert "near me" not in s17.HOMEPAGE_TITLE.lower()
    assert "near me" not in s17.HOMEPAGE_DESCRIPTION.lower()


# --- Marker upgrade + idempotency -----------------------------------------


def test_upgrades_v1_copy_to_v2(s17):
    source = _v1_meta_block(
        s17,
        title="Estate Sale Organizers Tampa Bay | Call OLS Today",
        description=(
            "Need estate sale organizers in Tampa Bay? OLS runs estate sales, "
            "appraisals, and downsizing across Pinellas to Citrus. "
            "Call (727) 542-6028."
        ),
    )
    after, status = s17.upgrade_homepage_meta(source)
    assert status == "upgraded"
    assert s17.HOMEPAGE_META_MARKER_V2 in after
    assert s17.HOMEPAGE_META_MARKER_V1 not in after
    assert s17.HOMEPAGE_TITLE in after
    assert s17.HOMEPAGE_DESCRIPTION in after
    # Old copy is gone.
    assert "Call OLS Today" not in after


def test_upgrade_is_idempotent(s17):
    source = _v1_meta_block(
        s17,
        title="Estate Sale Organizers Tampa Bay | Call OLS Today",
        description=(
            "Need estate sale organizers in Tampa Bay? OLS runs estate sales, "
            "appraisals, and downsizing across Pinellas to Citrus. "
            "Call (727) 542-6028."
        ),
    )
    once, _ = s17.upgrade_homepage_meta(source)
    twice, status = s17.upgrade_homepage_meta(once)
    assert status == "unchanged"
    assert twice == once


def test_upgrade_handles_legacy_session10_copy(s17):
    source = _v1_meta_block(
        s17,
        title="Estate Sale Organizers Tampa Bay | Appraisals & Downsizing",
        description=(
            "Tampa Bay estate sale organizers for estate sales, appraisals, "
            "downsizing, and cleanouts across Pinellas, Pasco, Hillsborough, "
            "Hernando, and Citrus."
        ),
    )
    after, status = s17.upgrade_homepage_meta(source)
    assert status == "upgraded"
    assert s17.HOMEPAGE_TITLE in after
    assert s17.HOMEPAGE_DESCRIPTION in after
    assert s17.HOMEPAGE_META_MARKER_V1 not in after


def test_upgrade_requires_marker(s17):
    with pytest.raises(RuntimeError):
        s17.upgrade_homepage_meta("<title>no marker here</title>")


# --- Cleanout intlinks sentence -------------------------------------------


def test_cleanout_present_not_duplicated(s17):
    source = _intlinks_block(s17, with_cleanout=True)
    after, status = s17.ensure_cleanout_sentence(source)
    assert status == "present"
    assert after == source
    assert after.lower().count("estate cleanout services") == 1


def test_cleanout_sentence_inserted_only_when_missing(s17):
    source = _intlinks_block(s17, with_cleanout=False)
    after, status = s17.ensure_cleanout_sentence(source)
    assert status == "inserted"
    assert "estate-cleanout-services" in after
    # Still inside the section (before its close tag), single insertion.
    assert after.count("estate-cleanout-services") == 1
    again, status2 = s17.ensure_cleanout_sentence(after)
    assert status2 == "present"
    assert again == after


def test_cleanout_absent_intlinks_is_noop(s17):
    source = "<head>no intlinks block</head>"
    after, status = s17.ensure_cleanout_sentence(source)
    assert status == "intlinks_absent"
    assert after == source


# --- GTM regression guard --------------------------------------------------


def test_full_transform_preserves_gtm(s17):
    source = (
        _gtm_block(s17)
        + _v1_meta_block(
            s17,
            title="Estate Sale Organizers Tampa Bay | Call OLS Today",
            description=(
                "Need estate sale organizers in Tampa Bay? OLS runs estate sales, "
                "appraisals, and downsizing across Pinellas to Citrus. "
                "Call (727) 542-6028."
            ),
        )
        + _intlinks_block(s17, with_cleanout=True)
    )
    after, _ = s17.upgrade_homepage_meta(source)
    after, _ = s17.ensure_cleanout_sentence(after)
    # Should not raise.
    s17.assert_gtm_preserved(source, after)
    assert s17.GTM_PUBLIC_ID in after
    assert s17.GTM_MARKER in after


def test_gtm_guard_raises_on_regression(s17):
    before = _gtm_block(s17)
    after = "<head>GTM snippet dropped</head>"
    with pytest.raises(RuntimeError):
        s17.assert_gtm_preserved(before, after)
