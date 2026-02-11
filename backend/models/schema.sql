-- Trading Card Platform Database Schema

-- Cards table: master list of all cards
CREATE TABLE IF NOT EXISTS cards (
    id SERIAL PRIMARY KEY,
    player_name VARCHAR(255) NOT NULL,
    card_year INTEGER NOT NULL,
    card_set VARCHAR(255),
    card_number VARCHAR(50),
    is_rookie BOOLEAN DEFAULT FALSE,
    sport VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player_name, card_year, card_set, card_number)
);

-- Sales data from eBay
CREATE TABLE IF NOT EXISTS sales (
    id SERIAL PRIMARY KEY,
    card_id INTEGER REFERENCES cards(id),
    sale_price DECIMAL(10, 2) NOT NULL,
    sale_date TIMESTAMP NOT NULL,
    listing_title TEXT,
    ebay_item_id VARCHAR(50) UNIQUE,
    condition VARCHAR(50),
    graded BOOLEAN DEFAULT FALSE,
    grade_company VARCHAR(20),
    grade_value DECIMAL(3, 1),
    source VARCHAR(50) DEFAULT 'ebay',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Active listings snapshot
CREATE TABLE IF NOT EXISTS active_listings (
    id SERIAL PRIMARY KEY,
    card_id INTEGER REFERENCES cards(id),
    listing_price DECIMAL(10, 2) NOT NULL,
    listing_type VARCHAR(20), -- 'auction' or 'buy_it_now'
    ebay_item_id VARCHAR(50) UNIQUE,
    snapshot_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- PSA population data
CREATE TABLE IF NOT EXISTS psa_population (
    id SERIAL PRIMARY KEY,
    card_id INTEGER REFERENCES cards(id),
    grade_value DECIMAL(3, 1) NOT NULL,
    population_count INTEGER NOT NULL,
    snapshot_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(card_id, grade_value, snapshot_date)
);

-- Price trends (computed daily)
CREATE TABLE IF NOT EXISTS price_trends (
    id SERIAL PRIMARY KEY,
    card_id INTEGER REFERENCES cards(id),
    trend_date DATE NOT NULL,
    avg_price DECIMAL(10, 2),
    median_price DECIMAL(10, 2),
    sales_count INTEGER DEFAULT 0,
    active_listings_count INTEGER DEFAULT 0,
    price_change_7d DECIMAL(5, 2), -- percentage
    price_change_30d DECIMAL(5, 2),
    velocity_score DECIMAL(5, 2), -- sales / listings ratio
    hotness_score DECIMAL(5, 2), -- computed metric
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(card_id, trend_date)
);

-- Social signals
CREATE TABLE IF NOT EXISTS social_signals (
    id SERIAL PRIMARY KEY,
    card_id INTEGER REFERENCES cards(id),
    platform VARCHAR(50), -- 'twitter', 'reddit'
    mention_count INTEGER DEFAULT 0,
    sentiment_score DECIMAL(3, 2), -- -1 to 1
    signal_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_sales_card_date ON sales(card_id, sale_date);
CREATE INDEX idx_sales_date ON sales(sale_date);
CREATE INDEX idx_cards_rookie ON cards(is_rookie);
CREATE INDEX idx_price_trends_date ON price_trends(trend_date);
CREATE INDEX idx_price_trends_hotness ON price_trends(hotness_score DESC);
