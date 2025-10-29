"""
URL configuration for config project.
"""

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from core import views as core_views
from core.views_admin import admin_bi_dashboard  

urlpatterns = [

    # --- Dashboard BI dentro del Admin ---
   path("admin/bi-dashboard/", admin_bi_dashboard, name="bi_dashboard"),

    # --- Panel admin de Django ---
    path("admin/", admin.site.urls),

    # --- App principal ---
    path("", include("core.urls")),

    # --- Autenticación (templates en templates/core/auth/) ---
    # Login / Logout / Signup
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="core/auth/login.html"),
        name="login",
    ),
    path(
        "accounts/logout/",
        auth_views.LogoutView.as_view(next_page="login"),
        name="logout",
    ),
    path("accounts/signup/", core_views.signup, name="signup"),

    # --- Recuperación de contraseña por correo ---
    path(
        "accounts/password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="core/auth/password_reset.html",
            email_template_name="core/auth/emails/password_reset_email.txt",
            html_email_template_name="core/auth/emails/password_reset_email.html",
            subject_template_name="core/auth/emails/password_reset_subject.txt",
        ),
        name="password_reset",
    ),
    path(
        "accounts/password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="core/auth/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "accounts/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="core/auth/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "accounts/reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="core/auth/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

    # --- Enviar enlace de reset desde el perfil (1 clic) ---
    path(
        "cuenta/enviar-reset/",
        core_views.enviar_link_reset,
        name="enviar_link_reset",
    ),
]
