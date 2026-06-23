# Runbook: Clean Up GA4 Key Events

Use this when `data/post_deploy_measurement_baseline.py` reports that passive
events are counted as GA4 key events/conversions.

## Goal

GA4 should count only real lead intent as key events:

- `form_submit`
- `phone_click`
- `email_click`
- `contact_cta_click`

GA4 should **not** count passive behavior as key events:

- `page_view`
- `session_start`
- `first_visit`
- `user_engagement`
- `scroll`
- `ads_conversion_Contact_Page_load_https_1`
- any event whose meaning is "visited the contact page" rather than "submitted/clicked/contacted"

## Current Problem Found

The 2026-06-23 measurement baseline found:

- `page_view`: 1,287 key events
- `ads_conversion_Contact_Page_load_https_1`: 73 key events
- `form_submit`: 8 key events

That makes the reported conversion count look much larger than real lead volume.
Do not use GA4 conversion/key-event totals as a business KPI until this is fixed.

## Cleanup Steps In GA4 UI

1. Open Google Analytics.
2. Select property `396184354`.
3. Go to **Admin**.
4. Under **Data display**, open **Key events**.
5. Remove/unmark these as key events:
   - `page_view`
   - `ads_conversion_Contact_Page_load_https_1`
6. Keep `form_submit` as a key event.
7. If present, mark these as key events:
   - `phone_click`
   - `email_click`
   - `contact_cta_click`
8. If `phone_click`, `email_click`, or `contact_cta_click` do not exist yet, create them in GTM first and wait for GA4 to receive them before marking them as key events.

## GTM Event Naming Standard

Use these exact event names so reports stay stable:

| User action | GA4 event name |
|---|---|
| Contact form successfully submitted | `form_submit` |
| Phone number clicked | `phone_click` |
| Email address clicked | `email_click` |
| Contact CTA clicked | `contact_cta_click` |

Avoid generic `click` as a key event. If GTM emits a generic click event, use
parameters for diagnostics but create a specific GA4 event for reporting.

## Verification

Immediately after the GA4 UI cleanup:

```bash
python data/post_deploy_measurement_baseline.py
```

Expected short-term result:

- `page_view` key events drop to `0` in future data.
- `ads_conversion_Contact_Page_load_https_1` key events drop to `0` in future data.
- The report may still show old bad key events for the 28-day window until the window ages out.

Best verification window:

- Re-run after 24-48 hours.
- Re-run again after 28 days for a fully clean comparison window.

## API Cleanup Option

The Google Analytics Admin API can list, create, patch, and delete key-event
resources. Listing key events is read-only, while deleting a key event requires
the `analytics.edit` OAuth scope.

In this repo's current setup, the GA4 Data API works, but the Analytics Admin API
is disabled in the GCP project. Until it is enabled, use the GA4 UI steps above.

To enable future API-based inspection:

1. In Google Cloud Console, enable **Google Analytics Admin API** for the service-account project.
2. Confirm the service account has GA4 property access.
3. Keep API cleanup behind an explicit human confirmation; do not delete key events automatically from weekly jobs.

Reference:

- Google Analytics Admin API `properties.keyEvents`
- Google Analytics Admin API `properties.keyEvents.delete`
