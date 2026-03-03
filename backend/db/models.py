"""
AI Event Agent — Database Models

SQLAlchemy models for events, speakers, and scrape run tracking.
"""

from datetime import datetime, date
from sqlalchemy import Boolean, Column, Date, String, Text, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Event(Base):
    """An AI/ML/Cloud event scraped from the web."""

    __tablename__ = "events"

    id = Column(String, primary_key=True)
    name = Column(String(500), nullable=False, index=True)
    description = Column(Text, default="")
    date_text = Column(String(200), default="")  # Raw date string from source
    location = Column(String(500), default="")
    city = Column(String(100), default="")
    status = Column(String(50), default="Unknown")  # Upcoming / Live / Past / Unknown
    category = Column(JSON, default=list)  # ["AI", "ML", "Cloud"]
    url = Column(String(2000), nullable=False, unique=True)
    organizer = Column(String(300), default="")
    event_type = Column(String(100), default="")  # Conference / Meetup / Webinar / Hackathon / Summit
    registration_url = Column(String(2000), default="")
    image_url = Column(String(2000), default="")

    # Timestamps
    scraped_at = Column(DateTime, default=datetime.utcnow)
    last_scraped_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    speakers = relationship("Speaker", back_populates="event", cascade="all, delete-orphan")

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "date_text": self.date_text,
            "location": self.location,
            "city": self.city,
            "status": self.status,
            "category": self.category or [],
            "url": self.url,
            "organizer": self.organizer,
            "event_type": self.event_type,
            "registration_url": self.registration_url,
            "image_url": self.image_url,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "last_scraped_at": self.last_scraped_at.isoformat() if self.last_scraped_at else None,
            "speakers": [s.to_dict() for s in self.speakers],
        }


class Speaker(Base):
    """A speaker identified at an event."""

    __tablename__ = "speakers"

    id = Column(String, primary_key=True)
    event_id = Column(String, ForeignKey("events.id"), nullable=False)
    name = Column(String(300), nullable=False)
    designation = Column(String(300), default="")
    company = Column(String(300), default="")
    talk_title = Column(String(500), default="")
    talk_summary = Column(Text, default="")
    linkedin_url = Column(String(2000), default="")
    linkedin_bio = Column(Text, default="")
    topic_links = Column(JSON, default=list)
    topic_category = Column(String(200), default="")
    previous_talks = Column(JSON, default=list)
    wikipedia_url = Column(String(2000), default="")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    event = relationship("Event", back_populates="speakers")

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "event_id": self.event_id,
            "name": self.name,
            "designation": self.designation,
            "company": self.company,
            "talk_title": self.talk_title,
            "talk_summary": self.talk_summary,
            "linkedin_url": self.linkedin_url,
            "linkedin_bio": self.linkedin_bio,
            "topic_links": self.topic_links or [],
            "topic_category": self.topic_category,
            "previous_talks": self.previous_talks or [],
            "wikipedia_url": self.wikipedia_url,
        }


class ScrapeRun(Base):
    """Tracks each scrape pipeline execution."""

    __tablename__ = "scrape_runs"

    id = Column(String, primary_key=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="running")  # running / completed / failed
    events_found = Column(Integer, default=0)
    events_new = Column(Integer, default=0)
    events_updated = Column(Integer, default=0)
    speakers_found = Column(Integer, default=0)
    errors = Column(JSON, default=list)  # List of error messages
    urls_scraped = Column(JSON, default=list)  # List of URLs attempted


class SearchQuery(Base):
    """Admin-managed search query configuration."""

    __tablename__ = "search_queries"

    id = Column(String, primary_key=True)
    query = Column(String(500), nullable=False, unique=True)
    topic = Column(String(200), default="General")
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=50)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "query": self.query,
            "topic": self.topic,
            "is_active": self.is_active,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Report(Base):
    """Generated daily shared PDF report."""

    __tablename__ = "reports"

    id = Column(String, primary_key=True)
    report_date = Column(Date, nullable=False, unique=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(2000), nullable=False)
    status = Column(String(50), default="ready")  # running / ready / failed
    summary_json = Column(JSON, default=dict)
    raw_text = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "report_date": self.report_date.isoformat() if isinstance(self.report_date, date) else str(self.report_date),
            "file_name": self.file_name,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "size_bytes": None,
        }


class AppSetting(Base):
    """Simple key-value app settings store."""

    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
