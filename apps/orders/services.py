"""Order creation logic (checkout)."""
from django.db import transaction

from apps.common.money import as_decimal, percent_of, round_money
from apps.pages.models import SiteSettings
from apps.promotions.models import Coupon, CouponRedemption

from .models import Order, OrderItem


@transaction.atomic
def create_order_from_cart(cart, data, user):
    """Create a PENDING/AWAITING_VERIFICATION order from the cart.

    Money rules (spec §4): fee is computed on (subtotal - discount).
    """
    items = list(cart.items.select_related("product", "variant"))
    subtotal = round_money(sum((i.line_total for i in items), as_decimal(0)))

    # Re-validate the coupon under a row lock to avoid races.
    coupon = None
    discount = as_decimal(0)
    if cart.coupon_id:
        coupon = Coupon.objects.select_for_update().get(pk=cart.coupon_id)
        ok, _msg = coupon.can_be_used_by(user)
        if ok and subtotal >= as_decimal(coupon.minimum_order_value):
            discount = coupon.discount_for(subtotal)
        else:
            coupon = None

    taxable = round_money(subtotal - discount)
    fee_pct = SiteSettings.load().platform_fee_percentage
    fee_amount = percent_of(taxable, fee_pct)
    total = round_money(taxable + fee_amount)

    order = Order.objects.create(
        user=user if (user and user.is_authenticated) else None,
        guest_email="" if (user and user.is_authenticated) else data["email"],
        guest_phone="" if (user and user.is_authenticated) else data["phone"],
        customer_name=data["customer_name"],
        pickup_store=data.get("pickup_store"),
        status=Order.Status.PENDING,
        payment_status=Order.PaymentStatus.AWAITING_VERIFICATION,
        payment_method=data["payment_method"],
        payment_reference=data.get("payment_reference", ""),
        platform_fee_percentage=fee_pct,
        platform_fee_amount=fee_amount,
        subtotal=subtotal,
        discount_amount=discount,
        total_amount=total,
        coupon=coupon,
        note=data.get("note", ""),
    )

    for item in items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            variant=item.variant,
            product_name=item.product.display_name,
            unit_price=item.unit_price,
            quantity=item.quantity,
            line_total=item.line_total,
        )

    if coupon:
        CouponRedemption.objects.create(coupon=coupon, user=order.user, order=order)
        Coupon.objects.filter(pk=coupon.pk).update(used_count=coupon.used_count + 1)

    # Stock is decremented on completion (see Order.mark_completed).
    cart.items.all().delete()
    cart.coupon = None
    cart.save(update_fields=["coupon"])
    return order
