from pathlib import Path
from django.core.management.utils import get_random_secret_key
import os
from decouple import config
import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar variables del .env
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY") or get_random_secret_key()

# Debug = solo True si no se está ejecutando en Render
DEBUG = 'RENDER' not in os.environ

ALLOWED_HOSTS = ['localhost', '127.0.0.1']
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# ----------------------------------------------------------------------
# APLICACIONES
# ----------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # Apps
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



# ----------------------------------------------------------------------
# MIDDLEWARE
# ----------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
]

ROOT_URLCONF = 'principal_eventos.urls'

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

# ----------------------------------------------------------------------
# BASE DE DATOS
# ----------------------------------------------------------------------
if DEBUG:
    # MySQL LOCAL
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
    # PostgreSQL en Render (automático)
    DATABASES = {
        'default': dj_database_url.config(
            default=os.getenv("DATABASE_URL"),
            conn_max_age=600,
            ssl_require=True
        )
    }

# ----------------------------------------------------------------------
# AUTENTICACIÓN
# ----------------------------------------------------------------------
AUTH_USER_MODEL = 'app_usuarios.Usuario'
LOGIN_URL = 'login_view'

# ----------------------------------------------------------------------
# ARCHIVOS ESTÁTICOS (CSS, JS)
# ----------------------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ----------------------------------------------------------------------
# MEDIA (IMÁGENES Y ARCHIVOS) CON AWS S3
# ----------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

# Detecta si estás en producción (Render) usando una variable del sistema
IS_PRODUCTION = os.getenv("RENDER") == "true"

if IS_PRODUCTION:
    # ----------------------------
    #   AWS S3 (Producción)
    # ----------------------------
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "us-east-1")

    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"

    # Archivos subidos por usuarios
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

    # Archivos estáticos (opcional, puedes dejarlos en Render)
    # STATICFILES_STORAGE = "storages.backends.s3boto3.S3StaticStorage"

    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"
    # AWS S3 NO USA MEDIA_ROOT

else:
    # ----------------------------
    #   Local (Desarrollo)
    # ----------------------------
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"


# ----------------------------------------------------------------------
# CORREO (Brevo o Gmail)
# ----------------------------------------------------------------------
USE_BREVO = config("USE_BREVO", default=False, cast=bool)

if USE_BREVO:
    EMAIL_BACKEND = "anymail.backends.brevo.EmailBackend"
    DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL")
    ANYMAIL = {"BREVO_API_KEY": config("BREVO_API_KEY")}
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = config("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")
    DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL")
    
# ----------------------------------------------------------------------