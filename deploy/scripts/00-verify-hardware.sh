#!/usr/bin/env bash
# ==============================================================================
# Zuke Wi-Fi Gateway - 00-verify-hardware.sh
# Non-destructive hardware and network diagnostic tool for Raspberry Pi
# ==============================================================================

set -euo pipefail

echo "===================================================================="
echo "    ZUKE WI-FI GATEWAY - HARDWARE & NETWORK DIAGNOSTIC"
echo "===================================================================="
echo ""

# 1. OS & Kernel Check
echo "[1/7] System Information:"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "  • OS Distribution : ${PRETTY_NAME:-Unknown}"
else
    echo "  • OS Distribution : Unknown (/etc/os-release not found)"
fi
echo "  • Kernel Version  : $(uname -r)"
echo "  • Architecture    : $(uname -m)"

# 2. Raspberry Pi Hardware Check
echo ""
echo "[2/7] Hardware Model:"
if [ -f /proc/device-tree/model ]; then
    PI_MODEL=$(tr -d '\0' < /proc/device-tree/model)
    echo "  • Model           : ${PI_MODEL}"
else
    echo "  • Model           : Generic Linux / Non-Raspberry Pi system detected"
fi

# 3. Network Interfaces
echo ""
echo "[3/7] Available Network Interfaces:"
ip -brief link show || ifconfig -s || true

# 4. Default Uplink / Internet Route
echo ""
echo "[4/7] Default Internet Route (WAN):"
DEFAULT_ROUTE=$(ip route show default 2>/dev/null || true)
if [ -n "${DEFAULT_ROUTE}" ]; then
    DETECTED_WAN=$(echo "${DEFAULT_ROUTE}" | awk '{print $5}' | head -n1)
    DETECTED_GW=$(echo "${DEFAULT_ROUTE}" | awk '{print $3}' | head -n1)
    echo "  • Default Route   : ${DEFAULT_ROUTE}"
    echo "  • Primary Uplink  : ${DETECTED_WAN}"
    echo "  • Upstream Router : ${DETECTED_GW}"
    
    # Check IP and subnet of WAN
    WAN_IP=$(ip -4 addr show dev "${DETECTED_WAN}" 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -n1 || true)
    echo "  • Uplink IP       : ${WAN_IP:-None}"
else
    echo "  • WARNING: No default internet route detected!"
    DETECTED_WAN=""
fi

# 5. Wireless Interfaces & AP Support
echo ""
echo "[5/7] Wireless Interfaces & Access Point (AP) Capability:"
if command -v iw >/dev/null 2>&1; then
    WLAN_IFACES=$(iw dev 2>/dev/null | awk '$1=="Interface"{print $2}')
    if [ -n "${WLAN_IFACES}" ]; then
        for iface in ${WLAN_IFACES}; do
            echo "  • Wireless Device : ${iface}"
            PHY=$(iw dev "${iface}" info 2>/dev/null | awk '$1=="wiphy"{print "phy"$2}')
            if [ -n "${PHY}" ]; then
                if iw phy "${PHY}" info 2>/dev/null | grep -A 10 "Supported interface modes" | grep -q "\bAP\b"; then
                    echo "    - AP Mode       : SUPPORTED ✓"
                else
                    echo "    - AP Mode       : NOT SUPPORTED ✗"
                fi
            fi
        done
    else
        echo "  • WARNING: No wireless interfaces detected via 'iw dev'."
    fi
else
    echo "  • 'iw' command not installed. Run 01-install-packages.sh to install wireless diagnostic tools."
fi

# 6. Subnet Conflict Check
echo ""
echo "[6/7] Subnet Conflict Analysis:"
PROPOSED_SUBNET="192.168.50."
if ip route show | grep -q "${PROPOSED_SUBNET}"; then
    echo "  • WARNING: Subnet ${PROPOSED_SUBNET}0/24 is ALREADY in use on this system!"
    echo "    Please choose a different SUBNET_BASE in gateway.env (e.g. 192.168.60)."
else
    echo "  • Proposed subnet (${PROPOSED_SUBNET}0/24) is clear. No conflicts detected ✓"
fi

# 7. Port Availability Check
echo ""
echo "[7/7] Core Port Status:"
for port in 22 53 67 80 5000; do
    if command -v ss >/dev/null 2>&1; then
        LISTENER=$(ss -tulpn "sport = :${port}" 2>/dev/null | grep -v "Netid" | head -n1 || true)
    else
        LISTENER=""
    fi
    if [ -n "${LISTENER}" ]; then
        echo "  • Port ${port} : In Use (${LISTENER})"
    else
        echo "  • Port ${port} : Available ✓"
    fi
done

echo ""
echo "===================================================================="
echo "Diagnostic complete. Hardware verification finished."
echo "===================================================================="
