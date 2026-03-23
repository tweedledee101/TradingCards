#!/usr/bin/env python3
"""
Opportunity QA - Background Validation

Runs against stored opportunities and flags suspicious matches.
Does NOT block the pipeline. Run after pipeline completes.

Usage:
    python3 qa_opportunities.py                  # QA all pending
    python3 qa_opportunities.py --scan-id 52     # QA specific run
    python3 qa_opportunities.py --recheck        # Re-QA previously flagged

Flags:
    extreme_roi       ROI > 500% -- almost certainly wrong SCP match
    high_roi          ROI > 300% -- likely wrong SCP match
    price_ratio_10x   SCP price is 10x+ the total cost
    no_scp_url        No SCP URL to verify against
    selenium_source   Price came from Selenium (not DB) -- less reliable
    low_bid_high_scp  Current bid < $5 but SCP > $50 -- early auction noise
"""
import argparse
import json
import statistics
from datetime import datetime, timedelta
from backend.utils.database import SessionLocal
from backend.models import Opportunity, SoldComp
from sqlalchemy import func

QA_RULES = [
    {
        'name': 'extreme_roi',
        'severity': 'critical',
        'check': lambda o: o.roi and float(o.roi) > 500,
        'reason': lambda o: f"ROI {float(o.roi):.0f}% -- almost certainly wrong SCP match",
    },
    {
        'name': 'high_roi',
        'severity': 'warning',
        'check': lambda o: o.roi and 300 < float(o.roi) <= 500,
        'reason': lambda o: f"ROI {float(o.roi):.0f}% -- verify SCP match",
    },
    {
        'name': 'price_ratio_10x',
        'severity': 'warning',
        'check': lambda o: (o.scp_price and o.buy_price and o.shipping is not None
                           and float(o.scp_price) > (float(o.buy_price) + float(o.shipping or 0)) * 10),
        'reason': lambda o: f"SCP ${float(o.scp_price):.2f} is 10x+ cost ${float(o.buy_price) + float(o.shipping or 0):.2f}",
    },
    {
        'name': 'no_scp_url',
        'severity': 'info',
        'check': lambda o: not o.scp_url,
        'reason': lambda o: "No SCP URL -- cannot verify price",
    },
    {
        'name': 'card_number_mismatch',
        'severity': 'critical',
        'check': lambda o: (o.scp_url and o.card_number
                           and f'-{o.card_number.lower()}' not in o.scp_url.lower()
                           and not o.scp_url.lower().endswith(o.card_number.lower())),
        'reason': lambda o: f"Card #{o.card_number} not found in SCP URL: {o.scp_url}",
    },
    {
        'name': 'low_bid_high_scp',
        'severity': 'warning',
        'check': lambda o: (o.listing_type == 'auction' and o.buy_price
                           and float(o.buy_price) < 5 and o.scp_price
                           and float(o.scp_price) > 50),
        'reason': lambda o: f"Bid ${float(o.buy_price):.2f} vs SCP ${float(o.scp_price):.2f} -- auction likely to climb",
    },
]

# Cross-validation rule runs separately (needs DB query per opportunity)
SCP_SOLD_COMP_DIVERGENCE = 0.50  # flag if >50% apart
MIN_COMPS_FOR_CROSSVAL = 3       # need at least 3 sold comps to be meaningful


def check_scp_vs_sold_comps(db, opp) -> dict:
    """Cross-validate SCP price against 130point sold comps.

    Returns a flag dict if divergence > 50%, else None.
    Only runs when we have both SCP price and 3+ sold comps.
    """
    if not opp.scp_price or not opp.card_number:
        return None

    scp = float(opp.scp_price)
    cutoff = datetime.now() - timedelta(hours=72)

    comps = db.query(SoldComp.sale_price).filter(
        func.lower(SoldComp.player_name) == opp.player_name.lower(),
        SoldComp.card_year == opp.card_year,
        func.lower(SoldComp.card_number) == (opp.card_number or '').lower(),
        SoldComp.created_at > cutoff,
    ).all()

    if len(comps) < MIN_COMPS_FOR_CROSSVAL:
        return None

    prices = sorted([float(c.sale_price) for c in comps])
    # Trim top/bottom 20% outliers if enough data
    if len(prices) >= 5:
        trim = max(1, len(prices) // 5)
        prices = prices[trim:-trim]
    median = statistics.median(prices)

    if median <= 0:
        return None

    divergence = abs(scp - median) / max(scp, median)
    if divergence <= SCP_SOLD_COMP_DIVERGENCE:
        return None

    direction = 'higher' if scp > median else 'lower'
    severity = 'critical' if divergence > 0.75 else 'warning'
    return {
        'rule': 'scp_vs_sold_comps',
        'severity': severity,
        'reason': f"SCP ${scp:.2f} is {divergence:.0%} {direction} than 130point median ${median:.2f} ({len(comps)} sold comps)",
    }


def run_qa(scan_id=None, recheck=False):
    db = SessionLocal()
    try:
        query = db.query(Opportunity)

        if scan_id:
            query = query.filter(Opportunity.scan_id == scan_id)

        if recheck:
            query = query.filter(Opportunity.qa_status == 'flagged')
        else:
            query = query.filter(Opportunity.qa_status == 'pending')

        opportunities = query.all()
        print(f"QA reviewing {len(opportunities)} opportunities...")
        print("-" * 60)

        counts = {'clean': 0, 'flagged': 0, 'critical': 0, 'crossval': 0}

        for opp in opportunities:
            flags = []
            for rule in QA_RULES:
                try:
                    if rule['check'](opp):
                        flags.append({
                            'rule': rule['name'],
                            'severity': rule['severity'],
                            'reason': rule['reason'](opp),
                        })
                except Exception:
                    continue

            # Cross-validation: SCP vs 130point sold comps
            crossval_flag = check_scp_vs_sold_comps(db, opp)
            if crossval_flag:
                flags.append(crossval_flag)
                counts['crossval'] += 1

            has_critical = any(f['severity'] == 'critical' for f in flags)

            if flags:
                opp.qa_status = 'critical' if has_critical else 'flagged'
                opp.qa_flags = flags
                opp.flagged = has_critical
                counts['critical' if has_critical else 'flagged'] += 1

                label = f"{opp.player_name} {opp.card_year} #{opp.card_number} [{opp.parallel}]"
                tag = 'CRITICAL' if has_critical else 'FLAG'
                print(f"  [{tag}] {label}")
                for f in flags:
                    print(f"    - [{f['severity']}] {f['reason']}")
                if opp.scp_url:
                    print(f"    SCP: {opp.scp_url}")
                if opp.ebay_url:
                    print(f"    eBay: {opp.ebay_url}")
            else:
                opp.qa_status = 'clean'
                counts['clean'] += 1

            opp.qa_reviewed_at = datetime.now()

        db.commit()

        print(f"\nQA complete: {counts['clean']} clean, {counts['flagged']} flagged, {counts['critical']} critical")
        if counts['crossval']:
            print(f"  Cross-validation flags: {counts['crossval']} (SCP vs 130point sold comps)")

    finally:
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='QA review stored opportunities')
    parser.add_argument('--scan-id', type=int, help='QA a specific pipeline run')
    parser.add_argument('--recheck', action='store_true', help='Re-QA previously flagged opportunities')
    args = parser.parse_args()

    run_qa(scan_id=args.scan_id, recheck=args.recheck)
