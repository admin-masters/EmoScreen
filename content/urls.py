# content/urls.py
from django.urls import path
from . import views

app_name = "content"

urlpatterns = [
    # Registration
    path("", views.registration_choice, name="registration_choice"),
    path("register/pediatrician/", views.register_pediatrician, name="register_pediatrician"),
    path("register/caregiver/", views.register_caregiver, name="register_caregiver"),

    # After registration, doctor/caregiver uses this "clinic link"
    path("clinic/<str:code>/", views.clinic_send, name="clinic_send"),

    # Parent flow
    path("screen/<str:code>/", views.parent_language_select, name="parent_language_select"),
    path("screen/<str:code>/<str:lang>/", views.screening_form, name="screening_form"),

    # On-screen result (if you want a separate route)
    path("result/<str:report_code>/", views.view_result, name="view_result"),

    # Doctor education
    path("education/<slug:slug>/", views.education_page, name="education_page"),

    path("admin/bulk-upload/", views.bulk_doctor_upload, name="bulk_doctor_upload"),

    # content/urls.py
    path("auth/complete/", views.auth_complete, name="auth_complete"),
    path("auth/logout/", views.auth_logout, name="auth_logout"),

    path("verify/<code>/<token>/", views.verify_phone, name="verify_phone"),

    path("terms/<code>/", views.terms_accept, name="terms_accept"),
    path("terms/", views.terms_public, name="terms_public"),
    path("admin/reports/", views.reports_dashboard, name="reports_dashboard"),            # NEW
    path("admin/reports/export/", views.reports_export, name="reports_export"),   
    path("admin/bulk-upload/admin/reports/", views.reports_dashboard),                   # TEMP
    path("admin/bulk-upload/admin/reports/export/", views.reports_export),               # TEMP

]
