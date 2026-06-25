#!/usr/bin/env bash
set -euo pipefail

install_cask_if_missing() {
  local cask="$1"
  local app_name="$2"

  if brew list --cask "$cask" >/dev/null 2>&1; then
    echo "PASS: $app_name is installed"
    return
  fi

  echo "Installing $app_name with Homebrew..."
  brew install --cask "$cask"
}

install_extension_if_possible() {
  local extension="$1"

  if ! command -v code >/dev/null 2>&1; then
    echo "WARN: VS Code 'code' CLI is not in PATH; install extension manually: $extension"
    return
  fi

  if code --list-extensions | grep -qxF "$extension"; then
    echo "PASS: VS Code extension installed: $extension"
  else
    echo "Installing VS Code extension: $extension"
    code --install-extension "$extension"
  fi
}

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This bootstrap script is intended for macOS." >&2
  exit 1
fi

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is not installed. Install it first from https://brew.sh, then rerun this script." >&2
  exit 1
fi

install_cask_if_missing "tailscale-app" "Tailscale"
install_cask_if_missing "visual-studio-code" "Visual Studio Code"

install_extension_if_possible "ms-vscode-remote.remote-ssh"
install_extension_if_possible "GitHub.copilot"
install_extension_if_possible "GitHub.copilot-chat"
install_extension_if_possible "ms-python.python"
install_extension_if_possible "ms-python.vscode-pylance"
install_extension_if_possible "charliermarsh.ruff"
install_extension_if_possible "ms-azuretools.vscode-docker"

echo
echo "Next:"
echo "1. Open Tailscale and sign into the same tailnet as the mini."
echo "2. Run ./generate_macbook_ssh_key.sh"
echo "3. Run ./configure_ssh_alias.sh <tailnet-name>"

