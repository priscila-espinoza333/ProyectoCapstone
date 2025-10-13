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
ALLOWED_HOSTS = ["*"] if DEBUG else os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",")

# --- Apps ---
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps del proyecto
    "core",
    "users",
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

# --- Templates ---
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Si usas templates a nivel de proyecto:
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
# Evita el warning W004 agregando solo rutas que existan
STATICFILES_DIRS = [
    p for p in [
        BASE_DIR / "static",          # estáticos globales (crea la carpeta si la usarás)
        BASE_DIR / "core" / "static", # estáticos de la app core (si existe)
    ] if p.exists()
]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Autenticación ---
AUTH_USER_MODEL = "users.User"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "mis_reservas"  # cambia si tu nombre de URL es distinto
LOGOUT_REDIRECT_URL = "login"        # "index" te daba 404 si no existe

# --- Email ---
# Para desarrollo, usa consola (no envía correos, imprime en terminal)
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)

# Config SMTP solo si no usas consola (produce errores si no hay credenciales)
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "1") == "1"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "no-reply@matchplay.local")

# --- Datos de contacto públicos (para vistas/páginas) ---
CONTACT_EMAIL_TO = os.getenv("CONTACT_EMAIL_TO", EMAIL_HOST_USER or "contacto@ejemplo.cl")
CONTACT_PHONE = os.getenv("CONTACT_PHONE", "+56 2 2857 3111")
CONTACT_PHONE_ALT = os.getenv("CONTACT_PHONE_ALT", "+56 2 2857 7472")
CONTACT_ADDRESS = os.getenv("CONTACT_ADDRESS", "El Barrancón 3240, San Bernardo, Santiago")
CONTACT_INSTAGRAM = os.getenv("CONTACT_INSTAGRAM", "https://instagram.com/matchplay")
CONTACT_WHATSAPP = os.getenv("CONTACT_WHATSAPP", "56912345678")  # solo dígitos con país

# --- Transbank (usa variables de entorno, no lo hardcodees) ---
WEBPAY_PLUS_COMMERCE_CODE = os.getenv("WEBPAY_PLUS_COMMERCE_CODE", "597055555532")  # TEST
WEBPAY_PLUS_API_KEY = os.getenv("WEBPAY_PLUS_API_KEY", "")
WEBPAY_PLUS_ENV = os.getenv("WEBPAY_PLUS_ENV", "TEST")  # TEST o LIVE

# --- APIs externas (no hardcodees claves reales) ---
OPENWEATHERMAP_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY", "")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")

# --- Celery ---
# Ojo: para que Celery funcione, debes definir CELERY_BROKER_URL y correr worker/beat.
# Configuración de Transbank Webpay
#WEBPAY_PLUS_COMMERCE_CODE = '597055555532'  # Código de comercio para pruebas
#WEBPAY_PLUS_API_KEY = '579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C'        # Para ambiente de pruebas, el API Key es el mismo
#WEBPAY_PLUS_ENV = 'TEST'                    # Puede ser 'TEST' o 'LIVE'

TRANSBANK_COMMERCE_CODE = os.getenv("TRANSBANK_COMMERCE_CODE", "597055555532")
TRANSBANK_API_KEY = os.getenv("TRANSBANK_API_KEY", "579B532A7440BB0C")
TRANSBANK_ENVIRONMENT = os.getenv("TRANSBANK_ENVIRONMENT", "TEST")

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('recintodeportivomatchplay@gmail.com')
EMAIL_HOST_PASSWORD = os.getenv('Admin.1234')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

#SendGrid API Key

SENDGRID_API_KEY = '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'
DEFAULT_FROM_EMAIL = 'recintodeportivomatchplay@gmail.com'

CELERY_BEAT_SCHEDULE = {
    "limpiar-reservas-expiradas-every-1-minute": {
        "task": "core.tasks.tarea_limpiar_reservas_expiradas",
        "schedule": 60.0,
    },
}

CSRF_FAILURE_VIEW = "core.views_errors.csrf_failure"
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
