"""
Base Django settings shared by every environment.

Environment-specific values live in ``local.py`` / ``production.py``.
Secrets and deployment values are read from the ``.env`` file (django-environ).
"""
from decimal import Decimal
from pathlib import Path

import environ

# project_root/  (base.py -> settings/ -> config/ -> root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)

ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    environ.Env.read_env(ENV_FILE)

# ── Core ────────────────────────────────────────────────────────────────────
SECRET_KEY = env("SECRET_KEY", default="django-insecure-change-me-in-production")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# ── Applications ────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    # Admin theme (must precede django.contrib.admin)
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    # daphne MUST precede django.contrib.staticfiles (Channels 4 runserver)
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Third party
    "channels",
    "django_celery_beat",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.facebook",
    "django_filters",
    "imagekit",
    "ckeditor",
    "django_htmx",
    "import_export",
    "solo",
    "adminsortable2",
    # Local apps
    "apps.common",
    "apps.accounts",
    "apps.catalogue",
    "apps.promotions",
    "apps.cart",
    "apps.orders",
    "apps.analytics",
    "apps.pages",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    # Local middleware
    "apps.common.middleware.HtmxMethodMiddleware",
    "apps.analytics.middleware.SiteVisitMiddleware",
    "apps.accounts.middleware.OnboardingMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.pages.context_processors.site_settings",
                "apps.cart.context_processors.cart_summary",
                "apps.promotions.context_processors.active_promotions",
                "apps.accounts.context_processors.social_providers",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ── Database ────────────────────────────────────────────────────────────────
DATABASES = {
    "default": env.db(
        "DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
    )
}

# ── Passwords ───────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── i18n / tz ───────────────────────────────────────────────────────────────
LANGUAGE_CODE = "bn"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

# ── Static / media ──────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# django-ckeditor ships CKEditor 4 (EOL). We mitigate by sanitising every rich
# text field with nh3 on save and restricting the toolbar; see apps/common/sanitize.py
SILENCED_SYSTEM_CHECKS = ["ckeditor.W001"]

# ── Auth ────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "accounts.CustomUser"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID = 1

# django-allauth (current settings, allauth >= 65.5)
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_ADAPTER = "apps.accounts.adapters.AccountAdapter"
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    },
    "facebook": {
        "METHOD": "oauth2",
        "SCOPE": ["email", "public_profile"],
    },
}

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# ── Email ───────────────────────────────────────────────────────────────────
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@example.com")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# ── Redis / Celery / Channels ───────────────────────────────────────────────
REDIS_URL = env("REDIS_URL", default="redis://127.0.0.1:6379/0")

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_BEAT_SCHEDULE = {
    "deactivate-expired-flash-sales": {
        "task": "apps.promotions.tasks.deactivate_expired_flash_sales",
        "schedule": 300.0,
    },
    "cleanup-stale-live-visitors": {
        "task": "apps.analytics.tasks.cleanup_stale_live_visitors",
        "schedule": 60.0,
    },
    "purge-old-site-visits": {
        "task": "apps.analytics.tasks.purge_old_site_visits",
        "schedule": 86400.0,
    },
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }
}

# ── Business config ─────────────────────────────────────────────────────────
# Platform fee lives in the DB (pages.SiteSettings). This is only the seed value
# used the first time `seed_demo_data` runs.
PLATFORM_FEE_SEED = Decimal(env("PLATFORM_FEE_PERCENTAGE", default="2.5"))
DEFAULT_CURRENCY = "BDT"
NEXT_PURCHASE_COUPON_PERCENT = Decimal("5.00")
NEXT_PURCHASE_COUPON_VALID_DAYS = 30
LIVE_VISITOR_TTL_SECONDS = 300
RATELIMIT_USE_CACHE = "default"

# ── Rich text ───────────────────────────────────────────────────────────────
CKEDITOR_CONFIGS = {
    "default": {
        "toolbar": "Custom",
        "height": 320,
        "width": "100%",
        "toolbar_Custom": [
            ["Bold", "Italic", "Underline"],
            ["BulletedList", "NumberedList"],
            ["Outdent", "Indent"],
            ["Link", "Unlink"],
            ["RemoveFormat"],
        ],
    }
}

IMPORT_EXPORT_USE_TRANSACTIONS = True

# ── Admin theme ─────────────────────────────────────────────────────────────
UNFOLD = {
    "SITE_TITLE": "ShopBazar Admin",
    "SITE_HEADER": "ShopBazar Administration",
    "SITE_URL": "/",
    "DASHBOARD_CALLBACK": "apps.pages.admin.dashboard_callback",
    "COLORS": {
        "primary": {
            "50": "230 244 244",
            "100": "209 232 232",
            "200": "168 212 212",
            "300": "124 190 190",
            "400": "74 163 163",
            "500": "14 115 115",
            "600": "11 92 92",
            "700": "11 76 76",
            "800": "11 59 59",
            "900": "11 43 43",
            "950": "7 28 28",
        },
    },
}

# ── Logging ─────────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
