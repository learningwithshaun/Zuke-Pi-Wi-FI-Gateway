#!/usr/bin/env bash
# ==============================================================================
# Zuke Wi-Fi Gateway - 02-setup-gateway.sh
# Safe, non-destructive configuration tool for Raspberry Pi Wi-Fi Gateway
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_DIR="${DEPLOY_DIR}/config"

if [ "${EUID}" -ne 0 ]; then
    echo "ERROR: Must be run as root (e.g. sudo bash 02-setup-gateway.sh)" >&2
    exit 1
fi

echo "===================================================================="
echo "    ZUKE WI-FI GATEWAY - DEPLOYMENT CONFIGURATION"
echo "===================================================================="

# Load Configuration
ENV_FILE="${CONFIG_DIR}/gateway.env"
[ -f "${ENV_FILE}" ] || ENV_FILE="${CONFIG_DIR}/gateway.env.example"

WAN_IFACE=""
WLAN_IFACE=""
WIFI_SSID="Zuke WiFi"
WIFI_CHANNEL=6
WIFI_COUNTRY_CODE="ZA"
SUBNET_BASE="192.168.50"
GATEWAY_IP="${SUBNET_BASE}.1"
NETMASK="255.255.255.0"
DHCP_RANGE_START="${SUBNET_BASE}.10"
DHCP_RANGE_END="${SUBNET_BASE}.250"
DHCP_LEASE_TIME="8h"
BACKUP_DIR="/etc/zuke/backups"
ZUKE_ROOT="/opt/zuke"

[ -f "${ENV_FILE}" ] && . "${ENV_FILE}"

echo "[1/6] Verifying required software packages..."
for cmd in hostapd dnsmasq nft nginx python3; do
    if ! command -v "${cmd}" >/dev/null 2>&1; then
        echo "ERROR: Missing required package: ${cmd}. Run 01-install-packages.sh first." >&2
        exit 1
    fi
done
echo "  • Required packages verified ✓"

echo ""
echo "[2/6] Detecting and validating network interfaces..."
if [ -z "${WAN_IFACE}" ]; then
    WAN_IFACE=$(ip route show default 2>/dev/null | awk '{print $5}' | head -n1 || true)
    [ -n "${WAN_IFACE}" ] || { echo "ERROR: Could not detect WAN uplink. Set WAN_IFACE in gateway.env." >&2; exit 1; }
    echo "  • Auto-detected WAN uplink: ${WAN_IFACE}"
fi

if [ -z "${WLAN_IFACE}" ]; then
    if command -v iw >/dev/null 2>&1; then
        WLAN_IFACE=$(iw dev 2>/dev/null | awk '$1=="Interface"{print $2}' | head -n1 || true)
    fi
    [ -n "${WLAN_IFACE}" ] || { echo "ERROR: Could not detect Wi-Fi interface. Set WLAN_IFACE in gateway.env." >&2; exit 1; }
    echo "  • Auto-detected Wi-Fi interface: ${WLAN_IFACE}"
fi

[ "${WAN_IFACE}" != "${WLAN_IFACE}" ] || { echo "ERROR: WAN and WLAN cannot be identical (${WAN_IFACE})!" >&2; exit 1; }

echo ""
echo "[3/6] Running network safety checks..."
WAN_IP=$(ip -4 addr show dev "${WAN_IFACE}" 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -n1 || true)
if [ -n "${WAN_IP}" ]; then
    WAN_PREFIX=$(echo "${WAN_IP}" | cut -d'.' -f1-3)
    if [ "${WAN_PREFIX}" = "${SUBNET_BASE}" ]; then
        echo "CRITICAL ERROR: Subnet conflict! WAN is already using ${WAN_PREFIX}.0/24." >&2
        echo "Change SUBNET_BASE in gateway.env (e.g. 192.168.60)." >&2
        exit 1
    fi
fi
echo "  • Subnet safety check passed ✓"

echo ""
echo "[4/6] Creating timestamped backup of current configurations..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CURRENT_BACKUP="${BACKUP_DIR}/backup_${TIMESTAMP}"
mkdir -p "${CURRENT_BACKUP}"

for item in /etc/hostapd/hostapd.conf /etc/default/hostapd /etc/dnsmasq.conf /etc/dnsmasq.d /etc/nftables.conf /etc/nftables.d /etc/sysctl.d/99-zuke-forward.conf /etc/nginx/sites-available /etc/nginx/sites-enabled; do
    if [ -e "${item}" ]; then
        cp -a "${item}" "${CURRENT_BACKUP}/"
    fi
done
echo "LATEST_BACKUP=${CURRENT_BACKUP}" > "${BACKUP_DIR}/latest"
echo "  • Backup created at: ${CURRENT_BACKUP} ✓"


echo ""
echo "[5/6] Generating templated configuration files..."
STAGE_DIR="/tmp/zuke-stage-${TIMESTAMP}"
mkdir -p "${STAGE_DIR}"

sed \
    -e "s|__WLAN_IFACE__|${WLAN_IFACE}|g" \
    -e "s|__SSID__|${WIFI_SSID}|g" \
    -e "s|__CHANNEL__|${WIFI_CHANNEL}|g" \
    -e "s|__COUNTRY_CODE__|${WIFI_COUNTRY_CODE}|g" \
    "${CONFIG_DIR}/hostapd.conf.template" > "${STAGE_DIR}/hostapd.conf"

sed \
    -e "s|__WLAN_IFACE__|${WLAN_IFACE}|g" \
    -e "s|__DHCP_RANGE_START__|${DHCP_RANGE_START}|g" \
    -e "s|__DHCP_RANGE_END__|${DHCP_RANGE_END}|g" \
    -e "s|__NETMASK__|${NETMASK}|g" \
    -e "s|__DHCP_LEASE_TIME__|${DHCP_LEASE_TIME}|g" \
    -e "s|__GATEWAY_IP__|${GATEWAY_IP}|g" \
    -e "s|__PORTAL_URL__|${PORTAL_URL:-http://${GATEWAY_IP}/}|g" \
    "${CONFIG_DIR}/dnsmasq.conf.template" > "${STAGE_DIR}/zuke-dnsmasq.conf"

sed \
    -e "s|__WLAN_IFACE__|${WLAN_IFACE}|g" \
    -e "s|__WAN_IFACE__|${WAN_IFACE}|g" \
    -e "s|__SUBNET__|${SUBNET_BASE}.0/24|g" \
    "${CONFIG_DIR}/nftables.conf.template" > "${STAGE_DIR}/zuke.nft"

sed \
    -e "s|__FRONTEND_DIST_DIR__|${ZUKE_ROOT}/frontend/dist|g" \
    "${CONFIG_DIR}/nginx-zuke.conf.template" > "${STAGE_DIR}/nginx-zuke.conf"

echo "net.ipv4.ip_forward = 1" > "${STAGE_DIR}/99-zuke-forward.conf"
echo "  • Files staged in: ${STAGE_DIR} ✓"

echo ""
echo "[6/6] Summary:"
echo "  • WAN Uplink      : ${WAN_IFACE}"
echo "  • Wi-Fi AP Device : ${WLAN_IFACE} (SSID: \"${WIFI_SSID}\")"
echo "  • Gateway IP      : ${GATEWAY_IP}/24"
echo "  • Backup Archive  : ${CURRENT_BACKUP}"

APPLY_FLAG="${1:-}"
if [ "${APPLY_FLAG}" = "--apply" ]; then
    echo ""
    echo "Applying configuration to system files..."
    mkdir -p /etc/hostapd /etc/dnsmasq.d /etc/nftables.d /etc/nginx/sites-available /etc/nginx/sites-enabled
    cp "${STAGE_DIR}/hostapd.conf" /etc/hostapd/hostapd.conf
    systemctl unmask hostapd 2>/dev/null || true
    [ -f /etc/default/hostapd ] && sed -i 's|^#\?DAEMON_CONF=.*|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd

    ip addr flush dev "${WLAN_IFACE}" || true
    ip addr add "${GATEWAY_IP}/24" dev "${WLAN_IFACE}"
    ip link set "${WLAN_IFACE}" up

    cp "${STAGE_DIR}/zuke-dnsmasq.conf" /etc/dnsmasq.d/zuke.conf
    cp "${STAGE_DIR}/99-zuke-forward.conf" /etc/sysctl.d/99-zuke-forward.conf
    sysctl -p /etc/sysctl.d/99-zuke-forward.conf

    cp "${STAGE_DIR}/zuke.nft" /etc/nftables.d/zuke.nft
    nft -f /etc/nftables.d/zuke.nft

    cp "${STAGE_DIR}/nginx-zuke.conf" /etc/nginx/sites-available/zuke
    rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
    ln -sf /etc/nginx/sites-available/zuke /etc/nginx/sites-enabled/zuke

    cp "${DEPLOY_DIR}/systemd/zuke-backend.service" /etc/systemd/system/zuke-backend.service
    cp "${DEPLOY_DIR}/systemd/zuke-nftables.service" /etc/systemd/system/zuke-nftables.service
    systemctl daemon-reload

    systemctl restart nginx dnsmasq hostapd zuke-nftables zuke-backend
    echo "Zuke Gateway successfully applied and activated!"
else
    echo ""
    echo "Dry run complete. Staged files are ready for inspection."
    echo "To activate on the Raspberry Pi: sudo bash 02-setup-gateway.sh --apply"
fi
