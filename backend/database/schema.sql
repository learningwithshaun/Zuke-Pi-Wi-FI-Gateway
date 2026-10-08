-- Zuke Wi-Fi Gateway SQLite Schema

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    marketing_consent INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS access_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    ip_address TEXT NOT NULL,
    session_token TEXT NOT NULL UNIQUE,
    authenticated INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_sessions_ip ON access_sessions(ip_address);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON access_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON access_sessions(expires_at);

