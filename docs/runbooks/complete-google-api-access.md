# Playbook: complete Google API access (you + agent)

Ordered, copy-pasteable steps for OLS. Each task has a **stop gate**: paste
the output (redact secrets) into chat before starting the next task.

**Legend**

| Tag | Who |
|---|---|
| **YOU** | Browser, Google Console, Ads UI, GA4 UI, GTM UI, GBP invite, `.env` edits |
| **ME** | Interpret probe JSON, draft follow-ups, run repo commands when SSH to the mini is available |
| **BOTH** | You run the command on the mini (or iMac); I tell you exactly what “good” looks like |

This cloud agent **cannot** click Google, complete OAuth, or SSH to the Mac mini
unless you paste output or open a session that can reach the machine.

**Never paste** developer tokens, OAuth client secrets, refresh tokens, or the
service-account JSON into chat. Paste status JSON, HTTP codes, and redacted
`.env` *keys* (`GOOGLE_ADS_DEVELOPER_TOKEN is set: yes/no`) only.

**Machines**

| Role | Path / note |
|---|---|
| Mac mini (production) | `/Users/aiagentecosystem/services/ols` — `docker-compose.server.yml`, container `ols-api` |
| iMac / laptop (OAuth + browser) | A clone with `.env`; needed for `get_google_ads_refresh_token.py` (opens a browser) |
| GCP project | `ols-marketing-agent` (`330992031618`) |
| Service account | `ols-operations@ols-marketing-agent.iam.gserviceaccount.com` |

After any `.env` change on the mini:

```bash
cd /Users/aiagentecosystem/services/ols
docker compose -f docker-compose.server.yml up -d --force-recreate api
```

`docker compose restart api` does **not** reload env. Confirm with
`docker exec ols-api printenv GA4_PROPERTY_ID`.

Known IDs (do not treat as secrets):

| Item | Value |
|---|---|
| GA4 property | `396184354` |
| Ads customer | `548-621-3910` → env `5486213910` |
| GTM account / container | `6201388805` / `168770630` (numeric, not `GTM-XXXX`) |
| GA4 measurement ID | `G-4HSTXZKG9E` |
| GBP location | `locations/8085786647786125239` |
| Operator spreadsheet | `1nFx6g0g1ICsl9qaKM1OsReeMOP25jCx5aZyQOjbpk1A` |

Pull this branch onto the mini before Task 1 so `scripts/probe_google_apis.py` exists:

```bash
cd /Users/aiagentecosystem/services/ols
git fetch origin
git checkout cursor/google-api-access-plan-9bdf
```

---

## Task 1 — Re-verify SA APIs on the Mac mini

Goal: one JSON report for Admin, GA4 Data, GSC, GTM, Sheets, GBP. The SA
**cannot** enable APIs (`serviceusage` 403). If anything is `SERVICE_DISABLED`,
you enable it in Cloud Console.

### 1.1 Confirm the stack is up — BOTH

```bash
cd /Users/aiagentecosystem/services/ols
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep ols-api
ls -l credentials/google-service-account.json
docker exec ols-api printenv GOOGLE_APPLICATION_CREDENTIALS GA4_PROPERTY_ID GSC_SITE_URL GTM_ACCOUNT_ID GTM_CONTAINER_ID GOOGLE_SHEETS_SPREADSHEET_ID GBP_LOCATION_ID
```

**Good:** `ols-api` is running; credential file exists; `GA4_PROPERTY_ID` and
`GSC_SITE_URL` are non-empty.

**If the container is down:** `docker compose -f docker-compose.server.yml up -d`.

### 1.2 Run the probe — BOTH

Pipe the host file into the container (no image rebuild):

```bash
cd /Users/aiagentecosystem/services/ols
docker exec -i --env-file .env ols-api python3 - < scripts/probe_google_apis.py
```

Paste the JSON into chat (no secrets in this output).

### 1.3 How to read the JSON — ME

| Probe key | `OK` means | If not OK |
|---|---|---|
| `ga4_admin` | Admin API on + SA can list key events | `SERVICE_DISABLED` → 1.4. `403` → 1.5 Viewer |
| `ga4_data` | Reporting works | `403` → SA Viewer on property `396184354` |
| `gsc` | Search analytics query works | `403` → add SA as User in Search Console. Try both `https://organizinglifeservices.com/` and `www` if `site_url` mismatches |
| `gtm` | SA can list accounts | `403` → add SA in GTM User Management. Empty `env_gtm_*` → Task 3 still needs IDs on mini `.env` |
| `sheets` | Spreadsheet opens | `403` → share sheet with SA as Editor |
| `gbp` | Accounts listed | `403` / access denied → Task 4. `429` → API is on but quota/approval still noisy |
| `google_ads_env.direct_api_env_ready` | All Ads OAuth vars set | `false` is expected until Task 2 |

### 1.4 Enable a disabled API — YOU

Project must be **ols-marketing-agent**:

1. Open [Enabled APIs](https://console.cloud.google.com/apis/dashboard?project=ols-marketing-agent).
2. If a needed API is missing, [API Library](https://console.cloud.google.com/apis/library?project=ols-marketing-agent) → search → **Enable**.

Enable if missing (do not enable extras):

- Google Analytics Admin API — `analyticsadmin.googleapis.com`  
  https://console.developers.google.com/apis/api/analyticsadmin.googleapis.com/overview?project=330992031618
- Google Analytics Data API — `analyticsdata.googleapis.com`
- Google Search Console API — `searchconsole.googleapis.com`
- Tag Manager API — `tagmanager.googleapis.com`
- Google Sheets API + Google Drive API
- (GBP, already requested) My Business Account Management, Business Information, Business Profile Performance

Wait a few minutes, re-run 1.2.

The SA cannot do this step.

### 1.5 Product-side permissions — YOU (only if 403)

| Product | Where | SA role |
|---|---|---|
| GA4 | Admin → Property access management → property `396184354` | **Viewer** (Editor only later, Task 3.7) |
| Search Console | Settings → Users and permissions | **Full** or at least **Restricted** with this property |
| GTM | Admin → User Management on the OLS container | **Read** for this task; **Publish** before Task 3 publish |
| Sheets | Share `1nFx6g0g1ICsl9qaKM1OsReeMOP25jCx5aZyQOjbpk1A` | **Editor** |

### Task 1 stop gate

Paste probe JSON. **ME** confirms which lines are OK vs Console vs product-permission. Do not start Task 2 until Admin + Data + GSC are `OK` (GTM/Sheets should be `OK` too if IDs/sheet are set). GBP may stay `429`/`403`.

---

## Task 2 — Google Ads read-only (direct API)

Goal: `GET /api/seo/ads/conversion-audit` against customer `5486213910`.
GA4-derived `/api/seo/ads/pull` stays as fallback. **No mutates.**

### 2.1 Confirm MCC + API Center — YOU

1. Sign in to [Google Ads](https://ads.google.com) as `hc707consultinggroup@gmail.com`.
2. You must be on a **manager (MCC)** account to open API Center. If the OLS
   customer is standalone, create/link an MCC and put OLS under it.
3. Tools → **API Center**  
   https://ads.google.com/aw/apicenter
4. If there is no developer token yet, apply for **Basic** access.
   Paste / attach [`docs/google_ads_api_design_doc.md`](../google_ads_api_design_doc.md)
   as the tool description (internal ops dashboard, read-only GAQL, single
   customer `548-621-3910`, no third-party access).
5. Copy the developer token into a password manager. **Do not paste it in chat.**
   Tell me only: `token exists: yes/no` and `access level: test / basic / standard`.

A **test** token cannot query the live OLS customer. You need **Basic** (or
Standard) on production. Google reviews the application; keep using GA4-derived
Ads pulls until Basic is granted.

### 2.2 Enable Google Ads API on GCP — YOU

1. https://console.cloud.google.com/apis/library/googleads.googleapis.com?project=ols-marketing-agent
2. **Enable**.

This is necessary but not sufficient (token + OAuth still required).

### 2.3 OAuth Desktop client — YOU

1. https://console.cloud.google.com/apis/credentials?project=ols-marketing-agent
2. If the OAuth consent screen is not set: External (or Internal if Workspace),
   app name `OLS Internal Ops`, authorized domain not required for Desktop.
   Add test user `hc707consultinggroup@gmail.com`.
   Scope later requested by the script: `https://www.googleapis.com/auth/adwords`.
3. **Create credentials** → **OAuth client ID** → Application type **Desktop app**
   → name `OLS Ads Desktop`.
4. Copy Client ID and Client Secret into a password manager.

### 2.4 Put client id/secret on the iMac `.env` — YOU

On the **machine with a browser** (iMac/laptop), in the repo `.env`:

```bash
GOOGLE_ADS_CLIENT_ID=....apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=...
```

Do not put the refresh token yet.

### 2.5 Generate the refresh token — YOU (browser)

Must run **on the host, not in Docker** (binds `localhost:8080`):

```bash
cd /path/to/organizing-life-services-ai
set -a && source .env && set +a
python3 scripts/get_google_ads_refresh_token.py
```

If `google-auth-oauthlib` is missing: `pip install google-auth-oauthlib python-dotenv`.

1. Browser opens. Sign in as **`hc707consultinggroup@gmail.com`** (the Ads owner).
2. If Google warns the app is unverified, **Continue** (test user).
3. Allow Ads access.
4. Terminal prints `GOOGLE_ADS_REFRESH_TOKEN=...`. Save it. Do not commit `.env`.

### 2.6 Write Ads vars on the Mac mini `.env` — YOU

On the mini, add (no dashes in customer id):

```bash
GOOGLE_ADS_CUSTOMER_ID=5486213910
GOOGLE_ADS_LOGIN_CUSTOMER_ID=<MCC id digits only, or leave empty if not using MCC login>
GOOGLE_ADS_DEVELOPER_TOKEN=<from API Center>
GOOGLE_ADS_CLIENT_ID=<desktop client id>
GOOGLE_ADS_CLIENT_SECRET=<desktop client secret>
GOOGLE_ADS_REFRESH_TOKEN=<from 2.5>
```

`GOOGLE_ADS_LOGIN_CUSTOMER_ID` is required when the OLS account is accessed
**through** the MCC. It is the MCC’s customer id, not `5486213910`.

Recreate the API container (see top of this file).

Sanity (values hidden):

```bash
docker exec ols-api python3 -c "
import os
keys=['GOOGLE_ADS_CUSTOMER_ID','GOOGLE_ADS_LOGIN_CUSTOMER_ID','GOOGLE_ADS_DEVELOPER_TOKEN','GOOGLE_ADS_REFRESH_TOKEN','GOOGLE_ADS_CLIENT_ID','GOOGLE_ADS_CLIENT_SECRET']
for k in keys:
    v=os.getenv(k,'')
    print(f'{k}: {\"set\" if v.strip() else \"EMPTY\"} len={len(v.strip())}')
"
```

Paste that `set/EMPTY` table into chat.

### 2.7 Call the read-only Ads routes — BOTH

```bash
set -a && source .env && set +a
curl -sS -H "X-API-Key: $OLS_API_KEY" http://127.0.0.1:8000/api/seo/ads/account-overview | python3 -m json.tool
curl -sS -H "X-API-Key: $OLS_API_KEY" http://127.0.0.1:8000/api/seo/ads/conversion-audit | python3 -m json.tool
curl -sS -H "X-API-Key: $OLS_API_KEY" http://127.0.0.1:8000/api/seo/ads/campaigns | python3 -m json.tool
```

**Good:** `available: true` on overview; conversion audit has `findings` (may be
empty if already clean). **ME** will flag names like “page load” / `PAGE_VIEW`
/ `primary_for_goal`.

**503** `developer token / OAuth not configured` → 2.6 env not in the container.

**Auth / permission errors** → wrong Google user on OAuth, test token on a
prod account, or missing `LOGIN_CUSTOMER_ID`.

GA4 fallback still works:

```bash
curl -sS -X POST -H "X-API-Key: $OLS_API_KEY" "http://127.0.0.1:8000/api/seo/ads/pull?days_back=7"
```

### 2.8 Ads UI hygiene (no API mutate) — YOU

In Google Ads for `548-621-3910`:

1. Goals → conversions.
2. Do **not** use `page_view` or contact-page-load actions as primary.
3. Keep / map **form_submit**. Add **phone_call_clicks** only after Task 3
   shows it in GA4 Realtime.
4. Tell me which conversion actions are primary (names only).

Do **not** ask me to implement `mutate` yet.

### Task 2 stop gate

Paste: Ads env `set/EMPTY` table, `account-overview` JSON, `conversion-audit`
JSON (no tokens). **ME** summarizes bogus conversion actions. Then Task 3.

---

## Task 3 — Measurement trust (GA4 + GTM)

Goal: GA4 key events = real leads; `tel:` clicks fire `phone_call_clicks`.
Do **not** wire `keyEvents.delete` yet.

### 3.1 Unmark junk key events — YOU (GA4 UI)

1. [Google Analytics](https://analytics.google.com/) → property **396184354**.
2. **Admin** → **Data display** → **Key events**.
3. **Unmark / remove star** from:
   - `page_view`
   - `ads_conversion_Contact_Page_load_https_1`
4. **Keep** `form_submit` starred.
5. Leave `phone_call_clicks` starred **only if** you will finish 3.4–3.6 this
   session; otherwise unmark it until Realtime shows hits (avoids a dead KPI).
6. Do **not** star `purchase`, `session_start`, `scroll`, or generic `click`.

The existing event name in this property is **`phone_call_clicks`**, not
`phone_click`. Do not create a second phone event.

### 3.2 Put GTM IDs on the mini — YOU

In mini `.env` (numeric IDs):

```bash
GTM_ACCOUNT_ID=6201388805
GTM_CONTAINER_ID=168770630
GA4_MEASUREMENT_ID=G-4HSTXZKG9E
```

If discover disagrees, use discover (3.3) and overwrite.

Recreate `ols-api`. Confirm:

```bash
docker exec ols-api printenv GTM_ACCOUNT_ID GTM_CONTAINER_ID GA4_MEASUREMENT_ID
```

`docker-compose.server.yml` now passes `GA4_MEASUREMENT_ID` into the container;
recreate after pulling this branch.

### 3.3 GTM permission + discover — YOU then BOTH

**YOU:** GTM → OLS container → Admin → User Management → add
`ols-operations@ols-marketing-agent.iam.gserviceaccount.com` with **Publish**
(Edit cannot publish live).

**BOTH:**

```bash
set -a && source .env && set +a
curl -sS -H "X-API-Key: $OLS_API_KEY" http://127.0.0.1:8000/api/seo/gtm/discover | python3 -m json.tool
curl -sS -H "X-API-Key: $OLS_API_KEY" http://127.0.0.1:8000/api/seo/gtm/audit | python3 -m json.tool
```

Paste JSON. **ME** checks for `OLS - tel link click` / `OLS - phone_call_clicks`
and whether IDs match.

### 3.4 Dry-run phone-click tag — BOTH

Preferred (API, no Shopify mutation guard):

```bash
curl -sS -X POST -H "X-API-Key: $OLS_API_KEY" \
  "http://127.0.0.1:8000/api/seo/gtm/ensure-phone-clicks?dry_run=true&create_version=true" \
  | python3 -m json.tool
```

Or on a machine with `.venv` + `.env`:

```bash
set -a && source .env && set +a
.venv/bin/python data/session14_gtm_phone_clicks.py
```

Paste the plan. **ME** confirms `would_create` vs already present.

### 3.5 Apply workspace write (does not go live) — BOTH

High-stakes: you are the human confirmation. **ME** can say PASS on the dry-run
plan after reviewing JSON (that is the judge verdict for this ops change).

```bash
curl -sS -X POST -H "X-API-Key: $OLS_API_KEY" \
  "http://127.0.0.1:8000/api/seo/gtm/ensure-phone-clicks?human_confirmed=true&judge_verdict=PASS&create_version=true" \
  | python3 -m json.tool
```

Save `version.path` from the response (`accounts/.../containers/.../versions/N`).

Script equivalent (mini has no host `.venv`; use docker only if you mount the
repo — otherwise stick to curl):

```bash
OLS_ALLOW_DATA_MUTATION=1 \
OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE \
.venv/bin/python data/session14_gtm_phone_clicks.py --apply
```

### 3.6 Publish live — YOU + BOTH

Confirm in GTM UI that the version looks right. Then:

```bash
curl -sS -X POST -H "X-API-Key: $OLS_API_KEY" \
  "http://127.0.0.1:8000/api/seo/gtm/publish?human_confirmed=true&judge_verdict=PASS&version_path=accounts/ACCOUNT/containers/CONTAINER/versions/N" \
  | python3 -m json.tool
```

**YOU verify:**

1. Live pages have `tel:+17275426028` (homepage, contact, service pages).
2. GTM Preview **or** live site → click a phone number.
3. GA4 **Realtime** / DebugView → event `phone_call_clicks`.
4. Then star `phone_call_clicks` as a key event if you unmarked it in 3.1.

### 3.7 Do **not** Admin-delete key events yet

Listing via Admin is enough (`analytics.readonly` + Viewer).

Later, and only after 3.1 + 3.6 are done:

1. **YOU:** raise SA to **Editor** on property `396184354`.
2. **ME:** add gated `keyEvents.delete` (same `human_confirmed` + `judge_verdict=PASS`
   as GTM publish) using scope `https://www.googleapis.com/auth/analytics.edit`.
3. Unattended weekly jobs must never delete key events.

Until that code exists, the GA4 UI unmark in 3.1 is the cleanup.

### 3.8 Re-measure — BOTH

Immediately: Realtime is enough.

After 24–48 hours on the mini (`data/` is mounted; use `--json-only` because
`docs/` is not in the API image):

```bash
cd /Users/aiagentecosystem/services/ols
docker exec -i --env-file .env -w /app ols-api python3 /app/data/post_deploy_measurement_baseline.py --json-only
```

Paste the JSON `ga4_tracking_status` (or the full file). Trailing 28-day totals
may still include old `page_view` key events until those days age out.

### Task 3 stop gate

Paste: GTM discover/audit, ensure result, publish result, and whether Realtime
showed `phone_call_clicks`. Then Task 4.

---

## Task 4 — GBP reads only

Code is already read-only. Do **not** enable Posts / Q&A APIs.

On-site schema/contact checks **passed** on 2026-07-25. Still re-check before
reapplying — Google denied the first request for quality checks.

### 4.1 Confirm live NAP / schema — YOU

1. https://search.google.com/test/rich-results?url=https://organizinglifeservices.com/
   — `LocalBusiness` has **no** `streetAddress`; `addressRegion` FL; `areaServed` intact.
2. `https://organizinglifeservices.com/pages/contact` → **301** to `/pages/contact-us`.
3. Contact page shows labeled **mailing address** (Tampa PMB), not a street as the
   storefront.

If any of those fail, **stop**. Fix with Shopify scripts in
[`GBP_API_ACCESS_NOTES.md`](../../GBP_API_ACCESS_NOTES.md) before reapplying.
Those scripts need production `.env` + mutation guards.

### 4.2 Enable the three read APIs in GCP — YOU

If Task 1 probe showed `SERVICE_DISABLED` for GBP:

- My Business Account Management API
- My Business Business Information API
- Business Profile Performance API

Do not enable Posts, Q&A, or Verifications write surfaces.

### 4.3 Reapply for GBP API access — YOU

Previous case `7-8753000040474` was **DENIED 21 Apr 2026**. Google asked for a
cooling-off period after a denial; do not spam applications.

Use this use case (verbatim):

> Internal operations dashboard to monitor performance metrics for a single
> owned-and-operated Google Business Profile listing. No third-party access.
> The application is a self-hosted FastAPI service used exclusively by the
> business owner to pull GBP performance data into a private Google Sheet
> for review and planning.

APIs requested: **Account Management, Business Information, Performance** only.
GCP project `ols-marketing-agent` / SA `ols-operations@...`.

Tell **ME** when Google emails approval or another denial (no need to forward
the whole email).

### 4.4 Invite the SA as Manager — YOU (after approval)

In Business Profile Manager for **Organizing Life Services Estate Sale Company**:

1. Users → add `ols-operations@ols-marketing-agent.iam.gserviceaccount.com`.
2. Role **Manager** (needed for Performance API).
3. If Google sends an invitation to accept via API, say so — **ME** can call
   discover after the invite exists.

### 4.5 Set env and pull — BOTH

Mini `.env`:

```bash
GBP_LOCATION_ID=locations/8085786647786125239
GBP_ACCOUNT_ID=accounts/<from discover>
```

Recreate `ols-api`. Then:

```bash
set -a && source .env && set +a
curl -sS -X POST -H "X-API-Key: $OLS_API_KEY" http://127.0.0.1:8000/api/seo/gbp/discover | python3 -m json.tool
```

If accounts are listed, pick the OLS account name and:

```bash
curl -sS -X POST -H "X-API-Key: $OLS_API_KEY" \
  "http://127.0.0.1:8000/api/seo/gbp/discover?account_name=accounts/ACCOUNTNUM" \
  | python3 -m json.tool
```

Confirm location `locations/8085786647786125239`. Then:

```bash
curl -sS -X POST -H "X-API-Key: $OLS_API_KEY" \
  "http://127.0.0.1:8000/api/seo/gbp/pull?days_back=28" | python3 -m json.tool
```

Optional sheets push:

```bash
curl -sS -X POST -H "X-API-Key: $OLS_API_KEY" http://127.0.0.1:8000/api/seo/gbp/push-to-sheets
```

**429:** API is on but quota is tight — request quota in Cloud Console; do not
enable write APIs as a workaround.

### Task 4 stop gate

Stable `gbp/pull` with daily metrics. **No** Posts/Q&A work after that.

---

## Task 5 — Only after Tasks 1–4

Do not start these while Ads conversion audit, phone clicks, or GBP reads are
still blocked.

### 5.1 PageSpeed Insights (CWV) — YOU then ME

**YOU:** Cloud Console → enable PageSpeed Insights API → create an **API key**
restricted to `pagespeedonline.googleapis.com`. Put `PAGESPEED_API_KEY` in
mini `.env` (we will add the env slot when wiring).

**ME:** add a weekly probe for homepage, Palm Harbor, Tarpon, Pinellas hub,
contact. Optional CrUX later. No write APIs.

### 5.2 Gated Ads mutates — ME after YOU approve the design

Only after Task 2 conversion-audit is trusted.

In scope later: pause/disable page-load conversion actions; flip
`primary_for_goal`; maybe daily budget caps.

Out of scope: unattended keyword pauses, bulk account changes.

Same gates as GTM: dashboard proposal → `human_confirmed` + `judge_verdict=PASS`
→ log before/after. **ME** implements when you say to start that code.

Until then, keep using the Ads **UI** (2.8).

### 5.3 Seedance keepers → PMax via API — ME after Ads read can list assets

Requires Task 2 working so we can see current `asset_group_asset` rows.

Then, separately:

1. **YOU:** YouTube channel you control; enable YouTube Data API; OAuth (can
   reuse a Desktop client with YouTube upload scope).
2. **ME:** unlisted upload of keeper MP4s, then Ads API create YouTube video
   `Asset` and attach to PMax asset groups. Gated, never auto-upload.

Until that exists, upload videos in the Ads / YouTube UI.

### 5.4 Looker Studio — YOU only

No GCP API to enable. In Looker Studio, sign in as the owner → add data
sources **GA4 property 396184354** and the operator Google Sheet. Share the
report only with yourself.

---

## If something goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Probe `SERVICE_DISABLED` | API off in project `ols-marketing-agent` | Task 1.4 Console Enable |
| Probe `403` | SA not a user on that product | Task 1.5 |
| Ads `503` | Env missing inside container | Recreate api after `.env` edit |
| Ads auth error, test token | Token not Basic yet | Keep GA4 `/ads/pull`; wait for Basic |
| GTM 403 on publish | SA is Edit, not Publish | GTM User Management |
| `phone_call_clicks` missing | Container not published, or no `tel:` links | 3.6 |
| GBP 429 | Quota / pending access | Task 4; do not enable Posts |
| `docker compose restart` and env unchanged | Restart does not reload env | `up -d --force-recreate api` |

Related: [google-api-access.md](../google-api-access.md),
[gcp-apis-to-enable.md](gcp-apis-to-enable.md),
[google_ads_api_design_doc.md](../google_ads_api_design_doc.md),
[gtm-write-and-publish.md](gtm-write-and-publish.md),
[ga4-key-event-cleanup.md](ga4-key-event-cleanup.md),
[GBP_API_ACCESS_NOTES.md](../../GBP_API_ACCESS_NOTES.md).
