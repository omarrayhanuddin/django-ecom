"""Expose which social providers are actually configured.

allauth's ``{% provider_login_url %}`` raises ``SocialApp.DoesNotExist`` when a
provider has no credentials. We only advertise providers that have a SocialApp
row (added via admin) or settings-based credentials.
"""
from django.core.cache import cache


def social_providers(request):
    key = "social_provider_ids_v1"
    ids = cache.get(key)
    if ids is None:
        ids = set()
        try:
            from allauth.socialaccount.models import SocialApp

            ids = set(SocialApp.objects.values_list("provider", flat=True))
        except Exception:
            ids = set()
        # settings-configured apps (e.g. Google with CLIENT_ID)
        try:
            from allauth.socialaccount import app_settings

            providers = app_settings.PROVIDERS or {}
            for name, conf in providers.items():
                app = conf.get("APP") if isinstance(conf, dict) else None
                if app and app.get("client_id"):
                    ids.add(name)
        except Exception:
            pass
        cache.set(key, ids, 300)
    return {"social_provider_ids": sorted(ids)}
