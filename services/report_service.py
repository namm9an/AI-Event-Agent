"""Daily PDF report generation and retrieval helpers."""

import os
import re as _re
import uuid
from datetime import date, datetime
from pathlib import Path

_LINK_RE = _re.compile(r'^\[LINK\](https?://\S+)\[/LINK\]$')

from sqlalchemy.orm import Session, joinedload

from config import REPORTS_DIR, REPORT_FONT_PATH, logger
from db.models import Event, Report


def _reports_root() -> Path:
    path = Path(REPORTS_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _collect_report_data(db: Session) -> tuple[list[Event], dict]:
    events = (
        db.query(Event)
        .options(joinedload(Event.speakers))
        .order_by(Event.last_scraped_at.desc())
        .limit(200)
        .all()
    )

    speakers = sum(len(e.speakers) for e in events)
    summary = {
        "events": len(events),
        "speakers": speakers,
        "generated_at": datetime.utcnow().isoformat(),
    }
    return events, summary


def _build_report_text(events: list[Event], summary: dict) -> str:
    lines = []
    lines.append("AI Event Agent Daily Report")
    lines.append(f"Generated at: {summary['generated_at']} UTC")
    lines.append(f"Total events: {summary['events']}")
    lines.append(f"Total speakers: {summary['speakers']}")
    lines.append("")

    for idx, event in enumerate(events, start=1):
        lines.append(f"{idx}. {event.name}")
        lines.append(f"   Date: {event.date_text}")
        lines.append(f"   Location: {event.location}, {event.city}")
        lines.append(f"   Status: {event.status}")
        lines.append(f"   Event URL: {event.url}")
        lines.append(f"   Topic links: {event.registration_url or 'N/A'}")
        if event.speakers:
            lines.append("   Speakers:")
            for sp in event.speakers[:8]:
                topic_links = ", ".join(sp.topic_links or []) if getattr(sp, "topic_links", None) else "N/A"
                prev_talks = ", ".join(sp.previous_talks or []) if getattr(sp, "previous_talks", None) else "N/A"
                lines.append(f"    - {sp.name} | {sp.designation} | {sp.company}")
                lines.append(f"      Topic: {getattr(sp, 'topic_category', '') or sp.talk_title or 'N/A'}")
                lines.append(f"      Topic links: {topic_links}")
                linkedin = getattr(sp, 'linkedin_url', '') or ''
                wikipedia = getattr(sp, 'wikipedia_url', '') or ''
                lines.append(f"      LinkedIn: [LINK]{linkedin}[/LINK]" if linkedin else "      LinkedIn: N/A")
                lines.append(f"      Wikipedia: [LINK]{wikipedia}[/LINK]" if wikipedia else "      Wikipedia: N/A")
                lines.append(f"      Previous talks: {prev_talks}")
                if sp.talk_summary:
                    lines.append(f"      Summary: {sp.talk_summary}")
        lines.append("")

    return "\n".join(lines)


def _find_unicode_font() -> Path | None:
    candidates = [
        REPORT_FONT_PATH,
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if path.exists():
            return path
    return None


def _contains_non_latin1(text: str) -> bool:
    return any(ord(ch) > 255 for ch in text)


def _render_pdf(text: str, output_path: Path) -> None:
    unicode_font_path = _find_unicode_font()

    try:
        from fpdf import FPDF

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        if unicode_font_path:
            pdf.add_font("Unicode", "", str(unicode_font_path))
            pdf.set_font("Unicode", size=11)
        else:
            pdf.set_font("Helvetica", size=11)
            if _contains_non_latin1(text):
                raise RuntimeError(
                    "Unicode font not found for fpdf2; falling back to PyMuPDF renderer"
                )

        for line in text.splitlines():
            m = _LINK_RE.match(line.strip())
            if m:
                url = m.group(1)
                pdf.set_text_color(26, 211, 255)  # cyan for clickable links
                pdf.cell(0, 6, url, link=url, new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(0, 0, 0)
            else:
                pdf.multi_cell(0, 6, line)
        pdf.output(str(output_path))
        return
    except Exception as exc:
        logger.warning("FPDF rendering failed (%s). Trying PyMuPDF fallback.", exc)

    try:
        import fitz

        doc = fitz.open()
        page = doc.new_page()
        y = 72
        for line in text.splitlines():
            if y > 800:
                page = doc.new_page()
                y = 72
            clean_line = _re.sub(r'\[/?LINK\]', '', line)
            page.insert_text((50, y), clean_line[:120], fontsize=10)
            y += 14
        doc.save(str(output_path))
        doc.close()
    except Exception as exc:
        raise RuntimeError(f"PDF generation failed for {output_path}: {exc}") from exc


def generate_daily_report(db: Session, report_date: date | None = None) -> Report:
    report_date = report_date or date.today()
    existing = db.query(Report).filter(Report.report_date == report_date).first()

    report_id = existing.id if existing else str(uuid.uuid4())
    file_name = f"daily-report-{report_date.isoformat()}.pdf"
    file_path = _reports_root() / file_name

    if not existing:
        existing = Report(
            id=report_id,
            report_date=report_date,
            file_name=file_name,
            file_path=str(file_path),
            status="running",
            summary_json={},
            raw_text="",
        )
        db.add(existing)
    else:
        existing.status = "running"

    db.commit()

    events, summary = _collect_report_data(db)
    raw_text = _build_report_text(events, summary)
    _render_pdf(raw_text, file_path)

    existing.file_name = file_name
    existing.file_path = str(file_path)
    existing.summary_json = summary
    existing.raw_text = raw_text
    existing.status = "ready"
    existing.created_at = datetime.utcnow()
    db.commit()
    db.refresh(existing)
    return existing


def list_reports(db: Session) -> list[dict]:
    reports = db.query(Report).order_by(Report.report_date.desc()).all()
    items = []
    for rep in reports:
        item = rep.to_dict()
        try:
            item["size_bytes"] = os.path.getsize(rep.file_path)
        except OSError:
            item["size_bytes"] = None
        items.append(item)
    return items
