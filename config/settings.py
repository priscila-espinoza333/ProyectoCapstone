"""
Django settings for config project.
"""

from pathlib import Path
import os

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Seguridad y entorno ---
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-not-for-prod")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if not DEBUG else ["*"]

# --- Apps ---
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Si tienes /templates a nivel de proyecto, descomenta o mantén:
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Base de datos ---
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# --- Password validators ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- i18n ---
LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

# --- Archivos estáticos y media ---
STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",          # estáticos globales 
    BASE_DIR / "core" / "static", # estáticos de la app core
]
# En producción,  ejecutar collectstatic hacia STATIC_ROOT:
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Email ---
# Para desarrollo: imprime los correos en la consola
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"      # <-- CORRECTO PARA GMAIL
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
CONTACT_EMAIL_TO = os.getenv("CONTACT_EMAIL_TO", EMAIL_HOST_USER)

# --- Datos de contacto públicos (para la vista de contacto) ---
CONTACT_EMAIL_TO = os.getenv("CONTACT_EMAIL_TO", EMAIL_HOST_USER or "contacto@ejemplo.cl")
CONTACT_PHONE = os.getenv("CONTACT_PHONE", "+56 2 2857 3111")
CONTACT_PHONE_ALT = os.getenv("CONTACT_PHONE_ALT", "+56 2 2857 7472")
CONTACT_ADDRESS = os.getenv("CONTACT_ADDRESS", "El Barrancón 3240, San Bernardo, Santiago")
CONTACT_INSTAGRAM = os.getenv("CONTACT_INSTAGRAM", "https://instagram.com/matchplay")
CONTACT_WHATSAPP = os.getenv("CONTACT_WHATSAPP", "56912345678")  # solo dígitos con país

# LOGIN
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "mis_reservas"
LOGOUT_REDIRECT_URL = "index"
