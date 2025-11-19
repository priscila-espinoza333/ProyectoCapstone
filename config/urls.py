from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from core import views as core_views
from core.views_admin import admin_bi_dashboard
from core.views_auth import CustomPasswordResetConfirmView

urlpatterns = [
    path("admin/bi-dashboard/", admin_bi_dashboard, name="bi_dashboard"),
    path("admin/", admin.site.urls),

    # Auth
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(
            template_name="core/auth/login.html",
        ),
        name="login",
    ),
    path(
        "accounts/logout/",
        auth_views.LogoutView.as_view(next_page="login"),
        name="logout",
    ),
    path("accounts/signup/", core_views.signup, name="signup"),

    # Reset de contraseña (solo aquí se envía el correo)
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
        CustomPasswordResetConfirmView.as_view(
            template_name="core/auth/password_reset_confirm.html",
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

    path("post-login/", core_views.post_login_redirect, name="post_login_redirect"),


    # (opcional) si decides mantener enviar_link_reset SOLO como redirect
    path(
        "cuenta/enviar-reset/",
        core_views.enviar_link_reset,
        name="enviar_link_reset",
    ),

    # App principal
    path("", include("core.urls")),
]
