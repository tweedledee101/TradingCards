-- Migration: Add parallel and ungraded_price columns to cards table
-- Constraint changes removed: migration_003_add_variant_columns.sql already defines
-- cards_unique_variant (incl. grade columns). Re-adding the same constraint name here
-- failed on fresh DBs and rolled back the whole transaction, skipping ungraded_price.

ALTER TABLE cards ADD COLUMN IF NOT EXISTS parallel VARCHAR(100) DEFAULT 'Base';
ALTER TABLE cards ADD COLUMN IF NOT EXISTS ungraded_price DECIMAL(10, 2);
