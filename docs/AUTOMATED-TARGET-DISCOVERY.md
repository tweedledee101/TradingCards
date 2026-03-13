# Automated Target Discovery System

**Eliminate manual player list curation with fully automated market-driven discovery**

---

## 🎯 Problem Solved

**Before**: Manually maintaining `config/targets.yaml` with 7-25 players - unsustainable, misses opportunities, requires constant research.

**After**: Fully automated system discovers 50-100 trending cards daily from market signals with zero manual intervention (except personal favorites).

---

## 🚀 How It Works

### Daily Workflow

```
1:00 AM - Discovery Job Runs
   ↓
   Scrape eBay trending searches
   ↓
   Find high-volume cards (50+ sales/week)
   ↓
   Score by: sales volume + price velocity + price range
   ↓
   Auto-update targets.yaml (top 50 cards)
   ↓
2:00 AM - Regular Scraper Runs
   ↓
   Uses auto-generated target list
   ↓
   Collects data for discovered cards
```

### Discovery Algorithm

**Discovery Score (0-100)**:
- **Sales Volume (50%)**: Cards with 50+ sales/week score highest
- **Price Velocity (30%)**: Cards with significant price changes (±20%+)
- **Price Range (20%)**: Prefer $50-$500 range (sweet spot for flipping)

**Thresholds**:
- Minimum Discovery Score: 40/100
- Minimum Sales Volume: 50 sales/week
- Price Range: $10-$5000 (filter junk and outliers)
- Maximum Targets: 50 cards (keep list manageable)

---

## 📋 Quick Start

### Test with Mock Data (5 minutes)

```bash
# Test discovery with mock data
python3 backend/test_discovery.py

# Check generated targets
cat config/targets.yaml
```

**Expected Output**:
```
🧪 Testing Automated Target Discovery

📊 Generating mock discovered cards...
✅ Generated 8 mock discoveries

🔥 Mock Discovered Cards:
  1. Caitlin Clark 2024 Prizm (Basketball)
     Score: 92.1 | Sales: 200 | Avg: $85.00 | Velocity: 35.2%
  2. Shohei Ohtani 2024 Topps (Baseball)
     Score: 88.7 | Sales: 180 | Avg: $150.00 | Velocity: 28.5%
  ...

💾 Updating targets.yaml...
╔══════════════════════════════════════════════════════════╗
║           DISCOVERY TEST COMPLETE                        ║
╠══════════════════════════════════════════════════════════╣
║  Total Targets:      8                                   ║
║  Manual Favorites:   0                                   ║
║  Auto-Discovered:    8                                   ║
╚══════════════════════════════════════════════════════════╝
```

### Run Real Discovery (requires eBay API)

```bash
# Run discovery immediately (test mode)
python3 -m backend.run_discovery --now

# Start daily scheduler (runs at 1 AM)
python3 -m backend.run_discovery
```

---

## 🔧 Configuration

### Manual Favorites (Preserved Across Auto-Updates)

Add personal favorites that won't be removed by auto-discovery:

```yaml
# config/targets.yaml
players:
  - name: "Michael Jordan"
    sport: "Basketball"
    queries:
      - "{name} 1986"
      - "{name} rookie"
    favorite: true  # ← Preserved across auto-updates
    added_at: "2025-02-15T10:00:00"
```

### Discovery Thresholds

Edit `backend/scrapers/ebay_trending_scraper.py`:

```python
class EbayTrendingDiscovery:
    MIN_SALES_VOLUME = 50  # Increase for stricter filtering
    MIN_PRICE = 10.0       # Minimum card price
    MAX_PRICE = 5000.0     # Maximum card price
```

Edit `backend/services/target_discovery.py`:

```python
class TargetDiscoveryService:
    MIN_DISCOVERY_SCORE = 40.0  # Minimum score to include
    MAX_TARGETS = 50            # Maximum targets to maintain
```

---

## 📊 What Gets Discovered

### High-Volume Cards
- **Rookies**: New player debuts with high sales (Wembanyama, Caitlin Clark)
- **Trending Veterans**: Established players with recent spikes (Ohtani signing)
- **Graded Cards**: PSA 10 population spikes driving demand

### Price Movers
- **Rising Stars**: Cards with 20%+ price increases in 7 days
- **Market Corrections**: Cards dropping 20%+ (buy opportunities)
- **Seasonal Trends**: Playoff performers, award winners

### Sweet Spot Cards
- **$50-$500 Range**: Best ROI for flipping (preferred)
- **$25-$50 Range**: High volume, lower margins (secondary)
- **$500-$2000 Range**: Lower volume, higher margins (tertiary)

---

## 🎛️ Managing Targets

### Add Manual Favorite

```python
from backend.services.target_discovery import TargetDiscoveryService

service = TargetDiscoveryService()
service.add_manual_favorite(
    player_name="Michael Jordan",
    sport="Basketball",
    queries=["{name} 1986", "{name} rookie", "{name} PSA"]
)
```

### Remove Manual Favorite

```python
service.remove_manual_favorite("Michael Jordan")
```

### View Current Targets

```bash
# View all targets
cat config/targets.yaml

# Count targets
grep "^  - name:" config/targets.yaml | wc -l

# View auto-discovered only
grep -A 5 "auto_discovered: true" config/targets.yaml
```

---

## 📈 Monitoring Discovery

### Check Discovery Logs

```bash
# View last discovery run
tail -n 100 logs/discovery.log

# Monitor live
tail -f logs/discovery.log
```

### Discovery Metrics

```bash
# Check targets.yaml metadata
grep -A 10 "metadata:" config/targets.yaml
```

**Example Output**:
```yaml
metadata:
  last_updated: '2025-02-15T01:05:23'
  auto_discovery_enabled: true
  total_targets: 48
```

---

## 🔄 Integration with Existing System

### Scheduler Integration

The discovery job runs **before** the regular scraper:

```
1:00 AM - Discovery Job
   ↓ Updates targets.yaml
2:00 AM - Regular Scraper
   ↓ Uses updated targets
```

**No changes needed** to existing scraper - it automatically reads the updated `targets.yaml`.

### Backward Compatibility

- **Manual targets still work**: Add `favorite: true` to preserve
- **Existing queries preserved**: Auto-discovery adds new queries
- **No breaking changes**: System falls back to manual list if discovery fails

---

## 🐛 Troubleshooting

### No Cards Discovered

**Cause**: eBay API rate limits or no cards meet thresholds

**Solution**:
```bash
# Lower thresholds temporarily
# Edit backend/scrapers/ebay_trending_scraper.py
MIN_SALES_VOLUME = 25  # Lower from 50
MIN_DISCOVERY_SCORE = 30.0  # Lower from 40.0
```

### Too Many Low-Quality Cards

**Cause**: Thresholds too low

**Solution**:
```bash
# Raise thresholds
MIN_SALES_VOLUME = 75  # Raise from 50
MIN_DISCOVERY_SCORE = 50.0  # Raise from 40.0
```

### Discovery Job Not Running

**Cause**: Scheduler not started

**Solution**:
```bash
# Check if running
ps aux | grep run_discovery

# Start scheduler
python3 -m backend.run_discovery
```

### Manual Favorites Removed

**Cause**: Missing `favorite: true` flag

**Solution**:
```yaml
# Add flag to preserve
players:
  - name: "Your Player"
    favorite: true  # ← Add this
```

---

## 🚀 Future Enhancements

### Phase 2: Card Ladder Integration
- Scrape "Biggest Movers" section
- Add cards with >20% price increase in 7 days
- Weight by Card Ladder popularity score

### Phase 3: PSA Grading Spikes
- Monitor PSA population changes
- Add cards with >100 new submissions in 30 days
- Detect grading trends (PSA 10 rate changes)

### Phase 4: Social Signals
- Twitter API: Track #sportscards mentions
- Reddit API: Monitor r/basketballcards hot posts
- Weight by engagement (likes, comments, shares)

### Phase 5: Release Calendars
- Topps/Panini release schedules
- Auto-add new releases on launch day
- Track pre-release hype

---

## 📊 Success Metrics

### Discovery Quality
- **Target**: 80%+ of discovered cards have 50+ sales/week
- **Target**: 60%+ of discovered cards show in Opportunity Finder
- **Target**: 40%+ of discovered cards have profitable arbitrage

### System Performance
- **Target**: Discovery completes in <5 minutes
- **Target**: 0 manual interventions per week
- **Target**: 50 active targets maintained daily

---

## 🎉 Benefits

### Before (Manual Curation)
- ❌ 7-25 players manually maintained
- ❌ Requires constant market research
- ❌ Misses emerging opportunities
- ❌ Biased toward personal knowledge
- ❌ Time-consuming to update

### After (Automated Discovery)
- ✅ 50-100 trending cards auto-discovered
- ✅ Zero manual intervention (except favorites)
- ✅ Catches emerging trends immediately
- ✅ Data-driven, unbiased selection
- ✅ Fully automated, hands-off

---

**Next Steps**: Run `python3 backend/test_discovery.py` to see it in action! 🚀
