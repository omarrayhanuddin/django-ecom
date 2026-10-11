from django.conf import settings
from django.db import models

from apps.common.money import as_decimal, percent_of, round_money


class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="carts",
    )
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    coupon = models.ForeignKey(
        "promotions.Coupon",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="carts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "কার্ট"

    def __str__(self):
        return f"Cart<{self.user or self.session_key}>"

    # ── Totals ─────────────────────────────────────────────────────────────
    @property
    def subtotal(self):
        return round_money(sum((i.line_total for i in self.items.all()), as_decimal(0)))

    @property
    def discount_amount(self):
        if not self.coupon:
            return as_decimal(0)
        return self.coupon.discount_for(self.subtotal)

    @property
    def platform_fee_percentage(self):
        from apps.pages.models import SiteSettings

        return SiteSettings.load().platform_fee_percentage

    @property
    def taxable_amount(self):
        return round_money(self.subtotal - self.discount_amount)

    @property
    def platform_fee_amount(self):
        return percent_of(self.taxable_amount, self.platform_fee_percentage)

    @property
    def total(self):
        return round_money(self.taxable_amount + self.platform_fee_amount)

    @property
    def item_count(self):
        return sum(i.quantity for i in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "catalogue.Product", on_delete=models.CASCADE, related_name="cart_items"
    )
    variant = models.ForeignKey(
        "catalogue.ProductVariant",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "কার্ট আইটেম"
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product", "variant"], name="uniq_cart_line"
            )
        ]

    def __str__(self):
        return f"{self.product} x{self.quantity}"

    @property
    def line_total(self):
        return round_money(as_decimal(self.unit_price) * self.quantity)
