"""Auction Browse query packs for find_auction_opportunities."""
import pytest

from backend.config.auction_queries import (
    BASEBALL_VALUE_QUERIES_CORE,
    build_baseball_value_queries,
    baseball_product_line_queries,
)


@pytest.mark.unit
def test_product_line_queries_use_years():
    qs = baseball_product_line_queries([2024, 2025])
    assert any('2025 Topps Chrome baseball' in q for q in qs)
    assert any('2024 Bowman Chrome baseball' in q for q in qs)


@pytest.mark.unit
def test_build_baseball_value_queries_includes_product_lines():
    qs, meta = build_baseball_value_queries([2023, 2024, 2025], product_line_year_cap=2)
    assert meta['product_lines'] is True
    assert meta['product_line_years_used'] == [2024, 2025]
    assert len(qs) > len(BASEBALL_VALUE_QUERIES_CORE)
    assert '2025 Topps Chrome baseball' in qs


@pytest.mark.unit
def test_build_baseball_value_queries_can_disable_product_lines():
    qs, meta = build_baseball_value_queries([2025], include_product_lines=False)
    assert meta['product_lines'] is False
    assert qs == BASEBALL_VALUE_QUERIES_CORE
