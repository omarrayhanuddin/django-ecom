"""End-to-end flow test: cart -> coupon -> checkout -> payment -> next-purchase coupon."""
import os
import sys
import uuid
from decimal import Decimal
from pathlib import Path

import django

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()  # noqa: E402

from django.contrib.auth import get_user_model  # noqa: E402
from django.test import Client  # noqa: E402

from apps.cart.models import Cart  # noqa: E402
from apps.catalogue.models import Product  # noqa: E402
from apps.orders.models import Order  # noqa: E402
from apps.pages.models import SiteSettings, StoreLocation  # noqa: E402
from apps.promotions.models import Coupon  # noqa: E402

User = get_user_model()
client = Client()
failures = []


def check(label, cond):
    print(("OK  " if cond else "FAIL") + "  " + label)
    if not cond:
        failures.append(label)


product = Product.objects.filter(base_price__gte=Decimal("500")).first()
store = StoreLocation.objects.first()
settings_obj = SiteSettings.load()

# Fresh guest cart
client.get("/cart/")
client.post("/cart/add/", {"product_id": product.id, "quantity": 1})
client.post("/cart/apply-coupon/", {"code": "welcome10"})

cart = Cart.objects.filter(session_key=client.session.session_key).first()
subtotal = cart.subtotal
discount = cart.discount_amount
fee = cart.platform_fee_amount
total = cart.total

expected_discount = (subtotal * Decimal("0.10")).quantize(Decimal("0.01"))
expected_taxable = (subtotal - expected_discount).quantize(Decimal("0.01"))
expected_fee = (expected_taxable * settings_obj.platform_fee_percentage / 100).quantize(Decimal("0.01"))
expected_total = expected_taxable + expected_fee

check("coupon discount = 10% of subtotal", discount == expected_discount)
check("platform fee on post-discount taxable", fee == expected_fee)
check("total = taxable + fee", total == expected_total)

# Checkout
resp = client.post(
    "/checkout/",
    {
        "customer_name": "Test Guest",
        "email": "guest@example.com",
        "phone": "01712345678",
        "pickup_store": store.id,
        "payment_method": "BKASH",
        "payment_reference": "TRX" + uuid.uuid4().hex[:10].upper(),
        "note": "",
        "agree": "on",
    },
)
check("checkout redirects (order created)", resp.status_code == 302)

order = Order.objects.filter(guest_email="guest@example.com").order_by("-id").first()
check("order exists", order is not None)
if order:
    check("order subtotal snapshot", order.subtotal == subtotal)
    check("order fee snapshot", order.platform_fee_amount == expected_fee)
    check("order total snapshot", order.total_amount == expected_total)
    check("order awaiting verification", order.payment_status == "AWAITING_VERIFICATION")
    check("guest can track by public token", client.get(f"/orders/track/{order.public_token}/").status_code == 200)

    # Mark paid via model (admin action equivalent) -> coupon issued
    order.mark_paid()
    order.refresh_from_db()
    check("payment marked paid", order.payment_status == "PAID")
    next_coupon = Coupon.objects.filter(code=f"NEXT-{order.order_number}").first()
    check("next-purchase coupon issued on payment", next_coupon is not None)
    if next_coupon:
        check("next coupon is 5%", next_coupon.discount_value == Decimal("5.00"))

# Guest cannot view order detail by number (must be owner)
if order:
    check("guest blocked from /orders/<number>/", client.get(f"/orders/{order.order_number}/").status_code == 302)

print("\nFAILURES:", len(failures))
for f in failures:
    print(" -", f)
raise SystemExit(1 if failures else 0)
