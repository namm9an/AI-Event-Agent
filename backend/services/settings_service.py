"""Helpers for app settings persistence."""

from sqlalchemy.orm import Session

from config import APP_TIMEZONE, DEFAULT_REPORT_TIME, DEFAULT_SCRAPE_TIME
from db.models import AppSetting


def get_setting(db: Session, key: str, default: str) -> str:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    return row.value if row else default


def set_setting(db: Session, key: str, value: str) -> None:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))
    db.commit()


def get_schedule_settings(db: Session) -> dict[str, str]:
    return {
        "timezone": get_setting(db, "timezone", APP_TIMEZONE),
        "scrape_time": get_setting(db, "scrape_time", DEFAULT_SCRAPE_TIME),
        "report_time": get_setting(db, "report_time", DEFAULT_REPORT_TIME),
    }
