-- Business Operating System tables (ADR-006)

CREATE TABLE IF NOT EXISTS business_goals (
    id SERIAL PRIMARY KEY,
    annual_income_target DECIMAL(10,2) NOT NULL,
    starting_capital DECIMAL(10,2) NOT NULL,
    weekly_hours_weekday DECIMAL(4,1) DEFAULT 12.5,
    weekly_hours_weekend DECIMAL(4,1) DEFAULT 8.0,
    target_margin_pct DECIMAL(5,2) DEFAULT 0.25,
    avg_shipping_cost DECIMAL(6,2) DEFAULT 4.50,
    platform_fee_pct DECIMAL(5,2) DEFAULT 0.13,
    reinvest_pct DECIMAL(5,2) DEFAULT 1.00,
    goal_start_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS daily_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL UNIQUE,
    available_capital DECIMAL(10,2),
    inventory_count INTEGER DEFAULT 0,
    inventory_cost_basis DECIMAL(10,2) DEFAULT 0,
    inventory_market_value DECIMAL(10,2) DEFAULT 0,
    listed_count INTEGER DEFAULT 0,
    unlisted_count INTEGER DEFAULT 0,
    revenue_today DECIMAL(10,2) DEFAULT 0,
    profit_today DECIMAL(10,2) DEFAULT 0,
    revenue_mtd DECIMAL(10,2) DEFAULT 0,
    profit_mtd DECIMAL(10,2) DEFAULT 0,
    revenue_ytd DECIMAL(10,2) DEFAULT 0,
    profit_ytd DECIMAL(10,2) DEFAULT 0,
    cards_bought_today INTEGER DEFAULT 0,
    cards_sold_today INTEGER DEFAULT 0,
    cards_listed_today INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS daily_plans (
    id SERIAL PRIMARY KEY,
    plan_date DATE NOT NULL,
    available_hours DECIMAL(4,1),
    target_revenue DECIMAL(10,2),
    target_profit DECIMAL(10,2),
    buy_budget DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'pending',
    actions JSONB DEFAULT '[]',
    results JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS capital_transactions (
    id SERIAL PRIMARY KEY,
    transaction_date DATE NOT NULL DEFAULT CURRENT_DATE,
    amount DECIMAL(10,2) NOT NULL,
    type VARCHAR(20) NOT NULL,
    description TEXT,
    opportunity_id INTEGER REFERENCES opportunities(id),
    inventory_id INTEGER REFERENCES inventory(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_snapshots_date ON daily_snapshots(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_plans_date ON daily_plans(plan_date);
CREATE INDEX IF NOT EXISTS idx_capital_date ON capital_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_capital_type ON capital_transactions(type);
