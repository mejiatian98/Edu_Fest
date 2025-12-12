# --------------------------------------------
# SETTINGS.PY — DJANGO + RENDER + AWS S3
# --------------------------------------------

from pathlib import Path
import os
from django.core.management.utils import get_random_secret_key
from dotenv import load_dotenv
import dj_database_url
from decouple import config

# --------------------------------------------
# BASE DIR & ENV
# --------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")  # Cargar .env local si existe

SECRET_KEY = os.getenv("SECRET_KEY") or get_random_secret_key()

# --------------------------------------------
# DEBUG / PRODUCCIÓN
# --------------------------------------------

IS_PRODUCTION = os.getenv("RENDER_EXTERNAL_HOSTNAME") is not None
DEBUG = not IS_PRODUCTION


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

    # Tu proyecto
    'app_usuarios.apps.AppUsuariosConfig',
    'app_admin_eventos',
    'app_asistentes',
    'app_participantes',
    'app_evaluadores',

    # Email Brevo
    'anymail',

    # AWS S3
    'storages',
]


# --------------------------------------------
# sitio ID (importante para django.contrib.sites)
# --------------------------------------------
SITE_ID = 1


# --------------------------------------------
# MIDDLEWARE
# --------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Necesario en Render
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

if DEBUG:
    # DEV – MySQL
    from decouple import config
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST'),
            'PORT': config('DB_PORT'),
        }
    }
else:
    # PRODUCCIÓN – PostgreSQL en Render
    DATABASES = {
        'default': dj_database_url.config(
            default=os.getenv("DATABASE_URL"),
            conn_max_age=600,
            ssl_require=True,
        )
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
# MEDIA FILES
# ---------------------------------------------------
if DEBUG:
    # Local media
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

else:
    # Amazon S3 media
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

    AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME")

    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"

    AWS_QUERYSTRING_AUTH = False
    AWS_DEFAULT_ACL = "public-read"




# ---------------------------------------------------
# EMAIL: Gmail en DEV, Brevo en PROD
# ---------------------------------------------------
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = config("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")
    DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL")

else:
    EMAIL_BACKEND = "anymail.backends.brevo.EmailBackend"
    BREVO_API_KEY = config("BREVO_API_KEY")
    DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL")
