# Ragnarok Gaming - UI Redesign Spec

## Design Philosophy
Aggressive, immersive, Norse-inspired. Not gimmicky -- premium.
Think God of War UI meets Bloomberg Terminal meets a war room.
The user should feel like they're hunting, not browsing.

## Color Palette (existing, refined)
- **Base**: Charcoal #0f1117 (keep)
- **Surface**: #1a1d27 cards, #13151d raised (keep)
- **Ember**: #e8590c primary accent (keep, but add glow effects)
- **Ember Pulse**: Subtle CSS animation on hover -- ember glows brighter
- **Frost**: #e0e0e0 text (keep)
- **Gold**: #c9a84c for premium/high-value indicators (NEW)
- **Blood Red**: #8b0000 for warnings/losses (NEW)
- **Rune Gray**: #2a2d3a for subtle background textures (NEW)

## Typography
- **Cinzel** for headings (keep -- already Norse-feeling)
- **Inter** for body (keep)
- Consider **Uncial Antiqua** or **MedievalSharp** for special accents (card names, section headers)

## Margin Textures
- Subtle Norse knotwork pattern as a repeating SVG watermark
- Opacity ~3-5% so it's felt, not seen
- Only in the page margins/gutters, not on cards
- Runic border accents on section dividers (thin line with rune marks)

## Opportunities Page - Strategy Windows

### Layout: Horizontal scrolling galleries stacked vertically

```
[Quick Flips]     ← swipe →  [card] [card] [CARD] [card] [card]
[Steady Earners]  ← swipe →  [card] [card] [CARD] [card] [card]  
[Hype Plays]      ← swipe →  [card] [card] [CARD] [card] [card]
[Deep Value]      ← swipe →  [card] [card] [CARD] [card] [card]
```

Each row is a horizontal scroll. Center card is enlarged (1.2x scale).
Cards on either side are slightly faded (opacity 0.7) and smaller.
Swipe/drag to browse. Click to expand full details.

### Strategy Definitions

**Quick Flips** (ember accent)
- ROI > 30%
- Auction ending within 48 hours
- Volume: daily or weekly sales
- "Act now or lose it"

**Steady Earners** (gold accent)
- Profit > $10
- Volume: weekly+ sales
- Consistent price (low variance)
- "Reliable income, low risk"

**Hype Plays** (blood red accent)
- Price trending UP this week vs last week
- Social/volume spike
- Higher risk, higher reward
- "Ride the wave"

**Deep Value** (frost/blue accent)
- Price significantly below SCP
- Lower volume but big margin
- Patience required
- "Buy low, wait, profit"

### Card Component (Gallery View)

```
┌─────────────────────────┐
│  [IMAGE - large]        │
│                         │
│  ─── runic divider ──── │
│                         │
│  Player Name            │
│  2026 Topps Chrome #99  │
│  [Gold Refractor]       │
│                         │
│  $12.50 bid  →  $45.00  │
│  ████████░░  +$28.65    │
│  profit bar    (72% ROI)│
│                         │
│  ⏱ 4h 23m    🔥 12 bids │
│                         │
│  [BID NOW]              │
└─────────────────────────┘
```

- Profit bar: visual fill showing how much of SCP price is profit
- Timer: countdown to auction end
- Bid count: social proof
- "BID NOW" button links to eBay

### Expanded Card Detail (click/tap)

Full-screen overlay with:
- Large card image (zoomable)
- All 3 SCP prices (Ungraded, Grade 9, PSA 10)
- Price history chart (if available)
- Volume indicator (sales per week)
- Confidence score from match engine
- SCP verification link
- eBay listing link
- "Schedule Bid" for snipe functionality

## Shop Page

### Layout: Grid with featured card hero

Top section: Featured/newest card, large hero image with price overlay.
Below: Grid of cards, 4-5 per row on desktop, 2 on mobile.
Each card has "Buy on eBay" button (ember colored, glows on hover).

### Card hover effect
- Slight lift (translateY -4px)
- Ember border glow
- Price badge scales up slightly

## Navigation

- Sticky top nav, dark with ember accent line underneath
- Logo left, nav links center, user avatar right
- Active page has ember underline
- Mobile: hamburger menu with slide-in panel

## Animations

- Page transitions: subtle fade (200ms)
- Card hover: lift + glow (150ms ease)
- Number changes: count-up animation for profit/ROI
- New opportunity: brief ember flash on card border
- Scroll: parallax on background texture (very subtle)

## Implementation Priority

1. Strategy windows on Opportunities page (highest impact)
2. Card gallery component with horizontal scroll
3. Norse texture in margins
4. Hover/glow effects
5. Shop page hero section
6. Navigation redesign
7. Animations and polish

## References
- God of War (2018) UI -- dark, gold accents, runic textures
- Bloomberg Terminal -- data density, dark theme
- Robinhood -- clean cards, profit/loss visualization
- Norse knotwork patterns -- Urnes style (flowing, organic)
