-- Migration 008: Data retention policy
-- Pruning function that removes stale data. Called by the app, not by cron.

-- Function: prune old data based on retention windows
CREATE OR REPLACE FUNCTION run_retention_cleanup() RETURNS JSONB AS $$
DECLARE
    deleted_errors INT;
    deleted_jobs INT;
    deleted_listings INT;
    deleted_trends INT;
BEGIN
    -- error_log: keep 30 days
    DELETE FROM error_log WHERE timestamp < NOW() - INTERVAL '30 days';
    GET DIAGNOSTICS deleted_errors = ROW_COUNT;

    -- job_runs: keep 30 days
    DELETE FROM job_runs WHERE started_at < NOW() - INTERVAL '30 days';
    GET DIAGNOSTICS deleted_jobs = ROW_COUNT;

    -- active_listings: remove listings older than 14 days (expired)
    DELETE FROM active_listings WHERE snapshot_date < NOW() - INTERVAL '14 days';
    GET DIAGNOSTICS deleted_listings = ROW_COUNT;

    -- price_trends: keep 90 days of daily data
    DELETE FROM price_trends WHERE trend_date < NOW() - INTERVAL '90 days';
    GET DIAGNOSTICS deleted_trends = ROW_COUNT;

    RETURN jsonb_build_object(
        'error_log', deleted_errors,
        'job_runs', deleted_jobs,
        'active_listings', deleted_listings,
        'price_trends', deleted_trends,
        'ran_at', NOW()
    );
END;
$$ LANGUAGE plpgsql;
