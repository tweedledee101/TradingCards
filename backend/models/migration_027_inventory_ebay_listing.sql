-- Link owned inventory to live eBay listings (manual, CSV, or future seller OAuth sync).
-- Enables hold-time metrics: purchase_date -> sale_date already on inventory_sales + inventory.

ALTER TABLE inventory ADD COLUMN IF NOT EXISTS ebay_item_id VARCHAR(50);
ALTER TABLE inventory ADD COLUMN IF NOT EXISTS ebay_listing_url TEXT;
ALTER TABLE inventory ADD COLUMN IF NOT EXISTS listing_ask_price DECIMAL(10, 2);
ALTER TABLE inventory ADD COLUMN IF NOT EXISTS listed_at DATE;

COMMENT ON COLUMN inventory.ebay_item_id IS 'eBay item id when this inventory row is (or was) listed for sale';
COMMENT ON COLUMN inventory.ebay_listing_url IS 'Canonical listing URL for seller tracking';
COMMENT ON COLUMN inventory.listing_ask_price IS 'Current BIN / ask when listed (optional snapshot)';
COMMENT ON COLUMN inventory.listed_at IS 'Date the card was listed on eBay (optional)';

CREATE INDEX IF NOT EXISTS idx_inventory_ebay_item_id ON inventory (ebay_item_id) WHERE ebay_item_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_inventory_account_status ON inventory (account_id, status);
