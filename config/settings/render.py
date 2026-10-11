"""
Render.com demo settings.

Runs with no external services: SQLite (committed with demo data), LocMem cache,
in-memory channel layer, and media served by Django. Intended for a client demo,
not production.
"""
import os

from .base import *  # noqa: F401,F403
from .base import BASE_DIR, env

DEBUG = env.bool("DEBUG", default=False)

SECRET_KEY = env("SECRET_KEY", default="render-demo-insecure-secret-key-change-me")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])
_render_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if _render_host and _render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_render_host)

_render_url = os.environ.get("RENDER_EXTERNAL_URL")
if _render_url:
    CSRF_TRUSTED_ORIGINS = [_render_url]

# SQLite shipped in the repo; no Postgres for the demo.
DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
}

# No Redis: in-process cache + channel layer, eager Celery.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Serve uploaded media through Django (demo only; on real infra use S3/nginx).
SERVE_MEDIA = True

# gunicorn (WSGI) cannot serve WebSockets; the homepage falls back to HTMX polling.
ENABLE_WEBSOCKET = False
