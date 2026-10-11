"""Reusable abstract models / mixins."""
from django.db import models
from django.utils import translation
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


def _pick(lang: str, bn: str, en: str) -> str:
    """Return the value matching the active language, with bn-first fallback."""
    if lang.startswith("bn"):
        return bn or en or ""
    return en or bn or ""


class BilingualNameMixin(models.Model):
    """Dual-field Bangla/English name with a display_name property."""

    name_bn = models.CharField("নাম (বাংলা)", max_length=255, blank=True)
    name_en = models.CharField("Name (English)", max_length=255, blank=True)

    class Meta:
        abstract = True

    @property
    def display_name(self) -> str:
        return _pick(translation.get_language() or "bn", self.name_bn, self.name_en)

    def localized_name(self, lang: str) -> str:
        return _pick(lang, self.name_bn, self.name_en)


class BilingualTextMixin(models.Model):
    """Dual-field Bangla/English short text (title/subtitle/label)."""

    class Meta:
        abstract = True


def unique_slugify(instance, source_value: str, slug_field: str = "slug") -> str:
    """Generate a slug unique for the instance's model."""
    base = slugify(source_value) or "item"
    slug = base
    model = instance.__class__
    counter = 1
    while (
        model._default_manager.exclude(pk=instance.pk)
        .filter(**{slug_field: slug})
        .exists()
    ):
        counter += 1
        slug = f"{base}-{counter}"
    return slug
