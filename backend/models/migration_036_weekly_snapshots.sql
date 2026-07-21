-- Weekly performance snapshots (pulled from eBay API)
CREATE TABLE IF NOT EXISTS weekly_snapshots (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL DEFAULT 1 REFERENCES accounts(id),
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    -- Inventory
    active_listings INTEGER DEFAULT 0,
    total_inventory_ask DECIMAL(10,2) DEFAULT 0,
    listings_under_5 INTEGER DEFAULT 0,
    listings_5_to_25 INTEGER DEFAULT 0,
    listings_25_to_100 INTEGER DEFAULT 0,
    listings_over_100 INTEGER DEFAULT 0,
    median_listing_price DECIMAL(10,2) DEFAULT 0,
    -- Sales
    items_sold INTEGER DEFAULT 0,
    total_revenue DECIMAL(10,2) DEFAULT 0,
    avg_sale_price DECIMAL(10,2) DEFAULT 0,
    sell_through_pct DECIMAL(5,1) DEFAULT 0,
    -- Purchases
    items_bought INTEGER DEFAULT 0,
    total_spent DECIMAL(10,2) DEFAULT 0,
    avg_buy_price DECIMAL(10,2) DEFAULT 0,
    -- Bidding
    bids_won INTEGER DEFAULT 0,
    bids_lost INTEGER DEFAULT 0,
    win_rate_pct DECIMAL(5,1) DEFAULT 0,
    -- Watchlist
    watchlist_count INTEGER DEFAULT 0,
    -- Computed
    net_profit_est DECIMAL(10,2) DEFAULT 0,
    inventory_value_change DECIMAL(10,2) DEFAULT 0,
    -- Raw data for drill-down
    raw_data JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_weekly_snapshots_account_week
    ON weekly_snapshots(account_id, week_start);
