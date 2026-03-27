-- Clarvia AEO Scanner — Supabase Schema
-- Run this SQL in the Supabase SQL Editor to create all required tables.

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------------------------------------------------------------------
-- scans: stores every scan result
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scans (
    id              UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    scan_id         TEXT NOT NULL UNIQUE,
    url             TEXT NOT NULL,
    service_name    TEXT NOT NULL,
    clarvia_score   INTEGER NOT NULL,
    rating          TEXT NOT NULL,
    dimensions      JSONB NOT NULL,
    onchain_bonus   JSONB NOT NULL,
    recommendations JSONB NOT NULL DEFAULT '[]',
    scan_duration_ms INTEGER NOT NULL,
    scanned_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scans_scan_id ON scans (scan_id);
CREATE INDEX IF NOT EXISTS idx_scans_url ON scans (url);
CREATE INDEX IF NOT EXISTS idx_scans_created_at ON scans (created_at DESC);

-- ---------------------------------------------------------------------------
-- reports: paid report records (linked to scans and Stripe sessions)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reports (
    id                  UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    scan_id             TEXT NOT NULL REFERENCES scans(scan_id),
    stripe_session_id   TEXT,
    stripe_payment_id   TEXT,
    payment_status      TEXT NOT NULL DEFAULT 'pending',  -- pending, paid, failed
    amount_cents        INTEGER NOT NULL DEFAULT 2900,
    currency            TEXT NOT NULL DEFAULT 'usd',
    email               TEXT,
    full_report_data    JSONB,
    pdf_url             TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    paid_at             TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_reports_scan_id ON reports (scan_id);
CREATE INDEX IF NOT EXISTS idx_reports_stripe_session ON reports (stripe_session_id);

-- ---------------------------------------------------------------------------
-- waitlist: email collection for launch notifications
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS waitlist (
    id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    email       TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_waitlist_email ON waitlist (email);

-- ---------------------------------------------------------------------------
-- scan_history: time-series data for trend tracking (Data Moat A)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scan_history (
    id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    url         TEXT NOT NULL,
    scan_id     TEXT NOT NULL,
    score       INTEGER NOT NULL,
    rating      TEXT NOT NULL,
    service_name TEXT NOT NULL,
    dimensions  JSONB,
    scanned_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scan_history_url ON scan_history (url);
CREATE INDEX IF NOT EXISTS idx_scan_history_scanned_at ON scan_history (scanned_at DESC);
CREATE INDEX IF NOT EXISTS idx_scan_history_url_time ON scan_history (url, scanned_at DESC);

-- ---------------------------------------------------------------------------
-- tracked_urls: URLs registered for periodic auto-rescan (Data Moat A)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tracked_urls (
    id          UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    url         TEXT NOT NULL UNIQUE,
    service_name TEXT NOT NULL,
    category    TEXT NOT NULL DEFAULT 'general',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tracked_urls_category ON tracked_urls (category);

-- ---------------------------------------------------------------------------
-- accessibility_probes: AI agent accessibility test results (Data Moat C)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS accessibility_probes (
    id              UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    url             TEXT NOT NULL,
    probe_score     INTEGER NOT NULL,
    probe_rating    TEXT NOT NULL,
    agent_reachable BOOLEAN NOT NULL DEFAULT false,
    agent_blocked   BOOLEAN NOT NULL DEFAULT false,
    latency_ms      INTEGER,
    allows_ai       BOOLEAN NOT NULL DEFAULT true,
    discovery_count INTEGER NOT NULL DEFAULT 0,
    json_available  BOOLEAN NOT NULL DEFAULT false,
    full_result     JSONB,
    probed_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_probes_url ON accessibility_probes (url);
CREATE INDEX IF NOT EXISTS idx_probes_probed_at ON accessibility_probes (probed_at DESC);

-- ---------------------------------------------------------------------------
-- analytics_events: persistent API traffic log (survives Render restarts)
-- Replaces ephemeral JSONL files as the durable analytics store.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analytics_events (
    id              BIGSERIAL PRIMARY KEY,
    ts              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date            DATE NOT NULL DEFAULT CURRENT_DATE,
    hour            TEXT NOT NULL DEFAULT '00',
    endpoint        TEXT NOT NULL,
    method          TEXT NOT NULL DEFAULT 'GET',
    status          INTEGER NOT NULL DEFAULT 200,
    response_ms     REAL NOT NULL DEFAULT 0,
    ip_hash         TEXT NOT NULL DEFAULT '',
    ua              TEXT NOT NULL DEFAULT '',
    agent           TEXT,           -- AI agent name if identified (Claude, GPT, etc.)
    tool_activity   TEXT            -- search, scan, feed, leaderboard, etc.
);

CREATE INDEX IF NOT EXISTS idx_analytics_ts ON analytics_events (ts DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_date ON analytics_events (date DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_agent ON analytics_events (agent) WHERE agent IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_analytics_endpoint ON analytics_events (endpoint);

ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY;

-- Service role (backend) can insert and read
CREATE POLICY "Service role full access on analytics_events"
    ON analytics_events FOR ALL USING (true) WITH CHECK (true);

-- ---------------------------------------------------------------------------
-- Row Level Security (RLS) policies
-- ---------------------------------------------------------------------------
-- Enable RLS on all tables
ALTER TABLE scans ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE waitlist ENABLE ROW LEVEL SECURITY;

ALTER TABLE scan_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE tracked_urls ENABLE ROW LEVEL SECURITY;
ALTER TABLE accessibility_probes ENABLE ROW LEVEL SECURITY;

-- Allow the service role (backend) to do everything
CREATE POLICY "Service role full access on scans"
    ON scans FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on reports"
    ON reports FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on waitlist"
    ON waitlist FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on scan_history"
    ON scan_history FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on tracked_urls"
    ON tracked_urls FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on accessibility_probes"
    ON accessibility_probes FOR ALL USING (true) WITH CHECK (true);

-- Public read access for scans (shared scan results)
CREATE POLICY "Public read scans"
    ON scans FOR SELECT
    USING (true);

CREATE POLICY "Public read scan_history"
    ON scan_history FOR SELECT
    USING (true);

CREATE POLICY "Public read accessibility_probes"
    ON accessibility_probes FOR SELECT
    USING (true);
