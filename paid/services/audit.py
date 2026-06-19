import hashlib
import secrets
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

from content.models import Question, SubmissionAnswer
from paid.models import (
    EsCfgQuestion,
    EsPayOrder,
    EsPayTransaction,
    EsRepReport,
    EsSubAnswer,
    EsSubSubmission,
    WorkflowCase,
    WorkflowDeliveryAttempt,
    WorkflowEvent,
    WorkflowPayment,
    WorkflowReport,
)


SESSION_CASE_PREFIX = "workflow_case_"


def _percent(completed: int, total: int) -> Decimal:
    if not total:
        return Decimal("0.00")
    value = (Decimal(completed) * Decimal("100")) / Decimal(total)
    return value.quantize(Decimal("0.01"))


def token_hash(token: str | None) -> str:
    if not token:
        return ""
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


def _case_code() -> str:
    return "WF" + secrets.token_hex(6).upper()


def _doctor_name(doctor) -> str:
    return " ".join(
        part for part in [doctor.salutation, doctor.first_name, doctor.last_name] if part
    ).strip()


def _request_meta(request) -> dict:
    if not request:
        return {"ip": None, "ua": "", "actor": "", "actor_type": WorkflowEvent.ActorType.SYSTEM}

    user = getattr(request, "user", None)
    actor = ""
    actor_type = WorkflowEvent.ActorType.SYSTEM
    if user and getattr(user, "is_authenticated", False):
        actor = getattr(user, "email", "") or getattr(user, "username", "")
        actor_type = WorkflowEvent.ActorType.DOCTOR

    return {
        "ip": request.META.get("REMOTE_ADDR"),
        "ua": request.META.get("HTTP_USER_AGENT", ""),
        "actor": actor,
        "actor_type": actor_type,
    }


def _set_session_case(request, doctor_code: str, case: WorkflowCase):
    if request:
        request.session[f"{SESSION_CASE_PREFIX}{doctor_code}"] = case.case_code


def get_session_case(request, doctor_code: str) -> WorkflowCase | None:
    if not request:
        return None
    case_code = request.session.get(f"{SESSION_CASE_PREFIX}{doctor_code}")
    if not case_code:
        return None
    return WorkflowCase.objects.filter(case_code=case_code).first()


def _event(
    case: WorkflowCase,
    event_type: str,
    *,
    stage: str = "",
    actor_type: str = WorkflowEvent.ActorType.SYSTEM,
    actor_identifier: str = "",
    message: str = "",
    metadata: dict | None = None,
    failure_reason: str = "",
    status_to: str = "",
):
    status_from = case.current_status
    WorkflowEvent.objects.create(
        case=case,
        event_type=event_type,
        stage=stage,
        status_from=status_from,
        status_to=status_to or "",
        actor_type=actor_type,
        actor_identifier=actor_identifier or "",
        message=message or "",
        failure_reason=failure_reason or "",
        metadata_json=metadata or {},
    )
    case.last_event_at = timezone.now()
    case.save(update_fields=["last_event_at", "updated_at"])


def transition(
    case: WorkflowCase,
    status: str,
    event_type: str,
    *,
    stage: str = "",
    actor_type: str = WorkflowEvent.ActorType.SYSTEM,
    actor_identifier: str = "",
    message: str = "",
    metadata: dict | None = None,
    failure_reason: str = "",
):
    now = timezone.now()
    status_from = case.current_status
    case.current_status = status
    case.last_event_at = now

    status_time_fields = {
        WorkflowCase.Status.SENT: "sent_at",
        WorkflowCase.Status.DELIVERED: "delivered_at",
        WorkflowCase.Status.OPENED: "opened_at",
        WorkflowCase.Status.PAYMENT_COMPLETED: "payment_completed_at",
        WorkflowCase.Status.IN_PROGRESS: "in_progress_at",
        WorkflowCase.Status.SUBMITTED: "submitted_at",
        WorkflowCase.Status.REPORT_GENERATED: "report_generated_at",
        WorkflowCase.Status.REPORT_SENT: "report_sent_at",
        WorkflowCase.Status.COMPLETED: "completed_at",
        WorkflowCase.Status.FAILED: "failed_at",
    }
    field = status_time_fields.get(status)
    update_fields = ["current_status", "last_event_at", "updated_at"]
    if field and not getattr(case, field):
        setattr(case, field, now)
        update_fields.append(field)
    if status == WorkflowCase.Status.FAILED:
        case.failure_stage = stage
        case.failure_reason = failure_reason or message
        update_fields.extend(["failure_stage", "failure_reason"])
    case.save(update_fields=update_fields)

    WorkflowEvent.objects.create(
        case=case,
        event_type=event_type,
        stage=stage,
        status_from=status_from,
        status_to=status,
        actor_type=actor_type,
        actor_identifier=actor_identifier or "",
        message=message or "",
        failure_reason=failure_reason or "",
        metadata_json=metadata or {},
    )
    return case


def record_delivery(
    case: WorkflowCase,
    *,
    channel: str,
    recipient: str,
    status: str,
    subject: str = "",
    provider: str = "",
    provider_message_id: str = "",
    error_text: str = "",
    metadata: dict | None = None,
    email_log=None,
):
    now = timezone.now()
    kwargs = {}
    if status in {WorkflowDeliveryAttempt.Status.SENT, WorkflowDeliveryAttempt.Status.SIMULATED}:
        kwargs["sent_at"] = now
    if status == WorkflowDeliveryAttempt.Status.DELIVERED:
        kwargs["delivered_at"] = now
    if status == WorkflowDeliveryAttempt.Status.OPENED:
        kwargs["opened_at"] = now
    attempt = WorkflowDeliveryAttempt.objects.create(
        case=case,
        channel=channel,
        recipient=recipient or "",
        subject=subject or "",
        status=status,
        provider=provider or "",
        provider_message_id=provider_message_id or "",
        error_text=error_text or "",
        metadata_json=metadata or {},
        email_log=email_log,
        **kwargs,
    )
    _event(
        case,
        "DELIVERY_ATTEMPT_RECORDED",
        stage="DELIVERY",
        message=f"{channel} delivery {status}",
        metadata={"attempt_id": attempt.id, "recipient": recipient, **(metadata or {})},
    )
    return attempt


def create_legacy_case(
    *,
    doctor,
    patient_whatsapp: str,
    language: str = "",
    request=None,
    token: str | None = None,
    patient_name: str = "",
    patient_email: str = "",
    source: str = "",
    delivery_url: str = "",
):
    access_hash = token_hash(token)
    if access_hash:
        existing = WorkflowCase.objects.filter(access_token_hash=access_hash).first()
        if existing:
            _set_session_case(request, doctor.unique_doctor_code, existing)
            return existing

    meta = _request_meta(request)
    case = WorkflowCase.objects.create(
        case_code=_case_code(),
        doctor=doctor,
        doctor_name_snapshot=_doctor_name(doctor),
        patient_name=patient_name or "",
        patient_whatsapp=patient_whatsapp or "",
        patient_email=patient_email or None,
        form_family=WorkflowCase.FormFamily.LEGACY if doctor.unique_doctor_code != settings.PUBLIC_DOCTOR_CODE else WorkflowCase.FormFamily.SELF,
        form_code="behavioral",
        form_title="Behavioral and Emotional Red Flags",
        form_version="legacy",
        language=language or "",
        is_paid=False,
        amount_paise=0,
        payment_status=WorkflowCase.PaymentStatus.NOT_REQUIRED,
        access_token_hash=access_hash,
        source=source or "legacy",
        created_by_user_email=meta["actor"] or None,
        created_ip=meta["ip"],
        user_agent=meta["ua"],
        total_questions=Question.objects.filter(active=True).count(),
        metadata_json={"delivery_url": delivery_url} if delivery_url else {},
    )
    WorkflowPayment.objects.create(
        case=case,
        is_required=False,
        amount_paise=0,
        status=WorkflowPayment.Status.NOT_REQUIRED,
    )
    WorkflowReport.objects.create(case=case)
    _event(
        case,
        "FORM_CREATED",
        stage="FORM_CREATION",
        actor_type=meta["actor_type"],
        actor_identifier=meta["actor"],
        message="Legacy form case created",
        metadata={"source": source, "language": language},
    )
    if delivery_url:
        transition(
            case,
            WorkflowCase.Status.SENT,
            "FORM_SENT",
            stage="DELIVERY",
            actor_type=meta["actor_type"],
            actor_identifier=meta["actor"],
            message="Legacy screening link generated for WhatsApp",
            metadata={"delivery_url": delivery_url},
        )
        record_delivery(
            case,
            channel=WorkflowDeliveryAttempt.Channel.WHATSAPP,
            recipient=patient_whatsapp,
            status=WorkflowDeliveryAttempt.Status.SENT,
            provider="wa.me",
            metadata={"url": delivery_url, "source": source},
        )
    _set_session_case(request, doctor.unique_doctor_code, case)
    return case


def create_paid_case(*, order: EsPayOrder, request=None, token: str | None = None, source: str = "", delivery_url: str = ""):
    existing = WorkflowCase.objects.filter(order=order).first()
    if existing:
        return existing

    meta = _request_meta(request)
    payment_status = (
        WorkflowCase.PaymentStatus.PENDING
        if order.final_amount_paise > 0
        else WorkflowCase.PaymentStatus.SKIPPED
    )
    case = WorkflowCase.objects.create(
        case_code=_case_code(),
        doctor=order.doctor,
        doctor_name_snapshot=_doctor_name(order.doctor),
        patient_name=order.patient_name,
        patient_whatsapp=order.patient_whatsapp,
        patient_email=order.patient_email,
        form_family=WorkflowCase.FormFamily.PAID,
        form_code=order.form_id,
        form_title=order.form.title,
        form_version=order.form.version,
        language=getattr(order.form, "language", "en") or "en",
        is_paid=order.final_amount_paise > 0,
        amount_paise=order.final_amount_paise,
        payment_status=payment_status,
        current_status=WorkflowCase.Status.CREATED,
        access_token_hash=token_hash(token),
        source=source or "paid",
        created_by_user_email=meta["actor"] or None,
        created_ip=order.created_ip or meta["ip"],
        user_agent=order.user_agent or meta["ua"],
        order=order,
        total_questions=EsCfgQuestion.objects.filter(form=order.form).count(),
        metadata_json={"delivery_url": delivery_url} if delivery_url else {},
    )
    WorkflowPayment.objects.create(
        case=case,
        order=order,
        is_required=order.final_amount_paise > 0,
        amount_paise=order.final_amount_paise,
        status=WorkflowPayment.Status.PENDING if order.final_amount_paise > 0 else WorkflowPayment.Status.SKIPPED,
        gateway="dummy" if order.final_amount_paise > 0 else "",
    )
    WorkflowReport.objects.create(case=case)
    _event(
        case,
        "FORM_CREATED",
        stage="FORM_CREATION",
        actor_type=meta["actor_type"],
        actor_identifier=meta["actor"],
        message="Paid form order created",
        metadata={"order_code": order.order_code, "source": source},
    )
    if delivery_url:
        transition(
            case,
            WorkflowCase.Status.SENT,
            "FORM_SENT",
            stage="DELIVERY",
            actor_type=meta["actor_type"],
            actor_identifier=meta["actor"],
            message="Paid form link generated for WhatsApp",
            metadata={"delivery_url": delivery_url, "order_code": order.order_code},
        )
        record_delivery(
            case,
            channel=WorkflowDeliveryAttempt.Channel.WHATSAPP,
            recipient=order.patient_whatsapp,
            status=WorkflowDeliveryAttempt.Status.SENT,
            provider="wa.me",
            metadata={"url": delivery_url, "source": source},
        )
    return case


def case_for_order(order: EsPayOrder) -> WorkflowCase:
    case = WorkflowCase.objects.filter(order=order).first()
    if case:
        return case
    return create_paid_case(order=order, source="backfill")


def case_for_token(token: str) -> WorkflowCase | None:
    access_hash = token_hash(token)
    if not access_hash:
        return None
    return WorkflowCase.objects.filter(access_token_hash=access_hash).first()


def mark_opened(case: WorkflowCase | None, *, request=None, actor_type=WorkflowEvent.ActorType.PATIENT, message="Form link opened"):
    if not case:
        return None
    meta = _request_meta(request)
    actor = meta["actor"] if actor_type != WorkflowEvent.ActorType.PATIENT else ""
    if case.current_status in {WorkflowCase.Status.CREATED, WorkflowCase.Status.SENT, WorkflowCase.Status.DELIVERED, WorkflowCase.Status.PAYMENT_PENDING}:
        transition(
            case,
            WorkflowCase.Status.OPENED,
            "FORM_OPENED",
            stage="FORM_OPEN",
            actor_type=actor_type,
            actor_identifier=actor,
            message=message,
            metadata={"path": getattr(request, "path", "") if request else ""},
        )
    else:
        _event(case, "FORM_REOPENED", stage="FORM_OPEN", actor_type=actor_type, actor_identifier=actor, message=message)
    return case


def mark_verified(case: WorkflowCase | None, request=None):
    if not case:
        return None
    _event(case, "PATIENT_VERIFIED", stage="VERIFY", actor_type=WorkflowEvent.ActorType.PATIENT, message="Parent phone verified")
    return case


def update_patient_contact(case: WorkflowCase | None, *, patient_name="", patient_whatsapp="", patient_email="", request=None):
    if not case:
        return None
    update_fields = ["updated_at"]
    if patient_name and patient_name != case.patient_name:
        case.patient_name = patient_name
        update_fields.append("patient_name")
    if patient_whatsapp and patient_whatsapp != case.patient_whatsapp:
        case.patient_whatsapp = patient_whatsapp
        update_fields.append("patient_whatsapp")
    if patient_email and patient_email != case.patient_email:
        case.patient_email = patient_email
        update_fields.append("patient_email")
    if len(update_fields) > 1:
        case.save(update_fields=update_fields)
        _event(
            case,
            "PATIENT_DETAILS_UPDATED",
            stage="PATIENT_DETAILS",
            actor_type=WorkflowEvent.ActorType.PATIENT,
            message="Patient contact details updated",
            metadata={"path": getattr(request, "path", "") if request else ""},
        )
    return case


def mark_in_progress(case: WorkflowCase | None, *, request=None, completed: int = 0, total: int = 0):
    if not case:
        return None
    if total:
        case.total_questions = total
        case.completed_questions = completed
        case.completion_percent = _percent(completed, total)
        case.save(update_fields=["total_questions", "completed_questions", "completion_percent", "updated_at"])
    if case.current_status not in {WorkflowCase.Status.SUBMITTED, WorkflowCase.Status.REPORT_GENERATED, WorkflowCase.Status.REPORT_SENT, WorkflowCase.Status.COMPLETED}:
        transition(case, WorkflowCase.Status.IN_PROGRESS, "FORM_STARTED", stage="PATIENT_COMPLETION", actor_type=WorkflowEvent.ActorType.PATIENT)
    return case


def attach_legacy_submission(case: WorkflowCase | None, submission, *, patient_name="", patient_email=""):
    if not case:
        return None
    case.legacy_submission = submission
    case.patient_name = patient_name or case.patient_name
    case.patient_email = patient_email or case.patient_email
    answer_count = SubmissionAnswer.objects.filter(submission=submission).count()
    case.completed_questions = answer_count or case.total_questions
    case.completion_percent = Decimal("100.00")
    case.save(update_fields=["legacy_submission", "patient_name", "patient_email", "completed_questions", "completion_percent", "updated_at"])
    report_track, _ = WorkflowReport.objects.get_or_create(case=case)
    report_track.legacy_submission = submission
    report_track.status = WorkflowReport.Status.COMPLETED
    report_track.generated_at = timezone.now()
    report_track.save(update_fields=["legacy_submission", "status", "generated_at", "updated_at"])
    transition(case, WorkflowCase.Status.SUBMITTED, "FORM_SUBMITTED", stage="PATIENT_COMPLETION", actor_type=WorkflowEvent.ActorType.PATIENT, metadata={"report_code": submission.report_code})
    transition(case, WorkflowCase.Status.REPORT_GENERATED, "REPORT_GENERATED", stage="REPORT_GENERATION", metadata={"report_code": submission.report_code})
    return case


def attach_paid_submission(case: WorkflowCase | None, submission: EsSubSubmission):
    if not case:
        return None
    answer_count = EsSubAnswer.objects.filter(submission=submission).count()
    total = case.total_questions or EsCfgQuestion.objects.filter(form=submission.form).count()
    case.paid_submission = submission
    case.patient_name = submission.child_name or case.patient_name
    case.completed_questions = answer_count
    case.total_questions = total
    case.completion_percent = _percent(answer_count, total)
    case.save(update_fields=["paid_submission", "patient_name", "completed_questions", "total_questions", "completion_percent", "updated_at"])
    report_track, _ = WorkflowReport.objects.get_or_create(case=case)
    report_track.paid_submission = submission
    report_track.save(update_fields=["paid_submission", "updated_at"])
    return case


def mark_paid_submitted(case: WorkflowCase | None, submission: EsSubSubmission):
    if not case:
        return None
    attach_paid_submission(case, submission)
    case.completion_percent = Decimal("100.00")
    case.save(update_fields=["completion_percent", "updated_at"])
    transition(case, WorkflowCase.Status.SUBMITTED, "FORM_SUBMITTED", stage="PATIENT_COMPLETION", actor_type=WorkflowEvent.ActorType.PATIENT)
    return case


def mark_payment_pending(case: WorkflowCase | None, order: EsPayOrder, transaction: EsPayTransaction | None = None):
    if not case:
        return None
    case.payment_status = WorkflowCase.PaymentStatus.PENDING
    case.save(update_fields=["payment_status", "updated_at"])
    payment, _ = WorkflowPayment.objects.get_or_create(case=case, defaults={"order": order})
    payment.order = order
    payment.transaction = transaction or payment.transaction
    payment.is_required = order.final_amount_paise > 0
    payment.amount_paise = order.final_amount_paise
    payment.gateway = transaction.gateway if transaction else payment.gateway or "dummy"
    payment.status = WorkflowPayment.Status.PENDING
    payment.reference_id = transaction.gateway_order_id if transaction else payment.reference_id
    payment.save()
    transition(case, WorkflowCase.Status.PAYMENT_PENDING, "PAYMENT_PENDING", stage="PAYMENT", actor_type=WorkflowEvent.ActorType.SYSTEM, metadata={"order_code": order.order_code})
    return case


def mark_payment_completed(case: WorkflowCase | None, order: EsPayOrder, transaction: EsPayTransaction | None = None):
    if not case:
        return None
    now = timezone.now()
    case.payment_status = WorkflowCase.PaymentStatus.COMPLETED
    case.payment_completed_at = case.payment_completed_at or now
    case.save(update_fields=["payment_status", "payment_completed_at", "updated_at"])
    payment, _ = WorkflowPayment.objects.get_or_create(case=case, defaults={"order": order})
    payment.order = order
    payment.transaction = transaction or payment.transaction
    payment.is_required = order.final_amount_paise > 0
    payment.amount_paise = order.final_amount_paise
    payment.gateway = transaction.gateway if transaction else payment.gateway or "dummy"
    payment.status = WorkflowPayment.Status.COMPLETED
    payment.reference_id = (transaction.gateway_payment_id or transaction.gateway_order_id) if transaction else payment.reference_id
    payment.paid_at = payment.paid_at or now
    payment.raw_payload_json = transaction.raw_payload_json if transaction else payment.raw_payload_json
    payment.save()
    transition(case, WorkflowCase.Status.PAYMENT_COMPLETED, "PAYMENT_COMPLETED", stage="PAYMENT", actor_type=WorkflowEvent.ActorType.GATEWAY, metadata={"order_code": order.order_code})
    return case


def mark_payment_failed(case: WorkflowCase | None, order: EsPayOrder, transaction: EsPayTransaction | None = None, reason: str = ""):
    if not case:
        return None
    now = timezone.now()
    case.payment_status = WorkflowCase.PaymentStatus.FAILED
    case.save(update_fields=["payment_status", "updated_at"])
    payment, _ = WorkflowPayment.objects.get_or_create(case=case, defaults={"order": order})
    payment.order = order
    payment.transaction = transaction or payment.transaction
    payment.is_required = order.final_amount_paise > 0
    payment.amount_paise = order.final_amount_paise
    payment.gateway = transaction.gateway if transaction else payment.gateway or "dummy"
    payment.status = WorkflowPayment.Status.FAILED
    payment.failed_at = now
    payment.error_text = reason
    payment.raw_payload_json = transaction.raw_payload_json if transaction else payment.raw_payload_json
    payment.save()
    transition(case, WorkflowCase.Status.FAILED, "PAYMENT_FAILED", stage="PAYMENT", actor_type=WorkflowEvent.ActorType.GATEWAY, message=reason, failure_reason=reason)
    return case


def mark_report_processing(case: WorkflowCase | None):
    if not case:
        return None
    report_track, _ = WorkflowReport.objects.get_or_create(case=case)
    report_track.status = WorkflowReport.Status.PROCESSING
    report_track.generation_started_at = report_track.generation_started_at or timezone.now()
    report_track.save(update_fields=["status", "generation_started_at", "updated_at"])
    transition(case, WorkflowCase.Status.REPORT_PROCESSING, "REPORT_PROCESSING", stage="REPORT_GENERATION")
    return case


def mark_report_generated(case: WorkflowCase | None, report: EsRepReport):
    if not case:
        return None
    now = timezone.now()
    case.report = report
    case.report_generated_at = case.report_generated_at or now
    case.save(update_fields=["report", "report_generated_at", "updated_at"])
    report_track, _ = WorkflowReport.objects.get_or_create(case=case)
    report_track.report = report
    report_track.status = WorkflowReport.Status.COMPLETED
    report_track.generated_at = report_track.generated_at or now
    report_track.save(update_fields=["report", "status", "generated_at", "updated_at"])
    transition(case, WorkflowCase.Status.REPORT_GENERATED, "REPORT_GENERATED", stage="REPORT_GENERATION", metadata={"report_id": report.id})
    return case


def mark_report_failed(case: WorkflowCase | None, reason: str):
    if not case:
        return None
    report_track, _ = WorkflowReport.objects.get_or_create(case=case)
    report_track.status = WorkflowReport.Status.FAILED
    report_track.error_text = reason
    report_track.save(update_fields=["status", "error_text", "updated_at"])
    transition(case, WorkflowCase.Status.FAILED, "REPORT_FAILED", stage="REPORT_GENERATION", message=reason, failure_reason=reason)
    return case


def mark_report_sent(case: WorkflowCase | None, *, to_patient=False, to_doctor=False, patient_status="", doctor_status=""):
    if not case:
        return None
    now = timezone.now()
    report_track, _ = WorkflowReport.objects.get_or_create(case=case)
    if to_patient:
        report_track.sent_to_patient_at = report_track.sent_to_patient_at or now
        report_track.patient_delivery_status = patient_status or report_track.patient_delivery_status
    if to_doctor:
        report_track.sent_to_doctor_at = report_track.sent_to_doctor_at or now
        report_track.doctor_delivery_status = doctor_status or report_track.doctor_delivery_status
    report_track.status = WorkflowReport.Status.SENT
    report_track.save()
    transition(case, WorkflowCase.Status.REPORT_SENT, "REPORT_SENT", stage="REPORT_DELIVERY", metadata={"to_patient": to_patient, "to_doctor": to_doctor})
    if to_patient or to_doctor:
        transition(case, WorkflowCase.Status.COMPLETED, "WORKFLOW_COMPLETED", stage="COMPLETION")
    return case


def mark_download(case: WorkflowCase | None, kind: str):
    if not case:
        return None
    _event(case, "REPORT_DOWNLOADED", stage="REPORT_DELIVERY", actor_type=WorkflowEvent.ActorType.PATIENT, metadata={"kind": kind})
    return case
