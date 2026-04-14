-- eBay Browse API search result cache
-- Avoids redundant API calls when the same variation is searched within TTL window.
-- Active BIN listings don't change fast; 12h TTL is safe.
CREATE TABLE IF NOT EXISTS ebay_search_cache (
    id SERIAL PRIMARY KEY,
    search_query TEXT NOT NULL,
    query_hash TEXT NOT NULL,
    results JSONB NOT NULL DEFAULT '[]',
    result_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ebay_search_cache_hash ON ebay_search_cache (query_hash);
CREATE INDEX IF NOT EXISTS idx_ebay_search_cache_created ON ebay_search_cache (created_at);
