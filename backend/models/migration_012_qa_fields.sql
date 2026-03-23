-- Migration 012: Add QA fields to opportunities
-- QA runs as a background process after pipeline stores results

ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS qa_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS qa_flags JSONB DEFAULT '[]'::jsonb;
ALTER TABLE opportunities ADD COLUMN IF NOT EXISTS qa_reviewed_at TIMESTAMP;

-- Index for finding unreviewed opportunities
CREATE INDEX IF NOT EXISTS idx_opportunities_qa_status ON opportunities(qa_status);
