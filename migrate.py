"""
Database Migration Runner

Tracks applied migrations in a schema_migrations table.
Applies missing migrations in order. Works against any target database.

Usage:
    python3 migrate.py              # migrate whatever DATABASE_URL points to
    python3 migrate.py --local      # migrate local postgres
    python3 migrate.py --rds        # migrate RDS
    python3 migrate.py --both       # migrate both local and RDS
    python3 migrate.py --status     # show what's applied vs pending
"""
import os
import sys
import glob
import argparse
import psycopg2
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), 'backend', '.env'))

LOCAL_URL = "postgresql://postgres:postgres@localhost:5432/trading_cards"
RDS_URL = os.getenv('DATABASE_URL', LOCAL_URL)
MIGRATION_DIR = os.path.join(os.path.dirname(__file__), 'backend', 'models')

BOOTSTRAP_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL UNIQUE,
    applied_at TIMESTAMP NOT NULL DEFAULT NOW()
);
"""


def get_migration_files():
    pattern = os.path.join(MIGRATION_DIR, 'migration_*.sql')
    files = sorted(glob.glob(pattern))
    return [(os.path.basename(f), f) for f in files]


def get_applied(conn):
    cur = conn.cursor()
    cur.execute("SELECT filename FROM schema_migrations ORDER BY filename")
    return {row[0] for row in cur.fetchall()}


def apply_migration(conn, filename, filepath):
    with open(filepath, 'r') as f:
        sql = f.read()
    cur = conn.cursor()
    try:
        cur.execute(sql)
        cur.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (filename,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        # If it fails because objects already exist, record it as applied
        err = str(e).lower()
        if 'already exists' in err or 'duplicate' in err:
            cur2 = conn.cursor()
            cur2.execute("INSERT INTO schema_migrations (filename) VALUES (%s) ON CONFLICT DO NOTHING", (filename,))
            conn.commit()
            return 'skipped'
        print(f"  ERROR: {e}")
        return False


def migrate(db_url, label="database"):
    print(f"\n=== Migrating: {label} ===")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = False
    except Exception as e:
        print(f"  Connection failed: {e}")
        return False

    # Bootstrap tracking table
    cur = conn.cursor()
    cur.execute(BOOTSTRAP_SQL)
    conn.commit()

    applied = get_applied(conn)
    migrations = get_migration_files()
    pending = [(name, path) for name, path in migrations if name not in applied]

    if not pending:
        print(f"  Up to date ({len(applied)} migrations applied)")
        conn.close()
        return True

    print(f"  {len(applied)} applied, {len(pending)} pending")
    for name, path in pending:
        result = apply_migration(conn, name, path)
        if result is True:
            print(f"  Applied: {name}")
        elif result == 'skipped':
            print(f"  Recorded: {name} (already existed)")
        else:
            print(f"  FAILED: {name}")
            conn.close()
            return False

    conn.close()
    print(f"  Done -- {len(pending)} migrations applied")
    return True


def show_status(db_url, label="database"):
    print(f"\n=== Status: {label} ===")
    try:
        conn = psycopg2.connect(db_url)
    except Exception as e:
        print(f"  Connection failed: {e}")
        return

    cur = conn.cursor()
    cur.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='schema_migrations')")
    if not cur.fetchone()[0]:
        print("  No schema_migrations table -- migrations not tracked yet")
        conn.close()
        return

    applied = get_applied(conn)
    migrations = get_migration_files()
    pending = [name for name, _ in migrations if name not in applied]

    print(f"  Applied: {len(applied)}")
    if pending:
        print(f"  Pending: {len(pending)}")
        for name in pending:
            print(f"    - {name}")
    else:
        print("  Up to date")
    conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Database migration runner')
    parser.add_argument('--local', action='store_true', help='Target local database')
    parser.add_argument('--rds', action='store_true', help='Target RDS database')
    parser.add_argument('--both', action='store_true', help='Target both local and RDS')
    parser.add_argument('--status', action='store_true', help='Show migration status')
    args = parser.parse_args()

    if args.status:
        if args.both or (not args.local and not args.rds):
            show_status(LOCAL_URL, "Local")
            show_status(RDS_URL, "RDS")
        elif args.local:
            show_status(LOCAL_URL, "Local")
        elif args.rds:
            show_status(RDS_URL, "RDS")
        sys.exit(0)

    if args.both:
        r1 = migrate(LOCAL_URL, "Local")
        r2 = migrate(RDS_URL, "RDS")
        sys.exit(0 if r1 and r2 else 1)
    elif args.local:
        sys.exit(0 if migrate(LOCAL_URL, "Local") else 1)
    elif args.rds:
        sys.exit(0 if migrate(RDS_URL, "RDS") else 1)
    else:
        # Default: migrate whatever DATABASE_URL points to
        sys.exit(0 if migrate(RDS_URL, "DATABASE_URL target") else 1)
