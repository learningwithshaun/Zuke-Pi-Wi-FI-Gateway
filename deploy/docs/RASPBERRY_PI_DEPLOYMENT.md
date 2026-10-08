# Raspberry Pi Deployment Guide

## 1. Overview

This document explains how to deploy the **Zuke Wi-Fi Gateway and Captive Portal** onto a Raspberry Pi running **Raspberry Pi OS (Bookworm 64-bit)**.

```text
                         INTERNET
                            │
                    ┌───────▼────────┐
                    │ Salon Router / │
                    │ Internet Modem │
                    └───────┬────────┘
                            │
                         Ethernet (WAN)
                            │
                    ┌───────▼────────┐
                    │  Raspberry Pi  │
                    │                │
                    │ • hostapd      │
                    │ • dnsmasq      │
                    │ • nftables     │
                    │ • Python/Flask │
                    │ • Nginx / SPA  │
                    └───────┬────────┘
                            │
                       Zuke WiFi
                            │
                ┌───────────┴───────────┐
                │                       │
          Customer Phone          Customer Laptop
```

---

## 2. Directory Layout on Raspberry Pi

Target installation directory on the Pi:
```text
/opt/zuke/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── venv/
│   └── data/zuke.db
├── frontend/
│   └── dist/
└── deploy/
    ├── config/
    ├── scripts/
    └── systemd/
```

---

## 3. Step-by-Step Deployment Procedure

### Step 1: Clone or Copy Repository to `/opt/zuke`
```bash
sudo mkdir -p /opt/zuke
sudo git clone https://github.com/learningwithshaun/Zuke-Pi-Wi-FI-Gateway.git /opt/zuke
sudo chown -R $USER:$USER /opt/zuke
```

### Step 2: Build Frontend and Setup Python Virtual Environment
```bash
# 1. Build frontend
cd /opt/zuke/frontend
npm install
npm run build

# 2. Setup backend virtual environment
cd /opt/zuke/backend
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
```

### Step 3: Run Hardware & Network Diagnostics (Non-destructive)
Execute the non-destructive diagnostic script to detect interfaces and check for AP support:
```bash
cd /opt/zuke/deploy/scripts
bash 00-verify-hardware.sh
```
Confirm:
* Detected WAN interface has internet connectivity.
* Detected Wi-Fi interface shows: `AP Mode : SUPPORTED ✓`.
* No subnet conflict with `192.168.50.0/24`.

### Step 4: Install System Packages
```bash
sudo bash 01-install-packages.sh
```
This installs `hostapd`, `dnsmasq`, `nftables`, `nginx`, and required utilities.

### Step 5: Configure Settings (Optional)
If your venue router uses `192.168.50.x`, customize the subnet prefix:
```bash
cp /opt/zuke/deploy/config/gateway.env.example /opt/zuke/deploy/config/gateway.env
nano /opt/zuke/deploy/config/gateway.env
```

### Step 6: Stage and Review Configuration (Dry Run)
```bash
sudo bash 02-setup-gateway.sh
```
* Generates all configuration files in `/tmp/zuke-stage-<timestamp>/`.
* Creates a timestamped backup in `/etc/zuke/backups/`.
* Makes **zero** network changes until `--apply` is specified.

### Step 7: Apply & Activate Gateway
When you are ready to apply the configuration:
```bash
sudo bash 02-setup-gateway.sh --apply
```

---

## 4. Rollback Procedure

If you ever wish to disable the gateway and restore the system to its original state:
```bash
sudo bash /opt/zuke/deploy/scripts/99-rollback-gateway.sh
```
This will:
1. Stop and disable `zuke-backend` and `zuke-nftables`.
2. Delete the `inet zuke` table from nftables without touching other firewall rules.
3. Remove drop-in configs from `dnsmasq.d` and `hostapd`.
4. Restore backed-up files from `/etc/zuke/backups/latest`.
5. Restart original networking services.
