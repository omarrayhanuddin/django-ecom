import uuid
from datetime import datetime

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.money import as_decimal, round_money


def generate_order_number():
    today = datetime.now().strftime("%Y%m%d")
    for _ in range(20):
        candidate = f"ORD-{today}-{uuid.uuid4().int % 10000:04d}"
        if not Order.objects.filter(order_number=candidate).exists():
            return candidate
    return f"ORD-{today}-{uuid.uuid4().hex[:6].upper()}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "অপেক্ষমাণ"
        CONFIRMED = "CONFIRMED", "নিশ্চিত"
        PROCESSING = "PROCESSING", "প্রস্তুত হচ্ছে"
        READY = "READY", "সংগ্রহের জন্য প্রস্তুত"
        CANCELLED = "CANCELLED", "বাতিল"
        COMPLETED = "COMPLETED", "সম্পন্ন"

    class PaymentStatus(models.TextChoices):
        UNPAID = "UNPAID", "অপরিশোধিত"
        AWAITING_VERIFICATION = "AWAITING_VERIFICATION", "যাচাইয়ের অপেক্ষায়"
        PAID = "PAID", "পরিশোধিত"
        REFUNDED = "REFUNDED", "ফেরত"

    class PaymentMethod(models.TextChoices):
        BANK_TRANSFER = "BANK_TRANSFER", "ব্যাংক ট্রান্সফার"
        BKASH = "BKASH", "বিকাশ"
        NAGAD = "NAGAD", "নগদ"
        ROCKET = "ROCKET", "রকেট"
        OTHER = "OTHER", "অন্যান্য"

    ALLOWED_TRANSITIONS = {
        "PENDING": {"CONFIRMED", "CANCELLED"},
        "CONFIRMED": {"PROCESSING", "CANCELLED"},
        "PROCESSING": {"READY", "CANCELLED"},
        "READY": {"COMPLETED"},
        "COMPLETED": set(),
        "CANCELLED": set(),
    }

    order_number = models.CharField(max_length=32, unique=True, blank=True)
    public_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )
    guest_email = models.EmailField(blank=True)
    guest_phone = models.CharField(max_length=11, blank=True)
    customer_name = models.CharField(max_length=255, blank=True)

    pickup_store = models.ForeignKey(
        "pages.StoreLocation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    payment_status = models.CharField(
        max_length=22, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID
    )
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.BKASH
    )
    payment_reference = models.CharField(max_length=120, blank=True)

    paid_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_orders",
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    platform_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    platform_fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    coupon = models.ForeignKey(
        "promotions.Coupon",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )
    note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "অর্ডার"
        verbose_name_plural = "অর্ডারসমূহ"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["payment_method", "payment_reference"],
                condition=~models.Q(payment_reference=""),
                name="uniq_payment_reference_per_method",
            )
        ]

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = generate_order_number()
        super().save(*args, **kwargs)

    @property
    def contact_email(self):
        return self.user.email if self.user else self.guest_email

    @property
    def contact_phone(self):
        if self.user and self.user.phone_number:
            return self.user.phone_number
        return self.guest_phone

    def can_transition_to(self, new_status):
        return new_status in self.ALLOWED_TRANSITIONS.get(self.status, set())

    def transition(self, new_status, save=True):
        if new_status == self.status:
            return True
        if not self.can_transition_to(new_status):
            return False
        self.status = new_status
        if save:
            self.save(update_fields=["status", "updated_at"])
        if new_status == self.Status.COMPLETED:
            self.mark_completed()
        return True

    def mark_paid(self, verified_by=None):
        """Mark payment verified and fire the paid side effects."""
        self.payment_status = self.PaymentStatus.PAID
        self.paid_at = timezone.now()
        self.verified_by = verified_by
        self.verified_at = timezone.now()
        if self.status == self.Status.PENDING:
            self.status = self.Status.CONFIRMED
        self.save(
            update_fields=[
                "payment_status",
                "paid_at",
                "verified_by",
                "verified_at",
                "status",
                "updated_at",
            ]
        )
        from .tasks import on_order_paid

        on_order_paid.delay(self.pk)

    def mark_completed(self):
        """Decrement stock once, on completion."""
        if getattr(self, "_stock_decremented", False):
            return
        for item in self.items.select_related("product", "variant"):
            if item.variant is not None and item.product.track_inventory:
                item.variant.stock_quantity = max(0, item.variant.stock_quantity - item.quantity)
                item.variant.save(update_fields=["stock_quantity"])
            elif item.product.track_inventory:
                item.product.stock_quantity = max(0, item.product.stock_quantity - item.quantity)
                item.product.save(update_fields=["stock_quantity"])
        self._stock_decremented = True


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "catalogue.Product", on_delete=models.PROTECT, related_name="order_items"
    )
    variant = models.ForeignKey(
        "catalogue.ProductVariant",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="order_items",
    )
    product_name = models.CharField(max_length=255)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"


class PaymentInstruction(models.Model):
    method_name = models.CharField(max_length=60)
    account_number = models.CharField(max_length=60)
    account_name = models.CharField(max_length=120, blank=True)
    instructions_bn = models.TextField(blank=True)
    instructions_en = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "পেমেন্ট নির্দেশনা"
        verbose_name_plural = "পেমেন্ট নির্দেশনাসমূহ"

    def __str__(self):
        return self.method_name

    @property
    def instructions(self):
        from django.utils import translation

        lang = translation.get_language() or "bn"
        if lang.startswith("bn"):
            return self.instructions_bn or self.instructions_en
        return self.instructions_en or self.instructions_bn


class PaymentReference(models.Model):
    """Optional audit log of submitted payment references (replay detection)."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payment_refs")
    method = models.CharField(max_length=20)
    reference = models.CharField(max_length=120)
    submitted_at = models.DateTimeField(auto_now_add=True)
