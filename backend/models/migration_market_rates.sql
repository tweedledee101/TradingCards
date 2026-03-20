CREATE TABLE IF NOT EXISTS market_rates (
    id SERIAL PRIMARY KEY,
    card_id INTEGER REFERENCES cards(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL DEFAULT 'sportscardspro',
    ungraded_price NUMERIC(10,2),
    grade_9_price NUMERIC(10,2),
    psa_10_price NUMERIC(10,2),
    date_recorded DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(card_id, source, date_recorded)
);
CREATE INDEX IF NOT EXISTS idx_market_rates_card_id ON market_rates(card_id);
CREATE INDEX IF NOT EXISTS idx_market_rates_date ON market_rates(date_recorded);
