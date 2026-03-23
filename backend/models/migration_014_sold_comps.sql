-- Migration 014: sold_comps table for 130point eBay sold data cache
-- Stores actual completed sale prices from 130point.com (eBay sold aggregator)
-- Used as pricing fallback and volume signal

CREATE TABLE IF NOT EXISTS sold_comps (
    id SERIAL PRIMARY KEY,
    player_name VARCHAR(255) NOT NULL,
    card_year INTEGER,
    card_set VARCHAR(255),
    card_number VARCHAR(50),
    parallel VARCHAR(100),
    sale_price DECIMAL(10, 2) NOT NULL,
    sale_type VARCHAR(20),  -- 'auction' or 'fixed'
    sale_date VARCHAR(50),  -- as reported by 130point
    listing_title TEXT,
    source VARCHAR(50) DEFAULT '130point',
    search_query TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sold_comps_player ON sold_comps (lower(player_name));
CREATE INDEX IF NOT EXISTS idx_sold_comps_lookup ON sold_comps (lower(player_name), card_year, lower(card_number));
CREATE INDEX IF NOT EXISTS idx_sold_comps_created ON sold_comps (created_at);
