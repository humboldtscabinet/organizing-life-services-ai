# Runbook: Dashboard Operational Alerts

The private dashboard has an operational alert inbox for server, backup, LLM,
SEO-audit, and integration health checks.

## Endpoint

Create or update an alert:

```bash
curl -X POST http://127.0.0.1:8000/api/dashboard/alerts \
  -H "X-API-Key: $OLS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "n8n",
    "severity": "WARNING",
    "title": "Backup verification failed",
    "message": "Postgres restore verifier returned non-zero.",
    "fingerprint": "backup:postgres",
    "details": {
      "script": "infra/backup/verify_postgres_backup.sh"
    }
  }'
```

Severity values:

- `INFO`
- `WARNING`
- `CRITICAL`

Status values:

- `open`
- `acknowledged`
- `dismissed`
- `resolved`

## Fingerprints

Use a stable `fingerprint` for recurring checks so repeated failures update the
same open alert instead of creating duplicates.

Suggested fingerprints:

- `stack:verify_stack`
- `backup:postgres`
- `backup:n8n`
- `backup:offsite_sync`
- `llm:ollama`
- `seo:weekly_audit`
- `ga4:key_event_trust`
- `gbp:api_access`

When the same active fingerprint is seen again, the API reopens the alert,
updates its message/details, and increments `occurrence_count`.

## Payload Hygiene

The alert API redacts obvious secret-like fields and truncates large strings
before storage, but callers should still avoid sending raw `.env` output,
tokens, cookies, or full command logs. Prefer short summaries plus the script
name, exit code, and the last useful non-secret error line.

## Dashboard Actions

The dashboard supports:

- acknowledge: "I saw this, keep it visible if it happens again"
- dismiss: "Hide this alert"
- resolve: available by API for future automation after a check passes

For now, keep the dashboard private through localhost, SSH tunnel, or Tailscale.
