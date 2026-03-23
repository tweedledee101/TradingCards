-- Migration 013: SCP search cache
-- Caches SCP Selenium search results so the auction pipeline
-- doesn't re-scrape the same card across runs.
-- Cache is keyed on player+year+card_number. Expires after 24 hours.

CREATE TABLE IF NOT EXISTS scp_cache (
    id SERIAL PRIMARY KEY,
    player_name VARCHAR(255) NOT NULL,
    card_year INTEGER,
    card_number VARCHAR(50) NOT NULL,
    search_query TEXT,
    variants JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scp_cache_lookup
    ON scp_cache (lower(player_name), card_year, lower(card_number));
