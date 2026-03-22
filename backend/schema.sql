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
-- Row Level Security (RLS) policies
-- ---------------------------------------------------------------------------
-- Enable RLS on all tables
ALTER TABLE scans ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE waitlist ENABLE ROW LEVEL SECURITY;

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

-- Public read access for scans (shared scan results)
CREATE POLICY "Public read scans"
    ON scans FOR SELECT
    USING (true);
