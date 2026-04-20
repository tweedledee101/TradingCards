#!/bin/bash
cd /home/tweedledee101/TradingCards
/usr/bin/python3 worm_scp_volume.py --limit 25000 --min-price 20 --max-price 1000 > /tmp/scp_volume.log 2>&1 &
echo "PID=$!"
sleep 10
echo "--- log tail ---"
tail -10 /tmp/scp_volume.log
echo "--- process ---"
ps aux | grep worm_scp | grep -v grep
