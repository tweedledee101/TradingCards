-- Sport on opportunities (UI filter); persisted pipeline skips for audit jobs.

ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS sport VARCHAR(50) NOT NULL DEFAULT 'Baseball';

CREATE INDEX IF NOT EXISTS idx_opportunities_sport ON opportunities (sport);
CREATE INDEX IF NOT EXISTS idx_opportunities_sport_listing ON opportunities (sport, listing_type);

CREATE TABLE IF NOT EXISTS pipeline_listing_skips (
    id SERIAL PRIMARY KEY,
    pipeline VARCHAR(32) NOT NULL,
    skip_reason VARCHAR(64) NOT NULL,
    ebay_item_id VARCHAR(50),
    sport VARCHAR(50),
    search_query TEXT,
    pipeline_card_label TEXT,
    ebay_title TEXT,
    buy_price DECIMAL(10, 2),
    scp_price DECIMAL(10, 2),
    ratio DECIMAL(10, 4),
    extra JSONB,
    job_run_id INTEGER REFERENCES job_runs(id) ON DELETE SET NULL,
    audited_at TIMESTAMP,
    audit_result JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_skips_pipeline_reason ON pipeline_listing_skips (pipeline, skip_reason);
CREATE INDEX IF NOT EXISTS idx_pipeline_skips_audited ON pipeline_listing_skips (audited_at);
CREATE INDEX IF NOT EXISTS idx_pipeline_skips_job ON pipeline_listing_skips (job_run_id);

COMMENT ON TABLE pipeline_listing_skips IS 'BIN/auction listings filtered out during scan — for false-junk audits and metrics';
COMMENT ON COLUMN opportunities.sport IS 'Pipeline sport context (Baseball, Basketball, Football, etc.)';
