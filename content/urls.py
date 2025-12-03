from django.urls import path
from . import views

app_name = "content"

urlpatterns = [
    # Registration
    path("", views.registration_choice, name="registration_choice"),
    path("register/pediatrician/", views.register_pediatrician, name="register_pediatrician"),
    path("register/caregiver/", views.register_caregiver, name="register_caregiver"),

    # Clinic / parent flow
    path("clinic/<str:code>/", views.clinic_send, name="clinic_send"),
    path("screen/<str:code>/", views.parent_language_select, name="parent_language_select"),
    path("screen/<str:code>/<str:lang>/", views.screening_form, name="screening_form"),
    path("result/<str:report_code>/", views.view_result, name="view_result"),

    # Doctor education
    path("education/<slug:slug>/", views.education_page, name="education_page"),

    # Admin
    path("admin/bulk-upload/", views.bulk_doctor_upload, name="bulk_doctor_upload"),
    path("admin/reports/", views.reports_dashboard, name="reports_dashboard"),
    path("admin/reports/export/", views.reports_export, name="reports_export"),

    # Auth
    path("auth/complete/", views.auth_complete, name="auth_complete"),
    path("auth/logout/", views.auth_logout, name="auth_logout"),

    # Verification & terms
    path("verify/<code>/<token>/", views.verify_phone, name="verify_phone"),
    path("verify/<code>/", views.verify_phone, name="verify_phone"),
    path("terms/<code>/", views.terms_accept, name="terms_accept"),
    path("terms/", views.terms_public, name="terms_public"),

    # Share / QR codes
    path("share/<code>/", views.share_landing, name="share_landing"),

    # --- IMPORTANT FIX: STATIC QR ROUTES MUST COME BEFORE DYNAMIC ONE ---
    path("qr/global.svg", views.global_qr_svg, name="global_qr_svg"),
    path("qr/self.svg", views.self_qr_svg, name="self_qr_svg"),

    # Dynamic QR route (must remain LAST)
    path("qr/<code>.svg", views.doctor_qr_svg, name="doctor_qr_svg"),

    # Start routes
    path("start/universal/", views.universal_entry, name="universal_entry"),
    path("start/global/", views.global_start, name="global_start"),
    path("start/self/", views.self_start, name="self_start"),
]
