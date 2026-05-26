# Runbook: Deploy / Update the Shopify JSON-LD Schema Snippet

The site's structured-data coverage (LocalBusiness, Service, Breadcrumb, etc.) lives in a single Liquid snippet on the Shopify theme.

## Prerequisites

- `SHOPIFY_STORE_DOMAIN` and `SHOPIFY_ADMIN_API_TOKEN` with `write_themes` scope.
- The snippet source lives at [data/seo-schema.liquid](../../data/seo-schema.liquid).

## Procedure

1. **Edit the snippet locally:**
   ```bash
   $EDITOR data/seo-schema.liquid
   ```
   Add/modify JSON-LD `@type` blocks as needed. Use [schema.org](https://schema.org) as the reference.

2. **Validate the JSON-LD** at https://validator.schema.org/ by pasting one of the rendered outputs (you can preview by visiting any live page once deployed).

3. **Push to Shopify theme:**
   ```bash
   python data/push_schema_snippet.py
   ```
   This uploads `data/seo-schema.liquid` to the active theme as `snippets/seo-schema.liquid`. The theme's `theme.liquid` should already include `{% render 'seo-schema' %}` in the `<head>` — if not, add it via the Shopify theme editor.

4. **Verify live:**
   - Visit any page in incognito
   - View source, search for `application/ld+json`
   - Should see all configured `@type` blocks

5. **Run a quick crawl to confirm coverage:**
   ```bash
   python data/deep_seo_audit.py
   ```
   Check §6 "Structured data coverage" — should be ≈100% of crawled 200-OK pages.

6. **Submit to Google for re-crawl:** in Search Console → URL Inspection → submit a few representative pages.

7. **Update [docs/seo-audits/CHANGELOG.md](../seo-audits/CHANGELOG.md).**

## If something goes wrong

- **Snippet uploads but doesn't render:** confirm `theme.liquid` has `{% render 'seo-schema' %}` in `<head>`.
- **schema.org validator errors:** usually a missing required field. Check the @type spec.
- **Coverage drops after a deploy:** Shopify theme may have a per-page meta override that's stripping the snippet. The audit's "Shopify override detector" surfaces these.

## Related code

- [data/seo-schema.liquid](../../data/seo-schema.liquid) — snippet source
- [data/push_schema_snippet.py](../../data/push_schema_snippet.py) — uploader
- [data/add_schema_markup.py](../../data/add_schema_markup.py) — bulk add (deprecated in favor of single snippet)
