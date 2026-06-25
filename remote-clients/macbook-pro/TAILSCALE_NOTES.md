# Tailscale Notes For OLS Remote Clients

Use Tailscale as a private transport only. It should make SSH and Screen
Sharing reachable from trusted devices without changing the OLS service
bindings.

## Required

- Mini, iMac, and MacBook Pro are signed into the same tailnet.
- MagicDNS is enabled.
- The mini has a stable MagicDNS name such as:

  ```text
  agent-eco-mini.<tailnet>.ts.net
  ```

- API, dashboard, n8n, Postgres, and Ollama stay bound to `127.0.0.1` on the
  mini.

## Avoid

- Do not expose dashboard/API/n8n/Postgres/Ollama to the public internet.
- Do not change Docker Compose service ports from localhost-only bindings.
- Do not copy the mini `.env` or credential files to the MacBook.
- Do not disable SSH password auth until both the iMac and MacBook key logins
  have been tested.

## Optional Later Hardening

- Tailscale ACLs that allow only the iMac and MacBook user/devices to reach the
  mini over SSH and Screen Sharing.
- Tailscale device approval for new devices.
- macOS firewall rules after Tailscale is proven.

