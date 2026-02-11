"""
Scheduler Service - Runs automated collection on schedule
"""
import yaml
from pathlib import Path
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from backend.services.automated_collector import AutomatedCollector
from backend.services.report_generator import ReportGenerator


class SchedulerService:
    """Manages scheduled data collection and reporting"""
    
    def __init__(self, config_path="config/targets.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.scheduler = BlockingScheduler()
        self.collector = AutomatedCollector(config_path)
        self.reporter = ReportGenerator(config_path)
    
    def _load_config(self):
        """Load configuration"""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def daily_job(self):
        """Run daily collection and reporting"""
        print(f"\n{'='*80}")
        print(f"🕐 SCHEDULED JOB STARTED - {datetime.now()}")
        print(f"{'='*80}\n")
        
        try:
            # Run collection
            results = self.collector.run_daily_collection()
            
            # Generate reports
            if self.config['schedule']['generate_reports']:
                report = self.reporter.generate_daily_report()
                print(f"\n✅ Reports generated: {report['count']} cards")
            
            print(f"\n{'='*80}")
            print(f"✅ SCHEDULED JOB COMPLETED - {datetime.now()}")
            print(f"{'='*80}\n")
            
        except Exception as e:
            print(f"\n❌ ERROR in scheduled job: {e}")
            import traceback
            traceback.print_exc()
    
    def start(self):
        """Start the scheduler"""
        schedule_config = self.config['schedule']
        time_str = schedule_config['daily_import_time']
        hour, minute = map(int, time_str.split(':'))
        
        # Add daily job
        self.scheduler.add_job(
            self.daily_job,
            CronTrigger(hour=hour, minute=minute),
            id='daily_collection',
            name='Daily Card Collection',
            replace_existing=True
        )
        
        print(f"🚀 Scheduler started!")
        print(f"📅 Daily collection scheduled for {time_str}")
        print(f"⏰ Next run: {self.scheduler.get_jobs()[0].next_run_time}")
        print(f"\nPress Ctrl+C to stop\n")
        
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            print("\n\n👋 Scheduler stopped")
    
    def run_now(self):
        """Run job immediately (for testing)"""
        print("🧪 Running job immediately (test mode)\n")
        self.daily_job()


if __name__ == "__main__":
    import sys
    
    scheduler = SchedulerService()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        # Run immediately for testing
        scheduler.run_now()
    else:
        # Start scheduler
        scheduler.start()
