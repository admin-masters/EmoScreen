# content/pdf_utils.py
from __future__ import annotations
import io, re, datetime
from typing import List, Tuple
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from pypdf import PdfReader, PdfWriter

# ---------------- Password helpers ----------------
def _first4_letters(name: str) -> str:
    s = re.sub(r"[^A-Za-z]", "", (name or ""))
    return s[:4].lower()

def _last4_digits(num: str) -> str:
    d = re.sub(r"\D", "", (num or ""))
    return (d[-4:] if len(d) >= 4 else d[-len(d):]).rjust(4, "0")

def doctor_pdf_password(doctor_first_name: str, doctor_whatsapp: str) -> str:
    """First 4 letters of DOCTOR'S FIRST NAME + last 4 digits of doctor's WhatsApp."""
    return f"{_first4_letters(doctor_first_name)}{_last4_digits(doctor_whatsapp)}"

def patient_pdf_password(patient_name: str, parent_whatsapp: str) -> str:
    """First 4 letters of PATIENT'S NAME + last 4 digits of parent's WhatsApp."""
    return f"{_first4_letters(patient_name)}{_last4_digits(parent_whatsapp)}"

# ---------------- Enhanced Layout constants ----------------
PAGE_W, PAGE_H = A4
LM = 25 * mm  # Increased left margin
RM = 25 * mm  # Increased right margin
TM = 25 * mm  # Increased top margin
BM = 25 * mm  # Increased bottom margin
CONTENT_W = PAGE_W - LM - RM

# Enhanced column widths for better balance
LABEL_COL_W = 85 * mm   # Increased for longer labels
VALUE_COL_W = CONTENT_W - LABEL_COL_W - 10 * mm  # Added gutter space
GUTTER = 10 * mm  # Space between columns

LH = 16  # Increased line height for better readability

def _new_canvas() -> Tuple[io.BytesIO, canvas.Canvas]:
    buf = io.BytesIO()
    return buf, canvas.Canvas(buf, pagesize=A4)

def _rule(c: canvas.Canvas, y: float) -> None:
    c.setLineWidth(0.8)
    c.setStrokeColorRGB(0.3, 0.3, 0.3)  # Darker gray for better visibility
    c.line(LM, y, PAGE_W - RM, y)

def _title(c: canvas.Canvas, text: str) -> float:
    c.setFont("Helvetica-Bold", 24)
    c.setFillColorRGB(0, 0, 0)  # Ensure black text
    c.drawCentredString(PAGE_W / 2, PAGE_H - TM, text)
    return PAGE_H - TM - 15 * mm

def _ensure_space(c: canvas.Canvas, y: float, need: float) -> float:
    if y - need < BM + 10:  # Extra buffer at bottom
        c.showPage()
        y = _title(c, "Report (cont.)")
    return y

def _section(c: canvas.Canvas, title: str, y: float) -> float:
    y = _ensure_space(c, y, LH * 3)
    c.setFont("Helvetica-Bold", 14)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(LM, y, title)
    y -= 6
    _rule(c, y)
    return y - 12

def _kv_row(c: canvas.Canvas, label: str, value: str, y: float, size: int = 11) -> float:
    """
    Enhanced 2-column K/V layout with proper spacing and alignment.
    """
    # Prepare label text with colon
    label_text = (label or "").strip()
    if label_text and not label_text.endswith(':'):
        label_text += ":"
    
    # Set fonts and get wrapped lines
    c.setFont("Helvetica-Bold", size)
    lab_lines = simpleSplit(label_text, "Helvetica-Bold", size, LABEL_COL_W)
    
    c.setFont("Helvetica", size)
    val_lines = simpleSplit(value or "", "Helvetica", size, VALUE_COL_W)
    
    # Calculate required space
    max_lines = max(len(lab_lines), len(val_lines), 1)
    need = max_lines * LH + 4  # Extra padding between rows
    
    # Ensure we have space
    y = _ensure_space(c, y, need)
    
    # Draw label column
    c.setFont("Helvetica-Bold", size)
    c.setFillColorRGB(0, 0, 0)
    current_y = y
    for line in lab_lines:
        c.drawString(LM, current_y, line)
        current_y -= LH
    
    # Draw value column
    c.setFont("Helvetica", size)
    current_y = y
    value_x = LM + LABEL_COL_W + GUTTER
    for line in val_lines:
        c.drawString(value_x, current_y, line)
        current_y -= LH
    
    return y - need

def _wrapped_text(c: canvas.Canvas, text: str, y: float, size: int = 11, indent: float = 0) -> float:
    """Enhanced text wrapping with proper spacing."""
    if not text:
        return y
    
    # Calculate available width considering indent
    available_width = CONTENT_W - indent
    lines = simpleSplit(text, "Helvetica", size, available_width)
    need = len(lines) * LH + 4
    
    y = _ensure_space(c, y, need)
    
    c.setFont("Helvetica", size)
    c.setFillColorRGB(0, 0, 0)
    
    for line in lines:
        c.drawString(LM + indent, y, line)
        y -= LH
    
    return y - 4

def _bullet_list(c: canvas.Canvas, items: List[str], y: float, size: int = 11) -> float:
    """Enhanced bullet list with proper indentation and spacing."""
    if not items:
        return y
    
    c.setFont("Helvetica", size)
    bullet_indent = 8 * mm
    text_indent = bullet_indent + 6 * mm
    
    for item in items:
        if not item:
            continue
            
        # Calculate space needed for this item
        available_width = CONTENT_W - text_indent
        lines = simpleSplit(item, "Helvetica", size, available_width)
        need = len(lines) * LH + 2
        
        y = _ensure_space(c, y, need)
        
        # Draw bullet
        c.setFillColorRGB(0, 0, 0)
        c.drawString(LM + bullet_indent, y, "•")
        
        # Draw text lines
        current_y = y
        for i, line in enumerate(lines):
            c.drawString(LM + text_indent, current_y, line)
            current_y -= LH
        
        y = current_y - 2  # Small gap between items
    
    return y

def _encrypt(pdf_bytes: bytes, password: str) -> bytes:
    """Encrypt with user password; owner=password. Works in Acrobat, Chrome, macOS Preview, etc."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    
    for p in reader.pages:
        writer.add_page(p)
    
    try:
        # pypdf >= 3.7
        writer.encrypt(user_password=password, owner_password=password)
    except TypeError:
        # older signature
        writer.encrypt(password, password)
    
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()

# --------- Enhanced Report Generators ---------
PATIENT_DISCLAIMER = (
    "The report is based on form submissions received from the patient. "
    "This report does not intend to diagnose any condition or provide any therapy or treatment advice. "
    "It merely indicates the red flags based on the patient's entries and must be reconfirmed by a qualified "
    "medical professional. This report is intended for the doctor's use; sharing with patients is at the "
    "doctor's discretion. The system does not retain patient identifiable information; to retrieve later, "
    "the report number must be provided."
)

DOCTOR_NOTE = 'Click on the "Doctor Education" button in the email to access red-flag related CME and references.'

def build_patient_report_pdf_bytes(
    *, patient_name: str, parent_phone: str, report_code: str,
    rf_labels: List[str], form_name: str = "Behavioral and Emotional Red Flags",
    report_date: datetime.datetime | None = None
) -> Tuple[bytes, str]:
    """Return (encrypted_pdf_bytes, password)."""
    buf, c = _new_canvas()
    y = _title(c, "Patient Report")
    
    # Enhanced subtitle with better spacing
    c.setFont("Helvetica-Bold", 16)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    subtitle = f"{(patient_name or 'Patient').strip()}'s Red Flag Report"
    c.drawString(LM, y, subtitle)
    y -= 20
    
    # Report metadata
    y = _kv_row(c, "Screening Form", form_name, y, 12)
    y = _kv_row(c, "Report Date", (report_date or datetime.datetime.utcnow()).strftime("%Y-%m-%d"), y, 12)
    y = _kv_row(c, "Report Number", report_code, y, 12)
    y -= 10
    
    # Red flags section
    y = _section(c, "The following red flags were noticed", y)
    if rf_labels:
        y = _bullet_list(c, rf_labels, y, 11)
    else:
        y = _bullet_list(c, ["None"], y, 11)
    y -= 10
    
    # Patient details section
    y = _section(c, "Patient Details", y)
    y = _kv_row(c, "Patient Name", patient_name or "(not stored)", y)
    y = _kv_row(c, "Patient Phone Number", parent_phone or "(not stored)", y)
    y = _kv_row(c, "Patient ID", report_code, y)
    y = _kv_row(c, "The patient has used the tracking/screening tool named", form_name, y)
    y -= 15
    
    # Disclaimer section
    y = _section(c, "Disclaimer", y)
    y = _wrapped_text(c, PATIENT_DISCLAIMER, y, size=10)
    
    c.showPage()
    c.save()
    
    pdf = buf.getvalue()
    pwd = patient_pdf_password(patient_name or "", parent_phone or "")
    return _encrypt(pdf, pwd), pwd

# --- add this helper anywhere above build_doctor_report_pdf_bytes ---

# Add/keep at top if not already present:
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
# assumes LM, CONTENT_W, LH, _ensure_space, _new_canvas, _title, _kv_row,
# _section, _wrapped_text, _encrypt, doctor_pdf_password, etc. already exist.

def _rf_list_with_education_buttons(
    c, labels, links, y, size: int = 11
) -> float:
    """
    Render bullet list of red flags with a SMALL, minimal 'Doctor Education'
    button on the RIGHT, vertically centered per item. Returns new y.
    """
    if not labels:
        return y

    c.setFont("Helvetica", size)
    bullet_indent = 8 * mm
    text_indent = bullet_indent + 6 * mm

    # Small outlined button (email-style look)
    BTN_W = 32 * mm
    BTN_H = 6 * mm
    RIGHT_GUTTER = 6 * mm

    for label, link in zip(labels, links or []):
        # width available for text after reserving right-side button
        available_w = CONTENT_W - text_indent - BTN_W - RIGHT_GUTTER
        lines = simpleSplit(label or "", "Helvetica", size, available_w) or [""]

        # total height this item will occupy
        block_h = max(1, len(lines)) * LH
        y = _ensure_space(c, y, block_h + 4)

        # bullet
        c.setFillColorRGB(0, 0, 0)
        c.drawString(LM + bullet_indent, y, "•")

        # text (may wrap)
        ty = y
        for ln in lines:
            c.drawString(LM + text_indent, ty, ln)
            ty -= LH

        # button: vertically centered against the text block
        if link:
            bx = LM + CONTENT_W - BTN_W
            by = y - (block_h / 2) - (BTN_H / 2) + 2  # center on block
            c.setLineWidth(0.6)
            c.setStrokeColorRGB(0.2, 0.2, 0.2)
            c.roundRect(bx, by, BTN_W, BTN_H, 2, stroke=1, fill=0)
            c.setFont("Helvetica", 8)  # small & minimal
            btn_txt = "Doctor Education"
            tw = c.stringWidth(btn_txt, "Helvetica", 8)
            c.drawString(bx + (BTN_W - tw) / 2, by + (BTN_H - 8) / 2 + 2, btn_txt)
            c.linkURL(link, (bx, by, bx + BTN_W, by + BTN_H), relative=0)

        # next item
        y = y - block_h - 2

    return y


def build_doctor_report_pdf_bytes(
    *, doctor_full_name: str, doctor_first_name: str, doctor_id: str, doctor_whatsapp: str,
    patient_name: str, parent_phone: str, report_code: str,
    rf_labels: list, education_links: list,            # <-- include links
    form_name: str = "Behavioral and Emotional Red Flags",
    report_date=None
):
    """Return (encrypted_pdf_bytes, password). Password uses the doctor's FIRST NAME."""
    buf, c = _new_canvas()
    y = _title(c, "Doctor Report")

    # Report meta
    import datetime as _dt
    y = _kv_row(c, "Screening Form", form_name, y, 12)
    y = _kv_row(c, "Report Date", (_dt.datetime.utcnow()).strftime("%Y-%m-%d"), y, 12)
    y = _kv_row(c, "Report Number", report_code, y, 12)
    y -= 10

    # Doctor details
    y = _section(c, "Doctor Details", y)
    y = _kv_row(c, "Doctor Name", doctor_full_name or "(not set)", y)
    y = _kv_row(c, "Doctor ID", doctor_id or "(not set)", y)
    y = _wrapped_text(c, DOCTOR_NOTE, y, size=10)
    y -= 10

    # Patient details
    y = _section(c, "Patient Details", y)
    y = _kv_row(c, "Patient Name", patient_name or "(not stored)", y)
    y = _kv_row(c, "Phone", parent_phone or "(not stored)", y)
    y = _kv_row(c, "Form Name", form_name, y)
    y = _kv_row(c, "Report ID", report_code, y)
    y -= 10

    # Red flags + buttons
    y = _section(c, "Red Flags Identified", y)
    if rf_labels:
        y = _rf_list_with_education_buttons(c, rf_labels, education_links or [], y, 11)
    else:
        y = _bullet_list(c, ["None"], y, 11)
    y -= 10

    # RESTORE disclaimer (this existed in your earlier version)
    y = _section(c, "Disclaimer", y)                 # ← section header
    y = _wrapped_text(c, PATIENT_DISCLAIMER, y, 10)  # ← same text you use elsewhere
    # (Your original function had this exact section. Restoring it here.)  # :contentReference[oaicite:1]{index=1}

    c.showPage()
    c.save()

    pdf = buf.getvalue()
    pwd = doctor_pdf_password(doctor_first_name or "", doctor_whatsapp or "")
    return _encrypt(pdf, pwd), pwd
