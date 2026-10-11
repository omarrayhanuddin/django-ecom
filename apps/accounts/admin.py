from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import Address, CustomUser, UserProfile


@admin.register(CustomUser)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = ("email", "full_name", "phone_number", "is_active", "is_staff", "onboarding_complete")
    list_filter = ("is_active", "is_staff", "is_superuser", "onboarding_complete")
    search_fields = ("email", "full_name", "phone_number")
    ordering = ("-date_joined",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("ব্যক্তিগত", {"fields": ("full_name", "phone_number", "onboarding_complete")}),
        ("অনুমতি", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("গুরুত্বপূর্ণ তারিখ", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "full_name", "password1", "password2")}),
    )


@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = ("user", "date_of_birth")


@admin.register(Address)
class AddressAdmin(ModelAdmin):
    list_display = ("user", "label", "district", "division", "is_default")
    list_filter = ("label", "is_default", "division")
    search_fields = ("user__email", "street_address", "district")
