-- Add last_seen_at for opportunity accumulation across pipeline runs.
-- Instead of deleting all BIN opps each run, we upsert by ebay_item_id
-- and age out listings not seen in 7 days.
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMP DEFAULT NOW();

-- Backfill existing rows
UPDATE opportunities SET last_seen_at = created_at WHERE last_seen_at IS NULL;

-- Index for cleanup queries
CREATE INDEX IF NOT EXISTS idx_opportunities_last_seen ON opportunities (last_seen_at);
CREATE INDEX IF NOT EXISTS idx_opportunities_ebay_item_id ON opportunities (ebay_item_id);
