-- Migration 005: Sell-Through Metrics & Holding Time
-- Track how fast cards sell and average days on market

-- Add columns to price_trends for sell-through metrics
ALTER TABLE price_trends ADD COLUMN IF NOT EXISTS avg_days_to_sell DECIMAL(5,2);
ALTER TABLE price_trends ADD COLUMN IF NOT EXISTS sell_through_rate DECIMAL(5,2);
ALTER TABLE price_trends ADD COLUMN IF NOT EXISTS active_listings_count INTEGER DEFAULT 0;
ALTER TABLE price_trends ADD COLUMN IF NOT EXISTS listings_to_sales_ratio DECIMAL(5,2);

-- Add columns for realistic profit calculations
ALTER TABLE price_trends ADD COLUMN IF NOT EXISTS estimated_net_profit DECIMAL(10,2);
ALTER TABLE price_trends ADD COLUMN IF NOT EXISTS roi_with_fees DECIMAL(5,2);
ALTER TABLE price_trends ADD COLUMN IF NOT EXISTS days_to_breakeven INTEGER;

-- Create view for quick flip opportunities
CREATE OR REPLACE VIEW quick_flip_opportunities AS
SELECT 
    c.id,
    c.player_name,
    c.card_year,
    c.card_set,
    c.sport,
    pt.avg_price,
    pt.hotness_score,
    pt.velocity_score,
    pt.avg_days_to_sell,
    pt.sell_through_rate,
    pt.listings_to_sales_ratio,
    pt.estimated_net_profit,
    pt.roi_with_fees,
    CASE 
        WHEN pt.avg_days_to_sell <= 7 THEN 'Fast'
        WHEN pt.avg_days_to_sell <= 14 THEN 'Moderate'
        ELSE 'Slow'
    END as turnover_speed,
    CASE
        WHEN pt.sell_through_rate >= 50 THEN 'High Demand'
        WHEN pt.sell_through_rate >= 25 THEN 'Moderate Demand'
        ELSE 'Low Demand'
    END as demand_level
FROM cards c
JOIN price_trends pt ON c.id = pt.card_id
WHERE pt.trend_date = CURRENT_DATE
AND pt.hotness_score > 40
AND pt.avg_days_to_sell IS NOT NULL
AND pt.avg_days_to_sell <= 14  -- Only show cards that sell within 2 weeks
AND pt.estimated_net_profit > 5  -- Minimum $5 net profit
ORDER BY 
    (pt.roi_with_fees / NULLIF(pt.avg_days_to_sell, 0)) DESC;  -- ROI per day

COMMENT ON VIEW quick_flip_opportunities IS 'Cards with fast turnover and good net profit';
COMMENT ON COLUMN price_trends.avg_days_to_sell IS 'Average days from listing to sale';
COMMENT ON COLUMN price_trends.sell_through_rate IS 'Percentage of listings that sold (sales / total listings * 100)';
COMMENT ON COLUMN price_trends.listings_to_sales_ratio IS 'Active listings divided by recent sales (lower = better)';
COMMENT ON COLUMN price_trends.estimated_net_profit IS 'Profit after eBay fees (13%), shipping ($5), and acquisition cost';
COMMENT ON COLUMN price_trends.roi_with_fees IS 'ROI percentage after all fees and costs';
COMMENT ON COLUMN price_trends.days_to_breakeven IS 'Estimated days until card sells based on historical velocity';
