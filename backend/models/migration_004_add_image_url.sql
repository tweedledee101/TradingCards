-- Migration 004: Add image_url column to cards table
-- Purpose: Store eBay card images for visual identification

ALTER TABLE cards ADD COLUMN IF NOT EXISTS image_url VARCHAR(500);

-- Add index for faster image lookups
CREATE INDEX IF NOT EXISTS idx_cards_image_url ON cards(image_url) WHERE image_url IS NOT NULL;
