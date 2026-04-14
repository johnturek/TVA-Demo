#!/usr/bin/env bash
# install-gh.sh — Install GitHub CLI (gh) on Debian/Ubuntu-based systems
#
# Usage:
#   chmod +x install-gh.sh && ./install-gh.sh
#
# For: Azure Cloud Shell, GitHub Codespaces, or any Debian/Ubuntu environment
# Docs: https://github.com/cli/cli/blob/trunk/docs/install_linux.md

set -euo pipefail

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  GitHub CLI (gh) — Install                           ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Check if already installed ───────────────────────────────────────────────
if command -v gh &> /dev/null; then
    echo "  ✅ GitHub CLI already installed: $(gh --version | head -1)"
    echo ""
    exit 0
fi

# ── Install gh via apt ───────────────────────────────────────────────────────
echo "[1/3] Installing prerequisites..."
(type -p wget >/dev/null || (sudo apt update && sudo apt install wget -y))

echo "[2/3] Adding GitHub CLI repository..."
sudo mkdir -p -m 755 /etc/apt/keyrings
out=$(mktemp)
wget -nv -O"$out" https://cli.github.com/packages/githubcli-archive-keyring.gpg
cat "$out" | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null
sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
sudo mkdir -p -m 755 /etc/apt/sources.list.d
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null

echo "[3/3] Installing GitHub CLI..."
sudo apt update && sudo apt install gh -y

# ── Verify ───────────────────────────────────────────────────────────────────
echo ""
if command -v gh &> /dev/null; then
    echo "  ✅ $(gh --version | head -1)"
else
    echo "  ❌ Installation failed"
    exit 1
fi

echo ""
echo "  Next steps:"
echo "    gh auth login"
echo "    ./install-copilot.sh"
echo ""
