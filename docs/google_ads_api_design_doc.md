# OLS Internal Ops Dashboard — Google Ads API Design Document

**Applicant:** Organizing Life Services LLC
**Tool name:** OLS Internal Ops Dashboard
**Access tier requested:** Basic
**Use case:** Single-tenant, internal-only reporting and conversion-action auditing for our own Google Ads account (customer ID 548-621-3910).

---

## 1. Architecture

Self-hosted, single-server deployment. All components run as Docker containers on one machine managed by the company owner. No multi-tenant infrastructure, no public-facing user accounts, no third-party data sharing.

| Component | Technology | Purpose |
|---|---|---|
| Backend API | FastAPI 0.115 (Python 3.11) | Business logic, Google API integration |
| Database | Postgres 16 | Stores pulled metrics for reporting |
| Frontend | Vite + React | Internal dashboard, API-key protected |
| Scheduler | n8n | Daily scheduled data pulls |
| Reverse proxy | nginx | Static dashboard + API routing |

The dashboard reads from Postgres only; it never calls the Google Ads API directly. All Ads API traffic originates from the FastAPI backend.

## 2. Google Ads integration

- **Client library:** Official `google-ads` Python client v25.x
- **Authentication:** OAuth2 with a long-lived refresh token issued to the company owner's Google account, which is the owner of the linked Ads customer.
- **Credential storage:** Developer token, OAuth client ID/secret, and refresh token are stored in environment variables on the server (`.env`, gitignored). Credentials are never sent to the browser or logged.
- **Source module:** `app/services/google_ads_service.py` — wraps `GoogleAdsService.search` queries and exposes a small set of read functions to the rest of the application.

## 3. API operations used (read-only, current scope)

The tool issues GAQL `SELECT` queries via `GoogleAdsService.search` against the following resources:

- `customer` — basic account info (descriptive_name, currency_code, time_zone, manager flag)
- `campaign` + `campaign_budget` — campaign list with status, advertising_channel_type, bidding_strategy_type, daily budget (amount_micros)
- `ad_group` and `ad_group_ad` — ad group performance
- `ad_group_criterion` — keyword-level performance
- `conversion_action` — conversion-action configuration audit (id, name, status, type, category, primary_for_goal, counting_type, click_through_lookback_window_days, value_settings)
- `metrics` — clicks, impressions, cost_micros, conversions, conversions_value, ctr, average_cpc — joined to the entities above over date ranges (typically last 30 days)

No `mutate` operations are issued at this time.

## 4. Call frequency and volume

- One scheduled pull per day via n8n (campaign + ad-group + keyword performance for the trailing 30 days).
- On-demand audits triggered manually from the dashboard by the owner.
- Estimated steady-state daily volume: **under 50 operations** against a single customer ID. Far below Basic-access daily limits.
- All requests are rate-limit aware; the client library's built-in retry/backoff is used.

## 5. Data flow

```
+----------------+     daily +-----------------+     +--------------+
| Google Ads API | <-------- | FastAPI backend | --> | Postgres DB  |
+----------------+   queries +-----------------+ ins +--------------+
                                     ^                       |
                                     |                       v
                              +-------------+         +--------------+
                              | Owner only  | <------ | React dash   |
                              | (browser)   |  reads  | (API-key)    |
                              +-------------+         +--------------+
```

Pulled rows are stored in a `google_ads_data` table (one row per campaign / ad-group / keyword / date) and a `workflow_logs` table for run audit trail.

## 6. Write operations (future scope)

Not in scope today. Any future write capability (e.g. pausing wasteful keywords, adjusting daily budgets, editing conversion-action settings) will be:

1. Surfaced in the dashboard as a **proposed change**.
2. Require **explicit human approval** (a button click by the owner) before any `mutate` request is sent.
3. Logged to the `workflow_logs` table with before/after state.

## 7. Security

- API key authentication (`X-API-Key` header) on every backend endpoint except `/health`.
- All secrets in `.env` (gitignored); no credentials in source control.
- HTTPS in production via reverse proxy.
- No third-party data sharing. No resale of API access. No multi-account brokering.
- Service is on a private network; the dashboard frontend is only reachable by the company owner.

## 8. Compliance

The tool will follow the Google Ads API Terms of Service, the Required Minimum Functionality (RMF) policy, and the Google Ads API policies on data handling. Specifically, the tool will not:

- Bulk-create accounts.
- Scrape competitor or third-party data.
- Expose Ads API data to anyone outside Organizing Life Services LLC.
- Resell, sublicense, or repackage Ads API access.

---

**Contact:** the email associated with the manager (MCC) account submitting this application.
