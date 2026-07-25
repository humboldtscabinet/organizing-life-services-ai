# Operator checklist: GA4 key-event cleanup (2026-07-25)

Do this in the Google Analytics UI (Admin API is disabled in GCP for this project).

## Steps

1. Open GA4 property **396184354** → **Admin** → **Data display** → **Key events**.
2. **Remove/unmark** as key events:
   - `page_view`
   - `ads_conversion_Contact_Page_load_https_1`
3. **Keep** `form_submit` as a key event.
4. If these events already exist in the property, **mark** as key events:
   - `phone_click`
   - `email_click`
   - `contact_cta_click`
5. If those three do not exist yet, create them in GTM first (see [`ga4-key-event-cleanup.md`](../runbooks/ga4-key-event-cleanup.md)), wait for hits, then mark them.

## Verify

After 24–48 hours:

```bash
set -a && source .env && set +a
.venv/bin/python data/post_deploy_measurement_baseline.py
```

Expect: future windows stop counting `page_view` / contact-page-load as key events. The trailing 28-day window may still look inflated until old days age out.

**Scheduled re-checks:** 2026-07-27 (smoke) and 2026-08-22 (clean-ish window).

Full runbook: [`ga4-key-event-cleanup.md`](../runbooks/ga4-key-event-cleanup.md).
