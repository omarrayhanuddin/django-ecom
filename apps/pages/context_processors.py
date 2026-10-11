"""Expose SiteSettings / SupportInfo to all templates."""


def site_settings(request):
    try:
        from .models import SiteSettings, SupportInfo

        return {
            "site_settings": SiteSettings.load(),
            "support_info": SupportInfo.load(),
        }
    except Exception:
        return {"site_settings": None, "support_info": None}
