-- Migration: Add ebay_search_url column to cards table

ALTER TABLE cards ADD COLUMN IF NOT EXISTS ebay_search_url TEXT;
