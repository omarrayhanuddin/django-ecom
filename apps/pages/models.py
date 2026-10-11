from django.db import models
from django.utils import translation

from apps.common.mixins import TimeStampedModel, unique_slugify
from apps.common.sanitize import clean_html
from solo.models import SingletonModel


class SiteSettings(SingletonModel):
    site_name_bn = models.CharField(max_length=120, default="শপবাজার")
    site_name_en = models.CharField(max_length=120, default="ShopBazar")
    platform_fee_percentage = models.DecimalField(
        "সার্ভিস ফি (%)", max_digits=5, decimal_places=2, default=2.5
    )
    announcement_bn = models.CharField(max_length=255, blank=True)
    announcement_en = models.CharField(max_length=255, blank=True)
    head_office_address = models.CharField(max_length=255, blank=True)
    head_office_email = models.EmailField(blank=True)
    head_office_phone = models.CharField(max_length=20, blank=True)
    facebook_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)

    class Meta:
        verbose_name = "সাইট সেটিংস"

    def __str__(self):
        return "Site Settings"

    @classmethod
    def load(cls):
        return cls.get_solo()

    @property
    def site_name(self):
        lang = translation.get_language() or "bn"
        if lang.startswith("bn"):
            return self.site_name_bn or self.site_name_en
        return self.site_name_en or self.site_name_bn

    @property
    def announcement(self):
        lang = translation.get_language() or "bn"
        if lang.startswith("bn"):
            return self.announcement_bn or self.announcement_en
        return self.announcement_en or self.announcement_bn


class StaticPage(TimeStampedModel):
    title_bn = models.CharField(max_length=200, blank=True)
    title_en = models.CharField(max_length=200, blank=True)
    slug = models.SlugField(unique=True)
    content = models.TextField(blank=True, help_text="Rich text (sanitised)")
    is_published = models.BooleanField(default=True)

    class Meta:
        verbose_name = "স্থির পৃষ্ঠা"
        verbose_name_plural = "স্থির পৃষ্ঠাসমূহ"

    def __str__(self):
        return self.title_bn or self.title_en or self.slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.title_en or self.title_bn)
        if self.content:
            self.content = clean_html(self.content)
        super().save(*args, **kwargs)

    @property
    def title(self):
        lang = translation.get_language() or "bn"
        if lang.startswith("bn"):
            return self.title_bn or self.title_en
        return self.title_en or self.title_bn


class StoreLocation(models.Model):
    name = models.CharField(max_length=150)
    address_bn = models.CharField(max_length=300, blank=True)
    address_en = models.CharField(max_length=300, blank=True)
    map_embed_url = models.URLField(blank=True, help_text="Google Maps iframe src")
    phone = models.CharField(max_length=20, blank=True)
    is_head_office = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "শোরুম"
        verbose_name_plural = "শোরুমসমূহ"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    @property
    def address(self):
        lang = translation.get_language() or "bn"
        if lang.startswith("bn"):
            return self.address_bn or self.address_en
        return self.address_en or self.address_bn


class SupportInfo(SingletonModel):
    phone_number = models.CharField(max_length=20, blank=True)
    support_hours_bn = models.CharField(max_length=120, blank=True)
    support_hours_en = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        verbose_name = "সাপোর্ট তথ্য"

    def __str__(self):
        return "Support Info"

    @classmethod
    def load(cls):
        return cls.get_solo()

    @property
    def support_hours(self):
        lang = translation.get_language() or "bn"
        if lang.startswith("bn"):
            return self.support_hours_bn or self.support_hours_en
        return self.support_hours_en or self.support_hours_bn
