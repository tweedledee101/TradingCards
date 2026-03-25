-- Migration 018: Auth + Multi-Tenancy
-- Adds accounts, users tables and account_id to all tenant-scoped tables.
-- Cognito sub (external identity) lives on users table.
-- account_id is nullable initially to preserve existing data; backfill follows.

-- ============================================================
-- 1. Core auth tables
-- ============================================================

CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    account_type VARCHAR(20) NOT NULL DEFAULT 'individual',  -- 'individual' or 'business'
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    cognito_sub VARCHAR(128) UNIQUE,          -- Cognito User Pool sub (set after first login)
    email VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(255),
    role VARCHAR(20) NOT NULL DEFAULT 'owner', -- 'owner', 'admin', 'member'
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_account ON users(account_id);
CREATE INDEX IF NOT EXISTS idx_users_cognito ON users(cognito_sub);

-- ============================================================
-- 2. Add account_id to tenant tables (nullable for backfill)
-- ============================================================

ALTER TABLE business_goals     ADD COLUMN IF NOT EXISTS account_id INTEGER REFERENCES accounts(id);
ALTER TABLE capital_transactions ADD COLUMN IF NOT EXISTS account_id INTEGER REFERENCES accounts(id);
ALTER TABLE daily_plans         ADD COLUMN IF NOT EXISTS account_id INTEGER REFERENCES accounts(id);
ALTER TABLE daily_snapshots     ADD COLUMN IF NOT EXISTS account_id INTEGER REFERENCES accounts(id);
ALTER TABLE inventory           ADD COLUMN IF NOT EXISTS account_id INTEGER REFERENCES accounts(id);
ALTER TABLE watchlist           ADD COLUMN IF NOT EXISTS account_id INTEGER REFERENCES accounts(id);
ALTER TABLE scheduled_bids      ADD COLUMN IF NOT EXISTS account_id INTEGER REFERENCES accounts(id);
ALTER TABLE inventory_sales     ADD COLUMN IF NOT EXISTS account_id INTEGER REFERENCES accounts(id);

-- ============================================================
-- 3. Backfill: create default account, assign all existing data
-- ============================================================

INSERT INTO accounts (id, name, account_type)
VALUES (1, 'Default Account', 'individual')
ON CONFLICT (id) DO NOTHING;

UPDATE business_goals      SET account_id = 1 WHERE account_id IS NULL;
UPDATE capital_transactions SET account_id = 1 WHERE account_id IS NULL;
UPDATE daily_plans          SET account_id = 1 WHERE account_id IS NULL;
UPDATE daily_snapshots      SET account_id = 1 WHERE account_id IS NULL;
UPDATE inventory            SET account_id = 1 WHERE account_id IS NULL;
UPDATE watchlist            SET account_id = 1 WHERE account_id IS NULL;
UPDATE scheduled_bids       SET account_id = 1 WHERE account_id IS NULL;
UPDATE inventory_sales      SET account_id = 1 WHERE account_id IS NULL;

-- ============================================================
-- 4. Make account_id NOT NULL after backfill
-- ============================================================

ALTER TABLE business_goals      ALTER COLUMN account_id SET NOT NULL;
ALTER TABLE capital_transactions ALTER COLUMN account_id SET NOT NULL;
ALTER TABLE daily_plans          ALTER COLUMN account_id SET NOT NULL;
ALTER TABLE daily_snapshots      ALTER COLUMN account_id SET NOT NULL;
ALTER TABLE inventory            ALTER COLUMN account_id SET NOT NULL;
ALTER TABLE watchlist            ALTER COLUMN account_id SET NOT NULL;
ALTER TABLE scheduled_bids       ALTER COLUMN account_id SET NOT NULL;
ALTER TABLE inventory_sales      ALTER COLUMN account_id SET NOT NULL;

-- Set defaults so existing code doesn't break until auth is wired
ALTER TABLE business_goals      ALTER COLUMN account_id SET DEFAULT 1;
ALTER TABLE capital_transactions ALTER COLUMN account_id SET DEFAULT 1;
ALTER TABLE daily_plans          ALTER COLUMN account_id SET DEFAULT 1;
ALTER TABLE daily_snapshots      ALTER COLUMN account_id SET DEFAULT 1;
ALTER TABLE inventory            ALTER COLUMN account_id SET DEFAULT 1;
ALTER TABLE watchlist            ALTER COLUMN account_id SET DEFAULT 1;
ALTER TABLE scheduled_bids       ALTER COLUMN account_id SET DEFAULT 1;
ALTER TABLE inventory_sales      ALTER COLUMN account_id SET DEFAULT 1;

-- ============================================================
-- 5. Indexes for tenant queries
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_business_goals_account ON business_goals(account_id);
CREATE INDEX IF NOT EXISTS idx_capital_txn_account ON capital_transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_daily_plans_account ON daily_plans(account_id);
CREATE INDEX IF NOT EXISTS idx_daily_snapshots_account ON daily_snapshots(account_id);
CREATE INDEX IF NOT EXISTS idx_inventory_account ON inventory(account_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_account ON watchlist(account_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_bids_account ON scheduled_bids(account_id);
CREATE INDEX IF NOT EXISTS idx_inventory_sales_account ON inventory_sales(account_id);

-- ============================================================
-- 6. Fix daily_snapshots unique constraint for multi-tenant
-- ============================================================

ALTER TABLE daily_snapshots DROP CONSTRAINT IF EXISTS daily_snapshots_snapshot_date_key;
ALTER TABLE daily_snapshots ADD CONSTRAINT daily_snapshots_account_date_key UNIQUE (account_id, snapshot_date);

-- Fix watchlist unique constraint (was card_id only, now per-account)
ALTER TABLE watchlist DROP CONSTRAINT IF EXISTS watchlist_card_id_key;
ALTER TABLE watchlist ADD CONSTRAINT watchlist_account_card_key UNIQUE (account_id, card_id);

-- Reset sequence so next account gets id=2
SELECT setval('accounts_id_seq', GREATEST((SELECT MAX(id) FROM accounts), 1));
