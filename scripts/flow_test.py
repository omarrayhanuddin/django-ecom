"""End-to-end flow test: auth-gated checkout -> coupon -> payment -> next-purchase coupon."""
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

# ── Anonymous user cannot check out ──
client.get("/cart/")
client.post("/cart/add/", {"product_id": product.id, "quantity": 1})
resp = client.get("/checkout/")
check("anonymous /checkout/ redirects to login", resp.status_code == 302 and "/accounts/login/" in resp.headers.get("Location", ""))

# ── Log in ──
user, _ = User.objects.get_or_create(
    email="flowtest@example.com",
    defaults={"full_name": "Flow Test", "phone_number": "01712345678", "onboarding_complete": True},
)
client.force_login(user)

# ── Build a cart as the user ──
client.post("/cart/add/", {"product_id": product.id, "quantity": 1})
client.post("/cart/apply-coupon/", {"code": "welcome10"})

cart = Cart.objects.filter(user=user).first()
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

check("authenticated /checkout/ loads", client.get("/checkout/").status_code == 200)

resp = client.post(
    "/checkout/",
    {
        "customer_name": "Flow Test",
        "email": user.email,
        "phone": "01712345678",
        "pickup_store": store.id,
        "payment_method": "BKASH",
        "payment_reference": "TRX" + uuid.uuid4().hex[:10].upper(),
        "note": "",
        "agree": "on",
    },
)
check("checkout redirects (order created)", resp.status_code == 302)

order = Order.objects.filter(user=user).order_by("-id").first()
check("order exists and belongs to the user", order is not None and order.user_id == user.id)
if order:
    check("order subtotal snapshot", order.subtotal == subtotal)
    check("order fee snapshot", order.platform_fee_amount == expected_fee)
    check("order total snapshot", order.total_amount == expected_total)
    check("order awaiting verification", order.payment_status == "AWAITING_VERIFICATION")

    order.mark_paid()
    order.refresh_from_db()
    check("payment marked paid", order.payment_status == "PAID")
    next_coupon = Coupon.objects.filter(code=f"NEXT-{order.order_number}").first()
    check("next-purchase coupon issued on payment", next_coupon is not None)
    if next_coupon:
        check("next coupon is 5%", next_coupon.discount_value == Decimal("5.00"))

    check("owner can view order detail", client.get(f"/orders/{order.order_number}/").status_code == 200)
    check("track by public token works", client.get(f"/orders/track/{order.public_token}/").status_code == 200)

print("\nFAILURES:", len(failures))
for f in failures:
    print(" -", f)
raise SystemExit(1 if failures else 0)
