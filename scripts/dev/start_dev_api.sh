#!/bin/bash
# Start local API server pointed at trading_cards_dev
cd /home/tweedledee101/TradingCards
source .venv/bin/activate
set -a
source backend/.env
set +a

# Swap to dev database
export DATABASE_URL="${DATABASE_URL%/trading_cards}/trading_cards_dev"
echo "Starting API against: $(echo $DATABASE_URL | grep -oP '/[^/]+$')"

nohup python3 -m backend.api.run > /tmp/api-dev.log 2>&1 &
echo "API PID: $!"
sleep 3
curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "API not ready yet -- check /tmp/api-dev.log"
