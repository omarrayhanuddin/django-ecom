"""Local development settings."""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = True
ALLOWED_HOSTS = ["*"]

# SQLite by default (base.py already falls back to it). Override with
# DATABASE_URL=postgres://... to use PostgreSQL locally.
# DATABASES inherited.

INTERNAL_IPS = ["127.0.0.1"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Use Redis only when explicitly enabled; otherwise run with in-memory
# cache + channel layer so the project runs with no external services.
USE_REDIS = env.bool("USE_REDIS", default=False)

if not USE_REDIS:
    CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    }
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
    # Run async tasks inline so emails/coupons work without a worker.
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
