from pathlib import Path
from decouple import config, Csv
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_BATTOMATIC_SECRET_KEY")
SITE_URL = os.getenv("DJANGO_BATTOMATIC_SITE_URL")
DEBUG = os.getenv("DJANGO_BATTOMATIC_DEBUG", default=True)
ALLOWED_HOSTS = [os.getenv("DJANGO_BATTOMATIC_ALLOWED_HOST", default='*')]
CSRF_TRUSTED_ORIGINS = [os.getenv("DJANGO_BATTOMATIC_CSRF_TRUSTED_ORIGINS")] if os.getenv("DJANGO_BATTOMATIC_CSRF_TRUSTED_ORIGINS", default='') else []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'batteries',
    'flightlog',
]

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

ROOT_URLCONF = 'battomatic.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'battomatic.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE':    'django.db.backends.mysql',
        'NAME':      os.getenv("DJANGO_BATTOMATIC_DB"),
        'USER':      os.getenv("DJANGO_BATTOMATIC_DB_USER"),
        'PASSWORD':  os.getenv("DJANGO_BATTOMATIC_DB_PASS"),
        'HOST':      'mariadb',
        'PORT':      '3306',
        'CHARSET':   'utf8mb4',
        'COLLATION': 'utf8mb4_general_ci',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.getenv("TIMEZONE")
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'charge_event_list'
LOGOUT_REDIRECT_URL = 'battery_list'

# Flight log import limits

FLIGHTLOG_MAX_FILES = 250
FLIGHTLOG_MAX_FILE_SIZE = 10 * 1024 * 1024
FLIGHTLOG_MAX_TOTAL_SIZE = 100 * 1024 * 1024

# Django rejects the request before the form if this is exceeded.
DATA_UPLOAD_MAX_NUMBER_FILES = FLIGHTLOG_MAX_FILES

# Files larger than this are streamed into temporary files instead of
# being held entirely in memory.
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024