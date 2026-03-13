-- Migration: Add parallel and ungraded_price columns to cards table

-- Add new columns
ALTER TABLE cards ADD COLUMN IF NOT EXISTS parallel VARCHAR(100) DEFAULT 'Base';
ALTER TABLE cards ADD COLUMN IF NOT EXISTS ungraded_price DECIMAL(10, 2);

-- Drop old unique constraint
ALTER TABLE cards DROP CONSTRAINT IF EXISTS cards_player_name_card_year_card_set_card_number_key;

-- Add new unique constraint including parallel
ALTER TABLE cards ADD CONSTRAINT cards_unique_variant 
    UNIQUE(player_name, card_year, card_set, card_number, parallel);
