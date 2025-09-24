# content/utils.py

import re
import secrets
import urllib.parse
import requests
from django.conf import settings
from django.core import signing  # NEW import added here

# --- Signed-token helpers (added near the top) ---
_VERI_SALT = "verify_phone_v1"

def last10_digits(s: str) -> str:
    """Return the last 10 digits from any phone-like string."""
    return re.sub(r"\D", "", s or "")[-10:]

def make_verify_token(pro_code: str, parent_phone: str) -> str:
    """
    Create a signed token that encodes (last10-digits, pro code).
    """
    data = {"p": last10_digits(parent_phone), "c": pro_code}
    return signing.dumps(data, salt=_VERI_SALT)

def read_verify_token(token: str, max_age_days: int = 7) -> dict:
    """
    Read & verify a token. Raises BadSignature/SignatureExpired on failure.
    """
    secs = max_age_days * 24 * 3600
    return signing.loads(token, salt=_VERI_SALT, max_age=secs)
# --------------------- WhatsApp text to PARENT (from your doc) ---------------------  :contentReference[oaicite:1]{index=1}
PARENT_WA_TEMPLATES = {
    "en": ("Hello,\n\nIn this message I’m sending you the evaluation form for Behavioral and Emotional Red Flags\n\n"
           "Please answer its questions carefully and if the response received indicates any areas of concern, please visit my clinic. Click Here:\n{link}"),
    "hi": ("नमस्ते,\n\nइस संदेश में मैं आपको Behavioral and Emotional Red Flags के लिए एक फ़ॉर्म भेज रहा हूँ\n\n"
           "कृपया इसके प्रश्नों का उत्तर सावधानी से दें और यदि फॉर्म का रिस्पांस किसी भी प्रकार की चिंता का संकेत देता है, तो कृपया मेरे क्लिनिक पर आकर मुझसे मिलें।\n\nयहाँ क्लिक करें:\n{link}"),
    "ta": ("வணக்கம்,\n\nஇந்தச் செய்தியில் நான் உங்களுக்கு Behavioral and Emotional Red Flags படிவத்தை அனுப்புகிறேன்\n\n"
           "இங்கே கிளிக் செய்யவும்:\n{link}"),
    "te": ("హలో,\n\nఈ సందేశంలో నేను మీకు Behavioral and Emotional Red Flags పంపుతున్నాను\n\n"
           "ఇక్కడ ఉన్న లింక్ ను నొక్కండి:\n{link}"),
    "ml": ("ഹലോ,\n\nഈ സന്ദേശത്തിൽ ഞാൻ നിങ്ങൾക്ക് Behavioral and Emotional Red Flags അയയ്ക്കുന്നു.\n\n"
           "ഇവിടെ ക്ലിക്ക് ചെയ്യുക:\n{link}"),
    "mr": ("नमस्कार,\n\nया मेसेजमध्ये मी तुम्हाला Behavioral and Emotional Red Flags साठी मूल्यांकन फॉर्म पाठवत आहे\n\n"
           "येथे क्लिक करा:\n{link}"),
    "bn": ("হ্যালো,\n\nএই বার্তায় আমি আপনাকে Behavioral and Emotional Red Flags পাঠাচ্ছি\n\n"
           "এখানে ক্লিক করুন:\n{link}"),
    "kn": ("ಹಲೋ,\n\nಈ ಸಂದೇಶದಲ್ಲಿ ನಾನು ನಿಮಗೆ Behavioral and Emotional Red Flags ಕಳುಹಿಸುತ್ತಿದ್ದೇನೆ\n\n"
           "ಇಲ್ಲಿ ಕ್ಲಿಕ್ ಮಾಡಿ:\n{link}"),
}

# --------------------- Email CTA text (doctor report) ---------------------  :contentReference[oaicite:2]{index=2}
ADVISE_PATIENT_TEXT = (
    "Dear Patient,\n"
    "I recommend that you bring your child to the clinic for a check-up, as some concerns have been noticed within the child. "
    "Please contact my clinic to schedule a convenient time for the visit.\n"
    "Best regards,\n"
    "Dr. {doctor_name}"
)

# --------------------- Patient booking message (buttons on patient result) ---------------------  :contentReference[oaicite:3]{index=3}
def booking_message_for_clinic(patient_name: str) -> str:
    name = patient_name or "a patient"
    return (
        f"Hello, this is {name} a patient of your clinic.\n\n"
        "I have filled up the Behavioral and Emotional Red Flags form and the report shows some issues. "
        "I want to book an appointment with the doctor.\n\n"
        "Please let me know the clinic timings to book an appointment or send me the appointment booking link."
    )


# --------------------- Small helpers ---------------------
def normalize_phone(s: str) -> str:
    """Keep digits only; add India code 91 if given a 10-digit local number."""
    if not s:
        return s
    digits = re.sub(r"\D", "", s)
    if len(digits) == 10:
        digits = "91" + digits
    return digits

def generate_doctor_code() -> str:
    return secrets.token_hex(4).upper()  # 8 hex chars

def generate_report_code() -> str:
    return secrets.token_hex(6).upper()  # 12 hex chars

def whatsapp_link(phone_digits: str, message: str) -> str:
    return f"https://wa.me/{phone_digits}?text={urllib.parse.quote(message)}"

def parent_message(lang_code: str, link: str) -> str:
    tpl = PARENT_WA_TEMPLATES.get(lang_code, PARENT_WA_TEMPLATES["en"])
    return tpl.format(link=link)

def white_label_context(pro):
    """Header block data for white-labeled pages; always provide a plain URL for photo."""
    display_name = (pro.first_name or "")
    if pro.last_name:
        display_name = f"{display_name} {pro.last_name}".strip()
    display_name = display_name or "Clinic"
    if pro.role == "CAREGIVER" and not pro.first_name:
        display_name = "Caregiver"

    photo_url = ""
    try:
        if pro.photo_url:
            photo_url = pro.photo_url.url if hasattr(pro.photo_url, "url") else str(pro.photo_url)
    except Exception:
        photo_url = str(pro.photo_url or "")

    return {
        "pro_name": f"{pro.salutation or ''} {display_name}".strip(),
        "pro_photo_url": photo_url,
        "clinic_address": pro.clinic_address,
        "appointment_number": pro.appointment_booking_number,
        "pro": pro,
    }

def clinic_contact_numbers(pro):
    """
    Prefer appointment_booking_number, else receptionist_whatsapp, else doctor's WhatsApp.
    Returns (tel_target_digits, whatsapp_target_digits) or (None, None).
    """
    tel_digits = normalize_phone(pro.appointment_booking_number or "") or \
                 normalize_phone(pro.receptionist_whatsapp or "") or \
                 normalize_phone(pro.whatsapp or "")
    wa_digits = tel_digits
    return (tel_digits, wa_digits)

# --------------------- Email (SendGrid) ---------------------
def _sendgrid_send(to_email: str, subject: str, html: str):
    if not settings.SENDGRID_API_KEY:
        print("[SendGrid] missing SENDGRID_API_KEY; printing email to console instead")
        print("To:", to_email); print("Subject:", subject); print("HTML:\n", html)
        return False
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email, To
        message = Mail(
            from_email=Email(settings.DEFAULT_FROM_EMAIL, settings.REPORT_FROM_NAME),
            to_emails=To(to_email),
            subject=subject,
            html_content=html,
        )
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        resp = sg.send(message)
        print(f"[SendGrid] status={resp.status_code}")
        return 200 <= resp.status_code < 300
    except Exception as e:
        body = getattr(e, "body", "")
        print("[SendGrid] error:", e, "\nBody:", body)
        return False

# --------------------- WhatsApp (AiSensy) ---------------------
def _valid_aisensy_destination(msisdn: str) -> bool:
    """AiSensy expects strictly '91' + 10 digits. No '+'."""
    return bool(re.fullmatch(r"91\d{10}", msisdn or ""))

def _ensure_param_count(params, expected):
    """Ensure the params list contains exactly `expected` strings."""
    p = ["" if v is None else str(v) for v in params]
    if len(p) < expected:
        p += [""] * (expected - len(p))
    elif len(p) > expected:
        p = p[:expected]
    return p

def _aisensy_send(destination_digits: str, username: str, template_params):
    """
    Trigger AiSensy template.
    Your approved template (screenshot) has **three** placeholders: {1} Name, {2} Link, {3} How-to.  :contentReference[oaicite:4]{index=4}
    We therefore send exactly three params in this order.
    """
    api_key = getattr(settings, "AISENSY_API_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjYzZjBkNDBlMzMxNjBhNzE5ODNhOTdjMCIsIm5hbWUiOiJJbmRpdGVjaCIsImFwcE5hbWUiOiJBaVNlbnN5IiwiY2xpZW50SWQiOiI2M2YwZDQwZTMzMTYwYTcxOTgzYTk3YmIiLCJhY3RpdmVQbGFuIjoiQkFTSUNfTU9OVEhMWSIsImlhdCI6MTY3NjcyNzMxMH0.pgz-k3jtvpn3WCYDmQ8MXyf1BR4xG-4yqYnm3d0SLeU")
    campaign = getattr(settings, "AISENSY_CAMPAIGN_NAME", "emoscreennew1509_1")
    expected_count = int(getattr(settings, "AISENSY_PARAM_COUNT", 3))  # default to 3

    if not api_key:
        print("[AiSensy] missing API key; skipping")
        return False

    dest = normalize_phone(destination_digits)
    if not _valid_aisensy_destination(dest):
        print(f"[AiSensy] destination invalid: {dest!r}; expected 91XXXXXXXXXX. Skipping.")
        return False

    params = _ensure_param_count(list(template_params or []), expected_count)

    url = "https://backend.aisensy.com/campaign/t1/api"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    # --- primary shape (per your PHP sample) ---
    body = {
        "apiKey": api_key,
        "campaignName": campaign,
        "destination": dest,
        "userName": str(username or ""),
        "templateParams": params,
    }
    try:
        r = requests.post(url, json=body, timeout=20, headers=headers)
        print("[AiSensy] primary status:", r.status_code, "resp:", r.text[:500])
        if r.ok:
            return True
        # --- fallback shape (some tenants require 'destinations': [dest]) ---
        body2 = {
            "apiKey": api_key,
            "campaignName": campaign,
            "destinations": [dest],
            "userName": str(username or ""),
            "templateParams": params,
        }
        r2 = requests.post(url, json=body2, timeout=20, headers=headers)
        print("[AiSensy] fallback status:", r2.status_code, "resp:", r2.text[:500])
        return r2.ok
    except Exception as e:
        print("[AiSensy] error:", e)
        return False

def notify_registration(pro, clinic_url: str):
    """
    Send the Doctor onboarding email (SendGrid) and AiSensy WhatsApp template.
    Doctor’s WhatsApp template uses exactly THREE params: [DoctorName, ClinicLink, HowToGuide].  :contentReference[oaicite:5]{index=5}
    """
    doc_name = f"{pro.salutation or ''} {pro.first_name or ''} {pro.last_name or ''}".strip()
    how_to_use = "https://bit.ly/43QkzpM"  # as in your approved copy

    # --- Email (SendGrid) ---
    html = f"""
      <div style="font-family:Arial,sans-serif">
        <p>Hello {doc_name},</p>
        <p>Thank you for registering for the Emotional &amp; Behavioural Screening Tool – an initiative supported by SAPA.</p>
        <p>This tool is designed to help you easily screen children for early behavioural and emotional concerns within your routine practice.</p>
        <p>Your personalized screening tool is now ready.</p>
        <p><strong>Clinic Link:</strong> <a href="{clinic_url}" target="_blank">{clinic_url}</a><br/>
           <strong>How to Use Guide:</strong> <a href="{how_to_use}" target="_blank">{how_to_use}</a></p>
      </div>
    """
    _sendgrid_send(pro.email, "Your Emoscreen personalized clinic link", html)

    # --- WhatsApp (AiSensy) ---
    # EXACTLY THREE PARAMS to match the approved template: {1} Name, {2} Link, {3} How-to Guide
    params = [doc_name, clinic_url, how_to_use]
    _aisensy_send(normalize_phone(pro.whatsapp), doc_name, params)
