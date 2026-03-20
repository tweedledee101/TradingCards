-- Migration 009b: Add SCP verification and image columns to opportunities
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS scp_url TEXT;
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS scp_grade_9 DECIMAL(10,2);
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS scp_psa_10 DECIMAL(10,2);
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS image_url TEXT;
