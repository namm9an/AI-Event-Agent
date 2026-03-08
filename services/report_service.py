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
        if event.registration_url:
            lines.append(f"   Registration: {event.registration_url}")
        if event.speakers:
            lines.append("   Speakers:")
            for sp in event.speakers[:8]:
                lines.append(f"    - {sp.name} | {sp.designation} | {sp.company}")
                topic = getattr(sp, 'topic_category', '') or sp.talk_title or ''
                if topic:
                    lines.append(f"      Topic: {topic}")
                topic_links = [l for l in (sp.topic_links or []) if l]
                if topic_links:
                    lines.append(f"      Topic links: {', '.join(topic_links)}")
                linkedin = getattr(sp, 'linkedin_url', '') or ''
                wikipedia = getattr(sp, 'wikipedia_url', '') or ''
                if linkedin:
                    lines.append(f"      LinkedIn: [LINK]{linkedin}[/LINK]")
                if wikipedia:
                    lines.append(f"      Wikipedia: [LINK]{wikipedia}[/LINK]")
                prev_talks = [t for t in (sp.previous_talks or []) if t]
                if prev_talks:
                    lines.append(f"      Previous talks: {', '.join(prev_talks)}")
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


def _render_pdf_structured(events: list, summary: dict, output_path: Path) -> None:
    """Render a well-formatted PDF report using fpdf2 with proper layout."""
    unicode_font_path = _find_unicode_font()

    try:
        from fpdf import FPDF

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)

        # Register fonts
        has_unicode = bool(unicode_font_path)

        _registered_styles: set[str] = set()

        def set_font(style: str = "", size: int = 11):
            if has_unicode:
                if style not in _registered_styles:
                    pdf.add_font("Unicode", style, str(unicode_font_path))
                    _registered_styles.add(style)
                pdf.set_font("Unicode", style=style, size=size)
            else:
                pdf.set_font("Helvetica", style=style, size=size)

        def add_link(url: str, label: str = ""):
            pdf.set_text_color(26, 130, 255)
            pdf.cell(0, 6, label or url, link=url, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)

        def hr():
            pdf.set_draw_color(200, 200, 200)
            y = pdf.get_y()
            pdf.line(10, y, 200, y)
            pdf.ln(4)

        # --- Title Page / Header ---
        pdf.add_page()
        set_font("B", 22)
        pdf.set_text_color(30, 60, 120)
        pdf.cell(0, 14, "AI Event Agent", new_x="LMARGIN", new_y="NEXT", align="C")
        set_font("B", 14)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 10, "Daily Intelligence Report", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(4)
        hr()

        # --- Summary Section ---
        set_font("B", 12)
        pdf.cell(0, 8, "Report Summary", new_x="LMARGIN", new_y="NEXT")
        set_font("", 10)
        pdf.cell(0, 6, f"Generated: {summary.get('generated_at', 'N/A')} UTC", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, f"Total Events: {summary.get('events', 0)}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, f"Total Speakers: {summary.get('speakers', 0)}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)
        hr()

        # --- Events ---
        for idx, event in enumerate(events, start=1):
            # Event header
            set_font("B", 12)
            pdf.set_fill_color(240, 245, 255)
            event_title = f"{idx}. {event.name}"
            pdf.multi_cell(0, 8, event_title, fill=True)
            pdf.ln(2)

            # Event details table
            set_font("", 10)
            details = [
                ("Date", event.date_text or "TBA"),
                ("Location", f"{event.location or ''}, {event.city or ''}".strip(", ")),
                ("Status", event.status or "Unknown"),
                ("Type", getattr(event, 'event_type', '') or ""),
            ]
            for label, value in details:
                if value:
                    set_font("B", 10)
                    pdf.cell(30, 6, f"{label}:")
                    set_font("", 10)
                    pdf.cell(0, 6, value, new_x="LMARGIN", new_y="NEXT")

            # URLs
            if event.url:
                set_font("B", 10)
                pdf.cell(30, 6, "Event URL:")
                add_link(event.url)
            if event.registration_url:
                set_font("B", 10)
                pdf.cell(30, 6, "Register:")
                add_link(event.registration_url)

            # Speakers
            if event.speakers:
                pdf.ln(2)
                set_font("B", 11)
                pdf.set_text_color(30, 60, 120)
                pdf.cell(0, 7, f"Speakers ({len(event.speakers)})", new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(0, 0, 0)

                # Speaker table header
                set_font("B", 9)
                pdf.set_fill_color(60, 90, 150)
                pdf.set_text_color(255, 255, 255)
                col_widths = [45, 35, 35, 40, 35]
                headers = ["Name", "Designation", "Company", "Topic", "Talk Title"]
                for i, h in enumerate(headers):
                    pdf.cell(col_widths[i], 7, h, border=1, fill=True)
                pdf.ln()
                pdf.set_text_color(0, 0, 0)

                # Speaker rows
                set_font("", 8)
                for sp_idx, sp in enumerate(event.speakers[:8]):
                    if sp_idx % 2 == 0:
                        pdf.set_fill_color(248, 248, 255)
                    else:
                        pdf.set_fill_color(255, 255, 255)

                    topic = getattr(sp, 'topic_category', '') or ''
                    cells = [
                        sp.name or "",
                        (sp.designation or "")[:25],
                        (sp.company or "")[:25],
                        topic[:30],
                        (sp.talk_title or "")[:30],
                    ]
                    for i, cell_text in enumerate(cells):
                        pdf.cell(col_widths[i], 6, cell_text, border=1, fill=True)
                    pdf.ln()

                # Speaker details (LinkedIn, summary, etc.)
                for sp in event.speakers[:8]:
                    linkedin = getattr(sp, 'linkedin_url', '') or ''
                    wikipedia = getattr(sp, 'wikipedia_url', '') or ''
                    if linkedin or wikipedia or sp.talk_summary:
                        set_font("", 8)
                        pdf.set_text_color(100, 100, 100)
                        if sp.talk_summary:
                            pdf.multi_cell(0, 5, f"  {sp.name}: {sp.talk_summary[:150]}")
                        if linkedin:
                            pdf.cell(20, 5, f"  LinkedIn: ")
                            add_link(linkedin, linkedin[:60])
                        if wikipedia:
                            pdf.cell(20, 5, f"  Wikipedia: ")
                            add_link(wikipedia, wikipedia[:60])
                        pdf.set_text_color(0, 0, 0)

            pdf.ln(3)
            hr()

        pdf.output(str(output_path))
        return

    except Exception as exc:
        logger.warning("Structured PDF rendering failed (%s). Trying fallback.", exc)

    # Fallback: plain text rendering
    _render_pdf_fallback(events, summary, output_path)


def _render_pdf_fallback(events: list, summary: dict, output_path: Path) -> None:
    """Simple fallback PDF renderer using PyMuPDF."""
    try:
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        y = 72

        def write_line(text: str, fontsize: int = 10):
            nonlocal page, y
            if y > 780:
                page = doc.new_page()
                y = 72
            clean = _re.sub(r'\[/?LINK\]', '', text)
            page.insert_text((50, y), clean[:120], fontsize=fontsize)
            y += fontsize + 4

        write_line("AI Event Agent — Daily Report", 16)
        write_line(f"Generated: {summary.get('generated_at', '')} UTC", 10)
        write_line(f"Events: {summary.get('events', 0)} | Speakers: {summary.get('speakers', 0)}", 10)
        y += 10

        for idx, event in enumerate(events, start=1):
            write_line(f"{idx}. {event.name}", 12)
            write_line(f"   Date: {event.date_text} | Location: {event.location}, {event.city}")
            write_line(f"   Status: {event.status}")
            if event.speakers:
                for sp in event.speakers[:5]:
                    topic = getattr(sp, 'topic_category', '') or ''
                    write_line(f"   - {sp.name} | {sp.designation} | {sp.company} | {topic}")
            y += 6

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
    _render_pdf_structured(events, summary, file_path)

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
