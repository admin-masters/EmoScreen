from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, render
from django.utils.dateparse import parse_date

from .forms import PatientEmailForm
from .models import EsPayEmailLog, EsRepReport, EsSubSubmission, WorkflowCase, WorkflowPayment, WorkflowReport
from .services.reporting import generate_and_store_reports
from .services import audit
from .views import (
    _email_log_display_status,
    _read_report_pdf,
    _send_paid_doctor_report_email,
    _send_paid_patient_report_email,
)

JOURNEY_LOCKED_CONTEXT = {"hide_journey_nav": True}


@staff_member_required
def workflow_dashboard(request):
    cases = (
        WorkflowCase.objects
        .select_related("doctor", "order", "report", "payment", "report_tracking")
        .order_by("-created_at")
    )

    doctor_query = request.GET.get("doctor", "").strip()
    patient_query = request.GET.get("patient", "").strip()
    date_from = parse_date(request.GET.get("date_from", ""))
    date_to = parse_date(request.GET.get("date_to", ""))
    payment_status = request.GET.get("payment_status", "").strip()
    form_status = request.GET.get("form_status", "").strip()
    report_status = request.GET.get("report_status", "").strip()
    form_family = request.GET.get("form_family", "").strip()

    if doctor_query:
        cases = cases.filter(
            Q(doctor_name_snapshot__icontains=doctor_query)
            | Q(doctor__first_name__icontains=doctor_query)
            | Q(doctor__last_name__icontains=doctor_query)
            | Q(doctor__email__icontains=doctor_query)
            | Q(doctor__unique_doctor_code__icontains=doctor_query)
        )
    if patient_query:
        cases = cases.filter(
            Q(case_code__icontains=patient_query)
            | Q(patient_name__icontains=patient_query)
            | Q(patient_whatsapp__icontains=patient_query)
            | Q(patient_email__icontains=patient_query)
            | Q(order__order_code__icontains=patient_query)
        )
    if date_from:
        cases = cases.filter(created_at__date__gte=date_from)
    if date_to:
        cases = cases.filter(created_at__date__lte=date_to)
    if payment_status:
        cases = cases.filter(payment_status=payment_status)
    if form_status:
        cases = cases.filter(current_status=form_status)
    if report_status:
        cases = cases.filter(report_tracking__status=report_status)
    if form_family:
        cases = cases.filter(form_family=form_family)

    revenue_paise = (
        WorkflowPayment.objects
        .filter(case__in=cases, status=WorkflowPayment.Status.COMPLETED)
        .aggregate(total=Sum("amount_paise"))
        .get("total")
        or 0
    )
    stats = {
        "total": cases.count(),
        "completed": cases.filter(current_status=WorkflowCase.Status.COMPLETED).count(),
        "failed": cases.filter(current_status=WorkflowCase.Status.FAILED).count(),
        "payment_pending": cases.filter(payment_status=WorkflowCase.PaymentStatus.PENDING).count(),
        "submitted": cases.filter(current_status__in=[
            WorkflowCase.Status.SUBMITTED,
            WorkflowCase.Status.REPORT_PROCESSING,
            WorkflowCase.Status.REPORT_GENERATED,
            WorkflowCase.Status.REPORT_SENT,
            WorkflowCase.Status.COMPLETED,
        ]).count(),
        "revenue_rupees": revenue_paise / 100,
    }

    return render(
        request,
        "paid/workflow_dashboard.html",
        {
            "cases": cases[:100],
            "stats": stats,
            "filters": request.GET,
            "status_choices": WorkflowCase.Status.choices,
            "payment_choices": WorkflowCase.PaymentStatus.choices,
            "family_choices": WorkflowCase.FormFamily.choices,
            "report_choices": WorkflowReport.Status.choices,
            **JOURNEY_LOCKED_CONTEXT,
        },
    )


@staff_member_required
def workflow_detail(request, case_code):
    case = get_object_or_404(
        WorkflowCase.objects.select_related("doctor", "order", "legacy_submission", "paid_submission", "report"),
        case_code=case_code,
    )
    return render(
        request,
        "paid/workflow_detail.html",
        {
            "case": case,
            "events": case.events.all()[:200],
            "deliveries": case.delivery_attempts.all().order_by("-created_at"),
            "payment": getattr(case, "payment", None),
            "report_tracking": getattr(case, "report_tracking", None),
            **JOURNEY_LOCKED_CONTEXT,
        },
    )


@staff_member_required
def workflow_report_delivery(request, case_code):
    case = get_object_or_404(
        WorkflowCase.objects.select_related("doctor", "order", "legacy_submission", "paid_submission", "report"),
        case_code=case_code,
    )
    order = case.order
    submission = case.paid_submission
    report = case.report
    notice = ""
    patient_email_form = None

    if order:
        submission = submission or EsSubSubmission.objects.filter(order=order).first()
        report = report or (EsRepReport.objects.filter(submission=submission).first() if submission else None)
        if not order.patient_email:
            patient_email_form = PatientEmailForm()

    if request.method == "POST":
        action = request.POST.get("action")
        if not order or not submission:
            notice = "This workflow does not have a paid order/submission available for report delivery."
        elif action == "refresh_report":
            report, _patient_pdf, _doctor_pdf = generate_and_store_reports(submission)
            audit.mark_report_generated(case, report)
            notice = "Report regenerated successfully."
        elif action == "send_patient_report":
            if not order.patient_email:
                patient_email_form = PatientEmailForm(request.POST)
                if patient_email_form.is_valid():
                    order.patient_email = patient_email_form.cleaned_data["patient_email"]
                    order.save(update_fields=["patient_email", "updated_at"])
                    audit.update_patient_contact(case, patient_email=order.patient_email, request=request)
                else:
                    notice = "Please enter a valid patient email before sending the patient report."

            if order.patient_email and not notice:
                if not report:
                    report, _patient_pdf, _doctor_pdf = generate_and_store_reports(submission)
                    audit.mark_report_generated(case, report)
                try:
                    patient_status, attempted = _send_paid_patient_report_email(
                        order,
                        report,
                        _read_report_pdf(report.patient_pdf_path),
                        case,
                    )
                    audit.mark_report_sent(case, to_patient=attempted, patient_status=patient_status)
                    notice = "Patient report email sent." if patient_status == "SENT" else "Patient report email failed."
                except OSError as exc:
                    notice = f"Patient report PDF could not be read: {exc}"
        elif action == "send_doctor_report":
            if not report:
                report, _patient_pdf, _doctor_pdf = generate_and_store_reports(submission)
                audit.mark_report_generated(case, report)
            try:
                doctor_status, attempted = _send_paid_doctor_report_email(
                    order,
                    report,
                    _read_report_pdf(report.patient_pdf_path),
                    _read_report_pdf(report.doctor_pdf_path),
                    case,
                )
                audit.mark_report_sent(case, to_doctor=attempted, doctor_status=doctor_status)
                notice = "Doctor report email sent." if doctor_status == "SENT" else "Doctor report email failed."
            except OSError as exc:
                notice = f"Doctor report PDFs could not be read: {exc}"

    email_logs = list(EsPayEmailLog.objects.filter(order=order).order_by("-created_at")[:20]) if order else []
    patient_logs = [log for log in email_logs if log.email_type == EsPayEmailLog.EmailType.PATIENT_REPORT]
    doctor_logs = [log for log in email_logs if log.email_type == EsPayEmailLog.EmailType.DOCTOR_REPORT]
    latest_patient_log = patient_logs[0] if patient_logs else None
    latest_doctor_log = doctor_logs[0] if doctor_logs else None

    return render(
        request,
        "paid/workflow_report_delivery.html",
        {
            "case": case,
            "order": order,
            "submission": submission,
            "report": report,
            "notice": notice,
            "patient_email_form": patient_email_form,
            "latest_patient_log": latest_patient_log,
            "latest_doctor_log": latest_doctor_log,
            "latest_patient_status": _email_log_display_status(latest_patient_log),
            "latest_doctor_status": _email_log_display_status(latest_doctor_log),
            "patient_logs": patient_logs,
            "doctor_logs": doctor_logs,
            "deliveries": case.delivery_attempts.all().order_by("-created_at"),
            "report_tracking": getattr(case, "report_tracking", None),
            **JOURNEY_LOCKED_CONTEXT,
        },
    )
