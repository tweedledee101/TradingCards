"""
Run Scheduler - Start automated data collection

Usage:
    # Start scheduler (runs at configured time)
    python -m backend.run_scheduler
    
    # Run immediately (for testing)
    python -m backend.run_scheduler --now
"""
from backend.services.scheduler import SchedulerService

if __name__ == "__main__":
    import sys
    
    scheduler = SchedulerService()
    
    if "--now" in sys.argv:
        scheduler.run_now()
    else:
        scheduler.start()
