-- Marketplace order hardening:
--  - escrow release tracking (funds_released_at)
--  - idempotency: at most one order per Stripe checkout session (partial unique
--    index allows NULLs for legacy/manual rows)

ALTER TABLE marketplace_orders ADD COLUMN IF NOT EXISTS funds_released_at TIMESTAMP;

CREATE UNIQUE INDEX IF NOT EXISTS uq_marketplace_orders_checkout_session
    ON marketplace_orders (stripe_checkout_session_id)
    WHERE stripe_checkout_session_id IS NOT NULL;
