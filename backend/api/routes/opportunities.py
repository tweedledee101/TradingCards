"""
Opportunities endpoints - Complete 3-phase opportunity finder
"""
from fastapi import APIRouter, Query
from typing import Optional
from backend.services.complete_opportunity_finder import CompleteOpportunityFinder
from backend.services.opportunity_analyzer import OpportunityAnalyzer
from backend.utils.database import SessionLocal

router = APIRouter()
finder = CompleteOpportunityFinder()
analyzer = OpportunityAnalyzer()


@router.get("/opportunities")
def get_opportunities(
    min_budget: Optional[float] = Query(default=None, description="Minimum card price"),
    max_budget: Optional[float] = Query(default=None, description="Maximum card price"),
    days: int = Query(default=90, description="Lookback period in days"),
    run_fresh: bool = Query(default=False, description="Run fresh eBay scrape (uses API calls)")
):
    """
    Complete 3-phase opportunity finder:
    - Phase 1: Discover top 20 players by volume (eBay scrape)
    - Phase 2: Filter cards within budget
    - Phase 3: Rank by profit potential
    
    Set run_fresh=true to scrape eBay (uses ~23 API calls)
    Set run_fresh=false to use existing database data (0 API calls)
    """
    try:
        if run_fresh:
            # Run complete analysis with eBay scraping
            results = finder.run_complete_analysis(
                min_budget=min_budget,
                max_budget=max_budget,
                days=days
            )
            return {
                "success": True,
                "data_source": "fresh_ebay_scrape",
                "api_calls_used": results['api_calls_used'],
                "top_20_players": results['top_20_players'],
                "opportunities": results['opportunities'],
                "count": len(results['opportunities'])
            }
        else:
            # Use existing database data (legacy endpoint)
            db = SessionLocal()
            try:
                opps = analyzer.find_opportunities(
                    db=db,
                    min_budget=min_budget,
                    max_budget=max_budget,
                    limit=100
                )
                return {
                    "success": True,
                    "data_source": "database_cache",
                    "api_calls_used": 0,
                    "opportunities": opps,
                    "count": len(opps)
                }
            finally:
                db.close()
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "opportunities": [],
            "count": 0
        }


@router.get("/opportunities/{card_id}")
def get_card_opportunity(card_id: int):
    """
    Get detailed opportunity analysis for a specific card
    """
    db = SessionLocal()
    try:
        opportunity = analyzer.analyze_card(db, card_id)
        
        if not opportunity:
            return {
                "card_id": card_id,
                "has_opportunity": False,
                "reason": "Not enough sales data or no profitable arbitrage"
            }
        
        return {
            "has_opportunity": True,
            "opportunity": opportunity
        }
    finally:
        db.close()


@router.get("/opportunities-stats")
def get_opportunity_stats():
    """
    Get overall market opportunity statistics
    """
    db = SessionLocal()
    try:
        all_opps = analyzer.find_opportunities(db, limit=100)
        
        if not all_opps:
            return {
                "total_opportunities": 0,
                "avg_roi": 0,
                "avg_profit": 0,
                "high_confidence_count": 0,
                "best_opportunity": None
            }
        
        total = len(all_opps)
        avg_roi = sum(o['arbitrage']['roi'] for o in all_opps) / total
        avg_profit = sum(o['arbitrage']['net_profit'] for o in all_opps) / total
        high_confidence = len([o for o in all_opps if 'VERY HIGH' in o['confidence'] or 'HIGH' in o['confidence']])
        
        return {
            "total_opportunities": total,
            "avg_roi": round(avg_roi, 1),
            "avg_profit": round(avg_profit, 2),
            "high_confidence_count": high_confidence,
            "best_opportunity": all_opps[0] if all_opps else None
        }
    except Exception as e:
        return {
            "total_opportunities": 0,
            "avg_roi": 0,
            "avg_profit": 0,
            "high_confidence_count": 0,
            "best_opportunity": None,
            "error": str(e)
        }
    finally:
        db.close()
