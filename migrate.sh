#!/bin/bash

# Apply database migration for inventory system

echo "🔄 Applying database migration..."

# Check if PostgreSQL is running
if ! pg_isready -q; then
    echo "❌ PostgreSQL is not running. Please start PostgreSQL first."
    exit 1
fi

# Apply migration
psql -U postgres -d trading_cards -f backend/models/migration_001.sql

if [ $? -eq 0 ]; then
    echo "✅ Migration applied successfully!"
    echo ""
    echo "New tables created:"
    echo "  - inventory"
    echo "  - inventory_sales"
    echo "  - watchlist"
    echo ""
    echo "Updated tables:"
    echo "  - active_listings (added listing_title, listing_url)"
    echo "  - price_trends (added momentum_score)"
    echo ""
    echo "🚀 Restart your API server to use new features:"
    echo "   python3 -m backend.api.run"
else
    echo "❌ Migration failed. Check the error messages above."
    exit 1
fi
