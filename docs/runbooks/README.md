# Runbooks

Step-by-step operational procedures for common tasks. Each runbook is self-contained — anyone (including future you, at 2am) should be able to follow it without asking questions.

## SEO operations

- [run-deep-seo-audit.md](run-deep-seo-audit.md) — generate a fresh deep SEO audit and synthesize it
- [ga4-key-event-cleanup.md](ga4-key-event-cleanup.md) — clean up GA4 key events so conversions reflect real lead intent
- [improve-google-analytics.md](improve-google-analytics.md) — step-by-step guide to improve OLS GA4 measurement (key events, phone clicks, weekly hygiene)
- [gtm-write-and-publish.md](gtm-write-and-publish.md) — gated GTM workspace writes, version create, and live publish
- [gcp-apis-to-enable.md](gcp-apis-to-enable.md) — which Google Cloud APIs to enable (and not enable) for OLS
- [google-api-access.md](../google-api-access.md) — per-product read/write status and completion plan
- [complete-google-api-access.md](complete-google-api-access.md) — ordered you+agent playbook (probe, Ads OAuth, GA4/GTM, GBP)
- [push-meta-rewrites.md](push-meta-rewrites.md) — push title/meta changes to Shopify
- [service-guardrails-homepage-ctr.md](service-guardrails-homepage-ctr.md) — noindex fee products + homepage organizers CTR apply
- [deploy-schema-snippet.md](deploy-schema-snippet.md) — update the Shopify JSON-LD schema snippet
- [data-mutation-scripts.md](data-mutation-scripts.md) — safely handle legacy direct-write scripts

## Ops

- [dashboard-alerts.md](dashboard-alerts.md) — create operational alerts for the private dashboard

## Conventions

- Every command is copy-pasteable
- Prerequisites are listed at the top
- "If something goes wrong" section at the bottom of each runbook
- Cross-reference relevant code with workspace-relative paths
