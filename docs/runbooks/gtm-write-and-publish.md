# Runbook: GTM write and publish (gated)

Upgrade path from read-only GTM audit to **workspace edits + version create**, with
**live publish** behind the same high-stakes gates used for Shopify writes.

## Prerequisites (operator)

1. Service account email (from `credentials/google-service-account.json` → `client_email`) is a GTM user on the OLS container with **Publish** permission (Edit alone cannot publish live).
2. `.env` has numeric IDs (not `GTM-XXXX`):

```bash
GTM_ACCOUNT_ID=...
GTM_CONTAINER_ID=...
# Optional but recommended for GA4 Event tags:
GA4_MEASUREMENT_ID=G-XXXXXXXX
```

3. Discover IDs if unknown:

```bash
curl -H "X-API-Key: $OLS_API_KEY" http://127.0.0.1:8000/api/seo/gtm/discover
```

4. OAuth scopes used by [`app/services/gtm_service.py`](../../app/services/gtm_service.py):
   - `tagmanager.readonly`
   - `tagmanager.edit.containers`
   - `tagmanager.edit.containerversions`
   - `tagmanager.publish`

## Safety model

| Action | Gate |
|---|---|
| Read / audit | API key only |
| Ensure phone-click tag (workspace + create version) | `human_confirmed=true` + `judge_verdict=PASS` |
| Publish version live | Same gates (separate endpoint) |

Unattended weekly jobs must **not** call publish. n8n may create dashboard
tasks; it must **never** call `POST /api/dashboard/tasks/{id}/apply`.

Dashboard Apply (preferred operator path): generate tasks, then Apply on the
card. Ensure writes the workspace and creates a version; live publish is a
**separate** follow-up task with a frozen `version_path`. If
`phone_call_clicks` already fired this week, the detector no-ops.

## Idempotent names

- Trigger: `OLS - tel link click`
- Tag: `OLS - phone_call_clicks`
- GA4 event name: `phone_call_clicks` (matches existing GA4 key event)

## Operator script (Mac mini / laptop)

Dry-run (default):

```bash
set -a && source .env && set +a
.venv/bin/python data/session14_gtm_phone_clicks.py
```

Apply workspace write + create version (does **not** publish):

```bash
OLS_ALLOW_DATA_MUTATION=1 \
OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE \
.venv/bin/python data/session14_gtm_phone_clicks.py --apply
```

Publish a version (script flag or API):

```bash
OLS_ALLOW_DATA_MUTATION=1 \
OLS_DATA_MUTATION_CONFIRM=I_HAVE_REVIEWED_THIS_PRODUCTION_WRITE \
.venv/bin/python data/session14_gtm_phone_clicks.py --apply --publish
```

## API

```bash
# Workspace ensure + version (no live publish)
curl -X POST -H "X-API-Key: $OLS_API_KEY" \
  "http://127.0.0.1:8000/api/seo/gtm/ensure-phone-clicks?human_confirmed=true&judge_verdict=PASS&create_version=true"
# → { "status": "success", "result": { "trigger": ..., "tag": ..., "version": {...} } }

# Publish
curl -X POST -H "X-API-Key: $OLS_API_KEY" \
  "http://127.0.0.1:8000/api/seo/gtm/publish?human_confirmed=true&judge_verdict=PASS&version_path=accounts/.../versions/..."
# → { "status": "success", "result": { "status": "published", "version_path": "..." } }
```

## Verify

1. GTM UI → workspace shows trigger/tag (or Versions after create).
2. After publish: GTM Preview or live site → click a `tel:` link.
3. GA4 **Realtime** / DebugView → event `phone_call_clicks`.
4. After 24–48h: `python data/post_deploy_measurement_baseline.py`

## If something goes wrong

| Symptom | Fix |
|---|---|
| 403 / permission denied on create | Raise SA to **Publish** in GTM User Management |
| Tag created but no measurement ID | Set `GA4_MEASUREMENT_ID` or ensure a GA4 Config / Google tag exists in the container |
| Event still missing in GA4 | Confirm live container published; hard-refresh site; check Preview |
| Duplicate tags | Re-run ensure — it matches by fixed OLS names and updates in place |
