# Automation System

Automated data collection and reporting for trending cards.

## Components

### 1. Target List (`config/targets.yaml`)
Configure which players and queries to track:
```yaml
players:
  - name: "Victor Wembanyama"
    sport: "Basketball"
    rookie_year: 2023
    queries:
      - "{name} 2023 prizm rookie"
      - "{name} prizm PSA 10"
```

### 2. Automated Collector (`backend/services/automated_collector.py`)
Loops through all targets and imports data automatically.

### 3. Report Generator (`backend/services/report_generator.py`)
Creates daily CSV and text reports of top trending cards.

### 4. Scheduler (`backend/services/scheduler.py`)
Runs collection and reporting on schedule using APScheduler.

## Quick Start

### Test It Now
```bash
# Run collection immediately (test mode)
python -m backend.run_scheduler --now
```

This will:
1. Import sales for all players in targets.yaml
2. Import active listings
3. Calculate trends
4. Generate reports in `reports/` folder

### Start Scheduler
```bash
# Start scheduler (runs daily at 2 AM by default)
python -m backend.run_scheduler
```

Press Ctrl+C to stop.

### View Reports
```bash
# Reports are saved in reports/ folder
ls reports/
# trending_cards_2025-02-11.csv
# trending_cards_2025-02-11.txt
```

## Configuration

Edit `config/targets.yaml`:

### Add Players
```yaml
players:
  - name: "Your Player"
    sport: "Basketball"
    rookie_year: 2024
    queries:
      - "{name} prizm rookie"
```

### Change Schedule
```yaml
schedule:
  daily_import_time: "02:00"  # 2 AM
  days_back: 7
```

### Configure Reports
```yaml
reports:
  output_dir: "reports"
  top_cards_limit: 25
```

## Usage Examples

### Run Immediately
```bash
python -m backend.run_scheduler --now
```

### Run on Schedule
```bash
# Runs daily at configured time
python -m backend.run_scheduler
```

### Run as Background Service (Linux)
```bash
# Create systemd service
sudo nano /etc/systemd/system/tradingcards-scheduler.service

[Unit]
Description=Trading Cards Scheduler
After=network.target

[Service]
User=root
WorkingDirectory=/home/tweedledee101/TradingCards
ExecStart=/usr/bin/python3 -m backend.run_scheduler
Restart=always

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable tradingcards-scheduler
sudo systemctl start tradingcards-scheduler
```

### Run with Cron (Alternative)
```bash
# Edit crontab
crontab -e

# Add line (runs at 2 AM daily)
0 2 * * * cd /home/tweedledee101/TradingCards && python -m backend.run_scheduler --now
```

## What It Does

### Daily Collection
1. Reads `config/targets.yaml`
2. For each player:
   - Runs all configured queries
   - Imports sold listings (last 7 days)
   - Imports active listings
3. Calculates trends for all cards
4. Generates reports

### Reports Generated
- **CSV Report:** `reports/trending_cards_YYYY-MM-DD.csv`
  - Rank, player, year, set, prices, scores
  - Import into Excel/Google Sheets
  
- **Text Report:** `reports/trending_cards_YYYY-MM-DD.txt`
  - Human-readable format
  - Top 25 cards with details

## Monitoring

### Check Logs
```bash
# If running in terminal
# Logs print to console

# If running as service
sudo journalctl -u tradingcards-scheduler -f
```

### Check Reports
```bash
# View latest report
cat reports/trending_cards_$(date +%Y-%m-%d).txt

# View CSV
cat reports/trending_cards_$(date +%Y-%m-%d).csv
```

## Troubleshooting

**No data imported:**
- Check eBay API credentials in `.env`
- Verify targets.yaml has valid players
- Check internet connection

**Scheduler not running:**
- Check time format in targets.yaml (24-hour)
- Verify APScheduler is installed: `pip install apscheduler`

**Reports empty:**
- Run collection first: `python -m backend.run_scheduler --now`
- Check database has data: `python backend/test_pipeline.py`

## Next Steps

- [ ] Add email notifications
- [ ] Add Slack/Discord webhooks
- [ ] Add error alerting
- [ ] Add data quality checks
- [ ] Add retry logic for failed imports
