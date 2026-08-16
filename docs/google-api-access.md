# Google marketing API access — status and completion plan

Canonical inventory of what OLS can call today, what is blocked, and what
“full functionality” actually means for this business. Companion runbook:
[gcp-apis-to-enable.md](runbooks/gcp-apis-to-enable.md).

**This cloud agent cannot live-probe Google.** Status below is from in-repo
clients, `.env.example`, GitHub Actions secrets, and the last operator probes
(especially 2026-07-25). Re-run the Mac mini verify snippet in the GCP runbook
before treating Admin / GBP as current.

OLS is a **single-tenant internal ops** stack. “Complete API access” means
trusted **reads** on every channel that drives leads or spend, plus **gated
writes** only where a human should approve a change. It does **not** mean
enabling DV360, SA360, Campaign Manager, Merchant Center, or unattended
mutates.

---

## Identity

| Piece | Value |
|---|---|
| GCP project | `ols-marketing-agent` (`330992031618`) |
| Service account | `ols-operations@ols-marketing-agent.iam.gserviceaccount.com` |
| Key file | `credentials/google-service-account.json` (gitignored); `GOOGLE_APPLICATION_CREDENTIALS` |
| Owner Google account | `hc707consultinggroup@gmail.com` (Ads OAuth consent) |
| Site | `https://organizinglifeservices.com` (`GSC_SITE_URL` in `.env.example` uses `www`) |
| GA4 property | `396184354` |
| Ads customer | `548-621-3910` (`GOOGLE_ADS_CUSTOMER_ID` without dashes: `5486213910`) |
| GBP listing | `locations/8085786647786125239` |
| Operator spreadsheet | Sheets ID in `.env` / onboarding (`GOOGLE_SHEETS_SPREADSHEET_ID`) |

**Two auth models**

1. **Service account** — Search Console, GA4 Data (+ Admin when enabled), GTM, Sheets/Drive, GBP (if Google approves the APIs). Product-side: add the SA email as a user on each property.
2. **User OAuth refresh token** — Google Ads only. Needs a developer token from an MCC (manager) account. The SA cannot replace this.

GitHub Actions (daily snapshot + weekly audit) only has
`GOOGLE_SERVICE_ACCOUNT_JSON`, `GA4_PROPERTY_ID`, `GSC_SITE_URL` (optional
`GBP_LOCATION_ID`, `GTM_ACCOUNT_ID`, `GTM_CONTAINER_ID`). **No Ads OAuth
secrets in Actions.**

---

## Status matrix

Legend: **Live** = code + GCP API + product permission have worked in an
operator environment. **Code ready / access blocked** = client exists but
credentials, Google approval, or a Console toggle is missing. **Out of mix** =
do not enable.

| Product | Auth | GCP API | Product permission | In-repo surface | Read | Write | Live status |
|---|---|---|---|---|---|---|---|
| **Search Console** | SA `webmasters.readonly` | `searchconsole.googleapis.com` | SA is a User on the property | `gsc_service.py`, URL Inspection, deep audit, daily snapshot | Search analytics + inspect | None (by design) | **Live** (Actions + Mac mini audits) |
| **GA4 Data API** | SA `analytics.readonly` | `analyticsdata.googleapis.com` | SA Viewer on property `396184354` | `ga4_service.py`, Ads-via-GA4, measurement baseline | Reports | None | **Live** |
| **GA4 Admin API** | SA `analytics.readonly` today | `analyticsadmin.googleapis.com` | Viewer to list; Editor + `analytics.edit` to delete key events | `post_deploy_measurement_baseline.py` list-only | Key-event config list | Not wired | **Flaky** — 2026-07-25 morning baseline: disabled; same-day GCP runbook probe: `keyEvents.list` OK. Re-verify. |
| **Google Ads (via GA4)** | Same as GA4 Data | (none extra) | Ads linked to GA4 | `google_ads_service.py` `pull_google_ads_data` | Campaign / keyword / cost as GA4 sees them | None | **Live** (proxy only) |
| **Google Ads API** | OAuth `adwords` + developer token | `googleads.googleapis.com` | Owner on customer `5486213910`; MCC token | `google_oauth.py`, `list_campaigns`, `audit_conversion_actions` | GAQL `SELECT` only | None (future: gated mutate) | **Not configured** — `GOOGLE_ADS_DEVELOPER_TOKEN` / refresh token empty; this agent has no `GOOGLE_ADS_*` |
| **Tag Manager** | SA `tagmanager.readonly` + edit/publish scopes | `tagmanager.googleapis.com` | SA user with **Publish** for live publish | `gtm_service.py`; gated `/api/seo/gtm/*` | Audit container | Workspace + version + publish (human + judge gates) | **Read live** (2026-07-25: 5 tags). Writes need Publish permission + `GTM_*` IDs on the **server** `.env` |
| **Sheets + Drive** | SA `spreadsheets` + `drive` | `sheets` + `drive` | Spreadsheet shared with SA | `sheets_service.py` | Spreadsheet | Push GSC/GA4/Ads/GBP/audit tabs | **Live** when spreadsheet is shared |
| **Business Profile** | SA `business.manage` | Account Management, Business Information, Performance | Google **API access approval** + SA invited as Manager | `gbp_service.py` (read-only) | Accounts, locations, daily metrics | None (by design) | **Blocked** — access request **denied** 2026-04-21 (case `7-8753000040474`). 2026-07-25 pull: API **429**. On-site NAP/schema checks **pass** |
| **PageSpeed / CrUX** | API key (not SA) | `pagespeedonline` / `chromeuxreport` | None | Not wired | Lab/field CWV | n/a | **Not enabled** — optional later |
| **IndexNow** | Public HTTP (Bing/Yandex) | n/a | Key page on the Shopify host | `data/session8_*`, later session scripts | n/a | URL submit | **Live** as a **non-Google** ping. Not a Google API |
| **YouTube Data** | OAuth | `youtube.googleapis.com` | Channel owner | Not wired | n/a | Upload unlisted videos for PMax | **Not enabled** — only needed if Ads API should attach Seedance keepers as video assets |
| **DV360 / CM360 / SA360** | — | — | — | — | — | — | **Out of mix** |
| **Merchant Center** | — | — | — | — | — | — | **Out of mix** (fee products are not a catalog) |
| **Google Indexing API** | — | — | Usually ineligible | — | — | — | **Skip** — use GSC Inspection + IndexNow |
| **Looker Studio** | Owner's Google login | n/a | Connect GA4/Sheets in UI | No code | Dashboards | n/a | UI-only; no API work required |

---

## What each live API can actually do

### Search Console (read complete for OLS)

Implemented:

- `searchanalytics.query` (query × page × date) into Postgres
- URL Inspection (`urlInspection.index.inspect`) — Google's own index verdict
- Deep audit / daily snapshot / GitHub Actions

Not implemented (and not needed for current ops):

- `webmasters` (write) sitemap submit — Shopify already emits the sitemap
- Search Analytics API write, sitemaps delete, inspect-as-Google crawl request

**Gap to “full GSC”:** none for OLS. Keep read-only. Confirm the SA user is on
**both** `https://organizinglifeservices.com/` and `https://www.organizinglifeservices.com`
if property URLs differ.

### GA4 Data (read complete for reporting)

Implemented: sessions, users, page views, landing pages, source/medium,
key-event / conversion breakdowns, Google Ads dimensions
(`sessionGoogleAdsCampaignName`, `advertiserAdCost`, etc.).

**Gaps:** no Measurement Protocol, no BigQuery export, no Data Import. Those
are optional. Business KPI still depends on **which events are marked key
events** (Admin / UI), not on more Data API metrics.

### GA4 Admin (read partial; write not wired)

Code can `properties.keyEvents.list`. It cannot create/patch/delete key events.

To finish:

1. Confirm `analyticsadmin.googleapis.com` stays enabled (the 2026-07-25
   baseline and the GCP runbook disagree — probe again).
2. Keep SA as **Viewer** for list-only weekly audits.
3. Only if you want API cleanup instead of the GA4 UI: grant SA **Editor**,
   add scope `https://www.googleapis.com/auth/analytics.edit`, and put
   `keyEvents.delete` behind the same high-stakes gates as GTM publish.
4. Unmark `page_view` and `ads_conversion_Contact_Page_load_https_1` in the UI
   regardless — that is the conversion-trust fix, API or not.

### Google Ads

**Today:** paid performance is **GA4-derived**. That is enough for spend and
clicks as Analytics attributes them. It cannot:

- List or disable conversion actions (the page-load “conversion” problem)
- Read campaign budgets, bidding, asset groups, or PMax video assets
- Confirm which Seedance MP4s are actually in Ads

**Direct API (code ready, credentials missing):**

- `GoogleAdsService.search` on `customer`, `campaign`, `campaign_budget`,
  `conversion_action`, plus the GA4 pull path
- Routes: `GET /api/seo/ads/account-overview`, `/campaigns`, `/conversion-audit`
- Setup: [google_ads_api_design_doc.md](google_ads_api_design_doc.md) +
  `scripts/get_google_ads_refresh_token.py` (scope `adwords`)

**Writes (not built):** any `mutate`. Design doc says future writes are
proposed-in-dashboard → owner click → log before/after. Do not unattended-pause
keywords.

**PMax video upload (not built):** Ads video assets are YouTube IDs. A complete
path is: YouTube Data API (unlisted upload) → Ads API `Asset` / `asset_group_asset`
create. That is a separate gated project after read-only Ads works.

### Tag Manager

Read: discover accounts/containers, list tags/triggers/variables, audit.

Write (gated): idempotent `OLS - tel link click` / `OLS - phone_call_clicks`,
create container version, publish live. Requires SA **Publish** on the container
and numeric `GTM_ACCOUNT_ID` / `GTM_CONTAINER_ID` (not `GTM-XXXX`).

**Gap:** iMac vs Mac mini `.env` split was flagged 2026-06-24 (GTM IDs on iMac,
not mini). Server runtime must have the IDs or weekly jobs cannot audit/publish.

### Google Business Profile

Code is **read-only** on purpose (accounts, locations, daily impressions / calls /
website clicks). Writes (posts, Q&A, review replies) are not in the repo and
should stay that way until read works.

Access request **denied** 21 Apr 2026. On-site schema/contact remediation for
reapplication **passed** in the 2026-07-25 baseline (`streetAddress` absent,
mailing address labeled). Remaining: Google reapproval + invite SA as Manager
+ quota (last call was HTTP 429). See [GBP_API_ACCESS_NOTES.md](../GBP_API_ACCESS_NOTES.md).

### Sheets

Write of operator tabs is the intended “write.” Broad Drive write is out of
scope. Share the dashboard spreadsheet with the SA as Editor.

---

## Completion plan

Do these in order. Each step is a permission or credential change, then a
verify command. Do not enable unused Marketing Platform products.

### 1. Re-verify what the SA can call (Mac mini)

Run the Admin probe in [gcp-apis-to-enable.md](runbooks/gcp-apis-to-enable.md).
Also hit GSC searchanalytics, GTM `accounts.list`, Sheets open, and GBP
`accounts` list. Record `OK` / `SERVICE_DISABLED` / `403` / `429`.

Fix Console enables only if something regresses to `SERVICE_DISABLED`. The SA
cannot enable APIs itself (`serviceusage` 403).

### 2. Google Ads read-only (highest remaining gap)

This unblocks conversion-action audit and PMax asset inventory. GA4-derived
pulls stay as fallback.

1. Ads account must sit under an **MCC**. Open API Center on the MCC; apply
   for a **Basic** developer token using [google_ads_api_design_doc.md](google_ads_api_design_doc.md)
   (already written as the application packet).
2. Enable **Google Ads API** on `ols-marketing-agent`.
3. Create an OAuth **Desktop** client; put `GOOGLE_ADS_CLIENT_ID` /
   `GOOGLE_ADS_CLIENT_SECRET` in server `.env`.
4. On a machine with a browser, as `hc707consultinggroup@gmail.com`:

   ```bash
   python scripts/get_google_ads_refresh_token.py
   ```

5. Set `GOOGLE_ADS_CUSTOMER_ID=5486213910`, `GOOGLE_ADS_REFRESH_TOKEN=...`,
   `GOOGLE_ADS_DEVELOPER_TOKEN=...`. Set `GOOGLE_ADS_LOGIN_CUSTOMER_ID` to the
   MCC id if the customer is accessed through the manager.
6. Recreate the API container so `.env` loads.
7. Verify: `GET /api/seo/ads/account-overview` and `/api/seo/ads/conversion-audit`.
8. In Ads UI (or later a gated mutate): stop optimizing to contact-page-load /
   page_view conversion actions; keep `form_submit` and (once GTM fires)
   `phone_call_clicks`.

Do **not** add Ads mutate until this read audit is in the weekly job.

### 3. GA4 key events + GTM phone clicks (measurement trust)

Independent of Ads, this is what makes “conversions” mean leads.

1. GA4 UI: unmark `page_view` and `ads_conversion_Contact_Page_load_https_1`;
   keep `form_submit`; keep `phone_call_clicks` only after it fires.
   Checklist: [ga4-key-event-cleanup.md](runbooks/ga4-key-event-cleanup.md).
2. Put `GTM_ACCOUNT_ID`, `GTM_CONTAINER_ID`, `GA4_MEASUREMENT_ID` on the
   **Mac mini** `.env`. Confirm SA has **Publish**.
3. Dry-run then gated apply: [gtm-write-and-publish.md](runbooks/gtm-write-and-publish.md).
4. Re-run `data/post_deploy_measurement_baseline.py` after Realtime shows
   `phone_call_clicks`.
5. Optional later: Admin API delete of leftover key events, gated, with
   `analytics.edit`.

### 4. GBP read (local visibility)

1. Confirm live schema still has **no** `streetAddress` and contact shows the
   labeled Tampa PMB ([GBP_API_ACCESS_NOTES.md](../GBP_API_ACCESS_NOTES.md)).
2. Reapply for Account Management + Business Information + Performance only.
   Use the internal-ops use-case text in that file. Do not request Posts/Q&A.
3. After approval: invite the SA as Manager; set `GBP_ACCOUNT_ID` /
   `GBP_LOCATION_ID`; `POST /api/seo/gbp/discover` then `/gbp/pull`.
4. If 429 persists, request quota in Cloud Console; keep retries/backoff in
   the client.

No GBP write APIs until daily metrics pull is stable.

### 5. Optional after 2–4

| Work | When it is worth it |
|---|---|
| PageSpeed Insights API key + weekly CWV on money pages | After phone-click measurement works |
| Ads `mutate` for conversion-action status / primary-for-goal | After read-only audit is trusted; same human+judge gates as GTM |
| YouTube unlisted upload + Ads `asset_group_asset` for Seedance keepers | After Ads read can list current PMax assets; never auto-upload |
| GA4 → BigQuery | Only if Sheets + Postgres stop being enough |
| Looker Studio | Owner connects GA4/Sheets in the UI; no GCP enable |

### 6. Never enable for OLS

Custom Search, Indexing API, Universal Analytics Reporting, Maps/Places,
Cloud Vision/NL/Translate, Merchant Center, DV360, Campaign Manager 360,
Search Ads 360, Web Risk. Reasons: [gcp-apis-to-enable.md](runbooks/gcp-apis-to-enable.md).

---

## Verify commands (after credentials exist)

```bash
# Mac mini — Admin list (Viewer is enough)
docker exec -i --env-file .env ols-api python3  # see gcp-apis-to-enable.md snippet

# Direct Ads (503 until OAuth + token exist)
curl -H "X-API-Key: $OLS_API_KEY" http://127.0.0.1:8000/api/seo/ads/conversion-audit

# GTM
curl -H "X-API-Key: $OLS_API_KEY" http://127.0.0.1:8000/api/seo/gtm/discover
curl -H "X-API-Key: $OLS_API_KEY" http://127.0.0.1:8000/api/seo/gtm/audit

# GBP (expect 403/429 until Google approves)
curl -X POST -H "X-API-Key: $OLS_API_KEY" http://127.0.0.1:8000/api/seo/gbp/discover
```

GitHub Actions will keep working for GSC + GA4 Data without Ads or GBP.

---

## Related

- [gcp-apis-to-enable.md](runbooks/gcp-apis-to-enable.md) — Console toggles
- [google_ads_api_design_doc.md](google_ads_api_design_doc.md) — Ads Basic-access application
- [gtm-write-and-publish.md](runbooks/gtm-write-and-publish.md)
- [ga4-key-event-cleanup.md](runbooks/ga4-key-event-cleanup.md)
- [GBP_API_ACCESS_NOTES.md](../GBP_API_ACCESS_NOTES.md)
- [phase1-automation.md](runbooks/phase1-automation.md)
