"""AI Event Agent — FastAPI API server."""

import os
import threading
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import String
from sqlalchemy.orm import Session, joinedload

from auth import (
    AuthUser,
    authenticate,
    create_access_token,
    get_current_user,
    require_super_admin,
)
from config import JWT_EXPIRE_HOURS, logger
from crew import run_crew
from db.database import SessionLocal, get_db, init_db
from db.models import Event, Report, ScrapeRun, SearchQuery, Speaker
from services.report_service import generate_daily_report, list_reports
from services.scheduler_service import app_scheduler
from services.settings_service import get_schedule_settings, set_setting


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    app_scheduler.start(_trigger_crew_background, _trigger_report_background)
    logger.info("FastAPI server started")
    try:
        yield
    finally:
        app_scheduler.stop()
        logger.info("FastAPI server stopped")


app = FastAPI(
    title="AI Event Agent API",
    description="Event and speaker intelligence with admin controls and daily reports",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    role: str


class MeResponse(BaseModel):
    username: str
    role: str
    expires_at: str


class QueryCreateRequest(BaseModel):
    query: str
    topic: str = "General"
    is_active: bool = True
    priority: int = 50


class QueryUpdateRequest(BaseModel):
    query: Optional[str] = None
    topic: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


class ScheduleUpdateRequest(BaseModel):
    timezone: str = "Asia/Kolkata"
    scrape_time: str = Field("00:00", pattern=r"^\d{2}:\d{2}$")
    report_time: str = Field("12:00", pattern=r"^\d{2}:\d{2}$")


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    report_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str


_crew_running = False
_report_running = False
_last_crew_result = None
_last_report_result = None


def _run_crew_job() -> None:
    global _crew_running, _last_crew_result
    try:
        _last_crew_result = run_crew()
    except Exception as exc:
        logger.error("Crew run failed: %s", exc)
        _last_crew_result = {"status": "failed", "errors": [str(exc)]}
    finally:
        _crew_running = False


def _trigger_crew_background() -> None:
    global _crew_running
    if _crew_running:
        raise HTTPException(status_code=409, detail="A crew run is already in progress")
    _crew_running = True
    threading.Thread(target=_run_crew_job, daemon=True).start()


def _run_report_job() -> None:
    global _report_running, _last_report_result
    db = SessionLocal()
    try:
        report = generate_daily_report(db)
        _last_report_result = {
            "status": report.status,
            "report_id": report.id,
            "report_date": report.report_date.isoformat() if report.report_date else None,
        }
    except Exception as exc:
        logger.error("Report generation failed: %s", exc)
        _last_report_result = {"status": "failed", "errors": [str(exc)]}
    finally:
        db.close()
        _report_running = False


def _trigger_report_background() -> None:
    global _report_running
    if _report_running:
        raise HTTPException(status_code=409, detail="A report generation is already in progress")
    _report_running = True
    threading.Thread(target=_run_report_job, daemon=True).start()


@app.post("/api/auth/login", response_model=LoginResponse)
def login(request: LoginRequest):
    user = authenticate(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user)
    return LoginResponse(
        access_token=token,
        expires_in_seconds=JWT_EXPIRE_HOURS * 3600,
        role=user.role,
    )


@app.get("/api/auth/me", response_model=MeResponse)
def me(user: AuthUser = Depends(get_current_user)):
    return MeResponse(
        username=user.username,
        role=user.role,
        expires_at=user.expires_at.isoformat(),
    )


@app.get("/api/status")
def get_status(
    db: Session = Depends(get_db),
    _: AuthUser = Depends(get_current_user),
):
    last_run = db.query(ScrapeRun).order_by(ScrapeRun.started_at.desc()).first()
    last_report = db.query(Report).order_by(Report.created_at.desc()).first()
    return {
        "status": "running",
        "crew_running": _crew_running,
        "report_running": _report_running,
        "scheduler": app_scheduler.info(),
        "totals": {
            "events": db.query(Event).count(),
            "speakers": db.query(Speaker).count(),
            "reports": db.query(Report).count(),
        },
        "last_run": {
            "id": last_run.id,
            "status": last_run.status,
            "started_at": last_run.started_at.isoformat() if last_run.started_at else None,
            "completed_at": last_run.completed_at.isoformat() if last_run.completed_at else None,
            "events_found": last_run.events_found,
            "events_new": last_run.events_new,
            "events_updated": last_run.events_updated,
            "speakers_found": last_run.speakers_found,
            "errors": last_run.errors or [],
        }
        if last_run
        else None,
        "last_report": {
            "id": last_report.id,
            "report_date": last_report.report_date.isoformat() if last_report.report_date else None,
            "status": last_report.status,
            "created_at": last_report.created_at.isoformat() if last_report.created_at else None,
            "file_name": last_report.file_name,
        }
        if last_report
        else None,
    }


@app.get("/api/events")
def list_events(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: AuthUser = Depends(get_current_user),
):
    query = db.query(Event).options(joinedload(Event.speakers))

    if status:
        query = query.filter(Event.status == status)
    if city:
        query = query.filter(Event.city.ilike(f"%{city}%"))
    if search:
        query = query.filter(Event.name.ilike(f"%{search}%"))
    if category:
        query = query.filter(Event.category.cast(String).ilike(f"%{category}%"))

    total = query.count()
    events = query.order_by(Event.last_scraped_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "events": [e.to_dict() for e in events],
    }


@app.get("/api/events/{event_id}")
def get_event(
    event_id: str,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(get_current_user),
):
    event = (
        db.query(Event)
        .options(joinedload(Event.speakers))
        .filter(Event.id == event_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event.to_dict()


@app.get("/api/speakers")
def list_speakers(
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: AuthUser = Depends(get_current_user),
):
    query = db.query(Speaker)
    if search:
        query = query.filter(Speaker.name.ilike(f"%{search}%"))

    total = query.count()
    speakers = query.offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "speakers": [s.to_dict() for s in speakers],
    }


@app.get("/api/reports")
def get_reports(
    db: Session = Depends(get_db),
    _: AuthUser = Depends(get_current_user),
):
    return {"reports": list_reports(db)}


@app.get("/api/reports/{report_id}/download")
def download_report(
    report_id: str,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(get_current_user),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="Report file missing")

    return FileResponse(
        report.file_path,
        media_type="application/pdf",
        filename=report.file_name,
    )


@app.post("/api/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(get_current_user),
):
    from config import get_chat_llm

    keywords = request.message.lower().split()
    relevant_events = []

    all_events = db.query(Event).options(joinedload(Event.speakers)).all()
    for event in all_events:
        event_text = f"{event.name} {event.description} {event.city} {event.location}".lower()
        if any(kw in event_text for kw in keywords):
            relevant_events.append(event)

    report_context = ""
    if request.report_id:
        report = db.query(Report).filter(Report.id == request.report_id).first()
        if report and report.raw_text:
            report_context = (
                "Selected report context:\n"
                f"Report date: {report.report_date}\n"
                f"Report text:\n{report.raw_text[:12000]}\n\n"
            )

    event_context = ""
    if relevant_events:
        event_context = "Relevant DB events:\n\n"
        for e in relevant_events[:12]:
            event_context += f"- {e.name}\n"
            event_context += f"  Date: {e.date_text}\n"
            event_context += f"  Location: {e.location}, {e.city}\n"
            event_context += f"  Status: {e.status}\n"
            event_context += f"  URL: {e.url}\n"
            if e.speakers:
                event_context += "  Speakers:\n"
                for sp in e.speakers[:5]:
                    event_context += f"    - {sp.name} ({sp.company})\n"
                    if sp.topic_category:
                        event_context += f"      Topic: {sp.topic_category}\n"
                    if sp.topic_links:
                        event_context += f"      Topic links: {', '.join(sp.topic_links)}\n"
            event_context += "\n"

    system_prompt = (
        "You are an AI Event Assistant. Use selected report context first, then DB event/speaker context. "
        "Answer concisely and avoid fabrication. If data is missing, explicitly say so.\n\n"
        f"{report_context}{event_context}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    for msg in request.history[-10:]:
        messages.append(msg)
    messages.append({"role": "user", "content": request.message})

    try:
        llm = get_chat_llm()
        response = llm.invoke(messages)
        return ChatResponse(response=response.content)
    except Exception as exc:
        logger.error("Chat LLM call failed: %s", exc)
        return ChatResponse(response="I am unable to answer right now. Please try again.")


@app.get("/api/admin/queries")
def admin_list_queries(
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_super_admin),
):
    rows = db.query(SearchQuery).order_by(SearchQuery.priority.asc(), SearchQuery.created_at.asc()).all()
    return {"queries": [r.to_dict() for r in rows]}


@app.post("/api/admin/queries")
def admin_create_query(
    payload: QueryCreateRequest,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_super_admin),
):
    existing = db.query(SearchQuery).filter(SearchQuery.query == payload.query).first()
    if existing:
        raise HTTPException(status_code=409, detail="Query already exists")

    row = SearchQuery(
        id=str(uuid.uuid4()),
        query=payload.query,
        topic=payload.topic,
        is_active=payload.is_active,
        priority=payload.priority,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row.to_dict()


@app.put("/api/admin/queries/{query_id}")
def admin_update_query(
    query_id: str,
    payload: QueryUpdateRequest,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_super_admin),
):
    row = db.query(SearchQuery).filter(SearchQuery.id == query_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Query not found")

    if payload.query is not None:
        row.query = payload.query
    if payload.topic is not None:
        row.topic = payload.topic
    if payload.is_active is not None:
        row.is_active = payload.is_active
    if payload.priority is not None:
        row.priority = payload.priority

    db.commit()
    db.refresh(row)
    return row.to_dict()


@app.delete("/api/admin/queries/{query_id}")
def admin_delete_query(
    query_id: str,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_super_admin),
):
    row = db.query(SearchQuery).filter(SearchQuery.id == query_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Query not found")
    db.delete(row)
    db.commit()
    return {"deleted": True, "id": query_id}


@app.get("/api/admin/schedule")
def admin_get_schedule(
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_super_admin),
):
    return get_schedule_settings(db)


@app.put("/api/admin/schedule")
def admin_update_schedule(
    payload: ScheduleUpdateRequest,
    db: Session = Depends(get_db),
    _: AuthUser = Depends(require_super_admin),
):
    set_setting(db, "timezone", payload.timezone)
    set_setting(db, "scrape_time", payload.scrape_time)
    set_setting(db, "report_time", payload.report_time)
    app_scheduler.reload_schedule(_trigger_crew_background, _trigger_report_background)
    return get_schedule_settings(db)


@app.post("/api/admin/run-now")
def admin_run_now(_: AuthUser = Depends(require_super_admin)):
    _trigger_crew_background()
    return {"started": True, "message": "Scrape pipeline started"}


@app.post("/api/admin/reports/generate-now")
def admin_report_now(_: AuthUser = Depends(require_super_admin)):
    _trigger_report_background()
    return {"started": True, "message": "Report generation started"}


@app.post("/api/run-crew")
def legacy_trigger(
    _: AuthUser = Depends(require_super_admin),
):
    _trigger_crew_background()
    return {"started": True, "message": "Crew pipeline started"}
