#!/bin/bash
# Migrate local PostgreSQL to RDS
# Usage: ./migrate-to-rds.sh <rds-endpoint> <rds-password>

set -e

RDS_HOST="${1:?Usage: $0 <rds-endpoint> <rds-password>}"
RDS_PASS="${2:?Usage: $0 <rds-endpoint> <rds-password>}"
RDS_USER="cardpulse"
RDS_DB="trading_cards"
LOCAL_DB="trading_cards"

echo "=== Dumping local database ==="
sudo -u postgres pg_dump --no-owner --no-acl "$LOCAL_DB" > /tmp/cardpulse_dump.sql
echo "Dump size: $(du -h /tmp/cardpulse_dump.sql | cut -f1)"

echo ""
echo "=== Loading into RDS ==="
PGPASSWORD="$RDS_PASS" psql -h "$RDS_HOST" -U "$RDS_USER" -d "$RDS_DB" -f /tmp/cardpulse_dump.sql

echo ""
echo "=== Verifying ==="
PGPASSWORD="$RDS_PASS" psql -h "$RDS_HOST" -U "$RDS_USER" -d "$RDS_DB" -c "
SELECT 'cards' as tbl, count(*) FROM cards
UNION ALL SELECT 'opportunities', count(*) FROM opportunities
UNION ALL SELECT 'sales_data', count(*) FROM sales_data
UNION ALL SELECT 'job_runs', count(*) FROM job_runs;
"

echo ""
echo "=== Done ==="
echo "Update your .env:"
echo "DATABASE_URL=postgresql://${RDS_USER}:${RDS_PASS}@${RDS_HOST}:5432/${RDS_DB}"
echo ""
echo "Add to GitHub Secrets:"
echo "  DATABASE_URL = postgresql://${RDS_USER}:${RDS_PASS}@${RDS_HOST}:5432/${RDS_DB}"
echo "  EBAY_CLIENT_ID = (your eBay client ID)"
echo "  EBAY_CLIENT_SECRET = (your eBay client secret)"

rm /tmp/cardpulse_dump.sql
