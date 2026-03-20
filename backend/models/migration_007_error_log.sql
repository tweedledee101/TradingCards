-- Migration 007: Error log and runtime observability
-- Tracks runtime errors, warnings, and notable events for pattern detection

CREATE TABLE IF NOT EXISTS error_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    level VARCHAR(10) NOT NULL DEFAULT 'ERROR',        -- DEBUG, INFO, WARN, ERROR, CRITICAL
    category VARCHAR(50),                               -- e.g. 'reprint_match', 'wrong_variation', 'scraper_timeout', 'api_error'
    source VARCHAR(100),                                -- module or endpoint that produced it
    message TEXT NOT NULL,
    context JSONB,                                      -- structured data: card_id, query, url, request_id, timing, etc.
    request_id VARCHAR(36),                             -- ties log entries to a single API request
    stack_trace TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_error_log_timestamp ON error_log (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_error_log_level ON error_log (level);
CREATE INDEX IF NOT EXISTS idx_error_log_category ON error_log (category);
CREATE INDEX IF NOT EXISTS idx_error_log_request_id ON error_log (request_id);
CREATE INDEX IF NOT EXISTS idx_error_log_source ON error_log (source);

-- Partial index: only errors and above (most common query)
CREATE INDEX IF NOT EXISTS idx_error_log_errors_only ON error_log (timestamp DESC) WHERE level IN ('ERROR', 'CRITICAL');
