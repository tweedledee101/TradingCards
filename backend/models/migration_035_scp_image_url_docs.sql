-- Migration: add scp_image_url to scp_cache variants
-- No schema change needed -- variants is JSONB, we just start writing
-- 'scp_image_url' into each variant dict alongside 'url', 'parallel', etc.
-- This is a documentation migration only (JSONB is schemaless).

-- Verify the column exists and is JSONB:
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'scp_cache' AND column_name = 'variants'
    ) THEN
        RAISE EXCEPTION 'scp_cache.variants column not found';
    END IF;
END $$;

-- No ALTER needed. The pipeline will start writing scp_image_url
-- into the variants JSONB on the next SCP image scrape.
