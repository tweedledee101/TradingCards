"""
Business Operating System API endpoints (ADR-006)
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
from decimal import Decimal

from backend.utils.database import get_db
from backend.models import BusinessGoal, CapitalTransaction, DailySnapshot
from backend.services.business_planner import BusinessPlanner

router = APIRouter()
planner = BusinessPlanner()


class GoalCreate(BaseModel):
    annual_income_target: float
    starting_capital: float
    weekly_hours_weekday: float = 12.5
    weekly_hours_weekend: float = 8.0
    target_margin_pct: float = 0.25
    platform_fee_pct: float = 0.13
    reinvest_pct: float = 1.0
    goal_start_date: str  # YYYY-MM-DD


class CapitalTransactionCreate(BaseModel):
    amount: float
    type: str  # deposit, withdrawal, purchase, sale
    description: Optional[str] = None
    opportunity_id: Optional[int] = None
    inventory_id: Optional[int] = None


@router.get("/business/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    """Full dashboard: snapshot + targets + trajectory + inventory."""
    return planner.get_dashboard(db)


@router.get("/business/trajectory")
def get_trajectory(db: Session = Depends(get_db)):
    """12-month compounding projection."""
    goal = planner.get_active_goal(db)
    if not goal:
        return {"error": "No goal set"}
    return {"trajectory": planner.compute_trajectory(goal)}


@router.get("/business/plan/today")
def get_todays_plan(
    hours: Optional[float] = Query(default=None, description="Override available hours"),
    db: Session = Depends(get_db)
):
    """Generate today's prioritized action plan."""
    goal = planner.get_active_goal(db)
    if not goal:
        return {"error": "No goal set"}
    return planner.generate_plan(db, goal, available_hours=hours)


@router.post("/business/goals")
def set_goal(data: GoalCreate, db: Session = Depends(get_db)):
    """Create or update business goal."""
    goal = BusinessGoal(
        annual_income_target=Decimal(str(data.annual_income_target)),
        starting_capital=Decimal(str(data.starting_capital)),
        weekly_hours_weekday=Decimal(str(data.weekly_hours_weekday)),
        weekly_hours_weekend=Decimal(str(data.weekly_hours_weekend)),
        target_margin_pct=Decimal(str(data.target_margin_pct)),
        platform_fee_pct=Decimal(str(data.platform_fee_pct)),
        reinvest_pct=Decimal(str(data.reinvest_pct)),
        goal_start_date=date.fromisoformat(data.goal_start_date),
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)

    trajectory = planner.compute_trajectory(goal)
    return {
        "id": goal.id,
        "year1_projected_profit": trajectory[-1]["cumulative_profit"],
        "trajectory": trajectory,
        "message": f"Goal set. Year 1 realistic target: ${trajectory[-1]['cumulative_profit']:,.2f}",
    }


@router.post("/business/capital")
def record_capital(data: CapitalTransactionCreate, db: Session = Depends(get_db)):
    """Record a capital transaction (deposit, withdrawal, purchase, sale)."""
    if data.type not in ('deposit', 'withdrawal', 'purchase', 'sale'):
        return {"error": "type must be: deposit, withdrawal, purchase, sale"}

    # Purchases and withdrawals are negative
    amount = abs(data.amount)
    if data.type in ('purchase', 'withdrawal'):
        amount = -amount

    txn = planner.record_transaction(
        db, amount, data.type, data.description,
        data.opportunity_id, data.inventory_id,
    )

    goal = planner.get_active_goal(db)
    capital = planner.get_available_capital(db, goal) if goal else 0

    return {
        "id": txn.id,
        "type": data.type,
        "amount": float(txn.amount),
        "available_capital": round(capital, 2),
    }


@router.get("/business/history")
def get_history(
    days: int = Query(default=30),
    db: Session = Depends(get_db)
):
    """Daily snapshots over time for charts."""
    goal = planner.get_active_goal(db)
    if not goal:
        return {"error": "No goal set"}

    capital_history = planner.get_capital_history(db, goal, days)

    from datetime import timedelta
    cutoff = date.today() - timedelta(days=days)
    snapshots = db.query(DailySnapshot).filter(
        DailySnapshot.snapshot_date >= cutoff
    ).order_by(DailySnapshot.snapshot_date).all()

    return {
        "capital_history": capital_history,
        "snapshots": [{
            "date": s.snapshot_date.isoformat(),
            "profit_today": float(s.profit_today or 0),
            "profit_mtd": float(s.profit_mtd or 0),
            "profit_ytd": float(s.profit_ytd or 0),
            "revenue_today": float(s.revenue_today or 0),
            "inventory_count": s.inventory_count,
            "available_capital": float(s.available_capital or 0),
        } for s in snapshots],
    }
