-- Job tracking table for runtime state management
-- Tracks all background jobs: pipeline, SCP collection, opportunity finder, etc.
-- Designed to migrate cleanly to AWS (DynamoDB or stays in RDS)

CREATE TABLE IF NOT EXISTS job_runs (
    id SERIAL PRIMARY KEY,
    job_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    items_processed INTEGER DEFAULT 0,
    items_total INTEGER,
    error_message TEXT,
    parameters JSONB,
    results_summary JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_job_runs_name_status ON job_runs(job_name, status);
CREATE INDEX idx_job_runs_started ON job_runs(started_at DESC);
