import json
import os
import secrets
import sys
from datetime import timedelta
from pathlib import Path

import django

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "emoscreen.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from content.constants import TERMS_VERSION
from content.models import RegisteredProfessional
from content.utils import make_verify_token, normalize_phone
from paid.models import EsCfgForm, EsPayOrder, WorkflowCase
from paid.services import audit
from paid.services.tokens import build_order_token_payload, hash_token, sign_payload


BASE_URL = "http://127.0.0.1:8000"
DOCTOR_CODE = "C488DF49"
DOCTOR_EMAIL = "codexqa95674388@gmail.com"
DOCTOR_USERNAME = "local_doctor_C488DF49"
DOCTOR_PASSWORD = "LocalPass123!"
OUT_PATH = Path("docs/e2e_testing/guide_data.json")


def absolute(path):
    return f"{BASE_URL}{path}"


def main():
    User = get_user_model()
    doctor, _ = RegisteredProfessional.objects.update_or_create(
        unique_doctor_code=DOCTOR_CODE,
        defaults={
            "role": RegisteredProfessional.Role.PEDIATRICIAN,
            "salutation": "Dr",
            "first_name": "Codex",
            "last_name": "QA",
            "email": DOCTOR_EMAIL,
            "whatsapp": "919429633099",
            "appointment_booking_number": "919429633099",
            "clinic_address": "Local QA Clinic",
            "state": "NULL",
            "district": "NULL",
            "receptionist_whatsapp": "919429633099",
            "terms_accepted_at": timezone.now(),
            "terms_version": TERMS_VERSION,
        },
    )
    user, _ = User.objects.update_or_create(
        username=DOCTOR_USERNAME,
        defaults={"email": DOCTOR_EMAIL, "is_staff": True, "is_superuser": True},
    )
    user.set_password(DOCTOR_PASSWORD)
    user.save()

    form = EsCfgForm.objects.filter(form_code="ES_0_2", is_active=True).first()
    if not form:
        form = EsCfgForm.objects.filter(is_active=True).order_by("age_min_months").first()
    if not form:
        raise RuntimeError("No active paid form is available.")

    order_code = f"GD{secrets.token_hex(4).upper()}"
    paid_phone = normalize_phone("919811223344")
    paid_order = EsPayOrder.objects.create(
        order_code=order_code,
        doctor=doctor,
        form=form,
        price_variant="INR_1",
        base_amount_paise=100,
        discount_paise=0,
        final_amount_paise=100,
        patient_name="Aarav Guide Test",
        patient_whatsapp=paid_phone,
        patient_email="parent.paid@example.com",
        status=EsPayOrder.Status.PAYMENT_PENDING,
        link_token_hash="pending",
        link_expires_at=timezone.now() + timedelta(days=7),
        created_ip="127.0.0.1",
        user_agent="Guide screenshot capture",
    )
    payload = build_order_token_payload(paid_order, DOCTOR_CODE)
    paid_token = sign_payload(payload)
    paid_order.link_token_hash = hash_token(paid_token)
    paid_order.status = EsPayOrder.Status.LINK_SENT
    paid_order.save(update_fields=["link_token_hash", "status", "updated_at"])
    paid_entry_path = reverse(
        "paid:patient_entry",
        args=[paid_order.order_code, DOCTOR_CODE, paid_order.form_id, paid_order.final_amount_paise, paid_token],
    )
    paid_entry_url = absolute(paid_entry_path)
    paid_case = audit.create_paid_case(
        order=paid_order,
        token=paid_token,
        source="e2e_testing_guide",
        delivery_url=paid_entry_url,
    )

    free_phone = normalize_phone("919822334455")
    free_token = make_verify_token(DOCTOR_CODE, free_phone, "en")
    free_verify_path = reverse("content:verify_phone", args=[DOCTOR_CODE, free_token])
    free_verify_url = f"{absolute(free_verify_path)}?lang=en"
    free_case = audit.create_legacy_case(
        doctor=doctor,
        patient_whatsapp=free_phone,
        language="en",
        token=free_token,
        source="e2e_testing_guide",
        delivery_url=free_verify_url,
    )

    data = {
        "base_url": BASE_URL,
        "doctor_code": DOCTOR_CODE,
        "doctor_username": DOCTOR_USERNAME,
        "doctor_password": DOCTOR_PASSWORD,
        "doctor_email": DOCTOR_EMAIL,
        "home_url": absolute(reverse("content:registration_choice")),
        "admin_root_url": absolute(reverse("admin:index")),
        "admin_bulk_upload_url": absolute(reverse("bulk_doctor_upload")),
        "clinic_url": absolute(reverse("content:clinic_send", args=[DOCTOR_CODE])),
        "legacy_clinic_url": absolute(reverse("legacy_clinic_send", args=[DOCTOR_CODE])),
        "how_to_guide_url": "https://bit.ly/43QkzpM",
        "paid_orders_url": absolute(reverse("paid:orders_list", args=[DOCTOR_CODE])),
        "paid_entry_url": paid_entry_url,
        "paid_payment_url": absolute(reverse("paid:patient_payment", args=[paid_order.order_code])),
        "paid_form_url": absolute(reverse("paid:patient_form", args=[paid_order.order_code])),
        "paid_review_url": absolute(reverse("paid:patient_review", args=[paid_order.order_code])),
        "paid_thank_you_url": absolute(reverse("paid:patient_thank_you", args=[paid_order.order_code])),
        "paid_order_code": paid_order.order_code,
        "paid_case_code": paid_case.case_code,
        "paid_case_detail_url": absolute(reverse("paid:workflow_detail", args=[paid_case.case_code])),
        "free_verify_url": free_verify_url,
        "free_screen_url": absolute(reverse("content:screening_form", args=[DOCTOR_CODE, "en"])),
        "free_case_code": free_case.case_code,
        "free_case_detail_url": absolute(reverse("paid:workflow_detail", args=[free_case.case_code])),
        "self_start_url": absolute(reverse("content:self_start")),
        "workflow_dashboard_url": absolute(reverse("paid:workflow_dashboard")),
        "admin_login_url": absolute(reverse("admin:login")),
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
