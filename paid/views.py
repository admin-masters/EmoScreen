import secrets
import json
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import escape
from django.utils import timezone
from django.db import transaction
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from content.models import RegisteredProfessional
from content.utils import normalize_phone, whatsapp_link
from content.views import _gate_google_and_email

from .forms import DemographicsForm, PaidPrescriptionForm, PatientEmailForm
from .models import EsCfgOption, EsCfgQuestion, EsCfgSection, EsPayEmailLog, EsPayOrder, EsPayRevenueSplit, EsPayTransaction, EsRepReport, EsSubAnswer, EsSubSubmission
from .services.mailer import _sendgrid_send_with_attachments, log_email
from .services.payment import RazorpayAdapter, RazorpayError
from .services.reporting import build_pdf_password, generate_and_store_reports
from .services.scoring import compute_submission_scores
from .services.tokens import build_order_token_payload, hash_token, sign_payload, unsign_payload
from .services import audit


JOURNEY_LOCKED_CONTEXT = {"hide_journey_nav": True}

PRICE_MAP = {
    "INR_499": 49900,
    "INR_100": 10000,
    "INR_20": 2000,
    "INR_1": 100,
    "INR_0": 0,
}


def _paid_order_is_final(order) -> bool:
    return (
        order.status == EsPayOrder.Status.SUBMITTED
        or EsSubSubmission.objects.filter(order=order, status=EsSubSubmission.Status.FINAL).exists()
    )


@require_http_methods(["GET", "POST"])
def prescribe_order(request, doctor_code):
    doctor = get_object_or_404(RegisteredProfessional, unique_doctor_code=doctor_code)
    gate = _gate_google_and_email(request, doctor, request.get_full_path())
    if gate is not None:
        return gate

    if request.method == "POST":
        form = PaidPrescriptionForm(request.POST)
        if form.is_valid():
            cfg_form = form.cleaned_data["form_code"]
            price_variant = form.cleaned_data["price_variant"]
            discount_paise = (form.cleaned_data.get("discount_rupees") or 0) * 100
            base_amount = PRICE_MAP[price_variant]
            final_amount = max(0, base_amount - discount_paise)

            order_code = secrets.token_hex(6).upper()
            order = EsPayOrder.objects.create(
                order_code=order_code,
                doctor=doctor,
                form=cfg_form,
                price_variant=price_variant,
                base_amount_paise=base_amount,
                discount_paise=discount_paise,
                final_amount_paise=final_amount,
                patient_name=form.cleaned_data["patient_name"],
                patient_whatsapp=normalize_phone(form.cleaned_data["patient_whatsapp"]),
                patient_email=form.cleaned_data.get("patient_email") or None,
                status=EsPayOrder.Status.PAYMENT_SKIPPED if final_amount == 0 else EsPayOrder.Status.PAYMENT_PENDING,
                link_token_hash="pending",
                link_expires_at=timezone.now() + timedelta(days=7),
                created_ip=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
            payload = build_order_token_payload(order, doctor_code)
            token = sign_payload(payload)
            order.link_token_hash = hash_token(token)
            order.status = EsPayOrder.Status.LINK_SENT
            order.save(update_fields=["link_token_hash", "status", "updated_at"])
            link = request.build_absolute_uri(
                reverse(
                    "paid:patient_entry",
                    args=[order.order_code, doctor.unique_doctor_code, order.form_id, order.final_amount_paise, token],
                )
            )
            try:
                audit.create_paid_case(
                    order=order,
                    request=request,
                    token=token,
                    source="paid_prescribe",
                    delivery_url=link,
                )
            except Exception as exc:
                print("Workflow audit error (paid prescribe):", exc)
            msg = (
                "Dear Parents,\n\n"
                f"I’m prescribing Emo Screen tool – {order.form.title}.\n\n"
                "To complete your order,\n"
                "CLICK HERE\n\n"
                f"{link}\n\n"
                "For any further queries or support, please send a WhatsApp message to +91-8297634553."
            )
            return render(request, "paid/prescribe_done.html", {"order": order, "form_link": link, "wa_link": whatsapp_link(order.patient_whatsapp, msg), "message": msg, "final_amount_rupees": order.final_amount_paise / 100, **JOURNEY_LOCKED_CONTEXT})
    else:
        form = PaidPrescriptionForm()

    return render(request, "paid/prescribe.html", {"doctor": doctor, "form": form, **JOURNEY_LOCKED_CONTEXT})


def orders_list(request, doctor_code):
    doctor = get_object_or_404(RegisteredProfessional, unique_doctor_code=doctor_code)
    gate = _gate_google_and_email(request, doctor, request.get_full_path())
    if gate is not None:
        return gate
    orders = EsPayOrder.objects.filter(doctor=doctor).order_by("-created_at")
    return render(request, "paid/orders_list.html", {"doctor": doctor, "orders": orders, **JOURNEY_LOCKED_CONTEXT})


def order_detail(request, doctor_code, order_code):
    doctor = get_object_or_404(RegisteredProfessional, unique_doctor_code=doctor_code)
    gate = _gate_google_and_email(request, doctor, request.get_full_path())
    if gate is not None:
        return gate
    order = get_object_or_404(EsPayOrder, doctor=doctor, order_code=order_code)
    return render(request, "paid/order_detail.html", {"order": order, "doctor": doctor, "final_amount_rupees": order.final_amount_paise / 100, **JOURNEY_LOCKED_CONTEXT})


@require_http_methods(["GET", "POST"])
def patient_entry(request, order_code, doctor_code, form_code, final_amount_paise, token):
    order = get_object_or_404(EsPayOrder, order_code=order_code, form_id=form_code)
    payload = unsign_payload(token)
    if payload["order_code"] != order_code or payload["doctor_code"] != doctor_code:
        raise Http404("Invalid token context")
    if order.link_token_hash != hash_token(token):
        raise Http404("Token mismatch")

    if _paid_order_is_final(order):
        return redirect("paid:patient_thank_you", order_code=order.order_code)

    workflow_case = audit.case_for_order(order)
    audit.mark_opened(workflow_case, request=request, message="Paid patient link opened")

    if request.method == "POST":
        form = PatientEmailForm(request.POST)
        if form.is_valid():
            order.patient_email = form.cleaned_data["patient_email"]
            order.save(update_fields=["patient_email", "updated_at"])
            audit.update_patient_contact(workflow_case, patient_email=order.patient_email, request=request)
            if order.final_amount_paise == 0 or order.status == EsPayOrder.Status.PAID:
                return redirect("paid:patient_form", order_code=order.order_code)
            return redirect("paid:patient_payment", order_code=order.order_code)
    else:
        form = PatientEmailForm(initial={"patient_email": order.patient_email})

    if not order.patient_email:
        return render(request, "paid/patient_entry.html", {"order": order, "email_form": form, "amount_path": final_amount_paise, "final_amount_rupees": order.final_amount_paise / 100, **JOURNEY_LOCKED_CONTEXT})
    if order.final_amount_paise == 0:
        return redirect("paid:patient_form", order_code=order.order_code)
    if order.status == EsPayOrder.Status.PAID:
        return redirect("paid:patient_form", order_code=order.order_code)
    return redirect("paid:patient_payment", order_code=order.order_code)


@require_http_methods(["GET", "POST"])
def patient_payment(request, order_code):
    order = get_object_or_404(EsPayOrder, order_code=order_code)
    if _paid_order_is_final(order):
        return redirect("paid:patient_thank_you", order_code=order.order_code)
    workflow_case = audit.case_for_order(order)

    if not order.patient_email:
        form = PatientEmailForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            order.patient_email = form.cleaned_data["patient_email"]
            order.save(update_fields=["patient_email", "updated_at"])
            audit.update_patient_contact(workflow_case, patient_email=order.patient_email, request=request)
            return redirect("paid:patient_payment", order_code=order.order_code)
        return render(
            request,
            "paid/patient_entry.html",
            {
                "order": order,
                "email_form": form,
                "amount_path": order.final_amount_paise,
                "final_amount_rupees": order.final_amount_paise / 100,
                "email_required_notice": "Please enter the patient email before continuing. This is where the patient report will be sent.",
                **JOURNEY_LOCKED_CONTEXT,
            },
        )

    if order.final_amount_paise <= 0:
        return redirect("paid:patient_form", order_code=order.order_code)
    if order.status == EsPayOrder.Status.PAID:
        return redirect("paid:patient_form", order_code=order.order_code)

    payment_mode = getattr(settings, "PAYMENT_GATEWAY", "dummy").lower()
    if payment_mode != "razorpay":
        tx = (
            EsPayTransaction.objects
            .filter(order=order, gateway="dummy")
            .exclude(status=EsPayTransaction.Status.FAILED)
            .order_by("-created_at")
            .first()
        )
        if not tx:
            tx = EsPayTransaction.objects.create(
                order=order,
                gateway="dummy",
                gateway_order_id=f"DUMMY_{order.order_code}",
                status=EsPayTransaction.Status.CREATED,
                amount_paise=order.final_amount_paise,
                currency="INR",
                raw_payload_json={"mode": "local_dummy"},
            )
        audit.mark_payment_pending(workflow_case, order, tx)

        if request.method == "POST":
            action = request.POST.get("dummy_payment_action", "success")
            if action == "fail":
                tx.status = EsPayTransaction.Status.FAILED
                tx.raw_payload_json = {"mode": "local_dummy", "action": "fail"}
                tx.save(update_fields=["status", "raw_payload_json", "updated_at"])
                audit.mark_payment_failed(workflow_case, order, tx, "Local dummy payment failure simulated.")
                return render(
                    request,
                    "paid/patient_payment.html",
                    {
                        "order": order,
                        "final_amount_rupees": order.final_amount_paise / 100,
                        "payment_error": "Dummy payment failure simulated. Retry with Complete Dummy Payment.",
                        "dummy_gateway": True,
                        "gateway_order_id": tx.gateway_order_id,
                        **JOURNEY_LOCKED_CONTEXT,
                    },
                )

            tx.status = EsPayTransaction.Status.SUCCESS
            tx.gateway_payment_id = f"dummy_pay_{secrets.token_hex(6)}"
            tx.gateway_signature = "local-dummy-signature"
            tx.raw_payload_json = {"mode": "local_dummy", "action": "success"}
            tx.save(update_fields=["status", "gateway_payment_id", "gateway_signature", "raw_payload_json", "updated_at"])
            order.status = EsPayOrder.Status.PAID
            order.paid_at = timezone.now()
            order.save(update_fields=["status", "paid_at", "updated_at"])
            _create_revenue_split(tx)
            audit.mark_payment_completed(workflow_case, order, tx)
            _send_assessment_link_email(order, request, workflow_case)
            return redirect("paid:patient_form", order_code=order.order_code)

        return render(
            request,
            "paid/patient_payment.html",
            {
                "order": order,
                "final_amount_rupees": order.final_amount_paise / 100,
                "dummy_gateway": True,
                "gateway_order_id": tx.gateway_order_id,
                **JOURNEY_LOCKED_CONTEXT,
            },
        )

    try:
        adapter = RazorpayAdapter()
    except RazorpayError as exc:
        audit.mark_payment_failed(workflow_case, order, reason=str(exc))
        return render(
            request,
            "paid/patient_payment.html",
            {
                "order": order,
                "final_amount_rupees": order.final_amount_paise / 100,
                "payment_error": str(exc),
                **JOURNEY_LOCKED_CONTEXT,
            },
        )

    tx = (
        EsPayTransaction.objects
        .filter(order=order)
        .exclude(status=EsPayTransaction.Status.FAILED)
        .order_by("-created_at")
        .first()
    )
    if not tx or not tx.gateway_order_id:
        gateway_order = adapter.create_order(
            receipt=order.order_code,
            amount_paise=order.final_amount_paise,
            notes={"order_code": order.order_code, "doctor_id": str(order.doctor_id)},
        )
        tx = EsPayTransaction.objects.create(
            order=order,
            gateway="razorpay",
            gateway_order_id=gateway_order.gateway_order_id,
            status=EsPayTransaction.Status.CREATED,
            amount_paise=order.final_amount_paise,
            currency=gateway_order.currency,
        )
    audit.mark_payment_pending(workflow_case, order, tx)

    if request.method == "POST":
        payload = {
            "razorpay_payment_id": request.POST.get("razorpay_payment_id"),
            "razorpay_order_id": request.POST.get("razorpay_order_id"),
            "razorpay_signature": request.POST.get("razorpay_signature"),
        }
        if payload["razorpay_order_id"] != tx.gateway_order_id:
            tx.status = EsPayTransaction.Status.FAILED
            tx.raw_payload_json = payload
            tx.save(update_fields=["status", "raw_payload_json", "updated_at"])
            audit.mark_payment_failed(workflow_case, order, tx, "Razorpay order mismatch.")
            return render(
                request,
                "paid/patient_payment.html",
                {
                    "order": order,
                    "final_amount_rupees": order.final_amount_paise / 100,
                    "payment_error": "Razorpay order mismatch. Please retry payment.",
                    "razorpay_key_id": adapter.public_key_id,
                    "razorpay_test_mode": not adapter.live_mode,
                    "gateway_order_id": tx.gateway_order_id,
                    **JOURNEY_LOCKED_CONTEXT,
                },
            )

        if adapter.verify_signature(payload):
            tx.status = EsPayTransaction.Status.SUCCESS
            tx.gateway_payment_id = payload["razorpay_payment_id"]
            tx.gateway_signature = payload["razorpay_signature"] or ""
            tx.raw_payload_json = payload
            tx.save(update_fields=["status", "gateway_payment_id", "gateway_signature", "raw_payload_json", "updated_at"])
            order.status = EsPayOrder.Status.PAID
            order.paid_at = timezone.now()
            order.save(update_fields=["status", "paid_at", "updated_at"])
            _create_revenue_split(tx)
            audit.mark_payment_completed(workflow_case, order, tx)
            _send_assessment_link_email(order, request, workflow_case)
            return redirect("paid:patient_form", order_code=order.order_code)

        tx.status = EsPayTransaction.Status.FAILED
        tx.raw_payload_json = payload
        tx.save(update_fields=["status", "raw_payload_json", "updated_at"])
        audit.mark_payment_failed(workflow_case, order, tx, "Razorpay signature verification failed.")

    return render(
        request,
        "paid/patient_payment.html",
        {
            "order": order,
            "final_amount_rupees": order.final_amount_paise / 100,
            "razorpay_key_id": adapter.public_key_id,
            "razorpay_test_mode": not adapter.live_mode,
            "gateway_order_id": tx.gateway_order_id,
            **JOURNEY_LOCKED_CONTEXT,
        },
    )


@csrf_exempt
@require_http_methods(["POST"])
def razorpay_webhook(request):
    try:
        adapter = RazorpayAdapter()
    except RazorpayError as exc:
        return HttpResponseBadRequest(str(exc))

    signature = request.headers.get("X-Razorpay-Signature", "")
    if not adapter.verify_webhook_signature(request.body, signature):
        return HttpResponseBadRequest("Invalid webhook signature")

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    event = payload.get("event", "")
    payload_root = payload.get("payload", {})
    payment_entity = payload_root.get("payment", {}).get("entity", {})
    order_entity = payload_root.get("order", {}).get("entity", {})
    gateway_order_id = payment_entity.get("order_id") or order_entity.get("id", "")
    payment_id = payment_entity.get("id", "")

    tx = EsPayTransaction.objects.filter(gateway_order_id=gateway_order_id).order_by("-created_at").first()
    if not tx:
        return JsonResponse({"ok": True, "ignored": "transaction_not_found"})

    tx.gateway_payment_id = payment_id or tx.gateway_payment_id
    tx.raw_payload_json = payload
    if event in {"payment.captured", "order.paid"}:
        tx.status = EsPayTransaction.Status.SUCCESS
    elif event in {"payment.failed"}:
        tx.status = EsPayTransaction.Status.FAILED
    tx.save(update_fields=["gateway_payment_id", "raw_payload_json", "status", "updated_at"])

    if tx.status == EsPayTransaction.Status.SUCCESS:
        order = tx.order
        if order.status != EsPayOrder.Status.PAID:
            order.status = EsPayOrder.Status.PAID
            order.paid_at = timezone.now()
            order.save(update_fields=["status", "paid_at", "updated_at"])
        _create_revenue_split(tx)
        workflow_case = audit.case_for_order(order)
        audit.mark_payment_completed(workflow_case, order, tx)
        _send_assessment_link_email(order, request, workflow_case)
    elif tx.status == EsPayTransaction.Status.FAILED:
        audit.mark_payment_failed(audit.case_for_order(tx.order), tx.order, tx, "Razorpay webhook marked payment failed.")

    return JsonResponse({"ok": True})


@require_http_methods(["GET", "POST"])
def patient_form(request, order_code):
    order = get_object_or_404(EsPayOrder, order_code=order_code)
    if _paid_order_is_final(order):
        return redirect("paid:patient_thank_you", order_code=order.order_code)
    if not order.patient_email:
        return redirect("paid:patient_payment", order_code=order.order_code)
    if order.final_amount_paise > 0 and order.status != EsPayOrder.Status.PAID:
        return redirect("paid:patient_payment", order_code=order.order_code)
    workflow_case = audit.case_for_order(order)
    audit.mark_opened(workflow_case, request=request, message="Paid assessment form opened")

    submission, _ = EsSubSubmission.objects.get_or_create(
        order=order,
        defaults={
            "form": order.form,
            "config_version": order.form.version,
            "child_name": order.patient_name,
        },
    )
    if submission.status == EsSubSubmission.Status.FINAL:
        return redirect("paid:patient_thank_you", order_code=order.order_code)

    section_order_map = {
        s.section_code: s.display_order
        for s in EsCfgSection.objects.filter(form=order.form)
    }
    all_questions = list(
        EsCfgQuestion.objects.filter(form=order.form)
        .select_related("option_set", "section")
    )
    questions = [q for q in all_questions if not _is_basic_detail_question(q)]
    questions.sort(key=lambda q: (
        section_order_map.get(q.section_id, 9999),
        q.question_order if q.question_order is not None else 9999,
        q.global_order if q.global_order is not None else 9999,
    ))
    option_set_codes = {q.option_set_id for q in questions if q.option_set_id}
    options_by_set = {}
    for opt in EsCfgOption.objects.filter(option_set_id__in=option_set_codes).order_by("option_order"):
        options_by_set.setdefault(opt.option_set_id, []).append(opt)

    demo_form = DemographicsForm(request.POST or None, initial={
        "child_name": submission.child_name,
        "child_dob": submission.child_dob,
        "assessment_date": submission.assessment_date,
        "gender": submission.gender,
        "completed_by": submission.completed_by,
        "consent_given": submission.consent_given,
    })

    if request.method == "POST" and demo_form.is_valid():
        _save_draft(submission, demo_form.cleaned_data, request.POST, questions, options_by_set)
        audit.attach_paid_submission(workflow_case, submission)
        audit.mark_in_progress(
            workflow_case,
            request=request,
            completed=EsSubAnswer.objects.filter(submission=submission).count(),
            total=len(questions),
        )
        return redirect("paid:patient_review", order_code=order.order_code)

    audit.attach_paid_submission(workflow_case, submission)
    audit.mark_in_progress(
        workflow_case,
        request=request,
        completed=EsSubAnswer.objects.filter(submission=submission).count(),
        total=len(questions),
    )

    answers = {a.question_id: str(a.value_json) for a in EsSubAnswer.objects.filter(submission=submission)}
    question_rows = []
    for q in questions:
        opts = options_by_set.get(q.option_set_id, [])
        question_rows.append({"question": q, "options": opts, "selected": answers.get(q.question_code, "")})

    return render(
        request,
        "paid/patient_form.html",
        {
            "order": order,
            "submission": submission,
            "demo_form": demo_form,
            "question_rows": question_rows,
            "final_amount_rupees": order.final_amount_paise / 100,
            **JOURNEY_LOCKED_CONTEXT,
        },
    )


def patient_review(request, order_code):
    order = get_object_or_404(EsPayOrder, order_code=order_code)
    submission = get_object_or_404(EsSubSubmission, order=order)
    if submission.status == EsSubSubmission.Status.FINAL:
        return redirect("paid:patient_thank_you", order_code=order.order_code)
    section_order_map = {
        s.section_code: s.display_order
        for s in EsCfgSection.objects.filter(form=order.form)
    }
    all_questions = list(
        EsCfgQuestion.objects.filter(form=order.form)
        .select_related("option_set", "section")
    )
    questions = [q for q in all_questions if not _is_basic_detail_question(q)]
    questions.sort(key=lambda q: (
        section_order_map.get(q.section_id, 9999),
        q.question_order if q.question_order is not None else 9999,
        q.global_order if q.global_order is not None else 9999,
    ))
    option_set_codes = {q.option_set_id for q in questions if q.option_set_id}
    option_labels = {
        opt.option_code: opt.label
        for opt in EsCfgOption.objects.filter(option_set_id__in=option_set_codes)
    }
    answers = {a.question_id: str(a.value_json) for a in EsSubAnswer.objects.filter(submission=submission)}
    review_rows = []
    for q in questions:
        selected = answers.get(q.question_code, "")
        review_rows.append({
            "question_text": q.question_text,
            "answer_text": option_labels.get(selected, selected),
        })
    return render(request, "paid/patient_review.html", {"order": order, "submission": submission, "review_rows": review_rows, **JOURNEY_LOCKED_CONTEXT})


@require_http_methods(["POST"])
@transaction.atomic
def patient_submit_final(request, order_code):
    order = get_object_or_404(EsPayOrder, order_code=order_code)
    submission = get_object_or_404(EsSubSubmission, order=order)
    workflow_case = audit.case_for_order(order)
    if submission.status == EsSubSubmission.Status.FINAL:
        return redirect("paid:patient_thank_you", order_code=order.order_code)

    compute_submission_scores(submission)
    submission.status = EsSubSubmission.Status.FINAL
    submission.save(update_fields=["status", "updated_at"])
    order.status = EsPayOrder.Status.SUBMITTED
    order.submitted_at = timezone.now()
    order.save(update_fields=["status", "submitted_at", "updated_at"])
    audit.mark_paid_submitted(workflow_case, submission)
    audit.mark_report_processing(workflow_case)

    try:
        report, patient_pdf, doctor_pdf = generate_and_store_reports(submission)
    except Exception as exc:
        audit.mark_report_failed(workflow_case, str(exc))
        raise
    audit.mark_report_generated(workflow_case, report)
    _send_report_emails(order, report, patient_pdf, doctor_pdf, workflow_case=workflow_case)

    return redirect("paid:patient_thank_you", order_code=order.order_code)


def download_report(request, order_code, kind):
    order = get_object_or_404(EsPayOrder, order_code=order_code)
    submission = get_object_or_404(EsSubSubmission, order=order)

    if kind == "doctor" and not getattr(request.user, "is_staff", False):
        gate = _gate_google_and_email(request, order.doctor, request.get_full_path())
        if gate is not None:
            return gate

    # Always regenerate from latest code/config before download so stale PDFs are replaced.
    generate_and_store_reports(submission)
    report = get_object_or_404(EsRepReport, submission=submission)
    audit.mark_report_generated(audit.case_for_order(order), report)

    if kind == "patient":
        fpath = report.patient_pdf_path
        filename = f"{order.order_code}_patient_report.pdf"
    elif kind == "doctor":
        fpath = report.doctor_pdf_path
        filename = f"{order.order_code}_doctor_report.pdf"
    else:
        raise Http404("Unknown report type")

    audit.mark_download(audit.case_for_order(order), kind)
    return FileResponse(open(fpath, "rb"), as_attachment=True, filename=filename)


def patient_thank_you(request, order_code):
    order = get_object_or_404(EsPayOrder, order_code=order_code)
    submission = EsSubSubmission.objects.filter(order=order).first()
    report = EsRepReport.objects.filter(submission=submission).first() if submission else None

    patient_password = ""
    if submission and report:
        patient_password = build_pdf_password(submission.child_name or order.patient_name, order.patient_whatsapp)

    return render(
        request,
        "paid/patient_thank_you.html",
        {
            "order": order,
            "submission": submission,
            "report": report,
            "patient_password": patient_password,
            **JOURNEY_LOCKED_CONTEXT,
        },
    )


def _save_draft(submission, demo_data, posted_data, questions, options_by_set):
    submission.child_name = demo_data["child_name"]
    submission.child_dob = demo_data["child_dob"]
    submission.assessment_date = demo_data["assessment_date"]
    submission.gender = demo_data["gender"]
    submission.completed_by = demo_data["completed_by"]
    submission.consent_given = demo_data["consent_given"]
    submission.status = EsSubSubmission.Status.DRAFT
    submission.save()

    for q in questions:
        key = f"q_{q.question_code}"
        raw_val = posted_data.get(key)
        if raw_val is None:
            continue

        score_val = None
        if q.option_set_id:
            option_lookup = {opt.option_code: opt for opt in options_by_set.get(q.option_set_id, [])}
            selected_option = option_lookup.get(raw_val)
            if q.is_scored and selected_option and selected_option.score_value is not None:
                score_val = Decimal(str(selected_option.score_value))
        elif q.is_scored and raw_val not in ("", None):
            score_val = Decimal(str(raw_val))

        EsSubAnswer.objects.update_or_create(
            submission=submission,
            question=q,
            defaults={"value_json": raw_val, "score_value": score_val},
        )


def _is_basic_detail_question(question):
    """Filter sheet questions that duplicate demographic header fields."""
    tokens = " ".join([
        (question.question_key or ""),
        (question.legacy_field_name or ""),
        (question.question_text or ""),
    ]).lower().replace("’", "'")
    collapsed = " ".join(tokens.split())

    basic_markers = (
        "dob",
        "date of birth",
        "date",
        "child name",
        "child's name",
        "completed by",
        "gender",
        "consent",
        "assessment date",
        "i hereby give consent",
    )
    if collapsed in {"date", "child name", "child's name", "completed by", "gender", "consent"}:
        return True
    return any(marker in collapsed for marker in basic_markers)


def _send_assessment_link_email(order, request, workflow_case=None):
    if not order.patient_email:
        return None

    existing_success = EsPayEmailLog.objects.filter(
        order=order,
        email_type=EsPayEmailLog.EmailType.PAYMENT_LINK,
        status=EsPayEmailLog.Status.SENT,
    ).exists()
    if existing_success:
        return None

    link = request.build_absolute_uri(reverse("paid:patient_form", args=[order.order_code]))
    subject = "EmoScreen Assessment Link"
    patient_name = escape(order.patient_name or "Parent")
    ok, meta = _sendgrid_send_with_attachments(
        order.patient_email,
        subject,
        (
            f"<p>Dear {patient_name}, Your doctor has prescribed EmoScreen service for you.</p>"
            f"<p>Please complete the assessment by filling up the form at this link: "
            f"<a href=\"{link}\">{link}</a></p>"
            "<p>If you need help to understand any of the questions please take help from your doctor.</p>"
            "<p>For any further queries or support, please send a WhatsApp message to: +91-8297634553.</p>"
        ),
        [],
    )
    delivery_status = _delivery_status(ok, meta)
    email_log = log_email(
        order,
        "PAYMENT_LINK",
        order.patient_email,
        subject,
        status=delivery_status,
        error_text="" if ok else str(meta),
        sendgrid_message_id=meta if ok else "",
    )
    if workflow_case:
        audit.record_delivery(
            workflow_case,
            channel="EMAIL",
            recipient=order.patient_email,
            subject=subject,
            status=delivery_status,
            provider=_email_provider(),
            provider_message_id=meta if ok else "",
            error_text="" if ok else str(meta),
            metadata={"link": link, "email_type": "PAYMENT_LINK"},
            email_log=email_log,
        )
    return email_log


def _delivery_status(ok, meta):
    return "SENT" if ok else "FAILED"


def _email_log_display_status(log):
    if not log:
        return ""
    if log.status == EsPayEmailLog.Status.QUEUED and not log.error_text:
        return "SENT"
    return log.status


def _email_provider():
    return "sendgrid" if getattr(settings, "SENDGRID_API_KEY", "") else "local-email-backend"


def _read_report_pdf(path):
    with open(path, "rb") as handle:
        return handle.read()


def _paid_child_name(order, report=None):
    submission = getattr(report, "submission", None)
    return (getattr(submission, "child_name", "") or order.patient_name or "the child").strip()


def _support_phone_display():
    return getattr(settings, "SUPPORT_PHONE_DISPLAY", "+91-9321450803")


def _paid_patient_report_body(order, report):
    child_name = escape(_paid_child_name(order, report))
    support_phone = escape(_support_phone_display())
    return (
        "<p>Dear Parent, please find the attached EmoScreen report.</p>"
        f"<p>Please find the attached EmoScreen report below for {child_name}.<br>"
        "Please connect with your doctor to know more.<br>"
        f"For any further queries or support, please send a WhatsApp message to - {support_phone}.</p>"
        "<p>The document is password protected. To open it, use the first 4 letters of your child's name "
        "and the last 4 digits of the phone number as the password.<br>"
        "For example, if your child's name is 'Emily' and their phone number is '9876543210', "
        "the password will be 'Emil3210'.</p>"
    )


def _paid_doctor_report_body(order, report):
    child_name = escape(_paid_child_name(order, report))
    support_phone = escape(_support_phone_display())
    return (
        "<p>Dear Doctor, please find the attached EmoScreen report.</p>"
        f"<p>Please find the attached EmoScreen report below for {child_name}.<br>"
        "Please connect with your patient to know more.<br>"
        f"For any further queries or support, please send a WhatsApp message to - {support_phone}.</p>"
        "<p>The documents are password protected. To open them:<br>"
        "For the doctor report, use the first 4 letters of your email and the last 4 digits of your phone number as the password.<br>"
        "For example, if your email is 'johnsmith@example.com' and your phone number is '9876543210', your password will be 'john3210'.<br>"
        "For the patient report, use the first 4 letters of the patient's name and the last 4 digits of the patient's phone number as the password.<br>"
        "For example, if the patient's name is 'Emily' and their phone number is '9876543210', the password will be 'Emil3210'.</p>"
    )


def _send_paid_patient_report_email(order, report, patient_pdf: bytes, workflow_case=None):
    if not order.patient_email:
        return "", False

    subject = "Patient Report for EmoScreen"
    ok, meta = _sendgrid_send_with_attachments(
        order.patient_email,
        subject,
        _paid_patient_report_body(order, report),
        [("patient_report.pdf", patient_pdf)],
    )
    delivery_status = _delivery_status(ok, meta)
    email_log = log_email(
        order,
        "PATIENT_REPORT",
        order.patient_email,
        subject,
        status=delivery_status,
        error_text="" if ok else str(meta),
        sendgrid_message_id=meta if ok else "",
    )
    if workflow_case:
        audit.record_delivery(
            workflow_case,
            channel="EMAIL",
            recipient=order.patient_email,
            subject=subject,
            status=delivery_status,
            provider=_email_provider(),
            provider_message_id=meta if ok else "",
            error_text="" if ok else str(meta),
            metadata={"email_type": "PATIENT_REPORT"},
            email_log=email_log,
        )
    if ok and report:
        report.emailed_to_parent_at = timezone.now()
        report.save(update_fields=["emailed_to_parent_at"])
    return delivery_status, True


def _send_paid_doctor_report_email(order, report, patient_pdf: bytes, doctor_pdf: bytes, workflow_case=None):
    doctor_email = order.doctor.email
    if not doctor_email:
        return "", False

    subject = "Doctor Report for EmoScreen"
    ok, meta = _sendgrid_send_with_attachments(
        doctor_email,
        subject,
        _paid_doctor_report_body(order, report),
        [("doctor_report.pdf", doctor_pdf), ("patient_report.pdf", patient_pdf)],
    )
    delivery_status = _delivery_status(ok, meta)
    email_log = log_email(
        order,
        "DOCTOR_REPORT",
        doctor_email,
        subject,
        status=delivery_status,
        error_text="" if ok else str(meta),
        sendgrid_message_id=meta if ok else "",
    )
    if workflow_case:
        audit.record_delivery(
            workflow_case,
            channel="EMAIL",
            recipient=doctor_email,
            subject=subject,
            status=delivery_status,
            provider=_email_provider(),
            provider_message_id=meta if ok else "",
            error_text="" if ok else str(meta),
            metadata={"email_type": "DOCTOR_REPORT"},
            email_log=email_log,
        )
    if ok and report:
        report.emailed_to_doctor_at = timezone.now()
        report.save(update_fields=["emailed_to_doctor_at"])
    return delivery_status, True


def _send_report_emails(order, report, patient_pdf: bytes, doctor_pdf: bytes, workflow_case=None):
    patient_status = ""
    doctor_status = ""
    attempted_patient = False
    attempted_doctor = False

    patient_status, attempted_patient = _send_paid_patient_report_email(order, report, patient_pdf, workflow_case)
    doctor_status, attempted_doctor = _send_paid_doctor_report_email(order, report, patient_pdf, doctor_pdf, workflow_case)
    audit.mark_report_sent(
        workflow_case,
        to_patient=attempted_patient,
        to_doctor=attempted_doctor,
        patient_status=patient_status,
        doctor_status=doctor_status,
    )


def _create_revenue_split(transaction):
    if EsPayRevenueSplit.objects.filter(transaction=transaction).exists():
        return
    half = int(transaction.amount_paise / 2)
    EsPayRevenueSplit.objects.create(
        transaction=transaction,
        party=EsPayRevenueSplit.Party.INDITECH,
        percent=50,
        amount_paise=half,
    )
    EsPayRevenueSplit.objects.create(
        transaction=transaction,
        party=EsPayRevenueSplit.Party.EQUIPOISE,
        percent=50,
        amount_paise=transaction.amount_paise - half,
    )
