# content/auth_urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.auth_complete, name="auth_complete"),  # handles post-login verification
    path("logout/", views.auth_logout, name="auth_logout"),
]
