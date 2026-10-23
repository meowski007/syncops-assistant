"""
Optional background scheduler for SyncOps ETL Pipeline.
Uses APScheduler to trigger periodic ETL ingestion.
NOTE: Scheduling is completely optional and is NOT started automatically on API boot.
"""

import time
from apscheduler.schedulers.background import BackgroundScheduler
from pipeline.run import run_pipeline
from app.logging_config import logger

def schedule_etl_job(interval_minutes: int = 60, source: str | None = None) -> BackgroundScheduler:
    """
    Initializes a background scheduler to run the ETL pipeline periodically.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=run_pipeline,
        trigger="interval",
        minutes=interval_minutes,
        kwargs={"source": source},
        id="syncops_etl_periodic_job",
        name="SyncOps Periodic Ingestion Pipeline",
        replace_existing=True
    )
    scheduler.start()
    logger.info(f"Optional ETL scheduler started with {interval_minutes}m interval.")
    return scheduler

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run SyncOps ETL Pipeline on a periodic schedule.")
    parser.add_argument("--interval", type=int, default=60, help="Interval in minutes between runs")
    parser.add_argument("--source", type=str, default=None, help="Input source")
    args = parser.parse_args()

    print(f"Starting optional ETL background scheduler every {args.interval} minutes. Press Ctrl+C to stop.")
    sched = schedule_etl_job(interval_minutes=args.interval, source=args.source)
    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        sched.shutdown()
        print("Scheduler stopped.")
