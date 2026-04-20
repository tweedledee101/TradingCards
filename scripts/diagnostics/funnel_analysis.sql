-- Liquid card funnel analysis
-- 1. How many liquid variants exist
-- 2. How many were searched on eBay
-- 3. How many returned results
-- 4. How many became opportunities

-- Step 1: Liquid variants
SELECT 'liquid_variants' as metric, COUNT(*) as cnt
FROM (
    SELECT DISTINCT sc.player_name, sc.card_year, sc.card_number, v->>'parallel' as parallel
    FROM scp_cache sc, jsonb_array_elements(sc.variants) v
    WHERE v->>'volume' IS NOT NULL AND v->>'volume' != ''
    AND (v->>'ungraded')::numeric BETWEEN 20 AND 1000
    AND (LOWER(v->>'volume') LIKE '%per day%' OR LOWER(v->>'volume') LIKE '%per week%')
) sub

UNION ALL

-- Step 2: Total eBay searches done
SELECT 'total_ebay_searches', COUNT(*) FROM ebay_search_cache

UNION ALL

-- Step 3: Searches with results
SELECT 'searches_with_results', COUNT(*) FROM ebay_search_cache WHERE result_count > 0

UNION ALL

-- Step 4: Dead searches
SELECT 'dead_searches', COUNT(*) FROM ebay_search_cache WHERE result_count = 0

UNION ALL

-- Step 5: Current opportunities
SELECT 'total_opportunities', COUNT(*) FROM opportunities

UNION ALL

SELECT 'bin_opportunities', COUNT(*) FROM opportunities WHERE listing_type = 'buy_it_now'

UNION ALL

SELECT 'auction_opportunities', COUNT(*) FROM opportunities WHERE listing_type = 'auction';
