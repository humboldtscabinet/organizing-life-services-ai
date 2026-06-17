# Data Script Safety Audit - 2026-06-17

## Summary

The `data/` folder is useful historical SEO operations context, but it also
contains one-off scripts that can write directly to Shopify, theme assets, XO
Gallery metafields, redirects, and IndexNow endpoints.

The safety posture after this pass:

- Read-only and draft-generation scripts remain usable.
- Direct production mutations from scripts run under `data/` are blocked by
  default at runtime.
- Operators must explicitly set `OLS_ALLOW_DATA_MUTATION=1` before a direct
  `data/` script can write to Shopify Admin API or IndexNow.
- Preferred future path is still guarded API routes with
  `human_confirmed=true` and `judge_verdict=PASS`.

## Runtime Guard

Implemented files:

- `data/_mutation_guard.py`
- `data/sitecustomize.py`
- root `sitecustomize.py`

The guard patches `httpx` and `requests` only when a Python target under
`data/` is run directly. It blocks:

- `POST`, `PUT`, `PATCH`, and `DELETE` to Shopify Admin API paths
- `POST`, `PUT`, `PATCH`, and `DELETE` to IndexNow endpoints

It allows:

- `GET` requests
- Shopify OAuth token exchange at `/admin/oauth/access_token`
- normal API/server/test Python processes outside `data/`

## Script Categories

### Read-only / Analysis

These are intended to inspect, audit, or export data without production writes:

- `ads_conversion_audit.py`
- `blog_audit.py`
- `deep_seo_audit.py`
- `fetch_article.py`
- `gsc_pull_opportunities.py`
- `inspect_source_pages.py`
- `meta_drafts.py`
- `post_change_audit.py`
- `pull_all_data.py`
- `round3_draft_metas.py`
- `theme_title_audit.py`
- `verify_quick_wins.py`
- `verify_round3_state.py`

### Draft / Local Output

These primarily generate local artifacts for review:

- `meta_drafts.py`
- `round3_draft_metas.py`
- audit JSON/Markdown under `data/audit_output/`

### Direct Mutators With Existing Dry-Run Support

These already have some dry-run behavior, but direct writes are now also
blocked unless `OLS_ALLOW_DATA_MUTATION=1` is set:

- `b1_faq_what_is_estate_sale.py`
- `b2_yard_vs_estate_sale_post.py`
- `internal_links_a3.py`
- `push_meta_round3.py`
- `push_meta_round3_direct.py`
- `push_schema_snippet.py`
- `session9_strip_street_address.py`
- `theme_apply_homepage_intlinks.py`
- `theme_apply_title_patch.py`
- `xo_gallery_alt_apply.py`

### Direct Mutators Without Adequate Modern Guarding

These are historical one-off scripts and should not be the normal operating
path. If a similar operation is needed again, prefer turning it into a guarded
API workflow or add explicit preview/approval behavior first:

- `add_schema_markup.py`
- `apply_blog_fixes.py`
- `article_apply_intlinks_a4.py`
- `article_apply_top4_faqs.py`
- `article_apply_yard_garage_faq.py`
- `article_body_upgrade_top6.py`
- `create_seo_pages.py`
- `fix_contact_page.py`
- `geo_pages_expansion.py`
- `page_apply_striking_distance.py`
- `push_meta_round2.py`
- `push_meta_round4_pages.py`
- `push_meta_to_shopify.py`
- `seo_update_batch.py`
- `session5_schema_intlinks_noindex.py`
- `session6_recrawl_nap_geo_metas.py`
- `session7_geo_crosslinks_recrawl.py`
- `session8_faq_article_indexnow.py`

## Operator Policy

Default:

```bash
python data/some_script.py
```

Direct writes fail closed.

For an approved emergency one-off write:

```bash
OLS_ALLOW_DATA_MUTATION=1 python data/some_script.py
```

Before using that override:

- confirm the target store/account
- run any available `--dry-run`
- capture expected changes
- prefer a guarded API endpoint if one exists
- keep the terminal output as audit evidence

## Remaining Cleanup

- Convert any still-useful direct mutators into guarded API routes.
- Archive or delete obsolete one-off scripts after confirming they are no
  longer needed for SEO history.
- Add per-script metadata if the folder remains operational long-term:
  `read_only`, `draft_only`, `mutates_shopify`, `requires_env_override`.
