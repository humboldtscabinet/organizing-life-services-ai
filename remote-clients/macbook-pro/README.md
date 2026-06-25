# MacBook Pro Remote Client Setup

This folder is a setup kit for making the MacBook Pro a thin client for the
headless Mac mini server.

The MacBook may clone this repo to read these instructions and run the helper
scripts, but daily OLS development should happen through VS Code Remote-SSH into
the mini's live repo:

```text
/Users/aiagentecosystem/services/ols
```

Do not copy `.env`, Google credentials, Docker volumes, n8n data, Ollama models,
or backup artifacts onto the MacBook.

## Target Model

- Mini: owns code execution, Docker, Ollama, secrets, n8n, Postgres, backups.
- iMac: existing Remote-SSH client.
- MacBook Pro: second Remote-SSH client for travel/cafes.
- Tailscale: private off-network transport.
- Services: stay bound to mini localhost only.

## One-Time MacBook Steps

1. Install Tailscale and sign into the same tailnet as the mini.
2. Install VS Code.
3. Install the VS Code extension `ms-vscode-remote.remote-ssh`.
4. Install Tailscale on the mini from the MacBook or iMac when you can enter
   the mini admin password:

   ```bash
   ./install_tailscale_on_mini.sh
   ```

   Homebrew installation uses Apple's package installer and requires `sudo`.
   After the app opens on the mini, finish the Tailscale sign-in and any
   Privacy & Security approval macOS asks for.

5. Apply mini power-management hardening when you can enter the mini admin
   password:

   ```bash
   ./apply_pmset_hardening_on_mini.sh
   ```

6. Generate a MacBook SSH key if you do not already have one:

   ```bash
   ssh-keygen -t ed25519 -C "macbook-pro-to-agent-eco-mini"
   ```

7. Add the public key to the mini:

   ```bash
   ./install_public_key_on_mini.sh
   ```

   This uses `~/.ssh/id_ed25519.pub` by default and appends it idempotently to
   `/Users/aiagentecosystem/.ssh/authorized_keys` on the mini.

8. Copy `ssh_config.example` into your MacBook SSH config, replacing
   `<tailnet>` with the real MagicDNS tailnet name:

   ```bash
   cat ssh_config.example >> ~/.ssh/config
   chmod 600 ~/.ssh/config
   ```

9. Test:

   ```bash
   ssh ols-mini
   ./verify_macbook_client.sh
   ```

10. In VS Code:

   - Remote-SSH: Connect to Host...
   - Choose `ols-mini`
   - Open folder `/Users/aiagentecosystem/services/ols`

11. Install recommended remote-side extensions in that Remote-SSH window:

   - GitHub Copilot
   - GitHub Copilot Chat
   - Python
   - Pylance
   - Ruff
   - Docker

## Browser URLs From The MacBook

With the SSH config forwards active:

- dashboard: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- n8n: `http://localhost:5678`

If VS Code auto-forwards different local ports, use the forwarded URLs VS Code
shows in the Ports panel.

## Mini Hardening Still Required

The 2026-06-25 iMac check showed:

- Tailscale is not installed on the mini yet.
- FileVault is on.
- `sleep` is disabled.
- `displaysleep`, `disksleep`, and `autorestart` are not fully hardened.
- `sudo` requires a human-entered admin password.

Run this after Tailscale/headless settings are configured:

```bash
./verify_mini_headless_state.sh
```

Exact mini-side admin commands, to run on the mini or over SSH when you can
enter the admin password:

```bash
sudo pmset -a sleep 0 displaysleep 0 disksleep 0
sudo pmset autorestart 1
```

Then decide the FileVault tradeoff:

- FileVault off: better unattended reboot recovery for a physically secure
  headless server.
- FileVault on: better disk-theft protection, but the mini needs manual unlock
  after power loss.

Only after both iMac and MacBook SSH key login work should you disable SSH
password auth.
