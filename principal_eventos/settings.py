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
DEBUG = not IS_PRODUCTION   # En Render siempre será False

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
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST'),
            'PORT': config('DB_PORT'),
            'OPTIONS': {"init_command": "SET sql_mode='STRICT_TRANS_TABLES'"},
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
# SITES FRAMEWORK
# --------------------------------------------
SITE_ID = 1

# --------------------------------------------
# STATIC FILES
# --------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

if IS_PRODUCTION:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# --------------------------------------------
# MEDIA FILES – AWS S3 (Solo en Producción)
# --------------------------------------------

if IS_PRODUCTION:
    # PRODUCCIÓN: Usar AWS S3
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "us-east-1")
    
    # Configuración de S3
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    AWS_DEFAULT_ACL = 'public-read'
    AWS_QUERYSTRING_AUTH = False
    AWS_S3_FILE_OVERWRITE = False
    
    # URLs para archivos media
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
    
    # Configurar STORAGES para Django 4.2+
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
else:
    # DESARROLLO: Usar almacenamiento local
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / "media"
    
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

# --------------------------------------------
# EMAIL – GMAIL EN DEV, BREVO EN PRODUCCIÓN
# --------------------------------------------

if DEBUG:
    # DESARROLLO: Usar Gmail
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
    EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
    DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@localhost")
    print(f"📧 Modo desarrollo: Enviando emails con Gmail ({EMAIL_HOST_USER})")
else:
    # PRODUCCIÓN: Usar Brevo
    EMAIL_BACKEND = "anymail.backends.brevo.EmailBackend"
    DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@example.com")
    BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
    
    ANYMAIL = {
        "BREVO_API_KEY": BREVO_API_KEY,
        "BREVO_API_URL": "https://api.brevo.com/v3/",
    }
    print(f"📧 Modo producción: Enviando emails con Brevo ({DEFAULT_FROM_EMAIL})")

# --------------------------------------------
# SEGURIDAD EN PRODUCCIÓN
# --------------------------------------------

if IS_PRODUCTION:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# --------------------------------------------
# DEFAULT PRIMARY KEY
# --------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'