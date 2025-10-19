from pathlib import Path
import os # Додаємо імпорт os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-2m^&axa-o84=ukjtq6fxz1n7m7!l&x41mj*weg^)-l*c898=$#"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# --- ЗМІНЕНО: Додано всі необхідні адреси ---
ALLOWED_HOSTS = [
    '3.121.188.223',
    'ec2-3-121-188-223.eu-central-1.compute.amazonaws.com',
]

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "rest_framework_simplejwt",
    "corsheaders",
    "clients",
    "orders",
    "inventory",
    "accounts",
    "users",
    "bot",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "my_iveco_crm.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "my_iveco_crm.wsgi.application"

# --- ЗМІНЕНО: Вказано правильну адресу бази даних AWS RDS ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres', # Назва вашої БД на RDS
        'USER': 'postgres', # Ваш логін до БД
        'PASSWORD': 'Italtruck', # ВАЖЛИВО: Вставте ваш пароль
        'HOST': 'iveco-crm-database.ctm2sws6sb0k.eu-central-1.rds.amazonaws.com',
        'PORT': '5432',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    { "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator", },
    { "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", },
    { "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator", },
    { "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator", },
]

LANGUAGE_CODE = "uk-ua"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
# Додаємо шлях для збору статичних файлів
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- ЗМІНЕНО: Додано адресу для локальної розробки та вашого сайту ---
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173", # Адреса вашого фронтенду при локальній розробці
    "https://dk2itrfnh33kx.cloudfront.net", # Адреса вашого фронтенду на AWS
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    )
}

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')



BOT_API_SECRET_KEY = "Tr7nK-j9!zP@5sWd_b0t-s3cr3t"