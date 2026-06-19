from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, render
from django.utils.dateparse import parse_date

from .models import WorkflowCase, WorkflowPayment, WorkflowReport

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
