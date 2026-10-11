"""Smoke-test key URLs against the local dev database."""
import os
import sys
from pathlib import Path

import django

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()  # noqa: E402

from django.test import Client  # noqa: E402

from apps.catalogue.models import Category, Product  # noqa: E402

client = Client()

product = Product.objects.first()
category = Category.objects.first()

urls = [
    "/",
    "/products/",
    f"/products/{product.slug}/",
    f"/categories/{category.slug}/",
    "/search/?q=rice",
    "/search/suggest/?q=ri",
    "/cart/",
    "/cart/panel/",
    "/cart/badge/",
    "/checkout/",
    "/promotions/flash-sale/",
    "/promotions/hot-deals/",
    "/about/",
    "/privacy/",
    "/terms/",
    "/brands/",
    "/stores/",
    "/contact/",
    "/analytics/live-count/",
    "/analytics/stats/",
    "/accounts/login/",
    "/accounts/register/",
]

failures = 0
for url in urls:
    try:
        resp = client.get(url)
        flag = "OK " if resp.status_code in (200, 301, 302) else "BAD"
        if flag == "BAD":
            failures += 1
        print(f"{flag} {resp.status_code}  {url}")
    except Exception as exc:  # noqa: BLE001
        failures += 1
        print(f"ERR      {url}  -> {type(exc).__name__}: {exc}")

# Cart add (POST)
resp = client.post("/cart/add/", {"product_id": product.id, "quantity": 2})
print(f"POST /cart/add/ -> {resp.status_code}  (badge: {resp.content[:40]!r})")
if resp.status_code != 200:
    failures += 1

# Checkout page with a cart
resp = client.get("/checkout/")
print(f"GET /checkout/ (with cart) -> {resp.status_code}")
if resp.status_code not in (200, 302):
    failures += 1

print("\nFAILURES:", failures)
raise SystemExit(1 if failures else 0)
