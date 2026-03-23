-- Migration 016: Scheduled bids (snipe queue)
CREATE TABLE IF NOT EXISTS scheduled_bids (
    id SERIAL PRIMARY KEY,
    player_name VARCHAR(255) NOT NULL,
    card_year INTEGER,
    card_set VARCHAR(255),
    card_number VARCHAR(50),
    parallel VARCHAR(100),
    max_bid DECIMAL(10,2) NOT NULL,
    snipe_seconds INTEGER NOT NULL DEFAULT 10,
    ebay_item_id VARCHAR(50),
    ebay_url TEXT,
    image_url TEXT,
    scp_price DECIMAL(10,2),
    end_time TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_scheduled_bids_status ON scheduled_bids(status);
CREATE INDEX idx_scheduled_bids_end_time ON scheduled_bids(end_time);
