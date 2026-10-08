# Zuke Raspberry Pi Wi-Fi Gateway + Captive Portal

High-performance, privacy-conscious Wi-Fi gateway and captive portal built for Raspberry Pi with a Python (Flask) backend and a mobile-first React (TypeScript + Vite + Tailwind CSS) frontend.

---

## Architecture

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
                    │ • hostapd      │  <-- Wi-Fi Access Point ("Zuke WiFi")
                    │ • dnsmasq      │  <-- DHCP & DNS server + RFC 8908
                    │ • nftables     │  <-- NAT Masquerade & dynamic IP authorization
                    │ • Python/Flask │  <-- Customer validation, sessions & gateway API
                    │ • Nginx / SPA  │  <-- Mobile-first captive portal frontend
                    └───────┬────────┘
                            │
                       Zuke WiFi
                            │
                ┌───────────┴───────────┐
                │                       │
          Customer Phone          Customer Laptop
```

### Customer Access Flow

```text
Customer connects to "Zuke WiFi"
              ↓
Pi assigns IP address (dnsmasq)
              ↓
Device attempts internet connection
              ↓
nftables redirects unauthenticated HTTP to Captive Portal
              ↓
Mobile-first Zuke registration page appears
              ↓
Customer enters Name and Email (optional marketing consent)
              ↓
Flask validates customer & creates session
              ↓
Flask authorizes device IP in nftables set (timeout 8h)
              ↓
Device granted unrestricted high-speed internet access
```

---

## Project Structure

```text
Zuke-Pi-Wi-FI-Gateway/
├── backend/
│   ├── app.py                      # Flask application factory
│   ├── config.py                   # Multi-environment configuration
│   ├── requirements.txt            # Python dependencies
│   ├── database/                   # SQLite database & migrations
│   │   ├── db.py
│   │   └── schema.sql
│   ├── models/                     # Customer & AccessSession models
│   ├── routes/
│   │   ├── captive_portal.py       # /api/captive-portal/register & /status
│   │   └── captive_detect.py       # Captive detection handlers (RFC 8908, Apple, Android)
│   ├── services/
│   │   ├── customer_service.py     # Registration & validation logic
│   │   └── gateway_service.py      # MockGatewayService (dev) & NftablesGatewayService (Pi)
│   └── tests/                      # Automated test suite (14 passing tests)
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts              # Vite config with backend API proxy
│   ├── tailwind.config.js          # Zuke branding color palette
│   ├── index.html
│   └── src/
│       ├── components/             # Reusable UI components (Header, Form, SuccessScreen)
│       ├── services/api.ts         # Gateway API integration
│       └── App.tsx                 # Main application shell
│
├── deploy/
│   ├── config/                     # Configuration templates (hostapd, dnsmasq, nftables, nginx)
│   ├── scripts/                    # Safe deployment & rollback scripts
│   │   ├── 00-verify-hardware.sh   # Non-destructive hardware diagnostic
│   │   ├── 01-install-packages.sh  # Apt-get package installation
│   │   ├── 02-setup-gateway.sh     # Safe setup (backup, template, optional --apply)
│   │   └── 99-rollback-gateway.sh  # Clean rollback & restoration
│   ├── systemd/                    # Service units (zuke-backend, zuke-nftables)
│   └── docs/                       # Raspberry Pi deployment guide
└── README.md
```

---

## Local Development Mode

The project is built to run safely on your development PC without modifying your host networking.

### 1. Backend Setup (Flask)
```bash
cd backend
python -m venv venv

# Windows:
.\venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

pip install -r requirements.txt
python app.py
```
* Backend runs at: `http://127.0.0.1:5000`
* In development, `MockGatewayService` is active: it stores authorized device IPs in memory and makes zero system networking changes.

### 2. Frontend Setup (React + Vite)
```bash
cd frontend
npm install
npm run dev
```
* Frontend runs at: `http://localhost:5173`
* API requests to `/api/*` are automatically proxied to Flask.

### 3. Running Backend Tests
```bash
pytest backend/tests -v
```

---

## Raspberry Pi Deployment

See the detailed guide in [`deploy/docs/RASPBERRY_PI_DEPLOYMENT.md`](deploy/docs/RASPBERRY_PI_DEPLOYMENT.md).

Quick summary of deployment scripts:
1. `bash deploy/scripts/00-verify-hardware.sh` - Non-destructive interface & AP capability check.
2. `sudo bash deploy/scripts/01-install-packages.sh` - Installs `hostapd`, `dnsmasq`, `nftables`, `nginx`.
3. `sudo bash deploy/scripts/02-setup-gateway.sh` - Staging & validation dry run with automatic backup.
4. `sudo bash deploy/scripts/02-setup-gateway.sh --apply` - Applies configuration to active services.
5. `sudo bash deploy/scripts/99-rollback-gateway.sh` - Restores original system configuration.

---

## Security & Privacy

* **Isolated Firewall**: Nftables rules are confined to a dedicated `table inet zuke`. Default tables and SSH access are never removed.
* **Privacy Conscious**: Only name and email are stored for access. Marketing consent is strictly opt-in.
* **No Hardcoded Secrets**: Configuration is managed via environment variables.
* **Kernel Expiration**: Authorized IPs expire automatically in the kernel `nftables` set (default: 8 hours).
