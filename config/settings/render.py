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
# Give concurrent requests time instead of erroring with "database is locked".
DATABASES["default"].setdefault("OPTIONS", {})["timeout"] = 20

# Render terminates TLS and forwards the scheme.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# No Redis: in-process cache + channel layer, eager Celery.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Serve uploaded media through Django (demo only; on real infra use S3/nginx).
SERVE_MEDIA = True

# gunicorn (WSGI) cannot serve WebSockets; the homepage falls back to HTMX polling.
ENABLE_WEBSOCKET = False

# ── Low-resource tuning (0.5 CPU / 512 MB) ──────────────────────────────────
# Down from the base INFO to cut per-request log noise and I/O.
LOGGING["root"]["level"] = "WARNING"
# Delete un-hashed duplicates after collectstatic to keep the static dir small.
WHITENOISE_KEEP_ONLY_HASHED_FILES = True
# WhiteNoise still serves the media files? No — media is Django-served; static is
# immutable (hashed), so let the browser/proxy cache it aggressively.
WHITENOISE_MAX_AGE = 31536000
