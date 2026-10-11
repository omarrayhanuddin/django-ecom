"""Focused tests for money rules, coupons and the order/payment flow."""
from decimal import Decimal

import pytest

from apps.cart.models import Cart
from apps.cart.services import add_item
from apps.catalogue.models import Category, Product
from apps.common.money import discount_percentage, percent_of, round_money
from apps.orders.models import Order, PaymentInstruction
from apps.orders.services import create_order_from_cart
from apps.pages.models import SiteSettings, StoreLocation
from apps.promotions.models import Coupon
from apps.promotions.services import issue_next_purchase_coupon, validate_coupon

pytestmark = pytest.mark.django_db


@pytest.fixture
def product():
    cat = Category.objects.create(name_bn="মুদি", name_en="Grocery")
    return Product.objects.create(
        name_bn="চাল", name_en="Rice", category=cat, sku="T-1",
        base_price=Decimal("500.00"), stock_quantity=10, track_inventory=True,
    )


def test_round_money_half_up():
    assert round_money("1.005") == Decimal("1.01")
    assert round_money(None) == Decimal("0.00")


def test_percent_of():
    assert percent_of(Decimal("468.00"), Decimal("2.5")) == Decimal("11.70")


def test_discount_percentage():
    assert discount_percentage(Decimal("500"), Decimal("400")) == 20
    assert discount_percentage(Decimal("500"), Decimal("500")) == 0


def test_coupon_percentage_and_cap():
    coupon = Coupon.objects.create(
        code="save20", discount_type=Coupon.DiscountType.PERCENTAGE,
        discount_value=Decimal("20"), max_discount_amount=Decimal("50"),
    )
    # 20% of 500 = 100, capped at 50
    assert coupon.discount_for(Decimal("500")) == Decimal("50")
    assert coupon.code == "SAVE20"


def test_validate_coupon_min_order(product):
    coupon = Coupon.objects.create(
        code="MIN", discount_type=Coupon.DiscountType.FIXED_AMOUNT,
        discount_value=Decimal("10"), minimum_order_value=Decimal("600"),
    )
    _c, discount, error = validate_coupon("min", None, Decimal("500"))
    assert error and discount == Decimal("0")


def test_order_fee_is_post_discount(product):
    settings_obj = SiteSettings.load()
    settings_obj.platform_fee_percentage = Decimal("2.5")
    settings_obj.save()
    store = StoreLocation.objects.create(name="Main", is_head_office=True)

    cart = Cart.objects.create(session_key="abc")
    add_item(cart, product, None, 2)  # subtotal 1000
    coupon = Coupon.objects.create(
        code="TEN", discount_type=Coupon.DiscountType.PERCENTAGE,
        discount_value=Decimal("10"),
    )
    cart.coupon = coupon
    cart.save()

    order = create_order_from_cart(
        cart,
        {
            "customer_name": "A", "email": "a@example.com", "phone": "01712345678",
            "pickup_store": store, "payment_method": Order.PaymentMethod.BKASH,
            "payment_reference": "T1", "note": "",
        },
        None,
    )
    assert order.subtotal == Decimal("1000.00")
    assert order.discount_amount == Decimal("100.00")
    # fee on (1000 - 100) = 900 -> 2.5% = 22.50
    assert order.platform_fee_amount == Decimal("22.50")
    assert order.total_amount == Decimal("922.50")
    assert order.payment_status == Order.PaymentStatus.AWAITING_VERIFICATION


def test_next_purchase_coupon_on_paid(product):
    store = StoreLocation.objects.create(name="Main2")
    cart = Cart.objects.create(session_key="xyz")
    add_item(cart, product, None, 1)
    order = create_order_from_cart(
        cart,
        {
            "customer_name": "B", "email": "b@example.com", "phone": "01712345678",
            "pickup_store": store, "payment_method": Order.PaymentMethod.BKASH,
            "payment_reference": "T2", "note": "",
        },
        None,
    )
    order.mark_paid()
    assert Coupon.objects.filter(code=f"NEXT-{order.order_number}").exists()


def test_payment_reference_is_unique(product):
    store = StoreLocation.objects.create(name="Main3")
    for ref in ("DUP",):
        cart = Cart.objects.create(session_key=f"s-{ref}")
        add_item(cart, product, None, 1)
        create_order_from_cart(
            cart,
            {
                "customer_name": "C", "email": "c@example.com", "phone": "01712345678",
                "pickup_store": store, "payment_method": Order.PaymentMethod.BKASH,
                "payment_reference": ref, "note": "",
            },
            None,
        )
    cart = Cart.objects.create(session_key="s-2")
    add_item(cart, product, None, 1)
    from django.db import IntegrityError

    with pytest.raises(IntegrityError):
        create_order_from_cart(
            cart,
            {
                "customer_name": "C", "email": "c@example.com", "phone": "01712345678",
                "pickup_store": store, "payment_method": Order.PaymentMethod.BKASH,
                "payment_reference": "DUP", "note": "",
            },
            None,
        )


def test_checkout_requires_login(client, product):
    """Anonymous users hitting /checkout/ are sent to login."""
    session = client.session
    session.save()
    cart = Cart.objects.create(session_key=session.session_key)
    add_item(cart, product, None, 1)
    resp = client.get("/checkout/")
    assert resp.status_code == 302
    assert "/accounts/login/" in resp["Location"]


def test_checkout_accessible_when_logged_in(client, product, django_user_model):
    user = django_user_model.objects.create_user(
        email="buyer@example.com", password="pw12345678",
        full_name="Buyer", phone_number="01712345678", onboarding_complete=True,
    )
    client.force_login(user)
    cart = Cart.objects.create(user=user)
    add_item(cart, product, None, 1)
    assert client.get("/checkout/").status_code == 200
