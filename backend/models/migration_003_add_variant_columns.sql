-- Migration 003: Add variant differentiation columns
-- Fixes critical issue where all card variants (base, silver, red ice, autos) are grouped together

-- Add parallel column (e.g., "Base", "Silver", "Red Ice", "Purple Wave")
ALTER TABLE cards ADD COLUMN IF NOT EXISTS parallel VARCHAR(100);

-- Add grade_company column (e.g., "PSA", "BGS", "SGC", "Raw")
ALTER TABLE cards ADD COLUMN IF NOT EXISTS grade_company VARCHAR(20);

-- Add grade_value column (e.g., 9, 10, 9.5)
ALTER TABLE cards ADD COLUMN IF NOT EXISTS grade_value DECIMAL(3, 1);

-- Update unique constraint to include variant columns
ALTER TABLE cards DROP CONSTRAINT IF EXISTS cards_player_name_card_year_card_set_card_number_key;
ALTER TABLE cards ADD CONSTRAINT cards_unique_variant 
    UNIQUE(player_name, card_year, card_set, card_number, parallel, grade_company, grade_value);

-- Create index for variant queries
CREATE INDEX IF NOT EXISTS idx_cards_variant ON cards(player_name, card_year, card_set, parallel, grade_company, grade_value);

-- Add comment
COMMENT ON COLUMN cards.parallel IS 'Card parallel/variant (Base, Silver, Red Ice, etc.)';
COMMENT ON COLUMN cards.grade_company IS 'Grading company (PSA, BGS, SGC) or Raw';
COMMENT ON COLUMN cards.grade_value IS 'Grade value (1-10) or NULL for raw cards';
