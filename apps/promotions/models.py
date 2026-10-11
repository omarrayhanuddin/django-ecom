from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.common.mixins import TimeStampedModel
from apps.common.money import as_decimal, round_money


class FlashSale(models.Model):
    name = models.CharField(max_length=150)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    products = models.ManyToManyField(
        "catalogue.Product", through="FlashSaleProduct", related_name="flash_sales"
    )

    class Meta:
        verbose_name = "ফ্ল্যাশ সেল"
        verbose_name_plural = "ফ্ল্যাশ সেল"
        ordering = ["-start_time"]

    def __str__(self):
        return self.name

    @property
    def is_current(self):
        now = timezone.now()
        return self.is_active and self.start_time <= now <= self.end_time

    @property
    def time_remaining_seconds(self):
        if not self.is_current:
            return 0
        return int((self.end_time - timezone.now()).total_seconds())


class FlashSaleProduct(models.Model):
    flash_sale = models.ForeignKey(
        FlashSale, on_delete=models.CASCADE, related_name="entries"
    )
    product = models.ForeignKey(
        "catalogue.Product", on_delete=models.CASCADE, related_name="flash_sale_entries"
    )
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["flash_sale", "product"], name="uniq_flashsale_product"
            )
        ]
        verbose_name = "ফ্ল্যাশ সেল পণ্য"

    def __str__(self):
        return f"{self.product} @ {self.discount_percentage}%"

    def save(self, *args, **kwargs):
        if self.sale_price is None and self.product_id:
            pct = as_decimal(self.discount_percentage)
            self.sale_price = round_money(self.product.base_price * (1 - pct / 100))
        super().save(*args, **kwargs)


class HotSale(models.Model):
    product = models.ForeignKey(
        "catalogue.Product", on_delete=models.CASCADE, related_name="hot_sales"
    )
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    label = models.CharField(max_length=60, default="Hot Deal")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "হট সেল"
        ordering = ["-discount_percentage"]

    def __str__(self):
        return f"{self.product} ({self.discount_percentage}% hot)"


class Coupon(models.Model):
    class DiscountType(models.TextChoices):
        PERCENTAGE = "PERCENTAGE", "শতাংশ"
        FIXED_AMOUNT = "FIXED_AMOUNT", "নির্দিষ্ট টাকা"

    code = models.CharField(max_length=40, unique=True)
    discount_type = models.CharField(
        max_length=15, choices=DiscountType.choices, default=DiscountType.PERCENTAGE
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    max_discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    minimum_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_uses = models.PositiveIntegerField(null=True, blank=True, help_text="খালি = অসীম")
    used_count = models.PositiveIntegerField(default=0, editable=False)
    per_user_limit = models.PositiveIntegerField(default=1)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_next_purchase = models.BooleanField(default=False)
    user = models.ForeignKey(
        "accounts.CustomUser",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="coupons",
    )

    class Meta:
        verbose_name = "কুপন"
        ordering = ["-id"]

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    # ── Validation / discount (spec §4.3) ─────────────────────────────────
    def clean(self):
        if self.discount_type == self.DiscountType.PERCENTAGE:
            if as_decimal(self.discount_value) > 100:
                raise ValidationError({"discount_value": "শতাংশ ১০০ এর বেশি হতে পারে না।"})

    def is_valid_now(self):
        now = timezone.now()
        if not self.is_active:
            return False, "কুপন সক্রিয় নয়।"
        if self.valid_from and now < self.valid_from:
            return False, "কুপন এখনো শুরু হয়নি।"
        if self.valid_to and now > self.valid_to:
            return False, "কুপনের মেয়াদ শেষ হয়েছে।"
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False, "এই কুপনের ব্যবহার সীমা শেষ।"
        return True, ""

    def user_redemption_count(self, user):
        if not user or not user.is_authenticated:
            return 0
        return self.redemptions.filter(user=user).count()

    def can_be_used_by(self, user):
        ok, msg = self.is_valid_now()
        if not ok:
            return False, msg
        if self.user_id and (not user or not user.is_authenticated or user.pk != self.user_id):
            return False, "এই কুপনটি আপনার জন্য নয়।"
        if self.per_user_limit is not None and user and user.is_authenticated:
            if self.user_redemption_count(user) >= self.per_user_limit:
                return False, "আপনি এই কুপন আগে ব্যবহার করেছেন।"
        return True, ""

    def discount_for(self, subtotal):
        subtotal = as_decimal(subtotal)
        if subtotal < as_decimal(self.minimum_order_value):
            return as_decimal(0)
        if self.discount_type == self.DiscountType.PERCENTAGE:
            discount = subtotal * as_decimal(self.discount_value) / 100
            if self.max_discount_amount:
                discount = min(discount, as_decimal(self.max_discount_amount))
        else:
            discount = as_decimal(self.discount_value)
        discount = min(discount, subtotal)
        return round_money(discount)


class CouponRedemption(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="redemptions")
    user = models.ForeignKey(
        "accounts.CustomUser",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="coupon_redemptions",
    )
    order = models.OneToOneField(
        "orders.Order", on_delete=models.CASCADE, related_name="coupon_redemption"
    )
    redeemed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.coupon.code} → {self.order_id}"


class Banner(TimeStampedModel):
    class Position(models.TextChoices):
        TOP_SLIDER = "TOP_SLIDER", "অনাউন্সমেন্ট"
        HERO = "HERO", "হিরো স্লাইডার"

    title_bn = models.CharField(max_length=150, blank=True)
    title_en = models.CharField(max_length=150, blank=True)
    subtitle_bn = models.CharField(max_length=255, blank=True)
    subtitle_en = models.CharField(max_length=255, blank=True)
    image = models.ImageField(upload_to="banners/")
    link_url = models.CharField(max_length=300, blank=True)
    position = models.CharField(
        max_length=12, choices=Position.choices, default=Position.HERO
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "ব্যানার"
        verbose_name_plural = "ব্যানার"
        ordering = ["order", "id"]

    def __str__(self):
        return self.title_bn or self.title_en or f"Banner #{self.pk}"

    @property
    def title(self):
        from django.utils import translation

        lang = translation.get_language() or "bn"
        if lang.startswith("bn"):
            return self.title_bn or self.title_en
        return self.title_en or self.title_bn
