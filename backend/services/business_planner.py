"""
Business Operating System (ADR-006)

Connects goals, capital, inventory, and opportunities into daily actionable plans.
Answers: Where am I? Where should I be? What do I do today?
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from backend.models import (
    BusinessGoal, DailySnapshot, DailyPlan, CapitalTransaction,
    Opportunity, Inventory, InventorySale
)

ZERO = Decimal('0')


class BusinessPlanner:

    def get_active_goal(self, db: Session, account_id: int = 1) -> Optional[BusinessGoal]:
        return db.query(BusinessGoal).filter(
            BusinessGoal.account_id == account_id
        ).order_by(BusinessGoal.created_at.desc()).first()

    # ── Goal Decomposition ──────────────────────────────────────────

    def compute_trajectory(self, goal: BusinessGoal) -> List[Dict]:
        """
        Month-by-month compounding projection from starting capital.
        Assumes full reinvestment, ~5 inventory turns/month (weekly turnover).
        Returns 12 monthly projections.
        """
        capital = float(goal.starting_capital)
        margin = float(goal.target_margin_pct)
        fee_rate = float(goal.platform_fee_pct)
        net_margin = margin - fee_rate  # e.g. 25% margin - 13% fees = 12% net
        turns_per_month = 2.0  # ~biweekly turnover (conservative for part-time)

        months = []
        cumulative_profit = 0.0

        for m in range(1, 13):
            monthly_revenue = capital * turns_per_month
            monthly_profit = monthly_revenue * net_margin
            cumulative_profit += monthly_profit
            capital += monthly_profit * float(goal.reinvest_pct)

            months.append({
                "month": m,
                "capital": round(capital, 2),
                "monthly_profit": round(monthly_profit, 2),
                "cumulative_profit": round(cumulative_profit, 2),
                "monthly_revenue": round(monthly_revenue, 2),
            })

        return months

    def get_daily_target(self, goal: BusinessGoal, snapshot: Optional[DailySnapshot]) -> Dict:
        """
        What you need to earn TODAY to stay on the compounding curve.
        """
        today = date.today()
        start = goal.goal_start_date
        days_elapsed = max((today - start).days, 0)
        days_remaining = max(365 - days_elapsed, 1)

        # Year 1 realistic target from trajectory
        trajectory = self.compute_trajectory(goal)
        year1_target = trajectory[-1]["cumulative_profit"] if trajectory else 0

        profit_ytd = float(snapshot.profit_ytd) if snapshot else 0.0
        profit_remaining = max(year1_target - profit_ytd, 0)

        # What's achievable today given current capital
        capital = float(snapshot.available_capital) if snapshot else float(goal.starting_capital)
        net_margin = float(goal.target_margin_pct) - float(goal.platform_fee_pct)
        max_daily_from_capital = capital * net_margin

        linear_daily = profit_remaining / days_remaining
        achievable = min(linear_daily, max_daily_from_capital)

        return {
            "year1_target": round(year1_target, 2),
            "daily_target": round(achievable, 2),
            "linear_daily": round(linear_daily, 2),
            "capital_limited_daily": round(max_daily_from_capital, 2),
            "days_elapsed": days_elapsed,
            "days_remaining": days_remaining,
            "profit_ytd": round(profit_ytd, 2),
            "profit_remaining": round(profit_remaining, 2),
        }

    # ── Capital Tracking ────────────────────────────────────────────

    def get_available_capital(self, db: Session, goal: BusinessGoal, account_id: int = 1) -> float:
        """Current available capital = starting + all transactions."""
        total = db.query(sqlfunc.sum(CapitalTransaction.amount)).filter(
            CapitalTransaction.account_id == account_id
        ).scalar()
        return float(goal.starting_capital) + (float(total) if total else 0.0)

    def record_transaction(self, db: Session, amount: float, txn_type: str,
                           description: str = None, opportunity_id: int = None,
                           inventory_id: int = None, account_id: int = 1) -> CapitalTransaction:
        txn = CapitalTransaction(
            account_id=account_id,
            transaction_date=date.today(),
            amount=Decimal(str(amount)),
            type=txn_type,
            description=description,
            opportunity_id=opportunity_id,
            inventory_id=inventory_id,
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)
        return txn

    def get_capital_history(self, db: Session, goal: BusinessGoal, days: int = 30, account_id: int = 1) -> List[Dict]:
        cutoff = date.today() - timedelta(days=days)
        rows = db.query(
            CapitalTransaction.transaction_date,
            sqlfunc.sum(CapitalTransaction.amount).label('net_change'),
        ).filter(
            CapitalTransaction.account_id == account_id,
            CapitalTransaction.transaction_date >= cutoff
        ).group_by(CapitalTransaction.transaction_date).order_by(
            CapitalTransaction.transaction_date
        ).all()

        running = float(goal.starting_capital)
        # Add all transactions before cutoff
        pre_total = db.query(sqlfunc.sum(CapitalTransaction.amount)).filter(
            CapitalTransaction.account_id == account_id,
            CapitalTransaction.transaction_date < cutoff
        ).scalar()
        if pre_total:
            running += float(pre_total)

        history = []
        for row in rows:
            running += float(row.net_change)
            history.append({
                "date": row.transaction_date.isoformat(),
                "capital": round(running, 2),
                "net_change": round(float(row.net_change), 2),
            })
        return history

    # ── Snapshot ────────────────────────────────────────────────────

    def generate_snapshot(self, db: Session, goal: BusinessGoal, account_id: int = 1) -> DailySnapshot:
        """Auto-generate today's snapshot from current DB state."""
        today = date.today()
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)

        capital = self.get_available_capital(db, goal, account_id=account_id)

        # Inventory stats
        inv_count = db.query(sqlfunc.count(Inventory.id)).filter(
            Inventory.account_id == account_id,
            Inventory.status == 'owned'
        ).scalar() or 0
        inv_cost = db.query(sqlfunc.sum(Inventory.purchase_price)).filter(
            Inventory.account_id == account_id,
            Inventory.status == 'owned'
        ).scalar() or ZERO
        listed = db.query(sqlfunc.count(Inventory.id)).filter(
            Inventory.account_id == account_id,
            Inventory.status == 'listed'
        ).scalar() or 0

        # Today's sales
        today_sales = db.query(
            sqlfunc.count(InventorySale.id),
            sqlfunc.coalesce(sqlfunc.sum(InventorySale.sale_price), ZERO),
            sqlfunc.coalesce(sqlfunc.sum(InventorySale.net_profit), ZERO),
        ).filter(
            InventorySale.account_id == account_id,
            InventorySale.sale_date == today
        ).first()

        # MTD
        mtd_sales = db.query(
            sqlfunc.coalesce(sqlfunc.sum(InventorySale.sale_price), ZERO),
            sqlfunc.coalesce(sqlfunc.sum(InventorySale.net_profit), ZERO),
        ).filter(
            InventorySale.account_id == account_id,
            InventorySale.sale_date >= month_start
        ).first()

        # YTD
        ytd_sales = db.query(
            sqlfunc.coalesce(sqlfunc.sum(InventorySale.sale_price), ZERO),
            sqlfunc.coalesce(sqlfunc.sum(InventorySale.net_profit), ZERO),
        ).filter(
            InventorySale.account_id == account_id,
            InventorySale.sale_date >= year_start
        ).first()

        # Today's buys
        today_buys = db.query(sqlfunc.count(CapitalTransaction.id)).filter(
            CapitalTransaction.account_id == account_id,
            CapitalTransaction.transaction_date == today,
            CapitalTransaction.type == 'purchase',
        ).scalar() or 0

        snap = DailySnapshot(
            account_id=account_id,
            snapshot_date=today,
            available_capital=Decimal(str(round(capital, 2))),
            inventory_count=inv_count,
            inventory_cost_basis=inv_cost,
            listed_count=listed,
            unlisted_count=max(inv_count - listed, 0),
            revenue_today=today_sales[1],
            profit_today=today_sales[2],
            revenue_mtd=mtd_sales[0],
            profit_mtd=mtd_sales[1],
            revenue_ytd=ytd_sales[0],
            profit_ytd=ytd_sales[1],
            cards_bought_today=today_buys,
            cards_sold_today=today_sales[0],
        )

        # Upsert
        existing = db.query(DailySnapshot).filter(
            DailySnapshot.account_id == account_id,
            DailySnapshot.snapshot_date == today
        ).first()
        if existing:
            for col in ['available_capital', 'inventory_count', 'inventory_cost_basis',
                        'listed_count', 'unlisted_count', 'revenue_today', 'profit_today',
                        'revenue_mtd', 'profit_mtd', 'revenue_ytd', 'profit_ytd',
                        'cards_bought_today', 'cards_sold_today']:
                setattr(existing, col, getattr(snap, col))
            db.commit()
            db.refresh(existing)
            return existing

        db.add(snap)
        db.commit()
        db.refresh(snap)
        return snap

    # ── Daily Plan Generator ────────────────────────────────────────

    def generate_plan(self, db: Session, goal: BusinessGoal,
                      account_id: int = 1, available_hours: float = None) -> Dict:
        """
        Generate today's action plan given available time and capital.
        """
        today = date.today()
        is_weekday = today.weekday() < 5

        if available_hours is None:
            weekly = float(goal.weekly_hours_weekday if is_weekday else goal.weekly_hours_weekend)
            days = 5 if is_weekday else 2
            available_hours = weekly / days

        snapshot = self.generate_snapshot(db, goal, account_id=account_id)
        targets = self.get_daily_target(goal, snapshot)
        capital = float(snapshot.available_capital)
        remaining_min = available_hours * 60
        actions = []

        # 1. Buy opportunities (highest ROI first, within capital)
        if capital > 20:
            opps = db.query(Opportunity).filter(
                Opportunity.buy_price <= Decimal(str(capital)),
                Opportunity.profit > 0,
                Opportunity.listing_type.in_(['buy_it_now', None]),
            ).order_by(Opportunity.roi.desc()).limit(10).all()

            buy_batch = []
            buy_cost = 0.0
            for opp in opps:
                cost = float(opp.buy_price)
                if remaining_min < 8 or (buy_cost + cost) > capital:
                    break
                buy_batch.append({
                    "opportunity_id": opp.id,
                    "player": opp.player_name,
                    "card": f"{opp.card_year} {opp.card_set} #{opp.card_number}",
                    "parallel": opp.parallel,
                    "cost": cost,
                    "est_profit": float(opp.profit),
                    "roi": float(opp.roi),
                    "ebay_url": opp.ebay_url,
                })
                buy_cost += cost
                remaining_min -= 8

            if buy_batch:
                actions.append({
                    "priority": 1,
                    "type": "buy",
                    "description": f"Buy {len(buy_batch)} opportunities (${round(buy_cost, 2)} capital)",
                    "est_time_min": len(buy_batch) * 8,
                    "est_profit": round(sum(b["est_profit"] for b in buy_batch), 2),
                    "est_cost": round(buy_cost, 2),
                    "items": buy_batch,
                })

        # 2. List unlisted inventory (highest margin first)
        unlisted = db.query(Inventory).filter(
            Inventory.account_id == account_id,
            Inventory.status == 'owned'
        ).order_by(Inventory.purchase_price.desc()).limit(10).all()

        if unlisted and remaining_min >= 12:
            list_batch = []
            for card in unlisted:
                if remaining_min < 12:
                    break
                list_batch.append({
                    "inventory_id": card.id,
                    "purchase_price": float(card.purchase_price),
                    "est_time_min": 12,
                })
                remaining_min -= 12

            if list_batch:
                actions.append({
                    "priority": 2,
                    "type": "list",
                    "description": f"List {len(list_batch)} unlisted cards",
                    "est_time_min": len(list_batch) * 12,
                    "items": list_batch,
                })

        # 3. Reprice stale listings (>14 days)
        stale_count = db.query(sqlfunc.count(Inventory.id)).filter(
            Inventory.account_id == account_id,
            Inventory.status == 'listed',
        ).scalar() or 0
        # Rough heuristic: assume 20% of listed cards are stale
        est_stale = max(int(stale_count * 0.2), 0)
        if est_stale > 0 and remaining_min >= 10:
            batch_size = min(est_stale, int(remaining_min / 3))
            actions.append({
                "priority": 3,
                "type": "reprice",
                "description": f"Check and reprice ~{batch_size} stale listings",
                "est_time_min": batch_size * 3,
                "items": [],
            })
            remaining_min -= batch_size * 3

        # 4. Research time (remaining minutes)
        if remaining_min >= 10:
            actions.append({
                "priority": 4,
                "type": "research",
                "description": f"Review new opportunities and market moves ({int(remaining_min)} min)",
                "est_time_min": int(remaining_min),
                "items": [],
            })

        # Catchup logic
        catchup = self._calculate_catchup(db, goal, snapshot, account_id=account_id)

        plan_data = {
            "plan_date": today.isoformat(),
            "available_hours": available_hours,
            "target_profit": targets["daily_target"],
            "year1_target": targets["year1_target"],
            "capital": round(capital, 2),
            "catchup_amount": catchup,
            "actions": actions,
            "snapshot": {
                "profit_today": float(snapshot.profit_today or 0),
                "profit_mtd": float(snapshot.profit_mtd or 0),
                "profit_ytd": float(snapshot.profit_ytd or 0),
                "revenue_today": float(snapshot.revenue_today or 0),
                "inventory_count": snapshot.inventory_count,
                "listed_count": snapshot.listed_count,
                "unlisted_count": snapshot.unlisted_count,
            },
            "trajectory": targets,
        }

        # Store plan
        existing = db.query(DailyPlan).filter(
            DailyPlan.account_id == account_id,
            DailyPlan.plan_date == today
        ).first()
        if existing:
            existing.available_hours = Decimal(str(available_hours))
            existing.target_profit = Decimal(str(targets["daily_target"]))
            existing.buy_budget = Decimal(str(capital))
            existing.actions = actions
            db.commit()
        else:
            plan = DailyPlan(
                account_id=account_id,
                plan_date=today,
                available_hours=Decimal(str(available_hours)),
                target_profit=Decimal(str(targets["daily_target"])),
                buy_budget=Decimal(str(capital)),
                actions=actions,
            )
            db.add(plan)
            db.commit()

        return plan_data

    def _calculate_catchup(self, db: Session, goal: BusinessGoal,
                           snapshot: DailySnapshot, account_id: int = 1) -> float:
        """Spread any weekly deficit over the next 7 days."""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        # Sum profit this week from snapshots
        week_profit = db.query(
            sqlfunc.coalesce(sqlfunc.sum(DailySnapshot.profit_today), ZERO)
        ).filter(
            DailySnapshot.account_id == account_id,
            DailySnapshot.snapshot_date >= week_start,
            DailySnapshot.snapshot_date <= today,
        ).scalar()

        targets = self.get_daily_target(goal, snapshot)
        days_so_far = (today - week_start).days + 1
        expected = targets["daily_target"] * days_so_far
        deficit = expected - float(week_profit or 0)

        if deficit <= 0:
            return 0.0

        days_left = max(7 - days_so_far, 1)
        return round(deficit / days_left, 2)

    # ── Dashboard ───────────────────────────────────────────────────

    def get_dashboard(self, db: Session, account_id: int = 1) -> Dict:
        """Full dashboard payload for the frontend."""
        goal = self.get_active_goal(db, account_id=account_id)
        if not goal:
            return {"has_goal": False, "message": "Set your business goal to get started."}

        snapshot = self.generate_snapshot(db, goal, account_id=account_id)
        targets = self.get_daily_target(goal, snapshot)
        trajectory = self.compute_trajectory(goal)
        capital = float(snapshot.available_capital)
        catchup = self._calculate_catchup(db, goal, snapshot, account_id=account_id)

        # Week stats
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_profit = db.query(
            sqlfunc.coalesce(sqlfunc.sum(DailySnapshot.profit_today), ZERO)
        ).filter(
            DailySnapshot.account_id == account_id,
            DailySnapshot.snapshot_date >= week_start,
        ).scalar()

        week_target = targets["daily_target"] * 7

        # Status
        ytd_pct = (targets["profit_ytd"] / targets["year1_target"] * 100) if targets["year1_target"] > 0 else 0

        return {
            "has_goal": True,
            "today": {
                "date": today.isoformat(),
                "available_capital": round(capital, 2),
                "daily_target_profit": targets["daily_target"],
                "profit_so_far": float(snapshot.profit_today or 0),
                "catchup_amount": catchup,
            },
            "week": {
                "target_profit": round(week_target, 2),
                "actual_profit": round(float(week_profit or 0), 2),
                "pct_complete": round(float(week_profit or 0) / week_target * 100, 1) if week_target > 0 else 0,
                "days_remaining": 7 - (today.weekday() + 1),
            },
            "month": {
                "target_profit": round(targets["daily_target"] * 30, 2),
                "actual_profit": float(snapshot.profit_mtd or 0),
            },
            "year": {
                "target_profit": targets["year1_target"],
                "actual_profit": targets["profit_ytd"],
                "pct_complete": round(ytd_pct, 1),
                "projected_annual": trajectory[-1]["cumulative_profit"] if trajectory else 0,
                "on_track": ytd_pct >= (targets["days_elapsed"] / 365 * 100) - 5,
            },
            "inventory": {
                "total_cards": snapshot.inventory_count,
                "listed": snapshot.listed_count,
                "unlisted": snapshot.unlisted_count,
                "cost_basis": float(snapshot.inventory_cost_basis or 0),
            },
            "trajectory": trajectory,
        }
