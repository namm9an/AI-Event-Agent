"""Background scheduler for scrape and report jobs."""

from __future__ import annotations

import threading
from datetime import datetime
from zoneinfo import ZoneInfo

from config import APP_TIMEZONE, logger
from db.database import SessionLocal
from services.settings_service import get_schedule_settings

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
except Exception:  # pragma: no cover
    BackgroundScheduler = None
    CronTrigger = None


class AppScheduler:
    def __init__(self):
        self.scheduler = None
        self.lock = threading.Lock()
        self.initialized = False

    def start(self, run_scrape_fn, run_report_fn) -> None:
        if BackgroundScheduler is None:
            logger.warning("APScheduler not installed; scheduled jobs disabled")
            return

        with self.lock:
            if self.initialized:
                return

            db = SessionLocal()
            try:
                settings = get_schedule_settings(db)
            finally:
                db.close()

            tz = settings.get("timezone", APP_TIMEZONE)
            self.scheduler = BackgroundScheduler(timezone=ZoneInfo(tz))
            self.scheduler.start()
            self._register_jobs(settings, run_scrape_fn, run_report_fn)
            self.initialized = True
            logger.info("Scheduler started with timezone=%s", tz)

    def _parse_hhmm(self, hhmm: str) -> tuple[int, int]:
        parts = hhmm.split(":")
        if len(parts) != 2:
            return 0, 0
        hour = max(0, min(23, int(parts[0])))
        minute = max(0, min(59, int(parts[1])))
        return hour, minute

    def _register_jobs(self, settings: dict[str, str], run_scrape_fn, run_report_fn) -> None:
        if not self.scheduler:
            return

        scrape_h, scrape_m = self._parse_hhmm(settings.get("scrape_time", "00:00"))
        report_h, report_m = self._parse_hhmm(settings.get("report_time", "12:00"))

        self.scheduler.add_job(
            run_scrape_fn,
            trigger=CronTrigger(hour=scrape_h, minute=scrape_m),
            id="daily_scrape",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self.scheduler.add_job(
            run_report_fn,
            trigger=CronTrigger(hour=report_h, minute=report_m),
            id="daily_report",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

        logger.info(
            "Scheduled jobs updated: scrape=%02d:%02d report=%02d:%02d",
            scrape_h,
            scrape_m,
            report_h,
            report_m,
        )

    def reload_schedule(self, run_scrape_fn, run_report_fn) -> None:
        if not self.scheduler:
            return
        db = SessionLocal()
        try:
            settings = get_schedule_settings(db)
        finally:
            db.close()
        self._register_jobs(settings, run_scrape_fn, run_report_fn)

    def info(self) -> dict:
        if not self.scheduler:
            return {"enabled": False}

        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                }
            )

        return {
            "enabled": True,
            "timezone": str(self.scheduler.timezone),
            "jobs": jobs,
            "checked_at": datetime.utcnow().isoformat(),
        }


app_scheduler = AppScheduler()
