-- Extra gallery images from eBay Browse API (image + thumbnails + additionalImages) for vision / UI.
-- Primary image remains in image_url; full ordered list in listing_image_urls (JSON array of strings).

ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS listing_image_urls JSONB DEFAULT NULL;

COMMENT ON COLUMN opportunities.listing_image_urls IS 'Distinct eBay CDN image URLs from Browse API (no HTML); for multimodal SCP retry / gallery UI';
