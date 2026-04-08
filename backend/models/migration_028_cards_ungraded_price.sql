-- Ensure cards.ungraded_price exists (ORM + auction pipeline).
-- migration_add_parallel.sql could roll back entirely when ADD CONSTRAINT conflicted
-- with migration_003's cards_unique_variant, leaving this column missing.

ALTER TABLE cards ADD COLUMN IF NOT EXISTS ungraded_price DECIMAL(10, 2);
