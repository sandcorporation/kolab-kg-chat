"""Django settings for the Kolab KG Chat API.

순수 Django Ninja API. 그래프 질의는 Django ORM이 아니라 async psycopg로
직접 수행한다(ADR-0003·0006). DATABASES는 ORM이 필요한 후속 이슈를 위해 구성한다.
"""
import os
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "dev-insecure-key-change-me"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS: list[str] = ["apps.sync", "apps.embeddings", "apps.eval"]  # management 명령 발견용
MIDDLEWARE: list[str] = []

ROOT_URLCONF = "config.urls"

_database_url = os.environ.get("DATABASE_URL")
if _database_url:
    _u = urlparse(_database_url)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _u.path.lstrip("/"),
            "USER": _u.username,
            "PASSWORD": _u.password,
            "HOST": _u.hostname,
            "PORT": _u.port or 5432,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
