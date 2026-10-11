"""allauth adapter: route brand-new social users through the onboarding form."""
from allauth.account.adapter import DefaultAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        user = request.user
        if user.is_authenticated and not getattr(user, "onboarding_complete", True):
            return "/accounts/onboarding/"
        return super().get_login_redirect_url(request)

    def get_signup_redirect_url(self, request):
        return "/accounts/onboarding/"
