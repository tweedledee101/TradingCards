-- Add SCP product URL to market_rates for direct price lookups
ALTER TABLE market_rates ADD COLUMN IF NOT EXISTS scp_product_url TEXT;
