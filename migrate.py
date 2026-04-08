"""
Database Migration Runner

Tracks applied migrations in a schema_migrations table.
Applies missing migrations in order. Works against any target database.

Usage:
    python3 migrate.py              # migrate whatever DATABASE_URL points to
    python3 migrate.py --local      # migrate local postgres
    python3 migrate.py --rds        # migrate RDS
    python3 migrate.py --dev        # dev DB: DATABASE_URL_DEV or same host as DATABASE_URL + /trading_cards_dev
    python3 migrate.py --both       # migrate both local and RDS
    python3 migrate.py --all-db     # local + RDS + dev (explicit or derived dev URL)
    python3 migrate.py --status     # show what's applied vs pending

    With --dev / --all-db, creates ``trading_cards_dev`` on the instance if missing (override: --no-create-dev-db).

    Empty databases get ``backend/models/schema.sql`` applied automatically before ``migration_*.sql`` (those migrations assume base tables exist).
"""
import os
import sys
import glob
import argparse
import psycopg2
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), 'backend', '.env'))

from backend.utils.dev_postgres import (
    DEFAULT_DEV_DATABASE,
    ensure_dev_database_exists,
    pg_username_from_url,
    resolve_dev_database_url,
)

LOCAL_URL = "postgresql://postgres:postgres@localhost:5432/trading_cards"
RDS_URL = os.getenv('DATABASE_URL', LOCAL_URL)
MIGRATION_DIR = os.path.join(os.path.dirname(__file__), 'backend', 'models')
BASE_SCHEMA_FILE = os.path.join(MIGRATION_DIR, 'schema.sql')

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


def _needs_base_schema(conn) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT to_regclass('public.cards') IS NULL")
    return bool(cur.fetchone()[0])


def _apply_base_schema(conn) -> bool:
    if not os.path.isfile(BASE_SCHEMA_FILE):
        print(f"  ERROR: missing base schema file {BASE_SCHEMA_FILE}", file=sys.stderr)
        return False
    print("  Fresh database: applying backend/models/schema.sql before numbered migrations")
    with open(BASE_SCHEMA_FILE, encoding='utf-8') as f:
        sql = f.read()
    cur = conn.cursor()
    try:
        cur.execute(sql)
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print(f"  ERROR applying schema.sql: {e}")
        return False


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

    if _needs_base_schema(conn):
        if not _apply_base_schema(conn):
            conn.close()
            return False

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
    parser.add_argument(
        '--dev',
        action='store_true',
        help='Target dev DB (DATABASE_URL_DEV or derived …/trading_cards_dev from DATABASE_URL)',
    )
    parser.add_argument('--both', action='store_true', help='Target both local and RDS')
    parser.add_argument(
        '--all-db',
        action='store_true',
        help='Migrate local, RDS (DATABASE_URL), and DATABASE_URL_DEV',
    )
    parser.add_argument('--status', action='store_true', help='Show migration status')
    parser.add_argument(
        '--no-create-dev-db',
        action='store_true',
        help='With --dev / --all-db: do not CREATE DATABASE if missing',
    )
    args = parser.parse_args()

    def _prod_url_for_dev_derive() -> str:
        u = (os.getenv('DATABASE_URL') or '').strip()
        return u if u else LOCAL_URL

    def _resolved_dev_url():
        return resolve_dev_database_url(
            explicit_dev=os.getenv('DATABASE_URL_DEV'),
            prod_url=_prod_url_for_dev_derive(),
            default_dev_db=DEFAULT_DEV_DATABASE,
        )

    def _need_dev_url(*, quiet: bool = False):
        url, src = _resolved_dev_url()
        if not url:
            print(
                'error: could not resolve dev database URL (set DATABASE_URL_DEV explicitly)',
                file=sys.stderr,
            )
            sys.exit(2)
        if src == 'derived from DATABASE_URL' and not quiet:
            print(f'  ({src}; add DATABASE_URL_DEV to backend/.env for tooling that prefers an explicit line)')
        return url

    def _ensure_dev_db(dev_url: str) -> None:
        if args.no_create_dev_db:
            return
        user = pg_username_from_url(dev_url)
        ok, msg = ensure_dev_database_exists(dev_url, grant_to_username=user or None)
        print(f'  {msg}')
        if not ok:
            print(
                '  hint: use a DB role with CREATEDB / superuser, or create the DB manually — '
                'aws/scripts/create_trading_cards_dev_database.md',
                file=sys.stderr,
            )
            sys.exit(1)

    if args.status:
        if args.all_db:
            show_status(LOCAL_URL, "Local")
            show_status(RDS_URL, "RDS")
            dev_url, src = _resolved_dev_url()
            if dev_url:
                print(f"\n  (dev URL: {src})")
                show_status(dev_url, "DATABASE_URL_DEV")
            else:
                print(
                    f"\n=== Status: DATABASE_URL_DEV ===\n"
                    f"  (not set; set DATABASE_URL_DEV or DATABASE_URL to derive …/{DEFAULT_DEV_DATABASE})"
                )
        elif args.dev:
            show_status(_need_dev_url(quiet=True), "DATABASE_URL_DEV")
        elif args.both or (not args.local and not args.rds and not args.dev):
            show_status(LOCAL_URL, "Local")
            show_status(RDS_URL, "RDS")
        elif args.local:
            show_status(LOCAL_URL, "Local")
        elif args.rds:
            show_status(RDS_URL, "RDS")
        sys.exit(0)

    if args.all_db:
        dev_url = _need_dev_url()
        _ensure_dev_db(dev_url)
        r1 = migrate(LOCAL_URL, "Local")
        r2 = migrate(RDS_URL, "RDS")
        r3 = migrate(dev_url, "DATABASE_URL_DEV")
        sys.exit(0 if r1 and r2 and r3 else 1)
    if args.both:
        r1 = migrate(LOCAL_URL, "Local")
        r2 = migrate(RDS_URL, "RDS")
        sys.exit(0 if r1 and r2 else 1)
    if args.dev:
        dev_url = _need_dev_url()
        _ensure_dev_db(dev_url)
        sys.exit(0 if migrate(dev_url, "DATABASE_URL_DEV") else 1)
    if args.local:
        sys.exit(0 if migrate(LOCAL_URL, "Local") else 1)
    if args.rds:
        sys.exit(0 if migrate(RDS_URL, "RDS") else 1)
    # Default: migrate whatever DATABASE_URL points to
    sys.exit(0 if migrate(RDS_URL, "DATABASE_URL target") else 1)
