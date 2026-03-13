-- Migration 004: Accuracy Tracking
-- Track prediction accuracy to validate scoring algorithms

CREATE TABLE IF NOT EXISTS prediction_tracking (
    id SERIAL PRIMARY KEY,
    card_id INTEGER REFERENCES cards(id) ON DELETE CASCADE,
    
    -- Prediction data (at time of prediction)
    prediction_date DATE NOT NULL,
    predicted_hotness DECIMAL(5,2),
    predicted_velocity DECIMAL(5,2),
    predicted_price DECIMAL(10,2),
    buy_zone_price DECIMAL(10,2),
    
    -- Actual outcome (7 days later)
    outcome_date DATE,
    actual_price DECIMAL(10,2),
    actual_velocity DECIMAL(5,2),
    price_change_pct DECIMAL(5,2),
    
    -- Accuracy metrics
    prediction_correct BOOLEAN,
    price_accuracy_pct DECIMAL(5,2),
    velocity_accuracy_pct DECIMAL(5,2),
    
    -- Notes
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_prediction_card ON prediction_tracking(card_id);
CREATE INDEX idx_prediction_date ON prediction_tracking(prediction_date);
CREATE INDEX idx_outcome_date ON prediction_tracking(outcome_date);
CREATE INDEX idx_prediction_correct ON prediction_tracking(prediction_correct);

-- View for accuracy stats
CREATE OR REPLACE VIEW accuracy_stats AS
SELECT 
    COUNT(*) as total_predictions,
    COUNT(CASE WHEN prediction_correct = true THEN 1 END) as correct_predictions,
    CASE 
        WHEN COUNT(*) > 0 THEN ROUND(COUNT(CASE WHEN prediction_correct = true THEN 1 END)::DECIMAL / COUNT(*)::DECIMAL * 100, 2)
        ELSE 0
    END as accuracy_pct,
    AVG(price_accuracy_pct) as avg_price_accuracy,
    AVG(velocity_accuracy_pct) as avg_velocity_accuracy,
    MIN(prediction_date) as first_prediction,
    MAX(prediction_date) as last_prediction
FROM prediction_tracking
WHERE outcome_date IS NOT NULL;

COMMENT ON TABLE prediction_tracking IS 'Tracks prediction accuracy to validate scoring algorithms';
COMMENT ON VIEW accuracy_stats IS 'Overall accuracy statistics for predictions';
