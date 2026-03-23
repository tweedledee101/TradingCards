"""
Daily Operations Report

Generates a daily summary of pipeline health, data quality, and opportunities.
Runs after pipelines complete. Outputs structured report to stdout and optionally
stores in database.

Tiers covered:
  Tier 2 - Runtime monitoring: pipeline job status, error rates, API health
  Tier 3 - Post-run validation: QA rules, data integrity, stale data detection
  Tier 4 - Daily report: summary stats, trends, action items
"""

import sys
import os
import json
from datetime import datetime, timedelta, date
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.utils.database import SessionLocal


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def get_db():
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


def run_report():
    db = get_db()
    report = {}

    try:
        # === TIER 2: Runtime Health ===
        report['pipeline_health'] = check_pipeline_health(db)
        report['database_health'] = check_database_health(db)
        report['data_freshness'] = check_data_freshness(db)

        # === TIER 3: Post-Run Validation ===
        report['data_quality'] = check_data_quality(db)
        report['qa_flags'] = check_qa_flags(db)

        # === TIER 4: Daily Summary ===
        report['opportunities'] = summarize_opportunities(db)
        report['trends'] = calculate_trends(db)
        report['action_items'] = generate_action_items(report)

        report['generated_at'] = datetime.utcnow().isoformat()
        report['status'] = 'OK' if not report['action_items']['critical'] else 'NEEDS_ATTENTION'

        # Print report
        print("=" * 70)
        print("RAGNAROK GAMING - DAILY OPERATIONS REPORT")
        print(f"Generated: {report['generated_at']} UTC")
        print(f"Status: {report['status']}")
        print("=" * 70)

        print_section("PIPELINE HEALTH", report['pipeline_health'])
        print_section("DATABASE HEALTH", report['database_health'])
        print_section("DATA FRESHNESS", report['data_freshness'])
        print_section("DATA QUALITY", report['data_quality'])
        print_section("QA FLAGS", report['qa_flags'])
        print_section("OPPORTUNITIES", report['opportunities'])
        print_section("TRENDS", report['trends'])
        print_action_items(report['action_items'])

        # Output JSON for artifact storage
        with open('/tmp/daily-report.json', 'w') as f:
            json.dump(report, f, indent=2, cls=DecimalEncoder)

        return report

    finally:
        db.close()


def check_pipeline_health(db):
    """Tier 2: Check recent job_runs for pipeline status"""
    result = {'bin_pipeline': None, 'auction_pipeline': None, 'errors_24h': 0}

    try:
        cutoff = datetime.utcnow() - timedelta(hours=24)

        # Latest BIN pipeline run
        row = db.execute(
            """SELECT status, started_at, completed_at, items_processed, items_total,
                      results_summary
               FROM job_runs WHERE job_name = 'opportunity_pipeline'
               ORDER BY started_at DESC LIMIT 1"""
        ).fetchone()
        if row:
            duration = None
            if row[2] and row[1]:
                duration = str(row[2] - row[1])
            result['bin_pipeline'] = {
                'status': row[0],
                'started_at': row[1],
                'completed_at': row[2],
                'duration': duration,
                'items_processed': row[3],
                'items_total': row[4],
                'summary': row[5]
            }

        # Latest Auction pipeline run
        row = db.execute(
            """SELECT status, started_at, completed_at, items_processed, items_total,
                      results_summary
               FROM job_runs WHERE job_name = 'auction_pipeline'
               ORDER BY started_at DESC LIMIT 1"""
        ).fetchone()
        if row:
            duration = None
            if row[2] and row[1]:
                duration = str(row[2] - row[1])
            result['auction_pipeline'] = {
                'status': row[0],
                'started_at': row[1],
                'completed_at': row[2],
                'duration': duration,
                'items_processed': row[3],
                'items_total': row[4],
                'summary': row[5]
            }

        # Error count in last 24h
        err_row = db.execute(
            """SELECT COUNT(*) FROM error_log WHERE created_at > :cutoff""",
            {'cutoff': cutoff}
        ).fetchone()
        result['errors_24h'] = err_row[0] if err_row else 0

    except Exception as e:
        result['error'] = str(e)

    return result


def check_database_health(db):
    """Tier 2: Table sizes and connection health"""
    result = {}
    try:
        tables = ['opportunities', 'cards', 'market_rates', 'active_listings',
                   'sales', 'scp_cache', 'sold_comps', 'job_runs', 'error_log',
                   'scheduled_bids', 'inventory', 'inventory_sales']
        for table in tables:
            try:
                row = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                result[table] = row[0] if row else 0
            except Exception:
                result[table] = 'TABLE_MISSING'

    except Exception as e:
        result['error'] = str(e)

    return result


def check_data_freshness(db):
    """Tier 2: How old is our data?"""
    result = {}
    try:
        # Latest opportunity
        row = db.execute(
            "SELECT MAX(created_at) FROM opportunities"
        ).fetchone()
        result['latest_opportunity'] = row[0] if row and row[0] else None

        # Latest SCP cache entry
        row = db.execute(
            "SELECT MAX(created_at) FROM scp_cache"
        ).fetchone()
        result['latest_scp_cache'] = row[0] if row and row[0] else None

        # Latest sold comp
        row = db.execute(
            "SELECT MAX(created_at) FROM sold_comps"
        ).fetchone()
        result['latest_sold_comp'] = row[0] if row and row[0] else None

        # Stale SCP cache (>24h old)
        cutoff_24h = datetime.utcnow() - timedelta(hours=24)
        row = db.execute(
            "SELECT COUNT(*) FROM scp_cache WHERE created_at < :cutoff",
            {'cutoff': cutoff_24h}
        ).fetchone()
        result['stale_scp_entries'] = row[0] if row else 0

        # Expired opportunities (auctions that ended)
        row = db.execute(
            """SELECT COUNT(*) FROM opportunities
               WHERE listing_type = 'auction' AND end_time < NOW()"""
        ).fetchone()
        result['expired_auctions'] = row[0] if row else 0

    except Exception as e:
        result['error'] = str(e)

    return result


def check_data_quality(db):
    """Tier 3: Data integrity checks"""
    result = {'issues': []}
    try:
        # Opportunities with no SCP price
        row = db.execute(
            "SELECT COUNT(*) FROM opportunities WHERE scp_price IS NULL OR scp_price = 0"
        ).fetchone()
        if row and row[0] > 0:
            result['issues'].append(f"{row[0]} opportunities with no SCP price")

        # Opportunities with negative profit
        row = db.execute(
            "SELECT COUNT(*) FROM opportunities WHERE net_profit < 0"
        ).fetchone()
        if row and row[0] > 0:
            result['issues'].append(f"{row[0]} opportunities with negative profit")

        # Duplicate eBay item IDs
        row = db.execute(
            """SELECT COUNT(*) FROM (
                SELECT ebay_item_id, COUNT(*) as cnt
                FROM opportunities
                WHERE ebay_item_id IS NOT NULL
                GROUP BY ebay_item_id HAVING COUNT(*) > 1
            ) dupes"""
        ).fetchone()
        if row and row[0] > 0:
            result['issues'].append(f"{row[0]} duplicate eBay item IDs in opportunities")

        result['issue_count'] = len(result['issues'])

    except Exception as e:
        result['error'] = str(e)

    return result


def check_qa_flags(db):
    """Tier 3: QA flag summary"""
    result = {'flags': {}, 'total_flagged': 0}
    try:
        rows = db.execute(
            """SELECT qa_flags, COUNT(*) FROM opportunities
               WHERE qa_flags IS NOT NULL AND qa_flags != '[]' AND qa_flags != 'null'
               GROUP BY qa_flags"""
        ).fetchall()

        for row in rows:
            flags = row[0] if isinstance(row[0], list) else json.loads(row[0] or '[]')
            for flag in flags:
                flag_name = flag if isinstance(flag, str) else flag.get('rule', str(flag))
                result['flags'][flag_name] = result['flags'].get(flag_name, 0) + 1
                result['total_flagged'] += 1

    except Exception as e:
        result['error'] = str(e)

    return result


def summarize_opportunities(db):
    """Tier 4: Opportunity summary"""
    result = {}
    try:
        # Total by listing type
        rows = db.execute(
            """SELECT listing_type, COUNT(*), AVG(net_profit), AVG(roi),
                      SUM(net_profit), MIN(buy_price), MAX(buy_price)
               FROM opportunities
               GROUP BY listing_type"""
        ).fetchall()

        for row in rows:
            result[row[0] or 'unknown'] = {
                'count': row[1],
                'avg_profit': round(float(row[2] or 0), 2),
                'avg_roi': round(float(row[3] or 0), 1),
                'total_potential_profit': round(float(row[4] or 0), 2),
                'price_range': f"${row[5] or 0:.2f} - ${row[6] or 0:.2f}"
            }

        # Top 5 by profit
        rows = db.execute(
            """SELECT player_name, card_name, buy_price, scp_price, net_profit, roi, listing_type
               FROM opportunities
               ORDER BY net_profit DESC LIMIT 5"""
        ).fetchall()
        result['top_5'] = [
            {
                'player': row[0], 'card': row[1],
                'buy': float(row[2] or 0), 'scp': float(row[3] or 0),
                'profit': float(row[4] or 0), 'roi': float(row[5] or 0),
                'type': row[6]
            }
            for row in rows
        ]

        # Players with most opportunities
        rows = db.execute(
            """SELECT player_name, COUNT(*) as cnt
               FROM opportunities GROUP BY player_name
               ORDER BY cnt DESC LIMIT 10"""
        ).fetchall()
        result['top_players'] = [{'player': row[0], 'count': row[1]} for row in rows]

    except Exception as e:
        result['error'] = str(e)

    return result


def calculate_trends(db):
    """Tier 4: Compare to previous runs"""
    result = {}
    try:
        # Opportunity count over last 7 days
        rows = db.execute(
            """SELECT DATE(created_at) as day, COUNT(*)
               FROM opportunities
               WHERE created_at > NOW() - INTERVAL '7 days'
               GROUP BY DATE(created_at)
               ORDER BY day"""
        ).fetchall()
        result['daily_opportunity_counts'] = [
            {'date': row[0], 'count': row[1]} for row in rows
        ]

        # Job run history (last 7 days)
        rows = db.execute(
            """SELECT job_name, status, started_at, completed_at
               FROM job_runs
               WHERE started_at > NOW() - INTERVAL '7 days'
               ORDER BY started_at DESC"""
        ).fetchall()
        result['recent_jobs'] = [
            {'job': row[0], 'status': row[1], 'started': row[2], 'completed': row[3]}
            for row in rows
        ]

        # Error trend
        rows = db.execute(
            """SELECT DATE(created_at) as day, COUNT(*)
               FROM error_log
               WHERE created_at > NOW() - INTERVAL '7 days'
               GROUP BY DATE(created_at)
               ORDER BY day"""
        ).fetchall()
        result['daily_error_counts'] = [
            {'date': row[0], 'count': row[1]} for row in rows
        ]

    except Exception as e:
        result['error'] = str(e)

    return result


def generate_action_items(report):
    """Tier 4: What needs attention?"""
    critical = []
    warnings = []
    info = []

    # Pipeline failures
    ph = report.get('pipeline_health', {})
    for pipeline in ['bin_pipeline', 'auction_pipeline']:
        p = ph.get(pipeline)
        if p and p.get('status') == 'failed':
            critical.append(f"{pipeline} FAILED -- check logs")
        elif p is None:
            warnings.append(f"{pipeline} has never run")

    # High error rate
    if ph.get('errors_24h', 0) > 50:
        critical.append(f"{ph['errors_24h']} errors in last 24h")
    elif ph.get('errors_24h', 0) > 10:
        warnings.append(f"{ph['errors_24h']} errors in last 24h")

    # Data freshness
    df = report.get('data_freshness', {})
    if df.get('stale_scp_entries', 0) > 100:
        warnings.append(f"{df['stale_scp_entries']} stale SCP cache entries (>24h)")
    if df.get('expired_auctions', 0) > 20:
        info.append(f"{df['expired_auctions']} expired auctions to clean up")

    # Data quality
    dq = report.get('data_quality', {})
    if dq.get('issue_count', 0) > 0:
        for issue in dq.get('issues', []):
            warnings.append(issue)

    # QA flags
    qa = report.get('qa_flags', {})
    if qa.get('total_flagged', 0) > 0:
        info.append(f"{qa['total_flagged']} opportunities with QA flags")

    # No opportunities found
    opps = report.get('opportunities', {})
    total_opps = sum(v.get('count', 0) for k, v in opps.items() if isinstance(v, dict) and 'count' in v)
    if total_opps == 0:
        critical.append("No opportunities found -- pipeline may be broken")
    elif total_opps < 10:
        warnings.append(f"Only {total_opps} opportunities found -- check filters")

    return {'critical': critical, 'warnings': warnings, 'info': info}


def print_section(title, data):
    print(f"\n--- {title} ---")
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict):
                print(f"  {k}:")
                for k2, v2 in v.items():
                    print(f"    {k2}: {v2}")
            elif isinstance(v, list):
                print(f"  {k}:")
                for item in v[:10]:
                    print(f"    - {item}")
            else:
                print(f"  {k}: {v}")


def print_action_items(items):
    print("\n" + "=" * 70)
    print("ACTION ITEMS")
    print("=" * 70)

    if items['critical']:
        print("\n  CRITICAL:")
        for item in items['critical']:
            print(f"    [!] {item}")

    if items['warnings']:
        print("\n  WARNINGS:")
        for item in items['warnings']:
            print(f"    [~] {item}")

    if items['info']:
        print("\n  INFO:")
        for item in items['info']:
            print(f"    [i] {item}")

    if not items['critical'] and not items['warnings']:
        print("\n  All clear -- no issues detected.")


if __name__ == '__main__':
    run_report()
