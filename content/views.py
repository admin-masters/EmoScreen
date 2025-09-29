# content/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.conf import settings
from django.db import transaction
from datetime import datetime
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import csv
import io
import os
from .i18n_static import get_ui_labels
from .i18n_static import get_ui_labels
from .models import UiString
from datetime import datetime
from django.http import FileResponse, HttpResponse, HttpResponseRedirect
from django.contrib.admin.views.decorators import staff_member_required
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.contrib.auth import logout  # <-- NEW for auth gate / logout
from django.utils import timezone
from urllib.parse import quote as urlquote
from .constants import TERMS_VERSION
from django.core.signing import BadSignature, SignatureExpired  # <-- NEW
from django.views.decorators.http import require_http_methods   # <-- NEW
from django.urls import reverse
from .forms import PediatricianForm, CaregiverForm, ClinicSendForm , BulkDoctorUploadForm
from .models import (
    RegisteredProfessional, Language, Question, QuestionI18n, Option, OptionI18n,
    RedFlag, RedFlagI18n, DoctorEducation, Submission, SubmissionAnswer, SubmissionRedFlag, ResultMessage
)
from .utils import (
    generate_doctor_code, normalize_phone, whatsapp_link, parent_message,
    white_label_context, generate_report_code, ADVISE_PATIENT_TEXT,
    clinic_contact_numbers, booking_message_for_clinic, notify_registration,
    make_verify_token, read_verify_token, last10_digits   # <-- NEW imports
)

# ---------- Registration ----------

def registration_choice(request):
    return render(request, "content/registration_choice.html")

@transaction.atomic
def register_pediatrician(request):
    if request.method == "POST":
        form = PediatricianForm(request.POST, request.FILES)
        if form.is_valid():
            pro = form.save(commit=False)
            pro.role = "PEDIATRICIAN"
            pro.unique_doctor_code = generate_doctor_code()
            pro.save()
            clinic_url = request.build_absolute_uri(reverse("content:clinic_send", args=[pro.unique_doctor_code]))
            # NEW: send onboarding notifications (SendGrid + optional AiSensy)
            notify_registration(pro, clinic_url)
            return render(request, "content/registration_done.html", {"clinic_url": clinic_url, "pro": pro})
    else:
        form = PediatricianForm()
    return render(request, "content/register_pediatrician.html", {"form": form})

@transaction.atomic
def register_caregiver(request):
    if request.method == "POST":
        form = CaregiverForm(request.POST, request.FILES)
        if form.is_valid():
            pro = form.save(commit=False)
            pro.role = "CAREGIVER"
            # split name -> first/last
            name = form.cleaned_data.get("name", "")
            parts = name.split(" ", 1)
            pro.first_name = parts[0]
            if len(parts) > 1:
                pro.last_name = parts[1]
            pro.unique_doctor_code = generate_doctor_code()
            pro.save()
            clinic_url = request.build_absolute_uri(reverse("content:clinic_send", args=[pro.unique_doctor_code]))
            notify_registration(pro, clinic_url)
            return render(request, "content/registration_done.html", {"clinic_url": clinic_url, "pro": pro})
    else:
        form = CaregiverForm()
    return render(request, "content/register_caregiver.html", {"form": form})

# ---------- Clinic link: send WhatsApp to parent ----------

def clinic_send(request, code):
    pro = get_object_or_404(RegisteredProfessional, unique_doctor_code=code)

    # -------- NEW: Google sign-in gate + email match --------
    expected = (pro.email or "").strip().lower()
    user_email = (getattr(request.user, "email", "") or "").strip().lower()

    wants_auth = request.GET.get("auth", "")
    # If not authenticated, start Google flow
    if not request.user.is_authenticated:
        request.session["post_auth_redirect"] = request.get_full_path()
        request.session["expected_email"] = expected
        return redirect(reverse("social:begin", args=["google-oauth2"]))

    # If logged in but email doesn't match, show error prompt with re-login
    if user_email != expected:
        # Allow user to sign out and retry
        relogin_url = reverse("social:begin", args=["google-oauth2"])
        # keep coming back here after Google
        relogin_url += f"?next={reverse('content:auth_complete')}"
        request.session["post_auth_redirect"] = request.get_full_path()
        request.session["expected_email"] = expected
        return render(
            request,
            "content/auth_error.html",
            {
                "expected_email": expected,
                "current_email": user_email or "(not signed in with Google email)",
                "retry_url": relogin_url,
                "clinic_url": request.get_full_path(),
                **white_label_context(pro),
            },
        )

    # -------- NEW: Require Terms on first login (or version change) --------
    if not pro.terms_accepted_at or (pro.terms_version != TERMS_VERSION):
        terms_url = reverse("content:terms_accept", args=[code])
        next_qs = "?next=" + urlquote(request.get_full_path())
        return redirect(terms_url + next_qs)
    # -------- END gate --------

    langs = list(Language.objects.all())
    lang_choices = [(l.lang_code, l.lang_name_english) for l in langs]

    if request.method == "POST":
        form = ClinicSendForm(request.POST, lang_choices=lang_choices)
        if form.is_valid():
            parent_phone = form.cleaned_data["parent_whatsapp"]
            lang = form.cleaned_data["language"]

            # NEW: verification link with signed token (instead of direct language page)
            token = make_verify_token(code, parent_phone, lang)
            verify_link = request.build_absolute_uri(
                reverse("content:verify_phone", args=[code, token])
            )
            verify_link += f"?lang={lang}"
            # Keep existing language-specific message templates:
            msg = parent_message(lang, verify_link)

            wa_url = whatsapp_link(parent_phone, msg)
            return redirect(wa_url)
    else:
        form = ClinicSendForm(lang_choices=lang_choices)

    ctx = {"form": form, "pro": pro, **white_label_context(pro)}
    return render(request, "content/clinic_send.html", ctx)
# content/views.py
from django.contrib.auth import logout
from django.core.signing import BadSignature, SignatureExpired

def _gate_google_and_email(request, pro, target_after_auth):
    """Reuse the same gate rules used in clinic_send (Google auth + email match)."""
    expected = (pro.email or "").strip().lower()
    user_email = (getattr(request.user, "email", "") or "").strip().lower()

    if not request.user.is_authenticated:
        request.session["post_auth_redirect"] = target_after_auth
        request.session["expected_email"] = expected
        return redirect(reverse("social:begin", args=["google-oauth2"]))

    if user_email != expected:
        relogin_url = reverse("social:begin", args=["google-oauth2"]) + "?next=" + reverse("content:auth_complete")
        request.session["post_auth_redirect"] = target_after_auth
        request.session["expected_email"] = expected
        return render(
            request,
            "content/auth_error.html",
            {
                "expected_email": expected,
                "current_email": user_email or "(not signed in with Google email)",
                "retry_url": relogin_url,
                "clinic_url": target_after_auth,
                **white_label_context(pro),
            },
        )
    return None  # OK

@require_http_methods(["GET", "POST"])
def terms_accept(request, code):
    """
    Show Terms once after Google login. Require explicit checkbox to proceed.
    """
    pro = get_object_or_404(RegisteredProfessional, unique_doctor_code=code)
    next_url = request.GET.get("next") or reverse("content:clinic_send", args=[code])

    # Ensure the same Google user as registered email
    gate = _gate_google_and_email(request, pro, target_after_auth=request.get_full_path())
    if gate is not None:
        return gate  # either redirect to Google or render auth_error

    error = ""
    if request.method == "POST":
        agree = request.POST.get("agree") == "on"
        if not agree:
            error = "You must agree to the Terms and Conditions to continue."
        else:
            pro.terms_accepted_at = timezone.now()
            pro.terms_version = TERMS_VERSION
            pro.save(update_fields=["terms_accepted_at", "terms_version"])
            return redirect(next_url)

    ctx = {"pro": pro, "error": error, **white_label_context(pro)}
    return render(request, "content/terms_accept.html", ctx)
# content/views.py
def terms_public(request):
    # Read-only Terms (no checkbox, no auth)
    return render(request, "content/terms_public.html")

def auth_complete(request):
    """
    Called after Google login. We verify that the authenticated user's email
    matches the expected email saved in session before allowing access.
    """
    expected = (request.session.get("expected_email") or "").lower()
    next_url = request.session.pop("post_auth_redirect", "/")
    actual = (getattr(request.user, "email", "") or "").lower()

    if not request.user.is_authenticated:
        # not signed in; send to Google again
        request.session["post_auth_redirect"] = next_url
        request.session["expected_email"] = expected
        return redirect(reverse("social:begin", args=["google-oauth2"]))

    if expected and actual != expected:
        # wrong account; sign out to force account chooser next time
        logout(request)
        # keep values to show message + retry link
        request.session["post_auth_redirect"] = next_url
        request.session["expected_email"] = expected
        return render(
            request,
            "content/auth_error.html",
            {
                "expected_email": expected,
                "current_email": actual or "(no email)",
                "retry_url": reverse("social:begin", args=["google-oauth2"]) + "?next=" + reverse("content:auth_complete"),
                "clinic_url": next_url,
            },
        )
    # OK -> go back to clinic page
    return redirect(next_url)

def auth_logout(request):
    logout(request)
    # If the user just logged out from an error page, send them to Google again
    next_url = request.GET.get("next") or "/"
    return redirect(next_url)

# ---------- Parent phone verification ----------

from .i18n_static import get_ui_labels  # add this import

@require_http_methods(["GET", "POST"])
def verify_phone(request, code, token):
    """
    1) Decode the token to get expected last-10 digits & professional code (+lang).
    2) Ask parent to enter their WhatsApp number; compare last-10.
    3) On success: mark session as verified for this code and redirect to language selection.
    """
    pro = get_object_or_404(RegisteredProfessional, unique_doctor_code=code)

    # Default to GET param lang (for expired/invalid token cases); fallback en
    lang_from_qs = (request.GET.get("lang") or "").strip() or "en"

    try:
        data = read_verify_token(token, max_age_days=7)
        expected_last10 = data.get("p", "")
        token_code = data.get("c")
        lang = data.get("l") or lang_from_qs  # prefer token, then QS
        if token_code != code:
            raise BadSignature("Code mismatch")
        ui = get_ui_labels(lang)
    except (BadSignature, SignatureExpired):
        ui = get_ui_labels(lang_from_qs)
        ctx = {
            "pro": pro,
            "ui": ui,
            "error": ui["verify_error_link_invalid"],
            **white_label_context(pro),
        }
        return render(request, "content/verify_phone.html", ctx)

    error = ""
    if request.method == "POST":
        entered = request.POST.get("parent_phone", "")
        if last10_digits(entered) == expected_last10:
            request.session[f"phone_verified_{code}"] = True
            return redirect(reverse("content:parent_language_select", args=[code]))
        else:
            error = ui["verify_error_mismatch"]

    ctx = {
        "pro": pro,
        "ui": ui,
        "lang": lang,
        "error": error,
        **white_label_context(pro),
    }
    return render(request, "content/verify_phone.html", ctx)

# ---------- Parent flow ----------

def parent_language_select(request, code):
    pro = get_object_or_404(RegisteredProfessional, unique_doctor_code=code)

    # NEW: require phone verification in this browser session
    if not request.session.get(f"phone_verified_{code}", False):
        return render(
            request,
            "content/verify_required.html",
            {"pro": pro, **white_label_context(pro)}
        )

    languages = Language.objects.all()
    ctx = {"pro": pro, "languages": languages, **white_label_context(pro)}
    return render(request, "content/parent_language_select.html", ctx)

def _build_screening_form(lang_code):
    questions = list(Question.objects.filter(active=True).order_by("display_order"))
    fields = []
    for q in questions:
        qi = QuestionI18n.objects.get(question=q, lang_id=lang_code)
        opts = Option.objects.filter(question=q).order_by("display_order")
        oi = OptionI18n.objects.filter(option__in=opts, lang_id=lang_code)
        by_option = {x.option_id: x.option_text for x in oi}
        fields.append({
            "question_code": q.question_code,
            "question_text": qi.question_text,
            "options": [{"code": o.option_code, "text": by_option.get(o.option_code, o.option_code)} for o in opts],
        })
    return fields, questions

@transaction.atomic
def screening_form(request, code, lang):
    pro = get_object_or_404(RegisteredProfessional, unique_doctor_code=code)
    required_demographics = ["patient_name", "parent_phone", "patient_email", "dob", "gender"]

    fields, questions = _build_screening_form(lang)
    ui = get_ui_labels(lang)

    # NEW: Form title and purpose
    form_title = ui_text("FORM_TITLE", lang, "Behavioral & Emotional Red Flags – Pre-consultation form")
    form_purpose = ui_text("FORM_PURPOSE", lang, "")  # Optional

    if request.method == "POST":
        missing = [k for k in required_demographics if not request.POST.get(k)]
        missing += [f["question_code"] for f in fields if not request.POST.get(f["question_code"])]
        if missing:
            ctx = {
                "error": "Please fill all required fields.",
                "fields": fields,
                "lang": lang,
                "pro": pro,
                "ui": ui,
                "form_title": form_title,       # Added
                "form_purpose": form_purpose,   # Added
                **white_label_context(pro),
            }
            return render(request, "content/screening_form.html", ctx)

        patient_name = request.POST.get("patient_name", "")
        parent_phone = normalize_phone(request.POST.get("parent_phone", ""))
        patient_email = (request.POST.get("patient_email") or "").strip()
        try:
            validate_email(patient_email)
        except ValidationError:
            ctx = {
                "error": "Please enter a valid email address.",
                "fields": fields,
                "lang": lang,
                "pro": pro,
                "ui": ui,
                "form_title": form_title,       # Added
                "form_purpose": form_purpose,   # Added
                **white_label_context(pro)
            }
            return render(request, "content/screening_form.html", ctx)

        selected_option_codes = [request.POST.get(f["question_code"]) for f in fields]
        options = list(Option.objects.filter(option_code__in=selected_option_codes))
        flags = []
        for opt in options:
            if opt.triggers_red_flag and opt.red_flag_id:
                flags.append(opt.red_flag_id)
        flags = list(dict.fromkeys(flags))
        flags_count = len(flags)

        report_code = generate_report_code()
        submission = Submission.objects.create(
            report_code=report_code,
            professional=pro,
            lang_id=lang,
            flags_count=flags_count,
            email_to=pro.email,
        )

        for opt in options:
            SubmissionAnswer.objects.create(
                submission=submission,
                question_id=opt.question_id,
                option_id=opt.option_code,
                triggers_red_flag=bool(opt.triggers_red_flag),
                red_flag_id=opt.red_flag_id,
            )
        for rf in flags:
            SubmissionRedFlag.objects.create(submission=submission, red_flag_id=rf)

        no_flags_msg = ResultMessage.objects.get(message_code="NO_FLAGS", lang_id=lang).message_text
        has_flags_intro = ResultMessage.objects.get(message_code="HAS_FLAGS_INTRO", lang_id=lang).message_text

        # NEW (aligned)
        rf_labels, education_links = _aligned_rf_labels_and_links(flags, lang, request)


        if flags_count > 0:
            _send_doctor_report_email(
                submission, pro, lang, rf_labels, education_links, patient_name, parent_phone, request
            )

        _send_patient_report_email(
            to_email=patient_email,
            patient_name=patient_name,
            parent_phone=parent_phone,
            report_code=report_code,
            rf_labels=rf_labels,
            request=request,
        )

        tel_digits, wa_digits = clinic_contact_numbers(pro)
        call_link = f"tel:{tel_digits}" if (flags_count > 0 and tel_digits) else ""
        wa_msg = booking_message_for_clinic(patient_name)
        wa_link = whatsapp_link(wa_digits, wa_msg) if (flags_count > 0 and wa_digits) else ""

        doctor_name = " ".join(filter(None, [pro.salutation, pro.first_name, pro.last_name])).strip()
        result_intro = ui.get("result_has_flags_intro") or has_flags_intro
        result_capture = ui["result_capture_screen"].format(doctor=doctor_name)
        result_emailed = ui["result_emailed_to_doctor"].format(doctor=doctor_name)
        result_visit = ui["result_visit_immediately"].format(doctor=doctor_name)

        ctx = {
            "report_code": report_code,
            "flags_count": flags_count,
            "no_flags_msg": no_flags_msg,
            "has_flags_intro": has_flags_intro,
            "rf_labels": rf_labels,
            "call_link": call_link,
            "wa_link": wa_link,
            "pro": pro,
            "result_intro": result_intro,
            "result_capture": result_capture,
            "result_emailed": result_emailed,
            "result_visit": result_visit,
            **white_label_context(pro),
        }
        return render(request, "content/result.html", ctx)

    # GET branch
    ctx = {
        "fields": fields,
        "lang": lang,
        "pro": pro,
        "ui": ui,
        "form_title": form_title,       # Added
        "form_purpose": form_purpose,   # Added
        **white_label_context(pro),
    }
    return render(request, "content/screening_form.html", ctx)


# content/views.py  (drop-in replacement for _send_doctor_report_email)
def _send_doctor_report_email(submission, pro, lang, rf_labels, education_links, patient_name, parent_phone, request):
    """Build and send doctor report (SendGrid) with two password-protected PDF attachments."""
    import base64
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Attachment, FileContent, FileName, FileType, Disposition

    from .utils import ADVISE_PATIENT_TEXT, whatsapp_link, normalize_phone
    from .pdf_utils import build_doctor_report_pdf_bytes, build_patient_report_pdf_bytes
    from datetime import datetime

    btn_style = (
    "display:inline-block;padding:6px 10px;"
    "background:#0ea5e9;color:#ffffff;text-decoration:none;"
    "border-radius:4px;font-weight:600;margin-left:8px"
    )

    # Red flags + education links (doctor-only)
    rf_list_html = "<ul style='padding-left:18px;margin:0'>" + "".join(
    (
        f"<li style='margin:6px 0'>{label}"
        f"<a href='{link}' target='_blank' rel='noopener' style='{btn_style}'>"
        f"Doctor Education</a></li>"
    )
    for label, link in zip(rf_labels, education_links)
    ) + "</ul>"

    advise_text = ADVISE_PATIENT_TEXT.format(
        doctor_name=f"{pro.salutation or ''} {pro.first_name or ''} {pro.last_name or ''}".strip()
    )
    advise_link = whatsapp_link(normalize_phone(parent_phone), advise_text)

    html = f"""
    <div style="font-family: Arial, sans-serif">
      <p><strong>Screening Form:</strong> Behavioral and Emotional Red Flags</p>
      <p><strong>Report Date:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}<br/>
         <strong>Report Number:</strong> {submission.report_code}</p>

      <h3>Doctor Details</h3>
      <p><strong>Doctor Name:</strong> {(pro.salutation or '') + ' ' + (pro.first_name or '') + ' ' + (pro.last_name or '')}<br/>
         <strong>Doctor ID:</strong> {pro.unique_doctor_code}</p>

      <h3>Patient Details</h3>
      <p><strong>Patient Name:</strong> {patient_name or '(not stored)'}<br/>
         <strong>Phone:</strong> {parent_phone or '(not stored)'}</p>

      <h3>Red Flags Identified</h3>
      {rf_list_html}

      <p><a href="{advise_link}"
            style="display:inline-block;background:#e02424;color:#fff;padding:10px 16px;border-radius:4px;text-decoration:none;"
            target="_blank" rel="noopener">Click Here to advise the patient to visit you</a></p>
        <p>We’ve attached your report as a PDF. It is password-protected.</p>
       <p><em>Note: A password is required to open the PDF.</em></p>
      <p><em>Password format Doctor Report:</em> first 4 letters of your name + last 4 digits of your WhatsApp number.</p>
      <p><em>Password format Patient Report:</em> first 4 letters of patient name + last 4 digits of patient WhatsApp number.</p>
      <hr/>
      <small>This report contains patient identifiable and private information. The system does not retain patient identifiable information.
      To obtain a copy in future you must provide the report number.</small>
    </div>
    """

    # ---- Build dynamic PDFs ----
    doctor_name_full = f"{pro.salutation or ''} {pro.first_name or ''} {pro.last_name or ''}".strip()

    doctor_pdf_bytes, doctor_pdf_pwd = build_doctor_report_pdf_bytes(
    doctor_full_name=doctor_name_full,
    doctor_first_name=(pro.first_name or ""),
    doctor_id=pro.unique_doctor_code,
    doctor_whatsapp=(pro.whatsapp or ""),
    patient_name=patient_name or "",
    parent_phone=parent_phone or "",
    report_code=submission.report_code,
    rf_labels=rf_labels,
    education_links=education_links,   # <— pass the links here
    )

    patient_pdf_bytes, patient_pdf_pwd = build_patient_report_pdf_bytes(
        patient_name=patient_name or "",
        parent_phone=parent_phone or "",
        report_code=submission.report_code,
        rf_labels=rf_labels,
    )
    if not settings.SENDGRID_API_KEY:
        print("---- SENDGRID DISABLED: printing doctor report email ----")
        print("To:", pro.email)
        print("Subject:", f"Red Flags report for {patient_name or 'patient'}")
        print("Doctor PDF Password:", doctor_pdf_pwd)
        print("Patient PDF Password:", patient_pdf_pwd)
        return

    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        msg = Mail(
            from_email=Email(settings.DEFAULT_FROM_EMAIL, settings.REPORT_FROM_NAME),
            to_emails=To(pro.email),
            subject=f"Red Flags report for {patient_name or 'patient'}",
            html_content=html,
        )
        att1 = Attachment(
            FileContent(base64.b64encode(doctor_pdf_bytes).decode()),
            FileName(f"DoctorReport_{submission.report_code}.pdf"),
            FileType("application/pdf"),
            Disposition("attachment"),
        )
        att2 = Attachment(
            FileContent(base64.b64encode(patient_pdf_bytes).decode()),
            FileName(f"PatientReport_{submission.report_code}.pdf"),
            FileType("application/pdf"),
            Disposition("attachment"),
        )
        try:
            msg.add_attachment(att1)
            msg.add_attachment(att2)
        except AttributeError:
            msg.attachments = [att1, att2]

        resp = sg.send(msg)
        print(f"[SendGrid] status={resp.status_code} (PDFs attached). DoctorPDFPwd={doctor_pdf_pwd} PatientPDFPwd={patient_pdf_pwd}")
        from .models import Submission
        Submission.objects.filter(pk=submission.pk).update(email_sent_at=datetime.utcnow())
    except Exception as e:
        print("SendGrid error:", e)

def _send_patient_report_email(to_email: str, patient_name: str, parent_phone: str,
                               report_code: str, rf_labels, request):
    """
    Email ONLY the patient PDF to the patient's email.
    PDF is password-protected: first 4 letters of patient’s name + last 4 digits of parent’s WhatsApp.
    """
    import base64
    from datetime import datetime
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Attachment, FileContent, FileName, FileType, Disposition

    from .pdf_utils import build_patient_report_pdf_bytes

    # Build the dynamic, encrypted Patient PDF
    pdf_bytes, pdf_pwd = build_patient_report_pdf_bytes(
        patient_name=patient_name or "",
        parent_phone=parent_phone or "",
        report_code=report_code,
        rf_labels=list(rf_labels or []),
    )

    # Simple patient-facing email body
    flags_html = ""
    if rf_labels:
        flags_html = "<ul>" + "".join(f"<li>{x}</li>" for x in rf_labels) + "</ul>"

    html = f"""
    <div style="font-family:Arial,sans-serif">
      <p><strong>Your Behavioral &amp; Emotional Red Flags report</strong></p>
      <p><strong>Report Number:</strong> {report_code}<br/>
         <strong>Date:</strong> {datetime.utcnow().strftime('%Y-%m-%d')}</p>
      {"<p><strong>Red flags noticed:</strong></p>" + flags_html if rf_labels else "<p>No red flags were identified.</p>"}
      <p>We’ve attached your report as a PDF. It is password-protected.</p>
       <p><em>Note: A password is required to open the PDF.</em></p>
      <p><em>Password format:</em> first 4 letters of your name + last 4 digits of your WhatsApp number.</p>
      <hr/>
      <small>This report is generated from your form responses. It does not diagnose a condition and is for information only. Please consult your doctor for medical advice.</small>
    </div>
    """

    if not settings.SENDGRID_API_KEY:
        # Dev mode: no email credentials present
        print("[SendGrid] missing SENDGRID_API_KEY; printing PATIENT email instead")
        print("To:", to_email)
        print("Subject:", f"Your Emoscreen report ({report_code})")
        print("HTML:\n", html)
        return

    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        msg = Mail(
            from_email=Email(settings.DEFAULT_FROM_EMAIL, settings.REPORT_FROM_NAME),
            to_emails=To(to_email),
            subject=f"Your Emoscreen report ({report_code})",
            html_content=html,
        )
        att = Attachment(
            FileContent(base64.b64encode(pdf_bytes).decode()),
            FileName(f"YourReport_{report_code}.pdf"),
            FileType("application/pdf"),
            Disposition("attachment"),
        )
        try:
            msg.add_attachment(att)
        except AttributeError:
            msg.attachments = [att]

        resp = sg.send(msg)
        print(f"[SendGrid] patient status={resp.status_code} (patient PDF attached).")
    except Exception as e:
        print("[SendGrid] patient email error:", e)



def view_result(request, report_code):
    """Doctor read-only page (now includes Doctor Education links)."""
    sub = get_object_or_404(Submission, report_code=report_code)
    pro = sub.professional
    rf_ids = list(
    SubmissionRedFlag.objects
    .filter(submission=sub)
    .order_by("id")                    # keep a stable, user-friendly order
    .values_list("red_flag_id", flat=True)
)
    rf_labels, education_links = _aligned_rf_labels_and_links(rf_ids, sub.lang_id, request)


    ctx = {"report_code": report_code, "rf_labels": rf_labels, "education_links": education_links, "pro": pro,
           **white_label_context(pro)}
    return render(request, "content/result_readonly.html", ctx)


from django.shortcuts import render, get_object_or_404
from .models import RedFlag, DoctorEducation, RedFlagI18n

def education_page(request, slug):
    rf = get_object_or_404(RedFlag, education_url_slug=slug)
    de = get_object_or_404(DoctorEducation, red_flag=rf, lang_id="en")

    rf_i18n = RedFlagI18n.objects.filter(red_flag=rf, lang_id="en").first()
    rf_title = rf_i18n.parent_label if rf_i18n else rf.red_flag_code

    return render(request, "content/education_page.html", {
        "rf": rf,
        "de": de,
        "rf_title": rf_title,
    })



# ---------------------- Bulk Doctor CSV Upload ----------------------

def _norm_header(s: str) -> str:
    """
    Normalize header names to ascii-ish snake_case so we can match
    user CSVs with small variations (parentheses, spaces, punctuation).
    """
    import re
    s = (s or "").strip().lower()
    s = re.sub(r"\(.*?\)", "", s)         # drop anything in parentheses
    s = re.sub(r"[^a-z0-9]+", "_", s)     # non-alnum -> underscore
    s = s.strip("_")
    return s

_EXPECT_MAP = {
    "doctor_name": {
        "doctor_name", "name", "doctor_s_name", "doctor", "full_name"
    },
    "whatsapp": {
        "whatsapp_number", "doctor_s_whatsapp_number_10_digits_only", "phone", "mobile", "whatsapp"
    },
    "email": {
        "email_id", "email", "email_address"
    },
    "imc_registration_number": {
        "doctor_s_imc_registration_number", "imc_registration_number", "imc_no", "medical_council_no"
    },
    "appointment_booking_number": {
        "clinic_appointment_booking_number_10_digits_only", "clinic_appointment_booking_number", "appointment_number"
    },
    "clinic_address": {
        "clinic_address_with_postal_code", "clinic_address", "address"
    },
    "state": {"state"},
    "district": {"district"},
    "receptionist_whatsapp": {
        "receptionist_whatsapp_number_10_digits_only", "receptionist_whatsapp_number"
    },
    "receptionist_email": {"receptionist_email_id", "receptionist_email"},
    "photo": {"doctor_s_photo", "photo", "photo_url"},
}

def _extract(row: dict, key: str) -> str:
    """Get a value for our canonical `key` from a normalized DictReader row."""
    for candidate in _EXPECT_MAP.get(key, {key}):
        if candidate in row:
            return (row.get(candidate) or "").strip()
    return ""

def _split_name(fullname: str):
    parts = (fullname or "").strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[-1]

def _is_ten_digit(s: str) -> bool:
    import re
    return bool(re.fullmatch(r"\d{10}", (s or "").strip()))

def _is_valid_email(email: str) -> bool:
    import re
    # Allow only Gmail/Googlemail by default (to match your forms and docs).
    m = re.fullmatch(r"[^@\s]+@(gmail\.com|googlemail\.com|inditech\.co\.in)", (email or "").strip(), flags=re.I)
    return bool(m)

def _default_or(value: str, fallback: str) -> str:
    return value if value else fallback

def _ensure_media_default_photo(pro):
    """
    Set default photo to media/profiles/doctor.jpg if nothing was uploaded.
    (File should exist in MEDIA_ROOT/profiles/doctor.jpg)
    """
    if not getattr(pro, "photo_url", None):
        pro.photo_url = None
    if not pro.photo_url:
        pro.photo_url.name = "profiles/doctor.jpg"

def _row_duplicate_exists(whatsapp_10: str, email: str) -> bool:
    """
    Check duplicates by normalized phone (stored as 91XXXXXXXXXX in DB via normalize_phone)
    or case-insensitive email match.
    """
    from .utils import normalize_phone
    normalized = normalize_phone(whatsapp_10)
    return RegisteredProfessional.objects.filter(
        models.Q(whatsapp=normalized) | models.Q(email__iexact=email)
    ).exists()

def _make_clinic_url(request, code: str) -> str:
    return request.build_absolute_uri(reverse("content:clinic_send", args=[code]))

def _write_result_csv(rows: list, file_path: str):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["#","Doctor Name","WhatsApp","Email","Status","Message"])
        for r in rows:
            w.writerow([r["idx"], r["name"], r["whatsapp"], r["email"], r["status"], r["message"]])

@staff_member_required
def bulk_doctor_upload(request):
    """
    Staff-only CSV importer (max 100 rows).
    For each valid & unique row: create doctor, send onboarding (WhatsApp + email), and include in results.
    """
    from .utils import normalize_phone, generate_doctor_code, notify_registration

    ctx = {"form": None}

    if request.method == "POST":
        form = BulkDoctorUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Decode CSV (support UTF-8 with BOM)
            raw = form.cleaned_data["csv_file"].read()
            text = raw.decode("utf-8-sig", errors="ignore")
            # Normalize headers
            sio = io.StringIO(text)
            reader = csv.reader(sio)
            try:
                headers = next(reader)
            except StopIteration:
                ctx["form"] = form
                ctx["summary"] = {"success": 0, "skipped": 0, "failed": 0}
                ctx["rows"] = []
                return render(request, "content/bulk_doctor_upload.html", ctx)

            norm_headers = [_norm_header(h) for h in headers]
            # Make a DictReader over the remaining rows with normalized keys
            data_rows = []
            for row in reader:
                data_rows.append({norm_headers[i]: (row[i] if i < len(row) else "") for i in range(len(norm_headers))})

            if len(data_rows) > 100:
                # Hard limit
                return render(request, "content/bulk_doctor_upload.html", {
                    "form": form,
                    "summary": {"success": 0, "skipped": 0, "failed": 0},
                    "rows": [],
                    "error": "CSV has more than 100 rows. Please split and upload again."
                })

            results = []
            success = skipped = failed = 0

            for idx, r in enumerate(data_rows, start=1):
                name_raw = _extract(r, "doctor_name")
                wa10 = _extract(r, "whatsapp")
                email = _extract(r, "email")
                imc = _extract(r, "imc_registration_number")
                app_no = _extract(r, "appointment_booking_number")
                address = _extract(r, "clinic_address") or "NULL"
                state = _extract(r, "state") or "NULL"
                district = _extract(r, "district") or "NULL"
                recep_wa = _extract(r, "receptionist_whatsapp")
                recep_email = _extract(r, "receptionist_email")

                # Basic validations (strict)
                if not name_raw:
                    failed += 1
                    results.append({"idx": idx, "name": name_raw, "whatsapp": wa10, "email": email,
                                    "status": "FAILED", "message": "Doctor Name is required"})
                    continue
                if not _is_ten_digit(wa10):
                    failed += 1
                    results.append({"idx": idx, "name": name_raw, "whatsapp": wa10, "email": email,
                                    "status": "FAILED", "message": "WhatsApp Number must be exactly 10 digits"})
                    continue
                if not _is_valid_email(email):
                    failed += 1
                    results.append({"idx": idx, "name": name_raw, "whatsapp": wa10, "email": email,
                                    "status": "FAILED", "message": "Email must be a valid Gmail/Googlemail address"})
                    continue
                if not imc:
                    failed += 1
                    results.append({"idx": idx, "name": name_raw, "whatsapp": wa10, "email": email,
                                    "status": "FAILED", "message": "IMC Registration Number is required"})
                    continue

                # Duplicates
                if _row_duplicate_exists(wa10, email):
                    skipped += 1
                    results.append({"idx": idx, "name": name_raw, "whatsapp": wa10, "email": email,
                                    "status": "SKIPPED", "message": "Duplicate (whatsapp/email already exists)"})
                    continue

                # Defaults / normalization
                if not _is_ten_digit(app_no):
                    app_no = wa10
                if not _is_ten_digit(recep_wa):
                    recep_wa = wa10
                if not recep_email:
                    recep_email = email

                first, last = _split_name(name_raw)
                pro = RegisteredProfessional(
                    role="PEDIATRICIAN",
                    salutation="Dr",
                    first_name=first,
                    last_name=last,
                    email=email,
                    whatsapp=normalize_phone(wa10),
                    imc_registration_number=imc,
                    appointment_booking_number=normalize_phone(app_no),
                    clinic_address=address or "NULL",
                    state=state or "NULL",
                    district=district or "NULL",
                    receptionist_whatsapp=normalize_phone(recep_wa),
                    unique_doctor_code=generate_doctor_code(),
                )

                # Attach default photo
                try:
                    _ensure_media_default_photo(pro)
                except Exception:
                    pass

                pro.save()

                # Build clinic link and notify (email + AiSensy)
                clinic_url = _make_clinic_url(request, pro.unique_doctor_code)
                notify_registration(pro, clinic_url)

                success += 1
                results.append({"idx": idx, "name": name_raw, "whatsapp": wa10, "email": email,
                                "status": "SUCCESS", "message": f"Registered. Code: {pro.unique_doctor_code}"})

            # Write a CSV result in media/exports and expose a download link
            stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            rel_path = f"exports/bulk_result_{stamp}.csv"
            file_path = os.path.join(settings.MEDIA_ROOT, rel_path)
            _write_result_csv(results, file_path)
            result_url = settings.MEDIA_URL + rel_path

            ctx.update({
                "form": BulkDoctorUploadForm(),
                "summary": {"success": success, "skipped": skipped, "failed": failed},
                "rows": results,
                "result_csv_url": result_url,
            })
            return render(request, "content/bulk_doctor_upload.html", ctx)
        else:
            ctx["form"] = form
            return render(request, "content/bulk_doctor_upload.html", ctx)

    # GET
    ctx["form"] = BulkDoctorUploadForm()
    return render(request, "content/bulk_doctor_upload.html", ctx)


def ui_text(key: str, lang: str, default: str = "") -> str:
    """
    Fetch UI copy from ui_strings by (key, lang). Falls back to English, then default.
    """
    try:
        return UiString.objects.get(key=key, lang_id=lang).text
    except UiString.DoesNotExist:
        try:
            return UiString.objects.get(key=key, lang_id="en").text
        except UiString.DoesNotExist:
            return default


# -- Helper: build aligned (labels, links) for a set of red-flag IDs --
from django.urls import reverse

def _aligned_rf_labels_and_links(rf_ids, lang, request):
    """
    Given a list of red_flag_codes (rf_ids), return two aligned lists:
    rf_labels[i] corresponds to education_links[i] for the SAME red flag.
    """
    rf_ids = list(dict.fromkeys(rf_ids))  # de-dupe, keep first-seen order
    # Fetch label and slug dicts keyed by red_flag_id
    labels_by_id = dict(
        RedFlagI18n.objects
        .filter(red_flag_id__in=rf_ids, lang_id=lang)
        .values_list("red_flag_id", "parent_label")
    )
    slugs_by_id = dict(
        RedFlag.objects
        .filter(red_flag_code__in=rf_ids)
        .values_list("red_flag_code", "education_url_slug")
    )
    # Build aligned lists in a deterministic order (first-seen order of rf_ids)
    rf_labels = [labels_by_id.get(rf, rf) for rf in rf_ids]
    education_links = [
        request.build_absolute_uri(
            reverse("content:education_page", args=[slugs_by_id.get(rf, "")])
        ) for rf in rf_ids
        if slugs_by_id.get(rf, "")
    ]
    return rf_labels, education_links
