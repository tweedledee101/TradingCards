#!/bin/bash
# Setup script - Install all dependencies

echo "🚀 Setting up Trading Card Platform..."
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Install dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip install -r backend/requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Configure .env: cp backend/.env.example backend/.env"
echo "  2. Setup database: psql -U postgres -c 'CREATE DATABASE trading_cards;'"
echo "  3. Run schema: psql -U postgres -d trading_cards -f backend/models/schema.sql"
echo "  4. Test pipeline: python backend/test_pipeline.py"
echo "  5. Start API: python -m backend.api.run"
echo ""
