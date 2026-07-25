# Step-by-step: Improve Google Analytics for OLS

Practical guide for **Organizing Life Services** (GA4 property `396184354`).  
Goal: measure **real leads**, not page views — so SEO and ads decisions are trustworthy.

Related docs:
- [`ga4-key-event-cleanup.md`](ga4-key-event-cleanup.md) — key-event unmark steps
- [`2026-07-25-ga4-key-event-cleanup-checklist.md`](../seo-audits/2026-07-25-ga4-key-event-cleanup-checklist.md)

---

## Current state (as of 2026-07-25)

**Key events you already have**

| Event | Key event? | Receiving data? | Recommendation |
|---|---|---|---|
| `form_submit` | Yes | Yes | Keep — primary lead KPI |
| `phone_call_clicks` | Yes | No (28d) | Keep marked **only if** you fix GTM so it fires; else unmark |
| `purchase` | No | No | Leave unmarked (not an ecommerce business) |

**Good news:** `page_view` and `ads_conversion_Contact_Page_load_https_1` are no longer showing as key events. That was the biggest integrity problem. Old 28-day reports may still look inflated until those days age out.

---

## Step 1 — Decide what “success” means

For OLS, a **lead** is someone who:

1. Submits the contact form → `form_submit`
2. Clicks a phone number to call → `phone_call_clicks` (your existing name)
3. Clicks an email address → `email_click` (optional; add later)
4. Clicks a clear “Contact / Call / Get a quote” CTA → `contact_cta_click` (optional; add later)

**Not** a lead:

- Viewing any page (`page_view`)
- Landing on `/pages/contact-us` (`ads_conversion_Contact_Page_load_https_1` or similar)
- Scroll, session_start, engagement
- Shopify `purchase` (you don’t sell products as the business model)

Use **key-event count of lead events** — not total “Conversions” that mix junk — when judging SEO/ads.

---

## Step 2 — Lock key events (5 minutes in GA4)

1. Open [Google Analytics](https://analytics.google.com/) → property **Organizing Life Services**.
2. **Admin** → **Data display** → **Events** → **Key events** tab.
3. Confirm:
   - Star **on** for `form_submit`
   - Star **on** for `phone_call_clicks` only if you will complete Step 4
   - Star **off** for `purchase`
   - Star **off** for anything that means “viewed a page”
4. If `page_view` or contact-page-load events reappear as key events later, unmark them immediately.

---

## Step 3 — Use the right reports every week

In GA4:

1. **Reports** → **Engagement** → **Events**  
   - Check counts for `form_submit` and `phone_call_clicks`.
2. **Reports** → **Engagement** → **Conversions** (key events)  
   - Should roughly match lead events only — not thousands of page views.
3. Optional: **Explore** → free-form exploration  
   - Dimensions: Event name, Session source/medium, Landing page  
   - Metric: Event count  
   - Filter: Event name = `form_submit`  
   - This shows which SEO pages produce form leads.

**Do not** treat “Conversions” as meaningful until you’ve confirmed Step 2 for a full week of clean data.

---

## Step 4 — Fix phone click tracking (highest-value next upgrade)

Your Key events list marks `phone_call_clicks`, but GA4 shows **no stream data** for 28 days. Either nobody is clicking tel: links, or (more likely) GTM isn’t firing the event.

### 4a. Confirm phone links on the site

On the live site, phone numbers should be links like:

```html
<a href="tel:+17275426028">(727) 542-6028</a>
```

Check homepage, contact, and service pages.

### 4b. Fix or create the GTM tag

You can do this via the **API path** (preferred for OLS ops) or the **GTM UI path**.

#### API path (gated)

Uses fixed idempotent names (`OLS - tel link click` / `OLS - phone_call_clicks`). Full permissions, dry-run, apply, and publish details: [gtm-write-and-publish.md](gtm-write-and-publish.md).

```bash
# Dry-run plan
.venv/bin/python data/session14_gtm_phone_clicks.py

# Workspace write + create version (does not publish live)
OLS_ALLOW_DATA_MUTATION=1 \
OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE \
.venv/bin/python data/session14_gtm_phone_clicks.py --apply

# Publish after review
OLS_ALLOW_DATA_MUTATION=1 \
OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE \
.venv/bin/python data/session14_gtm_phone_clicks.py --publish --version-path accounts/.../versions/N
```

Or via API (same gates as Shopify writes):

```bash
curl -X POST -H "X-API-Key: $OLS_API_KEY" \
  "http://127.0.0.1:8000/api/seo/gtm/ensure-phone-clicks?human_confirmed=true&judge_verdict=PASS&create_version=true"

curl -X POST -H "X-API-Key: $OLS_API_KEY" \
  "http://127.0.0.1:8000/api/seo/gtm/publish?human_confirmed=true&judge_verdict=PASS&version_path=..."
```

#### GTM UI path

1. Open **Google Tag Manager** for the OLS container.
2. Find any tag that fires `phone_call_clicks` (or similar).
3. If missing, create:

| Field | Value |
|---|---|
| Tag type | GA4 Event |
| Event name | `phone_call_clicks` (keep this exact name — it already exists in GA4) |
| Trigger | Click – Just Links |
| Trigger filter | Click URL contains `tel:` |

4. **Preview** GTM → click a phone number on the site → confirm the event appears.
5. **Submit** / publish the GTM container.
6. In GA4 **Realtime** (or DebugView), confirm `phone_call_clicks` arrives within a few minutes.

### 4c. Key event star

Once you see hits in Realtime/Events, keep `phone_call_clicks` starred as a key event.

> **Naming note:** Our older runbook mentioned `phone_click`. Your property already uses `phone_call_clicks`. Prefer **fixing the existing name** over creating a second event.

---

## Step 5 — Optional: email and CTA clicks (after phone works)

Only add these if you will maintain them.

### Email clicks

| Field | Value |
|---|---|
| Event name | `email_click` |
| Trigger | Click URL contains `mailto:` |
| Then | Mark as key event in GA4 after first hits |

### Primary CTA clicks

| Field | Value |
|---|---|
| Event name | `contact_cta_click` |
| Trigger | Clicks on main “Contact / Call / Schedule” buttons (CSS class or Click Text match) |
| Then | Mark as key event after first hits |

Avoid marking generic `click` as a key event.

---

## Step 6 — Clean up junk conversions from ads / auto-events

1. In GA4 **Admin** → **Data collection and modification** / linked Google Ads (if used), ensure you are **not** optimizing ads to “contact page load” or page_view-style conversions.
2. Prefer ad conversion actions mapped to:
   - `form_submit`
   - `phone_call_clicks` (once firing)
3. Leave Shopify `purchase` unmarked unless you intentionally track product checkouts as a secondary metric.

---

## Step 7 — Verify with the repo measurement script

From a machine with `.env` + Google credentials:

```bash
set -a && source .env && set +a
.venv/bin/python data/post_deploy_measurement_baseline.py
```

**Healthy short-term read**

- `form_submit` remains the main lead_intent key event with non-zero counts.
- `page_view` is **not** classified as a key event going forward.
- `phone_call_clicks` starts appearing after Step 4 (may take a day to show in standard reports).

**Timing**

| When | What |
|---|---|
| Immediately after GTM publish | GA4 Realtime / DebugView |
| 24–48 hours | Re-run measurement baseline (smoke) |
| ~28 days | Clean comparison window for “conversions” totals |

---

## Step 8 — Ongoing monthly hygiene (15 minutes)

1. Open **Key events** — confirm only lead events are starred.
2. Open **Events** — check `form_submit` volume vs prior month (directionally).
3. Spot-check 3 landing pages that got SEO traffic — do they produce `form_submit`?
4. If `phone_call_clicks` drops to zero again, re-test tel: links + GTM Preview.
5. Re-run `post_deploy_measurement_baseline.py` after major site/SEO launches.

---

## Target end state

| Event | Key event | Purpose |
|---|---|---|
| `form_submit` | Yes | Primary lead |
| `phone_call_clicks` | Yes | Phone lead |
| `email_click` | Yes (optional) | Email lead |
| `contact_cta_click` | Yes (optional) | Mid-funnel intent |
| `page_view` | No | Traffic only |
| `purchase` | No | Ignore for OLS KPIs |
| Contact-page-load ads events | No | Not a lead |

**Business KPI formula (simple):**

> Weekly leads ≈ `form_submit` + `phone_call_clicks` (+ email/CTA if added)

Use that number — not total GA4 “Conversions” — when evaluating SEO work (homepage organizers CTR, Palm Harbor, service-area pages, etc.).

---

## If something goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Conversions still look huge | Old polluted days in 28d window | Wait for window to age; confirm Key events list is clean |
| `form_submit` stops | Form / GTM regression | GTM Preview on contact form submit |
| `phone_call_clicks` stays empty | No `tel:` links or broken trigger | Step 4 |
| Measurement script says Admin API unavailable | Expected until enabled | Enable via [gcp-apis-to-enable.md](gcp-apis-to-enable.md); UI cleanup still works |
| Ads still optimize to page views | Ads conversion action misconfigured | Remap Ads to `form_submit` |

---

## Suggested order this week

1. Confirm Key events list matches Step 2 (you’re mostly done).
2. Fix `phone_call_clicks` in GTM (Step 4) — biggest remaining gap.
3. Publish GTM → verify Realtime.
4. Re-run measurement baseline in 1–2 days.
5. Only then add email/CTA events if you still want more funnel detail.
