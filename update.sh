#!/usr/bin/env bash
# Quick update script for Linux VPN Gateway
# Re-runs install.sh with --update flag to quickly refresh backend & frontend code

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${EUID}" -ne 0 ]]; then
    echo "This script must be run as root. Elevating privileges..."
    exec sudo bash "${SCRIPT_DIR}/install.sh" --update "$@"
else
    exec bash "${SCRIPT_DIR}/install.sh" --update "$@"
fi
