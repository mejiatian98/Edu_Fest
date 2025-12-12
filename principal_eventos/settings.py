# --------------------------------------------
# SETTINGS.PY — DJANGO + RENDER + AWS S3
# --------------------------------------------

from pathlib import Path
import os
from django.core.management.utils import get_random_secret_key
from dotenv import load_dotenv
import dj_database_url
from decouple import config, UndefinedValueError
import logging

logger = logging.getLogger(__name__)

# --------------------------------------------
# BASE DIR & ENV
# --------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY") or get_random_secret_key()

# --------------------------------------------
# DEBUG / PRODUCCIÓN
# --------------------------------------------
IS_PRODUCTION = os.getenv("RENDER_EXTERNAL_HOSTNAME") is not None
DEBUG = config('DEBUG', default=False, cast=bool)

# --------------------------------------------
# ALLOWED HOSTS
# --------------------------------------------
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# --------------------------------------------
# APPS
# --------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'app_usuarios.apps.AppUsuariosConfig',
    'app_admin_eventos',
    'app_asistentes',
    'app_participantes',
    'app_evaluadores',
    'anymail',
    'storages',
]

SITE_ID = 1

# --------------------------------------------
# MIDDLEWARE
# --------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'principal_eventos.urls'

# --------------------------------------------
# TEMPLATES
# --------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / "templates",
            "app_admin_eventos/templates/app_admin_eventos",
            "app_evaluadores/templates/app_evaluadores",
            "app_participantes/templates/app_participantes",
            "app_asistentes/templates/app_asistentes",
            "app_usuarios/templates/app_usuarios",
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'principal_eventos.wsgi.application'

# --------------------------------------------
# BASE DE DATOS
# --------------------------------------------
if IS_PRODUCTION:
    DATABASES = {
        'default': dj_database_url.config(
            default=os.getenv("DATABASE_URL"),
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('DB_NAME', default='bd_edufest'),
            'USER': config('DB_USER', default='root'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='3306'),
        }
    }

# --------------------------------------------
# AUTH
# --------------------------------------------
AUTH_USER_MODEL = 'app_usuarios.Usuario'
LOGIN_URL = 'login_view'

# --------------------------------------------
# STATIC FILES
# --------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

if IS_PRODUCTION:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ---------------------------------------------------
# MEDIA FILES - AWS S3
# ---------------------------------------------------
USE_S3 = IS_PRODUCTION

if USE_S3:
    try:
        AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID")
        AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
        AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")
        AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default="us-east-2")
        
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_STORAGE_BUCKET_NAME:
            STORAGES = {
                "default": {
                    "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
                },
                "staticfiles": {
                    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
                },
            }

            AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com"
            MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"
            
            AWS_S3_OBJECT_PARAMETERS = {
                'CacheControl': 'max-age=86400',
            }
            
            # ⭐ SIN ACL - Usa bucket policy en su lugar
            AWS_QUERYSTRING_AUTH = False
            AWS_DEFAULT_ACL = None
            AWS_S3_FILE_OVERWRITE = False
            AWS_S3_VERIFY = True
            
            logger.info("✅ AWS S3 configurado correctamente")
        else:
            raise ValueError("Credenciales de AWS incompletas")
            
    except Exception as e:
        logger.error(f"❌ Error configurando AWS S3: {e}")
        USE_S3 = False
        MEDIA_URL = "/media/"
        MEDIA_ROOT = BASE_DIR / "media"
else:
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------
# EMAIL CONFIGURATION
# ---------------------------------------------------
try:
    USE_BREVO = config('USE_BREVO', default=False, cast=bool)
    
    if USE_BREVO:
        BREVO_API_KEY = config("BREVO_API_KEY")
        
        if BREVO_API_KEY:
            EMAIL_BACKEND = "anymail.backends.brevo.EmailBackend"
            ANYMAIL = {
                "BREVO_API_KEY": BREVO_API_KEY,
            }
            DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@ejemplo.com")
            logger.info("✅ Email configurado con Brevo")
        else:
            raise ValueError("BREVO_API_KEY no encontrado")
    else:
        EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
        EMAIL_HOST = 'smtp.gmail.com'
        EMAIL_PORT = 587
        EMAIL_USE_TLS = True
        EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
        EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
        DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@ejemplo.com")
        logger.info("✅ Email configurado con Gmail")
        
except Exception as e:
    logger.error(f"❌ Error configurando email: {e}")
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = "noreply@ejemplo.com"
    logger.warning("⚠️ Email configurado para mostrar en consola")

# ---------------------------------------------------
# SECURITY (PRODUCCIÓN)
# ---------------------------------------------------
if IS_PRODUCTION:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

# ---------------------------------------------------
# PASSWORD VALIDATION
# ---------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------
# INTERNATIONALIZATION
# ---------------------------------------------------
LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------
# DEFAULT PRIMARY KEY
# ---------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------
# SUPERADMIN EMAIL
# ---------------------------------------------------
SUPERADMIN_EMAIL = config('SUPERADMIN_EMAIL', default='admin@ejemplo.com')