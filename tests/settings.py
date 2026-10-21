# -*- coding: utf-8 -*-
"""
Réglages Django minimaux pour tester le plugin hors du serveur PyScada
(SQLite en mémoire, pas de MariaDB ni de Redis).
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = "tests-only-not-a-secret"
DEBUG = True
USE_TZ = True
TIME_ZONE = "UTC"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "pyscada",
]
pyscada = __import__("pyscada.core")
INSTALLED_APPS += list(getattr(pyscada.core, "additional_installed_app", []))
INSTALLED_APPS += ["pyscada.thread"]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "test.sqlite3"),
    }
}
STATIC_URL = "/static/"
ROOT_URLCONF = "tests.urls"
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

PYSCADA = {}
PYSCADA_META = {"name": "Tests", "description": "Tests pyscada-thread"}
