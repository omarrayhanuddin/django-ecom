from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.common.validators import validate_bd_phone

from .managers import CustomUserManager


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """Email-first user. No username field."""

    email = models.EmailField("ইমেইল", unique=True)
    phone_number = models.CharField(
        "মোবাইল নম্বর",
        max_length=11,
        blank=True,
        validators=[validate_bd_phone],
        help_text="যেমন 01712345678",
    )
    full_name = models.CharField("পূর্ণ নাম", max_length=255)
    date_joined = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    onboarding_complete = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = "ব্যবহারকারী"
        verbose_name_plural = "ব্যবহারকারীগণ"

    def __str__(self):
        return self.email

    @property
    def first_name(self):
        return self.full_name.split(" ")[0] if self.full_name else ""


class UserProfile(models.Model):
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="profile"
    )
    avatar = models.ImageField("অ্যাভাটার", upload_to="avatars/", blank=True)
    date_of_birth = models.DateField("জন্ম তারিখ", null=True, blank=True)

    def __str__(self):
        return f"Profile<{self.user.email}>"


class Address(models.Model):
    class Label(models.TextChoices):
        HOME = "HOME", "বাসা"
        OFFICE = "OFFICE", "অফিস"
        OTHER = "OTHER", "অন্যান্য"

    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name="addresses"
    )
    label = models.CharField(
        "ধরন", max_length=10, choices=Label.choices, default=Label.HOME
    )
    division = models.CharField("বিভাগ", max_length=100)
    district = models.CharField("জেলা", max_length=100)
    upazila = models.CharField("উপজেলা", max_length=100, blank=True)
    street_address = models.CharField("ঠিকানা", max_length=255)
    is_default = models.BooleanField("ডিফল্ট", default=False)

    class Meta:
        verbose_name = "ঠিকানা"
        verbose_name_plural = "ঠিকানাসমূহ"

    def __str__(self):
        return f"{self.get_label_display()} — {self.street_address}, {self.district}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            Address.objects.filter(user=self.user).exclude(pk=self.pk).update(
                is_default=False
            )
