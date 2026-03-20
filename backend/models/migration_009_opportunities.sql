-- Migration 009: Opportunities table
-- Stores pipeline results so the UI can read them instantly

CREATE TABLE IF NOT EXISTS opportunities (
    id SERIAL PRIMARY KEY,
    player_name VARCHAR(255) NOT NULL,
    card_year INTEGER,
    card_set VARCHAR(255),
    card_number VARCHAR(50),
    parallel VARCHAR(100),
    scp_title TEXT,
    scp_price DECIMAL(10, 2) NOT NULL,
    buy_price DECIMAL(10, 2) NOT NULL,
    profit DECIMAL(10, 2) NOT NULL,
    roi DECIMAL(8, 2) NOT NULL,
    ebay_title TEXT,
    ebay_url TEXT,
    ebay_item_id VARCHAR(50),
    flagged BOOLEAN DEFAULT FALSE,
    scan_id INTEGER REFERENCES job_runs(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_opportunities_profit ON opportunities (profit DESC);
CREATE INDEX IF NOT EXISTS idx_opportunities_roi ON opportunities (roi DESC);
CREATE INDEX IF NOT EXISTS idx_opportunities_scan_id ON opportunities (scan_id);
CREATE INDEX IF NOT EXISTS idx_opportunities_player ON opportunities (player_name);
CREATE INDEX IF NOT EXISTS idx_opportunities_flagged ON opportunities (flagged);
