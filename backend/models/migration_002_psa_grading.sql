-- Migration 002: Add PSA Grading Population Table
-- Date: 2025-02-XX
-- Purpose: Store PSA grading data from NovaAct scraper

-- Create grading_population table
CREATE TABLE IF NOT EXISTS grading_population (
    id SERIAL PRIMARY KEY,
    card_id INTEGER NOT NULL REFERENCES cards(id) ON DELETE CASCADE,
    grade_company VARCHAR(10) NOT NULL DEFAULT 'PSA',
    psa_10_count INTEGER DEFAULT 0,
    psa_9_count INTEGER DEFAULT 0,
    psa_8_count INTEGER DEFAULT 0,
    total_graded INTEGER DEFAULT 0,
    psa_10_rate DECIMAL(5,4),  -- e.g., 0.2250 = 22.5%
    date_recorded DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(card_id, date_recorded)
);

-- Create index for faster queries
CREATE INDEX idx_grading_population_card_id ON grading_population(card_id);
CREATE INDEX idx_grading_population_date ON grading_population(date_recorded);

-- Add comment
COMMENT ON TABLE grading_population IS 'PSA grading population data from NovaAct scraper';
COMMENT ON COLUMN grading_population.psa_10_rate IS 'Percentage of PSA 10 grades (0-1 scale)';
