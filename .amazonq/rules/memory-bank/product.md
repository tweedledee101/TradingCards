# Trading Card Platform - Product Overview

## Purpose
A data-driven arbitrage opportunity finder for trading card dealers that identifies profitable card flips using **volume-based discovery** and **budget-first filtering**.

## Core Value Proposition
- **Volume-Based Discovery**: Find players with highest trading activity (ignore price initially)
- **Budget-First Filtering**: Only show opportunities within user's budget
- **Arbitrage Detection**: Buy below market, flip for profit after fees
- **Strategy Modes**: Quick Flip (high turnover) vs Sit & Wait (patient strategy)

## System Architecture (3 Phases)

### Phase 1: Volume Discovery
- Find top 100 players by **sales volume only** (last 90 days)
- Sort by: Total cards sold
- **Ignore price completely**
- Output: Ranked list of most-traded players

### Phase 2: Budget Filtering  
- User sets budget (e.g., $100)
- For each player (starting with #1 by volume):
  - Check if ANY cards exist ≤ budget
  - If YES: Add to target list (max 20 players)
  - If NO: Skip to next player
- Stop when 20 players found

### Phase 3: Opportunity Analysis
- Only analyze the 20 budget-friendly players
- Find cards with:
  - Quick sell (high velocity)
  - High margins (profit after fees)
  - Low error (price consistency)
  - High frequency (lots of sales)
  - High confidence (momentum signals)

## Key Features

### 🎯 Opportunity Finder (Primary Feature)
- **Arbitrage Analysis**: Buy price vs sell price with profit after fees and ROI calculations
- **Momentum Validation**: Price trends (rising/stable/falling), sales velocity, sell-through rates
- **Opportunity Score**: 0-100 scoring (70% arbitrage + 30% momentum)
- **Confidence Levels**: VERY HIGH 🔥, HIGH ✅, MEDIUM ⚠️, LOW 🥶
- **Dynamic Filters**: Budget range, minimum profit, minimum ROI, momentum direction
- **Fee Calculation**: Automatic eBay (12.9%) + PayPal fee deductions

### 💼 Portfolio Management
- **Inventory Tracking**: Record purchases with storage location management
- **Profit/Loss Tracking**: Real-time P&L calculations per card and portfolio-wide
- **ROI Analytics**: Portfolio-wide return on investment metrics
- **Sales Recording**: Track sales with automatic profit calculation

### 👀 Watchlist & Alerts
- **Price Monitoring**: Set target prices for specific cards
- **Price Alerts**: Notifications when cards hit target prices
- **Trend Monitoring**: Track hotness scores for watchlist cards

### 📊 Market Analytics
- **Price History**: 14-day historical price trends
- **Volume Analysis**: Sales volume tracking and momentum
- **Market Statistics**: Overall market overview and benchmarks
- **Buy Zone Calculator**: Velocity-adjusted buy recommendations
- **Card Detail Pages**: Full metadata with grading population and price benchmarks

### 🤖 Automation
- **Automated Target Discovery**: Auto-discover 50-100 trending cards daily from eBay market signals (zero manual curation)
- **Daily Discovery**: Runs at 1 AM to populate target list before scraper runs
- **Daily Collection**: Automated data scraping at 2 AM using auto-generated targets
- **Manual Favorites**: Preserve personal favorites across auto-updates
- **Daily Reports**: CSV and text reports of trending opportunities
- **Sample Data Generator**: 25 realistic cards for testing

## Target Users
- **Professional Card Dealers**: Primary audience - users who buy and flip cards for profit
- **Serious Collectors**: Secondary audience - collectors tracking portfolio value and market trends
- **Card Investors**: Users treating cards as investment vehicles with ROI focus

## Use Cases

### Primary Use Case: Find Profitable Flips
1. User sets budget filter ($100-$500)
2. Platform shows cards selling below market rate
3. User sees profit after fees ($45 profit, 35% ROI)
4. Momentum signals validate (rising prices, high velocity)
5. User purchases card and tracks in inventory
6. User sells card and records profit

### Secondary Use Case: Portfolio Management
1. User records card purchase ($150)
2. Platform tracks current market value ($210)
3. User sees real-time profit ($60, 40% ROI)
4. User decides to sell or hold based on momentum
5. User records sale and realizes profit

### Tertiary Use Case: Market Research
1. User monitors watchlist of target cards
2. Platform alerts when prices hit targets
3. User analyzes price history and grading trends
4. User identifies emerging opportunities

### Quaternary Use Case: Automated Target Discovery (NEW)
1. System discovers 100+ trending cards from eBay at 1 AM
2. Scores by sales volume (50%) + price velocity (30%) + price range (20%)
3. Auto-updates targets.yaml with top 50 cards (preserves manual favorites)
4. Regular scraper runs at 2 AM using auto-generated list
5. User sees fresh opportunities daily with zero manual research

## Data Sources (9 Total)

| Source | Purpose | Status |
|--------|---------|--------|
| eBay Trending Discovery | Auto-discover hot cards | Code Ready (Testing) |
| eBay Browse API | Sold listings, price data | Code Ready (API Blocked) |
| eBay Active Listings | Current market supply | Code Ready (API Blocked) |
| PSA Population | Grading spikes | Infrastructure Ready (Testing) |
| Card Ladder | Price velocity, benchmarks | Infrastructure Ready (Testing) |
| Sell-Through Rates | Market confidence | Code Ready (Need eBay Data) |
| Terapeak | Sell-through rates | Planned |
| Twitter/Reddit | Social sentiment | Planned |
| Release Calendars | New releases | Planned |

**Current Status**: 0/9 sources with real data, 6/9 infrastructure ready, using sample data (25 realistic cards)

## Deployment
- **Domain**: cardpulse.jgaffiliated.com
- **Infrastructure**: 100% AWS (Lambda, ECS, RDS, CloudFront)
- **Deployment**: CloudFormation (Infrastructure as Code)
- **Current Phase**: Phase 2.5 - Automated Discovery (Testing)
