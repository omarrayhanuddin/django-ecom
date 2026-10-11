"""Redirect freshly-social-logged-in users to the onboarding form."""
from django.shortcuts import redirect
from django.urls import reverse

EXEMPT_PREFIXES = (
    "/accounts/onboarding/",
    "/accounts/logout/",
    "/admin/",
    "/static/",
    "/media/",
)


class OnboardingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user
            and user.is_authenticated
            and not user.onboarding_complete
            and not request.path.startswith(EXEMPT_PREFIXES)
            and not request.path.startswith("/accounts/login")
            and not getattr(request, "htmx", False)
        ):
            return redirect(reverse("accounts:onboarding"))
        return self.get_response(request)
