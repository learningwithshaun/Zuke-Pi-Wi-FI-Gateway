# Zuke Wi-Fi Gateway Documentation

> A complete, beginner-friendly guide to understanding, developing, deploying, and operating the Zuke Wi-Fi Captive Portal Gateway on Windows and physical Raspberry Pi hardware.

---

## If You're New to This Project

Welcome! The Zuke Wi-Fi Gateway is an end-to-end guest Wi-Fi captive portal solution designed to run reliably on a physical Raspberry Pi. 

### Command Safety Labels Used in This Guide

Every command in this documentation is labeled to make system impacts immediately clear:

* 🟢 **SAFE / READ-ONLY**: Commands that only query or display information. They do not alter system files, firewall rules, or network interfaces.
* 🟡 **INSTALLATION / SYSTEM CHANGE**: Commands that install packages, compile assets, or write configuration files.
* 🔴 **GATEWAY CONFIGURATION**: Commands that modify the Raspberry Pi's active networking, bind static IPs, load kernel firewall rules, and convert the device into the active Zuke gateway.

### Recommended 19-Step Setup Sequence

Follow this end-to-end installation order:

1. **Connect Raspberry Pi to the existing network using Ethernet** (Step 1)
2. **Open the Raspberry Pi terminal / connect using SSH** (Step 2)
3. **Verify Git** (Step 3)
4. **Clone the repository** (Step 4)
5. **Enter `Zuke-Pi-Wi-FI-Gateway`** (Step 5)
6. **Verify the project files** (Step 6)
7. **Run `00-verify-hardware.sh`** (Step 7)
8. **Review the hardware inspection output** (Step 8)
9. **Install packages** (`01-install-packages.sh`)
10. **Configure `gateway.env`**
11. **Run the deployment dry-run** (`02-setup-gateway.sh`)
12. **Review the staged configuration**
13. **Apply the gateway configuration** (`02-setup-gateway.sh --apply`)
14. **Test `Zuke WiFi`**
15. **Test the captive portal**
16. **Test customer registration**
17. **Test internet access**
18. **Test session expiration**
19. **Know how to perform rollback** (`99-rollback-gateway.sh`)

---

## 1. Project Overview

### What the Zuke Wi-Fi Gateway Does

The Zuke Wi-Fi Gateway transforms a Raspberry Pi into a dedicated Wi-Fi access point and captive portal gateway. When customers visit a salon or venue, they connect to an open Wi-Fi network named **"Zuke WiFi"**. Before receiving full internet access, their phone or laptop is directed to a branded web portal where they enter their name and email address. 

Once the customer registers:
1. Their details and consent preferences are saved into an SQLite database.
2. A temporary access session is created (valid for 8 hours by default).
3. The Raspberry Pi firewall authorizes their device's IP address.
4. The customer is granted unrestricted, high-speed internet access routed through the venue's existing internet router.
5. When the 8-hour session expires, internet access ceases and the customer must register again to reconnect.

### Why the Raspberry Pi is Being Used

A Raspberry Pi (such as a Raspberry Pi 4 Model B or 3 Model B+) provides:
- **Dual Network Interfaces**: A built-in Ethernet port (WAN uplink to the venue router) and a built-in Wi-Fi radio (WLAN access point for guests).
- **Physical Network Isolation**: Guest Wi-Fi traffic stays on a separate subnet (`192.168.50.0/24`) and never directly touches the venue's internal private LAN devices (such as POS terminals or printers).
- **Low Power & Compact Footprint**: It runs continuously on 5V power without fans, noise, or large server hardware.
- **Full Linux Networking Stack**: Standard Linux kernel tools (`nftables`, `hostapd`, `dnsmasq`, `systemd`) provide rock-solid, production-grade network routing without costly enterprise hardware controllers.

### What the Customer Experience Looks Like

```text
Customer
   ↓
Connects to "Zuke WiFi" (Open network, no password required)
   ↓
Receives an IP address (e.g., 192.168.50.45 via dnsmasq)
   ↓
Captive portal opens automatically on customer's phone
   ↓
Customer enters name and email (optional marketing consent)
   ↓
Flask backend saves the customer record in SQLite
   ↓
Device IP is dynamically authorized in the nftables firewall
   ↓
Customer receives unrestricted high-speed internet access
   ↓
Access expires automatically after 8 hours
```

### Architecture Diagram

```text
                     CUSTOMER DEVICES
             (Smartphones, Tablets, Laptops)
                           │
                           │ Wi-Fi (SSID: "Zuke WiFi")
                           ▼
             ┌───────────────────────────┐
             │       Raspberry Pi        │
             │                           │
             │ • hostapd                 │ <-- 802.11 Access Point
             │ • dnsmasq                 │ <-- DHCP & DNS Server (RFC 8908)
             │ • nftables                │ <-- NAT Masquerade & Dynamic IP Rules
             │ • Nginx                   │ <-- Port 80 Reverse Proxy & SPA Host
             │ • React Frontend (SPA)    │ <-- Mobile-first registration portal
             │ • Flask Backend (API)     │ <-- Customer validation & session logic
             │ • SQLite Database         │ <-- Persistent customers & sessions
             └─────────────┬─────────────┘
                           │
                           │ Ethernet Cable (WAN: eth0 / end0)
                           ▼
             ┌───────────────────────────┐
             │   Salon Internet Router   │
             │       (Venue Modem)       │
             └─────────────┬─────────────┘
                           │
                           │ Fiber / VDSL / LTE Uplink
                           ▼
                       INTERNET
```

### Explanation of Components

| Component | Role in the Gateway | Beginner-Friendly Explanation |
| :--- | :--- | :--- |
| **hostapd** | Wi-Fi Access Point Daemon | Broadcasts the Wi-Fi network named `"Zuke WiFi"` so nearby phones can detect and connect to it wirelessly without requiring a pre-shared WPA password. |
| **dnsmasq** | DHCP & DNS Server | Gives each connected phone a private IP address (like `192.168.50.45`) and handles domain name lookups. It also announces the captive portal URL using RFC 8908 / RFC 8910 Option 114 so operating systems can prompt the user to sign in. |
| **nftables** | Linux Kernel Firewall & NAT | The network gatekeeper. It blocks unauthenticated internet traffic, redirects unauthenticated web browsers to the Zuke portal, translates network addresses (NAT Masquerade), and automatically unblocks authorized IPs for 8 hours using Linux kernel timers. |
| **Nginx** | Web Server & Reverse Proxy | Listens on port 80. Serves the pre-built React frontend directly to connecting phones and forwards API requests (`/api/*`) and captive detection probes (`/generate_204`, etc.) to the Python Flask backend. |
| **React Frontend** | Mobile Web App | The user interface customer sees on their screen. Features a clean, responsive card with inputs for name and email, instant error feedback, and a connection confirmation screen. |
| **Flask Backend** | Application Server & Gateway Controller | Validates user input, saves records into the SQLite database, creates secure session tokens, and instructs `nftables` to authorize the client IP address. |
| **SQLite** | Embedded Database | A fast, zero-configuration database stored in a single file on the SD card (`zuke.db`) to record registered customers and active access sessions. |
| **Internet Router** | Venue Gateway | The existing internet router in the salon that connects the Raspberry Pi to the outside world. |

---

## 2. Technology Stack

The Zuke Wi-Fi Gateway uses modern, standard open-source technologies:

### Operating System & Infrastructure
* **Raspberry Pi OS (Debian 12 Bookworm, 64-bit)**: The recommended operating system for the physical Raspberry Pi. Provides modern kernel support for `nftables` and `NetworkManager`.
* **systemd**: The standard Linux service manager. Keeps the Flask backend (`zuke-backend.service`) and firewall rules (`zuke-nftables.service`) running continuously and automatically restarts them if the Raspberry Pi reboots.
* **Git & GitHub**: Source control and repository hosting used to version, track, and distribute the project code.

### Backend Stack
* **Python 3 (3.10+)**: Core programming language for application logic, validation, and firewall management.
* **Flask (>= 3.0.0)**: Lightweight WSGI web framework providing REST API endpoints (`/api/health`, `/api/captive-portal/register`, `/api/captive-portal/status`) and probe handlers.
* **Flask-CORS (>= 4.0.0)**: Cross-Origin Resource Sharing middleware allowing local development across frontend and backend dev ports.
* **python-dotenv (>= 1.0.0)**: Loads environment variables from `.env` files into application settings.
* **Gunicorn (>= 22.0.0)**: Production WSGI server running behind Nginx on Linux/Raspberry Pi (`sys_platform != 'win32'`).
* **pytest (>= 8.0.0)**: Automated test suite for backend routes, database models, and mock gateway services.
* **SQLite 3**: Embedded relational database engine bundled with the Python standard library.

### Frontend Stack
* **React 18**: Component-based UI library powering the single-page captive portal application.
* **TypeScript 5**: Type-safe programming language ensuring high reliability and zero unexpected runtime type errors.
* **Vite 6**: Fast build tool and local development server with built-in API proxying.
* **Tailwind CSS 3**: Utility-first CSS framework configured with Zuke branding colors (`zuke-navy`, `zuke-orange`, `zuke-teal`).
* **lucide-react**: Lightweight icon set used for network badges, user icons, and confirmation indicators.

### Linux Networking & Firewall
* **hostapd**: User-space daemon for wireless access points, supporting IEEE 802.11b/g/n.
* **dnsmasq**: Combined lightweight DHCP server and caching DNS forwarder with RFC 8908 captive portal identification.
* **nftables**: Successor to `iptables`. Manages packet forwarding, NAT masquerading, and dynamic timed sets in a dedicated table named `inet zuke`.
* **Nginx**: High-performance HTTP server serving static frontend assets and reverse-proxying API traffic to Gunicorn.

---

## 3. Project Structure

Here is the actual repository directory tree:

```text
Zuke-Pi-Wi-FI-Gateway/
├── backend/
│   ├── database/
│   │   ├── __init__.py
│   │   ├── db.py                      # SQLite connection management & helpers
│   │   └── schema.sql                 # DDL definitions for customers & access_sessions
│   ├── models/
│   │   ├── __init__.py
│   │   └── customer.py                # Customer & AccessSession dataclass models
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── captive_portal.py          # /api/captive-portal/register & /status
│   │   └── captive_detect.py          # Android, Apple, Windows & RFC 8908 probes
│   ├── services/
│   │   ├── __init__.py
│   │   ├── customer_service.py        # Input validation, DB transactions & sessions
│   │   └── gateway_service.py         # MockGatewayService & NftablesGatewayService
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py                # Pytest fixtures and test app factory
│   │   ├── test_gateway_service.py    # Tests for status, mocks, and captive detection
│   │   └── test_registration.py       # Tests for customer registration and validation
│   ├── .env.example                   # Example backend environment variables
│   ├── app.py                         # Application factory (create_app) & dev server
│   ├── config.py                      # Configuration classes (Dev, Test, Prod)
│   └── requirements.txt               # Backend Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ErrorAlert.tsx         # User-friendly error alert box
│   │   │   ├── Header.tsx             # Zuke branding header and subtitle
│   │   │   ├── LoadingSpinner.tsx     # Animated spinner for pending actions
│   │   │   ├── RegistrationForm.tsx   # Name, email, consent form & validation
│   │   │   ├── SuccessScreen.tsx      # Connected status & web navigation screen
│   │   │   └── WifiBadge.tsx          # Connected network indicator ("Zuke WiFi")
│   │   ├── services/
│   │   │   └── api.ts                 # Frontend HTTP client (fetch) for backend API
│   │   ├── App.tsx                    # Root portal component & state machine
│   │   ├── index.css                  # Tailwind styles and global CSS
│   │   ├── main.tsx                   # React DOM entry point
│   │   └── types.ts                   # TypeScript interfaces for API requests/responses
│   ├── index.html                     # HTML document shell
│   ├── package.json                   # Frontend dependencies and npm scripts
│   ├── postcss.config.js              # PostCSS configuration
│   ├── tailwind.config.js             # Tailwind branding color palette
│   ├── tsconfig.json                  # TypeScript compiler configuration
│   ├── tsconfig.node.json             # Node-specific TypeScript compiler configuration
│   └── vite.config.ts                 # Vite bundler configuration & /api proxy
│
├── deploy/
│   ├── config/
│   │   ├── dnsmasq.conf.template      # dnsmasq template with DHCP & RFC 8908
│   │   ├── gateway.env.example        # Master environment configuration template
│   │   ├── hostapd.conf.template      # hostapd template for 802.11n Wi-Fi AP
│   │   ├── nftables.conf.template     # nftables template with table inet zuke
│   │   └── nginx-zuke.conf.template   # Nginx virtual host template
│   ├── docs/
│   │   └── RASPBERRY_PI_DEPLOYMENT.md # Deployment reference document
│   ├── scripts/
│   │   ├── 00-verify-hardware.sh      # Read-only hardware & network diagnostic
│   │   ├── 01-install-packages.sh     # Debian/Pi OS package installer
│   │   ├── 02-setup-gateway.sh        # Staging dry-run & optional --apply installer
│   │   └── 99-rollback-gateway.sh     # System rollback & configuration restorer
│   └── systemd/
│       ├── zuke-backend.service       # systemd unit for Flask/Gunicorn backend
│       └── zuke-nftables.service      # systemd unit for loading nftables rules
│
├── .gitignore                         # Git ignored files (venv, node_modules, db, etc.)
├── README.md                          # Repository quick-start guide
└── DOCUMENTATION.md                   # This comprehensive manual
```


### Purpose of Important Files & Directories

* **`backend/app.py`**: The Flask application factory (`create_app()`). Initializes Flask, enables CORS, registers database teardown hooks, mounts route blueprints, and exposes the `/api/health` monitoring endpoint.
* **`backend/config.py`**: Defines configuration classes (`DevelopmentConfig`, `TestingConfig`, `ProductionConfig`). Selects whether the backend operates using `MockGatewayService` or Linux `NftablesGatewayService`.
* **`backend/database/db.py`**: Manages SQLite connection lifecycle per Flask request. Ensures foreign key constraints are enforced (`PRAGMA foreign_keys = ON`) and manages connection cleanup.
* **`backend/database/schema.sql`**: SQLite DDL creating `customers` and `access_sessions` tables, along with search indexes on customer email, device IP, and session expiration.
* **`backend/models/customer.py`**: Dataclasses for `Customer` and `AccessSession`, providing serialization (`to_dict()`) for API responses.
* **`backend/routes/captive_portal.py`**: Handles API endpoints: customer registration (`POST /api/captive-portal/register`) and authorization status queries (`GET /api/captive-portal/status`). Automatically extracts client IP from proxy headers (`X-Forwarded-For`, `X-Real-IP`).
* **`backend/routes/captive_detect.py`**: Provides captive portal detection responses for Android (`/generate_204`), Apple CNA (`/hotspot-detect.html`), Windows NCSI (`/ncsi.txt`), and RFC 8908 (`/api/captive-portal/rfc8908`).
* **`backend/services/customer_service.py`**: Business logic layer. Validates name (1-100 characters) and email format, upserts customer records, generates cryptographically secure session tokens (`secrets.token_urlsafe(32)`), and triggers gateway authorization.
* **`backend/services/gateway_service.py`**: Implements network device authorization. Provides `MockGatewayService` for safe Windows development and `NftablesGatewayService` for controlling the Linux kernel firewall on the Raspberry Pi.
* **`frontend/src/`**: React application components (`RegistrationForm.tsx`, `SuccessScreen.tsx`, `Header.tsx`, `WifiBadge.tsx`), API client (`api.ts`), and TypeScript type definitions (`types.ts`).
* **`deploy/config/gateway.env.example`**: The master configuration blueprint. Specifies Wi-Fi SSID, channel, country code, client subnet, DHCP ranges, and system directories.
* **`deploy/config/hostapd.conf.template`**: hostapd configuration template defining open 802.11n Wi-Fi broadcasting on 2.4GHz with WMM support.
* **`deploy/config/dnsmasq.conf.template`**: dnsmasq configuration template defining DHCP lease pool, default gateway, local DNS mapping, and RFC 8908 Option 114.
* **`deploy/config/nftables.conf.template`**: Firewall template creating isolated table `inet zuke` with dynamic timed set `@authenticated_ips`, NAT masquerading, and port 80 captive portal redirection.
* **`deploy/config/nginx-zuke.conf.template`**: Nginx site configuration serving the compiled React frontend, redirecting probe URLs, and proxying `/api/` traffic to Flask.
* **`deploy/scripts/00-verify-hardware.sh`**: Non-destructive diagnostic tool verifying OS, hardware model, network links, AP mode support, WAN routes, and subnet safety.
* **`deploy/scripts/01-install-packages.sh`**: Automated installer for required Debian / Raspberry Pi OS packages.
* **`deploy/scripts/02-setup-gateway.sh`**: Validates interfaces, creates backups, stages templated configs, and safely applies them to active services when `--apply` is specified.
* **`deploy/scripts/99-rollback-gateway.sh`**: Restores the system to its pre-deployment state by stopping Zuke services, deleting `table inet zuke`, restoring backed-up configuration files, and restarting original daemons.

---

## 4. Prerequisites

Before beginning installation or development, ensure your environment meets the requirements below:

### Development Machine (Windows)

Developing or testing the application locally on Windows requires:
* **Operating System**: Windows 10 or Windows 11 (64-bit).
* **Git for Windows**: To clone the repository and run git commands.
* **Python**: Version 3.10, 3.11, or 3.12 (must be added to system `PATH`).
* **Node.js & npm**: Node.js v18.x or v20.x (LTS recommended) and npm v9+.
* **PowerShell**: Windows PowerShell 5.1 or PowerShell 7+.
* **Web Browser**: Any modern browser (Google Chrome, Microsoft Edge, Mozilla Firefox) for testing the captive portal UI.
* **No Special Network Privileges Required**: On Windows, the backend runs in `mock` mode. It does not alter your Windows firewall, adapters, or network settings.

### Raspberry Pi (Physical Hardware)

Deploying the gateway onto a physical unit requires:
* **Compatible Raspberry Pi Model**:
  * **Raspberry Pi 4 Model B** (Recommended: 2 GB, 4 GB, or 8 GB RAM).
  * **Raspberry Pi 3 Model B / Model B+** (Supported).
  * **Raspberry Pi 5** (Supported).
  * *Note*: The Raspberry Pi must have an onboard Wi-Fi chip or a supported external USB Wi-Fi dongle whose driver supports **AP (Access Point) mode** using the standard `nl80211` Linux subsystem.
* **Operating System**:
  * **Raspberry Pi OS (64-bit)** based on **Debian 12 (Bookworm)** is strongly recommended.
  * Raspberry Pi OS Lite (no desktop GUI) is ideal for maximum reliability and minimal memory usage.
* **Storage**:
  * MicroSD card with at least **16 GB** capacity (Class 10 / UHS-1 / A1 rated).
* **Power Supply**:
  * Official Raspberry Pi Power Supply (5V / 3.0A USB-C for Pi 4; 5V / 5.0A for Pi 5; 5V / 2.5A Micro-USB for Pi 3). Using low-quality phone chargers will cause brownouts and Wi-Fi radio dropouts.
* **Network Connections**:
  * **Wired Ethernet (WAN)**: A physical Ethernet cable connecting the Raspberry Pi's Ethernet port (`eth0` or `end0`) to the salon/venue internet router or switch. The Pi must obtain an IP address with active internet access from this router.
  * **Wireless Radio (WLAN)**: The internal wireless radio (`wlan0`) will be dedicated exclusively to broadcasting the "Zuke WiFi" network. It must not be connected as a client to an existing Wi-Fi network.
* **Permissions**:
  * Full `sudo` / root administrative privileges on the Raspberry Pi.
* **Network Access During Setup**:
  * Working internet connection via the Ethernet cable so `apt-get` can download packages and git can clone the repository.

---

## 5. Clone the Project

Run the following commands to download the project repository:

### On Windows (PowerShell)

> 🟢 **SAFE / READ-ONLY:** Downloads the project repository without modifying your machine.

```powershell
git clone https://github.com/learningwithshaun/Zuke-Pi-Wi-FI-Gateway.git
cd Zuke-Pi-Wi-FI-Gateway
```

### On the Raspberry Pi (Terminal / SSH)

> 🟢 **SAFE / READ-ONLY:** Clones the project files onto the Raspberry Pi.

```bash
sudo mkdir -p /opt/zuke
sudo chown -R $USER:$USER /opt/zuke
git clone https://github.com/learningwithshaun/Zuke-Pi-Wi-FI-Gateway.git /opt/zuke
cd /opt/zuke
```

### Verifying Successful Clone

Check that the core folders exist:

**On Windows:**
```powershell
Get-ChildItem -Directory | Select-Object Name
```
Expected output:
```text
backend
deploy
frontend
```

**On the Raspberry Pi:**
```bash
ls -la /opt/zuke
```
Expected output shows `backend`, `frontend`, `deploy`, `README.md`, and `DOCUMENTATION.md`.

---

## 6. Windows Development Setup

You can develop, test, and preview the full captive portal application on Windows without modifying any network adapters or firewall rules. On Windows, Flask runs with `GATEWAY_TYPE=mock`, which stores authorized client IPs in memory.

### Backend Setup (Flask)

Open a PowerShell terminal in the repository root:

> 🟢 **SAFE / READ-ONLY:** Runs entirely within an isolated Python virtual environment on your PC.

#### 1. Navigate to the backend directory:
```powershell
cd backend
```

#### 2. Create and activate a Python virtual environment:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If PowerShell shows an execution policy error, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and retry).*

#### 3. Install Python dependencies:
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. Configure local environment variables:
Create a `.env` file by copying `.env.example`:
```powershell
Copy-Item .env.example .env
```

The default values in `backend/.env` are pre-configured for local Windows development:
```ini
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=zuke-dev-secret-key-change-in-prod
HOST=0.0.0.0
PORT=5000
GATEWAY_TYPE=mock
SESSION_DURATION_HOURS=8
DATABASE_PATH=data/zuke.db
PORTAL_URL=http://localhost:5173/
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

#### 5. Start the Flask application:
```powershell
python app.py
```
Expected output:
```text
 * Serving Flask app 'backend.app'
 * Debug mode: on
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
```

#### 6. Test the Health Check Endpoint:
Open a second PowerShell window or browser and verify:
```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/health
```
Response:
```json
{
  "gateway_type": "mock",
  "service": "zuke-wifi-gateway",
  "status": "healthy"
}
```

#### 7. Run Automated Tests:
In your activated virtual environment, run the pytest suite from the project root:
```powershell
python -m pytest backend/tests -v
```
*(Or from the `backend` directory: `$env:PYTHONPATH=".."; pytest tests -v`)*

All 14 tests should pass, verifying registration, validation, mock timeout expiration, status queries, and captive detection redirects.

---

### Frontend Setup (React + Vite)

Open a new PowerShell terminal:

> 🟢 **SAFE / READ-ONLY:** Runs local development server on Node.js without system changes.

#### 1. Navigate to the frontend directory:
```powershell
cd frontend
```

#### 2. Install Node dependencies:
```powershell
npm install
```

#### 3. Start the Vite development server:
```powershell
npm run dev
```
Expected output:
```text
  VITE v6.0.3  ready in 180 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
```

#### 4. Open in your browser:
Navigate to: **`http://localhost:5173`**

#### How API Proxying Works in Development:
In `frontend/vite.config.ts`, Vite is configured with a proxy:
```typescript
server: {
  host: '0.0.0.0',
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:5000',
      changeOrigin: true,
    },
  },
}
```
When you register in the web interface at `http://localhost:5173`, the browser sends requests to `http://localhost:5173/api/captive-portal/register`. Vite forwards them seamlessly to Flask at `http://127.0.0.1:5000/api/captive-portal/register`.

#### 5. Building for Production:
To compile static HTML, JavaScript, and CSS assets:
```powershell
npm run build
```
The compiled files are generated in `frontend/dist/`. On the Raspberry Pi, Nginx serves these files directly.

---

## 7. Database Setup

The gateway uses **SQLite 3** for customer and session persistence.

### Database Location & Initialization
* **Storage Location**: By default, stored at `backend/data/zuke.db` (or whatever path is configured by `DATABASE_PATH`).
* **Automatic Creation**: You do not need to create or run manual database setup scripts. In `backend/app.py`, `init_db(app)` automatically checks for the database file and initializes the schema from `backend/database/schema.sql` whenever the application starts.
* **Foreign Keys**: Enforced on every connection via `PRAGMA foreign_keys = ON`.

### Database Tables

#### Table 1: `customers`
Stores registered customer contact information and marketing consent.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | PRIMARY KEY AUTOINCREMENT | Unique customer ID |
| `name` | `TEXT` | NOT NULL | Customer name (1-100 characters) |
| `email` | `TEXT` | NOT NULL UNIQUE | Customer email address (normalized to lowercase) |
| `marketing_consent` | `INTEGER` | NOT NULL DEFAULT 0 | `1` if opted into communications, `0` if declined |
| `created_at` | `TEXT` | DEFAULT (datetime('now')) | ISO timestamp when record was first created |
| `updated_at` | `TEXT` | DEFAULT (datetime('now')) | ISO timestamp of the customer's latest visit |

#### Table 2: `access_sessions`
Stores every Wi-Fi authorization granted to a client device.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | PRIMARY KEY AUTOINCREMENT | Unique session ID |
| `customer_id` | `INTEGER` | NOT NULL, REFERENCES customers(id) | Linked customer record |
| `ip_address` | `TEXT` | NOT NULL | IP address of the customer's phone/device |
| `session_token` | `TEXT` | NOT NULL UNIQUE | Cryptographic random URL-safe token |
| `authenticated` | `INTEGER` | NOT NULL DEFAULT 1 | `1` for active session |
| `created_at` | `TEXT` | DEFAULT (datetime('now')) | Session creation timestamp |
| `expires_at` | `TEXT` | NOT NULL | UTC ISO timestamp when access expires |

### How Customer Registration Creates an Access Session

1. **Submission**: The customer enters their name and email on the captive portal page.
2. **Validation**: `CustomerService.validate_registration_input()` ensures the name is between 1 and 100 characters and the email matches standard formatting.
3. **Upsert**:
   - If the customer email does not exist, a new row is inserted into `customers`.
   - If the customer is returning, their existing record is updated with their latest name, consent preference, and `updated_at = CURRENT_TIMESTAMP`.
4. **Session Token**: `secrets.token_urlsafe(32)` generates an unguessable 43-character token.
5. **Access Period**: Calculates `expires_at = now + (SESSION_DURATION_HOURS * 3600 seconds)` (default: 8 hours).
6. **Persistence**: An entry is inserted into `access_sessions` linking the `customer_id` and device IP.
7. **Firewall Authorization**: `GatewayService.authorize_device(ip_address, duration_seconds)` is invoked to grant network-level forwarding.

### How Session Expiration Works

* **At the Application Layer (Status Queries)**: When the frontend or device checks `/api/captive-portal/status`, the query verifies `expires_at > CURRENT_TIMESTAMP`. If the session has expired, it reports `authenticated: false`.
* **At the Firewall Layer (Raspberry Pi)**: In `NftablesGatewayService`, the client IP is added to the nftables set `@authenticated_ips` with `timeout 28800s`. The Linux kernel manages this timer internally. Once 8 hours elapse, the kernel automatically removes the IP from the set without needing cron jobs or polling scripts. Immediate packet forwarding to the WAN is revoked.

---

## 8. API Documentation

All API endpoints are implemented in `backend/routes/captive_portal.py` and `backend/routes/captive_detect.py`.

### 1. Health Check

* **Endpoint**: `GET /api/health`
* **Purpose**: Verify backend status, service availability, and active gateway driver.
* **Authentication**: None required.
* **Request Headers**: None.
* **Example Request**:
  ```bash
  curl http://127.0.0.1:5000/api/health
  ```
* **Success Response (200 OK)**:
  ```json
  {
    "gateway_type": "mock",
    "service": "zuke-wifi-gateway",
    "status": "healthy"
  }
  ```
  *(On the Raspberry Pi, `"gateway_type"` returns `"nftables"`).*

---

### 2. Customer Registration

* **Endpoint**: `POST /api/captive-portal/register`
* **Purpose**: Validates customer details, persists them in SQLite, creates an access session, and authorizes the client device IP for internet access.
* **Authentication**: None required.
* **Request Headers**: `Content-Type: application/json`
* **Request Body**:
  ```json
  {
    "name": "Amanda Smith",
    "email": "customer@example.com",
    "marketing_consent": true
  }
  ```
* **Fields**:
  * `name` *(string, required)*: Customer name (1 to 100 characters).
  * `email` *(string, required)*: Valid customer email address.
  * `marketing_consent` *(boolean, optional)*: Default `false`.

* **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "message": "Internet access granted",
    "session": {
      "authenticated": true,
      "expires_at": "2026-10-08T23:22:00.000000+00:00",
      "ip_address": "192.168.50.45",
      "token": "4vQ_W48YtB2b9f3Xl1j-R8_Xg3zW9A8f1aBC-dE0zK8"
    }
  }
  ```

* **Error Responses**:
  * **400 Bad Request (Invalid/Missing Name)**:
    ```json
    {
      "success": false,
      "error": "Please enter your name."
    }
    ```
  * **400 Bad Request (Invalid Email)**:
    ```json
    {
      "success": false,
      "error": "Please enter a valid email address."
    }
    ```
  * **400 Bad Request (Malformed JSON)**:
    ```json
    {
      "success": false,
      "error": "Invalid request format. Expected JSON body."
    }
    ```
  * **500 Internal Server Error**:
    ```json
    {
      "success": false,
      "error": "Unable to complete registration. Please try again."
    }
    ```

---

### 3. Captive Portal Connection Status

* **Endpoint**: `GET /api/captive-portal/status`
* **Purpose**: Inquire whether the client's IP address or session token is currently authenticated.
* **Authentication**: Optional session token passed via URL parameter `?token=...` or header `Authorization: Bearer <token>`.
* **Example Request**:
  ```bash
  curl "http://127.0.0.1:5000/api/captive-portal/status?token=4vQ_W48YtB2b9f3Xl1j-R8_Xg3zW9A8f1aBC-dE0zK8"
  ```
* **Response When Authenticated (200 OK)**:
  ```json
  {
    "authenticated": true,
    "ip_address": "192.168.50.45",
    "expires_at": "2026-10-08T23:22:00.000000+00:00"
  }
  ```
* **Response When Not Authenticated (200 OK)**:
  ```json
  {
    "authenticated": false,
    "ip_address": "192.168.50.45"
  }
  ```

---

### 4. Captive Portal Detection Probes

Modern mobile and desktop operating systems send HTTP probes as soon as they connect to a Wi-Fi network. The gateway intercepts these requests to either display the sign-in prompt or confirm connectivity.

#### Android & Google Chrome Probes
* **Endpoints**: `GET /generate_204` and `GET /gen_204`
* **Unauthenticated**: Returns `302 Found` redirecting to `PORTAL_URL` (`http://192.168.50.1/`). This causes Android to display the *"Sign in to Wi-Fi network"* notification.
* **Authenticated**: Returns `204 No Content`. Android recognizes the network has full internet connectivity.

#### Apple Captive Network Assistant (CNA) Probes
* **Endpoints**: `GET /hotspot-detect.html` and `GET /canonical.html`
* **Unauthenticated**: Returns `302 Found` redirecting to `PORTAL_URL`. This triggers the iOS/macOS automatic captive network slide-over sheet.
* **Authenticated**: Returns `200 OK` with HTML body `<HTML><HEAD><TITLE>Success</TITLE></HEAD><BODY>Success</BODY></HTML>`. iOS automatically closes the captive modal and connects.

#### Windows Network Connectivity Status Indicator (NCSI) Probes
* **Endpoints**: `GET /ncsi.txt` and `GET /connecttest.txt`
* **Unauthenticated**: Returns `302 Found` redirecting to `PORTAL_URL`. Windows pops up the *"Action needed"* browser prompt.
* **Authenticated**: Returns `200 OK` with plain text `Microsoft Connect Test`.

#### RFC 8908 / RFC 8910 Captive Portal API
* **Endpoint**: `GET /api/captive-portal/rfc8908`
* **Purpose**: Standardized JSON endpoint advertised to modern smartphones via DHCP Option 114.
* **Response When Unauthenticated (200 OK)**:
  ```json
  {
    "captive": true,
    "user-portal-url": "http://192.168.50.1/",
    "venue-info-url": "http://192.168.50.1/"
  }
  ```
* **Response When Authenticated (200 OK)**:
  ```json
  {
    "captive": false,
    "user-portal-url": "http://192.168.50.1/",
    "venue-info-url": "http://192.168.50.1/"
  }
  ```

---

## 9. Frontend Usage

The frontend is a single-page React application optimized for mobile smartphone displays.

### Visual Components & Customer Interaction Flow

1. **Top Header & Network Badge**:
   * Displays the brand header with the Zuke logo and caption *"Customer Wi-Fi - Internet Access"*.
   * Features the `WifiBadge` component confirming connection: `Connected to: Zuke WiFi`.
2. **Initial Status Check**:
   * On mount, `App.tsx` calls `checkStatus()`.
   * Displays a clean `LoadingSpinner` with *"Checking connection status..."*.
   * If the device is already authenticated, it skips registration and immediately renders `SuccessScreen`.
3. **Registration Form Card**:
   * If unauthenticated, displays the registration card: *"Welcome to Zuke Internet Access - Enjoy fast, reliable internet while you visit us."*
4. **Name Input**:
   * Single-line text input with a user icon.
   * Client-side validation ensures the field is not blank and is under 100 characters.
5. **Email Input**:
   * Single-line email input with a mail icon.
   * Client-side regex validation verifies email syntax before dispatching network requests.
6. **Marketing Consent Checkbox**:
   * *"I agree to receive Zuke marketing communications."* (Optional, defaults to unchecked).
7. **Submit Button**:
   * Styled in high-contrast Zuke Orange: *"Get Internet Access"*.
8. **Loading State**:
   * When submitted, inputs are disabled and the button switches to an animated spinner displaying *"Connecting..."*.
9. **Error Alert (`ErrorAlert.tsx`)**:
   * If validation fails or the server encounters an error, a red banner displays the specific message with a dismiss button.
10. **Success Screen (`SuccessScreen.tsx`)**:
    * Displays a green checkmark badge: *"You're connected! Welcome to Zuke."*
    * Shows the device IP, network status (*Active*), and access period (*8 Hours Unrestricted*).
    * Includes a *"Start Browsing the Web"* button linking to `https://www.google.com`.
    * Includes a *"Check Connection Status"* link to re-verify connectivity.

### How the Frontend Communicates with Flask

All network requests are handled in `frontend/src/services/api.ts`:
* **Registration**: Dispatches `POST /api/captive-portal/register` with JSON payload `{ name, email, marketing_consent }`.
* **Session Storage**: Upon successful registration, the backend returns a `session.token`. The frontend stores this token in browser `localStorage` under `zuke_session_token` to maintain session persistence across page refreshes.
* **Status Check**: Calls `GET /api/captive-portal/status?token=<token>` to query remaining session validity.

---

# First-Time Raspberry Pi Setup

This section walks you through preparing the Raspberry Pi, downloading the project, and running your very first diagnostic before making any configuration changes.

Follow these steps in this exact order:

## Step 1: Connect to the Raspberry Pi

For the initial gateway setup, the Raspberry Pi should preferably be connected to your existing internet router or network switch using a physical **Ethernet cable**.

### Why Ethernet Is Strongly Recommended:
* **Dedicated Management Channel**: During installation, the Raspberry Pi's internal Wi-Fi interface (`wlan0`) will be reconfigured into an open wireless Access Point named `Zuke WiFi`. If you were administering the Pi over Wi-Fi, you would lose your connection as soon as the wireless radio is reconfigured.
* **Separation of Concerns**: Using Ethernet for initial setup keeps your administrative SSH connection completely separate from the Wi-Fi interface being reconfigured.
* **Stable Internet Uplink**: An active Ethernet connection provides reliable internet access for downloading system packages and cloning the repository.

> ⚠️ **IMPORTANT:** Do NOT apply any gateway configuration yet. The Raspberry Pi should simply be powered on and connected to your local network via Ethernet.

---

## Step 2: Open the Raspberry Pi Terminal

All commands in this section are **Raspberry Pi Linux terminal commands**.

If you are working directly on the Raspberry Pi with a monitor and keyboard:
* Open the terminal application from the desktop or log into the Linux console.

If you are administering the Raspberry Pi remotely over the network using **SSH**:
* Open PowerShell (on Windows) or Terminal (on macOS/Linux).
* Connect to your Raspberry Pi using SSH while it is connected to your existing network via Ethernet.
* *Note*: The exact SSH command depends on your Raspberry Pi OS user account, configured hostname, or DHCP IP address assigned by your router (for example: `ssh <username>@<pi-ip-address>` or `ssh <username>@<hostname>.local`).

Verify that your terminal prompt shows that you are logged into the Raspberry Pi (for example: `user@raspberrypi:~ $`).

---

## Step 3: Verify Git Is Available

> 🟢 **SAFE / READ-ONLY:** Inspects whether Git is installed on the Raspberry Pi without making changes.

Before cloning the repository, verify that Git is installed on your Raspberry Pi:

```bash
git --version
```

* **If Git is installed**: You will see output like `git version 2.39.5` (or similar). Proceed directly to Step 4.
* **If Git is not installed**: Install Git from the official Debian/Raspberry Pi OS package repositories before proceeding:
  ```bash
  sudo apt update && sudo apt install -y git
  ```

---

## Step 4: Clone the Repository

> 🟢 **SAFE / READ-ONLY:** Downloads the project files from GitHub onto the Raspberry Pi. This does not alter network interfaces or system services.

Clone the official Zuke Wi-Fi Gateway repository onto your Raspberry Pi:

```bash
git clone https://github.com/learningwithshaun/Zuke-Pi-Wi-FI-Gateway.git
```

This command downloads the complete Zuke Wi-Fi Gateway project from GitHub into a new folder named `Zuke-Pi-Wi-FI-Gateway` in your current working directory.

---

## Step 5: Enter the Project Directory

Navigate into the cloned repository folder:

```bash
cd Zuke-Pi-Wi-FI-Gateway
```

> 📌 **NOTE:** All subsequent project commands throughout this guide assume that your terminal is inside this `Zuke-Pi-Wi-FI-Gateway` directory.


---

## Step 6: Verify the Project Files

> 🟢 **SAFE / READ-ONLY:** Inspects directory contents to verify a complete download.

Confirm that the repository contains the expected project files and folders:

```bash
ls -la
```

Verify that the following core directories exist:
* `backend/` — Flask application, models, routes, database schema, and test suite.
* `frontend/` — React single-page application and UI components.
* `deploy/` — Gateway configuration templates, systemd units, and setup scripts.

Next, verify that the deployment scripts exist under `deploy/scripts/`:

```bash
ls -la deploy/scripts/
```

You should see all four operational scripts:
* `00-verify-hardware.sh` — Hardware & network diagnostic script.
* `01-install-packages.sh` — Package installation script.
* `02-setup-gateway.sh` — Gateway configuration & staging script.
* `99-rollback-gateway.sh` — System rollback & recovery script.

---

## Step 7: Run the Read-Only Hardware Inspection

> 🟢 **SAFE / READ-ONLY:** Non-destructive hardware and network diagnostic. This command does NOT modify the system.

Execute the hardware diagnostic script. This **must be the FIRST Zuke deployment script run** on the physical Raspberry Pi:

```bash
bash deploy/scripts/00-verify-hardware.sh
```

### What `00-verify-hardware.sh` Checks:
* **Raspberry Pi Model**: Verifies hardware generation (Pi 3, 4, 5, etc.) via `/proc/device-tree/model`.
* **Operating System & Kernel**: Checks distribution release, kernel version, and architecture.
* **Network Interfaces**: Enumerates all available Ethernet and Wi-Fi network interfaces.
* **WAN Uplink Route**: Detects default gateway, primary uplink adapter (`eth0` or `end0`), and assigned IP address.
* **Wi-Fi Interface & AP Capability**: Identifies wireless hardware (`wlan0`) and confirms that the wireless driver supports **AP (Access Point) mode**.
* **Subnet Conflict Analysis**: Checks whether the proposed guest Wi-Fi subnet (`192.168.50.0/24`) is already used by the venue router.
* **Core Port Status**: Verifies availability of ports 22, 53, 67, 80, and 5000.

### What This Script Does NOT Do:
To ensure complete safety, `00-verify-hardware.sh`:
* Does **NOT** install or remove any packages.
* Does **NOT** change the firewall or load nftables rules.
* Does **NOT** configure or enable `hostapd`.
* Does **NOT** configure or enable `dnsmasq`.
* Does **NOT** change the gateway or routing tables.
* Does **NOT** alter the Wi-Fi configuration or SSID.

---

## Step 8: STOP AND REVIEW THE OUTPUT

> ⚠️ **CRITICAL STOPPING POINT:**
> **Do NOT continue to package installation or gateway setup until the hardware inspection output has been thoroughly reviewed.**

Before proceeding to any system-modifying steps, carefully inspect the terminal output from Step 7 and confirm the following key items:

| Inspection Item | What to Look For | What Must Be Confirmed |
| :--- | :--- | :--- |
| **1. WAN Uplink Interface** | Output under `[4/7] Default Internet Route (WAN)` | Confirms which interface provides internet access (typically `eth0` or `end0`) and shows an active IP address. |
| **2. Wi-Fi Interface** | Output under `[5/7] Wireless Interfaces` | Confirms which wireless device will become the Wi-Fi Access Point (typically `wlan0`). |
| **3. AP Mode Support** | Output line: `AP Mode : SUPPORTED ✓` | Confirms the wireless chip supports broadcasting as an access point. If it shows `NOT SUPPORTED ✗`, do NOT continue. |
| **4. Subnet Conflict** | Output line: `Proposed subnet (192.168.50.0/24) is clear. No conflicts detected ✓` | Confirms the venue router is NOT using `192.168.50.x`. If a conflict is detected, you must set a different `SUBNET_BASE` in `gateway.env` (e.g. `192.168.60`) before continuing. |
| **5. Operating System** | Output under `[1/7] System Information` | Confirms a compatible Debian/Raspberry Pi OS Bookworm Linux environment. |

Only after all of these checks pass should you proceed to package installation!

---

## 10. Raspberry Pi Hardware Inspection Reference

This section provides in-depth technical details on the 7 diagnostics performed by `00-verify-hardware.sh`.

### Running the Diagnostic

> 🟢 **SAFE / READ-ONLY:** Non-destructive hardware and network diagnostic tool.

From the project root:
```bash
bash deploy/scripts/00-verify-hardware.sh
```

*(Or from `/opt/zuke`: `cd /opt/zuke && bash deploy/scripts/00-verify-hardware.sh`)*

### Detailed Technical Breakdown of the 7 Checks

1. **System Information**: Verifies Raspberry Pi OS distribution (`/etc/os-release`), Linux kernel version (`uname -r`), and CPU architecture (`uname -m`).
2. **Hardware Model**: Reads `/proc/device-tree/model` to identify whether you are running on a Raspberry Pi 3, 4, 5, or another board.
3. **Available Network Interfaces**: Enumerates all detected physical network devices using `ip -brief link show`.
4. **Default Internet Route (WAN)**:
   * Inspects `ip route show default` to determine which interface connects the Pi to the venue router and internet.
   * Extracts the primary uplink interface name (typically `eth0` or `end0`).
   * Extracts the upstream router IP and the Raspberry Pi's WAN IP.
5. **Wireless Interfaces & AP Capability**:
   * Queries `iw dev` to find wireless radios (typically `wlan0`).
   * Examines `iw phy info` supported interface modes to verify that the wireless card supports **AP mode**.
6. **Subnet Conflict Analysis**:
   * Checks whether the proposed guest Wi-Fi subnet (`192.168.50.0/24`) is already being used on the venue network.
   * If the salon router is already using `192.168.50.x`, a warning is displayed so you can change the guest subnet before continuing.
7. **Core Port Availability**:
   * Inspects ports `22` (SSH), `53` (DNS), `67` (DHCP), `80` (HTTP), and `5000` (Flask) to ensure no conflicting daemons are blocking required services.

### What to Look for in the Output

* **Hardware Model**: Should state `Raspberry Pi 4 Model B`, `Raspberry Pi 3 Model B Plus`, etc.
* **Primary Uplink**: Should show an interface with a default route (e.g. `eth0`) and an assigned IP address from your router.
* **AP Mode**: Must report: `AP Mode : SUPPORTED ✓`.
* **Subnet Safety**: Must report: `Proposed subnet (192.168.50.0/24) is clear. No conflicts detected ✓`.
* **Ports**: Port 22 should be in use by SSH (normal); ports 53, 67, 80 should be available.

> ⚠️ **STOP AND RESOLVE IF:**
> 1. AP Mode shows `NOT SUPPORTED ✗`: Your Wi-Fi adapter or driver does not support Access Point broadcasting.
> 2. Subnet conflict shows `WARNING: Subnet 192.168.50.0/24 is ALREADY in use`: You must edit `SUBNET_BASE` in `gateway.env` (e.g., set `192.168.60`) before proceeding!

---

## 11. Raspberry Pi Installation

Once hardware verification succeeds, install the required Linux packages.

### Installation Command (Run on Raspberry Pi)

> 🟡 **INSTALLATION / SYSTEM CHANGE:** This command downloads and installs system software packages using `apt-get`. Requires root privileges (`sudo`).

```bash
sudo bash deploy/scripts/01-install-packages.sh
```

*(Or: `cd /opt/zuke && sudo bash deploy/scripts/01-install-packages.sh`)*

### What Packages Are Installed and Why

| Package | Purpose in Gateway |
| :--- | :--- |
| **`hostapd`** | Turns the Raspberry Pi's internal Wi-Fi chip into an IEEE 802.11b/g/n access point broadcasting the network. |
| **`dnsmasq`** | Handles DHCP IP address assignment and acts as a local DNS resolver for connecting guest phones. |
| **`nftables`** | Modern kernel packet classifier handling NAT masquerade, captive portal redirect rules, and authenticated IP tracking. |
| **`iw` & `wireless-tools`** | CLI utilities for querying wireless physical interfaces, signal levels, and capabilities. |
| **`rfkill`** | Utility to check and unblock wireless hardware blocks. |
| **`iproute2`** | Provides low-level Linux networking tools (`ip` command suite). |
| **`nginx`** | Production reverse proxy serving static React SPA assets on port 80 and forwarding API calls to Python. |
| **`python3`, `python3-pip`, `python3-venv`** | Python runtime and isolated virtual environment support. |
| **`curl` & `ca-certificates`** | Network utilities for testing HTTP endpoints and validating security certificates. |

### Post-Install Actions Performed by the Script
1. Temporarily stops and disables `hostapd` and `dnsmasq` so unconfigured daemons do not crash or cause boot-time errors.
2. Unblocks the Wi-Fi radio via `rfkill unblock wifi`.

---

## 12. Raspberry Pi Configuration

Gateway settings are managed through `deploy/config/gateway.env`.

### Creating the Configuration File

On the Raspberry Pi:
```bash
cp /opt/zuke/deploy/config/gateway.env.example /opt/zuke/deploy/config/gateway.env
nano /opt/zuke/deploy/config/gateway.env
```

### Configurable Variables Reference

| Variable | What It Controls | Example Value | Required? | Impact If Configured Incorrectly |
| :--- | :--- | :--- | :--- | :--- |
| **`WAN_IFACE`** | Internet uplink interface name (Ethernet cable to venue router). | `eth0` or `end0` | Optional (auto-detected if blank) | If set to an invalid interface, the Pi cannot route guest traffic to the internet. |
| **`WLAN_IFACE`** | Wi-Fi radio interface name. | `wlan0` | Optional (auto-detected if blank) | If set incorrectly, `hostapd` will fail to start and no Wi-Fi network will be broadcast. |
| **`WIFI_SSID`** | The wireless network name displayed on customers' phones. | `"Zuke WiFi"` | Required (default: `"Zuke WiFi"`) | If blank or containing illegal characters, `hostapd` will fail to start. |
| **`WIFI_CHANNEL`** | 2.4GHz Wi-Fi channel frequency. | `6` (options: 1 to 13; recommended 1, 6, or 11) | Required | If set to a heavily congested channel in the salon, customer Wi-Fi will suffer high latency or packet loss. |
| **`WIFI_COUNTRY_CODE`** | 2-letter ISO country code for wireless regulatory compliance. | `"ZA"` (South Africa) or `"US"`, `"GB"` | Required | If incorrect, regulatory limits may disable specific channels or restrict radio transmission power. |
| **`SUBNET_BASE`** | The first three octets of the guest IP subnet. | `"192.168.50"` | Required | **CRITICAL:** If this matches the venue router's subnet (e.g. both use `192.168.1`), IP routing conflicts will break all internet connectivity! |
| **`GATEWAY_IP`** | The static IP address assigned to the Pi on the Wi-Fi interface. | `"${SUBNET_BASE}.1"` (`192.168.50.1`) | Required | Connecting clients use this IP as their default gateway and DNS server. |
| **`NETMASK`** | Subnet mask for the guest Wi-Fi network. | `"255.255.255.0"` | Required | Incorrect mask can prevent phones from communicating with the gateway. |
| **`DHCP_RANGE_START`** | The lowest IP address assigned to guest devices by DHCP. | `"${SUBNET_BASE}.10"` (`192.168.50.10`) | Required | Must be on the same subnet as `GATEWAY_IP`. |
| **`DHCP_RANGE_END`** | The highest IP address assigned to guest devices by DHCP. | `"${SUBNET_BASE}.250"` (`192.168.50.250`) | Required | Defines maximum concurrent DHCP clients (~240 devices). |
| **`DHCP_LEASE_TIME`** | How long a device keeps its assigned IP address. | `"8h"` | Required | Must match or exceed the session duration so IP remains unchanged during the visit. |
| **`BACKEND_PORT`** | Port where Gunicorn/Flask listens locally. | `5000` | Required | If altered without updating Nginx proxy pass, web API will return 502 Bad Gateway. |
| **`FRONTEND_PORT`** | Port where Nginx serves the captive portal. | `80` | Required | Must be 80; captive portal detection relies on standard unencrypted HTTP. |
| **`PORTAL_URL`** | Full landing page URL sent to phones via RFC 8908 DHCP option 114. | `"http://${GATEWAY_IP}/"` (`http://192.168.50.1/`) | Required | If malformed, smartphones will fail to trigger the automatic captive portal prompt. |
| **`ZUKE_ROOT`** | Installation directory of the project on the Pi. | `"/opt/zuke"` | Required | Incorrect path breaks service units and script staging. |
| **`BACKEND_DIR`** | Backend code directory. | `"${ZUKE_ROOT}/backend"` | Required | Referenced by systemd unit for execution. |
| **`FRONTEND_DIST_DIR`**| Path to compiled React build files. | `"${ZUKE_ROOT}/frontend/dist"` | Required | Nginx root directive points to this folder; 404/403 occurs if path is invalid. |
| **`DATA_DIR`** | Path to SQLite database file storage. | `"${ZUKE_ROOT}/data"` | Required | Must have write permissions for SQLite. |
| **`BACKUP_DIR`** | Directory where system configuration backups are preserved. | `"/etc/zuke/backups"` | Required | Pre-deployment backups are stored here before any system files are altered. |

---

## 13. Deployment Dry Run

Before making any changes to the Raspberry Pi's active networking, always perform a dry run.

### Dry-Run Command (Run on Raspberry Pi)

> 🟢 **SAFE / READ-ONLY:** Generates and stages configuration templates in `/tmp/` and creates a backup without altering any live network interfaces or active services.

```bash
sudo bash deploy/scripts/02-setup-gateway.sh
```

*(Or: `cd /opt/zuke && sudo bash deploy/scripts/02-setup-gateway.sh`)*

### What the Dry Run Script Does

1. **Software Package Verification**: Confirms that `hostapd`, `dnsmasq`, `nft`, `nginx`, and `python3` are all installed.
2. **Interface Detection**: Detects your primary internet uplink (`WAN_IFACE`) and Wi-Fi interface (`WLAN_IFACE`), confirming they are separate physical adapters.
3. **Subnet Conflict Guard**: Checks your WAN IP against `SUBNET_BASE`. If the upstream router is on the same subnet, the script halts immediately before changing any files.
4. **Automatic Pre-Deployment Backup**: Creates a timestamped archive under `/etc/zuke/backups/backup_<YYYYMMDD_HHMMSS>/` capturing existing configurations:
   - `/etc/hostapd/hostapd.conf` & `/etc/default/hostapd`
   - `/etc/dnsmasq.conf` & `/etc/dnsmasq.d/`
   - `/etc/nftables.conf` & `/etc/nftables.d/`
   - `/etc/nginx/sites-available/` & `sites-enabled/`
   - `/etc/NetworkManager/conf.d/`
   - `/etc/sysctl.d/99-zuke-forward.conf`
   - Saves pointer file `/etc/zuke/backups/latest`.
5. **Templated Configuration Staging**: Populates a temporary staging directory (e.g. `/tmp/zuke-stage-20261008_163000/`) with rendered configuration files:
   - `hostapd.conf` (Wi-Fi AP configuration)
   - `zuke-dnsmasq.conf` (DHCP pool, gateway, and Option 114)
   - `zuke.nft` (nftables table inet zuke)
   - `nginx-zuke.conf` (Nginx virtual host and proxy pass)
   - `99-zuke-forward.conf` (`net.ipv4.ip_forward = 1`)
   - `99-zuke-unmanage.conf` (NetworkManager interface unmanage rule)

### What the Dry Run Does NOT Change

* Does **not** touch your active Wi-Fi radio or Ethernet adapter.
* Does **not** assign or flush IP addresses.
* Does **not** copy files into `/etc/hostapd`, `/etc/dnsmasq.d`, `/etc/nftables.d`, or `/etc/nginx`.
* Does **not** enable IP forwarding in the running Linux kernel.
* Does **not** restart or reload any systemd services.

### How to Inspect the Staged Files

Review the generated files in the staging directory shown in the script output:
```bash
# View the staged Wi-Fi configuration:
cat /tmp/zuke-stage-*/hostapd.conf

# View the staged DHCP & DNS configuration:
cat /tmp/zuke-stage-*/zuke-dnsmasq.conf

# View the staged nftables firewall rules:
cat /tmp/zuke-stage-*/zuke.nft
```
Verify that `interface=wlan0`, `ssid=Zuke WiFi`, and IP addresses match your network plan.

---

## 14. Applying the Gateway Configuration

> 🔴 **GATEWAY CONFIGURATION:** This command actively converts the Raspberry Pi into the Zuke gateway. It modifies system configuration files, binds static IP `192.168.50.1` to `wlan0`, reloads firewall tables into the Linux kernel, enables IP forwarding, and activates network daemons.

### Apply Command (Run on Raspberry Pi)

Run the script with the `--apply` flag:

```bash
sudo bash deploy/scripts/02-setup-gateway.sh --apply
```

*(Or: `cd /opt/zuke && sudo bash deploy/scripts/02-setup-gateway.sh --apply`)*

### What Happens During the Apply Phase

1. **hostapd Configuration**:
   * Copies `hostapd.conf` into `/etc/hostapd/hostapd.conf`.
   * Unmasks `hostapd` and updates `/etc/default/hostapd` to point to the configuration file.
2. **NetworkManager Isolation**:
   * Copies `99-zuke-unmanage.conf` into `/etc/NetworkManager/conf.d/` so NetworkManager stops attempting to manage `wlan0`.
   * Reloads NetworkManager via `nmcli general reload`.
3. **Wi-Fi Interface Static IP Assignment**:
   * Flushes any existing IP configuration on the Wi-Fi interface (`wlan0`).
   * Assigns static gateway IP: `192.168.50.1/24`.
   * Brings interface link state up (`ip link set wlan0 up`).
4. **DHCP & DNS Activation**:
   * Copies `zuke-dnsmasq.conf` into `/etc/dnsmasq.d/zuke.conf`.
5. **Kernel IP Forwarding**:
   * Copies `99-zuke-forward.conf` into `/etc/sysctl.d/99-zuke-forward.conf`.
   * Applies immediately via `sysctl -p /etc/sysctl.d/99-zuke-forward.conf` (`net.ipv4.ip_forward = 1`).
6. **nftables Firewall Rules**:
   * Copies `zuke.nft` into `/etc/nftables.d/zuke.nft`.
   * Loads the isolated `table inet zuke` into the active Linux kernel with `nft -f`.
7. **Nginx Web Server**:
   * Copies `nginx-zuke.conf` into `/etc/nginx/sites-available/zuke`.
   * Removes `/etc/nginx/sites-enabled/default`.
   * Creates symlink `/etc/nginx/sites-enabled/zuke`.
8. **systemd Units**:
   * Copies `zuke-backend.service` and `zuke-nftables.service` into `/etc/systemd/system/`.
   * Executes `systemctl daemon-reload`.
9. **Service Restart & Activation**:
   * Restarts and activates: `nginx`, `dnsmasq`, `hostapd`, `zuke-nftables`, and `zuke-backend`.

### What to Expect After Deployment

* A wireless network named **"Zuke WiFi"** will appear in the Wi-Fi scan on phones and laptops nearby.
* All 5 system services will show active status:
  ```bash
  sudo systemctl status hostapd dnsmasq nginx zuke-backend zuke-nftables
  ```

---

## 15. Customer Wi-Fi Flow

Here is the complete step-by-step lifecycle of a customer connecting to the gateway:

```text
Step 1:  Customer sees "Zuke WiFi" on their smartphone or laptop Wi-Fi list.
Step 2:  Customer taps to connect (no WPA password required).
Step 3:  The phone requests an IP address via DHCP.
Step 4:  dnsmasq assigns an IP (e.g. 192.168.50.45), assigns gateway 192.168.50.1,
         and delivers DHCP Option 114 pointing to http://192.168.50.1/.
Step 5:  The phone's operating system sends a captive portal probe:
         • Android: GET /generate_204
         • Apple:   GET /hotspot-detect.html
         • Windows: GET /ncsi.txt
Step 6:  nftables redirects the HTTP port 80 traffic to Nginx on the Raspberry Pi.
Step 7:  Nginx proxies the probe to Flask. Because the IP is not yet authorized,
         Flask returns a 302 redirect to http://192.168.50.1/.
Step 8:  The smartphone automatically opens its captive portal browser displaying the React frontend.
Step 9:  The customer enters their name (e.g. "Amanda") and email ("amanda@example.com").
Step 10: Customer taps "Get Internet Access".
Step 11: The React frontend dispatches POST /api/captive-portal/register to Flask.
Step 12: Flask validates the input (valid name, valid email structure).
Step 13: SQLite updates or inserts the customer into `customers` and creates an
         `access_sessions` record with an 8-hour expiration timestamp.
Step 14: GatewayService runs:
         nft add element inet zuke authenticated_ips { 192.168.50.45 timeout 28800s }
Step 15: The phone IP is now registered in the Linux kernel's `@authenticated_ips` set.
Step 16: Future packets from 192.168.50.45 match the nftables rule:
         iifname "wlan0" oifname "eth0" ip saddr @authenticated_ips accept
Step 17: Outbound traffic is NAT-masqueraded out through eth0 to the venue router and internet.
Step 18: React transitions to the SuccessScreen, and the phone confirms full internet access.
Step 19: Exactly 8 hours later, the Linux kernel timer expires, the IP is automatically
         removed from `@authenticated_ips`, and forwarding is instantly revoked.
```

---

## 16. Testing the Complete System

Follow this step-by-step physical testing procedure using a smartphone and the Raspberry Pi:

### 1. Wi-Fi Connection Test
* [ ] On your smartphone, open Wi-Fi settings.
* [ ] Look for the SSID **"Zuke WiFi"**.
* [ ] Tap to connect. It should connect without asking for a WPA password.
* [ ] Verify that your phone received an IP address in the `192.168.50.x` range (e.g., `192.168.50.10` to `192.168.50.250`).
* [ ] On the Pi, verify the DHCP lease was recorded:
  ```bash
  cat /var/lib/misc/dnsmasq.leases
  ```

### 2. Captive Portal Detection Test
* [ ] Within a few seconds of connecting, your phone should display a notification: *"Sign in to Wi-Fi network"* or automatically pop open the captive assistant screen.
* [ ] The Zuke captive portal page should load, displaying the header: *"ZUKE - Customer Wi-Fi"* and the form card.

### 3. Registration Form & Validation Test
* [ ] Leave the name empty, enter an email, and tap *"Get Internet Access"*.
* [ ] Verify that the form displays the error: *"Please enter your name."*
* [ ] Enter a valid name, but type an invalid email (e.g. `test@invalid`), and submit.
* [ ] Verify the error: *"Please enter a valid email address."*
* [ ] Enter a valid name and valid email (e.g. `test@example.com`), check or uncheck marketing consent, and tap *"Get Internet Access"*.

### 4. Authorization & Internet Access Test
* [ ] The screen should transition to the green **"You're connected! Welcome to Zuke."** screen.
* [ ] Tap *"Start Browsing the Web"* or open your phone's browser and navigate to `https://www.google.com` or `https://news.ycombinator.com`.
* [ ] Pages should load smoothly at full speed.
* [ ] On the Raspberry Pi, verify that your phone's IP appears in the nftables set:
  ```bash
  sudo nft list set inet zuke authenticated_ips
  ```
  Expected output includes your phone's IP with a remaining timeout:
  ```text
  table inet zuke {
      set authenticated_ips {
          type ipv4_addr
          flags timeout
          elements = { 192.168.50.45 timeout 7h59m42s }
      }
  }
  ```

### 5. Expiration Test
* [ ] In the database, check the recorded session:
  ```bash
  sqlite3 /opt/zuke/backend/data/zuke.db "SELECT id, customer_id, ip_address, expires_at FROM access_sessions ORDER BY id DESC LIMIT 1;"
  ```
* [ ] To test expiration immediately without waiting 8 hours, manually revoke the IP from nftables:
  ```bash
  sudo nft delete element inet zuke authenticated_ips '{ 192.168.50.45 }'
  ```
* [ ] Attempt to load a new website on the phone; forwarding should immediately fail and redirect back to the captive portal.

### 6. Multiple Customer Test
* [ ] Connect a second phone or laptop to "Zuke WiFi".
* [ ] Verify that the second device receives a distinct IP address (e.g. `192.168.50.46`).
* [ ] Verify that the second device cannot browse the internet until it registers its own details.
* [ ] Register the second device and verify both devices browse simultaneously.

### 7. Reconnection Test
* [ ] Turn Wi-Fi off and back on on an already-registered phone.
* [ ] Reconnect to "Zuke WiFi".
* [ ] Verify that internet access resumes immediately without requiring re-registration, as long as the 8-hour session remains active.

---

## 17. Troubleshooting

Use this guide to diagnose and resolve issues on the physical Raspberry Pi:

### 1. "Zuke WiFi" Does Not Appear in Wi-Fi Scans

* **Check `hostapd` Service Status**:
  ```bash
  sudo systemctl status hostapd
  ```
* **Check for Hardware Radio Blocks**:
  ```bash
  sudo rfkill list
  ```
  If Wi-Fi is soft-blocked, unblock it:
  ```bash
  sudo rfkill unblock wifi
  ```
* **Verify Wi-Fi Interface Exists**:
  ```bash
  iw dev
  ```
  Ensure `wlan0` appears and is not in use by NetworkManager client connections.
* **Test `hostapd` Manually for Detailed Errors**:
  ```bash
  sudo hostapd /etc/hostapd/hostapd.conf
  ```

---

### 2. Phone Connects to Wi-Fi but Receives No IP Address

* **Check `dnsmasq` Service Status**:
  ```bash
  sudo systemctl status dnsmasq
  ```
* **Inspect `dnsmasq` Log File**:
  ```bash
  sudo tail -n 50 /var/log/dnsmasq-zuke.log
  ```
* **Verify Gateway IP is Assigned to `wlan0`**:
  ```bash
  ip addr show dev wlan0
  ```
  Expected: `inet 192.168.50.1/24 scope global wlan0`. If missing, reassign manually:
  ```bash
  sudo ip addr add 192.168.50.1/24 dev wlan0
  sudo ip link set wlan0 up
  ```

---

### 3. Captive Portal Does Not Open Automatically

* **Check Nginx Web Server**:
  ```bash
  sudo systemctl status nginx
  ```
* **Test Local HTTP Probe on the Pi**:
  ```bash
  curl -I http://192.168.50.1/generate_204
  ```
  Expected: `HTTP/1.1 302 Found` with `Location: http://192.168.50.1/`.
* **Understanding HTTP vs. HTTPS Redirection**:
  * Captive portal redirection operates on unencrypted **HTTP (port 80)**.
  * If a user tries to open an **HTTPS (port 443)** website (such as `https://google.com`), modern browsers intentionally reject silent redirection because TLS certificates cannot match the intercepted domain. This security design prevents man-in-the-middle attacks.
  * Captive portals rely on OS detection probes (e.g., `generate_204`, `hotspot-detect.html`) sent over plain HTTP and RFC 8908 DHCP Option 114 to trigger the system captive browser automatically.
  * If the portal does not pop up automatically, open the phone's browser and navigate to: **`http://192.168.50.1`** or **`http://neverssl.com`**.

---

### 4. Portal Web Page Loads, but Registration Fails

* **Check Flask / Gunicorn Backend Service**:
  ```bash
  sudo systemctl status zuke-backend
  ```
* **Inspect Backend Error Logs**:
  ```bash
  sudo journalctl -u zuke-backend -n 50 --no-pager
  ```
* **Inspect Gunicorn Log Files**:
  ```bash
  sudo tail -n 50 /var/log/zuke/error.log
  ```
* **Check SQLite Permissions**:
  Ensure the database directory is writable:
  ```bash
  ls -la /opt/zuke/backend/data/
  ```

---

### 5. Registration Succeeds, but Internet Does Not Work

* **Check Kernel IP Forwarding**:
  ```bash
  sysctl net.ipv4.ip_forward
  ```
  Must output: `net.ipv4.ip_forward = 1`. If `0`, enable it:
  ```bash
  sudo sysctl -w net.ipv4.ip_forward=1
  ```
* **Check nftables Authenticated IP Set**:
  ```bash
  sudo nft list set inet zuke authenticated_ips
  ```
  Verify that your phone's IP appears inside the elements list.
* **Verify Pi Internet Connectivity (WAN)**:
  Test whether the Raspberry Pi itself has working internet:
  ```bash
  ping -c 3 8.8.8.8
  ```
  If this fails, check the Ethernet cable connected to the venue router.
* **Inspect Active Firewall Rules**:
  ```bash
  sudo nft list table inet zuke
  ```
  Verify that the `postrouting` masquerade rule and `forward` rules are loaded.

---

### 6. Internet Access Works but Expires Incorrectly

* Inspect the current kernel timeout for client elements:
  ```bash
  sudo nft list set inet zuke authenticated_ips
  ```
* Verify `SESSION_DURATION_HOURS` in `/opt/zuke/deploy/config/gateway.env` (default is 8).

---

### 7. SSH Connection Lost During Configuration

* The Zuke deployment specifically preserves SSH connectivity:
  * Port 22 is explicitly permitted on all interfaces in `nftables.conf.template` (`tcp dport 22 accept`).
  * The WAN Ethernet interface (`eth0` / `end0`) remains untouched by `hostapd` and `dnsmasq`.
* **Recovery**: Connect your PC to the same physical router/switch as the Raspberry Pi's Ethernet port and SSH using the Pi's Ethernet IP address.

---

### 8. Emergency Rollback

If you need to quickly revert all changes and restore original networking:
```bash
sudo bash /opt/zuke/deploy/scripts/99-rollback-gateway.sh
```

---

## 18. Rollback / Uninstallation

The repository includes a dedicated non-destructive rollback utility to restore your Raspberry Pi to its pre-gateway state.

### Rollback Command (Run on Raspberry Pi)

> 🟡 **INSTALLATION / SYSTEM CHANGE:** Stops Zuke services, removes Zuke firewall tables, cleans up drop-in configurations, and restores files from the latest backup archive.

```bash
sudo bash deploy/scripts/99-rollback-gateway.sh
```

*(Or: `cd /opt/zuke && sudo bash deploy/scripts/99-rollback-gateway.sh`)*

*(You can optionally supply a specific backup directory: `sudo bash 99-rollback-gateway.sh /etc/zuke/backups/backup_20261008_163000`).*

### What the Rollback Script Reverts

1. **Stops and Disables Zuke Services**:
   * Stops `zuke-backend.service`, `zuke-nftables.service`, and `hostapd`.
   * Disables them so they will not start on system boot.
2. **Deletes nftables Table**:
   * Executes `nft delete table inet zuke`.
   * Removes `/etc/nftables.d/zuke.nft`.
   * Leaves all other system firewall rules completely untouched.
3. **Removes Drop-in Configurations**:
   * Deletes `/etc/dnsmasq.d/zuke.conf`.
   * Deletes `/etc/hostapd/hostapd.conf`.
   * Deletes `/etc/NetworkManager/conf.d/99-zuke-unmanage.conf`.
   * Deletes `/etc/nginx/sites-available/zuke` and symlink `/etc/nginx/sites-enabled/zuke`.
   * Deletes `/etc/sysctl.d/99-zuke-forward.conf`.
   * Deletes `/etc/systemd/system/zuke-backend.service` and `zuke-nftables.service`.
4. **Restores Backed-up Files**:
   * Restores original configuration files from `/etc/zuke/backups/latest`.
5. **Reloads System Daemons**:
   * Executes `systemctl daemon-reload`.
   * Reloads NetworkManager via `nmcli general reload`.
   * Restarts standard `nginx` and `dnsmasq` services.

### When to Use Rollback
* When testing different network configurations or subnets.
* Before repurposing the Raspberry Pi hardware for another project.
* If a deployment configuration error causes unexpected behavior.

---

## 19. Security Considerations

A production captive portal must balance ease of guest access with network security and system hardening.

### Security Features Already Implemented in Zuke

* **Dedicated, Isolated Firewall Table**: All gateway rules reside strictly inside `table inet zuke`. Default system tables and other services are left untouched.
* **Persistent SSH Access Protection**: Port 22 is explicitly accepted on all interfaces in the input chain (`tcp dport 22 accept`), ensuring administrators never get locked out during setup or testing.
* **Kernel-Enforced Expiration**: Device authorization uses kernel-level timers in nftables (`flags timeout`). Expired IPs are purged directly by the Linux kernel, preventing stale access even if Python or Gunicorn crashes.
* **Cryptographic Session Tokens**: Tokens are generated via Python's `secrets.token_urlsafe(32)`, providing 256 bits of cryptographically strong entropy.
* **SQL Injection Prevention**: All database queries use SQLite parameterized statements (`?` placeholders).
* **Strict Input Validation**: Names are bounded between 1 and 100 characters, and emails are verified against standard email syntax before database queries are executed.
* **No Hardcoded Secrets**: Sensitive settings are loaded from `.env` files which are excluded from Git via `.gitignore`.
* **Fast-Fail Unauthenticated TCP**: Unauthenticated TCP forwarding attempts trigger immediate TCP resets (`reject with tcp reset`), allowing client devices to fail fast and trigger the captive portal prompt instead of hanging on timeouts.

### Recommended Security Enhancements

The following security enhancements are not currently enabled by default:

* **Client Isolation (`ap_isolate=1`)** — *Not currently enabled by default*:
  * In `deploy/config/hostapd.conf.template`, open Wi-Fi allows client devices on the subnet to discover each other's broadcast traffic. For public venues, adding `ap_isolate=1` to hostapd prevents guest devices from communicating with one another.
* **API Rate Limiting** — *Not currently implemented*:
  * Adding Nginx `limit_req_zone` rules to `/api/captive-portal/register` (e.g. 5 requests per minute per IP) prevents malicious scripts from flooding the database with fake registrations.
* **Database File Permissions** — *Recommended Manual Hardening*:
  * Ensure the SQLite database file and directory are restricted to the application user:
    ```bash
    sudo chmod 700 /opt/zuke/backend/data
    sudo chmod 600 /opt/zuke/backend/data/zuke.db
    ```
* **SSH Hardening** — *Recommended Host Hardening*:
  * Disable password authentication in `/etc/ssh/sshd_config` and enforce SSH key authentication.
* **HTTPS on Captive Portal Landing Page** — *Not currently implemented*:
  * The initial captive portal redirection requires plain HTTP (port 80) because browsers reject SSL redirection without certificate warnings. However, an internal trusted certificate or Let's Encrypt domain can be configured for post-registration management if desired.

---

## 20. Production Considerations

Before deploying the Zuke gateway in a live salon or business environment, verify the following operational factors:

### 1. Reliable Power Supply
* The Raspberry Pi must use an **official Raspberry Pi power supply** (5.1V / 3.0A USB-C for Pi 4; 5V / 5.0A for Pi 5).
* Standard mobile phone chargers cause voltage dips under radio load, resulting in Wi-Fi packet loss, SD card filesystem corruption, or silent kernel reboots.
* Verify power stability with:
  ```bash
  vcgencmd get_throttled
  ```
  *(Output `throttled=0x0` confirms clean, stable power without undervoltage).*

### 2. Physical Placement & Wi-Fi Coverage
* The onboard Raspberry Pi Wi-Fi antenna is a compact PCB trace antenna designed for indoor coverage within roughly **10 to 15 meters** through drywalls.
* For larger venues or locations with thick concrete walls, consider:
  * Placing the Raspberry Pi in an elevated, central location.
  * Plugging a supported high-gain external USB Wi-Fi dongle into a USB 3.0 port.

### 3. Wi-Fi Channel Planning
* Run an environment frequency scan to identify overlapping Wi-Fi networks from neighboring shops:
  ```bash
  sudo iw dev wlan0 scan | grep -E 'SSID|freq:'
  ```
* Choose an uncontested 2.4GHz non-overlapping channel (**1, 6, or 11**) and set `WIFI_CHANNEL` in `gateway.env`.

### 4. Venue Router Subnet Planning
* Always confirm the salon's primary router does not use `192.168.50.0/24`. If the venue router uses `192.168.50.x`, set `SUBNET_BASE="192.168.60"` in `gateway.env` to prevent routing collisions.

### 5. Automated Database Backups
* SQLite stores all customer emails in `/opt/zuke/backend/data/zuke.db`.
* Set up a daily cron job to copy this file to an external USB flash drive or offsite cloud backup:
  ```bash
  sqlite3 /opt/zuke/backend/data/zuke.db ".backup '/opt/zuke/backups/zuke_$(date +%F).db'"
  ```

### 6. Log Rotation
* Gunicorn and dnsmasq write logs to `/var/log/zuke/` and `/var/log/dnsmasq-zuke.log`.
* On busy networks, configure standard `logrotate` to prevent logs from filling the microSD card.

---

## 21. Useful Commands

A quick-reference guide of valid commands used throughout development and deployment.

### Development (Windows / PowerShell)

```powershell
# Activate Python virtual environment:
cd backend
.\venv\Scripts\Activate.ps1

# Run backend tests (from project root):
python -m pytest backend/tests -v

# Run Flask local server:
python app.py

# Test backend health check:
Invoke-RestMethod http://127.0.0.1:5000/api/health

# Run React frontend development server:
cd ..\frontend
npm run dev

# Build frontend for production:
npm run build
```

### Raspberry Pi Diagnostics (Read-Only)

> 🟢 **SAFE:** Read-only diagnostic commands.

```bash
# Run Zuke hardware and network diagnostic:
cd /opt/zuke/deploy/scripts
bash 00-verify-hardware.sh

# Check wireless interface capabilities and AP mode:
iw list | grep -A 10 "Supported interface modes"

# Check detected IP addresses:
ip -brief addr show

# Check default gateway routing:
ip route show default

# Check listening network ports:
ss -tulpn
```

### Service Management (Raspberry Pi)

> 🟡 **INSTALLATION / SYSTEM CHANGE:** Starts, stops, or restarts system daemons.

```bash
# Check status of all Zuke gateway services:
sudo systemctl status zuke-backend zuke-nftables hostapd dnsmasq nginx

# Restart backend service:
sudo systemctl restart zuke-backend

# Restart Wi-Fi access point:
sudo systemctl restart hostapd

# Restart DHCP & DNS service:
sudo systemctl restart dnsmasq

# Reload Nginx web server:
sudo systemctl reload nginx
```

### Logs & Monitoring (Raspberry Pi)

> 🟢 **SAFE / READ-ONLY:** Read-only inspection commands.

```bash
# Stream Flask/Gunicorn backend logs in real time:
sudo journalctl -u zuke-backend -f

# View Nginx access and error logs:
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# View dnsmasq DHCP assignment logs:
sudo tail -f /var/log/dnsmasq-zuke.log

# View active DHCP client leases:
cat /var/lib/misc/dnsmasq.leases
```

### Networking & Firewall (Raspberry Pi)

```bash
# View all currently authenticated client IPs and remaining lease times:
sudo nft list set inet zuke authenticated_ips

# View the full Zuke firewall table:
sudo nft list table inet zuke

# Manually authorize an IP address for 8 hours (28800s):
sudo nft add element inet zuke authenticated_ips '{ 192.168.50.45 timeout 28800s }'

# Manually revoke an IP address:
sudo nft delete element inet zuke authenticated_ips '{ 192.168.50.45 }'

# Check kernel IP forwarding flag (must return 1):
sysctl net.ipv4.ip_forward
```

### Deployment & Rollback (Raspberry Pi)

```bash
# Install packages:
sudo bash deploy/scripts/01-install-packages.sh

# Run dry run (staging & backup only):
sudo bash deploy/scripts/02-setup-gateway.sh

# Apply configuration and activate gateway:
sudo bash deploy/scripts/02-setup-gateway.sh --apply

# Roll back system to previous state:
sudo bash deploy/scripts/99-rollback-gateway.sh
```

---

## 22. Complete Setup Checklist

Use this checkbox checklist to track your progress from initial development to live deployment:

### Phase 1: Local Development & Verification
- [ ] Clone repository to local development PC
- [ ] Set up Python virtual environment in `backend/` and install `requirements.txt`
- [ ] Run backend tests (`python -m pytest backend/tests -v`) and verify 14 passing tests
- [ ] Install frontend Node dependencies (`npm install` in `frontend/`)
- [ ] Start backend (`python app.py`) and frontend (`npm run dev`)
- [ ] Verify registration form, validation, and status in browser at `http://localhost:5173`
- [ ] Run production frontend build (`npm run build` in `frontend/`)

### Phase 2: First-Time Raspberry Pi Setup (Steps 1 to 8)
- [ ] Connect Raspberry Pi to existing network using Ethernet (Step 1)
- [ ] Open Raspberry Pi terminal / connect using SSH (Step 2)
- [ ] Verify Git is available: `git --version` (Step 3)
- [ ] Clone repository: `git clone https://github.com/learningwithshaun/Zuke-Pi-Wi-FI-Gateway.git` (Step 4)
- [ ] Enter project directory: `cd Zuke-Pi-Wi-FI-Gateway` (Step 5)
- [ ] Verify project files: `ls -la` and `ls -la deploy/scripts/` (Step 6)
- [ ] Run read-only hardware inspection: `bash deploy/scripts/00-verify-hardware.sh` (Step 7)
- [ ] STOP AND REVIEW: Confirm WAN uplink, Wi-Fi device, AP mode supported, no subnet conflict, and OS supported (Step 8)

### Phase 3: Package Installation, Build & Configuration (Steps 9 to 10)
- [ ] Install packages: `sudo bash deploy/scripts/01-install-packages.sh` (Step 9)
- [ ] Set up Python virtual environment in `backend/` and install requirements (`./venv/bin/pip install -r requirements.txt`)
- [ ] Build React frontend assets: `npm install && npm run build` in `frontend/`
- [ ] Configure `gateway.env`: copy `deploy/config/gateway.env.example` to `deploy/config/gateway.env` (Step 10)
- [ ] Confirm or customize Wi-Fi SSID, channel, country code, and subnet

### Phase 4: Staging & Gateway Activation (Steps 11 to 13)
- [ ] Run deployment dry run: `sudo bash deploy/scripts/02-setup-gateway.sh` (Step 11)
- [ ] Confirm backup archive created in `/etc/zuke/backups/`
- [ ] Review staged configuration templates in `/tmp/zuke-stage-*/` (Step 12)
- [ ] Apply gateway configuration: `sudo bash deploy/scripts/02-setup-gateway.sh --apply` (Step 13)
- [ ] Confirm `hostapd`, `dnsmasq`, `nginx`, `zuke-backend`, and `zuke-nftables` are active

### Phase 5: Verification & Customer Testing (Steps 14 to 18)
- [ ] Test `Zuke WiFi`: Scan on a smartphone and connect (Step 14)
- [ ] Test captive portal: Verify sign-in prompt opens automatically (Step 15)
- [ ] Test customer registration: Submit Name and Email (Step 16)
- [ ] Test internet access: Confirm external web browsing works (Step 17)
- [ ] Test session expiration: Verify nftables set timer and database session (Step 18)
- [ ] Test reconnection: Verify reconnected devices maintain authorized access

### Phase 6: Operational Readiness & Rollback (Step 19)
- [ ] Confirm SSH remains accessible via Ethernet
- [ ] Familiarize team with rollback command: `sudo bash deploy/scripts/99-rollback-gateway.sh` (Step 19)

