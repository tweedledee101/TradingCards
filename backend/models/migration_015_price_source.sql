-- Migration 015: Add price_source to opportunities
-- Tracks where the pricing came from: 'scp', 'sold_comps', 'ebay_comps'
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS price_source VARCHAR(20) DEFAULT 'scp';
