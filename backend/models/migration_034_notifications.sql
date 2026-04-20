-- Migration: notifications table
-- Stores in-app notifications (sale alerts, pipeline results, system messages)

CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL DEFAULT 1 REFERENCES accounts(id),
    type VARCHAR(50) NOT NULL,  -- 'sale', 'opportunity', 'pipeline', 'system'
    title VARCHAR(255) NOT NULL,
    message TEXT,
    data JSONB DEFAULT '{}',  -- structured payload (sale details, opportunity link, etc.)
    read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_account_read
    ON notifications(account_id, read, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_type
    ON notifications(type, created_at DESC);
