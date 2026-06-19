# emoscreen/urls.py
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from content import views as content_views

urlpatterns = [
    path("admin/bulk-upload/clinic/<str:code>/", content_views.clinic_send, name="legacy_clinic_send"),
    path("admin/bulk-upload/", content_views.bulk_doctor_upload, name="bulk_doctor_upload"),
    path("admin/reports/", content_views.reports_dashboard, name="reports_dashboard"),
    path("admin/reports/export/", content_views.reports_export, name="reports_export"),
    path("admin/", admin.site.urls),
    path("", include("content.urls")),  # your app's other routes
    path("", include("paid.urls")),
    path("oauth/", include("social_django.urls", namespace="social")),  # NEW
    path("auth/complete/", include("content.auth_urls")),               # NEW
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
