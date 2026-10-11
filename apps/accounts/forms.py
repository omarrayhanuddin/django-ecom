from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction

from .models import Address, UserProfile

User = get_user_model()


class RegistrationForm(forms.Form):
    """Single-step registration: account + phone + one address."""

    full_name = forms.CharField(max_length=255, label="পূর্ণ নাম")
    email = forms.EmailField(label="ইমেইল")
    phone_number = forms.CharField(max_length=11, label="মোবাইল নম্বর")
    password1 = forms.CharField(
        widget=forms.PasswordInput, label="পাসওয়ার্ড", min_length=8
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput, label="পাসওয়ার্ড নিশ্চিত করুন"
    )
    division = forms.CharField(max_length=100, label="বিভাগ")
    district = forms.CharField(max_length=100, label="জেলা")
    upazila = forms.CharField(max_length=100, required=False, label="উপজেলা")
    street_address = forms.CharField(max_length=255, label="ঠিকানা")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("এই ইমেইল দিয়ে ইতিমধ্যে একটি অ্যাকাউন্ট আছে।")
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            self.add_error("password2", "দুটি পাসওয়ার্ড মিলছে না।")
        return cleaned

    @transaction.atomic
    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            email=data["email"],
            password=data["password1"],
            full_name=data["full_name"],
            phone_number=data["phone_number"],
            onboarding_complete=True,
        )
        Address.objects.create(
            user=user,
            label=Address.Label.HOME,
            division=data["division"],
            district=data["district"],
            upazila=data.get("upazila", ""),
            street_address=data["street_address"],
            is_default=True,
        )
        return user


class OnboardingForm(forms.Form):
    """Collected after social signup when phone/address are missing."""

    phone_number = forms.CharField(max_length=11, label="মোবাইল নম্বর")
    division = forms.CharField(max_length=100, label="বিভাগ")
    district = forms.CharField(max_length=100, label="জেলা")
    upazila = forms.CharField(max_length=100, required=False, label="উপজেলা")
    street_address = forms.CharField(max_length=255, label="ঠিকানা")

    @transaction.atomic
    def save(self, user):
        data = self.cleaned_data
        user.phone_number = data["phone_number"]
        user.onboarding_complete = True
        user.save(update_fields=["phone_number", "onboarding_complete"])
        if not user.addresses.exists():
            Address.objects.create(
                user=user,
                label=Address.Label.HOME,
                division=data["division"],
                district=data["district"],
                upazila=data.get("upazila", ""),
                street_address=data["street_address"],
                is_default=True,
            )
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name", "phone_number"]
        labels = {"full_name": "পূর্ণ নাম", "phone_number": "মোবাইল নম্বর"}


class AvatarForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["avatar", "date_of_birth"]
        widgets = {"date_of_birth": forms.DateInput(attrs={"type": "date"})}


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ["label", "division", "district", "upazila", "street_address", "is_default"]
