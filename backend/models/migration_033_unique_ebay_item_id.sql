-- Enforce unique ebay_item_id on opportunities (prevents duplicate rows).
-- Already applied manually on RDS 2026-04-17; this migration makes it tracked.
DROP INDEX IF EXISTS idx_opportunities_ebay_item_id;
CREATE UNIQUE INDEX IF NOT EXISTS idx_opportunities_ebay_item_id
    ON opportunities(ebay_item_id) WHERE ebay_item_id IS NOT NULL;
