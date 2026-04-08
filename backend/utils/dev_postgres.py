"""Dev replica DB on the same Postgres instance as DATABASE_URL (e.g. RDS)."""
from __future__ import annotations

from urllib.parse import unquote, urlparse, urlunparse

DEFAULT_DEV_DATABASE = "trading_cards_dev"
_MAINTENANCE_DATABASES = ("postgres", "template1")


def database_name_from_pg_url(url: str) -> str:
    u = urlparse(url)
    part = (u.path or "").strip("/").split("/")[0]
    return part or "postgres"


def pg_username_from_url(url: str) -> str:
    u = urlparse(url)
    if "@" not in u.netloc:
        return ""
    auth, _ = u.netloc.rsplit("@", 1)
    return unquote(auth.split(":", 1)[0]) if auth else ""


def derive_dev_database_url(prod_url: str, dev_db: str = DEFAULT_DEV_DATABASE) -> str:
    """Same host/user/password/options as prod_url, database name ``dev_db``."""
    prod_url = (prod_url or "").strip()
    if not prod_url:
        return ""
    u = urlparse(prod_url)
    path = "/" + dev_db.strip("/")
    return urlunparse((u.scheme, u.netloc, path, u.params, u.query, u.fragment))


def admin_url_same_instance(pg_url: str, maintenance_db: str) -> str:
    u = urlparse(pg_url)
    path = "/" + maintenance_db.strip("/")
    return urlunparse((u.scheme, u.netloc, path, u.params, u.query, u.fragment))


def resolve_dev_database_url(
    *,
    explicit_dev: str | None,
    prod_url: str | None,
    default_dev_db: str = DEFAULT_DEV_DATABASE,
) -> tuple[str, str]:
    """
    Returns (url, source) where source is ``explicit`` or ``derived``.

    If DATABASE_URL_DEV is set, use it. Else derive from DATABASE_URL.
    """
    ex = (explicit_dev or "").strip()
    if ex:
        return ex, "explicit DATABASE_URL_DEV"
    prod = (prod_url or "").strip()
    if not prod:
        return "", ""
    return derive_dev_database_url(prod, default_dev_db), "derived from DATABASE_URL"


def ensure_dev_database_exists(
    dev_url: str,
    *,
    grant_to_username: str | None = None,
) -> tuple[bool, str]:
    """
    Connect to maintenance DB on the same instance; CREATE DATABASE if missing.

    ``grant_to_username``: if set, GRANT ALL PRIVILEGES ON DATABASE ... (needed when
    connecting as a superuser/master that is not the app role).
    """
    import psycopg2
    from psycopg2 import sql as psql

    dev_url = (dev_url or "").strip()
    if not dev_url:
        return False, "empty dev_url"
    dbname = database_name_from_pg_url(dev_url)
    if not dbname or dbname in _MAINTENANCE_DATABASES:
        return False, f"refusing to treat {dbname!r} as dev database name"

    last_err: str | None = None
    for maint in _MAINTENANCE_DATABASES:
        admin = admin_url_same_instance(dev_url, maint)
        try:
            conn = psycopg2.connect(admin)
        except Exception as e:
            last_err = str(e)
            continue
        try:
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
            if cur.fetchone():
                return True, f"database {dbname!r} already exists"
            cur.execute("SELECT current_user")
            (creator,) = cur.fetchone()
            cur.execute(psql.SQL("CREATE DATABASE {}").format(psql.Identifier(dbname)))
            if grant_to_username and grant_to_username != creator:
                cur.execute(
                    psql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
                        psql.Identifier(dbname),
                        psql.Identifier(grant_to_username),
                    )
                )
            return True, f"created database {dbname!r}"
        except Exception as e:
            last_err = str(e)
            return False, last_err
        finally:
            conn.close()

    return False, last_err or "could not connect to postgres/template1 on this instance"
