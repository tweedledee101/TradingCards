"""
Job Tracker - Runtime state management for background jobs

Every script that runs a background task (pipeline, SCP collection,
opportunity finder, etc.) uses this to record its state. The API
exposes this via /api/status so the UI and other tools can check
what's running without asking anyone.

Designed to migrate to AWS:
- Local: PostgreSQL job_runs table
- AWS: Same table in RDS, or DynamoDB, or Step Functions state

Usage:
    from backend.utils.job_tracker import JobTracker

    tracker = JobTracker('scp_catalog')
    tracker.start(total=40, parameters={'players': 40, 'sport': 'Baseball'})

    for i, player in enumerate(players):
        # do work
        tracker.update(processed=i+1)

    tracker.complete(summary={'variations_found': 312, 'players': 40})

    # Or on failure:
    tracker.fail('Connection timeout after 30s')
"""
import json
from datetime import datetime
from backend.utils.database import SessionLocal
from backend.models import JobRun


class JobTracker:
    def __init__(self, job_name: str):
        self.job_name = job_name
        self.run_id = None
        self.db = None

    def start(self, total: int = None, parameters: dict = None):
        """Record job start"""
        self.db = SessionLocal()
        run = JobRun(
            job_name=self.job_name,
            status='running',
            started_at=datetime.now(),
            items_total=total,
            parameters=json.dumps(parameters) if parameters else None
        )
        self.db.add(run)
        self.db.commit()
        self.run_id = run.id
        return self

    def update(self, processed: int, total: int = None):
        """Update progress. Optionally reset total for multi-step jobs."""
        if not self.run_id or not self.db:
            return
        run = self.db.query(JobRun).get(self.run_id)
        if run:
            run.items_processed = processed
            if total is not None:
                run.items_total = total
            self.db.commit()

    def complete(self, summary: dict = None):
        """Mark job as completed"""
        if not self.run_id or not self.db:
            return
        run = self.db.query(JobRun).get(self.run_id)
        if run:
            run.status = 'completed'
            run.completed_at = datetime.now()
            run.results_summary = json.dumps(summary) if summary else None
            self.db.commit()
        self._close()

    def fail(self, error: str):
        """Mark job as failed"""
        if not self.run_id or not self.db:
            return
        run = self.db.query(JobRun).get(self.run_id)
        if run:
            run.status = 'failed'
            run.completed_at = datetime.now()
            run.error_message = error
            self.db.commit()
        self._close()

    def _close(self):
        if self.db:
            self.db.close()
            self.db = None

    @staticmethod
    def get_status(job_name: str = None):
        """Get latest run status for each job (or one specific job)"""
        db = SessionLocal()
        try:
            if job_name:
                run = db.query(JobRun).filter(
                    JobRun.job_name == job_name
                ).order_by(JobRun.started_at.desc()).first()
                return _run_to_dict(run) if run else None
            else:
                # Latest run per job name
                from sqlalchemy import func as sqlfunc
                subq = db.query(
                    JobRun.job_name,
                    sqlfunc.max(JobRun.id).label('max_id')
                ).group_by(JobRun.job_name).subquery()

                runs = db.query(JobRun).join(
                    subq, JobRun.id == subq.c.max_id
                ).all()

                return {r.job_name: _run_to_dict(r) for r in runs}
        finally:
            db.close()

    @staticmethod
    def is_running(job_name: str) -> bool:
        """Check if a specific job is currently running"""
        db = SessionLocal()
        try:
            run = db.query(JobRun).filter(
                JobRun.job_name == job_name,
                JobRun.status == 'running'
            ).first()
            return run is not None
        finally:
            db.close()


def _run_to_dict(run):
    """Convert JobRun to dict"""
    return {
        'id': run.id,
        'job_name': run.job_name,
        'status': run.status,
        'started_at': run.started_at.isoformat() if run.started_at else None,
        'completed_at': run.completed_at.isoformat() if run.completed_at else None,
        'items_processed': run.items_processed,
        'items_total': run.items_total,
        'error_message': run.error_message,
        'parameters': json.loads(run.parameters) if run.parameters else None,
        'results_summary': json.loads(run.results_summary) if run.results_summary else None
    }
