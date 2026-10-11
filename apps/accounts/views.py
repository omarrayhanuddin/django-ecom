from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, FormView, TemplateView

from .forms import (
    AddressForm,
    AvatarForm,
    OnboardingForm,
    ProfileForm,
    RegistrationForm,
)
from .models import Address


class RegisterView(FormView):
    template_name = "accounts/register.html"
    form_class = RegistrationForm
    success_url = reverse_lazy("pages:home")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return self.redirect_authenticated()
        return super().dispatch(request, *args, **kwargs)

    def redirect_authenticated(self):
        from django.shortcuts import redirect

        return redirect("pages:home")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(self.request, "স্বাগতম! আপনার অ্যাকাউন্ট তৈরি হয়েছে।")
        return super().form_valid(form)


class OnboardingView(LoginRequiredMixin, FormView):
    template_name = "accounts/onboarding.html"
    form_class = OnboardingForm
    success_url = reverse_lazy("pages:home")

    def form_valid(self, form):
        form.save(self.request.user)
        messages.success(self.request, "ধন্যবাদ! আপনার তথ্য সংরক্ষণ করা হয়েছে।")
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return kwargs


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        profile = getattr(user, "profile", None)
        ctx.setdefault("profile_form", ProfileForm(instance=user))
        ctx.setdefault("avatar_form", AvatarForm(instance=profile))
        ctx["orders"] = user.orders.order_by("-created_at")[:10]
        return ctx

    def post(self, request, *args, **kwargs):
        user = request.user
        profile = getattr(user, "profile", None)
        profile_form = ProfileForm(request.POST, instance=user)
        avatar_form = AvatarForm(request.POST, request.FILES, instance=profile)
        if profile_form.is_valid() and avatar_form.is_valid():
            profile_form.save()
            avatar_form.save()
            messages.success(request, "প্রোফাইল আপডেট হয়েছে।")
            from django.shortcuts import redirect

            return redirect("accounts:profile")
        return self.render_to_response(
            self.get_context_data(
                profile_form=profile_form, avatar_form=avatar_form
            )
        )


class AddressListView(LoginRequiredMixin, FormView):
    template_name = "accounts/addresses.html"
    form_class = AddressForm
    success_url = reverse_lazy("accounts:addresses")

    def get_queryset(self):
        return self.request.user.addresses.all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["addresses"] = self.get_queryset()
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.user = self.request.user
        if not self.request.user.addresses.exists():
            obj.is_default = True
        obj.save()
        messages.success(self.request, "ঠিকানা যোগ করা হয়েছে।")
        return super().form_valid(form)


class AddressDeleteView(LoginRequiredMixin, DeleteView):
    template_name = "accounts/address_confirm_delete.html"
    success_url = reverse_lazy("accounts:addresses")

    def get_queryset(self):
        return self.request.user.addresses.all()

    def form_valid(self, form):
        messages.success(self.request, "ঠিকানা মুছে ফেলা হয়েছে।")
        return super().form_valid(form)
