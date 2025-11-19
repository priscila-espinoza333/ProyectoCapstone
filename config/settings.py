"""
Django settings for config project.
"""
from pathlib import Path
import os
from dotenv import load_dotenv

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

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
    # Habilitar filtros como intcomma
    'django.contrib.humanize',
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
    "core.middleware.AdminSessionHardeningMiddleware",
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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "matchplay",
        "USER": "app_user",
        "PASSWORD": "SafePass2025!",
        "HOST": "127.0.0.1",
        "PORT": "5432",
        "CONN_MAX_AGE": 60,
    }
}

# ============================
#   CONFIGURACIÓN DE SESIONES
# ============================

# --- Cookies / Seguridad general ---
SESSION_COOKIE_NAME = "mp_sessionid"
SESSION_COOKIE_SECURE = not DEBUG      # True en prod (HTTPS), False en dev
CSRF_COOKIE_SECURE = not DEBUG         # True en prod (HTTPS), False en dev
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False           # CSRF no puede ser HttpOnly
SESSION_COOKIE_SAMESITE = "Lax"        # "Strict" si no embebes en iframes

# --- Persistencia por defecto para usuarios finales ---
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7   # 7 días
SESSION_SAVE_EVERY_REQUEST = True       # Renueva vencimiento si hay actividad


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

SESSION_EXPIRE_SECONDS = 1800  # 30 minutos
SESSION_EXPIRE_AFTER_LAST_ACTIVITY = True
SESSION_TIMEOUT_REDIRECT = '/login/'


# --- Email ---
# Para desarrollo, usa consola (no envía correos, imprime en terminal)
#EMAIL_BACKEND = os.getenv(
#    "EMAIL_BACKEND",
#    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
#)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = os.getenv("EMAIL_HOST")                 # ej: smtp.gmail.com
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))     # 587 = TLS
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "1") == "1"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "0") == "1"

EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")       # correo completo
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

# Emisor por defecto
DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    EMAIL_HOST_USER  # Si no defines otro, usa el mismo correo
)

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
# Webpay Plus (Transbank)
TBK_ENV = "TEST"  # "LIVE" para producción
TBK_COMMERCE_CODE = "597055555532"   # sandbox oficial Webpay Plus
TBK_API_KEY = "579B532A7440BB0C"     # sandbox oficial Webpay Plus


##MERCADO PAG
MERCADOPAGO_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN_TEST", "APP_USR-4405580064406280-111214-d83f062de946609bcdaaf6076cf10632-2985296633")  # <-- PON AQUÍ TU TOKEN TEST
MERCADOPAGO_TEST_BUYER_EMAIL = "montesluis984@gmail.com"   # comprador (payer)
MERCADOPAGO_TEST_SELLER_EMAIL = "TESTUSER2518639870572899821@testuser.com" 

MERCADOPAGO_SUCCESS_URL = "http://127.0.0.1:8000/pagos/mp/success/"
MERCADOPAGO_FAILURE_URL = "http://127.0.0.1:8000/pagos/mp/failure/"
MERCADOPAGO_PENDING_URL = "http://127.0.0.1:8000/pagos/mp/pending/"
MERCADOPAGO_WEBHOOK_URL = "http://127.0.0.1:8000/pagos/mp/webhook/"



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



# Aumentar límite de campos que acepta Django en un POST
DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000  # o 10000 si quieres ir sobrado
LOGIN_REDIRECT_URL = "post_login_redirect"



