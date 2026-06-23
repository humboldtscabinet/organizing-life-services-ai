# SEO Integrations

## Goal

Improve qualified organic traffic, local visibility, and business inquiries for
Organizing Life Services by making measured, reviewable improvements to the
Shopify site.

## Data Sources

- Google Search Console (GSC): queries, pages, impressions, clicks, CTR, rank
- Google Analytics 4 (GA4): sessions, conversions, landing-page behavior
- Shopify: pages, articles, image/gallery assets, SEO fields
- Google Ads: GA4-derived paid traffic now; direct Ads API when credentials and
  developer-token access are available
- Google Business Profile (GBP): pending/limited until API access is available

## Workflow

1. Pull data into Postgres.
2. Run audits that prioritize striking-distance rankings, low-CTR pages,
   location opportunities, technical/schema issues, and conversion relevance.
3. Generate dashboard tasks or markdown audit reports.
4. Draft changes only from measured opportunities and approved first-party
   business facts.
5. Require human approval and independent judge review for public writes.
6. Re-measure after a clean comparison window.

## What To Avoid

- Bulk AI posts that exist only to hit keyword or word-count targets.
- Direct `data/` write scripts when a guarded API route exists.
- Treating n8n or agents as production-safe just because they can call the API.
- Optimizing for vanity traffic that is unlikely to produce estate sale,
  downsizing, cleanout, or organization leads.

## Best Current Levers

- Improve titles/meta descriptions for pages with impressions and weak CTR.
- Strengthen internal links from high-authority pages to service-area pages.
- Keep structured data accurate and aligned with visible page content.
- Improve XO Gallery/image alt text for accessibility and long-tail discovery.
- Expand service-area content only when GSC/GA4 data shows a real opportunity.
