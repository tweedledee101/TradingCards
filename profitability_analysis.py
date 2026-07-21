#!/usr/bin/env python3
"""Trading Card Business Profitability Analysis - May 31, 2026"""

from datetime import datetime

# ============================================================
# EBAY SALES (from sold orders - what actually sold)
# Each entry: (date, item, sale_price, shipping_charged, fees_total, net_to_you)
# fees_total = eBay final value fee + promoted listings fee
# ============================================================
sales = [
    # From eBay payments ledger (most accurate - includes all fees)
    ("2026-05-31", "2026 Bowman Payton Tolle Blue Refractor Auto", 133.00, 8.00, 19.06+18.31, 113.94-18.31),  # processing
    ("2026-05-30", "2026 Bowman Munetaka Murakami Blue #9 RC", 206.62, 5.62, 29.56+28.61, 177.06-28.61),  # processing
    ("2026-05-28", "2024 Topps Inception Nolan Arenado Auto /50", 55.61, 5.62, 7.77+7.23, 47.84-7.23),
    ("2026-05-26", "2024 Bowman Draft Sapphire Konnor Griffin #BDC-22", 175.24, 5.24, 23.62+22.78, 151.62-22.78),
    ("2026-05-26", "2026 Chrome Black Parker Messick Base RC", 9.00, 2.50, 1.58+1.25, 7.42-1.25),
    ("2026-05-24", "2026 Bowman Chrome Luis Pena Green Refractor /99", 18.16, 5.17, 3.00+2.55, 15.16-2.55),
    ("2026-05-23", "2025 Bowman Chrome David Ortiz Jr Wave Refractor /350", 4.07, 1.32, 0.87, 3.20),
    ("2026-05-18", "2026 Bowman Cam Schlitter Under The Radar RC", 5.49, 2.50, 1.08+0.77, 4.41-0.77),
    ("2026-05-15", "2024 Topps Chrome Francisco Lindor Blue Sonar /125", 14.00, 8.00, 2.38+1.94, 11.62-1.94),
    ("2026-05-12", "2026 Topps S1 Titans of the Game Mike Trout Orange /25", 42.00, 8.00, 6.42+5.90, 35.58-5.90),
    ("2026-05-11", "2025 Topps Chrome Rookie Auto Daniel Schneemann", 7.50, 2.50, 1.37, 6.13),
    ("2026-05-10", "2024 Topps S2 Relic Evan Carter Black /199", 4.32, 1.32, 0.92+0.61, 3.40-0.61),
    ("2026-05-10", "2024 Topps Chrome Corey Seager Purple Refractor /250", 3.31, 1.32, 0.76, 2.55),
    ("2026-05-10", "2024 Topps Update Shota Imanaga Jack-O-Lantern Foil", 4.50, 2.50, 0.91, 3.59),
    ("2026-05-09", "2025 Bowman Chrome Auto Bo Walker Refractor /499", 8.00, 2.50, 1.40, 6.60),
    ("2026-05-07", "2025 Topps Heritage Luis Arraez Color of Year /76", 21.50, 8.00, 3.47, 18.03),
    ("2026-05-07", "2025 Bowman Chrome Auto Yeremi Cabrera", 18.00, 8.00, 2.79+2.34, 15.21-2.34),
    ("2026-05-06", "2025 Bowman Prospects Chase Hampton Blue Pattern /125", 3.50, 2.50, 0.77+0.46, 2.73-0.46),
    ("2026-05-06", "2025 Topps Chrome Update Moises Ballesteros Sepia RC", 2.57, 1.32, 0.66, 1.91),
    ("2026-05-05", "2023-24 Panini Select FIFA Micky van de Ven /199", 12.00, 0, 2.15+1.32, 9.85-1.32),
    ("2026-05-04", "2020-21 Panini Prizm Rookie Penmanship Saddiq Bey", 3.82, 1.32, 0.84+0.53, 2.98-0.53),
    ("2026-05-02", "2025-26 Topps Chrome Ball of Duty Tyrese Maxey", 2.32, 1.32, 0.63, 1.69),
    ("2026-04-30", "2024 Topps Update Jung-Hoo Lee Gold /2024 RC", 5.32, 1.32, 1.05+0.74, 4.27-0.74),
    ("2026-04-30", "2020-21 Panini Prizm Stephen Curry Silver", 6.32, 1.32, 1.21+0.89, 5.11-0.89),
    ("2026-04-30", "2011 Bowman Draft Mike Trout #101 RC", 78.00, 8.00, 11.48+10.88, 66.52-10.88),
    ("2026-04-22", "2021 Topps Update Kyle Finnegan Gold /2021 RC", 4.32, 1.32, 0.90+0.59, 3.42-0.59),
    ("2026-04-10", "2025 Bowman Sapphire Asbel Gonzalez #BCP-4 RC", 3.32, 1.32, 0.76+0.45, 2.56-0.45),
    ("2026-03-17", "2024 Topps Chrome Jonathan India Negative Refractor", 3.32, 1.32, 0.77+0.46, 2.55-0.46),
    ("2026-03-09", "2025 Topps Chrome Jarren Duran Aqua Refractor /199", 6.32, 1.32, 1.19+0.87, 5.13-0.87),
    ("2026-03-07", "James Wood 2025 Chrome Black True Gold Auto /50", 288.35, 8.35, 41.48+40.31, 246.87-40.31),
    ("2026-03-07", "NY Mets Card Lot (Scott Auto, Alonso, Marte)", 23.10, 8.10, 3.68+3.21, 19.42-3.21),
    ("2026-03-05", "2024 Topps Update Camo Chris Martin Gold /25", 3.82, 1.32, 0.84, 2.98),
    ("2026-03-05", "2024 Topps Chrome Yamamoto #18 Refractor (x2)", 45.27, 5.27, 6.72+6.20, 38.55-6.20),
    ("2026-03-05", "2024 Topps Chrome Kody Funderburk Blue RayWave /150", 4.31, 1.32, 0.90, 3.41),
    ("2026-02-15", "2025 Topps Chrome Kristian Campbell Blue Lava /150", 16.32, 1.32, 2.71+1.74, 13.61-1.74),
    ("2026-02-15", "2022 Panini Prizm Devonte Wyatt Green Prizm RC", 14.99, 0, 2.59, 12.40),
    ("2026-02-11", "Shohei Ohtani Dodgers Lot (RCs & Inserts)", 23.20, 0, 3.67+2.97, 19.53-2.97),
    ("2026-02-08", "Angels Lot Auto /50 RC + Ohtani /2021", 20.52, 0, 3.31, 17.21),
    ("2026-02-03", "2025 Topps Chrome Auto Hurston Waldrep Blue RayWave /150", 45.07, 0, 6.83+4.86, 38.24-4.86),
    ("2026-01-23", "2025 Topps Chrome Juan Soto Blue Refractor /150", 6.00, 0, 1.15, 4.85),
]

# ============================================================
# SHIPPING COSTS YOU PAID (from eBay payments ledger)
# ============================================================
shipping_labels = [
    ("2026-05-27", "ESUS334733050", 1.32),
    ("2026-05-27", "ESUS334733486", 1.32),
    ("2026-05-27", "9400108106245201287675 (Griffin)", 5.24),
    ("2026-05-27", "9400108106245201284452 (Pena)", 5.17),
    ("2026-05-20", "ESUS332974263 (Lindor)", 1.32),
    ("2026-05-20", "ESUS332974301 (Schlitter)", 1.32),
    ("2026-05-13", "ESUS331488742 (Schneemann)", 1.32),
    ("2026-05-13", "9400108106245154451659 (Trout TOG)", 5.97),
    ("2026-05-12", "ESUS331092142 (Seager)", 1.32),
    ("2026-05-12", "ESUS331091959 (Imanaga)", 1.32),
    ("2026-05-12", "ESUS331091762 (Bo Walker)", 1.32),
    ("2026-05-12", "ESUS331092188 (Evan Carter)", 1.32),
    ("2026-05-11", "9400108106244113580768 (Cabrera)", 5.48),
    ("2026-05-11", "9400108106245144525605 (Arraez)", 5.40),
    ("2026-05-07", "ESUS330361403 (Ballesteros)", 1.32),
    ("2026-05-07", "ESUS330361236 (van de Ven)", 1.32),
    ("2026-05-07", "ESUS330361441 (Hampton)", 1.32),
    ("2026-05-04", "ESUS329529107 (Saddiq Bey)", 1.32),
    ("2026-05-04", "ESUS329528989 (Maxey)", 1.32),
    ("2026-05-04", "ESUS329528676 (Curry)", 1.32),
    ("2026-05-04", "ESUS329528880 (Lee)", 1.32),
    ("2026-05-04", "9400108106245114869449 (Trout RC)", 5.48),
    ("2026-04-25", "ESUS327504900 (Finnegan)", 1.32),
    ("2026-04-16", "ESUS325307846 (Gonzalez)", 1.32),
    ("2026-03-20", "ESUS319748152 (India)", 1.32),
    ("2026-03-12", "ESUS318012614 (Duran)", 1.32),
    ("2026-03-07", "ESUS316842268 (Funderburk)", 1.32),
    ("2026-03-07", "ESUS316842783 (Chris Martin)", 1.32),
    ("2026-03-07", "9434608106244887665687 (James Wood)", 8.35),
    ("2026-03-07", "9434608106244887504559 (Mets Lot)", 8.10),
    ("2026-03-06", "9400108106244883857411 (Yamamoto Refractor)", 5.27),
    ("2026-02-18", "ESUS313110527", 1.32),
    ("2026-02-15", "ESUS312610381 (Campbell)", 1.32),
    ("2026-02-13", "9400108106245830380778 (Ohtani lot)", 5.20),
    ("2026-02-09", "9400108106245811979298 (Angels lot)", 5.52),
    ("2026-02-04", "9400108106245798990798 (Waldrep)", 5.07),
    ("2026-01-24", "ESUS307055975 (Soto)", 1.32),
]

# ============================================================
# PURCHASES - eBay card purchases (inventory acquisition)
# ============================================================
ebay_purchases = [
    ("2026-05-31", "2025 Bowman's Best Blue Refractor Kevin McGonigle AUTO /150", 192.72, "IN TRANSIT"),
    ("2026-05-14", "2024 Bowman Draft Konnor Griffin 1st Sapphire #BDC-22", 137.68, "SOLD 5/26 for $175.24"),
    ("2026-05-12", "2025 Bowman's Best Auto Redemption Nick Kurtz B25-NK", 161.94, "IN INVENTORY"),
    ("2026-05-10", "2026 Heritage Paul Skenes Black Border (REFUNDED)", 32.74, "REFUNDED"),
    ("2026-05-10", "2024 Topps Inception Nolan Arenado Auto /50", 34.92, "SOLD 5/28 for $55.61"),
    ("2026-04-24", "2025 Bowman Draft Caden Bodine AXIS-Orange /25", 22.34, "IN INVENTORY"),
    ("2026-03-21", "2025 Topps Update Juan Soto Mystical Green Foil /99", 21.10, "IN INVENTORY"),
    ("2026-03-20", "Mike Trout 2011 Bowman Draft #101 RC", 59.27, "SOLD 4/30 for $78.00"),
    ("2026-03-01", "2025 Topps Chrome Update Negative Nick Kurtz RC", 49.25, "IN INVENTORY"),
    ("2026-02-26", "2024 Topps Chrome Yamamoto Base RC #18", 14.23, "SOLD as part of Yamamoto lot"),
    ("2026-02-26", "2024 Topps Chrome Yamamoto #18 Refractor RC", 25.96, "SOLD 3/5 for $45.27 (x2 lot)"),
    ("2026-02-22", "James Wood 2025 Chrome Black True Gold Auto /50", 203.08, "SOLD 3/7 for $288.35"),
]

# ============================================================
# OTHER PURCHASES (non-eBay single cards)
# ============================================================
whatnot_purchases = [
    ("2026-05-10", "Whatnot break/purchase", 20.37),
    ("2026-05-10", "Whatnot break/purchase", 36.29),
    ("2026-05-10", "Whatnot break/purchase", 44.27),
    ("2026-05-10", "Whatnot break/purchase", 33.76),
]

retail_purchases = [
    ("2026-05-27", "DicksSportingGoods.com (megabox?)", 52.75),
    ("2026-05-17", "Dicks Sporting Goods Grafton (blaster?)", 31.65),
    ("2026-05-15", "Dicks Sporting Goods Grafton (megabox?)", 94.95),
    ("2026-04-13", "Dicks Sporting Goods Grafton", 58.03),
    # Pending
    ("2026-05-31", "Dicks Sporting Goods Grafton (pending)", 60.14),
    ("2026-05-31", "TARGET.COM (pending)", 52.74),
    ("2026-05-31", "TARGET.COM (pending)", 52.74),
]

other_expenses = [
    ("2026-05-31", "OFFICEMAX/DEPOT (supplies)", 18.65),
    ("2026-05-31", "MITCH'S SPORTS CARDS (singles?)", 4.21),
    ("2026-05-20", "USPS PO (shipping supplies?)", 6.98),
]

# ============================================================
# ANALYSIS
# ============================================================

print("=" * 70)
print("TRADING CARD BUSINESS - PROFITABILITY ANALYSIS")
print(f"Period: January 23, 2026 - May 31, 2026")
print(f"Starting Capital: $1,000.00")
print("=" * 70)

# --- GROSS SALES ---
gross_sales = sum(s[2] + s[3] for s in sales)  # sale price + shipping charged to buyer
print(f"\n{'─' * 70}")
print("REVENUE (Gross Sales)")
print(f"{'─' * 70}")
print(f"  Total items sold: {len(sales)}")
print(f"  Gross merchandise sales: ${sum(s[2] for s in sales):,.2f}")
print(f"  Shipping charged to buyers: ${sum(s[3] for s in sales):,.2f}")
print(f"  GROSS REVENUE: ${gross_sales:,.2f}")

# --- EBAY FEES ---
# From the payments ledger, fees are broken into FVF and Promoted Listings
# Let me calculate total fees from the net column
total_ebay_fvf = sum(s[4] for s in sales if isinstance(s[4], (int, float)))
# Actually let me just use the raw fee data from the ledger
# FVF fees (included in each sale's fee column)
# Promoted Listings fees (separate charges)

# Recalculate from ledger data directly
fvf_fees = []
promoted_fees = []

# From the detailed ledger:
promoted_listings_fees = [
    18.31, 28.61, 7.23, 22.78, 1.25, 2.55, 0.77, 1.94, 5.90, 0.61,
    2.34, 0.46, 1.32, 0.53, 0.74, 0.89, 10.88, 0.59, 0.45, 0.46,
    0.87, 40.31, 3.21, 6.20, 1.74, 2.97, 4.86, 0
]

fvf_fees_list = [
    19.06, 29.56, 7.77, 23.62, 1.58, 3.00, 0.87, 1.08, 2.38, 6.42,
    1.37, 0.92, 0.76, 0.91, 1.40, 3.47, 2.79, 0.77, 0.66, 2.15,
    0.84, 0.63, 1.05, 1.21, 11.48, 0.90, 0.76, 0.77, 1.19, 41.48,
    3.68, 0.84, 6.72, 0.90, 2.71, 2.59, 3.67, 3.31, 6.83, 1.15
]

total_fvf = sum(fvf_fees_list)
total_promoted = sum(promoted_listings_fees)
total_shipping_paid = sum(s[2] for s in shipping_labels)

print(f"\n{'─' * 70}")
print("EBAY COSTS (Selling Fees)")
print(f"{'─' * 70}")
print(f"  Final Value Fees (FVF ~13%): ${total_fvf:,.2f}")
print(f"  Promoted Listings Fees:      ${total_promoted:,.2f}")
print(f"  Shipping Labels Paid:        ${total_shipping_paid:,.2f}")
print(f"  TOTAL EBAY COSTS:            ${total_fvf + total_promoted + total_shipping_paid:,.2f}")

# --- COST OF GOODS SOLD ---
print(f"\n{'─' * 70}")
print("COST OF GOODS SOLD (Card Purchases)")
print(f"{'─' * 70}")

ebay_purchase_total = sum(p[2] for p in ebay_purchases)
# Subtract the refund
ebay_purchase_net = ebay_purchase_total - 32.74  # Skenes was refunded
whatnot_total = sum(w[2] for w in whatnot_purchases)
retail_total = sum(r[2] for r in retail_purchases)
other_total = sum(o[2] for o in other_expenses)

print(f"  eBay single card purchases:  ${ebay_purchase_net:,.2f} ({len(ebay_purchases)-1} cards)")
print(f"  Whatnot breaks:              ${whatnot_total:,.2f} ({len(whatnot_purchases)} purchases)")
print(f"  Retail (Dicks/Target boxes): ${retail_total:,.2f} ({len(retail_purchases)} purchases)")
print(f"  Other (supplies, LCS, USPS): ${other_total:,.2f}")
print(f"  TOTAL COGS + EXPENSES:       ${ebay_purchase_net + whatnot_total + retail_total + other_total:,.2f}")

# --- NET PROFIT/LOSS ---
print(f"\n{'─' * 70}")
print("PROFIT & LOSS SUMMARY")
print(f"{'─' * 70}")

total_revenue = gross_sales
total_costs = (total_fvf + total_promoted + total_shipping_paid + 
               ebay_purchase_net + whatnot_total + retail_total + other_total)
net_pl = total_revenue - total_costs

print(f"  Gross Revenue:               ${total_revenue:,.2f}")
print(f"  Less: eBay Fees:             -${total_fvf + total_promoted:,.2f}")
print(f"  Less: Shipping Costs:        -${total_shipping_paid:,.2f}")
print(f"  Less: Card Purchases (eBay): -${ebay_purchase_net:,.2f}")
print(f"  Less: Whatnot Breaks:        -${whatnot_total:,.2f}")
print(f"  Less: Retail Boxes:          -${retail_total:,.2f}")
print(f"  Less: Other Expenses:        -${other_total:,.2f}")
print(f"  {'─' * 50}")
print(f"  NET PROFIT/(LOSS):           ${net_pl:,.2f}")

# --- BANK ACCOUNT RECONCILIATION ---
print(f"\n{'─' * 70}")
print("BANK ACCOUNT RECONCILIATION")
print(f"{'─' * 70}")
# Current balance from bank statement
current_bank = 699.62  # last posted balance
pending_out = 192.72 + 18.65 + 60.14 + 4.21 + 52.74 + 52.74
pending_in = 0  # the eBay payment for Murakami/Tolle hasn't hit bank yet

print(f"  Starting balance (Mar 2):    $1,000.00")
print(f"  Current posted balance:      ${current_bank:,.2f}")
print(f"  Pending outflows:            -${pending_out:,.2f}")
print(f"  Projected balance:           ${current_bank - pending_out:,.2f}")
print(f"  eBay funds not yet paid out: $284.69")
print(f"  TRUE CASH POSITION:          ${current_bank - pending_out + 284.69:,.2f}")

# --- INVENTORY VALUE ---
print(f"\n{'─' * 70}")
print("CURRENT INVENTORY (Unsold Cards at Cost)")
print(f"{'─' * 70}")

inventory = [
    ("2025 Bowman's Best Blue Refractor Kevin McGonigle AUTO /150", 192.72, "Just bought - in transit"),
    ("2025 Bowman's Best Auto Redemption Nick Kurtz B25-NK", 161.94, "Redemption card"),
    ("2025 Bowman Draft Caden Bodine AXIS-Orange /25", 22.34, "In inventory"),
    ("2025 Topps Update Juan Soto Mystical Green Foil /99", 21.10, "In inventory"),
    ("2025 Topps Chrome Update Negative Nick Kurtz RC", 49.25, "In inventory"),
]

for item, cost, status in inventory:
    print(f"  ${cost:>7.2f}  {item[:55]}")
print(f"  {'─' * 50}")
inv_total = sum(i[1] for i in inventory)
print(f"  TOTAL INVENTORY AT COST:     ${inv_total:,.2f}")

# --- KEY FLIPS ---
print(f"\n{'─' * 70}")
print("TOP FLIPS (Buy -> Sell -> Profit)")
print(f"{'─' * 70}")

flips = [
    ("James Wood Chrome Black Gold Auto /50", 203.08, 288.35, 41.48+40.31+8.35),
    ("Konnor Griffin 1st Sapphire", 137.68, 175.24, 23.62+22.78+5.24),
    ("Mike Trout 2011 Bowman Draft RC", 59.27, 78.00, 11.48+10.88+5.48),
    ("Nolan Arenado Inception Auto /50", 34.92, 55.61, 7.77+7.23+5.62),
    ("Yamamoto Refractor (x2 sold as lot)", 14.23+25.96, 45.27, 6.72+6.20+5.27),
]

total_flip_profit = 0
for name, cost, sale, fees in flips:
    profit = sale - cost - fees
    total_flip_profit += profit
    print(f"  {name[:45]:<45} Cost: ${cost:>7.2f}  Sold: ${sale:>7.2f}  Fees: ${fees:>6.2f}  PROFIT: ${profit:>7.2f}")

print(f"\n  Total profit from tracked flips: ${total_flip_profit:,.2f}")

# --- WHERE THE MONEY IS GOING ---
print(f"\n{'─' * 70}")
print("WHERE YOUR MONEY IS GOING")
print(f"{'─' * 70}")

categories = [
    ("eBay Fees (FVF + Promoted)", total_fvf + total_promoted),
    ("Shipping Labels", total_shipping_paid),
    ("Retail Boxes (Dicks/Target)", retail_total),
    ("Whatnot Breaks", whatnot_total),
    ("eBay Card Purchases (inventory)", ebay_purchase_net),
    ("Other (supplies, LCS, USPS)", other_total),
]

total_spent = sum(c[1] for c in categories)
for name, amount in sorted(categories, key=lambda x: -x[1]):
    pct = amount / total_spent * 100
    bar = "█" * int(pct / 2)
    print(f"  {name:<35} ${amount:>8.2f}  ({pct:>4.1f}%) {bar}")

# --- THE REAL ANSWER ---
print(f"\n{'═' * 70}")
print("THE BOTTOM LINE")
print(f"{'═' * 70}")
print(f"""
  You started with $1,000 on March 2, 2026.
  
  Current bank balance (posted):     ${current_bank:,.2f}
  Plus eBay funds pending payout:    $284.69
  Less pending charges:              -${pending_out:,.2f}
  ═══════════════════════════════════════════
  CASH POSITION TODAY:               ${current_bank + 284.69 - pending_out:,.2f}
  
  Plus inventory at cost:            ${inv_total:,.2f}
  ═══════════════════════════════════════════
  TOTAL BUSINESS VALUE:              ${current_bank + 284.69 - pending_out + inv_total:,.2f}
  
  vs Starting Capital:               $1,000.00
  ═══════════════════════════════════════════
  NET GAIN/(LOSS):                   ${current_bank + 284.69 - pending_out + inv_total - 1000:,.2f}
""")

# Effective fee rate
net_after_fees = sum(s[2] for s in sales) - total_fvf - total_promoted
effective_fee_rate = (total_fvf + total_promoted) / sum(s[2] for s in sales) * 100
print(f"  Your effective eBay fee rate: {effective_fee_rate:.1f}% (FVF + Promoted Listings)")
print(f"  Industry standard is ~13% FVF only. You're paying extra for Promoted.")
print(f"  Promoted Listings alone cost you: ${total_promoted:,.2f}")
print()
