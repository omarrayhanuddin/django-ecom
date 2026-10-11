from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.common.mixins import BilingualNameMixin, TimeStampedModel, unique_slugify
from apps.common.money import as_decimal, discount_percentage
from apps.common.sanitize import clean_html

from .constants import (
    AVAILABILITY_CHOICES,
    AVAILABILITY_IN_STOCK,
    CAPACITY_CHOICES,
    PRODUCT_TYPE_CHOICES,
)


class Category(BilingualNameMixin, TimeStampedModel):
    slug = models.SlugField(unique=True, blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )
    icon = models.CharField(
        max_length=64, blank=True, help_text="Font Awesome class, e.g. fa-solid fa-mobile"
    )
    is_featured = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "ক্যাটাগরি"
        verbose_name_plural = "ক্যাটাগরিসমূহ"
        ordering = ["order", "name_en"]

    def __str__(self):
        return self.display_name or f"Category #{self.pk}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name_en or self.name_bn)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalogue:category", args=[self.slug])

    @property
    def is_parent(self):
        return self.parent_id is None


class Brand(TimeStampedModel):
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True, blank=True)
    logo = models.ImageField(upload_to="brands/", blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)


class Tag(models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(unique=True, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)


class Product(BilingualNameMixin, TimeStampedModel):
    slug = models.SlugField(unique=True, blank=True, max_length=220)
    sku = models.CharField("SKU", max_length=64, unique=True)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    brand = models.ForeignKey(
        Brand, null=True, blank=True, on_delete=models.SET_NULL, related_name="products"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="products")

    short_description_bn = models.CharField(max_length=300, blank=True)
    short_description_en = models.CharField(max_length=300, blank=True)
    full_description = models.TextField(blank=True, help_text="Rich text (sanitised)")

    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    availability = models.CharField(
        max_length=12,
        choices=AVAILABILITY_CHOICES,
        default=AVAILABILITY_IN_STOCK,
    )
    capacity = models.CharField(max_length=50, choices=CAPACITY_CHOICES, blank=True)
    product_type = models.CharField(
        max_length=20, choices=PRODUCT_TYPE_CHOICES, blank=True
    )

    stock_quantity = models.PositiveIntegerField(default=0)
    track_inventory = models.BooleanField(default=True)

    is_featured = models.BooleanField(default=False)
    is_trending = models.BooleanField(default=False)
    is_best_seller = models.BooleanField(default=False)
    is_top_rated = models.BooleanField(default=False)

    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = "পণ্য"
        verbose_name_plural = "পণ্যসমূহ"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["availability"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return self.display_name or self.sku

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name_en or self.name_bn)
        if self.full_description:
            self.full_description = clean_html(self.full_description)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalogue:product", args=[self.slug])

    # ── Pricing (see spec §4.1: first match wins) ──────────────────────────
    def _active_flash_sale_price(self):
        now = timezone.now()
        fsp = (
            self.flash_sale_entries.filter(
                flash_sale__is_active=True,
                flash_sale__start_time__lte=now,
                flash_sale__end_time__gte=now,
            )
            .order_by("sale_price")
            .first()
        )
        return fsp.sale_price if fsp else None

    def _active_hot_sale(self):
        return self.hot_sales.filter(is_active=True).order_by("-discount_percentage").first()

    def get_effective_price(self):
        flash = self._active_flash_sale_price()
        if flash is not None:
            return as_decimal(flash)

        hot = self._active_hot_sale()
        if hot:
            return self.base_price * (1 - as_decimal(hot.discount_percentage) / 100)

        if self.discount_price and self.discount_price < self.base_price:
            return as_decimal(self.discount_price)

        return as_decimal(self.base_price)

    @property
    def was_price(self):
        return as_decimal(self.base_price)

    @property
    def discount_percent(self):
        return discount_percentage(self.base_price, self.get_effective_price())

    @property
    def in_stock(self):
        if not self.track_inventory:
            return True
        return self.stock_quantity > 0

    @property
    def primary_image(self):
        img = self.images.filter(is_primary=True).first() or self.images.first()
        return img

    @property
    def short_description(self):
        from django.utils import translation

        lang = translation.get_language() or "bn"
        if lang.startswith("bn"):
            return self.short_description_bn or self.short_description_en
        return self.short_description_en or self.short_description_bn

    @property
    def average_rating(self):
        agg = self.reviews.filter(is_approved=True).aggregate(
            avg=models.Avg("rating"), count=models.Count("id")
        )
        return {"average": round(agg["avg"] or 0, 1), "count": agg["count"]}


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/%Y/%m/")
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.product.sku} image #{self.pk}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_primary:
            ProductImage.objects.filter(product=self.product).exclude(pk=self.pk).update(
                is_primary=False
            )


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="variants"
    )
    name = models.CharField(max_length=120, help_text='e.g. "লাল / XL"')
    sku = models.CharField(max_length=64, unique=True)
    price_override = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    stock_quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.product.sku} — {self.name}"

    @property
    def effective_price(self):
        if self.price_override:
            return as_decimal(self.price_override)
        return self.product.get_effective_price()


class ProductReview(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "user"], name="uniq_review_per_user"
            )
        ]

    def __str__(self):
        return f"{self.product} — {self.rating}★"
