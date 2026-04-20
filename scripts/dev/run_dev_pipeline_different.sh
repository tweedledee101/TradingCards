#!/bin/bash
# Run dev BIN pipeline with the DIFFERENT process:
#   - Player ranking from sales (no Browse discovery calls)
#   - Stricter listing matching (all parallel tokens must appear)
#   - Top 20 players (faster run for comparison)
#
# This writes to trading_cards_dev, not production.

cd /home/tweedledee101/TradingCards
source .venv/bin/activate
set -a
source backend/.env
set +a

echo "=== DEV PIPELINE: Different Process ==="
echo "  Rank source: sales (not Browse)"
echo "  Strict listings: ON"
echo "  Top players: 20"
echo "  Max eBay variations: 500 (fast comparison run)"
echo "  Writing to: trading_cards_dev"
echo ""

python3 scripts/run_find_opportunities_dev.py \
  --player-rank-source sales \
  --sales-rank-days 30 \
  --dev-strict-listings \
  --use-scp-cache \
  --max-ebay-variations 500 \
  --top-players 20 \
  --max-budget 200 \
  --min-profit 10 \
  --min-roi 20 \
  --skip-auction-chain
