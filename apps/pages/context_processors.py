"""Expose SiteSettings / SupportInfo / feature flags to all templates."""
from django.conf import settings


def site_settings(request):
    try:
        from .models import SiteSettings, SupportInfo

        return {
            "site_settings": SiteSettings.load(),
            "support_info": SupportInfo.load(),
        }
    except Exception:
        return {"site_settings": None, "support_info": None}


def features(request):
    return {"enable_websocket": getattr(settings, "ENABLE_WEBSOCKET", True)}
