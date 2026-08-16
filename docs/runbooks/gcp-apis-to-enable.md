# Runbook: GCP APIs to enable for OLS

Project: **`ols-marketing-agent`** (`330992031618`)  
Service account: `ols-operations@ols-marketing-agent.iam.gserviceaccount.com`

Enabling an API in Cloud Console only turns the product **on**. Access still
requires GA4 / GSC / GTM / Sheets / GBP product-side permissions.

**Who can enable:** a Google Cloud user with **Owner** or **Editor** (or
`serviceusage.services.enable`) on project `ols-marketing-agent`. The OLS
service account does **not** have permission to enable APIs via API — use the
Console links below.

Prefer **enable what the repo already calls**. Do not enable speculative write APIs.

## Verified status (2026-07-25)

Probed with the OLS service account (live API calls, not Service Usage list):

| API | Result |
|---|---|
| Google Analytics Admin API | **OK** (keyEvents.list) |
| Google Analytics Data API | **OK** |
| Google Search Console API | **OK** |
| Tag Manager API | **OK** |
| Sheets + Drive APIs | **OK** |
| My Business Account Management | Reachable but **429 quota** (API on; access/quota still noisy) |
| Google Ads API | **Deferred** — needs developer token + OAuth (not SA enable) |

The service account **cannot** call `serviceusage.services.enable` (403). Use a human
Owner/Editor in Console if anything above regresses to `SERVICE_DISABLED`.

## Enable now (high benefit)

| API (Console name) | Service name | Why |
|---|---|---|
| **Google Analytics Admin API** | `analyticsadmin.googleapis.com` | List/inspect key events; future gated cleanup |
| **Google Analytics Data API** | `analyticsdata.googleapis.com` | GA4 reports (sessions, events, conversions) |
| **Google Search Console API** | `searchconsole.googleapis.com` | Search analytics + URL Inspection |
| **Tag Manager API** | `tagmanager.googleapis.com` | GTM audit + gated write/publish |
| **Google Sheets API** | `sheets.googleapis.com` | Push audit/dashboard rows |
| **Google Drive API** | `drive.googleapis.com` | Required by Sheets client (`gspread`) |

**Admin API activation (do first if still disabled):**  
https://console.developers.google.com/apis/api/analyticsadmin.googleapis.com/overview?project=330992031618

## Enable for GBP reads (optional)

Called by [`app/services/gbp_service.py`](../../app/services/gbp_service.py). Enabling alone may not unlock data until Google approves GBP API access.

- **My Business Account Management API** — `mybusinessaccountmanagement.googleapis.com`
- **My Business Business Information API** — `mybusinessbusinessinformation.googleapis.com`
- **Business Profile Performance API** — `businessprofileperformance.googleapis.com`

Do **not** enable GBP write surfaces (Posts, Q&A, etc.) — code is read-only.

## Deferred: Google Ads API

Not “flip a switch and done.” Needs:

1. MCC **developer token** (Ads API Center)
2. OAuth desktop client + refresh token (`GOOGLE_ADS_*` in `.env`)
3. Optionally enable **Google Ads API** (`googleads.googleapis.com`) in the library once the token exists

Keep Ads **read-only** first. See [`.env.example`](../../.env.example) and [`scripts/get_google_ads_refresh_token.py`](../../scripts/get_google_ads_refresh_token.py).

Business impact: higher than most “new SEO APIs” — protects paid spend and conversion integrity.

## Worth enabling later

Enable these only when you are ready to **wire them into OLS** (weekly job, audit, or dashboard). Flipping the Console toggle alone does nothing.

| API | When | Why for OLS |
|---|---|---|
| **PageSpeed Insights API** (`pagespeedonline.googleapis.com`) | After GTM phone clicks + key-event hygiene are solid | Lab + field Core Web Vitals on money pages (homepage, Palm Harbor, Tarpon, Pinellas hub, contact). Needs an **API key**. |
| **Chrome UX Report API** (`chromeuxreport.googleapis.com`) | Optional with PSI | Lighter origin-level field CWV; PSI alone is often enough for a weekly check. |
| **reCAPTCHA Enterprise** | Only if contact-form spam spikes | Protects `form_submit` lead quality; not a growth lever by itself. |
| **BigQuery API** | Only if you turn on GA4 → BigQuery export | Heavy analysis / custom funnels; overkill while Sheets + Postgres audits suffice. |

Priority after current stack: **Ads OAuth (deferred above) → PageSpeed Insights → optional CrUX**.

## Never enable (for this business)

These do **not** increase qualified estate-sale leads for OLS. Enabling them adds blast radius and confusion.

| API | Why skip |
|---|---|
| **Custom Search API** | Builds Programmable Search over sites you control. It does **not** provide Google organic rank tracking or competitor SERPs. Use **Search Console** for your own queries/URLs. |
| **Google Indexing API** | Ordinary sites are usually ineligible. OLS uses GSC URL Inspection + **IndexNow** instead. |
| **Analytics Reporting API (Universal Analytics)** | Obsolete; GA4 Data API replaces it. |
| **Cloud Natural Language / Cloud Translation** | Repo already uses LLMs for copy and review. |
| **Cloud Vision** | Image work uses **Claude Vision**, not Google Vision. |
| **Maps / Places / Geocoding** | Little upside vs GBP reads + on-site LocalBusiness schema. |
| **Knowledge Graph Search API** | Niche entity SEO; low ROI for a local service business. |
| **YouTube Data API** | Not a primary OLS channel. |
| **Merchant Center / Content API for Shopping** | Fee/utility products are internal; SEO targets service pages, not product catalog. |
| **DV360 / Campaign Manager 360 / Search Ads 360** | Not in the media mix. |
| **Safe Browsing / Web Risk** | Ops curiosity only; not a lead driver. |
| Broad **Drive** write beyond Sheets, random Marketing Platform leftovers | Unused surface area. |

Rule of thumb: if an API does not improve **phone/form leads**, **measurement trust**, **local visibility**, or **Ads spend efficiency**, leave it disabled.

## Console walkthrough

1. [API Library](https://console.cloud.google.com/apis/library?project=ols-marketing-agent) — project must be `ols-marketing-agent`
2. Search each API name → **Enable** (or confirm already Enabled)
3. Or audit: [Enabled APIs dashboard](https://console.cloud.google.com/apis/dashboard?project=ols-marketing-agent)
4. After Admin API: wait 2–5 minutes, then verify (below)
5. If Admin returns permission errors: GA4 → Admin → Property access management → SA as **Viewer** on property `396184354` (Editor only for future key-event deletes)

## Verify Admin API (Mac mini)

There is no host `.venv` on the mini — use the API container:

```bash
cd /Users/aiagentecosystem/services/ols
docker exec -i --env-file .env ols-api python3 <<'PY'
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

creds_path = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS",
    "/app/credentials/google-service-account.json",
)
prop = os.environ["GA4_PROPERTY_ID"]
creds = service_account.Credentials.from_service_account_file(
    creds_path,
    scopes=["https://www.googleapis.com/auth/analytics.readonly"],
)
svc = build("analyticsadmin", "v1beta", credentials=creds, cache_discovery=False)
try:
    resp = svc.properties().keyEvents().list(
        parent=f"properties/{prop}", pageSize=200
    ).execute()
except Exception as e:
    print("ADMIN_FAIL:", e)
    raise SystemExit(1)
print("ADMIN_OK")
print("key_events:", [e.get("eventName") for e in resp.get("keyEvents", [])])
PY
```

| Result | Meaning |
|---|---|
| `ADMIN_OK` | Admin API enabled + SA can list key events |
| `SERVICE_DISABLED` | Still need Enable in Console |
| Permission error | Raise SA to Viewer on the GA4 property |

## Related

- [google-api-access.md](../google-api-access.md) — live vs blocked access and the completion plan
- [ga4-key-event-cleanup.md](ga4-key-event-cleanup.md) — UI cleanup + Admin API note
- [gtm-write-and-publish.md](gtm-write-and-publish.md) — GTM SA Publish permission
- [improve-google-analytics.md](improve-google-analytics.md) — measurement guide
