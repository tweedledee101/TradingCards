-- Migration 010: Add listing_type to opportunities table
-- Tracks whether opportunity is BIN or auction
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS listing_type VARCHAR(20) DEFAULT 'buy_it_now';
