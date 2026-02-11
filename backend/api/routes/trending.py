"""
Trending cards endpoints
"""
from fastapi import APIRouter, Query
from typing import List
from backend.services.data_pipeline import DataPipeline

router = APIRouter()
pipeline = DataPipeline()

@router.get("/trending")
def get_trending_cards(
    limit: int = Query(default=10, ge=1, le=100, description="Number of cards to return")
):
    """
    Get top trending cards by hotness score
    
    Returns cards sorted by hotness score (highest first)
    """
    trending = pipeline.get_trending_cards(limit=limit)
    return {
        "count": len(trending),
        "cards": trending
    }

@router.get("/trending/rookies")
def get_trending_rookies(
    limit: int = Query(default=10, ge=1, le=100, description="Number of cards to return")
):
    """
    Get top trending rookie cards only
    """
    all_trending = pipeline.get_trending_cards(limit=100)
    rookies = [card for card in all_trending if card.get('is_rookie')][:limit]
    return {
        "count": len(rookies),
        "cards": rookies
    }
