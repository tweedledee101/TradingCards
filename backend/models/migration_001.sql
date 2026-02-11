-- Migration: Add inventory tracking and update schema
-- Run this after initial schema.sql

-- Add missing columns to active_listings
ALTER TABLE active_listings ADD COLUMN IF NOT EXISTS listing_title TEXT;
ALTER TABLE active_listings ADD COLUMN IF NOT EXISTS listing_url TEXT;

-- Add missing column to price_trends
ALTER TABLE price_trends ADD COLUMN IF NOT EXISTS momentum_score DECIMAL(5, 2);

-- Create inventory table
CREATE TABLE IF NOT EXISTS inventory (
    id SERIAL PRIMARY KEY,
    card_id INTEGER REFERENCES cards(id),
    purchase_date DATE NOT NULL,
    purchase_price DECIMAL(10, 2) NOT NULL,
    purchase_source VARCHAR(100),
    quantity INTEGER DEFAULT 1,
    condition VARCHAR(50),
    graded BOOLEAN DEFAULT FALSE,
    grade_company VARCHAR(20),
    grade_value DECIMAL(3, 1),
    storage_location VARCHAR(100),
    notes TEXT,
    status VARCHAR(20) DEFAULT 'owned',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create inventory_sales table
CREATE TABLE IF NOT EXISTS inventory_sales (
    id SERIAL PRIMARY KEY,
    inventory_id INTEGER REFERENCES inventory(id),
    sale_date DATE NOT NULL,
    sale_price DECIMAL(10, 2) NOT NULL,
    sale_platform VARCHAR(100),
    fees DECIMAL(10, 2) DEFAULT 0,
    shipping_cost DECIMAL(10, 2) DEFAULT 0,
    net_profit DECIMAL(10, 2),
    roi_percentage DECIMAL(5, 2),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create watchlist table
CREATE TABLE IF NOT EXISTS watchlist (
    id SERIAL PRIMARY KEY,
    card_id INTEGER REFERENCES cards(id),
    target_price DECIMAL(10, 2),
    alert_threshold DECIMAL(5, 2),
    notes TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(card_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_inventory_card ON inventory(card_id);
CREATE INDEX IF NOT EXISTS idx_inventory_status ON inventory(status);
CREATE INDEX IF NOT EXISTS idx_inventory_sales_date ON inventory_sales(sale_date);
CREATE INDEX IF NOT EXISTS idx_watchlist_card ON watchlist(card_id);
