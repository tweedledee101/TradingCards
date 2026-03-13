-- Migration 003: Add Price Benchmarks Table
-- Date: 2025-02-XX
-- Purpose: Store price benchmark data from Card Ladder / 130point

-- Create price_benchmarks table
CREATE TABLE IF NOT EXISTS price_benchmarks (
    id SERIAL PRIMARY KEY,
    card_id INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,  -- 'cardladder', '130point', etc.
    current_price DECIMAL(10, 2),
    price_7d_ago DECIMAL(10, 2),
    price_30d_ago DECIMAL(10, 2),
    change_7d DECIMAL(5, 2),  -- Percentage change
    change_30d DECIMAL(5, 2),
    velocity_rating VARCHAR(20),  -- 'Hot', 'Warm', 'Cold', 'Stable'
    market_cap DECIMAL(12, 2),  -- Total market value
    date_recorded DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(card_id, source, date_recorded)
);

-- Create indexes
CREATE INDEX idx_price_benchmarks_card_id ON price_benchmarks(card_id);
CREATE INDEX idx_price_benchmarks_source ON price_benchmarks(source);
CREATE INDEX idx_price_benchmarks_date ON price_benchmarks(date_recorded);

-- Add comments
COMMENT ON TABLE price_benchmarks IS 'Price benchmark data from Card Ladder, 130point, etc.';
COMMENT ON COLUMN price_benchmarks.velocity_rating IS 'Market velocity: Hot, Warm, Cold, Stable';
COMMENT ON COLUMN price_benchmarks.market_cap IS 'Total estimated market value';
