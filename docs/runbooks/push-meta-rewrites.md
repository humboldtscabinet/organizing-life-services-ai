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
   OLS_ALLOW_DATA_MUTATION=1 \
   OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE \
   python data/push_meta_to_shopify.py
   ```
   Pushes to Shopify Admin API. Logs every page touched + before/after values.

4. **Verify:** Wait ~5 minutes for cache, then visit 3–5 pages in incognito and inspect `<title>` and `<meta name="description">`.

5. **Round 2 — fix anything still too long:**
   ```bash
   OLS_ALLOW_DATA_MUTATION=1 \
   OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE \
   python data/push_meta_round2.py
   ```
   Targets pages flagged `title_too_long` or `meta_description_too_long` in the most recent audit.

6. **Round 3+ (audit-driven, scalable workflow):**
   The round-3 pipeline reads directly from the latest deep-SEO audit JSON
   instead of hard-coded TARGETS lists. Use this for any future rewrite pass.

   ```bash
   # a) Generate drafts for every page flagged in the latest audit
   python data/round3_draft_metas.py
   # -> writes data/audit_output/round3_meta_drafts.json (all approved: false)

   # b) Open the JSON, review each draft, set "approved": true to deploy.
   #    You can also hand-edit draft.new_title / draft.new_meta_description.

   # c) Dry-run preview
   DRY_RUN=1 docker exec -e DRY_RUN=1 ols-api python3 /app/data/push_meta_round3.py

   # d) Push for real
   docker exec \
     -e OLS_ALLOW_DATA_MUTATION=1 \
     -e OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE \
     ols-api python3 /app/data/push_meta_round3.py
   ```

   Entries with `kind: "special"` (blog index, collections) are skipped
   automatically — those can't use per-resource SEO metafields.

7. **Update the changelog** at [docs/seo-audits/CHANGELOG.md](../seo-audits/CHANGELOG.md).

7. **Schedule a measurement audit** for ~28 days later so GSC has a clean comparison window. See [run-deep-seo-audit.md](run-deep-seo-audit.md).

## Length targets

- **Title:** ≤ 60 characters (else Google truncates with `…`)
- **Meta description:** 120–160 characters

## If something goes wrong

- **401 from Shopify:** token is expired or missing the `write_online_store_pages` scope. Regenerate the Admin API token.
- **Mutation blocked:** direct `data/` writes require both
  `OLS_ALLOW_DATA_MUTATION=1` and
  `OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE`.
  Prefer guarded API routes when one exists.
- **Pushed wrong meta:** revert via the Shopify admin UI for that specific page; the script is one-page-per-API-call so partial failures don't cascade.
- **Drafts look low quality:** edit the prompt at the top of `data/meta_drafts.py` and re-run.

## Related code

- [data/meta_drafts.py](../../data/meta_drafts.py)
- [data/push_meta_to_shopify.py](../../data/push_meta_to_shopify.py)
- [data/push_meta_round2.py](../../data/push_meta_round2.py)
- [data/round3_draft_metas.py](../../data/round3_draft_metas.py)
- [data/push_meta_round3.py](../../data/push_meta_round3.py)
- [data/inspect_source_pages.py](../../data/inspect_source_pages.py)
