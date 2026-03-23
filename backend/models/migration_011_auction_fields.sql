-- Migration 011: Add auction-specific fields to opportunities
-- Supports the auction-first pipeline (find_auction_opportunities.py)

ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS shipping DECIMAL(10,2) DEFAULT 0;
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS bid_count INTEGER DEFAULT 0;
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS end_time TIMESTAMP;
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS scp_volume TEXT;
