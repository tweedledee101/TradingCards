-- Shipping methods (replacing flat shipping fee), ship-by SLA, and
-- photo-verified shipment confirmation.

ALTER TABLE marketplace_listings ADD COLUMN IF NOT EXISTS shipping_method VARCHAR(30) NOT NULL DEFAULT 'single_card';

ALTER TABLE marketplace_orders ADD COLUMN IF NOT EXISTS ship_by_date DATE;
ALTER TABLE marketplace_orders ADD COLUMN IF NOT EXISTS shipment_photo_url TEXT;
ALTER TABLE marketplace_orders ADD COLUMN IF NOT EXISTS carrier VARCHAR(50);
