#!/usr/bin/env bash
# ==============================================================================
# Zuke Wi-Fi Gateway - 01-install-packages.sh
# Installs required Debian / Raspberry Pi OS Bookworm packages
# ==============================================================================

set -euo pipefail

if [ "${EUID}" -ne 0 ]; then
    echo "ERROR: This script must be run as root (e.g. sudo bash 01-install-packages.sh)" >&2
    exit 1
fi

echo "===================================================================="
echo "    ZUKE WI-FI GATEWAY - PACKAGE INSTALLATION"
echo "===================================================================="
echo ""

echo "[1/4] Updating package repositories..."
apt-get update -y

echo "[2/4] Installing networking & wireless packages..."
apt-get install -y --no-install-recommends \
    hostapd \
    dnsmasq \
    nftables \
    iw \
    wireless-tools \
    rfkill \
    iproute2

echo "[3/4] Installing web server & runtime dependencies..."
apt-get install -y --no-install-recommends \
    nginx \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    ca-certificates

echo "[4/4] Temporarily stopping and disabling hostapd & dnsmasq until configured..."
# Prevent unconfigured services from interfering or failing during system boot
systemctl stop hostapd 2>/dev/null || true
systemctl disable hostapd 2>/dev/null || true
systemctl stop dnsmasq 2>/dev/null || true
systemctl disable dnsmasq 2>/dev/null || true

# Ensure Wi-Fi is unblocked by rfkill
rfkill unblock wifi 2>/dev/null || true

echo ""
echo "===================================================================="
echo "Packages successfully installed."
echo "Next step: Configure gateway using 02-setup-gateway.sh"
echo "===================================================================="
