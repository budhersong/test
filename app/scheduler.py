import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler(timezone="Asia/Seoul")


def run_crawl_job():
    """스케줄러가 실행하는 크롤링 작업"""
    from app.database import SessionLocal
    from app.crawl_service import run_full_crawl

    db = SessionLocal()
    try:
        logger.info("정기 크롤링 시작: %s", datetime.now())
        run_full_crawl(db)
    finally:
        db.close()


def start_scheduler(day_of_week: str = "mon", hour: int = 9, minute: int = 0):
    trigger = CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute, timezone="Asia/Seoul")
    scheduler.add_job(run_crawl_job, trigger, id="weekly_crawl", replace_existing=True)
    scheduler.start()
    logger.info("스케줄러 시작 (매주 %s %02d:%02d KST)", day_of_week, hour, minute)


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
