#!/usr/bin/env bash
# install-copilot.sh — Install GitHub Copilot CLI in Azure Cloud Shell / Codespaces
#
# Usage:
#   chmod +x install-copilot.sh && ./install-copilot.sh
#
# What it does:
#   1. Installs the GitHub Copilot CLI (gh copilot extension)
#   2. Verifies the installation
#
# Prerequisites:
#   - Azure Cloud Shell (bash) or GitHub Codespaces terminal
#   - GitHub authentication (gh auth login) if not already configured

set -euo pipefail

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  GitHub Copilot CLI — Install                        ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Install Copilot CLI ──────────────────────────────────────────────────────
echo "[1/2] Installing GitHub Copilot CLI..."
curl -fsSL https://gh.io/copilot-install | bash

# ── Verify ───────────────────────────────────────────────────────────────────
echo ""
echo "[2/2] Verifying installation..."
if command -v gh &> /dev/null && gh copilot --version &> /dev/null; then
    echo "  ✅ GitHub Copilot CLI installed successfully"
    gh copilot --version 2>/dev/null || true
else
    echo "  ⚠️  Installation completed but verification failed."
    echo "     You may need to restart your shell or add to PATH."
fi

echo ""
echo "  Next steps:"
echo "    cd copilot-studio-lab/scripts"
echo "    pwsh setup.ps1"
echo ""
