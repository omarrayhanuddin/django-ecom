"""Log one SiteVisit per unique session."""
from .models import SiteVisit

SKIP_PREFIXES = ("/admin", "/static", "/media", "/favicon", "/analytics/live-count")


class SiteVisitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            if not request.path.startswith(SKIP_PREFIXES):
                if not request.session.session_key:
                    request.session.create()
                session_key = request.session.session_key
                if session_key:
                    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
                    ip = xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")
                    SiteVisit.objects.get_or_create(
                        session_key=session_key,
                        defaults={
                            "ip_address": ip or None,
                            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
                            "page_url": request.path[:500],
                        },
                    )
        except Exception:
            # Never let analytics break a request (e.g. before migrations run).
            pass
        return self.get_response(request)
