"""Unit tests for backend.utils.dev_postgres (URL helpers)."""
from __future__ import annotations

import pytest

from backend.utils.dev_postgres import (
    database_name_from_pg_url,
    derive_dev_database_url,
    pg_username_from_url,
    resolve_dev_database_url,
)


@pytest.mark.parametrize(
    "url,expected",
    [
        ("postgresql://h/t", "t"),
        ("postgresql://h/", "postgres"),
        ("postgresql://u:p@host:5432/trading_cards", "trading_cards"),
        ("postgresql://u:p@host:5432/trading_cards?sslmode=require", "trading_cards"),
    ],
)
def test_database_name_from_pg_url(url: str, expected: str) -> None:
    assert database_name_from_pg_url(url) == expected


def test_derive_dev_database_url_preserves_host_and_query() -> None:
    u = "postgresql://app:secret@rds.example:5432/trading_cards?sslmode=require"
    d = derive_dev_database_url(u)
    assert d == "postgresql://app:secret@rds.example:5432/trading_cards_dev?sslmode=require"


def test_pg_username_from_url() -> None:
    assert pg_username_from_url("postgresql://myuser:pass@host/db") == "myuser"
    assert pg_username_from_url("postgresql://host/db") == ""


def test_resolve_explicit_over_derived() -> None:
    url, src = resolve_dev_database_url(
        explicit_dev="postgresql://x/y_dev",
        prod_url="postgresql://a/b",
        default_dev_db="trading_cards_dev",
    )
    assert url == "postgresql://x/y_dev"
    assert "explicit" in src


def test_resolve_derived() -> None:
    url, src = resolve_dev_database_url(
        explicit_dev="",
        prod_url="postgresql://u:p@h:5432/trading_cards",
        default_dev_db="trading_cards_dev",
    )
    assert url.endswith("/trading_cards_dev")
    assert "derived" in src
