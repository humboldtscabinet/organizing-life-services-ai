# Runbook: Push Meta Title / Description Rewrites to Shopify

Used to deploy LLM-drafted page titles and meta descriptions to the live Shopify storefront.

## Prerequisites

- `SHOPIFY_STORE_DOMAIN` and `SHOPIFY_ADMIN_API_TOKEN` set in `.env` (see [`.env.example`](../../.env.example)).
- An OpenAI / Anthropic key for the draft-generation step (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`).

## Procedure

1. **Pull current live meta** to know baseline:
   ```bash
   python data/inspect_source_pages.py > /tmp/meta_before.txt
   ```

2. **Generate drafts:**
   ```bash
   python data/meta_drafts.py
   ```
   Writes proposed titles/metas to a JSON staging file (path printed at end of run). **Review the drafts manually** — do not auto-push without inspection.

3. **Push round 1:**
   ```bash
   python data/push_meta_to_shopify.py
   ```
   Pushes to Shopify Admin API. Logs every page touched + before/after values.

4. **Verify:** Wait ~5 minutes for cache, then visit 3–5 pages in incognito and inspect `<title>` and `<meta name="description">`.

5. **Round 2 — fix anything still too long:**
   ```bash
   python data/push_meta_round2.py
   ```
   Targets pages flagged `title_too_long` or `meta_description_too_long` in the most recent audit.

6. **Update the changelog** at [docs/seo-audits/CHANGELOG.md](../seo-audits/CHANGELOG.md).

7. **Schedule a measurement audit** for ~28 days later so GSC has a clean comparison window. See [run-deep-seo-audit.md](run-deep-seo-audit.md).

## Length targets

- **Title:** ≤ 60 characters (else Google truncates with `…`)
- **Meta description:** 120–160 characters

## If something goes wrong

- **401 from Shopify:** token is expired or missing the `write_online_store_pages` scope. Regenerate the Admin API token.
- **Pushed wrong meta:** revert via the Shopify admin UI for that specific page; the script is one-page-per-API-call so partial failures don't cascade.
- **Drafts look low quality:** edit the prompt at the top of `data/meta_drafts.py` and re-run.

## Related code

- [data/meta_drafts.py](../../data/meta_drafts.py)
- [data/push_meta_to_shopify.py](../../data/push_meta_to_shopify.py)
- [data/push_meta_round2.py](../../data/push_meta_round2.py)
- [data/inspect_source_pages.py](../../data/inspect_source_pages.py)
