"""Unit coverage for Session 12 service-guardrail theme patches."""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    # Mutation guard activates on import; fine for pure patch tests.
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def fee_products():
    return _load(
        "session12_noindex_fee_products",
        ROOT / "data" / "session12_noindex_fee_products.py",
    )


@pytest.fixture(scope="module")
def homepage_ctr():
    return _load(
        "session12_homepage_organizers_ctr",
        ROOT / "data" / "session12_homepage_organizers_ctr.py",
    )


def test_fee_product_noindex_patch_is_idempotent(fee_products):
    base = (
        fee_products.PAGE_ROBOTS_BLOCK
        + "\n    <!-- rest of head -->\n"
    )
    once, changed = fee_products.patch_product_noindex(base)
    assert changed is True
    assert fee_products.PRODUCT_NOINDEX_MARKER in once
    assert "product-cc-2-7-fee" in once
    assert 'content="noindex,follow"' in once

    twice, changed_again = fee_products.patch_product_noindex(once)
    assert changed_again is False
    assert twice == once


def test_fee_product_noindex_emits_single_robots_tag(fee_products):
    """Fee handles must not also emit a metafield robots tag."""
    patch = fee_products.build_product_noindex_patch()
    assert patch.count('<meta name="robots"') == 2
    assert "ols_noindex_product -%}" in patch
    assert (
        '{%- if ols_noindex_product -%}\n'
        '    <meta name="robots" content="noindex,follow">\n'
        "    {%- elsif product and product.metafields.seo.robots != blank -%}\n"
        '    <meta name="robots" content="{{ product.metafields.seo.robots | escape }}">\n'
        "    {%- endif -%}"
    ) in patch
    # Metafield robots tag is mutually exclusive with fee-handle noindex.
    assert patch.index("ols_noindex_product -%}") < patch.index(
        "product.metafields.seo.robots != blank"
    )


def test_homepage_meta_lengths_and_replace(homepage_ctr):
    assert len(homepage_ctr.HOMEPAGE_TITLE) <= 60
    assert 120 <= len(homepage_ctr.HOMEPAGE_DESCRIPTION) <= 160

    source = f"""
      {{%- comment -%}} {homepage_ctr.HOMEPAGE_META_MARKER}: title {{%- endcomment -%}}
      {{%- if template.name == 'index' -%}}
      Estate Sale Organizers Tampa Bay | Appraisals & Downsizing
      {{%- else -%}}
      {{{{ page_title }}}}
      {{%- endif -%}}
    </title>
    {{%- comment -%}} {homepage_ctr.HOMEPAGE_META_MARKER}: description {{%- endcomment -%}}
    {{%- if template.name == 'index' -%}}
    <meta name="description" content="Tampa Bay estate sale organizers for estate sales, appraisals, downsizing, and cleanouts across Pinellas, Pasco, Hillsborough, Hernando, and Citrus.">
    {{%- elsif page_description -%}}
    <meta name="description" content="{{{{ page_description | escape }}}}">
    {{%- endif -%}}
    {{%- include 'cookie-policy' -%}}
"""
    after_meta, meta_status = homepage_ctr.replace_homepage_meta(source)
    assert meta_status == "replaced"
    assert homepage_ctr.HOMEPAGE_TITLE in after_meta
    assert homepage_ctr.HOMEPAGE_DESCRIPTION in after_meta

    again, status2 = homepage_ctr.replace_homepage_meta(after_meta)
    assert status2 == "unchanged"
    assert again == after_meta

    with_links, link_status = homepage_ctr.patch_organizer_intlinks(after_meta)
    assert link_status == "inserted"
    assert homepage_ctr.INTLINKS_MARKER in with_links
    assert "/pages/estate-sale-palm-harbor-pinellas-county" in with_links
    assert "estate sale organizers" in with_links.lower()

    again_links, link_status2 = homepage_ctr.patch_organizer_intlinks(with_links)
    assert link_status2 == "unchanged"
    assert again_links == with_links
