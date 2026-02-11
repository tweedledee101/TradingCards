-- Inventory Tracking Schema

-- User inventory: cards owned
CREATE TABLE IF NOT EXISTS inventory (
    id SERIAL PRIMARY KEY,
    card_id INTEGER REFERENCES cards(id),
    purchase_date DATE NOT NULL,
    purchase_price DECIMAL(10, 2) NOT NULL,
    purchase_source VARCHAR(100), -- 'eBay', 'Card Show', 'Trade', etc.
    quantity INTEGER DEFAULT 1,
    condition VARCHAR(50),
    graded BOOLEAN DEFAULT FALSE,
    grade_company VARCHAR(20),
    grade_value DECIMAL(3, 1),
    storage_location VARCHAR(100),
    notes TEXT,
    status VARCHAR(20) DEFAULT 'owned', -- 'owned', 'listed', 'sold'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sales from inventory
CREATE TABLE IF NOT EXISTS inventory_sales (
    id SERIAL PRIMARY KEY,
    inventory_id INTEGER REFERENCES inventory(id),
    sale_date DATE NOT NULL,
    sale_price DECIMAL(10, 2) NOT NULL,
    sale_platform VARCHAR(100), -- 'eBay', 'COMC', 'Local', etc.
    fees DECIMAL(10, 2) DEFAULT 0,
    shipping_cost DECIMAL(10, 2) DEFAULT 0,
    net_profit DECIMAL(10, 2), -- sale_price - fees - shipping - purchase_price
    roi_percentage DECIMAL(5, 2), -- (net_profit / purchase_price) * 100
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Watchlist: cards to monitor
CREATE TABLE IF NOT EXISTS watchlist (
    id SERIAL PRIMARY KEY,
    card_id INTEGER REFERENCES cards(id),
    target_price DECIMAL(10, 2),
    alert_threshold DECIMAL(5, 2), -- percentage change to trigger alert
    notes TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(card_id)
);

-- Indexes
CREATE INDEX idx_inventory_card ON inventory(card_id);
CREATE INDEX idx_inventory_status ON inventory(status);
CREATE INDEX idx_inventory_sales_date ON inventory_sales(sale_date);
CREATE INDEX idx_watchlist_card ON watchlist(card_id);
