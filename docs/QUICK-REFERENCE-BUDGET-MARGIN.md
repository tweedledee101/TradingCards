# Quick Reference - Budget Filter & Profit Margin

## 🚀 Quick Start

### Generate Sample Data
```bash
cd ~/TradingCards
/usr/bin/python3 backend/generate_sample_data.py
```

### Start Platform
```bash
# Terminal 1 - Backend
/usr/bin/python3 -m backend.api.run

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### Open Browser
http://localhost:3000

---

## 💰 Budget Filter

**Location:** Top of Trending page

**Usage:**
```
Max Budget: [100] → Shows cards with buy zone ≤ $100
Max Budget: [empty] → Shows all cards
```

**Example:**
- Budget $50 → See 13 affordable cards
- Budget $100 → See 18 cards
- Budget $500 → See 22 cards

---

## 📊 Profit Margin

**Location:** New column in table (after Buy Zone)

**Calculation:**
```
Margin % = ((Avg Price - Buy Zone) / Buy Zone) × 100
```

**Example:**
- Avg $45, Buy Zone $38 → **+18.4%** margin
- Avg $450, Buy Zone $338 → **+33.1%** margin

**Color:** Blue (profit indicator)

---

## 🎯 Sort Options

**Location:** Top of Trending page

**Options:**
1. **Hotness Score** (default) - Best trending cards
2. **Profit Margin %** - Best profit opportunities

**When to use:**
- Morning scan → Sort by **Hotness** (find what's moving)
- Budget shopping → Sort by **Margin** (maximize ROI)
- Risk averse → Sort by **Margin** (safer plays)

---

## 📄 Pagination

**Location:** Bottom of table

**Controls:**
- **← Previous** - Go to previous page
- **Next →** - Go to next page
- **Page X of Y** - Current position

**Behavior:**
- 25 cards per page
- Up to 100 total cards
- Hidden in Focus Mode (always shows top 10)

---

## 💡 Column Tooltips

**How to use:** Hover over any column header

**Tooltips:**
- **Rank** - Card ranking by hotness score
- **Player** - Player name and sport
- **Year / Set** - Card year and set name
- **Avg Price** - Average sold price (last 7 days)
- **Buy Zone** - Recommended buy price (velocity-adjusted)
- **Margin %** - Potential profit % if bought at buy zone
- **Volume** - Number of sales (last 7 days)
- **Velocity** - Price change velocity (higher = hotter)
- **Hotness** - Overall hotness score (0-100)

---

## 🎲 Sample Data

**25 Realistic Cards:**
- 4 Green (BUY NOW) - Affordable, high velocity
- 4 Yellow (WATCH) - Close to buy zone
- 4 White (SKIP) - Overpriced or low velocity
- 13 Budget Friendly - $18-$65

**Price Range:** $18 - $8,500

**Sports:** Basketball (8), Football (9), Baseball (7), Hockey (1)

---

## 🎨 Row Colors

**Green** - In buy zone (≤ 105% of buy zone)
- **Action:** BUY NOW
- **Example:** Avg $45, Buy Zone $38 → Green

**Yellow** - Close to buy zone (≤ 115% of buy zone)
- **Action:** WATCH or wait for better price
- **Example:** Avg $450, Buy Zone $338 → Yellow

**White** - Overpriced (> 115% of buy zone)
- **Action:** SKIP
- **Example:** Avg $8500, Buy Zone $5525 → White

---

## 🔥 Focus Mode

**Toggle:** Top right button

**Behavior:**
- Shows only cards with hotness ≥ 60
- Limits to top 10 cards
- Hides pagination

**Use case:** Quick morning scan of hottest opportunities

---

## 📋 Typical Workflows

### Workflow 1: Small Budget ($50)
1. Set **Max Budget: $50**
2. Sort by **Profit Margin %**
3. See 13 affordable cards
4. Click green rows (in buy zone)
5. Add to inventory with ✅ button

### Workflow 2: Profit Maximizer
1. No budget filter
2. Sort by **Profit Margin %**
3. Top card: +33% margin
4. Check if you can afford buy zone
5. If yes → Buy, if no → Watch

### Workflow 3: Morning Scan
1. Click **Focus Mode**
2. See top 10 hottest cards
3. Check which are green (buy zone)
4. Add green cards to watchlist
5. Hunt on eBay

---

## ❓ FAQ

### Q: Why filter by buy zone, not average price?
**A:** Buy zone is what you'll actually pay. Avg price is what you'll sell for.

### Q: What if I want to see cards $50-$100?
**A:** Set budget to $100, then manually skip cards under $50. (Min budget filter coming in Phase 2)

### Q: Why does pagination disappear in Focus Mode?
**A:** Focus Mode always shows top 10, no need for pagination.

### Q: Can I save my budget preference?
**A:** Not yet. Coming in Phase 2 (localStorage or user profile).

### Q: What's the difference between Watchlist and Trending?
**A:** 
- **Trending** - What's hot RIGHT NOW (changes daily)
- **Watchlist** - What YOU care about (persistent)

### Q: If a card is green, why not auto-buy?
**A:** You might:
- Not have the budget right now
- Want to wait for even better price
- Prefer a different card with higher margin
- Need to verify card details first

---

## 🐛 Troubleshooting

### No cards showing
```bash
# Generate sample data
/usr/bin/python3 backend/generate_sample_data.py
```

### Budget filter not working
- Check that buy zone is calculated (not null)
- Verify budget is a number (not text)
- Try clearing filter (empty field)

### Pagination stuck
- Refresh page (🔄 button)
- Check total cards > 25
- Disable Focus Mode

### Tooltips not appearing
- Hover directly over column header text
- Wait 1 second for tooltip to appear
- Try different browser if issue persists

---

## 📊 Sample Data Details

### Green Zone (BUY NOW)
1. Paul Skenes - $45 (velocity 85)
2. Caitlin Clark - $32 (velocity 78)
3. Caleb Williams - $28 (velocity 72)
4. Anthony Edwards - $65 (velocity 68)

### Yellow Zone (WATCH)
5. Victor Wembanyama - $450 (velocity 55)
6. CJ Stroud - $85 (velocity 48)
7. Gunnar Henderson - $38 (velocity 42)
8. Jahmyr Gibbs - $22 (velocity 45)

### White Zone (SKIP)
9. Michael Jordan - $8,500 (velocity 25)
10. LeBron James - $3,200 (velocity 18)
11. Patrick Mahomes - $1,850 (velocity 32)
12. Shohei Ohtani - $425 (velocity 28)

### Budget Friendly
13. Marvin Harrison Jr - $18 (velocity 75)
14. Jayden Daniels - $24 (velocity 71)
15. Elly De La Cruz - $35 (velocity 58)
16. Brandon Miller - $42 (velocity 47)

---

## 🎯 Success Metrics

**Before:**
- ⏱️ 20 min to manually filter by budget
- 🤷 No visibility into profit potential
- 📉 Limited to 25 cards
- ❓ Confusion about columns

**After:**
- ⚡ Instant budget filtering
- 💰 Profit margin at a glance
- 📈 Browse 100+ cards
- 💡 Tooltips explain everything

---

## 📚 Related Documentation

- **Full Guide:** `docs/UI-ENHANCEMENTS-BUDGET-MARGIN.md`
- **Changelog:** `CHANGELOG.md` (v2.1.0)
- **Testing:** `docs/TEST-COVERAGE-REPORT.md`
- **UI Analysis:** `docs/UI-UX-ANALYSIS.md`

---

**Version:** 2.1.0  
**Last Updated:** 2025-02-XX  
**Status:** ✅ Implemented
