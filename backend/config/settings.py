from __future__ import annotations

import os
import copy
from pathlib import Path
import sys

from django.utils.log import DEFAULT_LOGGING

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = Path(os.environ.get("REPO_ROOT", BASE_DIR.parent))

VENDOR_DIR = REPO_ROOT / "inventree-part-import"
if VENDOR_DIR.exists():
    sys.path.insert(0, str(VENDOR_DIR))

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "changeme")
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [host for host in os.environ.get("ALLOWED_HOSTS", "*").split(",") if host]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"

# Para desenvolvimento (ficheiros estáticos dentro da app)
STATICFILES_DIRS = [BASE_DIR / "static"]

# Para produção (onde o collectstatic vai colocar tudo)
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
}

CORS_ALLOW_ALL_ORIGINS = os.environ.get("CORS_ALLOW_ALL", "true").lower() == "true"
DEFAULT_COUNTRY = os.environ.get("DEFAULT_COUNTRY", "PT")
DEFAULT_CURRENCY = os.environ.get("DEFAULT_CURRENCY", "EUR")
DEFAULT_LANGUAGE = os.environ.get("DEFAULT_LANGUAGE", "EN")
CSRF_TRUSTED_ORIGINS = [
    "https://import.inventree.itrocas.com",
    "http://import.inventree.itrocas.com",
]

LOGGING = copy.deepcopy(DEFAULT_LOGGING)
LOGGING.setdefault("loggers", {})
LOGGING["loggers"]["api.services.mouser"] = {
    "handlers": ["console"],
    "level": "INFO",
}

IMPORTER_CONFIG_TEMPLATE_DIR = Path(
    os.environ.get("IMPORTER_CONFIG_TEMPLATE_DIR", REPO_ROOT / "inventree_part_import_config")
).resolve()
IMPORTER_CONFIG_DIR = Path(
    os.environ.get("IMPORTER_CONFIG_DIR", REPO_ROOT / ".importer_config")
).resolve()
IMPORTER_REQUEST_TIMEOUT = float(os.environ.get("IMPORTER_REQUEST_TIMEOUT", 30))
IMPORTER_SUPPLIERS = [
    supplier.strip()
    for supplier in os.environ.get("IMPORTER_SUPPLIERS", "mouser,digikey").split(",")
    if supplier.strip()
]
