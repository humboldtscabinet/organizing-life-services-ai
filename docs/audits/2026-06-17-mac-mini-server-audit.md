# Mac Mini Server Audit - 2026-06-17

## Overall Status

**Pass with warnings.**

The Mac mini is reachable over SSH, running the OLS stack from the expected repo
path, serving API/dashboard/n8n locally, preserving Postgres from LAN exposure,
running Ollama with both Gemma models, and producing verified Postgres/n8n
backups. A real oversight was found and fixed during the audit: the launchd
backup job lacked Homebrew/OrbStack paths, so scheduled backups failed even
though manual backups worked. After remediation, launchd backup kickstart exited
0 and completed Postgres + n8n backup verification. The live mini repo was then
reconciled to the pushed GitHub commit containing the fix and this report.

## Evidence Summary

| Area | Status | Evidence |
| --- | --- | --- |
| SSH and live repo path | Pass | SSH key login works for `aiagentecosystem@192.168.1.73`; repo path is `/Users/aiagentecosystem/services/ols`. |
| Repo identity | Pass with caveat | Mini is on `main`; live repo was reconciled to pushed commit `6d7f07a`. Remote is `https://github.com/humboldtscabinet/organizing-life-services-ai.git`. Mini-side `git ls-remote` cannot authenticate to GitHub noninteractively. |
| Working tree | Pass | `git status --short` was clean after reconciliation. |
| Host identity | Pass | `whoami=aiagentecosystem`, `ComputerName=agent-eco-mini`, hostname `agent-eco-mini.attwifi.manager`, en0 IP `192.168.1.73`. |
| Always-on basics | Warning | `pmset` shows `sleep 0`, but `autorestart 0`; FileVault is on, so fully unattended recovery after power loss is not guaranteed. |
| Firewall | Warning | macOS application firewall is disabled. Current Docker services are localhost-only, so exposure is contained, but this should be reviewed before LAN/Tailscale changes. |
| Secrets/config | Pass | `.env` and Google credentials are `600`; no duplicate env keys; required secret keys present and non-placeholder; `N8N_IMAGE=n8nio/n8n:1.97.1`; CORS is not wildcard. |
| Preflight | Pass | Login-shell preflight completed with `0 failure(s), 0 warning(s)`. Non-login SSH shell lacks Homebrew/OrbStack PATH and should not be used for server scripts. |
| Runtime stack | Pass with expected warnings | `infra/server/verify_stack.sh` completed with 0 failures and 2 expected warnings: dashboard and n8n have no Docker healthcheck. |
| Network exposure | Pass | API, dashboard, and n8n publish only on `127.0.0.1`; Postgres has no published host port. |
| API health | Pass | `{"status":"ok","service":"ols-api","version":"0.5.0","database":"ok","auth":"enabled"}`. |
| Backups | Pass | Fresh encrypted Postgres and n8n backups created; Postgres restored into disposable DB with 10 tables; n8n archive verified with 12 entries and `database.sqlite`. |
| launchd backups | Pass after fix | Initial kickstart failed with `ERROR: Docker Compose is not available`; after PATH fix/reinstall, launchd had `last exit code = 0` and completed full backup verification. |
| Ollama/Gemma | Pass | `gemma4:12b` and `gemma4:31b` are installed; both generated responses; API container reports local LLM status ok. |
| Ollama exposure | Pass | `lsof` shows Ollama listening on `127.0.0.1:11434` only. |
| High-stakes gates | Pass | Route grep confirms `require_high_stakes_confirmation` across Shopify/content/lifecycle/bulk vision writes; `judge_verdict` is required in guarded paths. |
| `llm_audit` table | Pass | Postgres query returned `llm_audit`. |
| Mini-side tests | Warning | `.venv` is missing on the mini, so `pytest` did not run there. Last known full test run was on the iMac before push. |
| Reboot durability | Warning | Current system boot time is `2026-06-17 05:23:11`; stack/LLM/launchd checks pass in this post-reboot session. Codex attempted a reboot via `osascript`, but boot time did not change, so Codex-triggered reboot is not independently proven. |

## Findings And Risks

### High

- None currently open.

### Medium

- **Mini cannot authenticate to GitHub noninteractively.** Future `git pull` from the mini may fail until GitHub SSH/PAT auth is configured.
- **Unattended power recovery is not guaranteed.** `autorestart 0` and FileVault being on mean a power-loss scenario likely requires human intervention.
- **No mini-side Python test environment.** Runtime is healthy, but the mini itself cannot run `pytest` until a venv/test setup is created.

### Low

- Dashboard and n8n have no Docker healthcheck. They are reachable, and this is an expected warning.
- macOS firewall is disabled. Current services are bound to localhost only, but firewall posture should be revisited before any LAN exposure.
- Router DHCP reservation for `192.168.1.73` still needs human/router confirmation.
- Off-machine backup destination is not yet confirmed. Local encrypted backups are working.
- Accidental iMac clone at `/Users/hc707consultinggroup/ols` should be removed or clearly ignored.

## Remediation Checklist

1. Configure noninteractive GitHub auth on the mini, preferably SSH key auth.
2. Decide power-loss policy:
   - keep FileVault on and accept manual unlock, or
   - disable FileVault only if the mini is physically secure and unattended recovery is more important.
3. Enable `autorestart` / "Start up automatically after a power failure" if unattended recovery is desired.
4. Reserve `192.168.1.73` for `agent-eco-mini` in router DHCP settings.
5. Add a mini-side Python test environment or document that tests are run only from the iMac/CI.
6. Configure an off-machine backup copy target for `infra/backup/out/`.
7. Decide dashboard/n8n remote access path: SSH tunnel, Tailscale, or intentional LAN binding.

## Commands Proven During Audit

```bash
infra/server/preflight.sh
infra/server/verify_stack.sh
infra/backup/run_all_backups.sh
infra/backup/verify_postgres_backup.sh
infra/backup/verify_n8n_backup.sh
infra/server/verify_local_llm.sh
RUN_GENERATE_CHECK=true infra/server/verify_local_llm.sh
curl http://127.0.0.1:8000/health
launchctl kickstart -k gui/$(id -u)/com.ols.backups
```

All command evidence was collected without printing secret values.
