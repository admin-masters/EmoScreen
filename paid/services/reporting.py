import io
import os
import re
from pathlib import Path

from django.conf import settings
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from paid.models import (
    EsCfgDerivedList,
    EsCfgOption,
    EsCfgQuestion,
    EsCfgReportTemplate,
    EsRepReport,
    EsSubAnswer,
    EsSubScaleScore,
)

BRAND_LOGO_FILENAME = "logo_eq_final.jpeg"
BRAND_GREEN = colors.HexColor("#4caf50")
BRAND_BLUE = colors.HexColor("#0b2a4d")
TABLE_BORDER = colors.HexColor("#d6d6d6")
FOOTER_BG = colors.HexColor("#f3f3f3")


def build_pdf_password(prefix_source: str, phone: str) -> str:
    source = (prefix_source or "").strip()
    phone_digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    return f"{source[:4]}{phone_digits[-4:]}"


def report_paths(order_code: str):
    base = Path(settings.MEDIA_ROOT) / "paid_reports" / order_code
    os.makedirs(base, exist_ok=True)
    return {
        "patient": str(base / "patient.pdf"),
        "doctor": str(base / "doctor.pdf"),
    }


def _encrypt_pdf(raw_pdf: bytes, password: str) -> bytes:
    reader = PdfReader(io.BytesIO(raw_pdf))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(password)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def _age_text(dob, assessment_date):
    if not dob or not assessment_date:
        return ""
    months = (assessment_date.year - dob.year) * 12 + (assessment_date.month - dob.month)
    if assessment_date.day < dob.day:
        months -= 1
    years = max(0, months // 12)
    rem = max(0, months % 12)
    if years and rem:
        return f"{years} years {rem} months"
    if years:
        return f"{years} years"
    return f"{rem} months"


def _question_rows(submission):
    question_qs = EsCfgQuestion.objects.filter(form=submission.form).order_by("global_order", "question_order")
    answers = {a.question_id: a for a in EsSubAnswer.objects.filter(submission=submission)}
    options = {o.option_code: o for o in EsCfgOption.objects.all()}

    rows = []
    for q in question_qs:
        ans = answers.get(q.question_code)
        if not ans:
            continue
        raw = str(ans.value_json)
        opt = options.get(raw)
        label = opt.label if opt else raw
        rows.append((len(rows) + 1, q.question_text, label))
    return rows


def _ace_items(submission):
    answers = {a.question_id: str(a.value_json) for a in EsSubAnswer.objects.filter(submission=submission)}
    question_map = {q.question_code: q for q in EsCfgQuestion.objects.filter(form=submission.form)}
    option_map = {o.option_code: o for o in EsCfgOption.objects.all()}

    ace_lists = EsCfgDerivedList.objects.filter(form=submission.form, name__icontains="ace")
    items = []
    for dl in ace_lists:
        expected = str(dl.filter_response_value or "").strip().lower()
        section_code = dl.section_id
        for q_code, raw in answers.items():
            q = question_map.get(q_code)
            if not q:
                continue
            if section_code and q.section_id != section_code:
                continue
            opt = option_map.get(raw)
            candidates = {raw.lower()}
            if opt:
                candidates.add(str(opt.value).strip().lower())
                candidates.add(str(opt.label).strip().lower())
            if expected in candidates:
                items.append(q.question_text)
    return list(dict.fromkeys(items))


def _header_band(submission):
    age = _age_text(submission.child_dob, submission.assessment_date)
    left = (
        f"Child Name: {submission.child_name or ''}<br/>"
        f"Child Age: {age}<br/>"
        f"Child Gender: {submission.gender or ''}<br/>"
        f"Completed By: {submission.completed_by or ''}"
    )
    right = f"Date: {submission.assessment_date or ''}"
    return left, right


def _disclaimer_html(form, report_type):
    t = _report_template(form, report_type)
    if t and t.disclaimer_html:
        return t.disclaimer_html
    return (
        "Kindly note, this report is purely based on the information submitted by the patient's guardians. "
        "For support, please contact +91-9321450803."
    )


def _normalize_paragraph_html(text: str) -> str:
    """Normalize template HTML to ReportLab Paragraph-friendly markup."""
    cleaned = (text or "").strip()
    if not cleaned:
        return ""

    # ReportLab expects self-closing line breaks and supports a limited markup subset.
    cleaned = re.sub(r"<\s*br\s*>", "<br/>", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<\s*br\s*/\s*>", "<br/>", cleaned, flags=re.IGNORECASE)

    # Strip outer <p> wrapper often present in template HTML.
    cleaned = re.sub(r"^\s*<\s*p\s*>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<\s*/\s*p\s*>\s*$", "", cleaned, flags=re.IGNORECASE)
    return cleaned


def _report_template(form, report_type):
    return EsCfgReportTemplate.objects.filter(form=form, report_type=report_type).first()


def _resolve_logo_path(logo_value: str) -> str | None:
    if not logo_value:
        return None

    raw = Path(str(logo_value).strip())
    candidates = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        base = Path(getattr(settings, "BASE_DIR", Path.cwd()))
        media_root = Path(getattr(settings, "MEDIA_ROOT", ""))
        candidates.extend(
            [
                base / raw,
                base / "paid" / "assets" / "reporting" / "logos" / raw.name,
                base / "static" / "paid" / "reporting" / "logos" / raw.name,
                media_root / raw,
            ]
        )

    for candidate in candidates:
        if candidate and candidate.exists() and candidate.is_file():
            return str(candidate)
    return None


def _draw_page_footer(canvas, doc, template: EsCfgReportTemplate | None):
    canvas.saveState()
    page_width, _page_height = A4
    text_left = 6 * mm
    text_right = page_width - 6 * mm
    footer_height = 22 * mm
    base_y = 4 * mm

    canvas.setFillColor(FOOTER_BG)
    canvas.rect(0, 0, page_width, footer_height, stroke=0, fill=1)

    company = (template.footer_company if template else "") or "EQUIPOISE Learning Private Limited"
    tagline = (template.footer_tagline if template else "") or (
        "The ISO 9001-2015 Certified\nEmotional Intelligence Research & Training Organisation"
    )
    phone = (template.footer_phone if template else "") or "+91 9004806077"
    email = (template.footer_email if template else "") or "equip2006@gmail.com"

    canvas.setFillColor(colors.black)
    canvas.setFont("Times-Bold", 12)
    canvas.drawString(text_left, base_y + 12 * mm, company)
    canvas.setFont("Times-Roman", 11)
    for idx, line in enumerate(str(tagline).splitlines()):
        canvas.drawString(text_left, base_y + (7 - idx * 4.4) * mm, line)

    canvas.setFont("Times-Bold", 12)
    canvas.drawRightString(text_right, base_y + 12 * mm, "Contact us")
    canvas.setFont("Times-Roman", 11)
    canvas.drawRightString(text_right, base_y + 7 * mm, str(phone))
    canvas.drawRightString(text_right, base_y + 2.5 * mm, str(email))
    email_width = canvas.stringWidth(str(email), "Times-Roman", 11)
    canvas.setLineWidth(0.4)
    canvas.line(text_right - email_width, base_y + 1.8 * mm, text_right, base_y + 1.8 * mm)

    canvas.restoreState()


def _draw_page_header(canvas, doc, template: EsCfgReportTemplate | None, submission, report_type: str):
    canvas.saveState()
    page_width, page_height = A4
    text_left = 8 * mm
    top_y = page_height - 10 * mm

    title = "Doctor Report for EmoScreen" if report_type == "doctor" else "Patient Report for EmoScreen"
    canvas.setFillColor(colors.black)
    canvas.setFont("Times-Bold", 19)
    canvas.drawString(text_left, top_y, title)

    logo_value = (template.header_logo_path if template else "") or BRAND_LOGO_FILENAME
    logo_path = _resolve_logo_path(logo_value)
    if not logo_path and logo_value != BRAND_LOGO_FILENAME:
        logo_path = _resolve_logo_path(BRAND_LOGO_FILENAME)
    logo_y = top_y - 17 * mm
    if logo_path:
        canvas.drawImage(
            logo_path,
            text_left,
            logo_y,
            width=112 * mm,
            height=13 * mm,
            preserveAspectRatio=True,
            mask="auto",
        )

    header_left, header_right = _header_band(submission)
    band_top = logo_y - 6 * mm
    band_height = 30 * mm
    canvas.setFillColor(BRAND_GREEN)
    canvas.rect(0, band_top - band_height, page_width, band_height, stroke=0, fill=1)

    clean_left = re.sub(r"<br\s*/?>", "\n", header_left)
    lines = [line for line in clean_left.splitlines() if line.strip()]
    canvas.setFillColor(colors.white)
    canvas.setFont("Times-Roman", 12)
    text_y = band_top - 6 * mm
    for line in lines:
        canvas.drawString(text_left, text_y, line.strip())
        text_y -= 5 * mm

    canvas.drawRightString(page_width - 8 * mm, band_top - 6 * mm, re.sub(r"<[^>]*>", "", header_right))

    canvas.restoreState()


def _build_pdf(report_type: str, submission) -> bytes:
    template = _report_template(submission.form, report_type)
    styles = getSampleStyleSheet()
    h_style = ParagraphStyle("h", parent=styles["Heading2"], fontName="Times-Bold", fontSize=13, textColor=BRAND_BLUE, spaceBefore=10, spaceAfter=8)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontName="Times-Roman", fontSize=12, leading=16)
    table_cell = ParagraphStyle(
        "table_cell",
        parent=body,
        fontName="Times-Roman",
        fontSize=11.5,
        leading=14,
        wordWrap="LTR",
    )
    table_cell_bold = ParagraphStyle(
        "table_cell_bold",
        parent=table_cell,
        fontName="Times-Bold",
        textColor=colors.white,
        alignment=1,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=24 * mm,
        rightMargin=24 * mm,
        topMargin=72 * mm,
        bottomMargin=30 * mm,
    )

    story = []
    story.append(Spacer(1, 1))

    greeting = "Dear Doctor," if report_type == "doctor" else "Dear Parent,"
    story.append(Paragraph(f"<b>{greeting}</b>", body))
    story.append(Spacer(1, 4))
    if report_type == "doctor":
        story.append(Paragraph("Your patient has filled the EmoScreen form.", body))
    else:
        story.append(Paragraph("Thank you for completing the EmoScreen form.", body))
    story.append(Paragraph("The responses are as follows:", body))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Responses", h_style))
    response_rows = [
        [
            Paragraph("Sr.", table_cell_bold),
            Paragraph("Question", table_cell_bold),
            Paragraph("Response", table_cell_bold),
        ]
    ]
    for idx, q, a in _question_rows(submission):
        response_rows.append([
            Paragraph(str(idx), table_cell),
            Paragraph(str(q), table_cell),
            Paragraph(str(a), table_cell),
        ])

    rt = Table(response_rows, colWidths=[12 * mm, 98 * mm, 52 * mm], repeatRows=1, hAlign="CENTER")
    rt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.35, TABLE_BORDER),
        ("FONTSIZE", (0, 0), (-1, -1), 11.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
    ]))
    for row_idx in range(1, len(response_rows)):
        if row_idx % 2 == 0:
            rt.setStyle(TableStyle([("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor("#efefef"))]))
    story.append(rt)

    if report_type == "doctor":
        story.append(Spacer(1, 8))
        story.append(Paragraph(
            f"Total score for this filled questionnaire is {submission.total_score or 0} / {submission.total_score_max_display or 0}",
            body,
        ))

        risk_rows = [[
            Paragraph("Disorder", table_cell_bold),
            Paragraph("Score", table_cell_bold),
            Paragraph("Risk Factor (%)", table_cell_bold),
        ]]
        for s in EsSubScaleScore.objects.filter(submission=submission, included_in_doctor_table=True).select_related("scale"):
            risk_rows.append([
                Paragraph(str(s.scale.label), table_cell),
                Paragraph(f"{s.score}/{s.max_score}", table_cell),
                Paragraph(f"{s.risk_percent:.2f}", table_cell),
            ])
        if len(risk_rows) > 1:
            story.append(Paragraph("The results fall into moderate to high risk for the following disorders:", body))
            risk_table = Table(risk_rows, colWidths=[72 * mm, 42 * mm, 42 * mm], repeatRows=1, hAlign="CENTER")
            risk_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), BRAND_GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.35, TABLE_BORDER),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(risk_table)

        ace = _ace_items(submission)
        if ace:
            story.append(Spacer(1, 8))
            story.append(Paragraph("ACE:", h_style))
            for item in ace:
                story.append(Paragraph(f"• {item}", body))

        summary = (
            "As per the report, some concerns are observed in the child. This requires thorough evaluation & an urgent referral and support of a family EQ coach."
            if submission.has_concerns
            else "As per the report, no major concerns have been observed in the child. However, close monitoring for changes in behaviour & a follow-up with you is advised after 3 months to review."
        )
        story.append(Spacer(1, 8))
        story.append(Paragraph(summary, body))

    story.append(Spacer(1, 10))
    story.append(Paragraph(_normalize_paragraph_html(_disclaimer_html(submission.form, report_type)), body))
    def _on_page(canvas, doc):
        _draw_page_header(canvas, doc, template, submission, report_type)
        _draw_page_footer(canvas, doc, template)

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buf.getvalue()


def generate_and_store_reports(submission):
    order = submission.order
    doctor = order.doctor

    patient_pwd = build_pdf_password(submission.child_name or order.patient_name, order.patient_whatsapp)
    doctor_pwd = build_pdf_password(doctor.email, doctor.whatsapp or "")

    patient_pdf = _encrypt_pdf(_build_pdf("patient", submission), patient_pwd)
    doctor_pdf = _encrypt_pdf(_build_pdf("doctor", submission), doctor_pwd)

    paths = report_paths(order.order_code)
    with open(paths["patient"], "wb") as f:
        f.write(patient_pdf)
    with open(paths["doctor"], "wb") as f:
        f.write(doctor_pdf)

    report, _ = EsRepReport.objects.update_or_create(
        submission=submission,
        defaults={
            "patient_pdf_path": paths["patient"],
            "doctor_pdf_path": paths["doctor"],
            "patient_pdf_password_hint": f"{(submission.child_name or order.patient_name)[:4]} + last 4 digits of patient WhatsApp",
            "doctor_pdf_password_hint": f"{(doctor.email or '')[:4]} + last 4 digits of doctor WhatsApp",
        },
    )
    return report, patient_pdf, doctor_pdf
