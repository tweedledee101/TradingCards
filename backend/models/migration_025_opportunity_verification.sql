-- Cross-source listing verification (eBay vs SCP / comps). Populated by pipeline and future QA jobs.

ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS verification_status VARCHAR(32) NOT NULL DEFAULT 'pending';
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS verification_detail JSONB DEFAULT NULL;

COMMENT ON COLUMN opportunities.verification_status IS 'pending | verified | conflict | skipped — automated or manual cross-check state';
COMMENT ON COLUMN opportunities.verification_detail IS 'Structured notes: pipeline, schema version, checks run, discrepancies';
