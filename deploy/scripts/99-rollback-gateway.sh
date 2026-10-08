#!/usr/bin/env bash
# ==============================================================================
# Zuke Wi-Fi Gateway - 99-rollback-gateway.sh
# Safely reverts all Zuke configurations and restores previous system files
# ==============================================================================

set -euo pipefail

if [ "${EUID}" -ne 0 ]; then
    echo "ERROR: Must be run as root (e.g. sudo bash 99-rollback-gateway.sh)" >&2
    exit 1
fi

echo "===================================================================="
echo "    ZUKE WI-FI GATEWAY - SYSTEM ROLLBACK & RESTORATION"
echo "===================================================================="
echo ""

BACKUP_DIR="/etc/zuke/backups"
TARGET_BACKUP="${1:-}"

if [ -z "${TARGET_BACKUP}" ]; then
    if [ -f "${BACKUP_DIR}/latest" ]; then
        TARGET_BACKUP=$(cat "${BACKUP_DIR}/latest" | cut -d'=' -f2)
    fi
fi

if [ -z "${TARGET_BACKUP}" ] || [ ! -d "${TARGET_BACKUP}" ]; then
    echo "WARNING: No backup directory specified or found. Proceeding with clean removal."
    TARGET_BACKUP=""
else
    echo "Restoring from backup archive: ${TARGET_BACKUP}"
fi

echo ""
echo "[1/5] Stopping Zuke system services..."
systemctl stop zuke-backend 2>/dev/null || true
systemctl disable zuke-backend 2>/dev/null || true
systemctl stop zuke-nftables 2>/dev/null || true
systemctl disable zuke-nftables 2>/dev/null || true
systemctl stop hostapd 2>/dev/null || true
systemctl disable hostapd 2>/dev/null || true

echo "[2/5] Safely removing nftables isolated zuke table..."
if command -v nft >/dev/null 2>&1; then
    nft delete table inet zuke 2>/dev/null || true
fi
rm -f /etc/nftables.d/zuke.nft 2>/dev/null || true

echo "[3/5] Cleaning up service drop-in files..."
rm -f /etc/dnsmasq.d/zuke.conf 2>/dev/null || true
rm -f /etc/hostapd/hostapd.conf 2>/dev/null || true
rm -f /etc/NetworkManager/conf.d/99-zuke-unmanage.conf 2>/dev/null || true
rm -f /etc/nginx/sites-enabled/zuke 2>/dev/null || true
rm -f /etc/nginx/sites-available/zuke 2>/dev/null || true
rm -f /etc/sysctl.d/99-zuke-forward.conf 2>/dev/null || true
rm -f /etc/systemd/system/zuke-backend.service 2>/dev/null || true
rm -f /etc/systemd/system/zuke-nftables.service 2>/dev/null || true

echo "[4/5] Restoring backed-up configurations..."
if [ -n "${TARGET_BACKUP}" ] && [ -d "${TARGET_BACKUP}" ]; then
    [ -e "${TARGET_BACKUP}/hostapd.conf" ] && cp -a "${TARGET_BACKUP}/hostapd.conf" /etc/hostapd/
    [ -e "${TARGET_BACKUP}/hostapd" ] && cp -a "${TARGET_BACKUP}/hostapd" /etc/default/
    [ -e "${TARGET_BACKUP}/dnsmasq.conf" ] && cp -a "${TARGET_BACKUP}/dnsmasq.conf" /etc/
    [ -d "${TARGET_BACKUP}/dnsmasq.d" ] && cp -a "${TARGET_BACKUP}/dnsmasq.d/"* /etc/dnsmasq.d/ 2>/dev/null || true
    [ -e "${TARGET_BACKUP}/nftables.conf" ] && cp -a "${TARGET_BACKUP}/nftables.conf" /etc/
    [ -d "${TARGET_BACKUP}/nftables.d" ] && cp -a "${TARGET_BACKUP}/nftables.d/"* /etc/nftables.d/ 2>/dev/null || true
    [ -d "${TARGET_BACKUP}/sites-available" ] && cp -a "${TARGET_BACKUP}/sites-available/"* /etc/nginx/sites-available/ 2>/dev/null || true
    [ -d "${TARGET_BACKUP}/sites-enabled" ] && cp -a "${TARGET_BACKUP}/sites-enabled/"* /etc/nginx/sites-enabled/ 2>/dev/null || true
    [ -d "${TARGET_BACKUP}/conf.d" ] && cp -a "${TARGET_BACKUP}/conf.d/"* /etc/NetworkManager/conf.d/ 2>/dev/null || true
    echo "  • Restored backed up files successfully ✓"
fi

echo "[5/5] Reloading daemons..."
systemctl daemon-reload
if command -v nmcli >/dev/null 2>&1; then
    nmcli general reload 2>/dev/null || true
fi
systemctl restart nginx 2>/dev/null || true
systemctl restart dnsmasq 2>/dev/null || true

echo ""
echo "===================================================================="
echo "Rollback complete. System returned to previous state."
echo "===================================================================="
