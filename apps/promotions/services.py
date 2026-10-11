"""Promotion business logic shared by cart and orders."""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.common.money import as_decimal

from .models import Coupon


def get_active_flash_sale():
    now = timezone.now()
    from .models import FlashSale

    return (
        FlashSale.objects.filter(
            is_active=True, start_time__lte=now, end_time__gte=now
        )
        .prefetch_related("entries__product")
        .order_by("-start_time")
        .first()
    )


def validate_coupon(code: str, user, subtotal):
    """Return ``(coupon, discount, error_message)``.

    On success ``error_message`` is empty; on failure the coupon may be None.
    """
    subtotal = as_decimal(subtotal)
    if not code:
        return None, as_decimal(0), "কুপন কোড লিখুন।"
    try:
        coupon = Coupon.objects.get(code=code.strip().upper())
    except Coupon.DoesNotExist:
        return None, as_decimal(0), "কুপন কোডটি সঠিক নয়।"

    ok, msg = coupon.can_be_used_by(user)
    if not ok:
        return coupon, as_decimal(0), msg

    if subtotal < as_decimal(coupon.minimum_order_value):
        return (
            coupon,
            as_decimal(0),
            f"ন্যূনতম অর্ডার ৳{coupon.minimum_order_value} প্রয়োজন।",
        )

    return coupon, coupon.discount_for(subtotal), ""


def issue_next_purchase_coupon(order):
    """Create the NEXT-<order_number> coupon for a verified order (idempotent)."""
    code = f"NEXT-{order.order_number}"
    if Coupon.objects.filter(code=code).exists():
        return Coupon.objects.get(code=code)
    coupon = Coupon.objects.create(
        code=code,
        discount_type=Coupon.DiscountType.PERCENTAGE,
        discount_value=settings.NEXT_PURCHASE_COUPON_PERCENT,
        minimum_order_value=0,
        max_uses=1,
        per_user_limit=1,
        valid_from=timezone.now(),
        valid_to=timezone.now()
        + timedelta(days=settings.NEXT_PURCHASE_COUPON_VALID_DAYS),
        is_active=True,
        is_next_purchase=True,
        user=order.user,
    )
    return coupon
